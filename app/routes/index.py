from flask import render_template, request, redirect
from app import app

@app.route("/")
def index():
    if request.user:
        return redirect("/dashboard")
    return render_template("index.html")
