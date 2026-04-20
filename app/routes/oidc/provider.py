import binascii
import json
import os
import secrets
from datetime import datetime, timedelta, UTC
from urllib.parse import urlencode
from base64 import b64decode
from authlib.jose import JsonWebKey, jwt
from flask import jsonify, redirect, request, render_template

from app import app, logger
from app.db import App, User, db
from app.utilities.users import require_user

AUTH_CODE_TTL_SECONDS = 120
ACCESS_TOKEN_TTL_SECONDS = 600
SUPPORTED_ID_TOKEN_ALGS = {"HS256", "RS256"}
OIDC_SIGNING_KEY_PATH = "/data/oidc_signing_key.json"

auth_codes = {}
access_tokens = {}


def _load_oidc_signing_key():
    try:
        with open(OIDC_SIGNING_KEY_PATH, "r", encoding="utf-8") as key_file:
            key_data = json.load(key_file)
        logger.info("[oidc] loaded persisted signing key")
        return JsonWebKey.import_key(key_data)
    except FileNotFoundError:
        signing_key = JsonWebKey.generate_key("RSA", 2048, is_private=True)
        key_data = signing_key.as_dict(is_private=True)
        os.makedirs(os.path.dirname(OIDC_SIGNING_KEY_PATH), exist_ok=True)
        temp_path = f"{OIDC_SIGNING_KEY_PATH}.tmp"
        with open(temp_path, "w", encoding="utf-8") as key_file:
            json.dump(key_data, key_file)
        os.replace(temp_path, OIDC_SIGNING_KEY_PATH)
        logger.info("[oidc] generated new persisted signing key")
        return signing_key


oidc_signing_key = _load_oidc_signing_key()
oidc_public_jwk = oidc_signing_key.as_dict()
oidc_public_jwk["use"] = "sig"
oidc_public_jwk["alg"] = "RS256"


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
    logger.warning("[oidc] redirecting client error=%s", error)
    query = {"error": error}
    if state:
        query["state"] = state
    return redirect(f"{redirect_uri}?{urlencode(query)}")


def _client_authenticate(client: App):
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Basic "):
        try:
            raw = b64decode(auth_header.split(" ", 1)[1]).decode("utf-8")
            cid, csecret = raw.split(":", 1)
            return secrets.compare_digest(cid, client.client_id) and secrets.compare_digest(csecret, client.client_secret)
        except (ValueError, UnicodeDecodeError, binascii.Error):
            logger.warning("[oidc] basic client authentication failed for client_id=%s", client.client_id)
            return False

    posted_id = request.form.get("client_id", "")
    posted_secret = request.form.get("client_secret", "")
    if posted_id or posted_secret:
        logger.debug("[oidc] client authentication via post for client_id=%s", client.client_id)
    return secrets.compare_digest(posted_id, client.client_id) and secrets.compare_digest(posted_secret, client.client_secret)


def _resolve_id_token_alg(client: App) -> str:
    requested_alg = request.args.get("id_token_signed_response_alg") or request.args.get("id_token_alg")
    if requested_alg and requested_alg not in SUPPORTED_ID_TOKEN_ALGS:
        logger.warning("[oidc] unsupported id token alg requested for client_id=%s: %s", client.client_id, requested_alg)
        return ""
    return requested_alg or "RS256"


def _build_id_token(client: App, user: User, nonce: str | None = None, alg: str = "RS256"):
    # FIXME: respect scopes (and update documentation)
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
    if alg == "HS256":
        return jwt.encode({"alg": "HS256"}, claims, client.client_secret).decode("utf-8")
    return jwt.encode({"alg": "RS256", "kid": oidc_public_jwk["kid"]}, claims, oidc_signing_key).decode("utf-8")


