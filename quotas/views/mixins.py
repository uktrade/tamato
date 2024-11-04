from django.db import transaction

from common.business_rules import UniqueIdentifyingFields
from common.business_rules import UpdateValidity
from common.validators import UpdateType
from common.views.mixins import TrackedModelDetailMixin
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalMembership
from geo_areas.utils import get_all_members_of_geo_groups
from geo_areas.validators import AreaCode
from quotas import business_rules
from quotas import forms
from quotas import models
from quotas.constants import QUOTA_ORIGIN_EXCLUSIONS_FORMSET_PREFIX
from workbaskets.models import WorkBasket


class QuotaOrderNumberMixin:
    model = models.QuotaOrderNumber

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return models.QuotaOrderNumber.objects.approved_up_to_transaction(tx)


class QuotaUpdateMixin(
    QuotaOrderNumberMixin,
    TrackedModelDetailMixin,
):
    form_class = forms.QuotaUpdateForm
    permission_required = ["common.change_trackedmodel"]

    validate_business_rules = (
        business_rules.ON1,
        business_rules.ON2,
        business_rules.ON4,
        business_rules.ON9,
        business_rules.ON11,
        UniqueIdentifyingFields,
        UpdateValidity,
    )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        geo_area_options = (
            GeographicalArea.objects.current()
            .prefetch_related("descriptions")
            .with_latest_description()
            .as_at_today_and_beyond()
            .order_by("description")
        )
        groups_options = geo_area_options.filter(area_code=AreaCode.GROUP)
        geo_group_pks = [group.pk for group in groups_options]
        memberships = GeographicalMembership.objects.filter(
            geo_group__pk__in=geo_group_pks,
        ).prefetch_related("geo_group", "member")

        groups_with_members = {}
        for group_pk in geo_group_pks:
            members = memberships.filter(geo_group__pk=group_pk)
            groups_with_members[group_pk] = [m.member.pk for m in members]

        kwargs["geo_area_options"] = geo_area_options
        kwargs["exclusions_options"] = geo_area_options.exclude(
            area_code=AreaCode.GROUP,
        )
        kwargs["groups_with_members"] = groups_with_members
        kwargs["existing_origins"] = (
            self.object.get_current_origins().with_latest_geo_area_description()
        )
        return kwargs

    def update_origins(self, instance, form_origins):
        existing_origin_pks = {origin.pk for origin in instance.get_current_origins()}

        if form_origins:
            submitted_origin_pks = {o["pk"] for o in form_origins}
            deleted_origin_pks = existing_origin_pks.difference(submitted_origin_pks)

            for origin_pk in deleted_origin_pks:
                origin = models.QuotaOrderNumberOrigin.objects.get(
                    pk=origin_pk,
                )
                origin.new_version(
                    update_type=UpdateType.DELETE,
                    workbasket=WorkBasket.current(self.request),
                    transaction=instance.transaction,
                )
                # Delete the exclusions as well
                exclusions = models.QuotaOrderNumberOriginExclusion.objects.filter(
                    origin__pk=origin_pk,
                )
                for exclusion in exclusions:
                    exclusion.new_version(
                        update_type=UpdateType.DELETE,
                        workbasket=WorkBasket.current(self.request),
                        transaction=instance.transaction,
                    )

            for origin in form_origins:
                # If origin exists
                if origin.get("pk"):
                    existing_origin = models.QuotaOrderNumberOrigin.objects.get(
                        pk=origin.get("pk"),
                    )
                    updated_origin = existing_origin.new_version(
                        workbasket=WorkBasket.current(self.request),
                        transaction=instance.transaction,
                        order_number=instance,
                        valid_between=origin["valid_between"],
                        geographical_area=origin["geographical_area"],
                    )

                # It's a newly created origin
                else:
                    updated_origin = models.QuotaOrderNumberOrigin.objects.create(
                        order_number=instance,
                        valid_between=origin["valid_between"],
                        geographical_area=origin["geographical_area"],
                        update_type=UpdateType.CREATE,
                        transaction=instance.transaction,
                    )

                # whether it's edited or new we need to add/update exclusions
                self.update_exclusions(
                    instance,
                    updated_origin,
                    origin.get("exclusions"),
                )
        else:
            # even if no changes were made we must update the existing
            # origins to link to the updated order number
            existing_origins = (
                models.QuotaOrderNumberOrigin.objects.approved_up_to_transaction(
                    instance.transaction,
                ).filter(
                    order_number__sid=instance.sid,
                )
            )
            for origin in existing_origins:
                origin.new_version(
                    workbasket=WorkBasket.current(self.request),
                    transaction=instance.transaction,
                    order_number=instance,
                )

    def update_exclusions(self, quota, updated_origin, exclusions):
        existing_exclusions = (
            models.QuotaOrderNumberOriginExclusion.objects.current().filter(
                origin__sid=updated_origin.sid,
            )
        )
        existing_exclusions_geo_area_ids = set(
            existing_exclusions.values_list("excluded_geographical_area_id", flat=True),
        )
        submitted_exclusions_geo_area_ids = {
            e["geographical_area"].id for e in exclusions
        }
        deleted_exclusion_geo_area_ids = existing_exclusions_geo_area_ids.difference(
            submitted_exclusions_geo_area_ids,
        )

        for geo_area_id in deleted_exclusion_geo_area_ids:
            exclusion = existing_exclusions.get(
                excluded_geographical_area=geo_area_id,
            )
            exclusion.new_version(
                update_type=UpdateType.DELETE,
                workbasket=WorkBasket.current(self.request),
                transaction=quota.transaction,
            )

        for exclusion in exclusions:
            geo_area = GeographicalArea.objects.get(pk=exclusion["geographical_area"])
            if geo_area.pk in existing_exclusions_geo_area_ids:
                existing_exclusion = existing_exclusions.get(
                    excluded_geographical_area=geo_area,
                )
                existing_exclusion.new_version(
                    workbasket=WorkBasket.current(self.request),
                    transaction=quota.transaction,
                    origin=updated_origin,
                    excluded_geographical_area=geo_area,
                )

            else:
                models.QuotaOrderNumberOriginExclusion.objects.create(
                    origin=updated_origin,
                    excluded_geographical_area=geo_area,
                    update_type=UpdateType.CREATE,
                    transaction=quota.transaction,
                )

    @transaction.atomic
    def get_result_object(self, form):
        instance = super().get_result_object(form)

        # if JS is enabled we get data from the React form which includes origins and exclusions
        form_origins = form.cleaned_data.get("origins")

        self.update_origins(instance, form_origins)

        return instance


