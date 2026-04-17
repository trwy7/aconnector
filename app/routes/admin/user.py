from flask import render_template, request, abort
from app import app
from app.db import User
from app.utilities.users import require_user

@app.route("/admin/user/<string:userid>")
@require_user
def admin_vuser_page(userid):
    if request.user.level != 3:
        return abort(403)
    muser = User.query.get(userid)
    if not muser:
        return abort(404)
    return render_template("admin/user.html", user=muser)

@app.route("/admin/user/<string:userid>", methods=['POST'])
@require_user
def admin_vuser_modify(userid):
    if request.user.level != 3:
        return abort(403)
    muser = User.query.get(userid)
    if not muser:
        return abort(404)

    return redirect(request.path)
