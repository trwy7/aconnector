from flask import render_template, request, redirect, abort
from app import app
from app.db import App
from app.utilities.users import require_user

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
    if request.user.level == 4 or ca.owner == request.user:
        return render_template("apps/modify.html", app=ca, host=request.host)
    return abort(403)

@app.route("/app/<string:clientid>", methods=["POST"])
@require_user
def modify_app(clientid):
    ca = App.query.get(clientid)
    if request.user.level == 4 or ca.owner == request.user:
        ca.edit(
            name=request.form['name'],
            redirect_url=request.form['redir'],
            launch_url=request.form['launch']
        )
        return redirect(request.path)
    return abort(403)

@app.route("/app/<string:clientid>/rerollsecret", methods=["POST"])
@require_user
def reroll_app_secret(clientid):
    if request.user.level == 4 or ca.owner == request.user:
        ca = App.query.get(clientid)
        ca.reroll_secret()
        return render_template("apps/reroll.html", app=ca)
    return abort(403)