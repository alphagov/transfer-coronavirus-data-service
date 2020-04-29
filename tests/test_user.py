from unittest.mock import call, patch

import pytest

from user import User


@pytest.mark.usefixtures("valid_user")
@pytest.mark.usefixtures("user_with_invalid_email")
@pytest.mark.usefixtures("user_with_invalid_domain")
@pytest.mark.usefixtures("group_result")
@pytest.mark.usefixtures("admin_get_user")
@pytest.mark.usefixtures("user_details_response")
@pytest.mark.usefixtures("standard_download_group_response")
@pytest.mark.usefixtures("user_details_response")
@pytest.mark.usefixtures("create_user_arguments")
@pytest.mark.usefixtures("list_users_arguments")
@pytest.mark.usefixtures("list_users_response")
@pytest.mark.usefixtures("list_users_result")
def test_email_sanitised_on_init():
    test1 = "anormalemail@example.gov.uk"
    assert User(test1).email_address == test1

    assert User("ANEMAIL@example.gov.uk").email_address == "anemail@example.gov.uk"
    assert User(" anemail@example.gov.uk ").email_address == "anemail@example.gov.uk"


def test_email_address_is_valid(
    valid_user, user_with_invalid_email, user_with_invalid_domain
):
    assert valid_user.email_address_is_valid()
    assert not user_with_invalid_email.email_address_is_valid()
    assert not user_with_invalid_domain.email_address_is_valid()


def test_allowed_domains_rejects_invalid_domain(valid_user, user_with_invalid_domain):
    assert valid_user.domain_is_allowed()
    assert not user_with_invalid_domain.domain_is_allowed()


def test_allowed_domains(valid_user):
    assert [
       ".gov.uk",
       "@brake.co.uk",
       "@nhs.net",
       "@tesco.com",
       "@ocadoretail.com",
       "@morrisonsplc.co.uk",
       "@sainsburys.co.uk",
       "@iceland.co.uk",
       "@coop.co.uk",
       "@asda.co.uk",
       "@johnlewis.co.uk",
       "@capita.com",
       "@coreconsultants.io",
    ] == valid_user.allowed_domains()


def test_delete_with_invalid_email(user_with_invalid_email):
    assert not user_with_invalid_email.delete()


def test_delete_with_valid_email(monkeypatch, valid_user):
    with patch("user.make_request") as mocked_send:
        assert valid_user.delete()
        mocked_send.assert_called_with("admin_delete_user", valid_user.email_address)


def test_enable_with_invalid_email(user_with_invalid_email):
    assert not user_with_invalid_email.enable()


def test_enable_with_valid_email(monkeypatch, valid_user):
    with patch("user.make_request") as mocked_send:
        assert valid_user.enable()
        mocked_send.assert_called_with("admin_enable_user", valid_user.email_address)


def test_disable_with_invalid_email(user_with_invalid_email):
    assert not user_with_invalid_email.disable()


def test_disable_with_valid_email(monkeypatch, valid_user):
    with patch("user.make_request") as mocked_send:
        assert valid_user.disable()
        mocked_send.assert_called_with("admin_disable_user", valid_user.email_address)


def test_normalise(valid_user, admin_get_user, user_details_response):
    with patch("user.make_request") as mocked_send:
        result = User.normalise(admin_get_user)
        mocked_send.assert_called_with(
            "admin_list_groups_for_user", valid_user.email_address, {}, True
        )
        assert result == user_details_response


def test_details(
    monkeypatch,
    valid_user,
    admin_get_user,
    standard_download_group_response,
    user_details_response,
):
    make_request_results = [admin_get_user, standard_download_group_response]
    with patch("user.make_request", side_effect=make_request_results) as mocked_send:
        result = valid_user.get_details()
        assert result == user_details_response
        expected_calls = [
            call("admin_get_user", valid_user.email_address),
            call("admin_list_groups_for_user", valid_user.email_address, {}, True,),
        ]
        mocked_send.assert_has_calls(expected_calls)


