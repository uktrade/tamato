#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import warnings

import dotenv


def main():
    in_test = not {"pytest", "test"}.isdisjoint(sys.argv[1:])
    in_dev = in_test is False and "DEV" == str(os.environ.get("ENV")).upper()
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        "settings.test" if in_test else "settings.dev" if in_dev else "settings",
    )
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?",
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        dotenv.read_dotenv()
    main()
