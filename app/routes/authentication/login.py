from flask import render_template
from app import app
from app.db import User

@app.route("/login")
def login_page():
    return render_template("auth/login.html")