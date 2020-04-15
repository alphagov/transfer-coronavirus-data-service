#!/usr/bin/env python3
# import os

from flask import Flask, escape, redirect, request, session
from requests.utils import quote

import cognito
import s3paths
from cognito_groups import get_group_by_name, return_users_group, user_groups
from flask_helpers import render_template_custom

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
        user = cognito.get_user_details(email)

        if user != {}:
            session["admin_user_email"] = user["email"]
            session["admin_user_object"] = user

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

    app.logger.debug({"action": "admin_confirm_user", "args:": args})

    # Sanitise the email address if user edited
    if task in ["new", "continue-new"]:
        new_user = True
        if "email" in args:
            admin_user_object["email"] = cognito.sanitise_email(args["email"])

    # Handle Cognito create and update user logic
    if task in ["confirm-new", "confirm-existing"]:
        is_task_complete = perform_cognito_task(task, admin_user_object)

        target = "/admin/user/error"
        state = "created" if task == "confirm-new" else "updated"
        if is_task_complete:
            target = "/admin/user?done={}&email={}".format(
                state, quote(admin_user_object["email"])
            )
        clear_session(app)
        return redirect(target)

    admin_user_object = parse_edit_form_fields(args, admin_user_object, app)

    session["admin_user_email"] = admin_user_object["email"]
    session["admin_user_object"] = admin_user_object

    return render_template_custom(
        app,
        "admin/confirm-user.html",
        user=admin_user_object,
        new_user=new_user,
        user_group=admin_user_object["group"],
    )


def parse_edit_form_fields(
    post_fields: dict, admin_user_object: dict, app: Flask
) -> dict:

    app.logger.debug(
        {"action": "parse_edit_form_fields", "fields_type": str(type(post_fields))}
    )
    app.logger.debug(
        {
            "action": "parse_edit_form_fields",
            "custom_paths": post_fields.getlist("custom_paths"),
        }
    )
    app.logger.debug({"action": "parse_edit_form_fields", "post_fields": post_fields})
    sanitised_fields = {
        "custom_paths": [
            sanitise_string(input_path).replace("&amp;", "&")
            for input_path in post_fields.getlist("custom_paths")
        ]
    }

    for field in post_fields:
        if field != "custom_paths":
            sanitised_fields[field] = sanitise_input(post_fields, field)

    admin_user_object["name"] = sanitised_fields["full-name"]
    admin_user_object["phone_number"] = sanitised_fields["telephone-number"]

    is_local_authority = sanitised_fields["is-la-radio"] == "yes"
    user_group = get_group_by_name(sanitised_fields["account"])

    admin_user_object["custom:is_la"] = "1" if is_local_authority else "0"
    admin_user_object["group"] = user_group

    custom_path_multiple = []

    for requested_path in sanitised_fields["custom_paths"]:
        if requested_path_matches_user_type(is_local_authority, requested_path):
            custom_path_multiple.append(requested_path)
        else:
            app.logger.error(
                {
                    "error": "User denied access to requested path",
                    "user": admin_user_object["email"],
                    "path": requested_path,
                }
            )

    admin_user_object["custom:paths"] = str.join(";", custom_path_multiple)
    return admin_user_object


def requested_path_matches_user_type(is_local_authority, requested_path):
    is_path_valid = True

    if not is_local_authority and "local_authority" in requested_path:
        is_path_valid = False
    elif is_local_authority and "local_authority" not in requested_path:
        is_path_valid = False
    return is_path_valid


def perform_cognito_task(task, admin_user_object):
    is_task_complete = False

    if task == "confirm-new":
        is_task_complete = cognito.create_user(admin_user_object)

    elif task == "confirm-existing":
        is_task_complete = cognito.update_user_attributes(admin_user_object)

    return is_task_complete


def admin_edit_user(app):
    args = request.values
    new_user = False
    user_custom_paths = ""

    task = ""
    if "task" in args:
        task = args["task"]

    if task == "new":
        clear_session(app)

        session["admin_user_email"] = ""
        session["admin_user_object"] = {}

    admin_user_email = session["admin_user_email"]
    admin_user_object = session["admin_user_object"]

    # if the user doesn't exist, allow editng of email/userame
    if admin_user_email == "" or cognito.get_user_details(admin_user_email) == {}:
        new_user = True

    if task == "enable":
        return render_template_custom(
            app,
            "admin/confirm-enable.html",
            email=quote(admin_user_object["email"]),
            user_email=admin_user_object["email"],
        )
    if task == "do-enable-user":
        email = admin_user_object["email"]
        clear_session(app)
        cognito.enable_user(email, True)
        session["admin_user_email"] = email
        return redirect("/admin/user?done=enabled")

    if task == "disable":
        return render_template_custom(
            app,
            "admin/confirm-disable.html",
            email=quote(admin_user_object["email"]),
            user_email=admin_user_object["email"],
        )
    if task == "do-disable-user":
        email = admin_user_object["email"]
        clear_session(app)
        cognito.disable_user(email, True)
        session["admin_user_email"] = email
        return redirect("/admin/user?done=disabled")

    if task == "delete":
        return render_template_custom(
            app,
            "admin/confirm-delete.html",
            email=quote(admin_user_object["email"]),
            user_email=admin_user_object["email"],
        )
    if task == "do-delete-user":
        email = admin_user_object["email"]
        clear_session(app)
        cognito.delete_user(email, True)
        return redirect("/admin?done=deleted")

    is_la = False
    is_other = False

    if task != "new":
        user_is_la = admin_user_object["custom:is_la"] == "1"
        user_custom_paths = admin_user_object["custom:paths"].split(";")
        for path_test in user_custom_paths:
            if "/local_authority/" in path_test and user_is_la:
                is_la = True
                break
            else:
                is_other = True

    return render_template_custom(
        app,
        "admin/edit-user.html",
        user=admin_user_object,
        new_user=new_user,
        user_custom_paths=user_custom_paths,
        local_authority=value_paths_by_type("local_authority"),
        is_la=is_la,
        other=value_paths_by_type("other"),
        is_other=is_other,
        allowed_domains=(cognito.allowed_domains() if new_user else []),
        available_groups=user_groups(),
    )


def admin_reinvite_user(app):
    args = request.values

    task = ""
    if "task" in args:
        task = args["task"]

    admin_user_object = session["admin_user_object"]

    if task == "do-reinvite-user":
        email = admin_user_object["email"]
        cognito.reinvite_user(email, True)
        clear_session(app)
        session["admin_user_email"] = email
        return redirect("/admin/user?done=reinvited")

    return render_template_custom(
        app,
        "admin/confirm-reinvite.html",
        email=quote(admin_user_object["email"]),
        user_email=admin_user_object["email"],
    )


def admin_user_not_found(app):
    return "User not found"
