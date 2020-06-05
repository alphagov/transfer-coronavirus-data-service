import json
import os
from datetime import datetime

import flask
import pytest
import requests_mock

import stubs
import config
from main import (
    app,
    categorise_file,
    collect_files_by_date,
    create_presigned_url,
    date_file,
    generate_upload_file_path,
    get_file_name_category,
    get_files,
    is_mfa_configured,
    key_has_granted_prefix,
    load_user_lookup,
    re_case_word,
    return_attribute,
    upload_form_validate,
    user_custom_paths,
    validate_access_to_s3_path,
)


def test_css():
    with app.test_request_context("/css/govuk-frontend-3.6.0.min.css"):
        assert flask.request.view_args["path"] == "govuk-frontend-3.6.0.min.css"
        assert flask.request.url_rule.rule == "/css/<path:path>"


def test_js():
    with app.test_request_context("/js/govuk-frontend-3.6.0.min.js"):
        assert flask.request.view_args["path"] == "govuk-frontend-3.6.0.min.js"
        assert flask.request.url_rule.rule == "/js/<path:path>"


def test_assets():
    with app.test_request_context("/assets/images/govuk-crest-2x.png"):
        assert flask.request.view_args["path"] == "images/govuk-crest-2x.png"
        assert flask.request.url_rule.rule == "/assets/<path:path>"


def test_dist():
    with app.test_request_context("/dist/html5shiv.min.js"):
        assert flask.request.view_args["path"] == "html5shiv.min.js"
        assert flask.request.url_rule.rule == "/dist/<path:path>"


# Test the flask routes


@pytest.mark.usefixtures("test_client")
def test_route_index_logged_out(test_client):
    response = test_client.get("/")
    assert response.status_code == 200


@pytest.mark.usefixtures("test_client", "test_session")
def test_route_index_logged_in(test_client, test_session):
    with test_client.session_transaction() as client_session:
        client_session.update(test_session)
    response = test_client.get("/")
    body = response.data.decode()

    assert response.status_code == 200
    assert "You're currently logged in as" in body
    assert (
        '<span class="covid-transfer-username">test-user@test-domain.com</span>' in body
    )


@pytest.mark.usefixtures("test_client", "test_upload_session")
def test_route_index_logged_in_upload(test_client, test_upload_session):
    with test_client.session_transaction() as client_session:
        client_session.update(test_upload_session)

    response = test_client.get("/")
    body = response.data.decode()
    assert response.status_code == 200
    assert "<h3>Upload</h3>" in body


@pytest.mark.usefixtures("test_client", "test_session")
def test_route_files(test_client, test_session):
    with test_client.session_transaction() as client_session:
        client_session.update(test_session)

    root_path = "web-app-prod-data"
    bucket_name = "test_bucket"
    paths = load_user_lookup(test_session)
    stubber = stubs.mock_s3_list_objects(bucket_name, paths)

    with stubber:
        response = test_client.get("/files")
        body = response.data.decode()

        assert response.status_code == 200
        assert "You're currently logged in as" in body
        assert (
            '<span class="covid-transfer-username">test-user@test-domain.com</span>'
            in body
        )
        # Check the root path is removed from the presented link  text
        # This test may need to change if we change the download
        # behaviour
        assert f">{root_path}/local_authority" not in body
        assert "There are 10 files available to download:" in body
        assert "local_authority/haringey/people1.csv" in body
        assert "local_authority/haringey/people4.csv" in body


