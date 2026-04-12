from flask import render_template, request, redirect
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
        "New app"
    )
    return redirect(f"/app/{da.client_id}")