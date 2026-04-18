import random
from datetime import datetime, timedelta
from flask import render_template, request, make_response
from app import app, limiter
from app.db import User
from app.utilities.users import require_user

code_list: dict[tuple[str, datetime], tuple[str, str]] = {}

@app.route("/codelogin")
def codelogin_page():
    return render_template("auth/codelogin.html")

@app.route("/codelogin", methods=['POST'])
@limiter.limit("1 per 2 seconds", key_func=lambda: request.form.get("uname"))
@limiter.limit("5 per minute", key_func=lambda: request.form.get("uname"))
@limiter.limit("20 per hour", key_func=lambda: request.form.get("uname"))
def codelogin_post():
    rc = code_list.pop((int(request.form['code']), request.form['uname']), None)
    if (not rc) or rc[1] < datetime.now():
        return render_template("auth/codelogin.html", status="Invalid combination")
    uid = rc[0]
    luser = User.query.get(uid)
    if not luser:
        return "uh oh", 500
    rs = make_response(render_template("auth/logincomplete.html", user=luser))
    rs.set_cookie(
        "abridgetoken",
        luser.create_token().token,
        httponly=True,
        secure=False,
        max_age=2419200
    )
    return rs

@app.route("/account/getlogincode", methods=['POST'])
@limiter.limit("1 per 2 seconds", key_func=lambda: request.user)
@require_user
def codecreate_post():
    code = random.randint(1000000, 9999999)
    code_list[(code, request.user.username)] = (request.user.id, datetime.now() + timedelta(minutes=5))
    return render_template("account/codegen.html", code=code)