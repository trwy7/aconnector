from typing import TYPE_CHECKING

from flask import Request
from flask import request as flask_request

from app.db import Token, User


class AuthRequest(Request):
    user: User  # Technically can be None but that breaks type checking so we dont do it
    token: Token


if TYPE_CHECKING:
    request: AuthRequest = flask_request  # type: ignore
else:
    from flask import request
