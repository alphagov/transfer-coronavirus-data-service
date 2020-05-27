import os

from flask import Flask

from config import load_environment, setup_talisman


def test_setup_talisman():
    app = Flask(__name__)
    app.app_environment = "testing"
    talisman = setup_talisman(app)
    assert not talisman.force_https

    app = Flask(__name__)
    app.app_environment = "staging"
    talisman = setup_talisman(app)
    assert talisman.force_https

    app = Flask(__name__)
    app.app_environment = "production"
    talisman = setup_talisman(app)
    assert talisman.force_https


def test_load_environment():
    app = Flask(__name__)
    load_environment(app)
    assert app.secret_key == os.getenv("APPSECRET", "secret")
    assert app.config["client_id"] == os.getenv("CLIENT_ID", None)
    assert app.config["cognito_domain"] == os.getenv("COGNITO_DOMAIN", None)
    assert app.config["client_secret"] == os.getenv("CLIENT_SECRET", None)
    assert app.config["redirect_host"] == os.getenv("REDIRECT_HOST")
    assert app.config["bucket_name"] == os.getenv("BUCKET_NAME")
    assert app.config["region"] == os.getenv("REGION")
