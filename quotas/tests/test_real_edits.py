from django.urls import reverse

from common.models import Transaction
from common.tests import factories
from common.validators import UpdateType
from quotas import models
from quotas import validators


def test_quotas_workbasket_edit_create(client_with_current_workbasket, date_ranges):
    country1 = factories.CountryFactory.create()
    country2 = factories.CountryFactory.create()
    country3 = factories.CountryFactory.create()
    geo_group = factories.GeoGroupFactory.create()
    membership1 = factories.GeographicalMembershipFactory.create(
        member=country1,
        geo_group=geo_group,
    )
    membership2 = factories.GeographicalMembershipFactory.create(
        member=country2,
        geo_group=geo_group,
    )
    membership3 = factories.GeographicalMembershipFactory.create(
        member=country3,
        geo_group=geo_group,
    )

    data = {
        "order_number": "054000",
        "mechanism": validators.AdministrationMechanism.LICENSED.value,
        "category": validators.QuotaCategory.WTO.value,
        "start_date_0": date_ranges.big_no_end.lower.day,
        "start_date_1": date_ranges.big_no_end.lower.month,
        "start_date_2": date_ranges.big_no_end.lower.year,
        "end_date_0": "",
        "end_date_1": "",
        "end_date_2": "",
        "origins-0-pk": "",
        "origins-0-start_date_0": date_ranges.big_no_end.lower.day,
        "origins-0-start_date_1": date_ranges.big_no_end.lower.month,
        "origins-0-start_date_2": date_ranges.big_no_end.lower.year,
        "origins-0-end_date_0": "",
        "origins-0-end_date_1": "",
        "origins-0-end_date_2": "",
        "origins-0-geographical_area": geo_group.pk,
        "origins-0-exclusions-0-pk": "",
        "origins-0-exclusions-0-geographical_area": membership1.member.pk,
        "submit": "Save",
    }
    url = reverse("quota-ui-create")
    response = client_with_current_workbasket.post(url, data)

    tx = Transaction.objects.last()
    new_quota = models.QuotaOrderNumber.objects.approved_up_to_transaction(tx).last()

    assert response.status_code == 302
    assert response.url == reverse(
        "quota-ui-confirm-create",
        kwargs={"sid": new_quota.sid},
    )

    assert new_quota.origins.approved_up_to_transaction(tx).count() == 1
    new_origin = new_quota.quotaordernumberorigin_set.approved_up_to_transaction(
        tx,
    ).first()

    assert (
        new_origin.quotaordernumberoriginexclusion_set.approved_up_to_transaction(
            tx,
        ).count()
        == 1
    )
    new_exclusion = (
        new_origin.quotaordernumberoriginexclusion_set.approved_up_to_transaction(
            tx,
        ).first()
    )
    assert new_exclusion.excluded_geographical_area.sid == membership1.member.sid

    edit_data = {
        # update the order number
        "order_number": "054001",
        "mechanism": validators.AdministrationMechanism.LICENSED.value,
        "category": validators.QuotaCategory.WTO.value,
        "start_date_0": date_ranges.big_no_end.lower.day,
        "start_date_1": date_ranges.big_no_end.lower.month,
        "start_date_2": date_ranges.big_no_end.lower.year,
        "end_date_0": "",
        "end_date_1": "",
        "end_date_2": "",
        "origins-0-pk": new_origin.pk,
        "origins-0-start_date_0": date_ranges.big_no_end.lower.day,
        "origins-0-start_date_1": date_ranges.big_no_end.lower.month,
        "origins-0-start_date_2": date_ranges.big_no_end.lower.year,
        "origins-0-end_date_0": "",
        "origins-0-end_date_1": "",
        "origins-0-end_date_2": "",
        "origins-0-geographical_area": geo_group.pk,
        "origins-0-exclusions-0-pk": new_exclusion.pk,
        # update exclusion
        "origins-0-exclusions-0-geographical_area": membership2.member.pk,
        "submit": "Save",
    }
    url = reverse("quota-ui-edit-create", kwargs={"sid": new_quota.sid})
    response = client_with_current_workbasket.post(url, edit_data)

    assert response.status_code == 302
    assert response.url == reverse(
        "quota-ui-confirm-update",
        kwargs={"sid": new_quota.sid},
    )

    assert new_quota.transaction.workbasket.tracked_models.count() == 3
    assert (
        new_quota.transaction.workbasket.tracked_models.instance_of(
            models.QuotaOrderNumber,
        )
        .first()
        .update_type
        == UpdateType.CREATE
    )
    assert (
        new_quota.transaction.workbasket.tracked_models.instance_of(
            models.QuotaOrderNumberOrigin,
        )
        .first()
        .update_type
        == UpdateType.CREATE
    )
    assert (
        new_quota.transaction.workbasket.tracked_models.instance_of(
            models.QuotaOrderNumberOriginExclusion,
        )
        .first()
        .update_type
        == UpdateType.CREATE
    )


