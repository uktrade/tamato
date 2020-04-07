# Tariff Management Tool (TAMATO)

## Quickstart

### Using Docker

Run the following command to build the docker image:

    docker build -t tamato .

Then to run the app:

    docker run -p 8000:8000 tamato

Then you can browse to http://localhost:8000/ to view the app

### Running locally

This app requires Python 3.8.x and Node 12.16.x

Create a Python virtualenv and install the dependencies:

    python -m venv venv
    . venv/bin/activate
    pip install -r requirements-dev.txt

Create a `.env` file containing environment variables:

    cp sample.env .env

Fetch and compile GOV.UK Frontend dependency:

    npm install
    npm run build

Collect static assets:

    ./manage.py collectstatic

Run the app:

    ./manage.py runserver

Then you can browse to http://localhost:8000/ to view the app

## Testing

To run tests use the following command:

    ./manage.py test

To run with coverage use the following:

    ./manage.py test -- --cov

## Environment Variables

| Name | Description |
| ---- | ----------- |
|      |             |

## How to deploy

## How to write tests

Tests are written with Pytest

## How to contribute

Please submit a Pull Request

### Formatting.

This project uses black as an autoformatter.

## How to change application dependencies (libraries)

## Known manual procedures
