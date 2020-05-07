#!/usr/bin/env python3

import json
import os
import re
from datetime import datetime

import boto3
import requests
from botocore.exceptions import ClientError
from flask import Flask, redirect, request, send_file, send_from_directory, session
from flask_talisman import Talisman
from requests.auth import HTTPBasicAuth
from werkzeug.utils import secure_filename

import admin
import cognito
from flask_helpers import (
    admin_interface,
    end_user_interface,
    has_admin_role,
    has_upload_rights,
    login_required,
    render_template_custom,
    requires_group_in_list,
)
from logger import LOG
from user import User

app = Flask(__name__)
app.cf_space = os.getenv("CF_SPACE", "testing")
app.logger = LOG


def setup_talisman(app):
    csp = {"default-src": ["'self'", "https://*.s3.amazonaws.com"]}
    if app.cf_space == "testing":
        print("loading Talisman for testing - no HTTPS")
        return Talisman(
            app,
            force_https=False,
            strict_transport_security=False,
            session_cookie_secure=False,
            content_security_policy=csp,
        )
    else:
        print("loading Talisman with HTTPS")
        return Talisman(
            app,
            force_https=True,
            strict_transport_security=True,
            session_cookie_secure=True,
            content_security_policy=csp,
        )


def load_environment(app):
    """
    Load environment vars into flask app attributes
    """
    app.secret_key = os.getenv("APPSECRET", "secret")
    app.client_id = os.getenv("CLIENT_ID", None)
    app.cognito_domain = os.getenv("COGNITO_DOMAIN", None)
    app.client_secret = os.getenv("CLIENT_SECRET", None)
    app.redirect_host = os.getenv("REDIRECT_HOST")
    app.bucket_name = os.getenv("BUCKET_NAME")
    app.region = os.getenv("REGION")
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
    session["group"] = User.group(response["Username"])

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


@app.route("/403")
def server_error_403():
    error_message = session.get("error_message", "Access denied")
    app.logger.error(f"Server error: {error_message}")
    return (
        render_template_custom(
            app, "error.html", hide_logout=True, error=error_message
        ),
        403,
    )


@app.errorhandler(500)
def server_error_500(error):
    app.logger.error(f"Server error: {request.url}")
    return render_template_custom(app, "error.html", hide_logout=True, error=error), 500


@app.errorhandler(404)
def server_error_404(error):
    app.logger.error(f"Server error: {request.url}")
    return render_template_custom(app, "error.html", hide_logout=True, error=error), 404


@app.errorhandler(400)
def server_error_400(error):
    app.logger.error(f"Server error: {request.url}")
    return render_template_custom(app, "error.html", hide_logout=True, error=error), 400


@app.route("/")
@app.route("/index")
def index():

    args = request.args

    # TODO remove below if statement once admin app running online
    if "details" not in session and cognito.is_aws_authenticated():
        cognito.delegate_auth_to_aws(session)

    if "code" in args:
        oauth_code = args["code"]
        response = exchange_code_for_tokens(oauth_code)
        if response.status_code != 200:
            app.logger.error({"error": "OAuth failed", "response": response})
        return redirect("/admin" if has_admin_role() else "/")

    if "details" in session:
        upload_rights = has_upload_rights()
        is_admin_role = has_admin_role()
        return render_template_custom(
            app,
            "welcome.html",
            user=session["user"],
            email=session["email"],
            upload_rights=upload_rights,
            is_admin_role=is_admin_role,
        )
    else:
        login_url = (
            f"https://{app.cognito_domain}/oauth2/authorize?"
            f"client_id={app.client_id}&"
            "response_type=code&"
            f"redirect_uri={app.redirect_host}&"
            "scope=profile+email+phone+openid+aws.cognito.signin.user.admin"
        )
        return render_template_custom(
            app, "login.html", login_url=login_url, hide_logout=True
        )


@app.route("/logout")
@login_required
def logout():
    try:
        session.pop("details", None)
        session.pop("email", None)
        session.pop("user", None)
        session.pop("attributes", None)
        session.pop("group", None)
    except Exception as err:
        app.logger.error(err)

    return redirect(
        "https://{}/logout?client_id={}&logout_uri={}".format(
            app.cognito_domain, app.client_id, app.redirect_host
        )
    )