@app.route("/apps/auth")
def auth_oidc_page():
    _purge_expired()
    client_id = request.args.get("client_id")
    redirect_uri = request.args.get("redirect_uri")
    state = request.args.get("state")
    scope = request.args.get("scope", "")

    logger.info("[oidc] authorization request client_id=%s scope=%s response_type=%s", client_id, scope, request.args.get("response_type"))

    client = App.query.get(client_id) if client_id else None
    if not client:
        logger.warning("[oidc] unknown client_id=%s", client_id)
        return jsonify({"error": "invalid_client"}), 400

    if redirect_uri != client.redirect_url:
        logger.warning("[oidc] redirect_uri mismatch client_id=%s", client.client_id)
        return jsonify({"error": "invalid_request", "error_description": "redirect_uri mismatch"}), 400

    if request.args.get("response_type") != "code":
        logger.warning("[oidc] unsupported response_type for client_id=%s", client.client_id)
        return _oidc_error_redirect(redirect_uri, "unsupported_response_type", state)

    requested_scopes = set(scope.split()) if scope else set()
    if "openid" not in requested_scopes:
        logger.warning("[oidc] missing openid scope for client_id=%s", client.client_id)
        return _oidc_error_redirect(redirect_uri, "invalid_scope", state)
    if "offline_access" in requested_scopes:
        logger.warning("[oidc] offline_access requested but unsupported client_id=%s", client.client_id)
        return _oidc_error_redirect(redirect_uri, "invalid_scope", state)

    id_token_alg = _resolve_id_token_alg(client)
    if not id_token_alg:
        return _oidc_error_redirect(redirect_uri, "invalid_request", state)

    if not request.user:
        return redirect("/login?gota=" + client_id)

    if request.user.allowed_apps is not None and client.client_id not in request.user.allowed_apps.split(","):
        logger.debug("[oidc] user=%s is not allowed to access client_id=%s", request.user.username, client.client_id)
        return render_template("templates/error.html", status_code=403, error_message=f"An administrator has restricted your account from accessing <b>{client.name}</b>. Contact <b>{app.config['CONTACT_EMAIL']}</b> for more information."), 403

    if request.user not in client.user_auths:
        logger.debug("[oidc] requesting user=%s access to client_id=%s", request.user.username, client.client_id)
        return render_template("apps/auth.html", app=client)

    logger.debug("[oidc] user=%s is re-accessing client_id=%s", request.user.username, client.client_id)

    code = secrets.token_urlsafe(32)
    auth_codes[code] = {
        "client_id": client.client_id,
        "user_id": request.user.id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(sorted(requested_scopes)),
        "nonce": request.args.get("nonce"),
        "id_token_alg": id_token_alg,
        "exp": _now() + timedelta(seconds=AUTH_CODE_TTL_SECONDS),
    }

    #db.session.commit()
    logger.info("[oidc] issued authorization code for user=%s client_id=%s", request.user.username, client.client_id)
    return redirect(f"{redirect_uri}?{urlencode({'code': code, 'state': state} if state else {'code': code})}")

@app.route("/apps/auth", methods=['POST'])
@require_user
def auth_oidc_post():
    _purge_expired()
    client_id = request.args.get("client_id")
    redirect_uri = request.args.get("redirect_uri")
    state = request.args.get("state")
    scope = request.args.get("scope", "")

    logger.info("[oidc] authorization request client_id=%s scope=%s response_type=%s", client_id, scope, request.args.get("response_type"))

    client = App.query.get(client_id) if client_id else None
    if not client:
        logger.warning("[oidc] unknown client_id=%s", client_id)
        return jsonify({"error": "invalid_client"}), 400

    if redirect_uri != client.redirect_url:
        logger.warning("[oidc] redirect_uri mismatch client_id=%s", client.client_id)
        return jsonify({"error": "invalid_request", "error_description": "redirect_uri mismatch"}), 400

    if request.args.get("response_type") != "code":
        logger.warning("[oidc] unsupported response_type for client_id=%s", client.client_id)
        return _oidc_error_redirect(redirect_uri, "unsupported_response_type", state)

    requested_scopes = set(scope.split()) if scope else set()
    if "openid" not in requested_scopes:
        logger.warning("[oidc] missing openid scope for client_id=%s", client.client_id)
        return _oidc_error_redirect(redirect_uri, "invalid_scope", state)
    if "offline_access" in requested_scopes:
        logger.warning("[oidc] offline_access requested but unsupported client_id=%s", client.client_id)
        return _oidc_error_redirect(redirect_uri, "invalid_scope", state)
    
    if request.form.get('choice') != "Allow":
        logger.warning("[oidc] User denied auth for client_id=%s", client.client_id)
        return _oidc_error_redirect(redirect_uri, "access_denied", state)

    id_token_alg = _resolve_id_token_alg(client)
    if not id_token_alg:
        return _oidc_error_redirect(redirect_uri, "invalid_request", state)

    if request.user.allowed_apps is not None and client.client_id not in request.user.allowed_apps.split(","):
        logger.debug("[oidc] user=%s is not allowed to access client_id=%s", request.user.username, client.client_id)
        return render_template("templates/error.html", status_code=403, error_message=f"An administrator has restricted your account from accessing <b>{client.name}</b>. Contact {app.config['CONTACT_EMAIL']} for more information."), 403

    if request.user not in client.user_auths:
        logger.debug("[oidc] granted user=%s access to client_id=%s", request.user.username, client.client_id)
        client.user_auths.append(request.user)
        db.session.commit()


    code = secrets.token_urlsafe(32)
    auth_codes[code] = {
        "client_id": client.client_id,
        "user_id": request.user.id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(sorted(requested_scopes)),
        "nonce": request.args.get("nonce"),
        "id_token_alg": id_token_alg,
        "exp": _now() + timedelta(seconds=AUTH_CODE_TTL_SECONDS),
    }

    logger.info("[oidc] issued authorization code for user=%s client_id=%s", request.user.username, client.client_id)
    return redirect(f"{redirect_uri}?{urlencode({'code': code, 'state': state} if state else {'code': code})}")

