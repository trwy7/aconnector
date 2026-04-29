from flask import render_template

from app import app
from app.utilities.users import require_user


@app.route("/apps")
@require_user
def apps_page():
    return render_template("account/apps.html")
