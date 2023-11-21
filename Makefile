COMPOSE_LOCAL=docker-compose
DOCKER=docker
PROJECT=tamato
DEV=true

#default run can be replaced with exec
DOCKER_RUN?=run --rm
#db import file name
DB_DUMP?=${PROJECT}_db.sql
DB_NAME?=${PROJECT}
DB_USER?=postgres
DATE=$(shell date '+%Y_%m_%d')
TEMPLATE_NAME?="${DB_NAME}_${DATE}" 

-include .env
export

SPHINXOPTS    ?=

.PHONY: help clean clean-bytecode clean-static collectstatic compilescss dependencies \
	 docker-clean docker-deep-clean docker-down docker-up-db docker-down docker-image \
	 docker-db-dump docker-test node_modules run test test-fast docker-makemigrations \
	 docker-checkmigrations docker-migrate build-docs docker-restore-db docker-import-new-db 



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

## docker-build: Build docker image
docker-build:
	@echo
	@echo "> Building docker image..."
	@${COMPOSE_LOCAL} build

## docker-up: Run app in a Docker container
docker-up:
	@echo
	@echo "> Run docker container..."
	@${COMPOSE_LOCAL} up

## docker-test: Run tests in Docker container
docker-test:
	@echo
	@echo "> Running tests in Docker..."
	@${COMPOSE_LOCAL} ${DOCKER_RUN} \
		${PROJECT} ${PYTHON} -m pytest -n=auto --dist=loadfile \
		--alluredir=allure-results --nomigrations --cov --cov-report \
		 html:htmlcov --cov-report=term --cov-report=xml

docker-test-fast:
	@echo
	@echo "> Running tests in docker..."
	@${COMPOSE_LOCAL} ${DOCKER_RUN} \
		${PROJECT} ${PYTHON} -m pytest -x -n=auto --dist=loadfile 

## clean-docs: Clean the generated documentation files
clean-docs:
	@rm -f docs/source/training/*.rst
	@rm -rf docs/build

## build-docs: Build the project documentation
build-docs html:
	@sphinx-gherkindoc --raw-descriptions "docs/source/training" "docs/source/training"
	@for FILE in $$(ls -1 docs/source/training/*.rst | grep -v gherkin); do $(BASH) docs/source/training/augment.sh $$FILE; done
	@cd docs && sphinx-build -M html "source" "build"

## docker-clean: clean unused images and volumes
docker-clean:
	@echo
	@echo "> Cleaning unused images in docker..."	
	@${DOCKER} image prune -a -f
	@echo "> Cleaning unused volumes in docker..."	
	@${DOCKER} volume prune -f 

## docker-deep-clean: deep clean all unused systems (containers, networks, images, cache)
docker-deep-clean:
	@echo
	@echo "> Cleaning unused systems in docker..."	
	@${DOCKER} system prune -a

## docker-down: shut down services in Docker
docker-down:
	@echo
	@echo "> Bringing containers in docker down..."
	@${COMPOSE_LOCAL} down

## docker-up-db: shut down services in Docker
docker-up-db:
	@echo
	@echo "> Running db in docker..."	
	@${COMPOSE_LOCAL} up -d db
	@echo 
	@echo "Waiting for database \"ready for connections\""
	@sleep 15; 
	@echo "Database Ready for connections!"

## docker-import-new-db: Import new db DB_DUMP into new TEMPLATE_NAME in Docker container db must be running 
docker-import-new-db: docker-up-db
	@${COMPOSE_LOCAL} exec -u ${DB_USER} db psql -c "DROP DATABASE ${TEMPLATE_NAME}" || true  
	@${COMPOSE_LOCAL} exec -u ${DB_USER} db psql -c "CREATE DATABASE ${TEMPLATE_NAME} TEMPLATE template0"  
	@echo "> Running db dump: ${DB_DUMP}  in docker..."
	@cat ${DB_DUMP} | ${COMPOSE_LOCAL} exec -T db psql  -U ${DB_USER} -d ${TEMPLATE_NAME} 	
	@sleep 5; 

## docker-restore-db: Resotre db in Docker container set DB_NAME to rename db must be running  
docker-restore-db: docker-down docker-up-db
	@${COMPOSE_LOCAL} exec -u ${DB_USER} db psql -c "DROP DATABASE ${DB_NAME}" || true  
	@${COMPOSE_LOCAL} exec -u ${DB_USER} db psql -c "CREATE DATABASE ${DB_NAME} TEMPLATE ${TEMPLATE_NAME}"  
	@sleep 5;

## docker-db-dump: Run db dump to import data into Docker
docker-db-dump: docker-up-db
	@echo "> Running db dump in docker..."
	@cat ${DB_DUMP} | ${COMPOSE_LOCAL} exec -T db psql -U ${DB_USER} -d ${DB_NAME} 	

## docker-first-use: Run application for first time in Docker 
docker-first-use: docker-down docker-clean node_modules compilescss docker-build docker-import-new-db \
	docker-restore-db docker-migrate docker-superuser docker-up 

## docker-makemigrations: Run django makemigrations in Docker
docker-makemigrations: 
	@echo
	@echo "> Running makemigrations in docker..."
	@${COMPOSE_LOCAL} ${DOCKER_RUN} \
		${PROJECT} ${PYTHON} manage.py makemigrations

## docker-migrate: Run django makemigrations in Docker container
docker-migrate:
	@echo
	@echo "> Running database migrations in docker..."
	@${COMPOSE_LOCAL} ${DOCKER_RUN} \
		${PROJECT} ${PYTHON}  manage.py migrate

## docker-checkmigrations: Run django makemigrations checks in Docker container
docker-checkmigrations:
	@echo
	@echo "> Running check migrations in docker..."
	@${COMPOSE_LOCAL} ${DOCKER_RUN} --no-deps \
		${PROJECT} ${PYTHON}  manage.py makemigrations --check

## docker-django-shell: Run django shell in Docker container
docker-django-shell:
	@echo
	@echo "> Running django shell  in docker..."
	@${COMPOSE_LOCAL} ${DOCKER_RUN} \
		${PROJECT} ${PYTHON} manage.py shell_plus

## docker-collectstatic: Run django collectstatic in Docker container
docker-collectstatic:
	@echo
	@echo "> Collecting static assets in docker..."
	@${COMPOSE_LOCAL} ${DOCKER_RUN} \
		${PROJECT} ${PYTHON} manage.py collectstatic --noinput

## docker-bash: Run bash shell in Docker container
docker-bash:
	@echo
	@echo "> Running bash shell in docker..."
	@${COMPOSE_LOCAL} ${DOCKER_RUN} ${PROJECT} bash

## docker-superuser: Create superuser in Docker container
docker-superuser:
	@echo
	@echo "> Creating superuser in docker..."
	@${COMPOSE_LOCAL} ${DOCKER_RUN} \
		${PROJECT} ${PYTHON} manage.py createsuperuser
