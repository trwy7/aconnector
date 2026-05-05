import random
import re
import uuid
from datetime import datetime, timedelta
from types import EllipsisType

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.associationproxy import association_proxy

from . import app, logger

db = SQLAlchemy(app)

username_regex = re.compile(r"[a-z0-9\-]{3,20}")
name_regex = re.compile(r"[A-Za-z ]{3,40}")
appname_regex = re.compile(r"[A-Za-z ]{3,80}")


class UserAppLink(db.Model):
    __tablename__ = "user_app_link"
    
    user_id = Column(ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    app_id = Column(ForeignKey("app.client_id", ondelete="CASCADE"), primary_key=True)

    scopes = Column(db.String(500), nullable=False) 
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    user = db.relationship("User", back_populates="app_links")
    app = db.relationship("App", back_populates="user_links")
    def revoke(self):
        logger.info(
            "[db] Deleting userapplink for %s to %s", self.user.username, self.app.client_id
        )
        db.session.delete(self)
        db.session.commit()
    def setscopes(self, scopes: set):
        logger.debug("[db] Changing scopes for user %s for app %s: %s", self.user.username, self.app.client_id, str(scopes))
        self.scopes = " ".join(scopes)
        db.session.commit()

class User(db.Model):
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    level: Mapped[int] = mapped_column(Integer, default=0)  # 0=user, 3=superadmin
    username: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    apps: Mapped[list["App"]] = relationship(
        "App", back_populates="owner", cascade="all, delete-orphan"
    )
    tokens: Mapped[list["Token"]] = relationship(
        "Token", back_populates="user", cascade="all, delete-orphan"
    )
    disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    disable_app_create: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    allowed_apps: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    app_links: Mapped[list["UserAppLink"]] = relationship("UserAppLink", back_populates="user", cascade="all, delete-orphan")

    @staticmethod
    def create(email: str, username: str, name: str, disabled: bool = False):
        if not re.fullmatch(username_regex, username):
            logger.debug("[db] rejecting invalid username")
            return False  # Should just error the bad request
        logger.debug("[db] creating user %s", username)
        if not re.fullmatch(name_regex, name):
            logger.debug("[db] name for %s failed verification", username)
            return False  # Should just error the bad request
        usr = User(
            email=email,  # pyright: ignore [reportCallIssue]
            username=username,  # pyright: ignore [reportCallIssue]
            name=name,  # pyright: ignore [reportCallIssue]
            level=0 if email != app.config["OWNER_EMAIL"] else 3,  # pyright: ignore [reportCallIssue]
            disabled=disabled,  # pyright: ignore [reportCallIssue]
            disable_app_create=app.config["LOCK_NEW_USER_APP_CREATE"],  # pyright: ignore [reportCallIssue]
        )
        db.session.add(usr)
        db.session.commit()
        return usr

    def create_token(self):
        logger.debug("[db] creating token for %s", self.username)
        usr = Token(user=self)  # pyright: ignore [reportCallIssue]
        db.session.add(usr)
        db.session.commit()
        return usr

    def edit(
        self,
        name: str | None = None,
        email: str | None = None,
        disable: bool | None = None,
        disable_apps: bool | None = None,
        allowed_apps: str | None | EllipsisType = ...,
    ):
        logger.debug(
            "[db] editing details for %s (%s): %s %s %s %s",
            self.name,
            self.username,
            name,
            email,
            disable,
            disable_apps,
        )
        if name:
            if not re.fullmatch(name_regex, name):
                logger.debug("[db] new name for %s failed verification", self.username)
                return False  # Should just error the bad request
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

    def authorize(self, app: App, scopes: set):
        logger.debug("[db] Authorizing %s for %s: %s", self.username, app.client_id, str(scopes))
        nauth = UserAppLink(
            user=self,
            app=app,
            scopes=" ".join(scopes)
        )
        db.session.add(nauth)
        db.session.commit()
        return nauth

    def delete(self):
        logger.info(
            "[db] Deleting user %s (%s) with ID %s", self.name, self.email, self.id
        )
        db.session.delete(self)
        db.session.commit()


class Token(db.Model):
    token: Mapped[str] = mapped_column(
        String(60), primary_key=True, default=lambda: random.randbytes(30).hex()
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.id"), nullable=False
    )
    user: Mapped["User"] = relationship("User", back_populates="tokens")
    expiry: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now() + timedelta(weeks=6)
    )

    def delete(self):
        logger.info("[db] Deleting token for %s", self.user.username)
        db.session.delete(self)
        db.session.commit()


class App(db.Model):
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.id"), nullable=False
    )
    owner: Mapped["User"] = relationship("User", back_populates="apps")
    name: Mapped[str] = mapped_column(String(80), unique=False, nullable=False)
    client_id: Mapped[str] = mapped_column(
        String(20), primary_key=True, default=lambda: random.randbytes(10).hex()
    )
    client_secret: Mapped[str] = mapped_column(
        String(80), default=lambda: random.randbytes(40).hex()
    )
    redirect_url: Mapped[str] = mapped_column(
        String(200), default="https://example.com/oidc/redirect"
    )
    launch_url: Mapped[str] = mapped_column(
        String(200), default="https://example.com/login/oidc"
    )
    user_links: Mapped[list["UserAppLink"]] = relationship("UserAppLink", back_populates="app", cascade="all, delete-orphan")
    users = association_proxy("user_links", "user")

    @staticmethod
    def create(owner: User, name: str):
        logger.debug("[db] creating app for %s", owner.username)
        if not re.fullmatch(appname_regex, name):
            logger.debug("[db] app for %s failed name verification", owner.username)
            return False  # Should just error the bad request
        capp = App(owner=owner, name=name)  # pyright: ignore [reportCallIssue]
        db.session.add(capp)
        db.session.commit()
        return capp

    def reroll_secret(self):
        logger.debug(
            "[db] rerolling client secret for %s (%s)", self.name, self.client_id
        )
        self.client_secret = random.randbytes(40).hex()
        db.session.commit()
        return self

    def edit(
        self,
        name: str | None = None,
        redirect_url: str | None = None,
        launch_url: str | None = None,
    ):
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
        logger.info("[db] Deleting app %s (%s)", self.name, self.client_id)
        db.session.delete(self)
        db.session.commit()


with app.app_context():
    db.create_all()