class QuotaOrderNumberOriginMixin:
    model = models.QuotaOrderNumberOrigin

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return models.QuotaOrderNumberOrigin.objects.approved_up_to_transaction(tx)


class QuotaOrderNumberOriginUpdateMixin(
    QuotaOrderNumberOriginMixin,
    TrackedModelDetailMixin,
):
    form_class = forms.QuotaOrderNumberOriginUpdateForm
    permission_required = ["common.change_trackedmodel"]
    template_name = "quota-origins/edit.jinja"

    validate_business_rules = (
        business_rules.ON5,
        business_rules.ON6,
        business_rules.ON7,
        business_rules.ON10,
        business_rules.ON12,
        UniqueIdentifyingFields,
        UpdateValidity,
    )

    @transaction.atomic
    def get_result_object(self, form):
        object = super().get_result_object(form)

        geo_area = form.cleaned_data["geographical_area"]
        form_exclusions = [
            item["exclusion"]
            for item in form.cleaned_data[QUOTA_ORIGIN_EXCLUSIONS_FORMSET_PREFIX]
        ]

        all_new_exclusions = get_all_members_of_geo_groups(
            object.valid_between,
            form_exclusions,
        )

        for geo_area in all_new_exclusions:
            existing_exclusion = (
                object.quotaordernumberoriginexclusion_set.filter(
                    excluded_geographical_area=geo_area,
                )
                .current()
                .first()
            )

            if existing_exclusion:
                existing_exclusion.new_version(
                    workbasket=WorkBasket.current(self.request),
                    transaction=object.transaction,
                    origin=object,
                )
            else:
                models.QuotaOrderNumberOriginExclusion.objects.create(
                    origin=object,
                    excluded_geographical_area=geo_area,
                    update_type=UpdateType.CREATE,
                    transaction=object.transaction,
                )

        removed_excluded_areas = {
            e.excluded_geographical_area
            for e in object.quotaordernumberoriginexclusion_set.current()
        }.difference(set(form_exclusions))

        removed_exclusions = [
            object.quotaordernumberoriginexclusion_set.current().get(
                excluded_geographical_area__id=e.id,
            )
            for e in removed_excluded_areas
        ]

        for removed in removed_exclusions:
            removed.new_version(
                update_type=UpdateType.DELETE,
                workbasket=WorkBasket.current(self.request),
                transaction=object.transaction,
                origin=object,
            )

        return object
