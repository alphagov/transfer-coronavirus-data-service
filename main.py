#!/usr/bin/env python3

import json
import re
from collections import defaultdict
from datetime import datetime

import boto3
import requests
from botocore.exceptions import ClientError
from flask import Flask, redirect, request, send_file, send_from_directory, session
from jinja2 import TemplateError
from requests.auth import HTTPBasicAuth
from werkzeug.utils import secure_filename

import admin
import config
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
app.logger = LOG


def exchange_code_for_session_user(code, code_verifier=None) -> dict:
    """Exchange the authorization code for user tokens.

    Documentation:
    https://docs.aws.amazon.com/cognito/latest/developerguide/token-endpoint.html
    """
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    payload = {
        "grant_type": "authorization_code",
        "client_id": app.config["client_id"],
        "redirect_uri": "{}".format(app.config["redirect_host"]),
        "code": code,
    }
    token_endpoint_url = "https://{}/oauth2/token".format(app.config["cognito_domain"])

    oauth_response = requests.post(
        token_endpoint_url,
        data=payload,
        headers=headers,
        auth=HTTPBasicAuth(app.config["client_id"], app.config["client_secret"]),
    )

    oauth_response_body = oauth_response.json()
    # Get the id_token field
    id_token = oauth_response_body["id_token"]

    client = boto3.client("cognito-idp")
    cognito_user = client.get_user(AccessToken=oauth_response_body["access_token"])

    is_not_production = config.get("app_environment") != "production"
    # only get these attributes if the MFA is present
    if is_not_production or is_mfa_configured(cognito_user):
        session["attributes"] = cognito_user["UserAttributes"]
        session["user"] = cognito_user["Username"]
        session["email"] = return_attribute(session, "email")
        session["name"] = return_attribute(session, "name")
        session["details"] = id_token
        session["group"] = User.group(cognito_user["Username"])
        app.logger.info(
            "Successful login - user: %s email: %s", session["user"], session["email"]
        )
    # else oauth_response status code to 403
    else:
        session["error_message"] = (
            "Please contact us: "
            "We need to enable SMS authentication for your account."
        )
        oauth_response.status_code = 403

    return oauth_response


def is_mfa_configured(cognito_user):
    # does the MFAOptions list contain an entry where both
    # the DeliveryMedium is SMS
    # and the AttributeName is phone_number
    has_phone_mfa = any(
        [
            device["DeliveryMedium"] == "SMS"
            and device["AttributeName"] == "phone_number"
            for device in cognito_user.get("MFAOptions", [])
        ]
    )

    has_preferred_mfa_setting = cognito_user.get("PreferredMfaSetting", "") == "SMS_MFA"
    has_mfa_setting_list = "SMS_MFA" in cognito_user.get("UserMFASettingList", [])

    mfa_configured = [has_phone_mfa, has_preferred_mfa_setting, has_mfa_setting_list]
    return all(mfa_configured)


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


@app.route("/resources/<path:path>")
def download_resources(path):
    return send_from_directory("assets/resources", path, as_attachment=True)


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
    del session["error_message"]
    return (
        render_template_custom("error.html", hide_logout=True, error=error_message),
        403,
    )


@app.errorhandler(TemplateError)
def server_error_template_render(error):
    app.logger.error(f"Server error: {request.url}")
    return render_template_custom("error.html", hide_logout=True, error=error), 500


@app.errorhandler(500)
def server_error_500(error):
    app.logger.error(f"Server error: {request.url}")
    return render_template_custom("error.html", hide_logout=True, error=error), 500


@app.errorhandler(404)
def server_error_404(error):
    app.logger.error(f"Server error: {request.url}")
    return render_template_custom("error.html", hide_logout=True, error=error), 404


@app.errorhandler(400)
def server_error_400(error):
    app.logger.error(f"Server error: {request.url}")
    return render_template_custom("error.html", hide_logout=True, error=error), 400


@app.route("/")
@app.route("/index")
def index():
    # Log user-agent for browser use analysis
    app.logger.info({"user-agent": request.headers.get("User-Agent")})

    args = request.args

    if "code" in args:
        oauth_code = args["code"]
        response = exchange_code_for_session_user(oauth_code)
        if response.status_code != 200:
            app.logger.error({"error": "OAuth failed", "response": response})
            return redirect("/403")

        return redirect("/admin" if has_admin_role() else "/")

    if "details" in session:
        upload_rights = has_upload_rights()
        is_admin_role = has_admin_role()
        return render_template_custom(
            "welcome.html",
            user=session["user"],
            email=session["email"],
            upload_rights=upload_rights,
            is_admin_role=is_admin_role,
        )
    else:
        login_url = (
            f"https://{app.config['cognito_domain']}/oauth2/authorize?"
            f"client_id={app.config['client_id']}&"
            "response_type=code&"
            f"redirect_uri={app.config['redirect_host']}&"
            "scope=profile+email+phone+openid+aws.cognito.signin.user.admin"
        )
        return render_template_custom(
            "login.html", hide_logout=True, login_url=login_url
        )


