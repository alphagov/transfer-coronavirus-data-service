#!/usr/bin/env python3
# import os

from flask import Flask, escape, redirect, request, session, url_for
from requests.utils import quote

import s3paths
from cognito_groups import get_group_by_name, return_users_group, user_groups
from flask_helpers import render_template_custom
from logger import LOG
from user import User

local_valid_paths_var = []


def _local_valid_paths():
    global local_valid_paths_var
    if local_valid_paths_var == []:
        local_valid_paths_var = s3paths.valid_paths()
    return local_valid_paths_var


def value_paths_by_type(type):
    res = []
    for lvp in _local_valid_paths():
        if lvp["type"] == type:
            res = lvp
            break
    return res


def admin_user(app):
    done = "None"

    email = ""

    if len(request.args) != 0:
        email = request.args.get("email", "")
        done = request.args.get("done", "None")

    if len(request.form) != 0:
        email = request.form.get("email", "")
        done = request.form.get("done", "None")

    if email != "":
        clear_session(app)
    elif "admin_user_email" in session:
        email = session["admin_user_email"]

    if email != "":
        user = User(email)

        if user.get_details() != {}:
            session["admin_user_email"] = user.email_address

            user_group = return_users_group(user)

            return render_template_custom(
                app, "admin/user.html", user=user, user_group=user_group, done=done
            )

    return redirect("/admin/user/not-found")


def admin_user_error(app):
    return render_template_custom(app, "admin/user-error.html")


def sanitise_string(instr):
    return str(escape(instr))


def sanitise_input(args, key):
    if key in args:
        return sanitise_string(args[key])
    return ""


def clear_session(app):
    if "admin_user_email" in session:
        session.pop("admin_user_email")
    if "admin_user_object" in session:
        session.pop("admin_user_object")


def admin_list_users(app):
    return render_template_custom(app, "admin/list-user.html")


def admin_main(app):
    clear_session(app)
    return render_template_custom(app, "admin/index.html")


def admin_confirm_user(app):
    """
    Render the /admin/user/confirm flask route

    This route posts back to the same page and performs the
    user create/updates against cognito.
    """

    # Get the edited user content from the session
    # or initialise as an empty dictionary
    admin_user_object = session.get("admin_user_object", {})
    task = ""
    new_user = False

    # Redirect to admin home if post data missing
    args = request.form
    if len(args) == 0:
        clear_session(app)
        return redirect("/admin")
    elif "task" in args:
        task = args["task"]

    # Sanitise the email address if user edited
    if task in ["new", "continue-new"]:
        new_user = True
        if "email" in args:
            user = User(args["email"])
            if user.email_address_is_valid():
                admin_user_object["email_address"] = user.email_address
            else:
                return redirect(url_for("admin_edit_user"))

    # Handle Cognito create and update user logic
    if task in ["confirm-new", "confirm-existing"]:
        is_task_complete = perform_cognito_task(task, admin_user_object)

        target = "/admin/user/error"
        state = "created" if task == "confirm-new" else "updated"
        if is_task_complete:
            target = "/admin/user?done={}&email={}".format(
                state, quote(admin_user_object["email_address"])
            )
        clear_session(app)
        return redirect(target)

    user = parse_edit_form_fields(args, admin_user_object, app)

    session["admin_user_email"] = user.email_address
    session["admin_user_object"] = user.details

    return render_template_custom(
        app,
        "admin/confirm-user.html",
        user=user,
        new_user=new_user,
        user_group=user.group_dict(),
    )


def parse_edit_form_fields(
    post_fields: dict, admin_user_object: dict, app: Flask
):
    sanitised_fields = {
        "custom_paths": [
            sanitise_string(input_path).replace("&amp;", "&")
            for input_path in post_fields.getlist("custom_paths")
        ]
    }

    for field in post_fields:
        if field != "custom_paths":
            sanitised_fields[field] = sanitise_input(post_fields, field)

    is_local_authority = sanitised_fields["is-la-radio"] == "yes"
    custom_path_multiple = []
    for requested_path in sanitised_fields["custom_paths"]:
        if requested_path_matches_user_type(is_local_authority, requested_path):
            custom_path_multiple.append(requested_path)
        else:
            app.logger.error(
                {
                    "error": "User denied access to requested path",
                    "user": admin_user_object["email_address"],
                    "path": requested_path,
                }
            )

    user = User(post_fields["email"])
    user.from_form(
        sanitised_fields["full-name"],
        sanitised_fields["telephone-number"],
        str.join(";", custom_path_multiple),
        "1" if is_local_authority else "0",
        get_group_by_name(sanitised_fields["account"])
    )
    return user


