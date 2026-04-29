from flask import redirect, render_template

from app import app
from app.types import request


@app.route("/")
def index():
    if request.user:
        return redirect("/dashboard")
    return render_template("index.html")
