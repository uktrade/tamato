from contextlib import redirect_stdout
from io import StringIO
from itertools import chain
from pathlib import Path

from django.apps import apps
from django.conf import settings

from exporter.sqlite import runner
from exporter.sqlite import script


def make_export(path: Path):
    sqlite = runner.Runner(path)
    sqlite.make_empty_database()

    names = (name.split(".")[0] for name in settings.DOMAIN_APPS)
    models = chain(*[apps.get_app_config(name).get_models() for name in names])

    output = StringIO()
    with redirect_stdout(output):
        with script.ImportScript() as import_script:
            for model in models:
                columns = list(sqlite.read_column_order(model._meta.db_table))
                import_script.add_table(model, columns)

    sqlite.run_sqlite_script(output.getvalue())
