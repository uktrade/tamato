import logging
from enum import Enum
from functools import cached_property
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional

from xlrd.sheet import Cell

from common.models import TrackedModel
from common.validators import UpdateType
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalMembership
from importer.management.commands.doc_importer import RowsImporter
from importer.management.commands.import_command import ImportCommand
from importer.management.commands.import_fta import FTAMeasuresImporter
from importer.management.commands.import_fta import MainMeasureRow
from importer.management.commands.import_wto import WTOMeasureImporter
from importer.management.commands.import_wto import WTOMeasureRow
from importer.management.commands.patterns import BREXIT
from importer.management.commands.patterns import MeasureCreatingPattern
from importer.management.commands.patterns import MeasureEndingPattern
from importer.management.commands.patterns import OldMeasureRow
from importer.management.commands.patterns import QuotaCreatingPattern
from importer.management.commands.quota_importer import QuotaRow
from importer.management.commands.utils import col
from importer.management.commands.utils import EnvelopeSerializer
from importer.management.commands.utils import id_argument
from importer.management.commands.utils import spreadsheet_argument
from measures.models import MeasureExcludedGeographicalArea
from quotas.models import QuotaAssociation
from quotas.models import QuotaDefinition
from quotas.models import QuotaOrderNumber
from quotas.models import QuotaOrderNumberOrigin
from quotas.models import QuotaOrderNumberOriginExclusion
from quotas.validators import QuotaCategory
from regulations.models import Regulation
from workbaskets.models import WorkBasket

logger = logging.getLogger(__name__)


class QuotaUpdateVerb(Enum):
    # ADD – add quota fresh, go through measures sheet and add measures, check
    # defns match the measure dates?
    ADD = "Add"
    # ASSOC – add a quota association between the two measures
    ASSOC = "Link to parent"
    # DELETE – remove quota defns and quota order number, remove measures
    DELETE = "Delete"
    # INTERIM – add a missing interim definition but no measure changes required
    INTERIM = "Define interim period"
    # PREF_MEASURES – add measures from the FTA file
    PREF_MEASURES = "Add pref measures"
    # REDEFINE – delete all quota definitions and replace with new ones
    REDEFINE = "Redefine quota period"
    # REPLACE_ORIGIN – delete all origins and replace with new
    REPLACE_ORIGIN = "Replace quota origin"
    # UNEXCLUDE – delete quota origin exclusion
    UNEXCLUDE = "Replace exclusions"
    # UPDATE – find the quota definitions and update the volumes
    UPDATE = "Update volume"
    # UPDATE_QON - replace quota order number id
    UPDATE_QON = "Update quota order number"
    # WTO_MEASURES – add measures from the WTO file
    WTO_MEASURES = "Add non-pref measures"


class ChangeMeasureImporter(RowsImporter):
    def __init__(
        self, *args, generating_regulation: Regulation, changes: Dict, **kwargs
    ) -> None:
        self.generating_regulation = generating_regulation
        self.changes = changes
        super().__init__(*args, **kwargs)

    def setup(self) -> Iterator[TrackedModel]:
        self.measure_ender = MeasureEndingPattern(
            workbasket=self.workbasket,
        )

        self.measure_creator = MeasureCreatingPattern(
            generating_regulation=self.generating_regulation,
            workbasket=self.workbasket,
            duty_sentence_parser=self.duty_sentence_parser,
            measure_sid_counter=self.counters["measure_id"],
            measure_condition_sid_counter=self.counters["measure_condition_id"],
        )

        return iter([])

    def handle_row(
        self, row: Optional[OldMeasureRow], old_row: Optional[OldMeasureRow]
    ) -> Iterator[List[TrackedModel]]:
        if old_row:
            endings = self.measure_ender.end_date_measure(
                old_row, self.generating_regulation
            )
            yield from ([m] for m in endings)

        if row:
            defaults = {
                "duty_sentence": row.duty_expression,
                "geography": row.geographical_area,
                "goods_nomenclature": row.goods_nomenclature,
                "new_measure_type": row.measure_type_object,
                "order_number": row.quota,
                "authorised_use": (
                    row.measure_type
                    in ("105", "123", "115", "117", "119", "145", "146")
                ),
                "additional_code": row.additional_code,
                "validity_start": row.measure_start_date,
                "validity_end": row.measure_end_date,
            }
            defaults.update(self.changes)
            beginnings = self.measure_creator.create(**defaults)
            yield list(beginnings)