@pytest.mark.usefixtures("test_client", "test_session", "test_get_object")
def test_route_download(test_client, test_session, test_get_object):
    with test_client.session_transaction() as client_session:
        client_session.update(test_session)

    bucket_name = "test_bucket"
    bucket_granted_key = "web-app-prod-data/local_authority/haringey/test.csv"
    bucket_denied_key = "web-app-prod-data/local_authority/hackney/test.csv"

    granted_prefixes = return_attribute(test_session, "custom:path").split(";")

    stubber = stubs.mock_s3_get_object(
        bucket_name, granted_prefixes, bucket_granted_key, test_get_object
    )

    with stubber:
        response = test_client.get(f"/download/{bucket_granted_key}")
        body = response.data.decode()

        app.logger.debug(response.location)
        assert response.status_code == 302
        assert "<h1>Redirecting...</h1>" in body
        assert response.location not in ["http://localhost/403", "http://localhost/404"]

    stubber = stubs.mock_s3_get_object(
        bucket_name, granted_prefixes, bucket_denied_key, test_get_object
    )

    with stubber:
        response = test_client.get(f"/download/{bucket_denied_key}")
        body = response.data.decode()

        assert response.status_code == 302
        assert "<h1>Redirecting...</h1>" in body
        assert response.location == "http://localhost/403"


@pytest.mark.usefixtures("test_client", "test_session")
def test_route_upload_denied(test_client, test_session):
    with test_client.session_transaction() as client_session:
        client_session.update(test_session)

    response = test_client.get("/upload")
    body = response.data.decode()
    assert response.status_code == 302
    assert "<h1>Redirecting...</h1>" in body


@pytest.mark.usefixtures("test_client", "test_upload_session")
def test_route_upload_allowed(test_client, test_upload_session):
    with test_client.session_transaction() as client_session:
        client_session.update(test_upload_session)

    response = test_client.get("/upload")
    body = response.data.decode()
    assert response.status_code == 200
    assert '<h3 class="govuk-heading-m">File settings</h3>' in body


@pytest.mark.usefixtures("test_client")
def test_route_css(test_client):
    """ Check CSS actually resolves successfully """
    response = test_client.get("/css/govuk-frontend-3.6.0.min.css")
    body = response.data.decode()
    assert response.status_code == 200
    assert ".govuk-link{" in body


@pytest.mark.usefixtures("test_client")
def test_route_js(test_client):
    """ Check JS actually resolves successfully """
    response = test_client.get("/js/govuk-frontend-3.6.0.min.js")
    body = response.data.decode()
    assert response.status_code == 200
    assert "!function(t,e)" in body

    # Check IE shim JS
    response = test_client.get("/dist/html5shiv.min.js")
    body = response.data.decode()
    assert response.status_code == 200
    assert "!function(a,b)" in body


@pytest.mark.usefixtures("test_client", "test_session", "test_mfa_user")
@requests_mock.Mocker(kw="mocker")
def test_auth_flow(test_client, test_session, test_mfa_user, **args):
    """ Test mocked oauth exchange """

    token = "abc123"
    domain = "test.cognito.domain.com"
    token_endpoint_url = f"https://{domain}/oauth2/token"
    app.config["cognito_domain"] = domain
    app.config["client_id"] = "123456"
    app.config["client_secret"] = "987654"
    app.config["redirect_host"] = "test.domain.com"
    stubber = stubs.mock_cognito_auth_flow(token, test_mfa_user)

    with test_client.session_transaction() as client_session:
        client_session.update(test_session)

    """Test using request mocker and boto stub."""

    oauth_response = json.dumps({"id_token": token, "access_token": token})
    mocker = args["mocker"]
    mocker.request(method="POST", url=token_endpoint_url, text=oauth_response)
    response = test_client.get(f"/?code={token}")
    body = response.data.decode()
    assert response.status_code == 302
    assert "<h1>Redirecting...</h1>" in body
    stubber.deactivate()


@pytest.mark.usefixtures("test_client", "test_session", "test_no_mfa_user")
@requests_mock.Mocker(kw="mocker")
def test_auth_flow_with_no_mfa_user(
    test_client, test_session, test_no_mfa_user, **args
):
    """ Test mocked oauth exchange """

    token = "abc123"
    domain = "test.cognito.domain.com"
    token_endpoint_url = f"https://{domain}/oauth2/token"
    app.config["cognito_domain"] = domain
    config.set("app_environment", "production")
    app.config["client_id"] = "123456"
    app.config["client_secret"] = "987654"
    app.config["redirect_host"] = "test.domain.com"
    stubber = stubs.mock_cognito_auth_flow(token, test_no_mfa_user)

    with test_client.session_transaction() as client_session:
        client_session.update(test_session)

    """Test using request mocker and boto stub."""

    oauth_response = json.dumps({"id_token": token, "access_token": token})
    mocker = args["mocker"]
    mocker.request(method="POST", url=token_endpoint_url, text=oauth_response)
    response = test_client.get(f"/?code={token}")

    body = response.data.decode()
    assert response.status_code == 302
    assert "<h1>Redirecting...</h1>" in body
    assert response.headers.get("Location").endswith("403")
    stubber.deactivate()


