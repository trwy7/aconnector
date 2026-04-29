from app import app
from app.types import request


@app.route("/.well-known/openid-configuration")
def oidcconf():
    return {
        "issuer": f"https://{request.host}",
        "authorization_endpoint": f"https://{request.host}/apps/auth",
        "token_endpoint": f"https://{request.host}/apps/token",
        "userinfo_endpoint": f"https://{request.host}/apps/userinfo",
        "jwks_uri": f"https://{request.host}/apps/jwks",
        "scopes_supported": ["openid", "profile", "email"],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["HS256", "RS256"],
        "token_endpoint_auth_methods_supported": [
            "client_secret_post",
            "client_secret_basic",
        ],
    }
