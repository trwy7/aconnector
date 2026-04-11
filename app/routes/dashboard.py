from flask import render_template
from app import app
from app.utilities import users

@app.route("/dashboard")
@users.require_user
def dash_page():
    return render_template("dashboard.html")
