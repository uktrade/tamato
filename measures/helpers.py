from common.validators import UpdateType
from footnotes.models import Footnote
from measures.models import FootnoteAssociationMeasure
from measures.models import MeasureComponent
from measures.models import MeasureCondition
from measures.models import MeasureConditionComponent
from measures.parsers import DutySentenceParser
from measures.patterns import MeasureCreationPattern
from measures.util import diff_components


def update_measure(instance, transaction, current_workbasket, cleaned_data, defaults):

    measure_creation_pattern = MeasureCreationPattern(
        workbasket=current_workbasket,
        base_date=instance.valid_between.lower,
        defaults=defaults,
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
        cleaned_data.get("duty_sentence")
        and instance.duty_sentence != cleaned_data["duty_sentence"]
    ):
        diff_components(
            instance,
            cleaned_data["duty_sentence"],
            cleaned_data["valid_between"].lower,
            current_workbasket,
            # Creating components in the same transaction as the new version
            # of the measure minimises number of transaction and groups the
            # creation of measure and related objects in the same
            # transaction.
            transaction,
            MeasureComponent,
            "component_measure",
        )

    return instance.new_version(current_workbasket)


def update_measure_footnotes(instance, transaction, current_workbasket, footnote_pks):

    for pk in footnote_pks:
        footnote = (
            Footnote.objects.filter(pk=pk)
            .approved_up_to_transaction(transaction)
            .first()
        )

        existing_association = (
            FootnoteAssociationMeasure.objects.approved_up_to_transaction(
                transaction,
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
                workbasket=current_workbasket,
                transaction=transaction,
                footnoted_measure=instance,
            )
        else:
            FootnoteAssociationMeasure.objects.create(
                footnoted_measure=instance,
                associated_footnote=footnote,
                update_type=UpdateType.CREATE,
                transaction=transaction,
            )


def update_conditions(instance, transaction, current_workbasket, formset):
    """
    Gets condition formset from context data, loops over these forms and
    validates the data, checking for the condition_sid field in the data to
    indicate whether an existing condition is being updated or a new one created
    from scratch.

    Then deletes any existing conditions that are not being updated,
    before calling the MeasureCreationPattern.create_condition_and_components with the appropriate parser and condition data.
    """
    excluded_sids = []
    conditions_data = []
    existing_conditions = instance.conditions.approved_up_to_transaction(
        transaction,
    )

    for f in formset.forms:
        f.is_valid()
        condition_data = f.cleaned_data
        # If the form has changed and "condition_sid" is in the changed data,
        # this means that the condition is preexisting and needs to updated
        # so that its dependent_measure points to the latest version of measure
        if f.has_changed() and "condition_sid" in f.changed_data:
            excluded_sids.append(f.initial["condition_sid"])
            update_type = UpdateType.UPDATE
            condition_data["version_group"] = existing_conditions.get(
                sid=f.initial["condition_sid"],
            ).version_group
            condition_data["sid"] = f.initial["condition_sid"]
        # If changed and condition_sid not in changed_data, then this is a newly created condition
        elif f.has_changed() and "condition_sid" not in f.changed_data:
            update_type = UpdateType.CREATE

        condition_data["update_type"] = update_type
        conditions_data.append(condition_data)

    # Delete all existing conditions from the measure instance, except those that need to be updated
    for condition in existing_conditions.exclude(sid__in=excluded_sids):
        condition.new_version(
            workbasket=current_workbasket,
            update_type=UpdateType.DELETE,
            transaction=transaction,
        )

    if conditions_data:
        create_conditions(instance, transaction, current_workbasket, conditions_data)


def create_conditions(instance, transaction, current_workbasket, conditions_data):

    measure_creation_pattern = MeasureCreationPattern(
        workbasket=current_workbasket,
        base_date=instance.valid_between.lower,
    )
    parser = DutySentenceParser.get(
        instance.valid_between.lower,
        component_output=MeasureConditionComponent,
    )

    # Loop over conditions_data, starting at 1 because component_sequence_number has to start at 1
    for component_sequence_number, condition_data in enumerate(
        conditions_data,
        start=1,
    ):
        # Create conditions and measure condition components, using instance as `dependent_measure`

        condition = MeasureCondition(
            sid=condition_data.get("sid")
            or measure_creation_pattern.measure_condition_sid_counter(),
            component_sequence_number=component_sequence_number,
            dependent_measure=instance,
            update_type=condition_data.get("update_type") or UpdateType.CREATE,
            transaction=transaction,
            duty_amount=condition_data.get("duty_amount"),
            condition_code=condition_data["condition_code"],
            action=condition_data.get("action"),
            required_certificate=condition_data.get("required_certificate"),
            monetary_unit=condition_data.get("monetary_unit"),
            condition_measurement=condition_data.get(
                "condition_measurement",
            ),
        )
        if condition_data.get("version_group"):
            condition.version_group = condition_data.get("version_group")

        condition.clean()
        condition.save()

        if condition_data.get("applicable_duty"):
            diff_components(
                condition,
                condition_data.get("applicable_duty"),
                instance.valid_between.lower,
                current_workbasket,
                transaction,
                MeasureConditionComponent,
                "condition",
            )