def test_quota_update_existing_origin_and_exclusions_remove(
    client_with_current_workbasket,
    date_ranges,
):
    country1 = factories.CountryFactory.create()
    country2 = factories.CountryFactory.create()
    country3 = factories.CountryFactory.create()
    geo_group = factories.GeoGroupFactory.create()
    membership1 = factories.GeographicalMembershipFactory.create(
        member=country1,
        geo_group=geo_group,
    )
    membership2 = factories.GeographicalMembershipFactory.create(
        member=country2,
        geo_group=geo_group,
    )

    origin1 = factories.QuotaOrderNumberOriginFactory.create(geographical_area=country3)
    quota = origin1.order_number

    origin2 = factories.QuotaOrderNumberOriginFactory.create(
        geographical_area=geo_group,
        order_number=quota,
    )
    exclusion1 = factories.QuotaOrderNumberOriginExclusionFactory.create(
        excluded_geographical_area=membership1.member,
        origin=origin2,
    )
    exclusion2 = factories.QuotaOrderNumberOriginExclusionFactory.create(
        excluded_geographical_area=membership2.member,
        origin=origin2,
    )

    # sanity check
    tx = Transaction.objects.last()
    assert quota.quotaordernumberorigin_set.approved_up_to_transaction(tx).count() == 2
    assert (
        origin1.quotaordernumberoriginexclusion_set.approved_up_to_transaction(
            tx,
        ).count()
        == 0
    )
    assert (
        origin2.quotaordernumberoriginexclusion_set.approved_up_to_transaction(
            tx,
        ).count()
        == 2
    )

    data = {
        "start_date_0": quota.valid_between.lower.day,
        "start_date_1": quota.valid_between.lower.month,
        "start_date_2": quota.valid_between.lower.year,
        "end_date_0": "",
        "end_date_1": "",
        "end_date_2": "",
        "category": quota.category,
        "origins-0-pk": origin1.pk,
        "origins-0-start_date_0": origin1.valid_between.lower.day,
        "origins-0-start_date_1": origin1.valid_between.lower.month,
        "origins-0-start_date_2": origin1.valid_between.lower.year,
        "origins-0-end_date_0": "",
        "origins-0-end_date_1": "",
        "origins-0-end_date_2": "",
        "origins-0-geographical_area": origin1.geographical_area.pk,
        # remove the second origin and its exclusion
        "submit": "Save",
    }

    url = reverse("quota-ui-edit", kwargs={"sid": quota.sid})
    response = client_with_current_workbasket.post(url, data)

    assert response.status_code == 302
    assert response.url == reverse("quota-ui-confirm-update", kwargs={"sid": quota.sid})

    last_tx = Transaction.objects.last()

    updated_quota = (
        models.QuotaOrderNumber.objects.approved_up_to_transaction(last_tx)
        .filter(sid=quota.sid)
        .first()
    )

    assert updated_quota.origins.approved_up_to_transaction(last_tx).count() == 1
    updated_origin = (
        updated_quota.quotaordernumberorigin_set.approved_up_to_transaction(
            last_tx,
        ).first()
    )
    assert (
        updated_origin.quotaordernumberoriginexclusion_set.approved_up_to_transaction(
            last_tx,
        ).count()
        == 0
    )
    # update quota
    # update origin 1 to link to updated quota
    # delete quota origin 2
    # delete both quota origin 2 exclusions
    assert updated_origin.transaction.workbasket.tracked_models.count() == 5
    assert sorted(
        [
            item.get_update_type_display()
            for item in updated_origin.transaction.workbasket.tracked_models.all()
        ],
    ) == ["Delete", "Delete", "Delete", "Update", "Update"]
