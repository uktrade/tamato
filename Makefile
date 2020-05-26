PROJECT=tamato
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
	@${BIN}python manage.py collectstatic --noinput

compilescss:
	@echo
	@echo "> Compiling SCSS..."
	@npm run build

node_modules:
	@echo
	@echo "> Installing Javascript dependencies..."
	@npm ci

migrate:
	@echo
	@echo "> Running database migrations..."
	@python manage.py migrate --noinput

## run: Run webapp
run: export DJANGO_SETTINGS_MODULE=settings.dev
run: collectstatic migrate
	@echo
	@echo "> Running webapp..."
	@python manage.py runserver

run-cf: export DJANGO_SETTINGS_MODULE=settings
run-cf: collectstatic migrate
	@echo
	@echo "> Running webapp..."
	@gunicorn -b 0.0.0.0:8080 wsgi:application

## test: Run tests
test: export DJANGO_SETTINGS_MODULE=settings.test
test:
	@echo
	@echo "> Running tests..."
	python manage.py test

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
