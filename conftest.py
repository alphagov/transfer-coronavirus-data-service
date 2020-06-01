"""
This isn't used yet but there has to be a conftest file for
the test module includes to resolve successfully
"""
from datetime import datetime

import pytest

from config import load_environment
from main import app
from user import User


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


@pytest.fixture
def mock_env_staging(monkeypatch):
    monkeypatch.setenv("APP_ENVIRONMENT", "staging")


@pytest.fixture
def mock_env_production(monkeypatch):
    monkeypatch.setenv("APP_ENVIRONMENT", "production")


@pytest.fixture
def valid_user():
    return User("justin.casey@communities.gov.uk")


@pytest.fixture
def user_with_invalid_email():
    return User("not_an_email")


@pytest.fixture
def user_with_invalid_domain():
    return User("justin.casey@hotmail.com")


@pytest.fixture()
def admin_get_user():
    now = datetime.utcnow()
    return {
        "Username": "justin.casey@communities.gov.uk",
        "UserStatus": "CONFIRMED",
        "UserCreateDate": now,
        "UserLastModifiedDate": now,
        "Enabled": True,
        "UserAttributes": [
            {"Name": "sub", "Value": "a_uuid"},
            {"Name": "email_verified", "Value": "true"},
            {
                "Name": "custom:paths",
                "Value": ";".join(
                    [
                        "web-app-prod-data/local_authority/barking",
                        "web-app-prod-data/local_authority/haringey",
                    ]
                ),
            },
            {"Name": "name", "Value": "Justin Casey"},
            {"Name": "phone_number_verified", "Value": "false"},
            {"Name": "custom:is_la", "Value": "1"},
            {"Name": "phone_number", "Value": "+447123456789"},
            {"Name": "email", "Value": "justin.casey@communities.gov.uk"},
        ],
    }


@pytest.fixture()
def user_details_response(group_result):
    now = datetime.utcnow()
    return {
        "username": "justin.casey@communities.gov.uk",
        "status": "a_status",
        "createdate": now,
        "lastmodifieddate": now,
        "enabled": True,
        "sub": "a_uuid",
        "email_verified": "true",
        "custom:paths": "some_custom_paths",
        "name": "JustinCasey",
        "phone_number_verified": "false",
        "custom:is_la": "0",
        "phone_number": "a_phone",
        "email": "justin.casey@communities.gov.uk",
        "group": group_result,
    }


@pytest.fixture()
def standard_download_group_response():
    return {"Groups": [{"GroupName": "standard-download"}]}


@pytest.fixture()
def group_result():
    return {
        "preference": 10,
        "value": "standard-download",
        "display": "Standard download user",
    }


@pytest.fixture()
def create_user_arguments():
    return {
        "UserAttributes": [
            {"Name": "name", "Value": "Justin Casey"},
            {"Name": "email", "Value": "justin.casey@communities.gov.uk"},
            {"Name": "email_verified", "Value": "true"},
            {"Name": "phone_number", "Value": "+447123456789"},
            {"Name": "phone_number_verified", "Value": "false"},
            {"Name": "custom:is_la", "Value": "1"},
            {
                "Name": "custom:paths",
                "Value": ";".join(
                    [
                        "web-app-prod-data/local_authority/barking",
                        "web-app-prod-data/local_authority/haringey",
                    ]
                ),
            },
        ],
        "UserPoolId": "eu-west-2_poolid",
        "Username": "justin.casey@communities.gov.uk",
        "ForceAliasCreation": False,
        "DesiredDeliveryMediums": ["EMAIL"],
    }


@pytest.fixture()
def list_users_arguments():
    return {
        "AttributesToGet": [
            "name",
            "email",
            "email_verified",
            "phone_number",
            "phone_number_verified",
            "cognito:user_status",
            "custom:paths",
            "custom:is_la",
        ],
        "Limit": 20,
    }


@pytest.fixture()
def list_users_response(admin_get_user):
    return {
        "Users": [admin_get_user],
    }


@pytest.fixture()
def list_users_result(user_details_response):
    return {
        "users": [user_details_response],
        "token": "",
    }


@pytest.fixture()
def test_no_mfa_user():
    return {
        "Username": "test-secrets",
        "UserAttributes": [
            {"Name": "custom:paths", "Value": "local_authority/barnet"},
            {"Name": "custom:is_la", "Value": "1"},
        ],
    }


@pytest.fixture()
def test_mfa_user():
    return {
        "Username": "test-secrets",
        "UserAttributes": [
            {"Name": "custom:paths", "Value": "local_authority/barnet"},
            {"Name": "custom:is_la", "Value": "1"},
        ],
        "MFAOptions": [{"DeliveryMedium": "SMS", "AttributeName": "phone_number"}],
        "PreferredMfaSetting": "SMS_MFA",
        "UserMFASettingList": ["SMS_MFA"],
    }


@pytest.fixture()
def test_get_object():
    return {"Body": "test,the,csv", "ResponseMetadata": {"HTTPStatusCode": 200}}


@pytest.fixture()
def test_list_object_file():
    now = datetime.utcnow()
    prefix = "web-app-prod-data/local_authority/barnet"
    mock_list_object = {
        "Key": f"{prefix}/people1.csv",
        "Size": 100,
        "LastModified": now,
    }
    return mock_list_object


@pytest.fixture()
def test_ssm_parameters():
    return {
        "/cognito/client_id": "abc123",
        "/cognito/client_secret": "def456",  # pragma: allowlist secret
        "/cognito/domain": "example.com",
        "/s3/bucket_name": "my_bucket",
        "/flask/secret_key": "my_secret_key",
    }


@pytest.fixture()
def test_load_cognito_settings():
    return {
        "client_id": "abc123",
        "client_secret": "def456",  # pragma: allowlist secret
        "host_name": "example",
        "domain": "auth.eu-west-2.amazoncognito.com",
    }
