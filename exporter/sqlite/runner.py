import sys
from pathlib import Path
from subprocess import run
from typing import Iterator

from django.conf import settings


class Runner:
    """Runs commands on an SQLite database."""

    def __init__(self, db: Path) -> None:
        self.db = db

    def manage(self, *args: str):
        """
        Runs a Django management command on the SQLite database.

        This management command will be run such that ``settings.SQLITE`` is
        True, allowing SQLite specific functionality to be switched on and off
        using the value of this setting.
        """
        run(
            [sys.executable, "manage.py", *args],
            cwd=settings.BASE_DIR,
            capture_output=False,
            env={
                "DATABASE_URL": f"sqlite:///{self.db}",
            },
        )

    def make_empty_database(self):
        """
        Generate a new and empty SQLite database with the TaMaTo schema.

        Because SQLite uses different fields to PostgreSQL, first missing
        migrations are generated to bring in the different style of validity
        fields. However, these should not generally stick around and be applied
        to Postgres so they are removed after being applied.
        """
        try:
            self.manage("makemigrations", "--name", "sqlite_export")
            self.manage("migrate")
            assert self.db.exists()
        finally:
            for file in Path(settings.BASE_DIR).rglob(
                "**/migrations/*sqlite_export.py",
            ):
                file.unlink()

    def read_column_order(self, table: str) -> Iterator[str]:
        """
        Returns the name of the columns in the order they are defined in an
        SQLite database.

        This is necessary because the Django migrations do not generate the
        columns in the order they are defined on the model, and there's no other
        easy way to work out what the correct order is aside from reading them.
        """
        cmd = run(
            ["sqlite3", str(self.db), "--cmd", f"PRAGMA table_info({table});"],
            capture_output=True,
            input="",
        )
        for column in cmd.stdout.splitlines():
            name: bytes = column.split(b"|")[1]
            yield name.decode("utf-8")

    def run_sqlite_script(self, script: str):
        """
        Runs the supplied SQLite script against the SQLite database.

        The script is run in an environment with the same credentials as the
        main Django instance giving it full access to the database.
        """
        database = settings.DATABASES["default"]
        return run(
            ["sqlite3", str(self.db)],
            capture_output=False,
            input=script.encode("utf-8"),
            env={
                "PGHOST": database["HOST"],
                "PGPORT": str(database["PORT"]),
                "PGUSER": database["USER"],
                "PGPASSWORD": database["PASSWORD"],
                "PGDATABASE": database["NAME"],
            },
        )
