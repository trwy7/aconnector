import random
import re
from datetime import datetime, timedelta

from flask import redirect, render_template

from app import app, limiter, logger
from app.db import User
from app.types import request
from app.utilities import email
from app.utilities.jwt import decode_jwt
from app.utilities.users import require_user

register_list = {}
loginc_list = {}


def _cleanup():
    now = datetime.now()
    # Login codes
    td = []
    for tdv, (_, ed) in loginc_list.items():
        if ed < now:
            td.append(tdv)
    for tdv in td:
        loginc_list.pop(tdv, None)
    # Register codes
    td = []
    for tdv, (_, ed) in register_list.items():
        if ed < now:
            td.append(tdv)
    for tdv in td:
        register_list.pop(tdv, None)


@app.route("/login")
def login_page():
    _cleanup()
    if request.user:
        return redirect("/dashboard")
    return render_template("auth/login.html", gota=request.args.get("gota"))


@app.route("/login", methods=["POST"])
@limiter.limit("1 per 5 seconds")
@limiter.limit("5 per minute")
@limiter.limit("30 per hour")
@limiter.limit("1 per 5 seconds", key_func=lambda: request.form.get("email"))
@limiter.limit("2 per minute", key_func=lambda: request.form.get("email"))
@limiter.limit("10 per hour", key_func=lambda: request.form.get("email"))
def login_post():
    _cleanup()
    if request.user:
        return redirect("/dashboard")
    luser = User.query.filter_by(email=request.form["email"]).first()
    if luser:
        logger.debug(
            "[login] Found user for %s: %s. Sending email...",
            request.form["email"],
            luser.username,
        )
        code = random.randint(1000000, 9999999)
        vcode = random.randbytes(5).hex()
        loginc_list[(code, vcode, request.form["email"])] = (
            luser.id,
            datetime.now() + timedelta(minutes=5),
        )
        email.send(
            request.form["email"],
            f"Welcome back, {luser.username}!",
            f"Your login code is {str(code)}, enter it to sign back in.\nThe code expires in 5 minutes.\nid: {vcode}",
        )
        return render_template(
            "auth/logincode.html",
            email=request.form["email"],
            vcode=vcode,
            gota=request.form.get("gota"),
        )
    else:
        if not re.fullmatch(app.config["VEMAIL_REGEX"], request.form["email"]):
            logger.debug("[login] Email did not pass regex: %s", request.form["email"])
            return render_template("auth/login.html", status="Invalid email")
        logger.debug("[login] Sending register email to %s", request.form["email"])
        if (
            request.form["email"] not in register_list
            or register_list[request.form["email"]][1] < datetime.now()
        ):
            register_list[request.form["email"]] = (
                random.randint(100000, 999999),
                datetime.now() + timedelta(minutes=5),
            )
        email.send(
            request.form["email"],
            f"Your {app.config['NAME']} resgistration code is {str(register_list[request.form['email']][0])}",
            f"Hello!\nYour code is: {str(register_list[request.form['email']][0])}.\nYour code expires in 5 minutes, if you did not request this email, you may discard it.",
        )
        return render_template(
            "auth/requestcode.html",
            email=request.form["email"],
            gota=request.form.get("gota"),
        )


@app.route("/loginc", methods=["POST"])
@limiter.limit("5 per 4 seconds")
@limiter.limit("3 per 4 seconds", key_func=lambda: request.form.get("vcode"))
@limiter.limit("30 per 1 minute", key_func=lambda: request.form.get("vcode"))
def logincode_post():
    _cleanup()
    if request.user:
        return redirect("/dashboard")
    lc = loginc_list.pop(
        (int(request.form["code"]), request.form["vcode"], request.form["email"]), None
    )
    if not lc:
        return render_template(
            "auth/logincode.html",
            email=request.form["email"],
            vcode=request.form["vcode"],
            status="That code is incorrect or has expired",
            gota=request.form.get("gota"),
        )
    if lc[1] < datetime.now():
        return render_template(
            "auth/logincode.html",
            email=request.form["email"],
            vcode=request.form["vcode"],
            status="That code is incorrect or has expired",
            gota=request.form.get("gota"),
        )
    user = User.query.get(lc[0])
    if request.form.get("gota"):
        gota_path = decode_jwt(request.form.get("gota"))["rt"]
        if gota_path.startswith("/"):
            rs = redirect(gota_path)
        else:
            rs = redirect("/dashboard")
    else:
        rs = redirect("/dashboard")
    rs.set_cookie(
        "abridgetoken",
        user.create_token().token,
        httponly=True,
        samesite="Lax",
        secure=True,
        max_age=2419200,
    )
    return rs


