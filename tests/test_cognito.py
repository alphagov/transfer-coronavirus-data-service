from unittest.mock import patch

import boto3
from botocore.stub import Stubber

from cognito import env_pool_id, make_request


def test_env_pool_id(monkeypatch):
    with patch("cognito.list_pools") as mock_list_pools:
        monkeypatch.setenv("CF_SPACE", "staging")
        mock_list_pools.return_value = [
            {"name": "corona-cognito-pool-staging", "id": "staging-pool-id"},
            {"name": "corona-cognito-pool-prod", "id": "production-pool-id"},
        ]
        assert env_pool_id() == "staging-pool-id"

    with patch("cognito.list_pools") as mock_list_pools:
        monkeypatch.setenv("CF_SPACE", "production")
        mock_list_pools.return_value = [
            {"name": "corona-cognito-pool-staging", "id": "staging-pool-id"},
            {"name": "corona-cognito-pool-prod", "id": "production-pool-id"},
        ]
        assert env_pool_id() == "production-pool-id"


def test_delete_user():
    stubbed_make_request("admin_delete_user")


def test_enable_user():
    stubbed_make_request("admin_enable_user")


def test_disable_user():
    stubbed_make_request("admin_disable_user")


def stubbed_make_request(method_name):
    client = boto3.client("cognito-idp")
    stubber = Stubber(client)
    expected_params = {
        "UserPoolId": "some-pool-id",
        "Username": "test@digital.cabinet-office.gov.uk",
    }
    # If it responds with 200, should return true
    response = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    stubber.add_response(method_name, response, expected_params)
    with stubber:
        with patch("cognito.aws_client") as mock_get_client:
            mock_get_client.return_value = client
            with patch("cognito.env_pool_id") as mock_cognito_env_pool_id:
                mock_cognito_env_pool_id.return_value = "some-pool-id"
                assert make_request(method_name, "test@digital.cabinet-office.gov.uk")

    # If it responds with !200, should return false
    admin_delete_user_response = {"ResponseMetadata": {"HTTPStatusCode": 403}}
    stubber.add_response(method_name, admin_delete_user_response, expected_params)
    with stubber:
        with stubber:
            with patch("cognito.aws_client") as mock_get_client:
                with patch("cognito.env_pool_id") as mock_cognito_env_pool_id:
                    mock_cognito_env_pool_id.return_value = "some-pool-id"
                    assert not make_request(
                        method_name, "test@digital.cabinet-office.gov.uk"
                    )
