import json
import os

import flask
import pytest
import requests_mock

import stubs
from main import (
    app,
    create_presigned_url,
    get_files,
    load_user_lookup,
    return_attribute,
)


# Tests for assets helpers
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


@pytest.mark.usefixtures("test_client")
@pytest.mark.usefixtures("test_session")
def test_route_index_logged_in(test_client, test_session):
    with test_client.session_transaction() as client_session:
        client_session.update(test_session)
        app.logger.debug(test_session)
    response = test_client.get("/")
    body = response.data.decode()
    # print(body)
    assert response.status_code == 200
    assert "You're currently logged in as test-user." in body


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


@pytest.mark.usefixtures("test_client")
@pytest.mark.usefixtures("test_session")
@requests_mock.Mocker(kw="mocker")
def test_auth_flow(test_client, test_session, fake_jwt_decoder, **args):
    """ Test mocked oauth exchange """

    token = "abc123"
    domain = "test.cognito.domain.com"
    token_endpoint_url = f"https://{domain}/oauth2/token"
    app.cognito_domain = domain
    app.client_id = "123456"
    app.client_secret = "987654"
    app.redirect_host = "test.domain.com"
    stubber = stubs.mock_cognito(token)

    with test_client.session_transaction() as client_session:
        client_session.update(test_session)

    with stubber:
        """Test using request mocker and boto stub."""

        oauth_response = json.dumps({"id_token": token, "access_token": token})
        mocker = args["mocker"]
        mocker.request(method="POST", url=token_endpoint_url, text=oauth_response)
        response = test_client.get(f"/?code={token}")
        body = response.data.decode()
        assert response.status_code == 302
        assert "<h1>Redirecting...</h1>" in body
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
        assert f"{root_path}/local_authority/haringey/people1.csv" in matched_keys
        assert f"{root_path}/local_authority/haringey/people4.csv" in matched_keys
        assert (
            f"{root_path}/local_authority/haringey/nested/nested_people1.csv"
            in matched_keys
        )
        assert f"{root_path}/local_authority/barnet/people1.csv" in matched_keys
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
        assert ".co/test_bucket/test_key" in url
        stubber.deactivate()
