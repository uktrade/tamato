import json
import logging
import os
import sys
from pathlib import Path
from subprocess import run
from typing import Iterable
from typing import Iterator
from typing import Tuple

import apsw
from django.conf import settings

from exporter.sqlite.plan import Operation

logger = logging.getLogger(__name__)


class Runner:
    """Runs commands on an SQLite database."""

    database: apsw.Connection

    def __init__(self, database: apsw.Connection) -> None:
        self.database = database

    @classmethod
    def normalise_loglevel(cls, loglevel):
        """
        Attempt conversion of `loglevel` from a string integer value (e.g. "20")
        to its loglevel name (e.g. "INFO").

        This function can be used after, for instance, copying log levels from
        environment variables, when the incorrect representation (int as string
        rather than the log level name) may occur.
        """
        try:
            return logging._levelToName.get(int(loglevel))
        except:
            return loglevel

    @classmethod
    def manage(cls, sqlite_file: Path, *args: str):
        """
        Runs a Django management command on the SQLite database.

        This management command will be run such that ``settings.SQLITE`` is
        True, allowing SQLite specific functionality to be switched on and off
        using the value of this setting.
        """
        sqlite_env = os.environ.copy()

        # Correct log levels that are incorrectly expressed as string ints.
        if "CELERY_LOG_LEVEL" in sqlite_env:
            sqlite_env["CELERY_LOG_LEVEL"] = cls.normalise_loglevel(
                sqlite_env["CELERY_LOG_LEVEL"],
            )

        sqlite_env["DATABASE_URL"] = f"sqlite:///{str(sqlite_file)}"
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

    @classmethod
    def make_tamato_database(cls, sqlite_file: Path) -> "Runner":
        """Generate a new and empty SQLite database with the TaMaTo schema
        derived from Tamato's models - by performing 'makemigrations' followed
        by 'migrate' on the Sqlite file located at `sqlite_file`."""
        try:
            # Because SQLite uses different fields to PostgreSQL, missing
            # migrations are first generated to bring in the different style of
            # validity fields. However, these should not be applied to Postgres
            # and so should be removed (in the `finally` block) after they have
            # been applied (when running `migrate`).
            cls.manage(sqlite_file, "makemigrations", "--name", "sqlite_export")
            cls.manage(sqlite_file, "migrate")
            assert sqlite_file.exists()
            return cls(apsw.Connection(str(sqlite_file)))
        finally:
            for file in Path(settings.BASE_DIR).rglob(
                "**/migrations/*sqlite_export.py",
            ):
                file.unlink()

    def read_schema(self, type: str) -> Iterator[Tuple[str, str]]:
        """
        Generator yielding a tuple of 'name' and 'sql' column values from
        Sqlite's "schema table", 'sqlite_schema'.

        The `type` param filters rows that have a matching 'type' column value,
        which may be any one of: 'table', 'index', 'view', or 'trigger'.

        See https://www.sqlite.org/schematab.html for further details.
        """
        cursor = self.database.cursor()
        cursor.execute(
            f"""
            SELECT 
                name, sql
            FROM
                sqlite_master
            WHERE 
                sql IS NOT NULL
                AND type = '{type}'
                AND name NOT LIKE 'sqlite_%'
            """,
        )
        yield from cursor.fetchall()

    @property
    def tables(self) -> Iterator[Tuple[str, str]]:
        """Generator yielding a tuple of each Sqlite table object's 'name' and
        the SQL `CREATE_TABLE` statement that can be used to create the
        table."""
        yield from self.read_schema("table")

    @property
    def indexes(self) -> Iterator[Tuple[str, str]]:
        """Generator yielding a tuple of each SQLite table index object name and
        the SQL `CREATE_INDEX` statement that can be used to create it."""
        yield from self.read_schema("index")

    def read_column_order(self, table: str) -> Iterator[str]:
        """
        Returns the name of `table`'s columns in the order they are defined in
        an SQLite database.

        This is necessary because the Django migrations do not generate the
        columns in the order they are defined on the model, and there's no other
        easy way to work out what the correct order is aside from reading them.
        """
        cursor = self.database.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        for column in cursor.fetchall():
            yield column[1]

    def run_operations(self, operations: Iterable[Operation]):
        """Runs each operation in `operations` against `database` member
        attribute (a connection object to an SQLite database file)."""
        cursor = self.database.cursor()
        for operation in operations:
            logger.debug("%s: %s", self.database, operation[0])
            try:
                cursor.executemany(*operation)
            except apsw.SQLError as e:
                logger.error(e)
