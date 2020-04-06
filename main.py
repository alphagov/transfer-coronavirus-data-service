#!/usr/bin/env python3

import base64
import os
import re

import boto3
import requests
from botocore.exceptions import ClientError
from flask import Flask, redirect, request, send_file, send_from_directory, session
from flask_talisman import Talisman
from requests.auth import HTTPBasicAuth
from datetime import datetime

import admin
import cognito
from flask_helpers import admin_interface, login_required, render_template_custom
from logger import LOG
from werkzeug.utils import secure_filename


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
    return render_template_custom(app, "error.html", hide_logout=True, error=e), 500


@app.errorhandler(404)
def server_error_404(e):
    app.logger.error(f"Server error: {request.url}")
    return render_template_custom(app, "error.html", hide_logout=True, error=e), 404


@app.errorhandler(400)
def server_error_400(e):
    app.logger.error(f"Server error: {request.url}")
    return render_template_custom(app, "error.html", hide_logout=True, error=e), 400


@app.route("/")
@app.route("/index")
def index():

    if os.getenv("ADMIN", "false") == "true":
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
        upload_rights = True
        return render_template_custom(
            app,
            "welcome.html",
            user=session["user"],
            email=session["email"],
            upload_rights=upload_rights,
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


@app.route("/upload", methods=["POST", "GET"])
@login_required
def upload():
    if True:  # in group
        ucps = user_custom_paths(is_upload=True, session=session)
        preupload = True
        file_extensions = [
            {"ext": "csv", "display": "CSV"},
        ]
        filepathtoupload = ""
        presigned_object = ""

        if request.method == "POST":
            path = ""
            args = request.form
            if len(args) != 0:

                if "task" in args:
                    print("task", args["task"])
                    print("args", args)

                    if args["task"] == "upload":
                        # handled in javascript
                        # return a redirect here if JS is disabled
                        return redirect("/upload?js_disabled=True")

                    if args["task"] == "cancel-upload":
                        return redirect("/upload")

                    if args["task"] == "cancel-preupload":
                        return redirect("/")

                    if args["task"] == "preupload":
                        preupload = False
                        complete = 0
                        file_location = ""
                        file_name = ""
                        ext = ""

                        if "file_location" in args:
                            arg_fl = args["file_location"]
                            for fl in ucps:
                                if fl["key"] == arg_fl:
                                    file_location = fl["path"]
                                    print("file_location", file_location)
                                    complete += 1
                                    break

                        if "filename" in args:
                            arg_fn = args["filename"]
                            file_name = secure_filename(arg_fn)
                            print("file_name", file_name)
                            complete += 1

                        if "file_ext" in args:
                            arg_ext = args["file_ext"]
                            for fe in file_extensions:
                                if fe["ext"] == arg_ext:
                                    ext = fe["ext"]
                                    complete += 1
                                    print("ext", ext)
                                    break

                        if complete == 3:
                            filedatetime = datetime.now().strftime("%Y%m%d-%H%M")
                            filepathtoupload = "{}/{}_{}.{}".format(
                                file_location, filedatetime, file_name, ext
                            )
                            print("filepathtoupload", filepathtoupload)
                            # generate a S3 presigned_object PutObjct based
                            # on filepathtoupload
                            cpp = create_presigned_post(filepathtoupload)
                            presigned_object = cpp
                        else:
                            return redirect("/upload?error=True")

        return render_template_custom(
            app,
            "upload.html",
            user=session["user"],
            email=session["email"],
            presigned_object=presigned_object,
            preupload=preupload,
            filepathtoupload=filepathtoupload,
            file_extensions=file_extensions if preupload else [],
            upload_keys=[u["key"] for u in ucps] if preupload else [],
        )
    else:
        return redirect("/")


def create_presigned_post(object_name, expiration=3600):
    # Generate a presigned S3 POST URL
    s3_client = boto3.client('s3')
    try:
        response = s3_client.generate_presigned_post(app.bucket_name,
                                                     object_name,
                                                     ExpiresIn=expiration)
    except ClientError as e:
        logging.error(e)
        return None

    print(response)
    # The response contains the presigned URL and required fields
    return response


@app.route("/files")
@login_required
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


def user_custom_paths(session, is_upload=False):
    paths = []

    app_download_path = os.getenv("BUCKET_MAIN_PREFIX", "web-app-prod-data")
    app_upload_path = os.getenv("BUCKET_UPLOAD_PREFIX", "web-app-upload")

    user_key_prefixes = return_attribute(session, "custom:paths")
    for key_prefix in user_key_prefixes.split(";"):
        if key_prefix != "" and "/" in key_prefix:
            if not is_upload and not key_prefix.startswith(app_download_path):
                continue

            skp = key_prefix.split("/", 1)
            if is_upload:
                key = skp[1]
                path = "{}/{}".format(app_upload_path, skp[1])
            else:
                key = key_prefix
                path = key_prefix
            if key != "" and path != "":
                paths.append({"key": key, "path": path})

    return paths


def load_user_lookup(session):
    paths = []

    ucps = user_custom_paths(session, is_upload=False)
    for ucp in ucps:
        paths.append(ucp["path"])
        app.logger.info("User: {} prefix: {}".format(session["user"], ucp["path"]))

    return paths


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
