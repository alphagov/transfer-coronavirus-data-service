#!/usr/bin/env python3
# import os

from flask import escape, redirect, request, session
from requests.utils import quote

import cognito
import s3paths
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
            session["admin_user_action"] = "view"
            session["admin_user_email"] = user["email"]
            session["admin_user_object"] = user

            return render_template_custom(app, "admin/user.html", user=user, done=done)

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
    if "admin_user_action" in session:
        session.pop("admin_user_action")
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
    return render_template_custom(app, "admin/index.html")


def admin_confirm_user(app):

    admin_user_action = get_session_obj("admin_user_action")
    admin_user_object = get_session_obj("admin_user_object")

    args = request.form

    user = {}
    new_user = False

    if admin_user_action == "new" or admin_user_action == "edit-new":
        new_user = True
        if "email" in args:
            user = {"email": cognito.sanitise_email(args["email"])}
        else:
            user = {"email": ""}
        print(user)

    elif admin_user_action == "edit-existing":
        new_user = False
        user = admin_user_object

    elif admin_user_action == "confirm-new":
        new_user = True
        user = admin_user_object

    elif admin_user_action == "confirm-existing":
        new_user = False
        user = admin_user_object

    if "frompage" in args and "action" in args:
        if "self" == args["frompage"]:

            if args["action"] == "confirm" and new_user:
                email = admin_user_object["email"]
                create_res = cognito.create_user(
                    name=admin_user_object["name"],
                    email_address=email,
                    phone_number=admin_user_object["phone_number"],
                    attr_paths=admin_user_object["custom:paths"],
                    is_la=admin_user_object["custom:is_la"],
                )

                clear_session(app)

                if create_res:
                    return redirect(
                        "/admin/user?done=created&email={}".format(quote(email))
                    )
                else:
                    return redirect("/admin/user/error")

            if args["action"] == "confirm" and not new_user:
                email = admin_user_object["email"]
                update_res = cognito.update_user_attributes(
                    email_address=email,
                    new_name=admin_user_object["name"],
                    new_phone_number=admin_user_object["phone_number"],
                    new_paths=admin_user_object["custom:paths"].split(";"),
                    new_is_la=admin_user_object["custom:is_la"],
                )

                clear_session(app)

                if update_res:
                    return redirect(
                        "/admin/user?done=updated&email={}".format(quote(email))
                    )
                else:
                    return redirect("/admin/user/error")

            else:
                session["admin_user_action"] = (
                    "edit-new" if new_user else "edit-existing"
                )
                session["admin_user_object"] = admin_user_object
                return redirect("/admin/user/edit")

        return redirect("/admin/user/error")

    user["name"] = sanitise_input(args, "full-name")
    user["phone_number"] = sanitise_input(args, "telephone-number")

    san_is_la = sanitise_input(args, "is-la-radio")
    if san_is_la == "yes":
        user["custom:is_la"] = "1"
    elif san_is_la == "no":
        user["custom:is_la"] = "0"

    custom_paths_radio = sanitise_input(args, "custom_paths_radio")
    custom_path_multiple = []
    for tmp_arg in args.getlist("custom_paths"):
        if tmp_arg.startswith(custom_paths_radio):
            custom_path_multiple.append(sanitise_string(tmp_arg).replace("&amp;", "&"))

    print("-" * 20)
    print("CUSTOM_PATHS_RADIO", custom_paths_radio)
    print("CUSTOM_PATH_MULTIPLE", custom_path_multiple)
    print("-" * 20)

    if len(custom_path_multiple) != 0:
        user["custom:paths"] = str.join(";", custom_path_multiple)
    else:
        user["custom:paths"] = ""

    print(user)
    print("=" * 20)

    session["admin_user_action"] = "confirm-{}".format(
        "new" if new_user else "existing"
    )

    session["admin_user_email"] = user["email"]
    session["admin_user_object"] = user

    return render_template_custom(
        app, "admin/confirm-user.html", user=user, new_user=new_user
    )


