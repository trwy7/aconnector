from datetime import datetime
from functools import wraps

from flask import abort, render_template

from app import app, logger
from app.db import Token, User
from app.types import request


@app.before_request
def auth():
    request.user, request.token = get_user()
    if (
        request.user
        and request.user.disabled
        and request.path not in ["/static/style.css", "/static/script.js"]
    ):
        logger.debug(
            "[init/auth] Prevented disabled user %s from accessing %s",
            request.user.username,
            request.path,
        )
        return render_template("account/disabled.html"), 403


def get_user() -> tuple[None, None] | tuple[User, Token]:
    token = request.cookies.get("abridgetoken")
    if token:
        token = Token.query.get(token)
        if token and token.expiry > datetime.now():
            return token.user, token
    return None, None


def require_user(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not request.user:
            return abort(401)
        return func(*args, **kwargs)

    return wrapper
