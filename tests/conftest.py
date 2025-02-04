# -*- coding: utf-8 -*-
"""
    conftest
    ~~~~~~~~

    Test fixtures and what not

    :copyright: (c) 2017 by CERN.
    :license: MIT, see LICENSE for more details.
"""

import os
import tempfile
import time
from datetime import datetime

try:
    from urlparse import urlsplit
except ImportError:  # pragma: no cover
    from urllib.parse import urlsplit

import pytest
from flask import Flask, render_template
from flask import jsonify
from flask import request as flask_request
from flask.json import JSONEncoder
from flask_babelex import Babel
from flask_mail import Mail
from utils import Response, populate_data

from flask_security import (
    MongoEngineUserDatastore,
    PeeweeUserDatastore,
    PonyUserDatastore,
    RoleMixin,
    Security,
    SQLAlchemySessionUserDatastore,
    SQLAlchemyUserDatastore,
    UserMixin,
    auth_required,
    auth_token_required,
    http_auth_required,
    login_required,
    roles_accepted,
    roles_required,
    permissions_accepted,
    permissions_required,
)


@pytest.fixture()
def app(request):
    app = Flask(__name__)
    app.response_class = Response
    app.debug = True
    app.config["SECRET_KEY"] = "secret"
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = False
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SECURITY_TWO_FACTOR_SECRET"] = {
        "1": "TjQ9Qa31VOrfEzuPy4VHQWPCTmRzCnFzMKLxXYiZu9B"
    }
    app.config["SECURITY_TWO_FACTOR_SMS_SERVICE"] = "test"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["SECURITY_PASSWORD_SALT"] = "salty"
    # Make this plaintext for most tests - reduces unit test time by 50%
    app.config["SECURITY_PASSWORD_HASH"] = "plaintext"
    # Make this hex_md5 for token tests
    app.config["SECURITY_HASHING_SCHEMES"] = ["hex_md5"]
    app.config["SECURITY_DEPRECATED_HASHING_SCHEMES"] = []

    for opt in [
        "changeable",
        "recoverable",
        "registerable",
        "trackable",
        "passwordless",
        "confirmable",
        "two_factor",
    ]:
        app.config["SECURITY_" + opt.upper()] = opt in request.keywords

    pytest_major = int(pytest.__version__.split(".")[0])
    if pytest_major >= 4:
        marker_getter = request.node.get_closest_marker
    else:
        marker_getter = request.keywords.get
    settings = marker_getter("settings")
    babel = marker_getter("babel")
    if settings is not None:
        for key, value in settings.kwargs.items():
            app.config["SECURITY_" + key.upper()] = value

    mail = Mail(app)
    if babel is None or babel.args[0]:
        Babel(app)
    app.json_encoder = JSONEncoder
    app.mail = mail

    @app.route("/")
    def index():
        return render_template("index.html", content="Home Page")

    @app.route("/profile")
    @login_required
    def profile():
        return render_template("index.html", content="Profile Page")

    @app.route("/post_login")
    @login_required
    def post_login():
        return render_template("index.html", content="Post Login")

    @app.route("/http")
    @http_auth_required
    def http():
        return "HTTP Authentication"

    @app.route("/http_custom_realm")
    @http_auth_required("My Realm")
    def http_custom_realm():
        return render_template("index.html", content="HTTP Authentication")

    @app.route("/token", methods=["GET", "POST"])
    @auth_token_required
    def token():
        return render_template("index.html", content="Token Authentication")

    @app.route("/multi_auth")
    @auth_required("session", "token", "basic")
    def multi_auth():
        return render_template("index.html", content="Session, Token, Basic auth")

    @app.route("/post_logout")
    def post_logout():
        return render_template("index.html", content="Post Logout")

    @app.route("/post_register")
    def post_register():
        return render_template("index.html", content="Post Register")

    @app.route("/post_confirm")
    def post_confirm():
        return render_template("index.html", content="Post Confirm")

    @app.route("/admin")
    @roles_required("admin")
    def admin():
        return render_template("index.html", content="Admin Page")

    @app.route("/admin_and_editor")
    @roles_required("admin", "editor")
    def admin_and_editor():
        return render_template("index.html", content="Admin and Editor Page")

    @app.route("/admin_or_editor")
    @roles_accepted("admin", "editor")
    def admin_or_editor():
        return render_template("index.html", content="Admin or Editor Page")

    @app.route("/simple")
    @roles_accepted("simple")
    def simple():
        return render_template("index.html", content="SimplePage")

    @app.route("/admin_perm")
    @permissions_accepted("full-write", "super")
    def admin_perm():
        return render_template(
            "index.html", content="Admin Page with full-write or super"
        )

    @app.route("/admin_perm_required")
    @permissions_required("full-write", "super")
    def admin_perm_required():
        return render_template("index.html", content="Admin Page required")

    @app.route("/unauthorized")
    def unauthorized():
        return render_template("unauthorized.html")

    @app.route("/page1")
    def page_1():
        return "Page 1"

    @app.route("/json", methods=["GET", "POST"])
    def echo_json():
        return jsonify(flask_request.get_json())

    @app.route("/unauthz", methods=["GET", "POST"])
    def unauthz():
        return render_template("index.html", content="Unauthorized")

    return app


