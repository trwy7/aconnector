from flask import render_template
from app import app
from app.utilities.users import require_user

@app.route("/account")
@require_user
def account_page():
    return render_template("account/account.html")
