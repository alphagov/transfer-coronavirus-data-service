import os
import re
from functools import wraps

from flask import redirect, render_template, session

from logger import LOG


def is_admin_interface():
    return os.getenv("ADMIN", "false") == "true"


def has_admin_role():
    is_admin_role = False
    group = session.get("group", None)
    if group:
        is_admin_role = group["value"] in ["admin-view",  "admin-power", "admin-full"]
    return is_admin_role


def current_group_name():
    default_group_name = "group-not-available"
    group_name = default_group_name
    group = session.get("group", None)
    if group:
        group_name = group.get("value", default_group_name)
    return group_name


def is_development():
    return os.getenv("FLASK_ENV", "production") == "development"


def admin_interface(flask_route):
    @wraps(flask_route)
    def decorated_function(*args, **kwargs):
        if not is_admin_interface():
            session["error_message"] = "The requested route is not available"
            LOG.error({"action": "access denied", "reason": "ADMIN env var missing"})
            return redirect("/403")
        if not has_admin_role():
            session["error_message"] = "User not authorised to access this route"
            LOG.error(
                {
                    "action": "access denied",
                    "reason": "User not authorised",
                    "username": session.get("user", None),
                }
            )
            return redirect("/403")
        return flask_route(*args, **kwargs)

    return decorated_function


def end_user_interface(flask_route):
    @wraps(flask_route)
    def decorated_function(*args, **kwargs):
        if has_admin_role():
            session["error_message"] = "User not authorised to access this route"
            LOG.error(
                {
                    "action": "access denied",
                    "reason": "Admin user trying to access end-user interface",
                    "user": session["user"]
                }
            )
            return redirect("/403")
        return flask_route(*args, **kwargs)

    return decorated_function


def requires_group_in_list(valid_roles):
    def decorate_route(flask_route):
        @wraps(flask_route)
        def decorated_function(*args, **kwargs):
            if current_group_name() not in valid_roles:
                LOG.error(
                    {
                        "action": "access denied",
                        "reason": "User does not have required group",
                        "user": session["user"]
                    }
                )
                session["error_message"] = "User not authorised to access this route"
                return redirect("/403")
            return flask_route(*args, **kwargs)

        return decorated_function

    return decorate_route


def login_required(flask_route):
    @wraps(flask_route)
    def decorated_function(*args, **kwargs):
        if "details" not in session:
            session["error_message"] = "Login required to access this route"
            LOG.error(
                {
                    "action": "access denied",
                    "reason": "Login required to access this route"
                }
            )
            return redirect("/403")
        return flask_route(*args, **kwargs)

    return decorated_function


def upload_rights_required(flask_route):
    @wraps(flask_route)
    def decorated_function(*args, **kwargs):
        if not has_upload_rights():
            session["error_message"] = "User not authorised to access this route"
            LOG.error(
                {
                    "action": "access denied",
                    "reason": "User does not have upload permission",
                    "user": session["user"]
                }
            )
            return redirect("/403")
        return flask_route(*args, **kwargs)

    return decorated_function


def render_template_custom(app, template, hide_logout=False, **args):
    args["is_admin_interface"] = is_admin_interface()
    show_back_link = template not in ["welcome.html", "login.html"]

    show_logout = False
    display_username = ""
    if "details" in session and not hide_logout:
        show_logout = True
        display_username = session["email"]

    args["show_back_link"] = show_back_link
    args["show_logout"] = show_logout
    args["display_username"] = display_username

    page_title = os.getenv("PAGE_TITLE", "GOV.UK")
    if is_development():
        page_title = "{} - {}".format(app.cf_space.upper(), page_title)
    args["title"] = page_title

    return render_template(template, **args)


def has_upload_rights():
    has_upload_role = False
    if "group" in session:
        has_upload_role = session["group"]["value"] == "standard-upload"
    return has_upload_role
