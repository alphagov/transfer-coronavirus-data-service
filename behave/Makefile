.SHELL := /bin/sh
.DEFAULT_GOAL := zip
.PHONY = clean

rebuild:
	docker-compose build

run: rebuild
	docker-compose run chrome-driver bash -c ". /usr/src/app/behave_env.sh && behave"

test:
	behave

shell: rebuild
	docker-compose run chrome-driver bash
