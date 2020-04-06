FROM gdscyber/concourse-chrome-driver:latest

WORKDIR /usr/src/app

# Install python deps
COPY requirements-dev.txt .
COPY requirements.txt .
RUN pip3 install -r requirements-dev.txt

COPY . .
