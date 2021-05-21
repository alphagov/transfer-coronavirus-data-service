import logging
import os

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def before_scenario(context, _scenario):
    context.api_session = requests.Session()
    # options = webdriver.FirefoxOptions()
    # options.headless = os.environ["E2E_HEADLESS"] == "true"
    # context.browser = webdriver.Firefox(options=options)
    # context.browser.set_window_size(1080,800)

    options = Options()
    options.binary = "/usr/bin/google-chrome-stable"
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--single-process")
    options.add_argument("--disable-dev-shm-usage")

    context.browser = webdriver.Chrome("/usr/bin/chromedriver", chrome_options=options)
    context.browser.set_window_size(1080, 800)
    context.config.setup_logging(os.environ.get("LOG_LEVEL", "ERROR"))
    context.logger = logging.getLogger("behave")


def after_scenario(context, _scenario):
    context.browser.quit()
