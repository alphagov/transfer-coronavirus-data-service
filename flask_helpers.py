import os
from functools import wraps

from flask import redirect, render_template, session


def is_admin_interface():
    return os.getenv("ADMIN", "false") == "true"


def is_development():
    return os.getenv("FLASK_ENV", "production") == "development"


def admin_interface(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if not is_admin_interface():
            raise Exception("ADMIN not set when trying /admin")
        return f(*args, **kwargs)

    return decorated_function


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "details" not in session:
            return redirect("/")
        return f(*args, **kwargs)

    return decorated_function


def render_template_custom(app, template, **args):
    args["is_admin_interface"] = is_admin_interface()

    title_after_env = app.page_title
    if is_development:
        title_after_env = "{} - {}".format(app.cf_space.upper(), title_after_env)
    args["title"] = title_after_env

    return render_template(template, **args)
