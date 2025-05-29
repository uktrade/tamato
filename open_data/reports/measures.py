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
from open_data.models.report_models import ReportMeasureAsDefinedReport


def get_excluded_geographical_areas(measure):
    """
    Returns a tuple of geographical areas  exclusions associated with a measure.

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


def create_measure_as_defined_report(verbose=True):
    """Produces data for the Measures as Defined report (including future
    measures), stored in an open_data table."""

    ReportMeasureAsDefinedReport.objects.all().delete()

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
    measure_base = ReportMeasure.objects.filter(sid__gte=20000000)

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

    if verbose:
        print(f"Measures: {measures.count()} rows")
    for measure in measures:
        id += 1
        if verbose:
            if id % 1000 == 0:
                print(f"Completed {id} rows of Measures")

        (
            excluded_geographical_areas_ids,
            excluded_geographical_areas_descriptions,
        ) = get_excluded_geographical_areas(measure)

        if measure.additional_code:
            additional_code_code = (
                f"{measure.additional_code.type.sid}{measure.additional_code.code}"
            )
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
            goods_nomenclature_description = measure.goods_nomenclature.description
        else:
            goods_nomenclature_sid = ""
            goods_nomenclature_item_id = ""
            goods_nomenclature_indent = ""
            goods_nomenclature_description = ""

        if measure.geographical_area:
            geographical_area_sid = measure.geographical_area.sid
            geographical_area_area_id = measure.geographical_area.area_id
            geographical_area_description = measure.geographical_area.description
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

        ReportMeasureAsDefinedReport.objects.create(
            id=id,
            trackedmodel_ptr_id=measure.trackedmodel_ptr_id,
            commodity_sid=goods_nomenclature_sid,
            commodity_code=goods_nomenclature_item_id,
            commodity_indent=goods_nomenclature_indent,
            commodity_description=goods_nomenclature_description,
            measure_sid=measure.sid,
            measure_type_id=measure_type_sid,
            measure_type_description=measure_type_description,
            measure_additional_code_code=additional_code_code,
            measure_additional_code_description=additional_code_description,
            measure_duty_expression=measure.duty_sentence,
            measure_effective_start_date=measure.valid_between.lower,
            measure_effective_end_date=measure.valid_between.upper,
            measure_reduction_indicator=measure.reduction,
            measure_footnotes=measure.footnotes_id,
            measure_conditions=measure.conditions,
            measure_geographical_area_sid=geographical_area_sid,
            measure_geographical_area_id=geographical_area_area_id,
            measure_geographical_area_description=geographical_area_description,
            measure_excluded_geographical_areas_ids=excluded_geographical_areas_ids,
            measure_excluded_geographical_areas_descriptions=excluded_geographical_areas_descriptions,
            measure_quota_order_number=order_number,
            measure_regulation_id=measure.generating_regulation.public_identifier,
            measure_regulation_url=measure.generating_regulation.url,
        )