# Test access management functions


@pytest.mark.usefixtures("test_session")
def test_return_attribute(test_session):
    user_attribute_value = return_attribute(test_session, "custom:is_la")
    assert user_attribute_value == "1"


@pytest.mark.usefixtures("test_session")
def test_load_user_lookup(test_session):
    root_path = "web-app-prod-data"
    paths = load_user_lookup(test_session)
    assert f"{root_path}/local_authority/haringey" in paths
    assert f"{root_path}/local_authority/barnet" in paths
    test_session.update(
        {
            "attributes": [
                {"Name": "custom:is_la", "Value": "1"},
                {"Name": "custom:paths", "Value": ""},
            ]
        }
    )
    paths = load_user_lookup(test_session)
    assert len(paths) == 0
    replace_paths = f"{root_path}/local_authority/haringey;"
    test_session.update(
        {
            "attributes": [
                {"Name": "custom:is_la", "Value": "1"},
                {"Name": "custom:paths", "Value": replace_paths},
            ]
        }
    )
    paths = load_user_lookup(test_session)
    assert len(paths) == 1
    assert f"{root_path}/local_authority/haringey" in paths
    assert f"{root_path}/local_authority/barnet" not in paths
    replace_paths = ";web-app-prod-data/local_authority/haringey"
    test_session.update(
        {
            "attributes": [
                {"Name": "custom:is_la", "Value": "1"},
                {"Name": "custom:paths", "Value": replace_paths},
            ]
        }
    )
    paths = load_user_lookup(test_session)
    assert len(paths) == 1
    assert f"{root_path}/local_authority/haringey" in paths
    assert f"{root_path}/local_authority/barnet" not in paths
    replace_paths = (
        f"{root_path}/local_authority/haringey;;" f"{root_path}/local_authority/barnet"
    )
    test_session.update(
        {
            "attributes": [
                {"Name": "custom:is_la", "Value": "1"},
                {"Name": "custom:paths", "Value": replace_paths},
            ]
        }
    )
    paths = load_user_lookup(test_session)
    assert len(paths) == 2
    assert f"{root_path}/local_authority/haringey" in paths
    assert f"{root_path}/local_authority/barnet" in paths

    fake_root_path = "web-app-nonprod-data"
    replace_paths = (
        f"{fake_root_path}/local_authority/haringey;;"
        f"{fake_root_path}/local_authority/barnet"
    )
    test_session.update(
        {
            "attributes": [
                {"Name": "custom:is_la", "Value": "1"},
                {"Name": "custom:paths", "Value": replace_paths},
            ]
        }
    )
    paths = load_user_lookup(test_session)
    assert len(paths) == 0

    replace_paths = (
        f"{fake_root_path}/local_authority/haringey;;"
        f"{root_path}/local_authority/barnet"
    )
    test_session.update(
        {
            "attributes": [
                {"Name": "custom:is_la", "Value": "1"},
                {"Name": "custom:paths", "Value": replace_paths},
            ]
        }
    )
    paths = load_user_lookup(test_session)
    assert len(paths) == 1
    # check paths outside approved root path are not returned
    assert f"{fake_root_path}/local_authority/haringey" not in paths
    assert f"{root_path}/local_authority/barnet" in paths