def test_sanitise_phone(valid_user):
    assert valid_user.sanitise_phone("+441234567890") == "+441234567890"
    assert valid_user.sanitise_phone("441234567890") == "+441234567890"
    assert valid_user.sanitise_phone("01234567890") == "+441234567890"
    assert valid_user.sanitise_phone("string_prefix01234567890") == "+441234567890"
    assert valid_user.sanitise_phone("notaphonenumber") == ""


def test_sanitise_name(valid_user):
    assert valid_user.sanitise_name("joe bloggs") == "joebloggs"
    assert valid_user.sanitise_name("joe_bloggs") == "joe_bloggs"
    assert valid_user.sanitise_name("joe bloggs 2") == "joebloggs2"


def test_update_returns_false_if_user_not_found(valid_user):
    with patch.object(valid_user, "get_details", return_value={}):
        assert not valid_user.update(
            "new name", "+441234567890", "web-app-prod-data", "0", "standard-upload"
        )


def test_update_returns_false_if_new_details_are_all_none(valid_user, admin_get_user):
    with patch.object(valid_user, "get_details", return_value=admin_get_user):
        assert not valid_user.update(None, None, None, None, None)


def test_update_returns_false_if_new_details_are_not_strings(
    valid_user, admin_get_user
):
    with patch.object(valid_user, "get_details", return_value=admin_get_user):
        assert not valid_user.update(0, 1, 2, 3, 4)


def test_update(valid_user, admin_get_user, user_details_response, group_result):
    make_request_results = [
        admin_get_user,
        user_details_response,
        group_result,
        True,
        True,
    ]
    with patch("user.make_request", side_effect=make_request_results) as mocked_send:
        assert valid_user.update(
            "new name", "+441234567890", "web-app-prod-data", "0", "standard-upload"
        )
        expected_calls = [
            call("admin_get_user", valid_user.email_address),
            call("admin_list_groups_for_user", valid_user.email_address, {}, True),
            call(
                "admin_remove_user_from_group",
                valid_user.email_address,
                {"GroupName": "standard-download"},
            ),
            call(
                "admin_add_user_to_group",
                valid_user.email_address,
                {"GroupName": "standard-upload"},
            ),
            call(
                "admin_update_user_attributes",
                valid_user.email_address,
                {
                    "UserAttributes": [
                        {"Name": "custom:is_la", "Value": "0"},
                        {"Name": "name", "Value": "newname"},
                        {"Name": "phone_number", "Value": "+441234567890"},
                        {"Name": "phone_number_verified", "Value": "false"},
                    ]
                },
            ),
        ]
        mocked_send.assert_has_calls(expected_calls)


def test_update_will_not_change_group_if_unchanged(
    valid_user, admin_get_user, user_details_response, group_result
):
    make_request_results = [
        admin_get_user,
        user_details_response,
        group_result,
        True,
        True,
    ]
    with patch("user.make_request", side_effect=make_request_results) as mocked_send:
        assert valid_user.update(
            "new name", "+441234567890", "web-app-prod-data", "0", "standard-download"
        )
        expected_calls = [
            call("admin_get_user", valid_user.email_address),
            call("admin_list_groups_for_user", valid_user.email_address, {}, True),
            call(
                "admin_update_user_attributes",
                valid_user.email_address,
                {
                    "UserAttributes": [
                        {"Name": "custom:is_la", "Value": "0"},
                        {"Name": "name", "Value": "newname"},
                        {"Name": "phone_number", "Value": "+441234567890"},
                        {"Name": "phone_number_verified", "Value": "false"},
                    ]
                },
            ),
        ]
        mocked_send.assert_has_calls(expected_calls)


def test_set_mfa_preferences(valid_user):
    with patch("user.make_request") as mocked_send:
        valid_user.set_mfa_preferences()
        expected_additional_args = {
            "SMSMfaSettings": {"Enabled": True, "PreferredMfa": True},
        }
        mocked_send.assert_called_with(
            "admin_set_user_mfa_preference",
            valid_user.email_address,
            expected_additional_args,
        )