@app.route("/download/<path:path>")
@login_required
@end_user_interface
@requires_group_in_list(["standard-download", "standard-upload"])
def download(path):
    """
    Check the user has access to the requested file
    Generate a presigned S3 URL
    Redirect to download
    """
    prefixes = load_user_lookup(session)
    if key_has_granted_prefix(path, prefixes):
        redirect_url = create_presigned_url(app.bucket_name, path, 60)
        if redirect_url is not None:
            app.logger.info(
                "User {}: generated url for: {}".format(session["user"], path)
            )

            if "details" in session and "attributes" in session:
                if redirect_url.startswith(
                    "https://{}.s3.amazonaws.com/".format(app.bucket_name)
                ):
                    app.logger.info(
                        "User {}: downloaded: {}".format(session["user"], path)
                    )
                    return redirect(redirect_url, 302)
        else:
            return redirect("/404")
    else:
        return redirect("/404")


@app.route("/upload", methods=["POST", "GET"])
@login_required
@end_user_interface
@requires_group_in_list(["standard-upload"])
def upload():
    user_upload_paths = user_custom_paths(is_upload=True, session=session)
    preupload = True
    file_path_to_upload = ""
    presigned_object = ""

    file_extensions = {"csv": {"ext": "csv", "display": "CSV"}}

    if request.method == "POST":
        form_fields = request.form
        task = form_fields.get("task", None)

        if task == "preupload":
            preupload = False

            validated_form = upload_form_validate(
                form_fields, user_upload_paths, file_extensions
            )

            if validated_form["valid"]:
                file_path_to_upload = generate_upload_file_path(
                    validated_form["fields"]
                )

                # generate a S3 presigned_object PutObjct based
                # on s3 key in file_path_to_upload
                presigned_object = create_presigned_post(file_path_to_upload)
                if presigned_object is None:
                    return redirect("/upload?error=True")
            else:
                return redirect("/upload?error=True")

    return render_template_custom(
        app,
        "upload.html",
        user=session["user"],
        email=session["email"],
        presigned_object=presigned_object,
        preupload=preupload,
        filepathtoupload=file_path_to_upload,
        file_extensions=list(file_extensions.values()) if preupload else {},
        upload_keys=user_upload_paths if preupload else [],
    )


def generate_upload_file_path(form_fields):
    """
    Use validated form fields to create the key for S3
    """
    now = datetime.now().strftime("%Y%m%d-%H%M%S")
    file_path_to_upload = "{}/{}_{}.{}".format(
        form_fields["file_location"],
        now,
        form_fields["file_name"],
        form_fields["file_ext"],
    )
    return file_path_to_upload


def upload_form_validate(form_fields, valid_paths, valid_extensions):
    """
    Pass in the submitted form data along with
    paths granted to the user and
    file extensions approved for upload
    """

    status = {"valid": True, "fields": {}}
    if "file_location" in form_fields:
        file_location = form_fields["file_location"]
        field_valid = file_location in valid_paths
        if field_valid:
            status["fields"]["file_location"] = file_location
        else:
            status["valid"] = False

    if "file_name" in form_fields:
        file_name = secure_filename(form_fields["file_name"])
        status["fields"]["file_name"] = file_name

    if "file_ext" in form_fields:
        ext = form_fields["file_ext"]
        field_valid = form_fields["file_ext"] in valid_extensions.keys()
        if field_valid:
            status["fields"]["file_ext"] = ext
        else:
            status["valid"] = False

    return status


def key_has_granted_prefix(key, prefixes):
    """
    Check that the requested s3 key starts with
    one of the granted file prefixes
    """
    granted = False
    for prefix in prefixes:
        if key.startswith(prefix):
            granted = True

    return granted


