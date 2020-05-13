import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def before_scenario(context, _scenario):
    context.api_session = requests.Session()

    options = Options()
    options.binary = "bin/headless-chromium"
    options.add_argument("-headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--single-process")
    options.add_argument("--disable-dev-shm-usage")

    context.browser = webdriver.Chrome("/opt/chromedriver", chrome_options=options)
    context.browser.set_window_size(1080, 800)


def after_scenario(context, _scenario):
    context.browser.quit()