@pytest.fixture()
def mongoengine_datastore(request, app, tmpdir, realdburl):
    return mongoengine_setup(request, app, tmpdir, realdburl)


def mongoengine_setup(request, app, tmpdir, realdburl):
    from flask_mongoengine import MongoEngine

    db_name = "flask_security_test_%s" % str(time.time()).replace(".", "_")
    app.config["MONGODB_SETTINGS"] = {
        "db": db_name,
        "host": "mongomock://localhost",
        "port": 27017,
        "alias": db_name,
    }

    db = MongoEngine(app)

    class Role(db.Document, RoleMixin):
        name = db.StringField(required=True, unique=True, max_length=80)
        description = db.StringField(max_length=255)
        meta = {"db_alias": db_name}

    class User(db.Document, UserMixin):
        email = db.StringField(unique=True, max_length=255)
        username = db.StringField(max_length=255)
        password = db.StringField(required=False, max_length=255)
        security_number = db.IntField(unique=True)
        last_login_at = db.DateTimeField()
        current_login_at = db.DateTimeField()
        tf_primary_method = db.StringField(max_length=255)
        tf_totp_secret = db.StringField(max_length=255)
        tf_phone_number = db.StringField(max_length=255)
        last_login_ip = db.StringField(max_length=100)
        current_login_ip = db.StringField(max_length=100)
        login_count = db.IntField()
        active = db.BooleanField(default=True)
        confirmed_at = db.DateTimeField()
        roles = db.ListField(db.ReferenceField(Role), default=[])
        meta = {"db_alias": db_name}

    def tear_down():
        with app.app_context():
            User.drop_collection()
            Role.drop_collection()
            db.connection.drop_database(db_name)

    request.addfinalizer(tear_down)

    return MongoEngineUserDatastore(db, User, Role)


@pytest.fixture()
def sqlalchemy_datastore(request, app, tmpdir, realdburl):
    return sqlalchemy_setup(request, app, tmpdir, realdburl)


