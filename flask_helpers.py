import os
from functools import wraps

from flask import redirect, render_template, session


def is_admin_interface():
    return os.getenv("ADMIN", "false") == "true"


def is_development():
    return os.getenv("FLASK_ENV", "production") == "development"


def admin_interface(flask_route):
    @wraps(flask_route)
    def decorated_function(*args, **kwargs):

        if not is_admin_interface():
            raise Exception("ADMIN not set when trying /admin")
        return flask_route(*args, **kwargs)

    return decorated_function


def login_required(flask_route):
    @wraps(flask_route)
    def decorated_function(*args, **kwargs):
        if "details" not in session:
            return redirect("/")
        return flask_route(*args, **kwargs)

    return decorated_function


def upload_rights_required(flask_route):
    @wraps(flask_route)
    def decorated_function(*args, **kwargs):
        if not has_upload_rights():
            return redirect("/")
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
