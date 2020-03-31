#!/usr/bin/env python3

import base64
import os
from functools import wraps

import boto3
import requests
from botocore.exceptions import ClientError
from flask import (
    Flask,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
)
from flask_talisman import Talisman
from requests.auth import HTTPBasicAuth

import admin
import cognito
from logger import LOG

app = Flask(__name__)
app.cf_space = os.getenv("CF_SPACE", "testing")
app.logger = LOG


def setup_talisman(app):
    if app.cf_space == "testing":
        print("loading Talisman for testing - no HTTPS")
        return Talisman(
            app,
            force_https=False,
            strict_transport_security=False,
            session_cookie_secure=False,
        )
    else:
        print("loading Talisman with HTTPS")
        return Talisman(
            app,
            force_https=True,
            strict_transport_security=True,
            session_cookie_secure=True,
        )


def load_environment(app):
    """
    Load environment vars into flask app attributes
    """
    app.is_admin_interface = os.getenv("ADMIN", "false")
    app.secret_key = os.getenv("APPSECRET", "secret")
    app.client_id = os.getenv("CLIENT_ID", None)
    app.cognito_domain = os.getenv("COGNITO_DOMAIN", None)
    app.client_secret = os.getenv("CLIENT_SECRET", None)
    app.redirect_host = os.getenv("REDIRECT_HOST")
    app.bucket_name = os.getenv("BUCKET_NAME")
    app.region = os.getenv("REGION")
    app.page_title = os.getenv("PAGE_TITLE", "GOV.UK")
    set_app_settings(app)


def set_app_settings(app):
    """
    Use existing env vars if loaded
    """
    if None in [app.client_id, app.cognito_domain, app.client_secret]:
        cognito_credentials = cognito.load_app_settings()
        app.cognito_domain = cognito_credentials["cognito_domain"]
        app.client_id = cognito_credentials["client_id"]
        app.client_secret = cognito_credentials["client_secret"]


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "details" not in session:
            return redirect("/")
        return f(*args, **kwargs)

    return decorated_function


