#!/usr/bin/env python3
# import os

from flask import escape, redirect, request, session
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


def get_session_obj(id):
    if id in session:
        return session[id]
    return None


def admin_list_users(app):
    return render_template_custom(app, "admin/list-user.html")


def admin_main(app):
    clear_session(app)
    return render_template_custom(app, "admin/index.html")


def admin_confirm_user(app):

    admin_user_object = get_session_obj("admin_user_object")

    task = ""
    args = request.form
    if len(args) == 0:
        clear_session(app)
        return redirect("/admin")
    elif "task" in args:
        task = args["task"]

    app.logger.debug("admin_confirm_user:task:", task)

    user = {}
    new_user = False

    app.logger.debug("admin_confirm_user:args:", args)

    if task in ["new", "continue-new"]:
        new_user = True
        if "email" in args:
            user = {"email": cognito.sanitise_email(args["email"])}

    app.logger.debug("admin_confirm_user:user1:", user)

    if user == {}:
        user = admin_user_object

    app.logger.debug("admin_confirm_user:user2:", user)

    if "frompage" in args:
        if "self" == args["frompage"]:

            state = ""

            if task == "confirm-new":
                response = cognito.create_user(admin_user_object)
                state = "created"

            elif task == "confirm-existing":
                response = cognito.update_user_attributes(admin_user_object)
                state = "updated"
            else:
                session["admin_user_object"] = admin_user_object
                return redirect("/admin/user/edit")

            clear_session(app)

            if response:
                return redirect(
                    "/admin/user?done={}&email={}".format(state, quote(admin_user_object["email"]))
                )
            else:
                return redirect("/admin/user/error")

        return redirect("/admin/user/error")

    user["name"] = sanitise_input(args, "full-name")
    user["phone_number"] = sanitise_input(args, "telephone-number")

    account_type = sanitise_input(args, "account")
    # user_group = return_users_group({"group": account_type})
    user_group = get_group_by_name(account_type)
    user["group"] = user_group

    san_is_la = sanitise_input(args, "is-la-radio") == "yes"
    if san_is_la:
        user["custom:is_la"] = "1"
    else:
        user["custom:is_la"] = "0"

    custom_path_multiple = []
    for tmp_arg in args.getlist("custom_paths"):
        if not san_is_la and "local_authority" in tmp_arg:
            app.logger.error("NOT san_is_la and LA in path:{}".format(tmp_arg))
        elif san_is_la and "local_authority" not in tmp_arg:
            app.logger.error("san_is_la and not LA in path:{}".format(tmp_arg))
        else:
            custom_path_multiple.append(sanitise_string(tmp_arg).replace("&amp;", "&"))

    user["custom:paths"] = str.join(";", custom_path_multiple)

    session["admin_user_email"] = user["email"]
    session["admin_user_object"] = user

    return render_template_custom(
        app,
        "admin/confirm-user.html",
        user=user,
        new_user=new_user,
        user_group=user_group,
    )


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

    if task == "reinvite":
        return render_template_custom(
            app,
            "admin/confirm-reinvite.html",
            email=quote(admin_user_object["email"]),
            user_email=admin_user_object["email"],
        )
    if task == "do-reinvite-user":
        email = admin_user_object["email"]
        cognito.reinvite_user(email, True)
        clear_session(app)
        session["admin_user_email"] = email
        return redirect("/admin/user?done=reinvited")

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


def admin_user_not_found(app):
    return "User not found"
