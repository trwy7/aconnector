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
    # TODO: Email regex
    luser = User.query.filter_by(email=request.form['email']).first()
    if luser:
        logger.debug("[login] Found user for %s: %s. Sending email...", request.form['email'], luser.username)
        lcode = random.randbytes(20).hex()
        login_list[lcode] = luser.id
        email.send(request.form['email'], f"Welcome back, {luser.username}!", f"Click this link to sign back in: {url_for("lastlogin", code=lcode)}")
        return render_template("auth/rlink.html", email=request.form['email'])
    else:
        logger.debug("[login] Sending register email to %s", request.form['email'])
        if request.form['email'] not in ev_list:
            ev_list[request.form['email']] = random.randint(100000, 999999)
        email.send(request.form['email'], f"Your {app.config['NAME']} resgistration code is {str(ev_list[request.form['email']])}", f"Your code is: {str(ev_list[request.form['email']])}\nIf you did not request this email, you may discard it.")
        return render_template("auth/requestcode.html", email=request.form['email'])

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
    scode = ev_list.get(request.form['email'])
    if not scode:
        return redirect("/login")
    if scode != int(request.form['code']):
        return render_template("auth/requestcode.html", email=request.form['email'], status="Incorrect code")
    luser = User.query.filter_by(email=request.form['email']).first()
    if luser:
        return "An account was already made with this email!"
    
    return render_template("auth/finalsetup.html", email=request.form['email'], code=scode, status="This name is already taken")