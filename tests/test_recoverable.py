# -*- coding: utf-8 -*-
"""
    test_recoverable
    ~~~~~~~~~~~~~~~~

    Recoverable functionality tests
"""

import json
import time

import pytest
from flask import Flask
from utils import authenticate, json_authenticate, json_logout, logout, verify_token

from flask_security.core import UserMixin
from flask_security.forms import LoginForm
from flask_security.signals import password_reset, reset_password_instructions_sent
from flask_security.utils import (
    capture_flashes,
    capture_reset_password_requests,
    string_types,
)

try:
    from urlparse import parse_qsl, urlsplit
except ImportError:  # pragma: no cover
    from urllib.parse import parse_qsl, urlsplit

pytestmark = pytest.mark.recoverable()


def test_recoverable_flag(app, client, get_message):
    recorded_resets = []
    recorded_instructions_sent = []

    @password_reset.connect_via(app)
    def on_password_reset(app, user):
        recorded_resets.append(user)

    @reset_password_instructions_sent.connect_via(app)
    def on_instructions_sent(app, user, token):
        assert isinstance(app, Flask)
        assert isinstance(user, UserMixin)
        assert isinstance(token, string_types)
        recorded_instructions_sent.append(user)

    # Test the reset view
    response = client.get("/reset")
    assert b"<h1>Send password reset instructions</h1>" in response.data

    # Test submitting email to reset password creates a token and sends email
    with capture_reset_password_requests() as requests:
        with app.mail.record_messages() as outbox:
            response = client.post(
                "/reset", data=dict(email="joe@lp.com"), follow_redirects=True
            )

    assert len(recorded_instructions_sent) == 1
    assert len(outbox) == 1
    assert response.status_code == 200
    assert get_message("PASSWORD_RESET_REQUEST", email="joe@lp.com") in response.data
    token = requests[0]["token"]

    # Test view for reset token
    response = client.get("/reset/" + token)
    assert b"<h1>Reset password</h1>" in response.data

    # Test submitting a new password but leave out confirm
    response = client.post(
        "/reset/" + token, data={"password": "newpassword"}, follow_redirects=True
    )
    assert get_message("PASSWORD_NOT_PROVIDED") in response.data
    assert len(recorded_resets) == 0

    # Test submitting a new password
    response = client.post(
        "/reset/" + token,
        data={"password": "newpassword", "password_confirm": "newpassword"},
        follow_redirects=True,
    )

    assert get_message("PASSWORD_RESET") in response.data
    assert len(recorded_resets) == 1

    logout(client)

    # Test logging in with the new password
    response = authenticate(client, "joe@lp.com", "newpassword", follow_redirects=True)
    assert b"Welcome joe@lp.com" in response.data

    logout(client)

    # Test invalid email
    response = client.post(
        "/reset", data=dict(email="bogus@lp.com"), follow_redirects=True
    )
    assert get_message("USER_DOES_NOT_EXIST") in response.data

    logout(client)

    # Test invalid token
    response = client.post(
        "/reset/bogus",
        data={"password": "newpassword", "password_confirm": "newpassword"},
        follow_redirects=True,
    )
    assert get_message("INVALID_RESET_PASSWORD_TOKEN") in response.data

    # Test mangled token
    token = (
        "WyIxNjQ2MzYiLCIxMzQ1YzBlZmVhM2VhZjYwODgwMDhhZGU2YzU0MzZjMiJd."
        "BZEw_Q.lQyo3npdPZtcJ_sNHVHP103syjM"
        "&url_id=fbb89a8328e58c181ea7d064c2987874bc54a23d"
    )
    response = client.post(
        "/reset/" + token,
        data={"password": "newpassword", "password_confirm": "newpassword"},
        follow_redirects=True,
    )
    assert get_message("INVALID_RESET_PASSWORD_TOKEN") in response.data


@pytest.mark.settings()
def test_recoverable_json(app, client, get_message):
    recorded_resets = []
    recorded_instructions_sent = []

    @password_reset.connect_via(app)
    def on_password_reset(app, user):
        recorded_resets.append(user)

    @reset_password_instructions_sent.connect_via(app)
    def on_instructions_sent(app, user, token):
        recorded_instructions_sent.append(user)

    with capture_flashes() as flashes:
        # Test reset password creates a token and sends email
        with capture_reset_password_requests() as requests:
            with app.mail.record_messages() as outbox:
                response = client.post(
                    "/reset",
                    data='{"email": "joe@lp.com"}',
                    headers={"Content-Type": "application/json"},
                )
                assert response.headers["Content-Type"] == "application/json"

        assert len(recorded_instructions_sent) == 1
        assert len(outbox) == 1
        assert response.status_code == 200
        token = requests[0]["token"]

        # Test invalid email
        response = client.post(
            "/reset",
            data='{"email": "whoknows@lp.com"}',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
        assert response.jdata["response"]["errors"]["email"][0].encode(
            "utf-8"
        ) == get_message("USER_DOES_NOT_EXIST")

        # Test submitting a new password but leave out 'confirm'
        response = client.post(
            "/reset/" + token,
            data='{"password": "newpassword"}',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
        assert response.jdata["response"]["errors"]["password_confirm"][0].encode(
            "utf-8"
        ) == get_message("PASSWORD_NOT_PROVIDED")

        # Test submitting a new password
        response = client.post(
            "/reset/" + token + "?include_auth_token",
            data='{"password": "newpassword",\
                                     "password_confirm": "newpassword"}',
            headers={"Content-Type": "application/json"},
        )
        assert all(
            k in response.jdata["response"]["user"]
            for k in ["id", "authentication_token"]
        )
        assert len(recorded_resets) == 1

        # reset automatically logs user in
        logout(client)

        # Test logging in with the new password
        response = client.post(
            "/login?include_auth_token",
            data='{"email": "joe@lp.com",\
                                     "password": "newpassword"}',
            headers={"Content-Type": "application/json"},
        )
        assert all(
            k in response.jdata["response"]["user"]
            for k in ["id", "authentication_token"]
        )

        logout(client)

        # Use token again - should fail since already have set new password.
        response = client.post(
            "/reset/" + token,
            data='{"password": "newpassword",\
                                     "password_confirm": "newpassword"}',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
        assert len(recorded_resets) == 1

        # Test invalid token
        response = client.post(
            "/reset/bogus",
            data='{"password": "newpassword",\
                                     "password_confirm": "newpassword"}',
            headers={"Content-Type": "application/json"},
        )
        assert response.jdata["response"]["errors"].encode("utf-8") == get_message(
            "INVALID_RESET_PASSWORD_TOKEN"
        )
    assert len(flashes) == 0


def test_login_form_description(sqlalchemy_app):
    app = sqlalchemy_app()
    with app.test_request_context("/login"):
        login_form = LoginForm()
        expected = '<a href="/reset">Forgot password?</a>'
        assert login_form.password.description == expected


@pytest.mark.settings(reset_password_within="1 milliseconds")
def test_expired_reset_token(client, get_message):
    with capture_reset_password_requests() as requests:
        client.post("/reset", data=dict(email="joe@lp.com"), follow_redirects=True)

    user = requests[0]["user"]
    token = requests[0]["token"]

    time.sleep(1)

    with capture_flashes() as flashes:
        msg = get_message(
            "PASSWORD_RESET_EXPIRED", within="1 milliseconds", email=user.email
        )

        # Test getting reset form with expired token
        response = client.get("/reset/" + token, follow_redirects=True)
        assert msg in response.data

        # Test trying to reset password with expired token
        response = client.post(
            "/reset/" + token,
            data={"password": "newpassword", "password_confirm": "newpassword"},
            follow_redirects=True,
        )

        assert msg in response.data
    assert len(flashes) == 2


def test_bad_reset_token(client, get_message):
    # Test invalid token - get form
    response = client.get("/reset/bogus", follow_redirects=True)
    assert get_message("INVALID_RESET_PASSWORD_TOKEN") in response.data

    # Test invalid token - reset password
    response = client.post(
        "/reset/bogus",
        data={"password": "newpassword", "password_confirm": "newpassword"},
        follow_redirects=True,
    )
    assert get_message("INVALID_RESET_PASSWORD_TOKEN") in response.data

    # Test mangled token
    token = (
        "WyIxNjQ2MzYiLCIxMzQ1YzBlZmVhM2VhZjYwODgwMDhhZGU2YzU0MzZjMiJd."
        "BZEw_Q.lQyo3npdPZtcJ_sNHVHP103syjM"
        "&url_id=fbb89a8328e58c181ea7d064c2987874bc54a23d"
    )
    response = client.post(
        "/reset/" + token,
        data={"password": "newpassword", "password_confirm": "newpassword"},
        follow_redirects=True,
    )
    assert get_message("INVALID_RESET_PASSWORD_TOKEN") in response.data


def test_reset_token_deleted_user(app, client, get_message, sqlalchemy_datastore):
    with capture_reset_password_requests() as requests:
        client.post("/reset", data=dict(email="gene@lp.com"), follow_redirects=True)

    token = requests[0]["token"]

    # Delete user
    with app.app_context():
        # load user (and role) to get into session so cascade delete works.
        user = app.security.datastore.find_user(email="gene@lp.com")
        sqlalchemy_datastore.delete(user)
        sqlalchemy_datastore.commit()

    response = client.post(
        "/reset/" + token,
        data={"password": "newpassword", "password_confirm": "newpassword"},
        follow_redirects=True,
    )

    msg = get_message("INVALID_RESET_PASSWORD_TOKEN")
    assert msg in response.data


def test_used_reset_token(client, get_message):
    with capture_reset_password_requests() as requests:
        client.post("/reset", data=dict(email="joe@lp.com"), follow_redirects=True)

    token = requests[0]["token"]

    # use the token
    response = client.post(
        "/reset/" + token,
        data={"password": "newpassword", "password_confirm": "newpassword"},
        follow_redirects=True,
    )

    assert get_message("PASSWORD_RESET") in response.data

    logout(client)

    # attempt to use it a second time
    response2 = client.post(
        "/reset/" + token,
        data={"password": "otherpassword", "password_confirm": "otherpassword"},
        follow_redirects=True,
    )

    msg = get_message("INVALID_RESET_PASSWORD_TOKEN")
    assert msg in response2.data


def test_reset_passwordless_user(client, get_message):
    with capture_reset_password_requests() as requests:
        client.post("/reset", data=dict(email="jess@lp.com"), follow_redirects=True)

    token = requests[0]["token"]

    # use the token
    response = client.post(
        "/reset/" + token,
        data={"password": "newpassword", "password_confirm": "newpassword"},
        follow_redirects=True,
    )

    assert get_message("PASSWORD_RESET") in response.data


@pytest.mark.settings(reset_url="/custom_reset")
def test_custom_reset_url(client):
    response = client.get("/custom_reset")
    assert response.status_code == 200


@pytest.mark.settings(
    reset_password_template="custom_security/reset_password.html",
    forgot_password_template="custom_security/forgot_password.html",
)
def test_custom_reset_templates(client):
    response = client.get("/reset")
    assert b"CUSTOM FORGOT PASSWORD" in response.data

    with capture_reset_password_requests() as requests:
        client.post("/reset", data=dict(email="joe@lp.com"), follow_redirects=True)
        token = requests[0]["token"]

    response = client.get("/reset/" + token)
    assert b"CUSTOM RESET PASSWORD" in response.data


@pytest.mark.settings(
    redirect_host="localhost:8081",
    redirect_behavior="spa",
    reset_view="/reset-redirect",
)
def test_spa_get(app, client):
    """
    Test 'single-page-application' style redirects
    This uses json only.
    """
    with capture_reset_password_requests() as requests:
        response = client.post(
            "/reset",
            data='{"email": "joe@lp.com"}',
            headers={"Content-Type": "application/json"},
        )
        assert response.headers["Content-Type"] == "application/json"
        assert "user" not in response.jdata["response"]
    token = requests[0]["token"]

    response = client.get("/reset/" + token)
    assert response.status_code == 302
    split = urlsplit(response.headers["Location"])
    assert "localhost:8081" == split.netloc
    assert "/reset-redirect" == split.path
    qparams = dict(parse_qsl(split.query))
    assert qparams["email"] == "joe@lp.com"
    assert qparams["token"] == token


@pytest.mark.settings(
    reset_password_within="1 milliseconds",
    redirect_host="localhost:8081",
    redirect_behavior="spa",
    reset_error_view="/reset-error",
)
def test_spa_get_bad_token(app, client, get_message):
    """ Test expired and invalid token"""
    with capture_flashes() as flashes:
        with capture_reset_password_requests() as requests:
            response = client.post(
                "/reset",
                data='{"email": "joe@lp.com"}',
                headers={"Content-Type": "application/json"},
            )
            assert response.headers["Content-Type"] == "application/json"
            assert "user" not in response.jdata["response"]
        token = requests[0]["token"]
        time.sleep(1)

        response = client.get("/reset/" + token)
        assert response.status_code == 302
        split = urlsplit(response.headers["Location"])
        assert "localhost:8081" == split.netloc
        assert "/reset-error" == split.path
        qparams = dict(parse_qsl(split.query))
        assert len(qparams) == 2
        assert all(k in qparams for k in ["email", "error"])

        msg = get_message(
            "PASSWORD_RESET_EXPIRED", within="1 milliseconds", email="joe@lp.com"
        )
        assert msg == qparams["error"].encode("utf-8")

        # Test mangled token
        token = (
            "WyIxNjQ2MzYiLCIxMzQ1YzBlZmVhM2VhZjYwODgwMDhhZGU2YzU0MzZjMiJd."
            "BZEw_Q.lQyo3npdPZtcJ_sNHVHP103syjM"
            "&url_id=fbb89a8328e58c181ea7d064c2987874bc54a23d"
        )
        response = client.get("/reset/" + token)
        assert response.status_code == 302
        split = urlsplit(response.headers["Location"])
        assert "localhost:8081" == split.netloc
        assert "/reset-error" == split.path
        qparams = dict(parse_qsl(split.query))
        assert len(qparams) == 1
        assert all(k in qparams for k in ["error"])

        msg = get_message("INVALID_RESET_PASSWORD_TOKEN")
        assert msg == qparams["error"].encode("utf-8")
    assert len(flashes) == 0


@pytest.mark.settings(backwards_compat_auth_token_invalid=True)
def test_bc_password(app, client_nc):
    # Test behavior of BACKWARDS_COMPAT_AUTH_TOKEN_INVALID
    response = json_authenticate(client_nc, email="joe@lp.com")
    token = response.jdata["response"]["user"]["authentication_token"]
    verify_token(client_nc, token)
    json_logout(client_nc, token)

    with capture_reset_password_requests() as requests:
        response = client_nc.post(
            "/reset",
            data='{"email": "joe@lp.com"}',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200

    reset_token = requests[0]["token"]

    data = dict(password="newpassword", password_confirm="newpassword")
    response = client_nc.post(
        "/reset/" + reset_token + "?include_auth_token=1",
        data=json.dumps(data),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert "authentication_token" in response.jdata["response"]["user"]

    # changing password should have rendered existing auth tokens invalid
    verify_token(client_nc, token, status=401)

    # but new auth token should work
    token = response.jdata["response"]["user"]["authentication_token"]
    verify_token(client_nc, token)
