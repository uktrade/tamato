from datetime import datetime

from common.validators import UpdateType
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalMembership
from importer.management.commands.import_command import ImportCommand
from importer.management.commands.import_fta import FTAMeasuresImporter
from importer.management.commands.patterns import BREXIT
from importer.management.commands.patterns import OldMeasureRow
from importer.management.commands.utils import EnvelopeSerializer
from importer.management.commands.utils import spreadsheet_argument
from workbaskets.models import WorkBasket


class Command(ImportCommand):
    title = "Removal of Albania, Ghana and Jordan preferential regimes"

    def add_arguments(self, parser) -> None:
        spreadsheet_argument(parser, "old")
        super().add_arguments(parser)

    def run(self, workbasket: WorkBasket, env: EnvelopeSerializer) -> None:
        for area_id in ["GH", "AL", "JO", "ME"]:
            origin = GeographicalArea.objects.as_at(datetime.now()).get(area_id=area_id)
            rows = (
                row
                for row in (
                    OldMeasureRow(row) for row in self.get_sheet("old", "Sheet", 1)
                )
                if row.geo_sid == origin.sid
            )

            importer = FTAMeasuresImporter(
                workbasket,
                env,
                counters=self.options["counters"],
                staged_rows={},
                quotas={},
            )
            importer.import_sheets(iter([None]), rows)

        jo_gsp_general = GeographicalMembership(
            geo_group=GeographicalArea.objects.get(area_id="2020"),
            member=GeographicalArea.objects.get(area_id="JO"),
            valid_between=(BREXIT, None),
            workbasket=workbasket,
            update_type=UpdateType.CREATE,
        )
        jo_gsp_general.save()
        env.render_transaction([jo_gsp_general])
