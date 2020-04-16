PROJECT=tamato
VIRTUAL_ENV ?= venv
BIN=${VIRTUAL_ENV}/bin
DEV=true

-include .env
export

.PHONY: clean clean-bytecode clean-static collectstatic compilescss dependencies docker-image docker-test help node_modules run test


clean-static:
	@echo
	@echo "> Removing collected static files..."
	@rm -rf run/static static/*

clean-bytecode:
	@echo
	@echo "> Removing compiled bytecode..."
	@find . \( -name '__pycache__' -and -not -name "venv" \) -d -prune -exec rm -r {} +

clean: clean-bytecode clean-static

${BIN}:
	@if [ -z "$$NO_VIRTUAL_ENV" -a ! -d "${VIRTUAL_ENV}" ]; then echo "\n> Initializing virtualenv..."; python -m venv ${VIRTUAL_ENV}; fi

## dependencies: Install dependencies
dependencies: ${BIN} requirements.txt
	@echo
	@echo "> Fetching dependencies..."
	@${BIN}/pip install -r requirements.txt
	@${BIN}/pip freeze > requirements.lock
	@if [ ! "${DEV}" = "false" ]; then ${BIN}/pip install -r requirements-dev.txt; fi

## collectstatic: Collect assets into static folder
collectstatic: dependencies compilescss
	@echo
	@echo "> Collecting static assets..."
	@${BIN}/python manage.py collectstatic --noinput

compilescss: node_modules
	@echo
	@echo "> Compiling SCSS..."
	@npm run build

node_modules:
	@echo
	@echo "> Installing Javascript dependencies..."
	@npm install

## run: Run webapp
run:
	@echo
	@echo "> Running webapp..."
	@python manage.py runserver

run-cf: collectstatic migrate
	@echo
	@echo "> Running webapp..."
	@${BIN}/python manage.py runserver

## test: Run tests
test: export DJANGO_SETTINGS_MODULE=settings.test
test:
	@echo
	@echo "> Running tests..."
	${BIN}/python manage.py test

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
		-e DJANGO_SETTINGS_MODULE=settings.test \
		${PROJECT} sh -c "docker/wait_for_db && python manage.py test -- --cov"

help: Makefile
	@echo
	@echo " Commands in "$(PROJECT)":"
	@echo
	@sed -n 's/^##//p' $< | column -t -s ':' | sed -e 's/^/ /'
	@echo
