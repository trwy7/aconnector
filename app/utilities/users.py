from functools import wraps
from datetime import datetime
from flask import request, abort
from app.db import Token

def get_user():
    token = request.cookies.get('abridgetoken')
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