def test_set_user_settings(valid_user):
    with patch("user.make_request") as mocked_send:
        valid_user.set_user_settings()
        expected_additional_args = {
            "MFAOptions": [{"DeliveryMedium": "SMS", "AttributeName": "phone_number"}],
        }
        mocked_send.assert_called_with(
            "admin_set_user_settings",
            valid_user.email_address,
            expected_additional_args,
        )


def test_add_to_group(valid_user):
    # Returns false if invalid group included
    assert not valid_user.add_to_group("not_a_group")
    with patch("user.make_request") as mocked_send:
        mocked_send.return_value = True
        # Defaults to 'standard-download' if no group included
        valid_user.add_to_group()
        expected_additional_args = {
            "GroupName": "standard-download",
        }
        mocked_send.assert_called_with(
            "admin_add_user_to_group",
            valid_user.email_address,
            expected_additional_args,
        )
        # For all valid groups
        for group_name in [
            "standard-download",
            "standard-upload",
            "admin-view",
            "admin-power",
            "admin-full",
        ]:
            valid_user.add_to_group(group_name)
            expected_additional_args = {
                "GroupName": group_name,
            }
            mocked_send.assert_called_with(
                "admin_add_user_to_group",
                valid_user.email_address,
                expected_additional_args,
            )


def test_user_paths_are_valid_returns_false_if_not_admin_and_path_is_blank(valid_user):
    assert not valid_user.user_paths_are_valid("1", "", "standard-download")
    assert not valid_user.user_paths_are_valid("1", "", "standard-upload")


def test_user_paths_are_valid_non_la_users_can_only_get_non_la_paths(
    monkeypatch, valid_user
):
    assert valid_user.user_paths_are_valid(
        "0", "web-app-prod-data", "standard-download"
    )
    monkeypatch.setenv("BUCKET_MAIN_PREFIX", "ambridge")
    assert not valid_user.user_paths_are_valid(
        "0", "web-app-prod-data;ambridge/local_authority/", "standard-download"
    )


def test_user_paths_are_valid_la_users_can_only_get_la_paths(monkeypatch, valid_user):
    monkeypatch.setenv("BUCKET_MAIN_PREFIX", "ambridge")
    assert valid_user.user_paths_are_valid(
        "1", "ambridge/local_authority/", "standard-download"
    )

    assert not valid_user.user_paths_are_valid(
        "1", "web-app-prod-data;ambridge/local_authority/", "standard-download"
    )


def test_create_returns_false_if_checks_fail(
    monkeypatch, valid_user, user_with_invalid_email
):
    assert not user_with_invalid_email.create(
        "justin", "0201234567890", "web-app-prod-data", "0", "standard-download"
    )
    assert not valid_user.create(
        "justin", "not_a_phone_number", "web-app-prod-data", "0", "standard-download"
    )
    assert not valid_user.create(
        "justin", "not_a_phone_number", "web-app-prod-data", "1", "standard-download"
    )


def test_create(monkeypatch, valid_user, create_user_arguments):
    with patch("cognito.make_request") as mocked_cognito_send:
        mocked_cognito_send.return_value = True
        assert valid_user.create(
            "justin", "0201234567890", "web-app-prod-data", "0", "standard-download"
        )


def test_create_when_create_returns_false(
    monkeypatch, valid_user, create_user_arguments
):
    with patch("cognito.make_request") as mocked_cognito_send:
        mocked_cognito_send.return_value = False
        with patch("user.make_request") as mocked_send:
            assert valid_user.create(
                "justin", "0201234567890", "web-app-prod-data", "0", "standard-download"
            )
            mocked_cognito_send.assert_called_with(
                "admin_create_user", valid_user.email_address, create_user_arguments
            )
            expected_calls = [
                call(
                    "admin_set_user_mfa_preference",
                    valid_user.email_address,
                    {"SMSMfaSettings": {"Enabled": True, "PreferredMfa": True}},
                ),
                call(
                    "admin_set_user_settings",
                    valid_user.email_address,
                    {
                        "MFAOptions": [
                            {"DeliveryMedium": "SMS", "AttributeName": "phone_number"}
                        ]
                    },
                ),
                call(
                    "admin_add_user_to_group",
                    valid_user.email_address,
                    {"GroupName": "standard-download"},
                ),
            ]
            mocked_send.assert_has_calls(expected_calls)