class QuotaUpdateRow:
    def __init__(self, row: List[Cell]) -> None:
        self.quota_order_number = str(row[col("A")].value)
        self.verb = QuotaUpdateVerb(str(row[col("B")].value))
        self.notes = str(row[col("C")].value)

    @cached_property
    def quota(self) -> QuotaOrderNumber:
        return QuotaOrderNumber.objects.get(order_number=self.quota_order_number)


class Command(ImportCommand):
    help = "Update quotas"
    title = "Update quotas"

    def add_arguments(self, parser) -> None:
        spreadsheet_argument(parser, "new")
        spreadsheet_argument(parser, "old")
        spreadsheet_argument(parser, "wto")
        spreadsheet_argument(parser, "quota")
        parser.add_argument("changes", type=str)
        id_argument(parser, "measure")
        id_argument(parser, "measure-condition")
        id_argument(parser, "quota-order-number")
        id_argument(parser, "quota-order-number-origin")
        id_argument(parser, "quota-definition")
        id_argument(parser, "quota-suspension")
        super().add_arguments(parser)

    def get_existing_measures(self, quota_order_number: str) -> Iterator[OldMeasureRow]:
        rows = (OldMeasureRow(r) for r in self.get_sheet("old", "Sheet", 1))
        return (r for r in rows if r.order_number == f"05{quota_order_number[2:]}")

    def get_new_measures(self, quota: QuotaOrderNumber) -> Iterator[MainMeasureRow]:
        rows = (MainMeasureRow(r) for r in self.get_sheet("new", "MAIN", 1))
        return (r for r in rows if r.order_number == f"05{quota.order_number[2:]}")

    def get_wto_measures(self, quota: QuotaOrderNumber) -> Iterator[WTOMeasureRow]:
        rows = (
            WTOMeasureRow(r) for r in self.get_sheet("wto", self.options["changes"], 1)
        )
        return (r for r in rows if r.quota_number == quota.order_number)

    def run(self, workbasket: WorkBasket, env: EnvelopeSerializer) -> None:
        self.quotas = {
            row.order_number: row
            for row in (QuotaRow(r) for r in self.get_sheet("quota", "ALL", 1))
        }

        quota_creator = QuotaCreatingPattern(
            order_number_counter=self.options["counters"]["quota_order_number_id"],
            order_number_origin_counter=self.options["counters"][
                "quota_order_number_origin_id"
            ],
            definition_counter=self.options["counters"]["quota_definition_id"],
            suspension_counter=self.options["counters"]["quota_suspension_id"],
            workbasket=workbasket,
            critical_interim=False,
            start_date=BREXIT,
        )
        fta_importer = FTAMeasuresImporter(
            workbasket,
            env,
            counters=self.options["counters"],
            staged_rows={},
            quotas={},
        )

        if env.envelope_id == 210002:  # hack
            eu_group = GeographicalArea.objects.get(area_id="1013")
            safeguard_group = GeographicalArea.objects.get(area_id="5050")
            measures = (
                r.as_measure
                for r in (OldMeasureRow(r) for r in self.get_sheet("old", "Sheet", 1))
                if r.geo_sid == safeguard_group.sid and "European Union" in r.excluded_areas
            )
            areas = list(
                GeographicalMembership.objects
                .as_at(BREXIT)
                .filter(geo_group=eu_group)
                .exclude(member__area_id="EU")
            )
            for measure in measures:
                logger.debug("Exclude from %s", measure.sid)
                env.render_transaction(
                    [
                        MeasureExcludedGeographicalArea(
                            modified_measure=measure,
                            excluded_geographical_area=membership.member,
                            workbasket=workbasket,
                            update_type=UpdateType.CREATE,
                        )
                        for membership in areas
                    ]
                )

        updates = (
            QuotaUpdateRow(r)
            for r in self.get_sheet("quota", self.options["changes"], 1)
        )

        for row in updates:
            new = self.quotas.get(row.quota_order_number, None)
            logger.info("%s %s", row.verb, row.quota_order_number)

            if row.verb == QuotaUpdateVerb.DELETE:
                exists = QuotaOrderNumber.objects.filter(
                    order_number=row.quota_order_number
                ).exists()
                logger.info("Exists %s", exists)
                if not exists:
                    list(
                        quota_creator.create(
                            order_number=new.order_number,
                            mechanism=new.mechanism,
                            origins=new.origins,
                            category=QuotaCategory.PREFERENTIAL,
                            period_start_date=new.period_start,
                            period_end_date=new.period_end,
                            period_type=new.type,
                            unit=new.measurement,
                            volume=new.volume,
                            interim_volume=new.interim_volume,
                            parent_order_number=new.parent_order_number,
                            coefficient=new.coefficient,
                            excluded_origins=new.excluded_origins,
                        )
                    )

                fta_importer.import_sheets(
                    iter([None]), self.get_existing_measures(row.quota_order_number)
                )

                if exists:
                    for defn in QuotaDefinition.objects.filter(
                        order_number__order_number=row.quota_order_number
                    ):
                        logger.info("Deleting defn %s", defn)
                        for assoc in QuotaAssociation.objects.filter(sub_quota=defn):
                            logger.info("Deleting assoc %s", assoc)
                            env.render_transaction(
                                [
                                    assoc.new_draft(
                                        workbasket, update_type=UpdateType.DELETE
                                    )
                                ]
                            )
                        env.render_transaction(
                            [defn.new_draft(workbasket, update_type=UpdateType.DELETE)]
                        )
                    # for quota in QuotaOrderNumber.objects.filter(order_number=row.quota_order_number):
                    #    env.render_transaction([quota.new_draft(workbasket, update_type=UpdateType.DELETE)])

            elif row.verb == QuotaUpdateVerb.ADD:
                # Load quota rows from main sheet
                # Load measure rows
                for transaction in quota_creator.create(
                    order_number=new.order_number,
                    mechanism=new.mechanism,
                    origins=new.origins,
                    category=QuotaCategory.PREFERENTIAL,
                    period_start_date=new.period_start,
                    period_end_date=new.period_end,
                    period_type=new.type,
                    unit=new.measurement,
                    volume=new.volume,
                    interim_volume=new.interim_volume,
                    parent_order_number=new.parent_order_number,
                    coefficient=new.coefficient,
                    excluded_origins=new.excluded_origins,
                ):
                    env.render_transaction(transaction)

                fta_importer.quotas[new.order_number] = new
                fta_importer.import_sheets(
                    self.get_new_measures(row.quota), iter([None])
                )

            elif row.verb == QuotaUpdateVerb.ASSOC:
                # Find quota row from main sheet
                # Create quota association
                for defn in QuotaDefinition.objects.filter(order_number=row.quota):
                    association = quota_creator.associate_to_parent(
                        defn, str(new.parent_order_number), str(new.coefficient)
                    )
                    env.render_transaction([association])

            elif row.verb == QuotaUpdateVerb.INTERIM:
                # INTERIM – add a missing interim definition but no measure changes required
                assert not QuotaDefinition.objects.filter(
                    order_number=row.quota,
                    valid_between__contains=BREXIT,
                ).exists()
                new_end_date = new.period_end.replace(year=BREXIT.year)
                qd = quota_creator.define_quota(
                    quota=row.quota,
                    volume=new.interim_volume,
                    unit=new.measurement,
                    start_date=BREXIT,
                    end_date=new_end_date,
                )
                qd.save()
                env.render_transaction([qd])

            elif row.verb == QuotaUpdateVerb.REDEFINE:
                normal_dates, interim_dates = quota_creator.get_period_dates(
                    new.period_start, new.period_end, new.type
                )

                interim_qd = None
                if interim_dates:
                    # Find the existing definition which will presumably be live
                    # and update it, instead of trying to delete it
                    interim_start, interim_end = interim_dates
                    old_qd = QuotaDefinition.objects.get(
                        order_number=row.quota,
                        valid_between__contains=interim_start,
                    )
                    interim_qd = old_qd.new_draft(
                        workbasket,
                        valid_between=interim_dates,
                        volume=new.interim_volume,
                        initial_volume=new.interim_volume,
                        update_type=UpdateType.UPDATE,
                    )
                    env.render_transaction([interim_qd])

                    for old_qd in QuotaDefinition.objects.filter(
                        order_number=row.quota
                    ).exclude(id__in=[old_qd.id, interim_qd.id]):
                        deletion = old_qd.new_draft(
                            workbasket, update_type=UpdateType.DELETE
                        )
                        env.render_transaction([deletion])
                else:
                    for old_qd in QuotaDefinition.objects.filter(
                        order_number=row.quota
                    ):
                        deletion = old_qd.new_draft(
                            workbasket, update_type=UpdateType.DELETE
                        )
                        env.render_transaction([deletion])

                normal_qd = quota_creator.define_quota(
                    row.quota,
                    new.volume,
                    new.measurement,
                    *normal_dates,
                )
                normal_qd.save()

                env.render_transaction([normal_qd])

                # 4. Associate
                if new.parent_order_number:
                    assert new.coefficient
                    association = self.associate_to_parent(
                        normal_qd, new.parent_order_number, new.coefficient
                    )
                    association.save()
                    env.render_transaction([association])

                    if interim_qd:
                        association = self.associate_to_parent(
                            interim_qd, new.parent_order_number, new.coefficient
                        )
                        association.save()
                        env.render_transaction([association])

            # REPLACE_ORIGIN – delete all origins and replace with new
            elif row.verb == QuotaUpdateVerb.REPLACE_ORIGIN:
                geo_id = row.notes.strip()
                if geo_id != "":
                    replacing = [
                        GeographicalArea.objects.get(area_id=row.notes.strip())
                    ]
                else:
                    replacing = [
                        q.geographical_area
                        for q in QuotaOrderNumberOrigin.objects.filter(
                            order_number=row.quota
                        )
                    ]

                logger.info("Replacing %s with %s", replacing, new.origins)
                matching = lambda: (
                    r
                    for r in self.get_existing_measures(row.quota_order_number)
                    if r.geographical_area in replacing
                )
                for measure_row in matching():
                    measure = measure_row.as_measure
                    measure.workbasket = workbasket
                    measure.update_type = UpdateType.DELETE
                    env.render_transaction([measure])

                models = [quota_creator.add_origin(row.quota, o) for o in new.origins]
                for origin in QuotaOrderNumberOrigin.objects.filter(
                    order_number=row.quota,
                    geographical_area__in=replacing,
                ):
                    models.append(
                        origin.new_draft(workbasket, update_type=UpdateType.DELETE)
                    )
                env.render_transaction(models)

                for origin in new.origins:
                    ChangeMeasureImporter(
                        workbasket,
                        env,
                        generating_regulation=Regulation.objects.get(
                            regulation_id="C2100007"
                        ),
                        changes={"geography": origin},
                        counters=self.options["counters"],
                    ).import_sheets(
                        matching(),
                        iter([None]),
                    )

            # UNEXCLUDE – delete quota origin exclusion
            elif row.verb == QuotaUpdateVerb.UNEXCLUDE:
                origin = QuotaOrderNumberOrigin.objects.get(order_number=row.quota)
                currently_excluded = set(origin.excluded_areas.all())
                to_be_excluded = set(new.excluded_origins)
                to_delete = currently_excluded - to_be_excluded
                to_add = to_be_excluded - currently_excluded
                models = []
                for addition in to_add:
                    for model in quota_creator.exclude_origin(origin, addition):
                        models.append(model)
                for deletion in to_delete:
                    exclusion = QuotaOrderNumberOriginExclusion.objects.get(
                        origin=origin, excluded_geographical_area=deletion
                    )
                    models.append(
                        exclusion.new_draft(workbasket, update_type=UpdateType.DELETE)
                    )
                env.render_transaction(models)

            # UPDATE – find the quota definitions and update the volumes
            elif row.verb == QuotaUpdateVerb.UPDATE:
                logger.debug(
                    "New period: %s -> %s @ %s (int. @ %s)",
                    new.period_start,
                    new.period_end,
                    new.volume,
                    new.interim_volume,
                )
                updated = False
                for defn in QuotaDefinition.objects.filter(order_number=row.quota):
                    defn.workbasket = workbasket
                    defn.update_type = UpdateType.UPDATE
                    defn_start = defn.valid_between.lower
                    logger.debug(
                        "Considering defn: %s @ %s", defn.valid_between, defn.volume
                    )
                    if (
                        defn_start.month != new.period_start.month
                        or defn_start.day != new.period_start.day
                    ) and defn.volume != new.interim_volume:
                        # update interim
                        updated = True
                        defn.volume = new.interim_volume
                        defn.initial_volume = new.interim_volume
                        env.render_transaction([defn])
                    elif (
                        defn_start.month == new.period_start.month
                        and defn_start.day == new.period_start.day
                        and defn.volume != new.volume
                    ):
                        # update regular
                        updated = True
                        defn.volume = new.volume
                        defn.initial_volume = new.volume
                        env.render_transaction([defn])

                if not updated:
                    logger.warning(
                        "Nothing to UPDATE for quota %s?", row.quota_order_number
                    )

            # WTO_MEASURES – import WTO measures to a pre-existing quota
            elif row.verb == QuotaUpdateVerb.WTO_MEASURES:
                importer = WTOMeasureImporter(
                    workbasket,
                    env,
                    counters=self.options["counters"],
                    quotas=self.quotas,
                )
                importer.import_sheets(
                    self.get_wto_measures(row.quota),
                    iter([None]),
                )

            # PREF_MEASURES – import FTA measures to a pre-existing quota
            elif row.verb == QuotaUpdateVerb.PREF_MEASURES:
                fta_importer.import_sheets(
                    self.get_new_measures(row.quota),
                    iter([None]),
                )

            elif row.verb == QuotaUpdateVerb.UPDATE_QON:
                new_qon = row.notes.strip()
                assert new_qon == "0" + str(int(new_qon))

                for measure_row in self.get_existing_measures(row.quota_order_number):
                    measure = measure_row.as_measure
                    measure.workbasket = workbasket
                    measure.update_type = UpdateType.DELETE
                    env.render_transaction([measure])

                models = [
                    row.quota.new_draft(
                        order_number=new_qon,
                        workbasket=workbasket,
                        update_type=UpdateType.UPDATE,
                    )
                ]

                for defn in QuotaDefinition.objects.filter(
                    order_number__order_number=row.quota
                ):
                    models.append(
                        defn.new_draft(
                            order_number=models[0],
                            workbasket=workbasket,
                            update_type=UpdateType.UPDATE,
                        )
                    )
                env.render_transaction(models)

                importer = ChangeMeasureImporter(
                    workbasket,
                    env,
                    generating_regulation=Regulation.objects.get(
                        regulation_id="C2100006"
                    ),
                    changes={"order_number": models[0]},
                    counters=self.options["counters"],
                )
                importer.import_sheets(
                    self.get_existing_measures(row.quota_order_number), iter([None])
                )
