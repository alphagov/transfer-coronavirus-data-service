from unittest.mock import patch

import pytest
from werkzeug.datastructures import ImmutableMultiDict

from admin import (
    parse_edit_form_fields,
    perform_cognito_task,
    remove_invalid_user_paths,
    requested_path_matches_user_type,
)
from helpers import body_has_element_with_attributes, flatten_html
from main import app


@pytest.mark.usefixtures("admin_user")
@pytest.mark.usefixtures("user_confirm_form")
@pytest.mark.usefixtures("test_client")
@pytest.mark.usefixtures("test_session")
@pytest.mark.usefixtures("user_details_response")
@pytest.mark.usefixtures("test_admin_session")
@pytest.mark.usefixtures("update_admin_user")
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


def test_perform_cognito_task(admin_user):
    with patch("admin.User.create") as mocked_user_get_details:
        mocked_user_get_details.return_value = True
        assert perform_cognito_task("confirm-new", admin_user)


# ROUTE tests - The flask routes are actually defined in main.py
# but the route functions are delegated to the admin module
# so they seem to fit better in here.


def test_route_admin(test_client, test_admin_session):
    with test_client.session_transaction() as client_session:
        client_session.update(test_admin_session)

    response = test_client.get("/admin")
    body = response.data.decode()
    assert response.status_code == 200
    assert '<h1 class="govuk-heading-l">User administration</h1>' in body


def test_route_admin_user(
    test_client, test_admin_session, admin_user, user_details_response
):
    with test_client.session_transaction() as client_session:
        client_session.update(test_admin_session)
        client_session["admin_user_object"] = admin_user
        client_session["admin_user_email"] = admin_user["email"]

    with patch("admin.User.get_details") as mocked_user_get_details:
        mocked_user_get_details.return_value = user_details_response
        response = test_client.post("/admin/user", data={"task": "view"})
        body = response.data.decode()
        flat = flatten_html(body)
        assert response.status_code == 200
        assert '<h1 class="govuk-heading-l">Manage user</h1>' in body
        assert 'id="user_email">' + admin_user["email"] + "<" in flat


def test_route_admin_user_edit(
    test_client, test_admin_session, admin_user, user_details_response
):
    with test_client.session_transaction() as client_session:
        client_session.update(test_admin_session)
        client_session["admin_user_object"] = admin_user
        client_session["admin_user_email"] = admin_user["email"]

    with patch("admin.User.get_details") as mocked_user_get_details:
        mocked_user_get_details.return_value = user_details_response
        response = test_client.post("/admin/user/edit", data={"task": "edit"})
        body = response.data.decode()
        assert response.status_code == 200
        assert '<h1 class="govuk-heading-l">Edit user</h1>' in body
        assert body_has_element_with_attributes(
            body, {"name": "email", "value": admin_user["email"]}
        )
        assert body_has_element_with_attributes(
            body, {"name": "telephone-number", "value": admin_user["phone_number"]}
        )


def test_route_admin_confirm_user_confirm_new(
    test_client, test_admin_session, admin_user, user_details_response
):
    with test_client.session_transaction() as client_session:
        client_session.update(test_admin_session)
        client_session["admin_user_object"] = admin_user
        client_session["admin_user_email"] = admin_user["email"]

    with patch("admin.User.create") as mocked_user_create:
        mocked_user_create.return_value = True
        with patch("admin.User.get_details") as mocked_user_get_details:
            mocked_user_get_details.return_value = user_details_response
            response = test_client.post(
                "/admin/user/confirm",
                data={"task": "confirm-new"},
                follow_redirects=True,
            )
            assert response.status_code == 200
            body = response.data.decode()
            assert "Created successfully" in body
            mocked_user_create.assert_called_with(
                "Justin Casey",
                "+447123456789",
                admin_user["custom:paths"],
                "1",
                "standard-download",
            )


def test_route_admin_confirm_user_confirm_existing(
    test_client, test_admin_session, update_admin_user, user_details_response
):
    with test_client.session_transaction() as client_session:
        client_session.update(test_admin_session)
        client_session["admin_user_object"] = update_admin_user
        client_session["admin_user_email"] = update_admin_user["email"]

    with patch("admin.User.update") as mocked_user_update:
        with patch("admin.User.get_details") as mocked_user_get_details:
            mocked_user_get_details.return_value = user_details_response
            mocked_user_update.return_value = True
            response = test_client.post(
                "/admin/user/confirm",
                data={"task": "confirm-existing"},
                follow_redirects=True,
            )
            assert response.status_code == 200
            body = response.data.decode()
            assert "Updated successfully" in body
            mocked_user_update.assert_called_with(
                "Justine Hindsight",
                "+447987654321",
                "web-app-prod-data/local_authority/newham",
                "1",
                "standard-upload",
            )


def test_route_admin_reinvite_user_can_reinvite(
    test_client, test_admin_session, update_admin_user, user_details_response
):
    with test_client.session_transaction() as client_session:
        client_session.update(test_admin_session)
        client_session["admin_user_object"] = update_admin_user
        client_session["admin_user_email"] = update_admin_user["email"]

    with patch("admin.User.reinvite") as mocked_user_reinvite:
        with patch("admin.User.get_details") as mocked_user_get_details:
            mocked_user_get_details.return_value = user_details_response
            mocked_user_reinvite.return_value = True
            response = test_client.post(
                "/admin/user/reinvite",
                data={"task": "do-reinvite-user"},
                follow_redirects=True,
            )
            assert response.status_code == 200
            body = response.data.decode()
            assert "Reinvited successfully" in body
            mocked_user_reinvite.assert_called()