def test_reinvite(monkeypatch, valid_user, user_details_response):
    with patch.object(User, "get_details", return_value=user_details_response):
        with patch.object(User, "delete", return_value=True):
            with patch.object(User, "create", return_value=True):
                assert valid_user.reinvite()


def test_reinvite_returns_false_if_user_does_not_exist(monkeypatch, valid_user):
    with patch.object(User, "get_details", return_value={}):
        assert not valid_user.reinvite()


def test_reinvite_returns_false_if_user_exists_but_cannot_be_deleted(
    monkeypatch, valid_user
):
    with patch.object(User, "get_details", return_value={}):
        with patch.object(User, "delete", return_value=False):
            assert not valid_user.reinvite()


def test_reinvite_returns_false_if_user_exists_can_be_deleted_but_cannot_be_created(
    monkeypatch, valid_user
):
    with patch.object(User, "get_details", return_value={}):
        with patch.object(User, "delete", return_value=True):
            with patch.object(User, "create", return_value=False):
                assert not valid_user.reinvite()


def test_list(
    monkeypatch,
    list_users_arguments,
    list_users_response,
    group_result,
    list_users_result,
):
    with patch("user.make_request") as mocked_send:
        with patch.object(User, "group", return_value=group_result):
            mocked_send.return_value = list_users_response
            users = User.list()
            assert users == list_users_result
            mocked_send.assert_called_with("list_users", "", list_users_arguments, True)


def test_list_includes_arguments(
    monkeypatch,
    list_users_arguments,
    list_users_response,
    group_result,
    list_users_result,
):
    with patch("user.make_request") as mocked_send:
        with patch.object(User, "group", return_value=group_result):
            list_users_response.update({"PaginationToken": "new-token"})
            mocked_send.return_value = list_users_response
            users = User.list("test-email", "some-token", 30)
            list_users_result.update({"token": "new-token"})
            assert users == list_users_result
            list_users_arguments.update(
                {
                    "Filter": 'email ^= "test-email"',
                    "PaginationToken": "some-token",
                    "Limit": 30,
                }
            )
            mocked_send.assert_called_with("list_users", "", list_users_arguments, True)


def test_group_returns_default_group_if_none_returned(
    monkeypatch, valid_user, group_result
):
    with patch("user.make_request") as mocked_send:
        mocked_send.return_value = {}
        group = User.group("username")
        assert group == group_result
        mocked_send.assert_called_with(
            "admin_list_groups_for_user", "username", {}, True
        )


def test_group_returns_correct_group(monkeypatch, valid_user):
    with patch("user.make_request") as mocked_send:
        expected_results = [
            {
                "name": "standard-download",
                "preference": 10,
                "display": "Standard download user",
            },
            {
                "name": "standard-upload",
                "preference": 20,
                "display": "Standard download and upload user",
            },
            {
                "name": "admin-view",
                "preference": 70,
                "display": "User administrator read-only",
            },
            {
                "name": "admin-power",
                "preference": 80,
                "display": "User administrator power (reinvite/disable)",
            },
            {
                "name": "admin-full",
                "preference": 90,
                "display": "User administrator full access",
            },
        ]
        for result in expected_results:
            response = {"Groups": [{"GroupName": result["name"]}]}
            mocked_send.return_value = response
            group = User.group("username")
            assert group == {
                "preference": result["preference"],
                "value": result["name"],
                "display": result["display"],
            }
            mocked_send.assert_called_with(
                "admin_list_groups_for_user", "username", {}, True
            )
