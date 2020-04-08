import pytest

from flask_helpers import has_upload_rights
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
