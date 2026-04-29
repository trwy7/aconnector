from flask import render_template

from app import app


@app.route("/help/oidc")
def help_oidc():
    return render_template("help/oidc.html")
