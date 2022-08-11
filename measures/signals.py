from typing import Type

from django.db.models.signals import pre_save
from django.dispatch import receiver

from common.validators import UpdateType
from measures import models


@receiver(pre_save, sender=models.Measure, dispatch_uid="update_terminating_regulation")
def update_terminating_regulation(sender: Type, **kwargs):
    """
    Update the terminating regulation on the measure to not be present if the
    measure has no explicit end date or to be equal to the generating regulation
    if the measure has an explicit end date and the termination regulation is
    not already set.

    This automatically avoids issues with ~`measures.business_rules.ME33` and
    ~`measures.business_rules.ME34`.
    """
    instance: models.Measure = kwargs["instance"]
    should_have_reg = not instance.valid_between.upper_inf
    if should_have_reg and instance.terminating_regulation is None:
        instance.terminating_regulation = instance.generating_regulation
    elif not should_have_reg:
        instance.terminating_regulation = None


@receiver(pre_save, sender=models.Measure, dispatch_uid="handle_changed_commodity_code")
def handle_changed_commodity_code(sender: Type, **kwargs):
    """If the commodity code is being changed on an existing measure, the
    measure is deleted instead of doing an `UPDATE` and a new measure created
    with the updated commodity code."""
    instance: models.Measure = kwargs["instance"]
    is_update = instance.update_type == UpdateType.UPDATE
    previous: models.Measure = instance.get_versions().version_ordering().last()

    if is_update and previous is not None:
        try:
            nomenclature_removed = not (
                previous.goods_nomenclature and instance.goods_nomenclature
            )
        except type(previous.goods_nomenclature).DoesNotExist:
            return

        nomenclature_changed = (
            True
            if nomenclature_removed
            else instance.goods_nomenclature.sid != previous.goods_nomenclature.sid
        )
        if nomenclature_changed:
            instance.copy(instance.transaction.workbasket.new_transaction())
            instance.goods_nomenclature = previous.goods_nomenclature
            instance.update_type = UpdateType.DELETE
