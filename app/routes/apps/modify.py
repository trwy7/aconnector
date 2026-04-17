from flask import render_template, request, redirect, abort
from app import app
from app.db import App
from app.utilities.users import require_user

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
    if not ca:
        return abort(404)
    if request.user.level == 3 or ca.owner == request.user:
        return render_template("apps/modify.html", app=ca, host=request.host)
    return abort(403)

@app.route("/app/<string:clientid>", methods=["POST"])
@require_user
def modify_app(clientid):
    ca = App.query.get(clientid)
    if not ca:
        return abort(404)
    if request.user.level == 3 or ca.owner == request.user:
        ca.edit(
            name=request.form['name'],
            redirect_url=request.form['redir'],
            launch_url=request.form['launch']
        )
        return redirect(request.path)
    return abort(403)

@app.route("/app/<string:clientid>/delete")
@require_user
def delete_app_page(clientid):
    ca = App.query.get(clientid)
    if not ca:
        return abort(404)
    if request.user.level == 3 or ca.owner == request.user:
        return render_template("apps/delete.html", app=ca)
    return abort(403)

@app.route("/app/<string:clientid>/delete", methods=["POST"])
@require_user
def delete_app(clientid):
    ca = App.query.get(clientid)
    if not ca:
        return abort(404)
    if request.user.level == 3 or ca.owner == request.user:
        ca.delete()
        return redirect("/apps")
    return abort(403)

@app.route("/app/<string:clientid>/rerollsecret", methods=["POST"])
@require_user
def reroll_app_secret(clientid):
    if ca.owner == request.user:
        ca = App.query.get(clientid)
        ca.reroll_secret()
        return render_template("apps/reroll.html", app=ca)
    return abort(403)