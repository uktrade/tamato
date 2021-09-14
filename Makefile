PROJECT=tamato
DEV=true

-include .env
export

SPHINXOPTS    ?=

.PHONY: help clean clean-bytecode clean-static collectstatic compilescss dependencies docker-image docker-test node_modules run test test-fast build-docs



help: Makefile
	@echo
	@echo " Commands in "$(PROJECT)":"
	@echo
	@sed -n 's/^##//p' $< | column -t -s ':' | sed -e 's/^/ /'
	@echo

ifndef PYTHON
PYTHON=python
endif

clean-static:
	@echo
	@echo "> Removing collected static files..."
	@rm -rf run/static static/*

clean-bytecode:
	@echo
	@echo "> Removing compiled bytecode..."
	@find . \( -name '__pycache__' -and -not -name "venv" \) -d -prune -exec rm -r {} +

clean: clean-bytecode clean-static

## dependencies: Install dependencies
dependencies: requirements.txt
	@echo
	@echo "> Fetching dependencies..."
	@pip install -r requirements.txt
	@if [ ! "${DEV}" = "false" ]; then pip install -r requirements-dev.txt; fi

## collectstatic: Collect assets into static folder
collectstatic: compilescss
	@echo
	@echo "> Collecting static assets..."
	@${BIN}${PYTHON} manage.py collectstatic --noinput

compilescss:
	@echo
	@echo "> Compiling SCSS..."
	@npm run build

node_modules:
	@echo
	@echo "> Installing Javascript dependencies..."
	@npm install

migrate:
	@echo
	@echo "> Running database migrations..."
	@${PYTHON} manage.py migrate --noinput

## run: Run webapp
run: export DJANGO_SETTINGS_MODULE=settings.dev
run: collectstatic migrate
	@echo
	@echo "> Running webapp..."
	@${PYTHON} manage.py runserver_plus 0.0.0.0:8000

## test: Run tests
test-fast:
	@echo
	@echo "> Running tests..."
	@${PYTHON} -m pytest -x -n=auto --dist=loadfile

test:
	@echo
	@echo "> Running tests..."
	@${PYTHON} -m pytest -n=auto --dist=loadfile --alluredir=allure-results --nomigrations --cov --cov-report html:htmlcov --cov-report=term --cov-report=xml

## docker-image: Build docker image
docker-image:
	@echo
	@echo "> Building docker image..."
	@docker-compose build

## docker-run: Run app in a Docker container
docker-run:
	@echo
	@echo "> Run docker container..."
	@docker-compose up

## docker-test: Run tests in Docker container
docker-test:
	@echo
	@echo "> Running tests in Docker..."
	@docker-compose run \
		${PROJECT} sh -c "docker/wait_for_db && ${PYTHON} manage.py test -- -n=auto --dist=loadfile --cov"

## build-docs: Build the project documentation
build-docs html:
	@sphinx-build . docs/_build -c docs/ -b html


paas-login:
	@echo "> Login to PaaS"
	@cf login -a api.london.cloud.service.gov.uk --sso


%-db.json:
	@echo "> Get ${app}-db service key..."
	@cf service-key ${app}-db EXTERNAL_ACCESS_KEY | tail -n9 > ${app}-db.json


paas-db-tunnel: ${app}-db.json
	@echo "> SSH Tunnel to ${app}-db..."
	$(eval host := $(shell jq -r '.host' < ${app}-db.json))
	$(eval port := $(shell jq -r '.port' < ${app}-db.json))
	@cf ssh -N -L $(port)1:$(host):$(port) ${app}


paas-db-tunnel-shell: ${app}-db.json
	$(eval user := $(shell jq -r '.username' < ${app}-db.json))
	$(eval pass := $(shell jq -r '.password' < ${app}-db.json))
	$(eval name := $(shell jq -r '.name' < ${app}-db.json))
	@PGPASSWORD=$(pass) psql -h localhost -p 54321 -U $(user) $(name)
