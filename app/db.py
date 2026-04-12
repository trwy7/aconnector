from . import app, logger
import uuid
import random
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy(app)

user_app_association = db.Table(
    "user_app_link",
    db.Model.metadata,
    db.Column("user_id", db.ForeignKey('user.id'), primary_key=True),
    db.Column("app_id", db.ForeignKey('app.client_id'), primary_key=True)
)

class User(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    level = db.Column(db.Integer, default=0) # 0=user, 3=superadmin
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(40), nullable=False)
    disabled = db.Column(db.Boolean, nullable=False, default=False)
    app_auths = db.relationship("App", secondary=user_app_association, back_populates="user_auths")
    @staticmethod
    def create(email: str, username: str, name: str):
        logger.debug("[db] creating user %s", username)
        usr = User(
            email=email,
            username=username,
            name=name,
            level=0 if email != app.config['OWNER_EMAIL'] else 3
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

class Token(db.Model):
    token = db.Column(db.String(60), primary_key=True, default=lambda: random.randbytes(30).hex())
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='tokens')
    expiry = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now() + timedelta(weeks=6))

class App(db.Model):
    owner_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    owner = db.relationship('User', backref='apps')
    name = db.Column(db.String(80), unique=False, nullable=False)
    client_id = db.Column(db.String(20), primary_key=True, default=lambda: random.randbytes(10).hex())
    client_secret = db.Column(db.String(80), default=lambda: random.randbytes(40).hex())
    redirect_url = db.Column(db.String(200), default="https://example.com/oidc/redirect")
    launch_url = db.Column(db.String(200), default="https://example.com/login/oidc")
    scopes = db.Column(db.Text, default="username,email")
    custom_attrs = db.Column(db.JSON, default=lambda: {})
    user_auths = db.relationship("User", secondary=user_app_association, back_populates="app_auths")
    @staticmethod
    def create(owner: User, name: str):
        logger.debug("[db] creating app for %s", owner.username)
        capp = App(
            owner=owner,
            name=name
        )
        db.session.add(capp)
        db.session.commit()
        return capp

with app.app_context():
    db.create_all()