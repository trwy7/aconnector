from flask import abort, render_template

from app import app
from app.db import App, User
from app.types import request
from app.utilities.users import require_user


@app.route("/admin")
@require_user
def admin_page():
    if request.user.level != 3:
        return abort(403)
    return render_template(
        "admin/admin.html", apps=App.query.all(), users=User.query.all()
    )
