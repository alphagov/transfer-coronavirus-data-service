from unittest.mock import patch

import pytest
import stubs
from werkzeug.datastructures import ImmutableMultiDict

from admin import (
    parse_edit_form_fields,
    perform_cognito_task,
    remove_invalid_user_paths,
    requested_path_matches_user_type,
)
from helpers import body_has_element_with_attributes, flatten_html
from main import app


@pytest.mark.usefixtures("admin_user", "user_confirm_form")
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
    assert not requested_path_matches_user_type(True, "")
    assert not requested_path_matches_user_type(False, "")


@pytest.mark.usefixtures("admin_user")
def test_remove_invalid_user_paths(admin_user):
    granted_paths = admin_user["custom:paths"].split(";")
    granted_paths.sort()
    user = remove_invalid_user_paths(admin_user)
    valid_paths = user["custom:paths"].split(";")
    valid_paths.sort()
    assert granted_paths == valid_paths

    other_path = "web-app-prod-data/other/nhs"
    admin_user["custom:is_la"] = "1"
    invalid_paths = []
    invalid_paths += granted_paths
    invalid_paths.append(other_path)
    admin_user["custom:paths"] = ";".join(invalid_paths)
    user = remove_invalid_user_paths(admin_user)
    assert other_path not in user["custom:paths"]

    admin_user["custom:is_la"] = "0"
    admin_user["custom:paths"] = ";".join(granted_paths)
    user = remove_invalid_user_paths(admin_user)
    assert user["custom:paths"] == ""


@pytest.mark.usefixtures("admin_user")
def test_perform_cognito_task(admin_user):
    with patch("admin.User.create") as mocked_user_get_details:
        mocked_user_get_details.return_value = True
        assert perform_cognito_task("confirm-new", admin_user)


# ROUTE tests - The flask routes are actually defined in main.py
# but the route functions are delegated to the admin module
# so they seem to fit better in here.


@pytest.mark.usefixtures("test_client", "test_admin_session")
def test_route_admin(test_client, test_admin_session):
    with test_client.session_transaction() as client_session:
        client_session.update(test_admin_session)

    response = test_client.get("/admin")
    body = response.data.decode()
    assert response.status_code == 200
    assert '<h1 class="govuk-heading-l">User administration</h1>' in body


@pytest.mark.usefixtures(
    "test_client", "test_admin_session", "admin_user", "admin_get_user"
)
def test_route_admin_user_query(
    test_client, test_admin_session, admin_user, admin_get_user
):
    with test_client.session_transaction() as client_session:
        client_session.update(test_admin_session)

    email = admin_user["email"]
    stubber = stubs.mock_user_get_details(email, admin_get_user)
    with stubber:
        quoted_email = email.replace("@", "%40")
        response = test_client.get(f"/admin/user?email={quoted_email}")
        body = response.data.decode()
        flat = flatten_html(body)
        assert response.status_code == 200
        assert '<h1 class="govuk-heading-l">Manage user</h1>' in body
        assert 'id="user_email">' + admin_user["email"] + "<" in flat
        stubber.deactivate()


@pytest.mark.usefixtures(
    "test_client", "test_admin_session", "admin_user", "admin_get_user"
)
def test_route_admin_user(test_client, test_admin_session, admin_user, admin_get_user):
    with test_client.session_transaction() as client_session:
        client_session.update(test_admin_session)
        client_session["admin_user_object"] = admin_user
        client_session["admin_user_email"] = admin_user["email"]

    email = admin_user["email"]
    stubber = stubs.mock_user_get_details(email, admin_get_user)
    with stubber:
        response = test_client.post("/admin/user", data={"task": "view"})
        body = response.data.decode()
        flat = flatten_html(body)
        assert response.status_code == 200
        assert '<h1 class="govuk-heading-l">Manage user</h1>' in body
        assert 'id="user_email">' + admin_user["email"] + "<" in flat


@pytest.mark.usefixtures(
    "test_client", "test_admin_session", "admin_user", "admin_get_user"
)
def test_route_admin_user_edit(
    test_client, test_admin_session, admin_user, admin_get_user
):
    with test_client.session_transaction() as client_session:
        client_session.update(test_admin_session)
        client_session["admin_user_object"] = admin_user
        client_session["admin_user_email"] = admin_user["email"]

    email = admin_user["email"]
    stubber = stubs.mock_user_get_details(email, admin_get_user)
    with stubber:
        response = test_client.post("/admin/user/edit", data={"task": "edit"})
        body = response.data.decode()
        # flat = flatten_html(body)
        assert response.status_code == 200
        assert '<h1 class="govuk-heading-l">Edit user</h1>' in body
        assert body_has_element_with_attributes(
            body, {"name": "email", "value": admin_user["email"]}
        )
        assert body_has_element_with_attributes(
            body, {"name": "telephone-number", "value": admin_user["phone_number"]}
        )
