from contextlib import redirect_stdout
from io import StringIO
from itertools import chain
from pathlib import Path
from tempfile import TemporaryDirectory

from django.apps import apps
from django.conf import settings

from exporter.sqlite import runner
from exporter.sqlite import script


def make_export_script(sqlite: runner.Runner, directory: Path = None):
    directory = directory or Path(TemporaryDirectory().name)

    with script.ImportScript(directory) as import_script:
        names = (name.split(".")[0] for name in settings.DOMAIN_APPS)
        models = chain(*[apps.get_app_config(name).get_models() for name in names])
        for model in models:
            columns = list(sqlite.read_column_order(model._meta.db_table))
            import_script.add_table(model, columns)

    return import_script


def make_export(path: Path):
    sqlite = runner.Runner(path)
    sqlite.make_empty_database()

    with TemporaryDirectory() as tempdir:
        output = StringIO()
        with redirect_stdout(output):
            make_export_script(sqlite, Path(tempdir))
        sqlite.run_sqlite_script(output.getvalue())
