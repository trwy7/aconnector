import binascii
import secrets
from datetime import datetime, timedelta, UTC
from urllib.parse import urlencode

from authlib.jose import jwt
from flask import jsonify, redirect, request

from app import app
from app.db import App, User

AUTH_CODE_TTL_SECONDS = 120
ACCESS_TOKEN_TTL_SECONDS = 600

auth_codes = {}
access_tokens = {}


def _now() -> datetime:
    return datetime.now(UTC)


def _purge_expired() -> None:
    now = _now()
    expired_codes = [code for code, data in auth_codes.items() if data["exp"] <= now]
    for code in expired_codes:
        auth_codes.pop(code, None)

    expired_tokens = [token for token, data in access_tokens.items() if data["exp"] <= now]
    for token in expired_tokens:
        access_tokens.pop(token, None)


def _oidc_error_redirect(redirect_uri: str, error: str, state: str | None = None):
    query = {"error": error}
    if state:
        query["state"] = state
    return redirect(f"{redirect_uri}?{urlencode(query)}")


def _client_authenticate(client: App):
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Basic "):
        try:
            from base64 import b64decode

            raw = b64decode(auth_header.split(" ", 1)[1]).decode("utf-8")
            cid, csecret = raw.split(":", 1)
            return secrets.compare_digest(cid, client.client_id) and secrets.compare_digest(csecret, client.client_secret)
        except (ValueError, UnicodeDecodeError, binascii.Error):
            return False

    posted_id = request.form.get("client_id", "")
    posted_secret = request.form.get("client_secret", "")
    return secrets.compare_digest(posted_id, client.client_id) and secrets.compare_digest(posted_secret, client.client_secret)


def _build_id_token(client: App, user: User, nonce: str | None = None):
    now = _now()
    claims = {
        "iss": f"https://{request.host}/app/{client.client_id}",
        "sub": user.id,
        "aud": client.client_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ACCESS_TOKEN_TTL_SECONDS)).timestamp()),
        "auth_time": int(now.timestamp()),
        "email": user.email,
        "name": user.name,
        "preferred_username": user.username,
    }
    if nonce:
        claims["nonce"] = nonce
    return jwt.encode({"alg": "HS256"}, claims, client.client_secret).decode("utf-8")


@app.route("/apps/auth")
def auth_oidc_page():
    _purge_expired()

    client_id = request.args.get("client_id")
    redirect_uri = request.args.get("redirect_uri")
    state = request.args.get("state")
    scope = request.args.get("scope", "")

    client = App.query.get(client_id) if client_id else None
    if not client:
        return jsonify({"error": "invalid_client"}), 400

    if redirect_uri != client.redirect_url:
        return jsonify({"error": "invalid_request", "error_description": "redirect_uri mismatch"}), 400

    if request.args.get("response_type") != "code":
        return _oidc_error_redirect(redirect_uri, "unsupported_response_type", state)

    requested_scopes = set(scope.split()) if scope else set()
    if "openid" not in requested_scopes:
        return _oidc_error_redirect(redirect_uri, "invalid_scope", state)
    if "offline_access" in requested_scopes:
        return _oidc_error_redirect(redirect_uri, "invalid_scope", state)

    if not request.user:
        return _oidc_error_redirect(redirect_uri, "login_required", state)

    if request.user not in client.user_auths:
        client.user_auths.append(request.user)

    code = secrets.token_urlsafe(32)
    auth_codes[code] = {
        "client_id": client.client_id,
        "user_id": request.user.id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(sorted(requested_scopes)),
        "nonce": request.args.get("nonce"),
        "exp": _now() + timedelta(seconds=AUTH_CODE_TTL_SECONDS),
    }

    from app.db import db

    db.session.commit()
    return redirect(f"{redirect_uri}?{urlencode({'code': code, 'state': state} if state else {'code': code})}")


@app.route("/apps/token", methods=["POST"])
def token_oidc_page():
    _purge_expired()

    if request.form.get("grant_type") != "authorization_code":
        return jsonify({"error": "unsupported_grant_type"}), 400

    code = request.form.get("code", "")
    code_data = auth_codes.pop(code, None)
    if not code_data:
        return jsonify({"error": "invalid_grant"}), 400

    client = App.query.get(code_data["client_id"])
    if not client or not _client_authenticate(client):
        return jsonify({"error": "invalid_client"}), 401

    redirect_uri = request.form.get("redirect_uri")
    if redirect_uri != code_data["redirect_uri"]:
        return jsonify({"error": "invalid_grant"}), 400

    user = User.query.get(code_data["user_id"])
    if not user or user.disabled:
        return jsonify({"error": "invalid_grant"}), 400

    access_token = secrets.token_urlsafe(32)
    token_exp = _now() + timedelta(seconds=ACCESS_TOKEN_TTL_SECONDS)
    access_tokens[access_token] = {
        "client_id": client.client_id,
        "user_id": user.id,
        "scope": code_data["scope"],
        "exp": token_exp,
    }

    id_token = _build_id_token(client, user, code_data.get("nonce"))
    return jsonify(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_TTL_SECONDS,
            "id_token": id_token,
            "scope": code_data["scope"],
        }
    )


@app.route("/apps/userinfo")
def userinfo_oidc_page():
    _purge_expired()

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "invalid_token"}), 401

    token = auth_header.split(" ", 1)[1]
    token_data = access_tokens.get(token)
    if not token_data:
        return jsonify({"error": "invalid_token"}), 401

    user = User.query.get(token_data["user_id"])
    if not user:
        return jsonify({"error": "invalid_token"}), 401

    scopes = set(token_data["scope"].split()) if token_data["scope"] else set()
    claims = {"sub": user.id}
    if "email" in scopes:
        claims["email"] = user.email
        claims["email_verified"] = True
    if "profile" in scopes:
        claims["name"] = user.name
        claims["preferred_username"] = user.username

    return jsonify(claims)


@app.route("/apps/jwks")
def jwks_oidc_page():
    return jsonify({"keys": []})