def sqlalchemy_setup(request, app, tmpdir, realdburl):
    from flask_sqlalchemy import SQLAlchemy
    from flask_security.models import fsqla

    if realdburl:
        db_url, db_info = _setup_realdb(realdburl)
        app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    else:
        f, path = tempfile.mkstemp(
            prefix="flask-security-test-db", suffix=".db", dir=str(tmpdir)
        )
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + path

    db = SQLAlchemy(app)

    fsqla.FsModels.set_db_info(db)

    class Role(db.Model, fsqla.FsRoleMixin):
        pass

    class User(db.Model, fsqla.FsUserMixin):
        security_number = db.Column(db.Integer, unique=True)
        # For testing allow null passwords.
        password = db.Column(db.String(255), nullable=True)

        def get_security_payload(self):
            # Make sure we still properly hook up to flask JSONEncoder
            return {"id": str(self.id), "last_update": self.update_datetime}

    with app.app_context():
        db.create_all()

    def tear_down():
        if realdburl:
            db.drop_all()
            _teardown_realdb(db_info)
        else:
            os.close(f)
            os.remove(path)

    request.addfinalizer(tear_down)

    return SQLAlchemyUserDatastore(db, User, Role)


@pytest.fixture()
def sqlalchemy_session_datastore(request, app, tmpdir, realdburl):
    return sqlalchemy_session_setup(request, app, tmpdir, realdburl)