@app.route("/apps/token", methods=["POST"])
def token_oidc_page():
    _purge_expired()

    logger.info("[oidc] token request grant_type=%s", request.form.get("grant_type"))

    if request.form.get("grant_type") != "authorization_code":
        logger.warning("[oidc] unsupported token grant_type=%s", request.form.get("grant_type"))
        return jsonify({"error": "unsupported_grant_type"}), 400

    code = request.form.get("code", "")
    code_data = auth_codes.pop(code, None)
    if not code_data:
        logger.warning("[oidc] invalid or expired authorization code")
        return jsonify({"error": "invalid_grant"}), 400

    client = App.query.get(code_data["client_id"])
    if not client or not _client_authenticate(client):
        logger.warning("[oidc] token request client authentication failed client_id=%s", code_data["client_id"])
        return jsonify({"error": "invalid_client"}), 401

    redirect_uri = request.form.get("redirect_uri")
    if redirect_uri != code_data["redirect_uri"]:
        logger.warning("[oidc] token request redirect_uri mismatch client_id=%s", client.client_id)
        return jsonify({"error": "invalid_grant"}), 400

    user = User.query.get(code_data["user_id"])
    if not user or user.disabled:
        logger.warning("[oidc] token request user unavailable client_id=%s", client.client_id)
        return jsonify({"error": "invalid_grant"}), 400

    access_token = secrets.token_urlsafe(32)
    token_exp = _now() + timedelta(seconds=ACCESS_TOKEN_TTL_SECONDS)
    access_tokens[access_token] = {
        "client_id": client.client_id,
        "user_id": user.id,
        "scope": code_data["scope"],
        "exp": token_exp,
    }

    id_token_alg = code_data.get("id_token_alg", "RS256")
    id_token = _build_id_token(client, user, code_data.get("nonce"), id_token_alg)
    logger.info("[oidc] issued tokens for user=%s client_id=%s id_token_alg=%s", user.username, client.client_id, id_token_alg)
    return jsonify({
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": ACCESS_TOKEN_TTL_SECONDS,
        "id_token": id_token,
        "scope": code_data["scope"],
    })


@app.route("/apps/userinfo")
def userinfo_oidc_page():
    _purge_expired()

    logger.debug("[oidc] userinfo request")

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        logger.warning("[oidc] userinfo missing bearer token")
        return jsonify({"error": "invalid_token"}), 401

    token = auth_header.split(" ", 1)[1]
    token_data = access_tokens.get(token)
    if not token_data:
        logger.warning("[oidc] userinfo invalid or expired token")
        return jsonify({"error": "invalid_token"}), 401

    user = User.query.get(token_data["user_id"])
    if not user:
        logger.warning("[oidc] userinfo user not found")
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
    logger.debug("[oidc] jwks requested")
    return jsonify({"keys": [oidc_public_jwk]})