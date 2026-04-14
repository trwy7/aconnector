from flask import request
from app.utilities.users import require_user
from app import app

@app.route("/apps/auth")
def auth_oidc_page():
    return request.args

@app.route("/apps/token")
def token_oidc_page():
    return request.args

@app.route("/apps/userinfo")
def userinfo_oidc_page():
    return request.args

@app.route("/apps/jwks")
def jwks_oidc_page():
    return request.args