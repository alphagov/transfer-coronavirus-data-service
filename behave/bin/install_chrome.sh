#! /bin/bash
CHROME_DRIVER_VERSION=70.0.3538.16    # 2.37
HEADLESS_CHROME_VERSION=v1.0.0-55     # v1.0.0-41

cd /opt
curl -SL https://chromedriver.storage.googleapis.com/${CHROME_DRIVER_VERSION}/chromedriver_linux64.zip > chromedriver.zip
unzip chromedriver.zip
rm chromedriver.zip
# download chrome binary
curl -SL https://github.com/adieuadieu/serverless-chrome/releases/download/${HEADLESS_CHROME_VERSION}/stable-headless-chromium-amazonlinux-2017-03.zip > headless-chromium.zip
unzip headless-chromium.zip
rm headless-chromium.zip
ln -fs /opt/headless-chromium /opt/chrome
