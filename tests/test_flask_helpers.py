import os

import pytest
from flask import session

from flask_helpers import (
    has_upload_rights,
    is_admin_interface,
    is_development,
    user_has_a_valid_role,
)
from main import app


@pytest.mark.usefixtures("test_session", "test_upload_session")
def test_route_index_logged_in(test_session, test_upload_session):

    with app.test_request_context("/"):
        session.update(test_session)
        assert not has_upload_rights()

    with app.test_request_context("/"):
        session.update(test_upload_session)
        assert has_upload_rights()


def test_is_admin_interface():
    os.environ["ADMIN"] = "true"
    assert is_admin_interface()
    os.environ["ADMIN"] = "false"
    assert not is_admin_interface()
    del os.environ["ADMIN"]
    assert not is_admin_interface()


def test_is_development():
    os.environ["APP_ENVIRONMENT"] = "staging"
    assert is_development()
    os.environ["APP_ENVIRONMENT"] = "testing"
    assert is_development()
    os.environ["APP_ENVIRONMENT"] = "production"
    assert not is_development()
    del os.environ["APP_ENVIRONMENT"]
    assert not is_development()


@pytest.mark.usefixtures("test_session")
def test_user_has_a_valid_role(test_session):
    with app.test_request_context("/"):
        session.update(test_session)
        assert not user_has_a_valid_role(["admin-full"])
        assert user_has_a_valid_role(["standard-download"])
        assert not user_has_a_valid_role(["admin-power", "admin-full"])
        assert user_has_a_valid_role(["standard-upload", "standard-download"])
