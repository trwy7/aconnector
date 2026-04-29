from datetime import datetime
from functools import wraps

from flask import abort

from app.db import Token, User
from app.types import request


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
