import csv
import datetime
import logging
from tempfile import NamedTemporaryFile

from django.contrib.postgres.aggregates import StringAgg
from django.db.models import Case
from django.db.models import CharField
from django.db.models import F
from django.db.models import OuterRef
from django.db.models import Q
from django.db.models import Subquery
from django.db.models import TextField
from django.db.models import Value
from django.db.models import When
from django.db.models.functions import Concat

from open_data.models import ReportFootnoteAssociationMeasure
from open_data.models import ReportMeasure
from open_data.models import ReportMeasureCondition
from open_data.models import ReportMeasureExcludedGeographicalArea

logger = logging.getLogger(__name__)


def normalise_loglevel(loglevel):
    """
    Attempt conversion of `loglevel` from a string integer value (e.g. "20") to
    its loglevel name (e.g. "INFO").

    This function can be used after, for instance, copying log levels from
    environment variables, when the incorrect representation (int as string
    rather than the log level name) may occur.
    """
    try:
        return logging._levelToName.get(int(loglevel))
    except:
        return loglevel


class MeasureExport:
    """Runs the export command against TAP data to extract Measure CSV data."""

    def __init__(
        self,
        target_file: NamedTemporaryFile,
        include_future_measure: bool = False,
    ):
        self.target_file = target_file
        self.include_future_measure = include_future_measure

    @staticmethod
    def csv_headers():
        """
        Produces a list of headers for the CSV.

        Returns:
            list: list of header names
        """
        measure_headers = [
            "id",
            "trackedmodel_ptr_id",
            "commodity__sid",
            "commodity__code",
            "commodity__indent",
            "commodity__description",
            "measure__sid",
            "measure__type__id",
            "measure__type__description",
            "measure__additional_code__code",
            "measure__additional_code__description",
            "measure__duty_expression",
            "measure__effective_start_date",
            "measure__effective_end_date",
            "measure__reduction_indicator",
            "measure__footnotes",
            "measure__conditions",
            "measure__geographical_area__sid",
            "measure__geographical_area__id",
            "measure__geographical_area__description",
            "measure__excluded_geographical_areas__ids",
            "measure__excluded_geographical_areas__descriptions",
            "measure__quota__order_number",
            "measure__regulation__id",
            "measure__regulation__url",
        ]

        return measure_headers

    @staticmethod
    def get_excluded_geographical_areas(measure):
        """
        Returns a tuple of geographical areas  exclusions associated with a
        measure.

        Args:
            measure: the measure to be queried

        Returns:
            tuple(str, str) : geographical exclusions ID and description
        """
        geographical_area_ids = []
        geographical_area_descriptions = []

        for geo_area in (
            ReportMeasureExcludedGeographicalArea.objects.filter(
                modified_measure=measure.trackedmodel_ptr_id,
            )
            .select_related(
                "excluded_geographical_area",
            )
            .order_by("excluded_geographical_area__area_id")
        ):
            if geo_area.excluded_geographical_area.area_id:
                geographical_area_ids.append(
                    geo_area.excluded_geographical_area.area_id,
                )
            if geo_area.excluded_geographical_area.description:
                geographical_area_descriptions.append(
                    geo_area.excluded_geographical_area.description,
                )

        if geographical_area_ids:
            geographical_area_ids_str = "|".join(geographical_area_ids)
        else:
            geographical_area_ids_str = ""

        if geographical_area_descriptions:
            geographical_area_descriptions_str = "|".join(
                geographical_area_descriptions,
            )
        else:
            geographical_area_descriptions_str = ""

        return geographical_area_ids_str, geographical_area_descriptions_str

    def run(self):
        footnote_subquery = (
            ReportFootnoteAssociationMeasure.objects.filter(
                footnoted_measure=OuterRef("pk"),
            )
            .values(
                "footnoted_measure",
            )
            .annotate(
                footnotes_id=StringAgg(
                    expression=Concat(
                        "associated_footnote__footnote_type__footnote_type_id",
                        "associated_footnote__footnote_id",
                        output_field=CharField(),
                    ),
                    delimiter="|",
                    ordering=(
                        "associated_footnote__footnote_type__footnote_type_id",
                        "associated_footnote__footnote_id",
                    ),
                ),
            )
        )

        condition_subquery = (
            ReportMeasureCondition.objects.filter(
                dependent_measure_id=OuterRef("pk"),
            )
            .values(
                "dependent_measure_id",
            )
            .annotate(
                condition_display=StringAgg(
                    expression=Concat(
                        Value("condition:"),
                        "condition_code__code",
                        Case(
                            When(
                                Q(required_certificate__isnull=True),
                                then=Value(""),
                            ),
                            default=Concat(
                                Value(",certificate:"),
                                F("required_certificate__certificate_type__sid"),
                                F("required_certificate__sid"),
                            ),
                        ),
                        Value(",action:"),
                        "action__code",
                        output_field=TextField(),
                    ),
                    delimiter="|",
                    ordering=("condition_code__code", "component_sequence_number"),
                ),
            )
        )
        # hard coded date for testing
        filter_date = datetime.date(2025, 1, 13)
        measure_base = ReportMeasure.objects.filter(sid__gte=20000000)
        if not self.include_future_measure:
            measure_base = measure_base.filter(valid_between__contains=filter_date)

        measures = (
            measure_base.select_related(
                "trackedmodel_ptr",
                "goods_nomenclature",
                "order_number",
                "generating_regulation",
                "measure_type",
                "geographical_area",
                "additional_code",
                "additional_code__type",
            )
            .annotate(footnotes_id=Subquery(footnote_subquery.values("footnotes_id")))
            .annotate(
                conditions=Subquery(condition_subquery.values("condition_display")),
            )
            .order_by(
                "goods_nomenclature__item_id",
                "measure_type__sid",
                "geographical_area__area_id",
            )
        )

        id = 0
        with open(self.target_file.name, "wt") as file:
            writer = csv.writer(file)
            writer.writerow(self.csv_headers())
            for measure in measures:
                id += 1
                if id % 1000 == 0:
                    print(id)

                (
                    excluded_geographical_areas_ids,
                    excluded_geographical_areas_descriptions,
                ) = self.get_excluded_geographical_areas(measure)

                if measure.additional_code:
                    additional_code_code = f"{measure.additional_code.type.sid}{measure.additional_code.code}"
                    additional_code_description = measure.additional_code.description
                else:
                    additional_code_code = ""
                    additional_code_description = ""

                if measure.order_number:
                    order_number = measure.order_number.order_number
                else:
                    order_number = measure.dead_order_number

                if measure.goods_nomenclature:
                    goods_nomenclature_sid = measure.goods_nomenclature.sid
                    goods_nomenclature_item_id = measure.goods_nomenclature.item_id
                    goods_nomenclature_indent = measure.goods_nomenclature.indent
                    goods_nomenclature_description = (
                        measure.goods_nomenclature.description
                    )
                else:
                    goods_nomenclature_sid = ""
                    goods_nomenclature_item_id = ""
                    goods_nomenclature_indent = ""
                    goods_nomenclature_description = ""

                if measure.geographical_area:
                    geographical_area_sid = measure.geographical_area.sid
                    geographical_area_area_id = measure.geographical_area.area_id
                    geographical_area_description = (
                        measure.geographical_area.description
                    )
                else:
                    geographical_area_sid = ""
                    geographical_area_area_id = ""
                    geographical_area_description = ""

                if measure.measure_type:
                    measure_type_sid = measure.measure_type.sid
                    measure_type_description = measure.measure_type.description
                else:
                    measure_type_sid = ""
                    measure_type_description = ""

                measure_data = [
                    id,
                    measure.trackedmodel_ptr_id,
                    goods_nomenclature_sid,
                    goods_nomenclature_item_id,
                    goods_nomenclature_indent,
                    goods_nomenclature_description,
                    measure.sid,
                    measure_type_sid,
                    measure_type_description,
                    additional_code_code,
                    additional_code_description,
                    measure.duty_sentence,
                    measure.valid_between.lower,
                    measure.valid_between.upper,
                    measure.reduction,
                    measure.footnotes_id,
                    measure.conditions,
                    geographical_area_sid,
                    geographical_area_area_id,
                    geographical_area_description,
                    excluded_geographical_areas_ids,
                    excluded_geographical_areas_descriptions,
                    order_number,
                    measure.generating_regulation.public_identifier,
                    measure.generating_regulation.url,
                ]

                writer.writerow(measure_data)
