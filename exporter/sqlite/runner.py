import sys
from pathlib import Path
from subprocess import run
from typing import Iterator

from django.conf import settings


class Runner:
    def __init__(self, db: Path) -> None:
        self.db = db

    def manage(self, *args: str):
        run(
            [sys.executable, sys.argv[0], *args],
            capture_output=False,
            env={
                "SQLITE": "1",
                "DATABASE_URL": f"sqlite:///{self.db}",
            },
        )

    def make_empty_database(self):
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
        cmd = run(
            ["sqlite3", str(self.db), "--cmd", f"PRAGMA table_info({table});"],
            capture_output=True,
            input="",
        )
        for column in cmd.stdout.splitlines():
            name: bytes = column.split(b"|")[1]
            yield name.decode("utf-8")

    def run_sqlite_script(self, script: str):
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
