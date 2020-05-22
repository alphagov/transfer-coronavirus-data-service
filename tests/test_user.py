import os

import pytest
import stubs

from user import User


def test_user_init_email_sanitised():
    test1 = "anormalemail@example.gov.uk"
    assert User(test1).email_address == test1

    assert User("ANEMAIL@example.gov.uk").email_address == "anemail@example.gov.uk"
    assert User(" anemail@example.gov.uk ").email_address == "anemail@example.gov.uk"


@pytest.mark.usefixtures(
    "valid_user", "user_with_invalid_email", "user_with_invalid_domain"
)
def test_user_email_address_is_valid(
    valid_user, user_with_invalid_email, user_with_invalid_domain
):
    assert valid_user.email_address_is_valid()
    assert not user_with_invalid_email.email_address_is_valid()
    assert not user_with_invalid_domain.email_address_is_valid()


@pytest.mark.usefixtures("valid_user", "user_with_invalid_domain")
def test_allowed_domains_rejects_invalid_domain(valid_user, user_with_invalid_domain):
    assert valid_user.domain_is_allowed()
    assert not user_with_invalid_domain.domain_is_allowed()


@pytest.mark.usefixtures("valid_user")
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


@pytest.mark.usefixtures("user_with_invalid_email")
def test_delete_with_invalid_email(user_with_invalid_email):
    assert not user_with_invalid_email.delete()


@pytest.mark.usefixtures("user_with_invalid_email")
def test_enable_with_invalid_email(user_with_invalid_email):
    assert not user_with_invalid_email.enable()


@pytest.mark.usefixtures("user_with_invalid_email")
def test_disable_with_invalid_email(user_with_invalid_email):
    assert not user_with_invalid_email.disable()


@pytest.mark.usefixtures("valid_user")
def test_sanitise_phone(valid_user):
    assert valid_user.sanitise_phone("+441234567890") == "+441234567890"
    assert valid_user.sanitise_phone("441234567890") == "+441234567890"
    assert valid_user.sanitise_phone("01234567890") == "+441234567890"
    assert valid_user.sanitise_phone("string_prefix01234567890") == "+441234567890"
    assert valid_user.sanitise_phone("notaphonenumber") == ""


@pytest.mark.usefixtures("valid_user")
def test_sanitise_name(valid_user):
    assert valid_user.sanitise_name("joe bloggs") == "joebloggs"
    assert valid_user.sanitise_name("joe_bloggs") == "joe_bloggs"
    assert valid_user.sanitise_name("joe bloggs 2") == "joebloggs2"


@pytest.mark.usefixtures("valid_user")
def test_update_returns_false_if_user_not_found(valid_user):
    email = valid_user.email_address
    stubber = stubs.mock_user_not_found(email)
    with stubber:
        assert not valid_user.update(
            "new name", "+441234567890", "web-app-prod-data", "0", "standard-upload"
        )
        stubber.deactivate()


@pytest.mark.usefixtures("valid_user", "admin_get_user")
def test_update_returns_false_if_new_details_are_all_none(valid_user, admin_get_user):
    email = valid_user.email_address
    attributes = {
        "name": None,
        "phone_number": None,
        "custom:paths": None,
        "custom:is_la": None,
    }
    stubber = stubs.mock_user_update(email, admin_get_user, attributes)
    with stubber:
        assert not valid_user.update(None, None, None, None, None)
        stubber.deactivate()


@pytest.mark.usefixtures("valid_user", "admin_get_user")
def test_update_returns_false_if_new_details_are_not_strings(
    valid_user, admin_get_user
):
    email = valid_user.email_address
    attributes = {
        "name": 1,
        "phone_number": 2,
        "custom:paths": 3,
        "custom:is_la": 4,
    }
    stubber = stubs.mock_user_update(email, admin_get_user, attributes)
    with stubber:
        assert not valid_user.update(0, 1, 2, 3, 4)
        stubber.deactivate()


@pytest.mark.usefixtures("valid_user")
def test_user_paths_are_valid_returns_false_if_not_admin_and_path_is_blank(valid_user):
    assert not valid_user.user_paths_are_valid("1", "", "standard-download")
    assert not valid_user.user_paths_are_valid("1", "", "standard-upload")
    assert not valid_user.user_paths_are_valid("0", "", "standard-download")
    assert not valid_user.user_paths_are_valid("0", "", "standard-upload")


