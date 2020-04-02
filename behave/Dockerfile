FROM ubuntu:18.04

WORKDIR /usr/src/app
RUN apt-get update
RUN apt-get install -y apt-utils zip unzip
RUN apt-get install -y python3.7 python3-distutils python3-pip
RUN apt-get install -y build-essential libssl-dev libffi-dev python3-dev
RUN apt-get install -y curl tar imagemagick python-gtk2
RUN apt-get install -y libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1

# install chromedriver and headless-chrome
RUN mkdir ./bin
COPY bin/* ./bin/
RUN bash bin/install_chrome.sh

ENV PATH=.:/opt:$PATH

# Install python deps
COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY . .
