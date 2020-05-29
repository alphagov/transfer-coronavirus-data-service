import pytest
from flask import session

from flask_helpers import (
    has_upload_rights,
    is_admin_interface,
    is_development,
    user_has_a_valid_role,
)
from main import app
import config


@pytest.mark.usefixtures("test_session", "test_upload_session")
def test_route_index_logged_in(test_session, test_upload_session):

    with app.test_request_context("/"):
        session.update(test_session)
        assert not has_upload_rights()

    with app.test_request_context("/"):
        session.update(test_upload_session)
        assert has_upload_rights()


def test_is_admin_interface():
    config.set("admin", "true")
    assert is_admin_interface()
    config.set("admin", "false")
    assert not is_admin_interface()
    config.delete("admin")
    assert not is_admin_interface()


def test_is_development():
    config.set("app_environment", "staging")
    assert is_development()
    config.set("app_environment", "testing")
    assert is_development()
    config.set("app_environment", "production")
    assert not is_development()
    config.delete("app_environment")
    assert not is_development()


@pytest.mark.usefixtures("test_session")
def test_user_has_a_valid_role(test_session):
    with app.test_request_context("/"):
        session.update(test_session)
        assert not user_has_a_valid_role(["admin-full"])
        assert user_has_a_valid_role(["standard-download"])
        assert not user_has_a_valid_role(["admin-power", "admin-full"])
        assert user_has_a_valid_role(["standard-upload", "standard-download"])
