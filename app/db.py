from . import app, logger
import re
import uuid
import random
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy(app)

user_app_association = db.Table(
    "user_app_link",
    db.Model.metadata,
    db.Column("user_id", db.ForeignKey('user.id', ondelete="CASCADE"), primary_key=True),
    db.Column("app_id", db.ForeignKey('app.client_id', ondelete="CASCADE"), primary_key=True)
)

username_regex = re.compile(r"[a-z0-9\-]{3,20}")
name_regex = re.compile(r"[A-Za-z ]{3,40}")
appname_regex = re.compile(r"[A-Za-z ]{3,80}")

class User(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    level = db.Column(db.Integer, default=0) # 0=user, 3=superadmin
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(40), nullable=False)
    apps = db.relationship('App', back_populates='owner', cascade="all, delete-orphan")
    tokens = db.relationship('Token', back_populates='user', cascade="all, delete-orphan")
    disabled = db.Column(db.Boolean, nullable=False, default=False)
    disable_app_create = db.Column(db.Boolean, nullable=False, default=False)
    allowed_apps = db.Column(db.Text, nullable=True, default=None)
    app_auths = db.relationship("App", secondary=user_app_association, back_populates="user_auths")
    @staticmethod
    def create(email: str, username: str, name: str, disabled: bool=False):
        if not re.fullmatch(username_regex, username):
            logger.debug("[db] rejecting invalid username")
            return False # Should just error the bad request
        logger.debug("[db] creating user %s", username)
        if not re.fullmatch(name_regex, name):
            logger.debug("[db] name for %s failed verification", username)
            return False # Should just error the bad request
        usr = User(
            email=email,
            username=username,
            name=name,
            level=0 if email != app.config['OWNER_EMAIL'] else 3,
            disabled=disabled,
            disable_app_create=app.config['LOCK_NEW_USER_APP_CREATE']
        )
        db.session.add(usr)
        db.session.commit()
        return usr
    def create_token(self):
        logger.debug("[db] creating token for %s", self.username)
        usr = Token(user=self)
        db.session.add(usr)
        db.session.commit()
        return usr
    def edit(self, name: str=None, email: str=None, disable: bool=None, disable_apps: bool=None, allowed_apps: str|None=...):
        logger.debug("[db] editing details for %s (%s): %s %s %s %s", self.name, self.username, name, email, disable, disable_apps)
        if name:
            if not re.fullmatch(name_regex, name):
                logger.debug("[db] new name for %s failed verification", self.username)
                return False # Should just error the bad request
            self.name = name
        if email:
            self.email = email
        if disable is not None:
            self.disabled = disable
        if disable_apps is not None:
            self.disable_app_create = disable_apps
        if allowed_apps != ...:
            self.allowed_apps = allowed_apps
        db.session.commit()
        return self
    def delete(self):
        db.session.delete(self)
        db.session.commit()

class Token(db.Model):
    token = db.Column(db.String(60), primary_key=True, default=lambda: random.randbytes(30).hex())
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', back_populates='tokens')
    expiry = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now() + timedelta(weeks=6))
    def delete(self):
        db.session.delete(self)
        db.session.commit()

class App(db.Model):
    owner_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    owner = db.relationship('User', back_populates='apps')
    name = db.Column(db.String(80), unique=False, nullable=False)
    client_id = db.Column(db.String(20), primary_key=True, default=lambda: random.randbytes(10).hex())
    client_secret = db.Column(db.String(80), default=lambda: random.randbytes(40).hex())
    redirect_url = db.Column(db.String(200), default="https://example.com/oidc/redirect")
    launch_url = db.Column(db.String(200), default="https://example.com/login/oidc")
    user_auths = db.relationship("User", secondary=user_app_association, back_populates="app_auths")
    @staticmethod
    def create(owner: User, name: str):
        logger.debug("[db] creating app for %s", owner.username)
        if not re.fullmatch(appname_regex, name):
            logger.debug("[db] app for %s failed name verification", owner.username)
            return False # Should just error the bad request
        capp = App(
            owner=owner,
            name=name
        )
        db.session.add(capp)
        db.session.commit()
        return capp
    def reroll_secret(self):
        logger.debug("[db] rerolling secret for %s (%s)", self.name, self.client_id)
        self.client_secret = random.randbytes(40).hex()
        db.session.commit()
        return self
    def edit(self, name: str=None, redirect_url: str=None, launch_url: str=None):
        logger.debug("[db] editing details for %s (%s)", self.name, self.client_id)
        if name:
            self.name = name
        if redirect_url:
            self.redirect_url = redirect_url
        if launch_url:
            self.launch_url = launch_url
        db.session.commit()
        return self
    def delete(self):
        db.session.delete(self)
        db.session.commit()

with app.app_context():
    db.create_all()