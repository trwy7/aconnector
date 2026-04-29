import importlib
import logging
import os
import re

from flask import Flask, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.types import request

# Init logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("authbridge")

# Init app
logger.info("Starting AuthBridge")
app = Flask(__name__, template_folder="pages", static_folder="static")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////data/db.sqlite3"
app.config["NAME"] = os.environ.get("APP_NAME", "AuthBridge")
app.config["OWNER_EMAIL"] = os.environ.get("OWNER_EMAIL", "")
app.config["CONTACT_EMAIL"] = os.environ.get("CONTACT_EMAIL", "")
app.config["VEMAIL_REGEX"] = re.compile(os.environ.get("VEMAIL_REGEX", ""))
app.config["VEMAIL_MESSAGE"] = os.environ.get("VEMAIL_MESSAGE", "")
app.config["LOCK_NEW_USER_APP_CREATE"] = (
    os.environ.get("LOCK_NEW_APP_CREATE", "true").lower() != "false"
)

from .utilities import users


@app.before_request
def auth():
    request.user, request.token = users.get_user()
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


@app.context_processor
def ctx_processor():
    return {
        "gconfig": app.config,
        "user": request.user,
        "token": request.token,
        "host": request.host,
    }


## Init extensions
logger.debug("Init flask extensions")
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per 2 minutes", "20 per 10 seconds"],
    storage_uri="memory://",
    storage_options={"socket_connect_timeout": 30},
    strategy="fixed-window",
)

logger.debug("Init routes...")
# Import routes
rdir = os.path.join(os.path.dirname(__file__), "routes")
for root, _, files in os.walk(rdir):
    for file in files:
        if file.endswith(".py"):
            fd = (
                os.path.join(root, file)
                .replace(rdir, "app.routes")
                .replace(os.sep, ".")
                .replace(".py", "")
            )
            logger.debug("Init route %s", fd)
            _ = importlib.import_module(fd)
