from additional_codes.models import AdditionalCode
from additional_codes.models import AdditionalCodeDescription
from footnotes.models import Footnote
from footnotes.models import FootnoteDescription
from footnotes.models import FootnoteType
from importer.management.commands.import_command import ImportCommand
from importer.management.commands.import_sheet import SheetImporter
from importer.management.commands.import_ukgt import NewRow
from importer.management.commands.import_ukgt import UKGTImporter
from importer.management.commands.patterns import OldMeasureRow
from importer.management.commands.utils import EnvelopeSerializer
from importer.management.commands.utils import id_argument
from importer.management.commands.utils import spreadsheet_argument
from workbaskets.models import WorkBasket


class Command(ImportCommand):
    help = "Import updates to the UKGT and TAPI"
    title = "UKGT and TAPI"

    def add_arguments(self, parser) -> None:
        spreadsheet_argument(parser, "new")
        spreadsheet_argument(parser, "old")
        id_argument(parser, "measure")
        id_argument(parser, "measure-condition")
        super().add_arguments(parser)

    def run(self, workbasket: WorkBasket, env: EnvelopeSerializer) -> None:
        # 1. Footnote type
        ft = SheetImporter(
            FootnoteType,
            workbasket,
            "footnote_type_id",
            "application_code",
            "description",
            "valid_between[0]",
            "valid_between[1]",
        )
        for model in ft.import_rows(self.get_sheet("new", "Footnote types", 1)):
            model.save()
            env.render_transaction([model])

        # 2. Footnotes + descriptions
        f = SheetImporter(
            Footnote,
            workbasket,
            None,
            "footnote_type",
            "footnote_id",
            "valid_between[0]",
            "valid_between[1]",
            None,
        )
        fd = SheetImporter(
            FootnoteDescription,
            workbasket,
            "description",
            "described_footnote[1]",
            "described_footnote[0]",
            "valid_between[0]",
            "valid_between[1]",
            "description_period_sid",
        )
        for row in self.get_sheet("new", "Footnotes", 1):
            models = []
            for primary in f.import_rows([row]):
                primary.save()
                models.append(primary)
            for description in fd.import_rows([row]):
                description.save()
                models.append(description)
            env.render_transaction(models)

        # 3. Additional codes + descriptions
        a = SheetImporter(
            AdditionalCode,
            workbasket,
            "sid",
            "type",
            "code",
            "valid_between[0]",
            "valid_between[1]",
            None,
            None,
        )
        ad = SheetImporter(
            AdditionalCodeDescription,
            workbasket,
            "described_additional_code",
            None,
            None,
            "valid_between[0]",
            "valid_between[1]",
            "description_period_sid",
            "description",
        )
        for row in self.get_sheet("new", "Add codes", 1):
            models = []
            for primary in a.import_rows([row]):
                primary.save()
                models.append(primary)
            for description in ad.import_rows([row]):
                description.save()
                models.append(description)
            env.render_transaction(models)

        # 4. Measures
        m = UKGTImporter(workbasket, env, counters=self.options["counters"])
        m.import_sheets(
            (NewRow(r) for r in self.get_sheet("new", "Measures")),
            (OldMeasureRow(r) for r in self.get_sheet("old", "Sheet")),
        )
