from flask import Flask, request, redirect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__, template_folder="pages", static_folder="static")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/db.sqlite3'

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per 2 minutes", "20 per 10 seconds"],
    storage_uri="redis://acredis:6379",
    storage_options={"socket_connect_timeout": 30},
    strategy="fixed-window"
)

