from flask import render_template, request, redirect
from app import app
from app.utilities.users import require_user

@app.route("/account")
@require_user
def account_page():
    return render_template("account/account.html")

@app.route("/account/namechange")
@require_user
def namechange_page():
    return render_template("account/namechange.html")

@app.route("/account/namechange", methods=['POST'])
@require_user
def namechange():
    request.user.edit(name=request.form['name'])
    return redirect("/account")