def admin_interface(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if app.is_admin_interface == "false":
            raise Exception("ADMIN not set when trying /admin")
        return f(*args, **kwargs)

    return decorated_function


def render_template_custom(template, **args):
    args["is_admin_interface"] = app.is_admin_interface

    title_after_env = app.page_title
    if app.cf_space != "production":
        title_after_env = "{} - {}".format(app.cf_space, title_after_env)

    args["title"] = title_after_env
    return render_template(template, **args)


def exchange_code_for_tokens(code, code_verifier=None) -> dict:
    """Exchange the authorization code for user tokens.

    Documentation:
    https://docs.aws.amazon.com/cognito/latest/developerguide/token-endpoint.html
    """
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    payload = {
        "grant_type": "authorization_code",
        "client_id": app.client_id,
        "redirect_uri": "{}".format(app.redirect_host),
        "code": code,
    }
    token_endpoint_url = "https://{}/oauth2/token".format(app.cognito_domain)

    oauth_response = requests.post(
        token_endpoint_url,
        data=payload,
        headers=headers,
        auth=HTTPBasicAuth(app.client_id, app.client_secret),
    )

    oauth_response_body = oauth_response.json()
    # Get the id_token field
    id_token = oauth_response_body["id_token"]

    client = boto3.client("cognito-idp")
    response = client.get_user(AccessToken=oauth_response_body["access_token"])

    session["attributes"] = response["UserAttributes"]
    session["user"] = response["Username"]
    session["email"] = return_attribute(session, "email")
    session["details"] = id_token

    app.logger.info(
        "Successful login - user: %s email: %s", session["user"], session["email"]
    )

    return oauth_response


@app.route("/js/<path:path>")
def send_js(path):
    return send_from_directory("js", path)


@app.route("/css/<path:path>")
def send_css(path):
    return send_from_directory("css", path)


@app.route("/dist/<path:path>")
def send_dist(path):
    return send_from_directory("dist", path)


@app.route("/assets/<path:path>")
def send_assets(path):
    return send_from_directory("assets", path)


@app.route("/favicon.ico")
def favicon():
    return send_file("assets/images/favicon.ico")


@app.route("/apple-touch-icon.png")
def apple_touch():
    return send_file("assets/images/govuk-apple-touch-icon.png")


@app.route("/apple-touch-icon-152x152.png")
def apple_touch_152():
    return send_file("assets/images/govuk-apple-touch-icon-152x152.png")


@app.route("/robots.txt")
def send_robots():
    return "User-agent: *\r\nDisallow: /", 200


@app.route("/browserconfig.xml")
def send_browser_config():
    return (
        """<?xml version="1.0" encoding="utf-8"?>
<browserconfig>
    <msapplication>
    </msapplication>
</browserconfig>""",
        200,
    )


@app.errorhandler(500)
def server_error_500(e):
    app.logger.error(f"Server error: {request.url}")
    return render_template_custom("error.html", error=e), 500


@app.errorhandler(404)
def server_error_404(e):
    app.logger.error(f"Server error: {request.url}")
    return render_template_custom("error.html", error=e), 404


@app.errorhandler(400)
def server_error_400(e):
    app.logger.error(f"Server error: {request.url}")
    return render_template_custom("error.html", error=e), 400


@app.route("/")
@app.route("/index")
def index():

    if app.is_admin_interface == "true":
        return redirect("/admin")

    args = request.args

    if "code" in args:
        app.logger.debug("Perform auth exchange")
        oauth_code = args["code"]
        response = exchange_code_for_tokens(oauth_code)
        if response.status_code != 200:
            app.logger.error({"error": "OAuth failed", "response": response})
        return redirect("/")

    if "details" in session:
        app.logger.debug("Logged in")
        return render_template_custom(
            "welcome.html", user=session["user"], email=session["email"]
        )
    else:
        app.logger.debug("Logged out")
        login_url = (
            f"https://{app.cognito_domain}/oauth2/authorize?"
            f"client_id={app.client_id}&"
            "response_type=code&"
            f"redirect_uri={app.redirect_host}&"
            "scope=profile+email+phone+openid+aws.cognito.signin.user.admin"
        )
        return render_template_custom(
            "login.html", login_url=login_url, title=app.page_title
        )


@app.route("/logout")
@login_required
def logout():
    try:
        session.pop("details", None)
        session.pop("email", None)
        session.pop("user", None)
        session.pop("attributes", None)
    except Exception as err:
        app.logger.error(err)

    return redirect(
        "https://{}/logout?client_id={}&logout_uri={}".format(
            app.cognito_domain, app.client_id, app.redirect_host
        )
    )


@app.route("/download")
@login_required
def download():
    args = request.args

    if "url" in args:
        redirect_url = args["url"]

        base64_bytes = redirect_url.encode("utf-8")
        url_bytes = base64.b64decode(base64_bytes)
        redirect_url = url_bytes.decode("utf-8")

        if "details" in session and "attributes" in session:
            if redirect_url.startswith(
                "https://{}.s3.amazonaws.com/".format(app.bucket_name)
            ):
                no_scheme = redirect_url.split("https://", 1)[1]
                no_host = no_scheme.split("/", 1)[1]
                only_key = no_host.split("?", 1)[0]
                app.logger.info(
                    "User {}: downloaded: {}".format(session["user"], only_key)
                )
                return redirect(redirect_url, 302)
    else:
        return redirect("/404")


@app.route("/files")
@login_required
def files():
    if "details" in session and "attributes" in session:
        files = get_files(app.bucket_name, session)

        # TODO sorting

        return render_template_custom(
            "files.html",
            user=session["user"],
            email=session["email"],
            files=files,
            title=app.page_title,
        )
    else:
        return redirect("/")


# ----------- ADMIN ROUTES -----------
# ====================================


@app.route("/admin")
@admin_interface
def admin_main():
    return admin.admin_main(app)


@app.route("/admin/user/list")
@admin_interface
def admin_list_users():
    return admin.admin_list_users(app)


@app.route("/admin/user", methods=["POST", "GET"])
@admin_interface
def admin_user():
    return admin.admin_user(app)


@app.route("/admin/user/edit", methods=["POST", "GET"])
@admin_interface
def admin_edit_user():
    return admin.admin_edit_user(app)


@app.route("/admin/user/error")
@admin_interface
def admin_user_error():
    return admin.admin_user_error(app)


@app.route("/admin/user/confirm", methods=["POST"])
@admin_interface
def admin_confirm_user():
    return admin.admin_confirm_user(app)


@app.route("/admin/user/not-found")
@admin_interface
def admin_user_not_found():
    return admin.admin_user_not_found(app)


# ====================================


def create_presigned_url(bucket_name: str, object_name: str, expiration=3600) -> str:
    """Generate a presigned URL to share an S3 object

    :param bucket_name: str
    :param object_name: str
    :param expiration: int Time in seconds for the presigned URL to remain valid
    :return: str Presigned URL. If error, returns None.
    """

    # Generate a presigned URL for the S3 object
    s3_client = boto3.client(
        "s3",
        region_name=app.region,
        config=boto3.session.Config(signature_version="s3v4"),
    )
    try:
        response = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_name},
            ExpiresIn=expiration,
            HttpMethod="GET",
        )
    except ClientError as err:
        app.logger.error(err)
        return None

    # The response contains the presigned URL
    return response


