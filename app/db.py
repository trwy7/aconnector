from . import app
import uuid
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    level = db.Column(db.Integer, default=1)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(80), unique=False, nullable=False)
    firstname = db.Column(db.String(80), unique=False, nullable=False)
    lastname = db.Column(db.String(80), unique=False, nullable=False)
    disabled = db.Column(db.Boolean, nullable=False, default=False)

class Token(db.Model):
    token = db.Column(db.String(60), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='tokens')
    type = db.Column(db.String(5), nullable=False)
    expiry = db.Column(db.DateTime, nullable=False)

class Application(db.Model):
    owner_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    owner = db.relationship('User', backref='apps')
    name = db.Column(db.String(80), unique=False, nullable=False)
    client_id = db.Column(db.String(20), primary_key=True)
    client_secret = db.Column(db.String(80))
    redirect_url = db.Column(db.String(200))
    launch_url = db.Column(db.String(200))
    custom_attrs = db.Column(db.JSON)

with app.app_context():
    db.create_all()