from datetime import datetime
from flask import request
from app.db import Token

def get_user():
    token = request.cookies.get('abridgetoken')
    if token:
        token = Token.query.get(token)
        if token and token.expiry > datetime.now():
            return token.user, token
    return None, None