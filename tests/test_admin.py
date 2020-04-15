import pytest
from werkzeug.datastructures import ImmutableMultiDict

import stubs
from admin import (
    parse_edit_form_fields,
    perform_cognito_task,
    requested_path_matches_user_type,
)
from main import app


@pytest.mark.usefixtures("admin_user")
@pytest.mark.usefixtures("user_confirm_form")
def test_parse_edit_form_fields(admin_user, user_confirm_form):

    # Check that correct changes are made for valid form data
    user = parse_edit_form_fields(
        ImmutableMultiDict(user_confirm_form), admin_user, app
    )
    assert "web-app-prod-data/local_authority/barnet" in user["custom:paths"]
    assert "web-app-prod-data/local_authority/hackney" in user["custom:paths"]
    assert user["group"]["value"] == "standard-upload"

    # Check that invalid form data is sanitised safely
    dirty_form = {}
    dirty_form.update(user_confirm_form)
    dirty_form["full-name"] = 'Justin Casey"; test'
    user = parse_edit_form_fields(ImmutableMultiDict(dirty_form), admin_user, app)
    assert user["name"] == "Justin Casey&#34;; test"

    # Check that non local authority users are denied access to local authority paths
    invalid_path_form = {}
    invalid_path_form.update(user_confirm_form)
    invalid_path_form["is-la-radio"] = "no"
    user = parse_edit_form_fields(
        ImmutableMultiDict(invalid_path_form), admin_user, app
    )
    assert user["custom:is_la"] == "0"
    assert user["custom:paths"] == ""

    # Check that local authority users are denied access to non local authority paths
    invalid_path_form = {}
    invalid_path_form.update(user_confirm_form)
    invalid_path_form["is-la-radio"] = "yes"
    invalid_path_form["custom_paths"] = ["web-app-prod-data/other/nhs"]
    user = parse_edit_form_fields(
        ImmutableMultiDict(invalid_path_form), admin_user, app
    )
    assert user["custom:is_la"] == "1"
    assert user["custom:paths"] == ""

    # Check that non local authority user can be granted access to NHS data
    valid_nhs_form = {}
    valid_nhs_form.update(user_confirm_form)
    valid_nhs_form["is-la-radio"] = "no"
    valid_nhs_form["custom_paths"] = ["web-app-prod-data/other/nhs"]
    user = parse_edit_form_fields(ImmutableMultiDict(valid_nhs_form), admin_user, app)
    assert user["custom:is_la"] == "0"
    assert user["custom:paths"] == "web-app-prod-data/other/nhs"


def test_requested_path_matches_user_type():

    assert requested_path_matches_user_type(
        True, "web-app-prod-data/local_authority/barnet"
    )
    assert not requested_path_matches_user_type(
        False, "web-app-prod-data/local_authority/barnet"
    )
    assert requested_path_matches_user_type(False, "web-app-prod-data/other/nhs")
    assert not requested_path_matches_user_type(True, "web-app-prod-data/other/nhs")


@pytest.mark.usefixtures("admin_user")
def test_perform_cognito_task(admin_user):
    stubber = stubs.mock_cognito_create_user(admin_user)
    # TODO: stub additional responses in stubs.mock_cognito_create_user
    with stubber:
        assert perform_cognito_task("confirm-new", admin_user)

        stubber.deactivate()
