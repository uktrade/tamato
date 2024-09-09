#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import warnings

import dotenv

ENV_INFO_FLAG = "--env-info"


def output_env_info():
    """Inspect and output environment diagnostics for help with platform /
    environment debugging."""

    from pathlib import Path

    cwd = Path().resolve()
    script_path = Path(__file__).resolve()
    executable_path = Path(sys.executable).resolve()
    path = os.environ.get("PATH")

    print("Environment diagnostics")
    print("----")
    print(f" Current working directory: {cwd}")
    print(f" Current script path: {script_path}")
    print(f" Python executable path: {executable_path}")
    print(f" PATH: {path}")
    print("----")

    # Remove the flag to avoid Django unknown command errors.
    sys.argv = [arg for arg in sys.argv if arg != ENV_INFO_FLAG]


def set_django_settings_module():
    """Set the DJANGO_SETTINGS_MODULE env var with an appropriate value."""

    in_test = not {"pytest", "test"}.isdisjoint(sys.argv[1:])
    in_dev = in_test is False and "DEV" == str(os.environ.get("ENV")).upper()
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        "settings.test" if in_test else "settings.dev" if in_dev else "settings",
    )


def main():
    if ENV_INFO_FLAG in sys.argv:
        output_env_info()

    set_django_settings_module()

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
        dotenv.load_dotenv()
    main()
