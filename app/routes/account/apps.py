from flask import render_template, request, redirect
from app import app
from app.db import App
from app.utilities.users import require_user

# FIXME: enforce permissions

@app.route("/apps")
@require_user
def apps_page():
    return render_template("account/apps.html")

@app.route("/apps/create")
@require_user
def create_app_page():
    da = App.create(
        request.user,
        "My new app"
    )
    return redirect(f"/app/{da.client_id}")

@app.route("/app/<string:clientid>")
@require_user
def modify_app_page(clientid):
    ca = App.query.get(clientid)
    return render_template("apps/modify.html", app=ca)

@app.route("/app/<string:clientid>", methods=["POST"])
@require_user
def modify_app(clientid):
    ca = App.query.get(clientid)
    ca.edit(
        name=request.form['name'],
        redirect_url=request.form['redir'],
        launch_url=request.form['launch']
    )
    return render_template("apps/modify.html", app=ca)

@app.route("/app/<string:clientid>/rerollsecret", methods=["POST"])
@require_user
def reroll_app_secret(clientid):
    ca = App.query.get(clientid)
    ca.reroll_secret()
    return render_template("apps/reroll.html", app=ca)