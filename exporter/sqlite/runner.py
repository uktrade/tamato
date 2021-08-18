import decimal
import json
import logging
import os
import sqlite3
import sys
from pathlib import Path
from subprocess import run
from typing import Iterable
from typing import Iterator

from django.conf import settings

from exporter.sqlite.plan import Operation

logger = logging.getLogger(__name__)

# Cast Decimal objects to a string representation
# to preserve their precision. They can then be cast
# back to a Decimal without introducing error.
sqlite3.register_adapter(decimal.Decimal, str)


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
        sqlite_env = os.environ.copy()
        sqlite_env["DATABASE_URL"] = f"sqlite:///{self.db}"
        # Required to make sure the postgres default isn't set as the DB_URL
        if sqlite_env.get("VCAP_SERVICES"):
            vcap_env = json.loads(sqlite_env["VCAP_SERVICES"])
            vcap_env.pop("postgres", None)
            sqlite_env["VCAP_SERVICES"] = json.dumps(vcap_env)

        run(
            [sys.executable, "manage.py", *args],
            cwd=settings.BASE_DIR,
            capture_output=False,
            env=sqlite_env,
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
        with sqlite3.connect(str(self.db)) as connection:
            cursor = connection.cursor()
            cursor.execute(f"PRAGMA table_info({table})")
            for column in cursor.fetchall():
                yield column[1]

    def run_operations(self, operations: Iterable[Operation]):
        """Runs the supplied sequence of operations against the SQLite
        database."""
        with sqlite3.connect(
            str(self.db),
            detect_types=sqlite3.PARSE_DECLTYPES,
            isolation_level=None,
        ) as connection:
            cursor = connection.cursor()
            for operation in operations:
                logger.debug("%s: %s", self.db, operation[0])
                try:
                    cursor.executemany(*operation)
                except sqlite3.IntegrityError as e:
                    logger.error(e)
