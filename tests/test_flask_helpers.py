import os

import pytest

from flask_helpers import has_upload_rights, is_admin_interface, is_development
from main import app


@pytest.mark.usefixtures("test_client")
@pytest.mark.usefixtures("test_session")
def test_route_index_logged_in(test_client, test_session):
    with test_client.session_transaction() as client_session:
        client_session.update(test_session)
        app.logger.debug(test_session)
    with app.test_request_context("/"):
        is_upload = has_upload_rights()
        assert not is_upload


def test_is_admin_interface():
    os.environ["ADMIN"] = "true"
    assert is_admin_interface()
    os.environ["ADMIN"] = "false"
    assert not is_admin_interface()
    del os.environ["ADMIN"]
    assert not is_admin_interface()


def test_is_development():
    os.environ["FLASK_ENV"] = "development"
    assert is_development()
    os.environ["FLASK_ENV"] = "production"
    assert not is_development()
    del os.environ["FLASK_ENV"]
    assert not is_development()