def sqlalchemy_session_setup(request, app, tmpdir, realdburl):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import scoped_session, sessionmaker, relationship, backref
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy import Boolean, DateTime, Column, Integer, String, ForeignKey

    f, path = tempfile.mkstemp(
        prefix="flask-security-test-db", suffix=".db", dir=str(tmpdir)
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + path

    engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"], convert_unicode=True)
    db_session = scoped_session(
        sessionmaker(autocommit=False, autoflush=False, bind=engine)
    )
    Base = declarative_base()
    Base.query = db_session.query_property()

    class RolesUsers(Base):
        __tablename__ = "roles_users"
        id = Column(Integer(), primary_key=True)
        user_id = Column("user_id", Integer(), ForeignKey("user.id"))
        role_id = Column("role_id", Integer(), ForeignKey("role.id"))

    class Role(Base, RoleMixin):
        __tablename__ = "role"
        id = Column(Integer(), primary_key=True)
        name = Column(String(80), unique=True)
        description = Column(String(255))

    class User(Base, UserMixin):
        __tablename__ = "user"
        id = Column(Integer, primary_key=True)
        email = Column(String(255), unique=True)
        username = Column(String(255))
        password = Column(String(255))
        security_number = Column(Integer, unique=True)
        last_login_at = Column(DateTime())
        current_login_at = Column(DateTime())
        tf_primary_method = Column(String(255), nullable=True)
        tf_totp_secret = Column(String(255), nullable=True)
        tf_phone_number = Column(String(255), nullable=True)
        last_login_ip = Column(String(100))
        current_login_ip = Column(String(100))
        login_count = Column(Integer)
        active = Column(Boolean())
        confirmed_at = Column(DateTime())
        roles = relationship(
            "Role", secondary="roles_users", backref=backref("users", lazy="dynamic")
        )

    with app.app_context():
        Base.metadata.create_all(bind=engine)

    def tear_down():
        db_session.close()
        os.close(f)
        os.remove(path)

    request.addfinalizer(tear_down)

    return SQLAlchemySessionUserDatastore(db_session, User, Role)


@pytest.fixture()
def peewee_datastore(request, app, tmpdir, realdburl):
    return peewee_setup(request, app, tmpdir, realdburl)


def peewee_setup(request, app, tmpdir, realdburl):
    from peewee import (
        TextField,
        DateTimeField,
        IntegerField,
        BooleanField,
        ForeignKeyField,
        CharField,
    )
    from flask_peewee.db import Database

    if realdburl:
        engine_mapper = {
            "postgres": "peewee.PostgresqlDatabase",
            "mysql": "peewee.MySQLDatabase",
        }
        db_url, db_info = _setup_realdb(realdburl)
        pieces = urlsplit(db_url)
        db_config = {
            "name": pieces.path[1:],
            "engine": engine_mapper[pieces.scheme.split("+")[0]],
            "user": pieces.username,
            "passwd": pieces.password,
            "host": pieces.hostname,
        }
    else:
        f, path = tempfile.mkstemp(
            prefix="flask-security-test-db", suffix=".db", dir=str(tmpdir)
        )
        db_config = {"name": path, "engine": "peewee.SqliteDatabase"}

    app.config["DATABASE"] = db_config

    db = Database(app)

    class Role(db.Model, RoleMixin):
        name = CharField(unique=True, max_length=80)
        description = TextField(null=True)

    class User(db.Model, UserMixin):
        email = TextField()
        username = TextField()
        security_number = IntegerField(null=True)
        password = TextField(null=True)
        last_login_at = DateTimeField(null=True)
        current_login_at = DateTimeField(null=True)
        tf_primary_method = TextField(null=True)
        tf_totp_secret = TextField(null=True)
        tf_phone_number = TextField(null=True)
        last_login_ip = TextField(null=True)
        current_login_ip = TextField(null=True)
        login_count = IntegerField(null=True)
        active = BooleanField(default=True)
        confirmed_at = DateTimeField(null=True)

    class UserRoles(db.Model):
        """ Peewee does not have built-in many-to-many support, so we have to
        create this mapping class to link users to roles."""

        user = ForeignKeyField(User, backref="roles")
        role = ForeignKeyField(Role, backref="users")
        name = property(lambda self: self.role.name)
        description = property(lambda self: self.role.description)

    with app.app_context():
        for Model in (Role, User, UserRoles):
            Model.drop_table()
            Model.create_table()

    def tear_down():
        if realdburl:
            db.close_db(None)
            _teardown_realdb(db_info)
        else:
            db.close_db(None)
            os.close(f)
            os.remove(path)

    request.addfinalizer(tear_down)

    return PeeweeUserDatastore(db, User, Role, UserRoles)


@pytest.fixture()
def pony_datastore(request, app, tmpdir, realdburl):
    return pony_setup(request, app, tmpdir, realdburl)


def pony_setup(request, app, tmpdir, realdburl):

    from pony.orm import Database, Optional, Required, Set
    from pony.orm.core import SetInstance

    SetInstance.append = SetInstance.add
    db = Database()

    class Role(db.Entity):
        name = Required(str, unique=True)
        description = Optional(str, nullable=True)
        users = Set(lambda: User)

    class User(db.Entity):
        email = Required(str)
        username = Optional(str)
        security_number = Optional(int)
        password = Optional(str, nullable=True)
        last_login_at = Optional(datetime)
        current_login_at = Optional(datetime)
        tf_primary_method = Optional(str, nullable=True)
        tf_totp_secret = Optional(str, nullable=True)
        tf_phone_number = Optional(str, nullable=True)
        last_login_ip = Optional(str)
        current_login_ip = Optional(str)
        login_count = Optional(int)
        active = Required(bool, default=True)
        confirmed_at = Optional(datetime)
        roles = Set(lambda: Role)

        def has_role(self, name):
            return name in {r.name for r in self.roles.copy()}

    if realdburl:
        db_url, db_info = _setup_realdb(realdburl)
        pieces = urlsplit(db_url)
        db.bind(
            provider=pieces.scheme.split("+")[0],
            user=pieces.username,
            password=pieces.password,
            host=pieces.hostname,
            database=pieces.path[1:],
        )
    else:
        app.config["DATABASE"] = {"name": ":memory:", "engine": "pony.SqliteDatabase"}
        db.bind("sqlite", ":memory:", create_db=True)

    db.generate_mapping(create_tables=True)

    def tear_down():
        if realdburl:
            _teardown_realdb(db_info)

    request.addfinalizer(tear_down)

    return PonyUserDatastore(db, User, Role)


@pytest.fixture()
def sqlalchemy_app(app, sqlalchemy_datastore):
    def create():
        app.security = Security(app, datastore=sqlalchemy_datastore)
        return app

    return create


@pytest.fixture()
def sqlalchemy_session_app(app, sqlalchemy_session_datastore):
    def create():
        app.security = Security(app, datastore=sqlalchemy_session_datastore)
        return app

    return create


@pytest.fixture()
def peewee_app(app, peewee_datastore):
    def create():
        app.security = Security(app, datastore=peewee_datastore)
        return app

    return create


@pytest.fixture()
def mongoengine_app(app, mongoengine_datastore):
    def create():
        app.security = Security(app, datastore=mongoengine_datastore)
        return app

    return create


@pytest.fixture()
def pony_app(app, pony_datastore):
    def create():
        app.security = Security(app, datastore=pony_datastore)
        return app

    return create


@pytest.fixture()
def client(request, sqlalchemy_app):
    app = sqlalchemy_app()
    populate_data(app)
    return app.test_client()


@pytest.fixture()
def client_nc(request, sqlalchemy_app):
    # useful for testing token auth.
    # No Cookies for You!
    app = sqlalchemy_app()
    populate_data(app)
    return app.test_client(use_cookies=False)


@pytest.yield_fixture()
def in_app_context(request, sqlalchemy_app):
    app = sqlalchemy_app()
    with app.app_context():
        yield app


@pytest.fixture()
def get_message(app):
    def fn(key, **kwargs):
        rv = app.config["SECURITY_MSG_" + key][0] % kwargs
        return rv.encode("utf-8")

    return fn


@pytest.fixture(
    params=["sqlalchemy", "sqlalchemy-session", "mongoengine", "peewee", "pony"]
)
def datastore(request, app, tmpdir, realdburl):
    if request.param == "sqlalchemy":
        rv = sqlalchemy_setup(request, app, tmpdir, realdburl)
    elif request.param == "sqlalchemy-session":
        rv = sqlalchemy_session_setup(request, app, tmpdir, realdburl)
    elif request.param == "mongoengine":
        rv = mongoengine_setup(request, app, tmpdir, realdburl)
    elif request.param == "peewee":
        rv = peewee_setup(request, app, tmpdir, realdburl)
    elif request.param == "pony":
        rv = pony_setup(request, app, tmpdir, realdburl)
    return rv


@pytest.fixture()
def script_info(app, datastore):
    try:
        from flask.cli import ScriptInfo
    except ImportError:
        from flask_cli import ScriptInfo

    def create_app(info):
        app.config.update(
            **{"SECURITY_USER_IDENTITY_ATTRIBUTES": ("email", "username")}
        )
        app.security = Security(app, datastore=datastore)
        return app

    return ScriptInfo(create_app=create_app)


def pytest_addoption(parser):
    parser.addoption(
        "--realdburl",
        action="store",
        default=None,
        help="""Set url for using real database for testing.
        For postgres: 'postgres://user:password@host/')""",
    )


@pytest.fixture(scope="session")
def realdburl(request):
    """
    Support running datastore tests against a real DB.
    For example psycopg2 is very strict about types in queries
    compared to sqlite
    To use postgres you need to of course run a postgres instance on localhost
    then pass in an extra arg to pytest:
    --realdburl postgres://<user>@localhost/
    For mysql same - just download and add a root password.
    --realdburl "mysql+pymysql://root:<password>@localhost/"
    """
    return request.config.option.realdburl


def _setup_realdb(realdburl):
    """
    Called when we want to run unit tests against a real DB.
    This is useful since different DB drivers are pickier about queries etc
    (such as pyscopg2 and postgres)
    """
    from sqlalchemy import create_engine
    from sqlalchemy_utils import database_exists, create_database

    db_name = "flask_security_test_%s" % str(time.time()).replace(".", "_")

    db_uri = realdburl + db_name
    engine = create_engine(db_uri)
    if not database_exists(engine.url):
        create_database(engine.url)
    print("Setting up real DB at " + db_uri)
    return db_uri, {"engine": engine}


def _teardown_realdb(db_info):
    from sqlalchemy_utils import drop_database

    drop_database(db_info["engine"].url)
