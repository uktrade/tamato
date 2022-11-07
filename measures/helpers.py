from common.validators import UpdateType
from footnotes.models import Footnote
from measures.models import FootnoteAssociationMeasure
from measures.models import MeasureComponent
from measures.patterns import MeasureCreationPattern
from measures.util import diff_components
from workbaskets.models import WorkBasket


def update_measure(instance, request, cleaned_data):
    sid = instance.sid

    measure_creation_pattern = MeasureCreationPattern(
        workbasket=WorkBasket.current(request),
        base_date=instance.valid_between.lower,
        defaults={
            "generating_regulation": cleaned_data["generating_regulation"],
        },
    )

    if cleaned_data.get("exclusions"):
        for exclusion in cleaned_data.get("exclusions"):
            pattern = (
                measure_creation_pattern.create_measure_excluded_geographical_areas(
                    instance,
                    exclusion,
                )
            )
            [p for p in pattern]
    if (
        request.session[f"instance_duty_sentence_{instance.sid}"]
        != cleaned_data["duty_sentence"]
    ):
        diff_components(
            instance,
            cleaned_data["duty_sentence"],
            cleaned_data["valid_between"].lower,
            WorkBasket.current(request),
            # Creating components in the same transaction as the new version
            # of the measure minimises number of transaction and groups the
            # creation of measure and related objects in the same
            # transaction.
            instance.transaction,
            MeasureComponent,
            "component_measure",
        )

    footnote_pks = [
        dct["footnote"] for dct in request.session.get(f"formset_initial_{sid}", [])
    ]
    footnote_pks.extend(request.session.get(f"instance_footnotes_{sid}", []))

    request.session.pop(f"formset_initial_{sid}", None)
    request.session.pop(f"instance_footnotes_{sid}", None)

    for pk in footnote_pks:
        footnote = (
            Footnote.objects.filter(pk=pk)
            .approved_up_to_transaction(instance.transaction)
            .first()
        )

        existing_association = (
            FootnoteAssociationMeasure.objects.approved_up_to_transaction(
                instance.transaction,
            )
            .filter(
                footnoted_measure__sid=instance.sid,
                associated_footnote__footnote_id=footnote.footnote_id,
                associated_footnote__footnote_type__footnote_type_id=footnote.footnote_type.footnote_type_id,
            )
            .first()
        )
        if existing_association:
            existing_association.new_version(
                workbasket=WorkBasket.current(request),
                transaction=instance.transaction,
                footnoted_measure=instance,
            )
        else:
            FootnoteAssociationMeasure.objects.create(
                footnoted_measure=instance,
                associated_footnote=footnote,
                update_type=UpdateType.CREATE,
                transaction=instance.transaction,
            )

    return instance
