import csv
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


def subquery_test():
    subquery1 = ReportMeasureCondition.objects.values(
        "dependent_measure_id",
    ).annotate(
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
                        Value("certificate"),
                        F("required_certificate__certificate_type__sid"),
                        F("required_certificate__certificate_type__sid"),
                        F("required_certificate__sid"),
                    ),
                ),
                Value("action:"),
                "action__code",
                output_field=TextField(),
            ),
            delimiter="|",
            ordering=("condition_code__code", "component_sequence_number"),
        ),
    )
    return subquery1

    # subquery = ReportMeasureCondition.objects.filter(
    #     dependent_measure_id=OuterRef("pk")
    # ).values(
    #     'dependent_measure_id').annotate(
    #     condition_display=StringAgg(
    #         expression=Concat(
    #             Value("condition:"), "condition_code__code",
    #             Value("Certificate"),
    #             Value("action:"), "action__code",
    #             output_field=TextField()),
    #         delimiter="|",
    #         ordering=("condition_code__code", "component_sequence_number"),
    #     ))
    # return subquery


class MeasureExport:
    """Runs the export command against TAP data to extract Measure CSV data."""

    def __init__(self, target_file: NamedTemporaryFile):
        self.target_file = target_file

    @staticmethod
    def csv_headers():
        """
        Produces a list of headers for the CSV.

        Returns:
            list: list of header names
        """
        measure_headers = [
            "id",
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
        Returns a tuple of geographical areas and exclusions associated with a
        Quota.

        Args:
            measure: the measure to be queried

        Returns:
            tuple(str, str) : geographical areas and exclusions
        """
        geographical_area_ids = []
        geographical_area_descriptions = []

        # get all geographical areas that are / were / will be enabled on the end date of the measure
        for geo_area in (
            ReportMeasureExcludedGeographicalArea.objects.filter(
                modified_measure=measure.trackedmodel_ptr_id,
            )
            .select_related(
                "excluded_geographical_area",
            )
            .order_by("excluded_geographical_area_id")
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
        subquery = (
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
                    ordering="associated_footnote_id",
                ),
            )
        )

        measures = (
            ReportMeasure.objects.filter(sid__gte=20000000)
            .select_related(
                "trackedmodel_ptr",
                "goods_nomenclature",
                "order_number",
                "generating_regulation",
                "measure_type",
                "geographical_area",
                "additional_code",
                "additional_code__type",
            )
            .annotate(footnotes_id=Subquery(subquery.values("footnotes_id")))
        )

        # Add order by
        id = 0
        with open(self.target_file.name, "wt") as file:
            writer = csv.writer(file)
            writer.writerow(self.csv_headers())
            for measure in measures:
                id += 1
                print(id)
                if id > 2000:
                    return
                conditions = "conditions to be done"
                if measure.additional_code:
                    additional_code__code = f"{measure.additional_code.type.sid}{measure.additional_code.code}"
                    additional_code__description = measure.additional_code.description
                else:
                    additional_code__code = ""
                    additional_code__description = ""

                (
                    excluded_geographical_areas__ids,
                    excluded_geographical_areas__descriptions,
                ) = self.get_excluded_geographical_areas(measure)
                if measure.order_number:
                    order_number = measure.order_number.order_number
                else:
                    order_number = ""

                measure_data = [
                    id,
                    measure.goods_nomenclature.sid,
                    measure.goods_nomenclature.item_id,
                    measure.goods_nomenclature.indent,
                    measure.goods_nomenclature.description,
                    measure.sid,
                    measure.measure_type.sid,
                    measure.measure_type.description,
                    additional_code__code,
                    additional_code__description,
                    measure.duty_sentence,
                    measure.valid_between.lower,
                    measure.valid_between.upper,
                    measure.reduction,
                    measure.footnotes_id,
                    conditions,
                    measure.geographical_area.sid,
                    measure.geographical_area.area_id,
                    measure.geographical_area.description,
                    excluded_geographical_areas__ids,
                    excluded_geographical_areas__descriptions,
                    order_number,
                    measure.generating_regulation.public_identifier,
                    measure.generating_regulation.url,
                ]

                writer.writerow(measure_data)


# qs = ReportFootnoteAssociationMeasure.objects.annotate(
# fname =  Concat("associated_footnote__footnote_type__footnote_type_id",
# "associated_footnote__footnote_id",  output_field=CharField()))

# qs = ReportFootnoteAssociationMeasure.objects.annotate(
# fname = S Concat("associated_footnote__footnote_type__footnote_type_id",
# "associated_footnote__footnote_id",  output_field=CharField()))
