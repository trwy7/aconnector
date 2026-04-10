import logging
import os
import importlib
from flask import Flask, request, redirect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Init logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("aconnector")

# Init app
logger.info("Starting AConnector")
app = Flask(__name__, template_folder="pages", static_folder="static")
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:////data/db.sqlite3'
app.config['NAME'] = os.environ.get("APP_NAME", "AuthBridge")

@app.context_processor
def add_conf():
    return {"gconfig": app.config}

## Init extensions
logger.debug("Init extensions")
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per 2 minutes", "20 per 10 seconds"],
    storage_uri="memory://",
    storage_options={"socket_connect_timeout": 30},
    strategy="fixed-window"
)

logger.debug("Init routes...")
# Import routes
rdir = os.path.join(os.path.dirname(__file__), "routes")
for root, _, files in os.walk(rdir):
    for file in files:
        if file.endswith(".py"):
            fd = os.path.join(root, file) \
                .replace(rdir, "app.routes") \
                .replace(os.sep, ".") \
                .replace(".py", "")
            logger.debug("Init route %s", fd)
            importlib.import_module(fd)
