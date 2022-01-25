#!/usr/bin/env python
from distutils.core import setup

import setuptools

setup(
    name="tamato",
    version="0.0.1",
    description="UK Tariff Management Tool",
    maintainer="Department for International Trade",
    maintainer_email="webops@digital.trade.gov.uk",
    url="https://github.com/uktrade/tamato",
    packages=setuptools.find_packages(),
    install_requires=[
        "dj-database-url",
        "django",
        "django-dotenv",
        "django-extra-fields",
        "django-filter",
        "django-fsm",
        "django-health-check",
        "django-polymorphic",
        "django-webpack-loader",
        "django_extensions",
        "djangorestframework",
        "gunicorn",
        "jinja2",
        "psycopg2-binary",
        "sentry-sdk",
        "werkzeug",
        "whitenoise",
    ],
    dependency_links=[
        "https://github.com/alphagov/govuk-frontend-jinja/tarball/master#egg=govuk-frontend-jinja",
    ],
)
