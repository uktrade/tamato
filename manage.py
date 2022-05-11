#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

import dotenv


def main():
    in_test = not {"pytest", "test"}.isdisjoint(sys.argv[1:])
    in_dev = "DEV" == os.environ.get("ENV")
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        "settings.test" if in_test else "settings.dev" if in_dev else "settings",
    )
    print("00000 ", os.environ.get("DJANGO_SETTINGS_MODULE")
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
    dotenv.read_dotenv()
    main()