@pytest.mark.usefixtures("test_session")
def test_get_files(test_session):
    """ Test mocked delete ssm param """
    root_path = "web-app-prod-data"
    bucket_name = "test_bucket"
    paths = load_user_lookup(test_session)

    stubber = stubs.mock_s3_list_objects(bucket_name, paths)

    with stubber:
        os.environ["AWS_ACCESS_KEY_ID"] = "fake"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "fake"
        matched_files = get_files(bucket_name, test_session)
        matched_keys = [matched_file["key"] for matched_file in matched_files]
        # check page 1 is there
        assert f"{root_path}/local_authority/haringey/people1.csv" in matched_keys
        # check page 2 is there
        assert f"{root_path}/local_authority/haringey/people4.csv" in matched_keys
        # check that recursive paths are returned
        assert (
            f"{root_path}/local_authority/haringey/nested/nested_people1.csv"
            in matched_keys
        )
        # check that page 1 of 2nd prefix is returned
        assert f"{root_path}/local_authority/barnet/people1.csv" in matched_keys
        # check that page 2 of 2nd prefix is returned
        assert f"{root_path}/local_authority/barnet/people4.csv" in matched_keys
        stubber.deactivate()


@pytest.mark.usefixtures("test_session")
def test_create_presigned_url(test_session):
    """ Test creation of presigned url """
    bucket = "test_bucket"
    paths = load_user_lookup(test_session)
    stubber = stubs.mock_s3_list_objects(bucket, paths)

    with stubber:
        key = "test_key"
        url = create_presigned_url(bucket, key, expiration=600)
        assert "https://test_bucket.s3.amazonaws.com/test_key" in url
        stubber.deactivate()


@pytest.mark.usefixtures("test_session")
def test_user_custom_paths(test_session):
    download_paths = user_custom_paths(test_session, is_upload=False)
    assert "web-app-prod-data/local_authority/haringey" in download_paths
    upload_paths = user_custom_paths(test_session, is_upload=True)
    assert "web-app-upload/local_authority/barnet" in upload_paths


@pytest.mark.usefixtures("test_session", "upload_form_fields", "valid_extensions")
def test_upload_form_validate(test_session, upload_form_fields, valid_extensions):
    upload_paths = user_custom_paths(test_session, is_upload=True)
    validation_status = upload_form_validate(
        upload_form_fields, upload_paths, valid_extensions
    )
    # valid with fixture data
    assert validation_status["valid"]
    validation_status = upload_form_validate(
        upload_form_fields, ["web-app-upload/other/gds"], valid_extensions
    )
    # not valid if granted paths don't match
    assert not validation_status["valid"]
    invalid_form_fields = {}
    invalid_form_fields.update(upload_form_fields)
    invalid_form_fields["file_ext"] = "xls"
    validation_status = upload_form_validate(
        invalid_form_fields, upload_paths, valid_extensions
    )
    # not valid if file type is not matched
    assert not validation_status["valid"]


@pytest.mark.usefixtures("upload_form_fields")
def test_generate_upload_file_path(upload_form_fields):
    file_path = generate_upload_file_path(upload_form_fields)
    assert file_path.startswith(upload_form_fields["file_location"])
    assert upload_form_fields["file_name"] in file_path
    assert file_path.endswith(f".{upload_form_fields['file_ext']}")


def test_key_has_granted_prefix():
    key = "web-app-prod-data/other/gds/file.csv"
    prefixes = ["web-app-prod-data/other/gds"]
    assert key_has_granted_prefix(key, prefixes)
    key = "web-app-prod-data/other/not-gds/file.csv"
    prefixes = ["web-app-prod-data/other/gds"]
    assert not key_has_granted_prefix(key, prefixes)
    key = "web-app-prod-data/other/gds/file.csv"
    prefixes = ["web-app-prod-data/other/gds", "web-app-prod-data/other/nhs"]
    assert key_has_granted_prefix(key, prefixes)
    key = "web-app-prod-data/other/nhs/file.csv"
    prefixes = ["web-app-prod-data/other/gds", "web-app-prod-data/other/nhs"]
    assert key_has_granted_prefix(key, prefixes)
    key = "web-app-prod-data/other/gds/some/other/file/structure/file.csv"
    prefixes = ["web-app-prod-data/other/gds"]
    assert key_has_granted_prefix(key, prefixes)
    key = "web-app-prod-data/other/gds/file.csv"
    prefixes = ["web-app-prod-data/other/non-gds", "web-app-prod-data/other/nhs"]
    assert not key_has_granted_prefix(key, prefixes)