@app.route("/register")
def register_redir():
    return redirect("/login")


@app.route("/register", methods=["POST"])
@limiter.limit("2 per 2 seconds")
@limiter.limit("10 per minute")
@limiter.limit("60 per hour")
def register_post():
    _cleanup()
    if request.user:
        return redirect("/dashboard")
    scode = register_list.get(request.form["email"])
    if not scode:
        return redirect("/login")
    if scode[1] < datetime.now():
        logger.debug(
            "[login] Removing expired register code for %s", request.form["email"]
        )
        register_list.pop(request.form["email"], None)
        return redirect("/login")
    if scode[0] != int(request.form["code"]):
        return render_template(
            "auth/requestcode.html",
            email=request.form["email"],
            status="Incorrect code",
            gota=request.form.get("gota"),
        )
    luser = User.query.filter_by(email=request.form["email"]).first()
    if luser:
        return "An account was already made with this email!"
    return render_template(
        "auth/finalsetup.html",
        email=request.form["email"],
        code=scode[0],
        gota=request.form.get("gota"),
    )


@app.route("/finalregister", methods=["POST"])
@limiter.limit("2 per 2 seconds")
@limiter.limit("15 per minute")
@limiter.limit("30 per hour")
def register_finalpost():
    _cleanup()
    if request.user:
        return redirect("/dashboard")
    logger.debug("[login] Removing register code for %s", request.form["email"])
    scode = register_list.pop(request.form["email"], None)
    if not scode:
        return redirect("/login")
    if scode[1] < datetime.now():
        logger.debug(
            "[login] %s attempted making an account with an expired code: %s",
            request.form["email"],
            str(scode[1]),
        )
        return redirect("/login")
    if scode[0] != int(request.form["code"]):
        logger.debug(
            "[login] %s attempted making an account with an invalid code: %s",
            request.form["email"],
            str(scode[0]),
        )
        return redirect("/login")
    logger.debug("[login] Creating account for %s", request.form["email"])
    luser = User.query.filter_by(email=request.form["email"]).first()
    if luser:
        return "An account was already made with this email!"
    luser = User.query.filter_by(username=request.form["uname"]).first()
    if luser:
        register_list[request.form["email"]] = (
            scode[0],
            datetime.now() + timedelta(minutes=5),
        )
        return render_template(
            "auth/finalsetup.html",
            email=request.form["email"],
            code=scode[0],
            status=f"{request.form['uname']} is already taken",
            gota=request.form.get("gota"),
        )
    logger.debug("[auth] Creating user for %s", request.form["email"])
    user = User.create(
        email=request.form["email"],
        username=request.form["uname"],
        name=request.form["name"],
    )
    if request.form.get("gota"):
        gota_path = decode_jwt(request.form.get("gota"))["rt"]
        if gota_path.startswith("/"):
            rs = redirect(gota_path)
        else:
            rs = redirect("/dashboard")
    else:
        rs = redirect("/dashboard")
    rs.set_cookie(
        "abridgetoken",
        user.create_token().token,
        httponly=True,
        samesite="Lax",
        secure=True,
        max_age=2419200,
    )
    return rs


@app.route("/logout")
@require_user
def logout_route():
    _cleanup()
    request.token.delete()
    rs = redirect("/login")
    rs.set_cookie(
        "abridgetoken", "none", httponly=True, samesite="Lax", secure=False, max_age=0
    )
    return rs
