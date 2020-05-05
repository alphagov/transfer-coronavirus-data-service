from unittest.mock import patch

import pytest

import cognito
import stubs


def test_env_pool_id(monkeypatch):
    with patch("cognito.list_pools") as mock_list_pools:
        monkeypatch.setenv("CF_SPACE", "staging")
        mock_list_pools.return_value = [
            {"name": "corona-cognito-pool-staging", "id": "staging-pool-id"},
            {"name": "corona-cognito-pool-prod", "id": "production-pool-id"},
        ]
        assert cognito.env_pool_id() == "staging-pool-id"

    with patch("cognito.list_pools") as mock_list_pools:
        monkeypatch.setenv("CF_SPACE", "production")
        mock_list_pools.return_value = [
            {"name": "corona-cognito-pool-staging", "id": "staging-pool-id"},
            {"name": "corona-cognito-pool-prod", "id": "production-pool-id"},
        ]
        assert cognito.env_pool_id() == "production-pool-id"


def test_list_pools():
    user_pool_id = "eu-west-2_poolid"
    stubber = stubs.mock_cognito_list_pools(user_pool_id)

    with stubber:
        pools = cognito.list_pools()
        assert pools[0]["id"] == user_pool_id
        stubber.deactivate()


@pytest.mark.usefixtures("admin_user", "create_user_arguments")
def test_update_user(admin_user, create_user_arguments):
    user_pool_id = "eu-west-2_poolid"
    attributes = create_user_arguments["UserAttributes"]
    stubber = stubs.mock_cognito_update_user_attributes(
        user_pool_id, admin_user, attributes
    )

    with stubber:
        updated = cognito.update_user(admin_user["email"], attributes)
        assert updated
        stubber.deactivate()