@pytest.mark.usefixtures("valid_user")
def test_user_paths_are_valid_non_la_users_can_only_get_non_la_paths(valid_user):
    main_prefix = os.environ.get("BUCKET_MAIN_PREFIX")
    assert valid_user.user_paths_are_valid(
        "0", f"{main_prefix}/other/gds", "standard-download"
    )
    assert valid_user.user_paths_are_valid(
        "0", f"{main_prefix}/other/gds;{main_prefix}/other/nhs", "standard-download"
    )

    assert not valid_user.user_paths_are_valid(
        "0", f"{main_prefix}/local_authority/barking", "standard-download"
    )
    assert not valid_user.user_paths_are_valid(
        "0",
        f"{main_prefix}/local_authority/barking;{main_prefix}/other/gds",
        "standard-download",
    )


@pytest.mark.usefixtures("valid_user")
def test_user_paths_are_valid_la_users_can_only_get_la_paths(valid_user):
    main_prefix = os.environ.get("BUCKET_MAIN_PREFIX")
    assert valid_user.user_paths_are_valid(
        "1", f"{main_prefix}/local_authority/barking", "standard-download"
    )

    assert valid_user.user_paths_are_valid(
        "1",
        f"{main_prefix}/local_authority/barking;{main_prefix}/local_authority/barnet",
        "standard-download",
    )

    assert not valid_user.user_paths_are_valid(
        "1", f"{main_prefix}/other/gds", "standard-download"
    )
    assert not valid_user.user_paths_are_valid(
        "1",
        f"{main_prefix}/other/gds;{main_prefix}/local_authority/barking",
        "standard-download",
    )


@pytest.mark.usefixtures("valid_user", "user_with_invalid_email")
def test_create_returns_false_if_checks_fail(valid_user, user_with_invalid_email):
    main_prefix = os.environ.get("BUCKET_MAIN_PREFIX")
    assert not user_with_invalid_email.create(
        "justin", "0201234567890", f"{main_prefix}/other/gds", "0", "standard-download"
    )
    assert not valid_user.create(
        "justin",
        "not_a_phone_number",
        f"{main_prefix}/other/gds",
        "0",
        "standard-download",
    )
    assert not valid_user.create(
        "justin",
        "not_a_phone_number",
        f"{main_prefix}/other/gds",
        "1",
        "standard-download",
    )


@pytest.mark.usefixtures("admin_user", "create_user_arguments")
def test_user_create_user(admin_user, create_user_arguments):
    group_name = admin_user["group"]["value"]
    stubber = stubs.mock_cognito_create_user(admin_user, create_user_arguments)

    with stubber:
        test_user = User(admin_user["email"])
        assert test_user.create(
            admin_user["name"],
            admin_user["phone_number"],
            admin_user["custom:paths"],
            admin_user["custom:is_la"],
            group_name,
        )
        stubber.deactivate()


@pytest.mark.usefixtures("admin_user", "create_user_arguments")
def test_creating_invalid_phone_number(admin_user, create_user_arguments):
    group_name = admin_user["group"]["value"]
    stubber = stubs.mock_cognito_create_user(admin_user, create_user_arguments)

    with stubber:
        test_user = User(admin_user["email"])
        assert not test_user.create(
            admin_user["name"],
            "",
            admin_user["custom:paths"],
            admin_user["custom:is_la"],
            group_name,
        )
        stubber.deactivate()


@pytest.mark.usefixtures(
    "valid_user", "admin_user", "admin_get_user", "create_user_arguments"
)
def test_user_reinvite_valid_user_success(
    valid_user, admin_user, admin_get_user, create_user_arguments
):
    stubber = stubs.mock_user_reinvite(
        admin_user, admin_get_user, create_user_arguments
    )
    with stubber:
        assert valid_user.reinvite()
        stubber.deactivate()


@pytest.mark.usefixtures("valid_user", "admin_user")
def test_user_reinvite_user_not_found_fail(valid_user, admin_user):
    stubber = stubs.mock_user_not_found(admin_user["email"])
    with stubber:
        assert not valid_user.reinvite()
        stubber.deactivate()


@pytest.mark.usefixtures("valid_user", "admin_user", "admin_get_user")
def test_reinvite_delete_user_fails(valid_user, admin_user, admin_get_user):
    stubber = stubs.mock_delete_user_failure(admin_user, admin_get_user)
    with stubber:
        assert not valid_user.reinvite()
        stubber.deactivate()


@pytest.mark.usefixtures(
    "valid_user", "admin_user", "admin_get_user", "create_user_arguments"
)
def test_reinvite_create_user_fails(
    valid_user, admin_user, admin_get_user, create_user_arguments
):
    stubber = stubs.mock_create_user_failure(
        admin_user, admin_get_user, create_user_arguments
    )
    with stubber:
        assert not valid_user.reinvite()
        stubber.deactivate()
