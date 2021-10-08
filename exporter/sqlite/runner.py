import json
import logging
import os
import sys
from pathlib import Path
from subprocess import run
from tempfile import NamedTemporaryFile
from typing import Iterable
from typing import Iterator

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
    def manage(cls, db: Path, *args: str):
        """
        Runs a Django management command on the SQLite database.

        This management command will be run such that ``settings.SQLITE`` is
        True, allowing SQLite specific functionality to be switched on and off
        using the value of this setting.
        """
        sqlite_env = os.environ.copy()
        sqlite_env["DATABASE_URL"] = f"sqlite:///{str(db)}"
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
    def from_empty_database(cls) -> "Runner":
        """
        Generate a new and empty SQLite database with the TaMaTo schema.

        Because SQLite uses different fields to PostgreSQL, first missing
        migrations are generated to bring in the different style of validity
        fields. However, these should not generally stick around and be applied
        to Postgres so they are removed after being applied.
        """
        try:
            with NamedTemporaryFile() as db_name:
                db = Path(db_name.name)
                cls.manage(db, "makemigrations", "--name", "sqlite_export")
                cls.manage(db, "migrate")
                assert db.exists()

                # Copy the template database into memory.
                template = apsw.Connection(str(db))
                runner = cls(apsw.Connection(":memory:"))
                runner.database.deserialize("main", template.serialize("main"))
                return runner
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
        cursor = self.database.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        for column in cursor.fetchall():
            yield column[1]

    def run_operations(self, operations: Iterable[Operation]):
        """Runs the supplied sequence of operations against the SQLite
        database."""
        cursor = self.database.cursor()
        for operation in operations:
            logger.debug("%s: %s", self.database, operation[0])
            try:
                cursor.executemany(*operation)
            except apsw.SQLError as e:
                logger.error(e)

    def get_bytes(self) -> bytes:
        """Returns the bytes of the SQLite database."""
        return self.database.serialize("main")