@pytest.mark.usefixtures("test_mfa_user", "test_no_mfa_user")
def test_is_mfa_configured(test_mfa_user, test_no_mfa_user):
    # Check returns True for valid user
    assert is_mfa_configured(test_mfa_user)
    # Check returns False for invalid user
    assert not is_mfa_configured(test_no_mfa_user)
    # Check returns False if phone_number attribute is wrong
    test_wrong_sms_attribute = {}
    test_wrong_sms_attribute.update(test_mfa_user)
    test_wrong_sms_attribute["MFAOptions"][0]["AttributeName"] = "phone"
    assert not is_mfa_configured(test_wrong_sms_attribute)
    # Check returns False if "PreferredMfaSetting" is not set
    test_missing_preferred_device = {}
    test_missing_preferred_device.update(test_mfa_user)
    del test_missing_preferred_device["PreferredMfaSetting"]
    assert not is_mfa_configured(test_missing_preferred_device)
    test_wrong_preferred_device = {}
    test_wrong_preferred_device.update(test_mfa_user)
    test_wrong_preferred_device["PreferredMfaSetting"] = "Email_MFA"
    assert not is_mfa_configured(test_wrong_preferred_device)


@pytest.mark.usefixtures("test_get_object")
def test_validate_access_to_s3_path(test_get_object):
    bucket_name = "bucket"
    granted_key = "granted/filename"
    denied_key = "denied/filename"

    stubber = stubs.mock_s3_get_object(
        bucket_name, ["granted"], granted_key, test_get_object
    )
    with stubber:
        assert validate_access_to_s3_path(bucket_name, granted_key)
        stubber.deactivate()

    stubber = stubs.mock_s3_get_object(
        bucket_name, ["granted"], denied_key, test_get_object
    )
    with stubber:
        assert not validate_access_to_s3_path(bucket_name, denied_key)
        stubber.deactivate()


@pytest.mark.usefixtures("test_session")
def test_collect_files_by_date(test_session):
    bucket_name = "test_bucket"
    paths = load_user_lookup(test_session)
    now = datetime.utcnow()
    date_string = now.strftime("%d/%m/%Y")

    stubber = stubs.mock_s3_list_objects(bucket_name, paths)
    with stubber:
        os.environ["AWS_ACCESS_KEY_ID"] = "fake"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "fake"
        matched_files = get_files(bucket_name, test_session)
        collected = collect_files_by_date(matched_files)
        assert date_string in collected["by_date"]
        assert collected["count"] == 10


@pytest.mark.usefixtures("test_list_object_file")
def test_categorise_file(test_list_object_file):
    prefix = "web-app-prod-data/local_authority/barnet"
    file0 = test_list_object_file
    categorise_file(file0, prefix)
    assert file0["Category"] == "People1"


def test_get_file_name_category():
    bare_file_name = "20200526-120000.csv"
    assert get_file_name_category(bare_file_name) == ""
    prefixed_file_name = "nhs-20200526-120000.csv"
    assert get_file_name_category(prefixed_file_name) == "nhs"
    suffixed_file_name = "20200526-120000-nhs.csv"
    assert get_file_name_category(suffixed_file_name) == "nhs"
    underscored_file_name = "nhs_20200526_120000.csv"
    assert get_file_name_category(underscored_file_name) == "nhs"


@pytest.mark.usefixtures("test_list_object_file")
def test_date_file(test_list_object_file):
    now = datetime.utcnow()
    date_string = now.strftime("%d/%m/%Y")
    date_sorter = now.strftime("%Y%m%d%H%M")

    file0 = test_list_object_file
    date_file(file0)
    assert file0["SortTime"] == date_sorter
    assert file0["ShowDate"] == date_string


def test_re_case_word():
    assert re_case_word("nhs") == "NHS"
    assert re_case_word("gds") == "GDS"
    assert re_case_word("dwp") == "DWP"
    assert re_case_word("mhclg") == "MHCLG"
    assert re_case_word("other") == "Other"