def admin_edit_user(app):
    args = request.form
    user = {}
    enable_email_edit = False

    if len(args) == 0:
        return redirect("/admin")

    # print(args)

    if "task" in args:
        if args["task"] == "goto-view":
            session["admin_user_action"] = "view"
            return redirect("/admin/user")

        if args["task"] == "new":
            clear_session(app)

            user = {}
            user_custom_paths = ""
            # new user so allow email edit
            enable_email_edit = True

            session["admin_user_action"] = "new"
            session["admin_user_email"] = ""
            session["admin_user_object"] = {}

    admin_user_action = get_session_obj("admin_user_action")
    admin_user_email = get_session_obj("admin_user_email")
    admin_user_object = get_session_obj("admin_user_object")

    if admin_user_email != "":
        try:
            user = cognito.get_user_details(admin_user_email)
        except cognito.CognitoException as e:
            app.logger.err(e)
        if user == {}:
            return redirect("/admin/user/not-found")

    if "task" in args:
        if args["task"] == "reinvite":
            session["admin_user_action"] = "reinvite"
            return render_template_custom(
                app,
                "admin/confirm-reinvite.html",
                email=quote(user["email"]),
                user_email=user["email"],
            )
        if args["task"] == "do-reinvite-user":
            email = user["email"]
            clear_session(app)
            cognito.reinvite_user(email, True)
            session["admin_user_action"] = "view"
            session["admin_user_email"] = email
            return redirect("/admin/user?done=reinvited")

        if args["task"] == "enable":
            session["admin_user_action"] = "enable"
            return render_template_custom(
                app,
                "admin/confirm-enable.html",
                email=quote(user["email"]),
                user_email=user["email"],
            )
        if args["task"] == "do-enable-user":
            email = user["email"]
            print(email)
            cognito.enable_user(email, True)
            clear_session(app)
            session["admin_user_action"] = "view"
            session["admin_user_email"] = email
            return redirect("/admin/user?done=enabled")

        if args["task"] == "disable":
            session["admin_user_action"] = "disable"
            return render_template_custom(
                app,
                "admin/confirm-disable.html",
                email=quote(user["email"]),
                user_email=user["email"],
            )
        if args["task"] == "do-disable-user":
            email = user["email"]
            cognito.disable_user(email, True)
            clear_session(app)
            session["admin_user_action"] = "view"
            session["admin_user_email"] = email
            return redirect("/admin/user?done=disabled")

        if args["task"] == "delete":
            session["admin_user_action"] = "delete"
            return render_template_custom(
                app,
                "admin/confirm-delete.html",
                email=quote(user["email"]),
                user_email=user["email"],
            )
        if args["task"] == "do-delete-user":
            email = user["email"]
            cognito.delete_user(email, True)
            clear_session(app)
            return redirect("/admin?done=deleted")

        if args["task"] == "edit":
            session["admin_user_action"] = "edit-existing"
            session["admin_user_object"] = user
            admin_user_action = "edit-existing"
            enable_email_edit = False

    elif admin_user_action == "edit-new":
        user = admin_user_object
        user_custom_paths = user["custom:paths"]
        enable_email_edit = True

    elif admin_user_action == "edit-existing":
        user = admin_user_object
        user_custom_paths = user["custom:paths"]
        enable_email_edit = False

    elif admin_user_action == "edit-new":
        user = admin_user_object
        user_custom_paths = user["custom:paths"]
        # edting a new user so allow email edit
        enable_email_edit = True

    is_la = False
    is_wholesaler = False
    is_dwp = False
    is_other = False

    print(user)

    if admin_user_action != "new":
        user_is_la = user["custom:is_la"] == "1"

        user_custom_paths = user["custom:paths"].split(";")
        for custom_path in user_custom_paths:
            if "/local_authority/" in custom_path and user_is_la:
                is_la = True
                break
            if "/wholesaler/" in custom_path and not user_is_la:
                is_wholesaler = True
                break
            if "/dwp" in custom_path and not user_is_la:
                is_dwp = True
                break
            if "/other/" in custom_path and not user_is_la:
                is_other = True
                break

    return render_template_custom(
        app,
        "admin/edit-user.html",
        user=user,
        enable_email_edit=enable_email_edit,
        user_custom_paths=user_custom_paths,
        local_authority=value_paths_by_type("local_authority"),
        is_la=is_la,
        wholesaler=value_paths_by_type("wholesaler"),
        is_wholesaler=is_wholesaler,
        dwp=value_paths_by_type("dwp"),
        is_dwp=is_dwp,
        other=value_paths_by_type("other"),
        is_other=is_other,
    )


def admin_user_not_found(app):
    return "User not found"
