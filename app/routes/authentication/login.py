from flask import render_template, request
from app import app
from app.db import User

@app.route("/login")
def login_page():
    return render_template("auth/login.html")

@app.route("/login", methods=['POST'])
def login_post():
    # TODO: Email regex
    return str(request.form)