@app.route("/error_test")
def error_test():
    print(1 / 0)
    return redirect("/500")


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
            app.config["cognito_domain"],
            app.config["client_id"],
            app.config["redirect_host"],
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

    user_can_see_object_path = key_has_granted_prefix(path, prefixes)
    lambda_can_get_object = validate_access_to_s3_path(app.config["bucket_name"], path)

    app.logger.debug("User granted access to path: %s", str(user_can_see_object_path))
    app.logger.debug("Lambda can get object: %s", str(lambda_can_get_object))
    if user_can_see_object_path and lambda_can_get_object:
        redirect_url = create_presigned_url(app.config["bucket_name"], path, 60)
        if redirect_url is not None:
            app.logger.info(
                "User {}: generated url for: {}".format(session["user"], path)
            )

            if "details" in session and "attributes" in session:
                if redirect_url.startswith(
                        "https://{}.s3.amazonaws.com/".format(app.config["bucket_name"])
                ):
                    app.logger.info(
                        "User {}: downloaded: {}".format(session["user"], path)
                    )
                    return redirect(redirect_url, 302)
        else:
            return redirect("/404")
    else:
        return redirect("/403")


@app.route("/upload", methods=["POST", "GET"])
@login_required
@end_user_interface
@requires_group_in_list(["standard-upload"])
def upload():
    user_upload_paths = user_custom_paths(is_upload=True, session=session)
    preupload = True
    file_path_to_upload = ""
    presigned_object = ""
    upload_history = []

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

    else:
        upload_history = get_upload_history(config.get("bucket_name"), session)
        app.logger.debug({"uploads": upload_history})

    return render_template_custom(
        "upload.html",
        user=session["user"],
        email=session["email"],
        is_la=return_attribute(session, "custom:is_la"),
        presigned_object=presigned_object,
        preupload=preupload,
        filepathtoupload=file_path_to_upload,
        file_extensions=list(file_extensions.values()) if preupload else {},
        upload_keys=user_upload_paths if preupload else [],
        upload_history=collect_files_by_date(upload_history),
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
            app.config["bucket_name"], object_name, ExpiresIn=expiration
        )

        csvw = {
            "@context": "http://www.w3.org/ns/csvw",
            "url": object_name,
            "dc:creator": session["email"],
            "dc:date": datetime.utcnow().isoformat(),
            "dc:publisher": "Government Digital Service",
        }

        s3_client.put_object(
            Body=json.dumps(csvw),
            Bucket=app.config["bucket_name"],
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
    files = get_files(app.config["bucket_name"], session)

    # TODO sorting

    return render_template_custom(
        "files.html",
        user=session["user"],
        email=session["email"],
        files=collect_files_by_date(files),
        is_la=return_attribute(session, "custom:is_la"),
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


@app.route("/admin/error-test")
def admin_error_test():
    print(1 / 0)
    return redirect("/500")


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
        region_name=app.config["region"],
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
    prefixes = load_user_lookup(user_session)
    app.logger.debug({"prefixes": prefixes})

    file_keys = list_s3_bucket_matching_prefixes(bucket_name, prefixes)

    resp = []

    for file_key in file_keys:
        app.logger.info(
            "User {}: file_key: {}".format(user_session["user"], file_key["key"])
        )

        url_string = f"/download/{file_key['key']}"
        file_key["url"] = url_string
        resp.append(file_key)

    app.logger.info(resp)

    return resp


def get_upload_history(bucket_name: str, user_session: dict) -> list:
    prefixes = user_custom_paths(user_session, True)
    app.logger.debug({"prefixes": prefixes})

    file_keys = list_s3_bucket_matching_prefixes(bucket_name, prefixes)
    file_keys = list(
        filter(lambda item: not item["key"].endswith("-metadata.json"), file_keys)
    )
    return file_keys


def list_s3_bucket_matching_prefixes(bucket_name, prefixes):
    conn = boto3.client(
        "s3", region_name="eu-west-2"
    )  # again assumes boto.cfg setup, assume AWS S3

    file_keys = []

    for prefix in prefixes:
        paginator = conn.get_paginator("list_objects")
        operation_parameters = {"Bucket": bucket_name, "Prefix": prefix}
        page_iterator = paginator.paginate(**operation_parameters)
        for page in page_iterator:
            if "Contents" in page:
                for file_item in page["Contents"]:
                    if not file_item["Key"].endswith("/"):
                        # add category derived from file path and name
                        categorise_file(file_item, prefix)
                        # add date strings for rendering and sorting
                        date_file(file_item)
                        # change key case to lower
                        file_keys.append(
                            {key.lower(): value for key, value in file_item.items()}
                        )

    # sort in reverse date order
    file_keys = sorted(file_keys, key=lambda file: file["sorttime"], reverse=True)
    return file_keys


def categorise_file(file_item, prefix):
    """
    Take paths after the file prefix
    and words of the file name and
    join into a single category string
    """
    key = file_item["Key"]
    file_path = key.replace(prefix, "")
    # remove empty strings from starting or trailing slashes
    path_steps = list(filter(lambda folder: folder != "", file_path.split("/")))
    full_file_name = path_steps.pop()
    file_category = get_file_name_category(full_file_name)
    if file_category != "":
        path_steps.append(file_category)

    categories = [re_case_word(re.sub(r"[-_]", " ", word)) for word in path_steps]

    joined_category = " > ".join(categories)
    if joined_category == "":
        joined_category = "Daily Incoming Data"

    app.logger.debug({"categories": categories, "joined": joined_category})
    file_item["Category"] = joined_category
    file_item["Categories"] = categories
    return file_item


def get_file_name_category(file_name):
    """
    Strip any numeric strings from the file name
    and convert to space delimited string for
    rendering
    """
    # remove file extension
    file_name = " ".join(file_name.split(".")[:-1])

    file_name_words = re.split("[-_]", file_name)
    # remove numeric strings
    file_category_words = filter(
        lambda word: not re.match("^[0-9]+$", word), file_name_words
    )

    file_category = " ".join(file_category_words)
    return file_category


def re_case_word(word):
    """
    Title case word unless known initialism which should be upper
    """
    initialisms = ["DWP", "NHS", "MHCLG", "GDS"]

    if word.upper() in initialisms:
        re_cased = word.upper()
    else:
        re_cased = word.title()
    return re_cased


def date_file(file_item):
    """
    Add Show_Date and Sort_Date as strings
    calculated from LastModified
    """
    file_item["ShowDate"] = file_item["LastModified"].strftime("%d/%m/%Y")
    file_item["ShowTime"] = file_item["LastModified"].strftime("%H:%M")
    file_item["SortDate"] = file_item["LastModified"].strftime("%Y%m%d")
    file_item["SortTime"] = file_item["LastModified"].strftime("%Y%m%d%H%M")
    app.logger.debug({"date": file_item["SortDate"], "time": file_item["SortTime"]})
    return file_item


def collect_files_by_date(file_items):
    files_by_date = defaultdict(list)
    file_count = len(file_items)
    for file_item in file_items:
        file_date = file_item["showdate"]
        files_by_date[file_date].append(file_item)
    return {"by_date": files_by_date, "count": file_count}


def return_attribute(session: dict, get_attribute: str) -> str:
    if "attributes" in session:
        for attribute in session["attributes"]:
            app.logger.debug(attribute["Name"])
            if "Name" in attribute:
                if attribute["Name"] == get_attribute:
                    return attribute["Value"]
    return ""


def user_custom_paths(session, is_upload=False):
    # paths = []

    app_download_path = config.get("bucket_main_prefix", "web-app-prod-data")
    app_upload_path = config.get("bucket_upload_prefix", "web-app-upload")

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


def validate_access_to_s3_path(bucket_name, path):
    """
    Validate the Lambda has permission to perform GetObject
    If the Lambda does not have permission
    the presigned URL will fail
    """
    s3_client = boto3.client("s3")
    try:
        s3_client.get_object(Bucket=bucket_name, Key=path)
        access_granted = True
    except ClientError as err:
        access_granted = False
        app.logger.error(vars(err))
    return access_granted


@app.template_filter("s3_remove_root_path")
def s3_remove_root_path(key):
    """
    Remove root element from path
    """
    file_link_path = re.sub(r"^[^/]+\/", "", key)
    return file_link_path