def test_route_admin_reinvite_user(
    test_client, test_admin_session, update_admin_user, user_details_response
):
    with test_client.session_transaction() as client_session:
        client_session.update(test_admin_session)
        client_session["admin_user_object"] = update_admin_user
        client_session["admin_user_email"] = update_admin_user["email"]

    response = test_client.post("/admin/user/reinvite", follow_redirects=True,)
    assert response.status_code == 200
    body = response.data.decode()
    assert "Are you sure you want to reinvite" in body


def test_route_admin_enable_user_can_enable(
    test_client, test_admin_session, update_admin_user, user_details_response
):
    with test_client.session_transaction() as client_session:
        client_session.update(test_admin_session)
        client_session["admin_user_object"] = update_admin_user
        client_session["admin_user_email"] = update_admin_user["email"]

    with patch("admin.User.enable") as mocked_user_enable:
        with patch("admin.User.get_details") as mocked_user_get_details:
            mocked_user_get_details.return_value = user_details_response
            mocked_user_enable.return_value = True
            response = test_client.post(
                "/admin/user/enable",
                data={"task": "do-enable-user"},
                follow_redirects=True,
            )
            assert response.status_code == 200
            body = response.data.decode()
            assert "Enabled successfully" in body
            mocked_user_enable.assert_called()


def test_route_admin_enable_user(
    test_client, test_admin_session, update_admin_user, user_details_response
):
    with test_client.session_transaction() as client_session:
        client_session.update(test_admin_session)
        client_session["admin_user_object"] = update_admin_user
        client_session["admin_user_email"] = update_admin_user["email"]

    response = test_client.post("/admin/user/enable", follow_redirects=True,)
    assert response.status_code == 200
    body = response.data.decode()
    assert "Are you sure you want to enable" in body


def test_route_admin_enable_user_can_disable(
    test_client, test_admin_session, update_admin_user, user_details_response
):
    with test_client.session_transaction() as client_session:
        client_session.update(test_admin_session)
        client_session["admin_user_object"] = update_admin_user
        client_session["admin_user_email"] = update_admin_user["email"]

    with patch("admin.User.disable") as mocked_user_disable:
        with patch("admin.User.get_details") as mocked_user_get_details:
            mocked_user_get_details.return_value = user_details_response
            mocked_user_disable.return_value = True
            response = test_client.post(
                "/admin/user/disable",
                data={"task": "do-disable-user"},
                follow_redirects=True,
            )
            assert response.status_code == 200
            body = response.data.decode()
            assert "Disabled successfully" in body
            mocked_user_disable.assert_called()


def test_route_admin_disable_user(
    test_client, test_admin_session, update_admin_user, user_details_response
):
    with test_client.session_transaction() as client_session:
        client_session.update(test_admin_session)
        client_session["admin_user_object"] = update_admin_user
        client_session["admin_user_email"] = update_admin_user["email"]

    response = test_client.post("/admin/user/disable", follow_redirects=True,)
    assert response.status_code == 200
    body = response.data.decode()
    assert "Are you sure you want to disable" in body


def test_route_admin_enable_user_can_delete(
    test_client, test_admin_session, update_admin_user, user_details_response
):
    with test_client.session_transaction() as client_session:
        client_session.update(test_admin_session)
        client_session["admin_user_object"] = update_admin_user
        client_session["admin_user_email"] = update_admin_user["email"]

    with patch("admin.User.delete") as mocked_user_delete:
        with patch("admin.User.get_details") as mocked_user_get_details:
            mocked_user_get_details.return_value = user_details_response
            mocked_user_delete.return_value = True
            response = test_client.post(
                "/admin/user/delete",
                data={"task": "do-delete-user"},
                follow_redirects=True,
            )
            assert response.status_code == 200
            body = response.data.decode()
            # Successful deletes take the user to the admin index page
            assert "User administration" in body
            mocked_user_delete.assert_called()


def test_route_admin_delete_user(
    test_client, test_admin_session, update_admin_user, user_details_response
):
    with test_client.session_transaction() as client_session:
        client_session.update(test_admin_session)
        client_session["admin_user_object"] = update_admin_user
        client_session["admin_user_email"] = update_admin_user["email"]

    response = test_client.post("/admin/user/delete", follow_redirects=True,)
    assert response.status_code == 200
    body = response.data.decode()
    assert "Are you sure you want to delete" in body


def test_admin_routes_redirect_if_do_not_have_permission(test_client, test_session):
    with test_client.session_transaction() as client_session:
        client_session.update(test_session)
        client_session["admin_user_object"] = test_session
        client_session["admin_user_email"] = test_session["email"]

    paths = [
        "admin/user",
        "/admin/user/delete",
        "/admin/user/disable",
        "/admin/user/enable",
        "/admin/user/reinvite",
        "/admin/user/confirm",
        "/admin/user/edit",
    ]
    for path in paths:
        response = test_client.post(path, follow_redirects=True)
        assert response.status_code == 403
        body = response.data.decode()
        assert "User not authorised to access this route" in body


def test_admin_routes_redirect_if_not_logged_in(test_client):
    with test_client.session_transaction() as client_session:
        client_session.clear()

    paths = [
        "admin/user",
        "/admin/user/delete",
        "/admin/user/disable",
        "/admin/user/enable",
        "/admin/user/reinvite",
        "/admin/user/confirm",
        "/admin/user/edit",
    ]
    for path in paths:
        response = test_client.post(path, follow_redirects=True)
        assert response.status_code == 403
        body = response.data.decode()
        assert "User not authorised to access this route" in body
