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
	@docker-compose -f docker-compose-test.yml run \
		${PROJECT} ${PYTHON} manage.py test -- -n=auto --dist=loadfile --cov

## clean-docs: Clean the generated documentation files
clean-docs:
	@rm -f docs/source/training/*.rst
	@rm -rf docs/build

## build-docs: Build the project documentation
build-docs html:
	@sphinx-gherkindoc --raw-descriptions "docs/source/training" "docs/source/training"
	@for FILE in $$(ls -1 docs/source/training/*.rst | grep -v gherkin); do $(BASH) docs/source/training/augment.sh $$FILE; done
	@cd docs && sphinx-build -M html "source" "build"


## docker-first-use: Run application for first time in Docker 
docker-first-use:
	@echo
	@echo "> Running db in docker..."
	@docker-compose down
	@docker-compose up -d db
	@echo "> Running migrate in docker..."
	@docker-compose run --rm \
		${PROJECT} ${PYTHON} manage.py migrate
	@echo "> Run docker container..."
	@docker-compose up 

## docker-migrations: Run django makemigrations in Docker
docker-migrations:
	@echo
	@echo "> Running makemigrations in docker..."
	@docker-compose run --rm \
		${PROJECT} ${PYTHON} manage.py makemigrations

## docker-migrate: Run django makemigrations in Docker container
docker-migrate:
	@echo
	@echo "> Running database migrations in docker..."
	@docker-compose run --rm \
		${PROJECT} ${PYTHON}  manage.py migrate

## docker-migrations: Run django makemigrations in Docker container
docker-checkmigrations:
	@echo
	@echo "> Running check migrations in docker..."
	@docker-compose run --rm --no-deps \
		${PROJECT} ${PYTHON}  manage.py makemigrations --check

## docker-shell: Run django shell in Docker container
docker-shell:
	@echo
	@echo "> Running django shell  in docker..."
	@docker-compose run --rm \
		${PROJECT} ${PYTHON} manage.py shell

## docker-collectstatic: Run django collectstatic in Docker container
docker-collectstatic:
	@echo
	@echo "> Collecting static assets in docker..."
	@docker-compose run --rm \
		${PROJECT} ${PYTHON}  manage.py collectstatic

## docker-bash: Run bash shell in Docker container
docker-bash:
	@echo
	@echo "> Running bash shell in docker..."
	@docker-compose run --rm ${PROJECT} bash

## docker-pytest: Run pytest in Docker container
docker-pytest:
	@echo
	@echo "> Running pytest in docker..."
	@docker-compose -f docker-compose-test.yml run --rm \
		${PROJECT} ${PYTHON} -m pytest -n=auto --dist=loadfile --alluredir=allure-results --nomigrations --cov --cov-report html:htmlcov --cov-report=term --cov-report=xml

## docker-superuser: Create superuser in Docker container
docker-superuser:
	@echo
	@echo "> Creating superuser in docker..."
	@docker-compose run --rm \
		${PROJECT} ${PYTHON} manage.py createsuperuser
