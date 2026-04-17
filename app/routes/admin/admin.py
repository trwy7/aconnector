from flask import render_template, request, abort
from app import app
from app.db import App, User
from app.utilities.users import require_user

@app.route("/admin")
@require_user
def admin_page():
    if request.user.level != 3:
        return abort(403)
    return render_template("admin/admin.html", apps=App.query.all(), users=User.query.all())
