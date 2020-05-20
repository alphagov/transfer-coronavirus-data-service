import pytest

import cognito
import stubs


def test_env_pool_id_development():
    user_pool_id = stubs.MOCK_COGNITO_USER_POOL_ID
    stubber = stubs.mock_cognito_list_pools()
    with stubber:
        assert cognito.env_pool_id() == user_pool_id


def test_env_pool_id_production(monkeypatch):
    user_pool_id = stubs.MOCK_COGNITO_USER_POOL_ID
    monkeypatch.setenv("CF_SPACE", "production")
    stubber = stubs.mock_cognito_list_pools(env="prod")
    with stubber:
        assert cognito.env_pool_id() == user_pool_id


def test_list_pools():
    user_pool_id = stubs.MOCK_COGNITO_USER_POOL_ID
    stubber = stubs.mock_cognito_list_pools()

    with stubber:
        pools = cognito.list_pools()
        assert pools[0]["id"] == user_pool_id
        stubber.deactivate()


@pytest.mark.usefixtures("admin_user", "create_user_arguments")
def test_create_user(admin_user, create_user_arguments):
    stubber = stubs.mock_cognito_admin_create_user(admin_user, create_user_arguments)

    with stubber:
        created = cognito.create_user(
            admin_user["name"],
            admin_user["email"],
            admin_user["phone_number"],
            admin_user["custom:is_la"],
            admin_user["custom:paths"],
        )
        assert created
        stubber.deactivate()


@pytest.mark.usefixtures("admin_user", "create_user_arguments")
def test_update_user(admin_user, create_user_arguments):
    attributes = create_user_arguments["UserAttributes"]
    stubber = stubs.mock_cognito_admin_update_user_attributes(admin_user, attributes)

    with stubber:
        updated = cognito.update_user(admin_user["email"], attributes)
        assert updated
        stubber.deactivate()


@pytest.mark.usefixtures("admin_user")
def test_delete_user(admin_user):
    stubber = stubs.mock_cognito_admin_delete_user(admin_user["email"])

    with stubber:
        deleted = cognito.delete_user(admin_user["email"])
        assert deleted
        stubber.deactivate()


@pytest.mark.usefixtures("admin_user")
def test_disable_user(admin_user):
    stubber = stubs.mock_cognito_admin_disable_user(admin_user["email"])

    with stubber:
        disabled = cognito.disable_user(admin_user["email"])
        assert disabled
        stubber.deactivate()


@pytest.mark.usefixtures("admin_user")
def test_enable_user(admin_user):
    stubber = stubs.mock_cognito_admin_enable_user(admin_user["email"])

    with stubber:
        enabled = cognito.enable_user(admin_user["email"])
        assert enabled
        stubber.deactivate()


@pytest.mark.usefixtures("admin_user")
def test_set_user_settings(admin_user):
    stubber = stubs.mock_cognito_admin_set_user_settings(admin_user["email"])

    with stubber:
        updated = cognito.set_user_settings(admin_user["email"])
        assert updated
        stubber.deactivate()


@pytest.mark.usefixtures("admin_user")
def test_set_mfa_preferences(admin_user):
    stubber = stubs.mock_cognito_admin_set_user_mfa_preference(admin_user["email"])

    with stubber:
        updated = cognito.set_mfa_preferences(admin_user["email"])
        assert updated
        stubber.deactivate()


@pytest.mark.usefixtures("admin_user")
def test_add_to_group(admin_user):
    group_name = admin_user["group"]["value"]
    stubber = stubs.mock_cognito_admin_add_user_to_group(
        admin_user["email"], group_name
    )

    with stubber:
        updated = cognito.add_to_group(admin_user["email"], group_name)
        assert updated
        stubber.deactivate()


@pytest.mark.usefixtures("admin_user")
def test_remove_from_group(admin_user):
    group_name = admin_user["group"]["value"]
    stubber = stubs.mock_cognito_admin_remove_user_from_group(
        admin_user["email"], group_name
    )

    with stubber:
        updated = cognito.remove_from_group(admin_user["email"], group_name)
        assert updated
        stubber.deactivate()


@pytest.mark.usefixtures("admin_user", "admin_get_user")
def test_get_user(admin_user, admin_get_user):
    stubber = stubs.mock_cognito_admin_get_user(admin_user["email"], admin_get_user)

    with stubber:
        user = cognito.get_user(admin_user["email"])
        assert user["Username"] == admin_user["email"]
        stubber.deactivate()


@pytest.mark.usefixtures("admin_user")
def test_list_groups_for_user(admin_user):
    stubber = stubs.mock_cognito_admin_list_groups_for_user(admin_user)

    with stubber:
        groups = cognito.list_groups_for_user(admin_user["email"])
        assert "Groups" in groups
        assert len(groups["Groups"]) > 0
        first_group = groups["Groups"][0]
        assert first_group["GroupName"] == admin_user["group"]["value"]
        stubber.deactivate()
