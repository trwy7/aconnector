import random
from flask import render_template, request, url_for, redirect
from app import app, logger, limiter
from app.db import User, db
from app.utilities import email

ev_list = {}
login_list = {}

@app.route("/login")
def login_page():
    return render_template("auth/login.html")

@app.route("/login", methods=['POST'])
@limiter.limit("1 per 2 seconds")
@limiter.limit("5 per minute")
@limiter.limit("20 per hour")
def login_post():
    luser = User.query.filter_by(email=request.form['email']).first()
    if luser:
        logger.debug("[login] Found user for %s: %s. Sending email...", request.form['email'], luser.username)
        lcode = random.randbytes(20).hex()
        login_list[lcode] = luser.id
        email.send(request.form['email'], f"Welcome back, {luser.username}!", f"Click this link to sign back in: {url_for("login_tokpost", token=lcode, _external=True)}")
        return render_template("auth/rlink.html", email=request.form['email'])
    else:
        # TODO: Email regex
        logger.debug("[login] Sending register email to %s", request.form['email'])
        if request.form['email'] not in ev_list:
            ev_list[request.form['email']] = random.randint(100000, 999999)
        email.send(request.form['email'], f"Your {app.config['NAME']} resgistration code is {str(ev_list[request.form['email']])}", f"Your code is: {str(ev_list[request.form['email']])}\nIf you did not request this email, you may discard it.")
        return render_template("auth/requestcode.html", email=request.form['email'])

@app.route("/login/<string:token>")
@limiter.limit("2 per 2 seconds")
def login_tokpost(token):
    uid = login_list.pop(token, None)
    if not uid:
        return redirect("/login")
    luser = User.query.get(uid)
    if not luser:
        return "uh oh", 500
    rs = redirect("/dashboard")
    rs.set_cookie(
        "abridgetoken",
        luser.create_token().token,
        httponly=True,
        samesite="Lax",
        secure=True,
        max_age=2419200
    )
    return rs

@app.route("/register")
def register_redir():
    return redirect("/login")

@app.route("/register", methods=['POST'])
@limiter.limit("2 per 2 seconds")
@limiter.limit("15 per minute")
@limiter.limit("30 per hour")
def register_post():
    scode = ev_list.get(request.form['email'])
    if not scode:
        return redirect("/login")
    if scode != int(request.form['code']):
        return render_template("auth/requestcode.html", email=request.form['email'], status="Incorrect code")
    luser = User.query.filter_by(email=request.form['email']).first()
    if luser:
        return "An account was already made with this email!"
    return render_template("auth/finalsetup.html", email=request.form['email'], code=scode)

@app.route("/finalregister", methods=['POST'])
@limiter.limit("2 per 2 seconds")
@limiter.limit("15 per minute")
@limiter.limit("30 per hour")
def register_finalpost():
    scode = ev_list.pop(request.form['email'], None)
    if not scode:
        return redirect("/login")
    if scode != int(request.form['code']):
        return render_template("auth/requestcode.html", email=request.form['email'], status="Incorrect code")
    luser = User.query.filter_by(email=request.form['email']).first()
    if luser:
        return "An account was already made with this email!"
    luser = User.query.filter_by(username=request.form['uname']).first()
    if luser:
        return render_template("auth/finalsetup.html", email=request.form['email'], code=scode, status=f"{request.form['uname']} is already taken")
    logger.debug("[auth] Creating user for %s", request.form['email'])
    user = User.create(email=request.form['email'], username=request.form['uname'], name=request.form['name'])
    rs = redirect("/dashboard")
    rs.set_cookie(
        "abridgetoken",
        user.create_token().token,
        httponly=True,
        samesite="Lax",
        secure=True,
        max_age=2419200
    )
    return rs

@app.route("/logout")
def logout_route():
    rs = redirect("/login")
    rs.set_cookie(
        "abridgetoken",
        "none",
        httponly=True,
        samesite="Lax",
        secure=False,
        max_age=0
    )
    return rs
