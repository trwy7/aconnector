import random
from datetime import datetime, timedelta

from flask import make_response, render_template

from app import app, limiter
from app.db import User
from app.types import request
from app.utilities.jwt import decode_jwt
from app.utilities.users import require_user

code_list: dict[tuple[int, str], tuple[str, datetime]] = {}


@app.route("/login/code")
def codelogin_page():
    return render_template("auth/codelogin.html", gota=request.args.get("gota"))


@app.route("/login/code", methods=["POST"])
@limiter.limit("1 per 2 seconds", key_func=lambda: request.form.get("uname", ""))
@limiter.limit("5 per minute", key_func=lambda: request.form.get("uname", ""))
@limiter.limit("20 per hour", key_func=lambda: request.form.get("uname", ""))
def codelogin_post():
    rc = code_list.pop((int(request.form["code"]), request.form["uname"]), None)
    if (not rc) or rc[1] < datetime.now():
        return render_template(
            "auth/codelogin.html",
            status="Invalid combination",
            gota=request.form.get("gota"),
        )
    uid = rc[0]
    luser = User.query.get(uid)
    if not luser:
        return "uh oh", 500
    if request.form.get("gota"):
        gota_path = decode_jwt(request.form.get("gota"))["rt"]
        if gota_path.startswith("/"):
            rs = make_response(
                render_template(
                    "auth/logincomplete.html", user=luser, gota_path=gota_path
                )
            )
        else:
            rs = make_response(render_template("auth/logincomplete.html", user=luser))
    else:
        rs = make_response(render_template("auth/logincomplete.html", user=luser))
    rs.set_cookie(
        "abridgetoken",
        luser.create_token().token,
        httponly=True,
        secure=False,
        max_age=2419200,
    )
    return rs


@app.route("/account/getlogincode", methods=["POST"])
@limiter.limit("1 per 2 seconds", key_func=lambda: request.user)
@require_user
def codecreate_post():
    code = random.randint(1000000, 9999999)
    code_list[(code, request.user.username)] = (
        request.user.id,
        datetime.now() + timedelta(minutes=5),
    )
    return render_template("account/codegen.html", code=code)
