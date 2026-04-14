from flask import request
from app import app

@app.route("/app/<string:clientid>/.well-known/openid-configuration")
def app_oidcconf(clientid):
    return { # TODO: end_session_endpoint
        "issuer": f"https://{request.host}/app/{clientid}",
        "authorization_endpoint": f"https://{request.host}/apps/auth",
        "token_endpoint": f"https://{request.host}/apps/token",
        "userinfo_endpoint": f"https://{request.host}/apps/token",
        "jwks_uri": f"https://{request.host}/apps/jwks" # Authentik uses the client id in this, we may need to also.
    }