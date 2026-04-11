from flask import render_template, request, url_for, redirect
from app import app, logger, limiter
from app.db import User, db
from app.utilities import email

@app.route("/dashboard")
def dash_page():
    return render_template("dashboard.html")
