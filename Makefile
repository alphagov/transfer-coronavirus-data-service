# In your python env, run `make install` to insall required packages
# and then either `make` for a single test run
# or `make watch` for a continuous pipeline that reruns on changes.
#
# Comments to cyber.security@digital.cabinet-office.gov.uk
# This is free and unencumbered software released into the public domain.

.SILENT: test install upgrade watch checks target_dir add_deps copy_dir build run zip

rebuild:
	docker-compose build

shell: rebuild
	docker-compose run chrome-driver bash

clean:
	rm -rf __pycache__ .coverage *.zip *.egg-info .tox venv .pytest_cache htmlcov **/__pycache__ **/*.pyc .target setup.cfg
	echo "✔️ Cleanup of files completed!"

test:
	pytest -c pytest.ini -sqx --disable-warnings
	echo "✔️ Tests passed!"

checks: clean
	echo "⏳ running pipeline..."
	set -e
	isort --atomic -yq
	black -q .
	flake8 . --max-line-length=91
	echo "✔️ Checks pipeline passed!"

install:
	set -e
	echo "⏳ installing..."
	pip3 -q install black flake8 mypy watchdog pyyaml argh pytest isort requests_mock pytest-env
	pip3 -q install -r requirements.txt
	echo "✔️ Pip dependencies installed!"

watch:
	echo "✔️ Watch setup, save a python file to trigger test pipeline"
	watchmedo shell-command --drop --ignore-directories --patterns="*.py" --ignore-patterns="*#*" --recursive --command='clear && make --no-print-directory test' .

target_dir:
	rm -rf .target/
	mkdir -p .target

add_deps:
	pip3 install -r requirements.txt -t .target

copy_dir:
	set -e
	echo "⏳ copying..."
	cp *.py .target
	cp hub.csv .target
	cp *.yml .target
	cp *.txt .target
	cp -R assets .target
	cp -R css .target
	cp -R dist .target
	cp -R js .target
	cp -R templates .target

build: clean target_dir add_deps copy_dir

run: rebuild
	docker-compose run --service-ports chrome-driver python3 run.py main testing

run_test: rebuild
	docker-compose run --service-ports chrome-driver python3 run.py main testing

run_staging: rebuild
	docker-compose run --service-ports chrome-driver python3 run.py main staging

run_prod: rebuild
	docker-compose run --service-ports chrome-driver python3 run.py main production

admin_test: rebuild
	docker-compose run --service-ports chrome-driver python3 run.py admin testing

admin_staging: rebuild
	docker-compose run --service-ports chrome-driver python3 run.py admin staging

admin_prod: rebuild
	docker-compose run --service-ports chrome-driver python3 run.py admin production

zip: build
	mkdir -p builds
	cd .target; zip -X -9 ../builds/backend-consumer-app.zip -r .
	echo "✔️ zip file built!"

e2e: rebuild
	docker-compose run chrome-driver bash -c "python3 run.py main testing & cd behave && behave --tags='@user'"
	docker-compose run chrome-driver bash -c "python3 run.py admin testing & cd behave && behave --tags='@admin'"

concourse_e2e:
	cd behave && behave --tags='@user'
