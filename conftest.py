"""
This isn't used yet but there has to be a conftest file for
the test module includes to resolve successfully
"""
import pytest

from main import app, load_environment


def get_standard_download_group():
    return {
        "preference": 10,
        "value": "standard-download",
        "display": "Standard download user",
    }


def get_standard_upload_group():
    return {
        "preference": 20,
        "value": "standard-upload",
        "display": "Standard download and upload user",
    }


def get_admin_full_group():
    return {
        "preference": 90,
        "value": "admin-full",
        "display": "User administrator full access",
    }


def get_default_session():
    user_paths = (
        "web-app-prod-data/local_authority/haringey;"
        "web-app-prod-data/local_authority/barnet"
    )
    session = {
        "details": {
            "user": "test-user@test-domain.com",
            "email": "test-user@test-domain.com",
        },
        "user": "test-user@test-domain.com",
        "email": "test-user@test-domain.com",
        "attributes": [
            {"Name": "custom:is_la", "Value": "1"},
            {"Name": "custom:paths", "Value": user_paths},
        ],
        "group": get_standard_download_group(),
    }
    return session


@pytest.fixture()
def test_session():
    return get_default_session()


@pytest.fixture()
def test_upload_session():
    session = get_default_session()
    session["group"] = get_standard_upload_group()
    return session


@pytest.fixture()
def test_admin_session():
    session = get_default_session()
    session["group"] = get_admin_full_group()
    return session


@pytest.fixture()
def test_jwt():
    return get_test_jwt()


def get_test_jwt():
    return {"cognito:username": "test-user", "email": "test-user@test-domain.com"}


@pytest.fixture()
def fake_jwt_decoder():
    def decoder(
        token: str, key: str, algorithms: list = [], verify: bool = False
    ) -> dict:
        return get_test_jwt()

    return decoder


@pytest.fixture()
def test_client():
    # Flask provides a way to test your application by exposing the Werkzeug test Client
    # and handling the context locals for you.
    testing_client = app.test_client()
    load_environment(app)

    # Establish an application context before running the tests.
    ctx = app.app_context()
    ctx.push()

    yield testing_client  # this is where the testing happens!

    ctx.pop()


@pytest.fixture()
def standard_download():
    return get_standard_download_group()


@pytest.fixture()
def standard_upload():
    return get_standard_upload_group()


@pytest.fixture()
def upload_form_fields():
    return {
        "file_location": "web-app-upload/local_authority/haringey",
        "file_name": "test_upload",
        "file_ext": "csv",
    }


@pytest.fixture()
def valid_extensions():
    return {"csv": {"ext": "csv", "display": "CSV"}}


@pytest.fixture()
def admin_user():
    return {
        "name": "Justin Casey",
        "email": "justin.casey@communities.gov.uk",
        "phone_number": "+447123456789",
        "group": get_standard_download_group(),
        "custom:is_la": "1",
        "custom:paths": ";".join(
            [
                "web-app-prod-data/local_authority/barking",
                "web-app-prod-data/local_authority/haringey",
            ]
        ),
    }


@pytest.fixture()
def user_confirm_form():
    form = {
        "full-name": "Justin Casey",
        "email": "justin.casey@communities.gov.uk",
        "telephone-number": "07123456789",
        "account": "standard-upload",
        "is-la-radio": "yes",
        "custom_paths": [
            "web-app-prod-data/local_authority/barnet",
            "web-app-prod-data/local_authority/hackney",
        ],
    }
    return form