def get_files(bucket_name: str, user_session: dict):

    conn = boto3.client(
        "s3", region_name="eu-west-2"
    )  # again assumes boto.cfg setup, assume AWS S3

    file_keys = []
    prefixes = load_user_lookup(user_session)

    for prefix in prefixes:
        paginator = conn.get_paginator("list_objects")
        operation_parameters = {"Bucket": bucket_name, "Prefix": prefix}
        page_iterator = paginator.paginate(**operation_parameters)
        for page in page_iterator:
            if "Contents" in page:
                for item in page["Contents"]:
                    if not item["Key"].endswith("/"):
                        file_keys.append({"key": item["Key"], "size": item["Size"]})

    resp = []
    for file_key in file_keys:
        print("User {}: file_key: {}".format(user_session["user"], file_key["key"]))
        url = create_presigned_url(bucket_name, file_key["key"], 300)
        if url is not None:
            app.logger.info(
                "User {}: generated url for: {}".format(
                    user_session["user"], file_key["key"]
                )
            )
            url_bytes = url.encode("utf-8")
            url_base64 = base64.b64encode(url_bytes)
            url_string = url_base64.decode("utf-8")
            resp.append(
                {"url": url_string, "key": file_key["key"], "size": file_key["size"]}
            )
    app.logger.info(resp)
    return resp


def return_attribute(session: dict, get_attribute: str) -> str:
    if "attributes" in session:
        for attribute in session["attributes"]:
            if "Name" in attribute:
                if attribute["Name"] == get_attribute:
                    return attribute["Value"]
    return ""


def load_user_lookup(session):
    paths = []

    # user_is_local_authority = return_attribute(session, "custom:is_la") == "1"
    app_authorised_paths = [os.getenv("BUCKET_MAIN_PREFIX", "web-app-prod-data")]
    user_authorised_paths = return_attribute(session, "custom:paths")

    user_key_prefixes = user_authorised_paths.split(";")
    for key_prefix in user_key_prefixes:
        root_folder = key_prefix.split("/")[0]
        if root_folder in app_authorised_paths:
            paths.append(key_prefix)
            app.logger.info("User: {} prefix: {}".format(session["user"], key_prefix))

    return paths


def run():
    """
    Run a local server
    """
    setup_talisman(app)
    load_environment(app)
    app.run(host="0.0.0.0", port=os.getenv("PORT", "8000"))


if __name__ == "__main__":
    run()