def create_presigned_post(object_name, expiration=3600):
    # Generate a presigned S3 POST URL
    s3_client = boto3.client("s3")
    try:
        response = s3_client.generate_presigned_post(
            app.bucket_name, object_name, ExpiresIn=expiration
        )

        csvw = {
            "@context": "http://www.w3.org/ns/csvw",
            "url": object_name,
            "dc:creator": session["email"],
        }

        s3_client.put_object(
            Body=json.dumps(csvw),
            Bucket=app.bucket_name,
            Key="{}-metadata.json".format(object_name),
        )
    except ClientError as e:
        app.logger.error(e)
        return None

    # print(response)
    # The response contains the presigned URL and required fields
    return response


@app.route("/files")
@login_required
@end_user_interface
@requires_group_in_list(["standard-download", "standard-upload"])
def files():
    files = get_files(app.bucket_name, session)

    # TODO sorting

    return render_template_custom(
        app, "files.html", user=session["user"], email=session["email"], files=files
    )


# ----------- ADMIN ROUTES -----------
# ====================================


@app.route("/admin")
@admin_interface
@requires_group_in_list(["admin-view", "admin-power", "admin-full"])
def admin_main():
    return admin.admin_main(app)


@app.route("/admin/user/list")
@admin_interface
@requires_group_in_list(["admin-view", "admin-power", "admin-full"])
def admin_list_users():
    return admin.admin_list_users(app)


@app.route("/admin/user", methods=["POST", "GET"])
@admin_interface
@requires_group_in_list(["admin-view", "admin-power", "admin-full"])
def admin_user():
    return admin.admin_user(app)


@app.route("/admin/user/edit", methods=["POST", "GET"])
@admin_interface
@requires_group_in_list(["admin-power", "admin-full"])
def admin_edit_user():
    return admin.admin_edit_user(app)


@app.route("/admin/user/reinvite", methods=["POST"])
@admin_interface
@requires_group_in_list(["admin-power", "admin-full"])
def admin_reinvite_user():
    return admin.admin_reinvite_user(app)


@app.route("/admin/user/enable", methods=["POST"])
@admin_interface
@requires_group_in_list(["admin-power", "admin-full"])
def admin_enable_user():
    return admin.admin_enable_user(app)


@app.route("/admin/user/disable", methods=["POST"])
@admin_interface
@requires_group_in_list(["admin-power", "admin-full"])
def admin_disable_user():
    return admin.admin_disable_user(app)


@app.route("/admin/user/delete", methods=["POST"])
@admin_interface
@requires_group_in_list(["admin-full"])
def admin_delete_user():
    return admin.admin_delete_user(app)


@app.route("/admin/user/error")
@admin_interface
@requires_group_in_list(["admin-view", "admin-power", "admin-full"])
def admin_user_error():
    return admin.admin_user_error(app)


@app.route("/admin/user/confirm", methods=["POST"])
@admin_interface
@requires_group_in_list(["admin-view", "admin-power", "admin-full"])
def admin_confirm_user():
    return admin.admin_confirm_user(app)


@app.route("/admin/user/not-found")
@admin_interface
@requires_group_in_list(["admin-view", "admin-power", "admin-full"])
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
        app.logger.info(
            "User {}: file_key: {}".format(user_session["user"], file_key["key"])
        )

        url_string = f"/download/{file_key['key']}"
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


def user_custom_paths(session, is_upload=False):
    # paths = []

    app_download_path = os.getenv("BUCKET_MAIN_PREFIX", "web-app-prod-data")
    app_upload_path = os.getenv("BUCKET_UPLOAD_PREFIX", "web-app-upload")

    user_paths_attribute = return_attribute(session, "custom:paths")
    user_paths = user_paths_attribute.split(";")

    user_paths = [
        path.replace(app_download_path, app_upload_path) if is_upload else path
        for path in user_paths
        if path.startswith(app_download_path)
    ]

    return user_paths


def load_user_lookup(session):
    user_paths = user_custom_paths(session, is_upload=False)
    return user_paths


@app.template_filter("s3_remove_root_path")
def s3_remove_root_path(key):
    """
    Remove root element from path
    """
    file_link_path = re.sub(r"^[^/]+\/", "", key)
    return file_link_path


def run():
    """
    Run a local server
    """
    setup_talisman(app)
    load_environment(app)
    app.run(host="0.0.0.0", port=os.getenv("PORT", "8000"))


if __name__ == "__main__":
    run()