def requested_path_matches_user_type(
    is_local_authority: bool, requested_path: str
) -> bool:
    is_path_valid = True
    if requested_path == "":
        is_path_valid = False
    elif (not is_local_authority) and "local_authority" in requested_path:
        is_path_valid = False
    elif is_local_authority and ("local_authority" not in requested_path):
        is_path_valid = False
    return is_path_valid


def remove_invalid_user_paths(user: dict) -> dict:
    user_custom_paths = user["custom:paths"].split(";")
    is_local_authority_user = user["custom:is_la"] == "1"
    valid_user_paths = []
    for custom_path in user_custom_paths:
        is_path_valid = requested_path_matches_user_type(
            is_local_authority_user, custom_path
        )
        if is_path_valid:
            valid_user_paths.append(custom_path)

    user["custom:paths"] = ";".join(valid_user_paths)

    return user


def perform_cognito_task(task: str, admin_user_object: dict) -> bool:
    is_task_complete = False
    user = User(admin_user_object["email_address"])

    print(task)
    print(admin_user_object)

    if task == "confirm-new":
        is_task_complete = user.create(
            admin_user_object["name"],
            admin_user_object["phone_number"],
            admin_user_object["custom:paths"],
            admin_user_object["custom:is_la"],
            admin_user_object["group"]["value"]
        )
    elif task == "confirm-existing":
        is_task_complete = user.update(
            admin_user_object["name"],
            admin_user_object["phone_number"],
            admin_user_object["custom:paths"],
            admin_user_object["custom:is_la"],
            admin_user_object["group"]["value"]
        )

    return is_task_complete


def admin_edit_user(app):
    args = request.values
    new_user = False
    user_custom_paths = []

    task = ""
    if "task" in args:
        task = args["task"]

    if task == "new":
        clear_session(app)

        session["admin_user_email"] = ""
        session["admin_user_object"] = {}

    admin_user_email = session["admin_user_email"]
    user = User(admin_user_email)

    # If the user doesn't exist, allow editing of email/username
    # and don't pre-set user account type options.
    if admin_user_email == "" or user.get_details() == {}:
        new_user = True

    return render_template_custom(
        app,
        "admin/edit-user.html",
        user=user,
        new_user=new_user,
        local_authority_download_paths=value_paths_by_type("local_authority"),
        other_download_paths=value_paths_by_type("other"),
        allowed_domains=(User("").allowed_domains() if new_user else []),
        available_groups=user_groups(),
    )


def admin_reinvite_user(app):
    args = request.values

    task = ""
    if "task" in args:
        task = args["task"]

    admin_user_object = session["admin_user_object"]

    if task == "do-reinvite-user":
        email = admin_user_object["email_address"]
        User(email).reinvite()
        clear_session(app)
        session["admin_user_email"] = email
        return redirect("/admin/user?done=reinvited")

    return render_template_custom(
        app,
        "admin/confirm-reinvite.html",
        email=quote(admin_user_object["email_address"]),
        user_email=admin_user_object["email_address"],
    )


def admin_enable_user(app):

    args = request.values

    task = ""
    if "task" in args:
        task = args["task"]

    admin_user_object = session["admin_user_object"]

    if task == "do-enable-user":
        email = admin_user_object["email_address"]
        clear_session(app)
        User(email).enable()
        session["admin_user_email"] = email
        return redirect("/admin/user?done=enabled")

    return render_template_custom(
        app,
        "admin/confirm-enable.html",
        email=quote(admin_user_object["email_address"]),
        user_email=admin_user_object["email_address"],
    )


def admin_disable_user(app):

    args = request.values

    task = ""
    if "task" in args:
        task = args["task"]

    admin_user_object = session["admin_user_object"]

    if task == "do-disable-user":
        email = admin_user_object["email_address"]
        clear_session(app)
        User(email).disable()
        session["admin_user_email"] = email
        return redirect("/admin/user?done=disabled")

    return render_template_custom(
        app,
        "admin/confirm-disable.html",
        email=quote(admin_user_object["email_address"]),
        user_email=admin_user_object["email_address"],
    )


def admin_delete_user(app):

    args = request.values

    task = ""
    if "task" in args:
        task = args["task"]

    admin_user_object = session["admin_user_object"]

    if task == "do-delete-user":
        email = admin_user_object["email_address"]
        clear_session(app)
        User(email).delete()
        return redirect("/admin?done=deleted")

    return render_template_custom(
        app,
        "admin/confirm-delete.html",
        email=quote(admin_user_object["email_address"]),
        user_email=admin_user_object["email_address"],
    )


def admin_user_not_found(app):
    return render_template_custom(app, "error.html", error="User not found")
