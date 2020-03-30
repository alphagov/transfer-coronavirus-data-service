import base64
import os

import boto3
import requests
from botocore.exceptions import ClientError
from flask import (
    Flask,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
)
from requests.auth import HTTPBasicAuth

from logger import LOG

app = Flask(__name__)
app.logger = LOG


def load_environment(app):
    """
    Load environment vars into flask app attributes
    """
    app.secret_key = os.getenv("APPSECRET", "secret")
    app.client_id = os.getenv("CLIENT_ID")
    app.cognito_domain = os.getenv("COGNITO_DOMAIN")
    app.client_secret = os.getenv("CLIENT_SECRET")
    app.redirect_host = os.getenv("REDIRECT_HOST")
    app.bucket_name = os.getenv("BUCKET_NAME")
    app.region = os.getenv("REGION")
    app.page_title = os.getenv("PAGE_TITLE", "GOV.UK")


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


@app.route("/robots.txt")
def send_robots():
    return "User-agent: *\r\nDisallow: /", 200


@app.errorhandler(500)
def server_error_500(e):
    app.logger.error(f"Server error: {request.url}")
    return render_template("error.html", error=e, title=app.page_title), 500


@app.errorhandler(404)
def server_error_404(e):
    app.logger.error(f"Server error: {request.url}")
    return render_template("error.html", error=e, title=app.page_title), 500


@app.route("/")
@app.route("/index")
def index():

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
        return render_template(
            "welcome.html",
            user=session["user"],
            email=session["email"],
            title=app.page_title,
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
        return render_template("login.html", login_url=login_url, title=app.page_title)


@app.route("/logout")
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
def files():
    if "details" in session and "attributes" in session:
        files = get_files(app.bucket_name, session)

        # TODO sorting

        return render_template(
            "files.html",
            user=session["user"],
            email=session["email"],
            files=files,
            title=app.page_title,
        )
    else:
        return redirect("/")


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
    load_environment(app)
    app.run(host="0.0.0.0", port=os.getenv("PORT", "8000"))


if __name__ == "__main__":
    run()
