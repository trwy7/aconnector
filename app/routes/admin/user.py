from flask import abort, redirect, render_template

from app import app
from app.db import User
from app.types import request
from app.utilities.users import require_user


@app.route("/admin/user/<string:userid>")
@require_user
def admin_vuser_page(userid):
    if request.user.level != 3:
        return abort(403)
    muser = User.query.get(userid)
    if not muser:
        return abort(404)
    return render_template("admin/user.html", auser=muser)


@app.route("/admin/user/<string:userid>", methods=["POST"])
@require_user
def admin_vuser_modify(userid):
    if request.user.level != 3:
        return abort(403)
    muser = User.query.get(userid)
    if not muser:
        return abort(404)
    muser.edit(
        name=request.form["name"],
        email=request.form["email"],
        disable=request.form.get("disable") == "on",
        disable_apps=request.form.get("disableapp") == "on",
        allowed_apps=request.form["allowed_apps"]
        if request.form["allowed_apps"] != "all"
        else None,
    )
    return redirect(request.path)


@app.route("/admin/users/create")
@require_user
def admin_create_user_page():
    if request.user.level != 3:
        return abort(403)
    return render_template("admin/createuser.html")


@app.route("/admin/users/create", methods=["POST"])
@require_user
def admin_create_user():
    if request.user.level != 3:
        return abort(403)
    muser = User.create(
        username=request.form["uname"],
        name=request.form["name"],
        email=request.form["email"],
        disabled=request.form.get("disable") == "on",
    )
    return redirect("/admin/user/" + muser.id)


@app.route("/admin/user/<string:userid>/delete")
@require_user
def admin_vuser_del_page(userid):
    if request.user.level != 3:
        return abort(403)
    muser = User.query.get(userid)
    if not muser:
        return abort(404)
    return render_template("admin/deleteuser.html", auser=muser)


@app.route("/admin/user/<string:userid>/delete", methods=["POST"])
@require_user
def admin_vuser_delete(userid):
    if request.user.level != 3:
        return abort(403)
    muser = User.query.get(userid)
    if not muser:
        return abort(404)
    muser.delete()
    return redirect("/admin")
