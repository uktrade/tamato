from datetime import date
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.views.generic import FormView
from rest_framework import permissions
from rest_framework import viewsets

from common.business_rules import UniqueIdentifyingFields
from common.business_rules import UpdateValidity
from common.forms import delete_form_for
from common.serializers import AutoCompleteSerializer
from common.tariffs_api import URLs
from common.tariffs_api import get_quota_data
from common.validators import UpdateType
from common.views import SortingMixin
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalMembership
from geo_areas.utils import get_all_members_of_geo_groups
from geo_areas.validators import AreaCode
from measures.models import Measure
from quotas import business_rules
from quotas import forms
from quotas import models
from quotas import serializers
from quotas.constants import QUOTA_ORIGIN_EXCLUSIONS_FORMSET_PREFIX
from quotas.filters import OrderNumberFilterBackend
from quotas.filters import QuotaFilter
from quotas.models import QuotaAssociation
from quotas.models import QuotaBlocking
from quotas.models import QuotaSuspension
from workbaskets.models import WorkBasket
from workbaskets.views.decorators import require_current_workbasket
from workbaskets.views.generic import CreateTaricCreateView
from workbaskets.views.generic import CreateTaricDeleteView
from workbaskets.views.generic import CreateTaricUpdateView
from workbaskets.views.generic import EditTaricView


class QuotaOrderNumberViewset(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows quota order numbers to be viewed."""

    serializer_class = AutoCompleteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderNumberFilterBackend]

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return models.QuotaOrderNumber.objects.approved_up_to_transaction(tx)


class QuotaOrderNumberOriginViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaOrderNumberOrigin.objects.has_approved_state()
    serializer_class = serializers.QuotaOrderNumberOriginSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaOrderNumberOriginExclusionViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaOrderNumberOriginExclusion.objects.has_approved_state()
    serializer_class = serializers.QuotaOrderNumberOriginExclusionSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaAssociationViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaAssociation.objects.has_approved_state()
    serializer_class = serializers.QuotaAssociationSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaSuspensionViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaSuspension.objects.has_approved_state()
    serializer_class = serializers.QuotaSuspensionSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaBlockingViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaBlocking.objects.has_approved_state()
    serializer_class = serializers.QuotaBlockingSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaEventViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaEvent.objects.has_approved_state()
    serializer_class = serializers.QuotaEventSerializer
    permission_classes = [permissions.IsAuthenticated]


class QuotaOrderNumberMixin:
    model = models.QuotaOrderNumber

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return models.QuotaOrderNumber.objects.approved_up_to_transaction(tx)


class QuotaCreate(QuotaOrderNumberMixin, CreateTaricCreateView):
    form_class = forms.QuotaOrderNumberCreateForm
    template_name = "layouts/create.jinja"

    permission_required = ["common.add_trackedmodel"]

    validate_business_rules = (
        business_rules.ON1,
        business_rules.ON2,
        UniqueIdentifyingFields,
        UpdateValidity,
    )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        geo_area_options = (
            GeographicalArea.objects.current()
            .with_latest_description()
            .as_at_today_and_beyond()
            .prefetch_related("descriptions")
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
        return kwargs

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            page_title="Create a new quota order number",
            **kwargs,
        )

    def create_origins(self, instance, form_origins):
        for origin in form_origins:
            new_origin = models.QuotaOrderNumberOrigin.objects.create(
                order_number=instance,
                valid_between=origin["valid_between"],
                geographical_area=origin["geographical_area"],
                update_type=UpdateType.CREATE,
                transaction=instance.transaction,
            )

            self.create_exclusions(
                instance,
                new_origin,
                origin.get("exclusions"),
            )

    def create_exclusions(self, quota, created_origin, exclusions):
        for exclusion in exclusions:
            geo_area = GeographicalArea.objects.get(pk=exclusion["geographical_area"])
            models.QuotaOrderNumberOriginExclusion.objects.create(
                origin=created_origin,
                excluded_geographical_area=geo_area,
                update_type=UpdateType.CREATE,
                transaction=quota.transaction,
            )

    @transaction.atomic
    def get_result_object(self, form):
        instance = super().get_result_object(form)

        # if JS is enabled we get data from the React form which includes origins and exclusions
        form_origins = form.cleaned_data.get("origins")

        self.create_origins(instance, form_origins)

        return instance


class QuotaConfirmCreate(QuotaOrderNumberMixin, TrackedModelDetailView):
    template_name = "quotas/confirm-create.jinja"


class QuotaList(QuotaOrderNumberMixin, TamatoListView):
    """Returns a list of QuotaOrderNumber objects."""

    template_name = "quotas/list.jinja"
    filterset_class = QuotaFilter


class QuotaDetail(QuotaOrderNumberMixin, TrackedModelDetailView, SortingMixin):
    template_name = "quotas/detail.jinja"
    sort_by_fields = ["goods_nomenclature"]

    @property
    def quota_data(self):
        data = get_quota_data({"order_number": self.object.order_number})
        if not data or data["meta"]["pagination"]["total_count"] == 0:
            return None
        return data.get("data")[0]

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        definitions = self.object.definitions.current()

        current_definition = definitions.as_at_and_beyond(date.today()).first()
        context["current_definition"] = current_definition
        context["uk_tariff_url"] = (
            f"{URLs.BASE_URL.value}quota_search?order_number={self.object.order_number}"
        )

        context["sub_quota_associations"] = QuotaAssociation.objects.current().filter(
            main_quota=current_definition,
        )

        context["main_quota_associations"] = QuotaAssociation.objects.current().filter(
            sub_quota=current_definition,
        )

        context["blocking_period"] = (
            QuotaBlocking.objects.filter(quota_definition=current_definition)
            .as_at_and_beyond(date.today())
            .first()
        )

        context["suspension_period"] = (
            QuotaSuspension.objects.filter(quota_definition=current_definition)
            .as_at_and_beyond(date.today())
            .first()
        )

        context["quota_data"] = self.quota_data

        order = self.get_ordering()
        if not order:
            order = "goods_nomenclature"

        context["measures"] = (
            Measure.objects.latest_approved()
            .filter(order_number=self.object)
            .as_at(date.today())
            .order_by(order)
        )
        url_params = urlencode({"order_number": self.object.pk})
        context["measures_url"] = f"{reverse('measure-ui-list')}?{url_params}"

        return context


class QuotaDelete(
    QuotaOrderNumberMixin,
    TrackedModelDetailMixin,
    CreateTaricDeleteView,
):
    form_class = forms.QuotaDeleteForm
    success_path = "list"

    validate_business_rules = (business_rules.ON11,)


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


class QuotaUpdate(
    QuotaUpdateMixin,
    CreateTaricUpdateView,
):
    pass


class QuotaEditCreate(
    QuotaUpdateMixin,
    EditTaricView,
):
    pass


class QuotaEditUpdate(
    QuotaUpdateMixin,
    EditTaricView,
):
    pass


class QuotaConfirmUpdate(QuotaOrderNumberMixin, TrackedModelDetailView):
    template_name = "common/confirm_update.jinja"


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


class QuotaOrderNumberOriginUpdate(
    QuotaOrderNumberOriginUpdateMixin,
    CreateTaricUpdateView,
):
    pass


class QuotaOrderNumberOriginCreate(
    QuotaOrderNumberOriginUpdateMixin,
    CreateTaricCreateView,
):
    form_class = forms.QuotaOrderNumberOriginForm
    template_name = "layouts/create.jinja"

    def form_valid(self, form):
        quota = models.QuotaOrderNumber.objects.current().get(sid=self.kwargs["sid"])
        form.instance.order_number = quota
        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        context["page_title"] = "Create a new quota origin"
        context["page_label"] = mark_safe(
            """Find out more about <a class="govuk-link" 
        href="https://data-services-help.trade.gov.uk/tariff-application-platform/tariff-policy/origin-quotas/">
        quota origins</a>.""",
        )

        return context


class QuotaOrderNumberOriginConfirmCreate(
    QuotaOrderNumberOriginMixin,
    TrackedModelDetailView,
):
    template_name = "quota-origins/confirm-create.jinja"


class QuotaOrderNumberOriginEditUpdate(
    QuotaOrderNumberOriginUpdateMixin,
    EditTaricView,
):
    pass


class QuotaOrderNumberOriginConfirmUpdate(
    QuotaOrderNumberOriginMixin,
    TrackedModelDetailView,
):
    template_name = "quota-origins/confirm-update.jinja"


class QuotaDefinitionConfirmDelete(
    QuotaOrderNumberMixin,
    TrackedModelDetailView,
):
    template_name = "quota-definitions/confirm-delete.jinja"


@method_decorator(require_current_workbasket, name="dispatch")
class QuotaSuspensionOrBlockingCreate(
    PermissionRequiredMixin,
    FormView,
):
    """UI endpoint for creating a suspension period or a blocking period."""

    template_name = "quota-suspensions/create.jinja"
    form_class = forms.QuotaSuspensionOrBlockingCreateForm
    permission_required = "common.add_trackedmodel"

    @property
    def quota_order_number(self):
        return models.QuotaOrderNumber.objects.current().get(sid=self.kwargs["sid"])

    @property
    def workbasket(self):
        return WorkBasket.current(self.request)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["quota_order_number"] = self.quota_order_number
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["page_title"] = "Create a suspension or blocking period"
        context["quota_order_number"] = self.quota_order_number
        return context

    def form_valid(self, form):
        self.object = form.save(workbasket=self.workbasket)
        return super().form_valid(form)

    def get_success_url(self):
        redirect_map = {
            QuotaSuspension: reverse(
                "quota_suspension-ui-confirm-create",
                kwargs={"sid": self.object.sid},
            ),
            QuotaBlocking: reverse(
                "quota_blocking-ui-confirm-create",
                kwargs={"sid": self.object.sid},
            ),
        }
        return redirect_map.get(type(self.object))


class QuotaSuspensionConfirmCreate(TrackedModelDetailView):
    model = models.QuotaSuspension
    template_name = "quota-suspensions/confirm-create.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        quota_order_number = self.object.quota_definition.order_number
        list_url = reverse(
            "quota_definition-ui-list",
            kwargs={"sid": quota_order_number.sid},
        )
        url_param = urlencode({"quota_type": "suspension_periods"})
        context.update(
            {
                "quota_order_number": quota_order_number,
                "object_name": "Suspension period",
                "list_url": f"{list_url}?{url_param}",
            },
        )
        return context


class QuotaBlockingConfirmCreate(TrackedModelDetailView):
    model = models.QuotaBlocking
    template_name = "quota-suspensions/confirm-create.jinja"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        quota_order_number = self.object.quota_definition.order_number
        list_url = reverse(
            "quota_definition-ui-list",
            kwargs={"sid": quota_order_number.sid},
        )
        url_param = urlencode({"quota_type": "blocking_periods"})
        context.update(
            {
                "quota_order_number": quota_order_number,
                "object_name": "Blocking period",
                "list_url": f"{list_url}?{url_param}",
            },
        )
        return context


class QuotaSuspensionUpdateMixin(TrackedModelDetailMixin):
    model = QuotaSuspension
    template_name = "quota-suspensions/edit.jinja"
    form_class = forms.QuotaSuspensionUpdateForm
    permission_required = ["common.change_trackedmodel"]

    def get_success_url(self):
        return reverse(
            "quota_suspension-ui-confirm-update",
            kwargs={"sid": self.object.sid},
        )


class QuotaSuspensionUpdate(
    QuotaSuspensionUpdateMixin,
    CreateTaricUpdateView,
):
    pass


class QuotaSuspensionEditCreate(
    QuotaSuspensionUpdateMixin,
    EditTaricView,
):
    pass


class QuotaSuspensionEditUpdate(
    QuotaSuspensionUpdateMixin,
    EditTaricView,
):
    pass


class QuotaSuspensionConfirmUpdate(TrackedModelDetailView):
    model = models.QuotaSuspension
    template_name = "quota-suspensions/confirm-update.jinja"


class QuotaSuspensionDelete(TrackedModelDetailMixin, CreateTaricDeleteView):
    form_class = forms.QuotaSuspensionDeleteForm
    model = models.QuotaSuspension
    template_name = "quota-suspensions/delete.jinja"

    def get_success_url(self):
        return reverse(
            "quota_suspension-ui-confirm-delete",
            kwargs={"sid": self.object.sid},
        )


class QuotaSuspensionConfirmDelete(TrackedModelDetailView):
    model = QuotaSuspension
    template_name = "quota-suspensions/confirm-delete.jinja"

    @property
    def deleted_suspension(self):
        return QuotaSuspension.objects.filter(sid=self.kwargs["sid"]).last()

    def get_queryset(self):
        """
        Returns a queryset with one single version of the suspension in
        question.

        Done this way so the sid can be rendered on the confirm delete page and
        generic tests don't fail which try to load the page without having
        deleted anything.
        """
        return QuotaSuspension.objects.filter(pk=self.deleted_suspension)


class SubQuotaConfirmUpdate(TrackedModelDetailView):
    model = models.QuotaDefinition
    template_name = "quota-definitions/sub-quota-definitions-confirm-update.jinja"

    @property
    def association(self):
        return QuotaAssociation.objects.current().get(sub_quota__sid=self.kwargs["sid"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["association"] = self.association
        return context

    def dispatch(self, request, *args, **kwargs):
        """
        Should a user land on the this page for a definition which is not a sub-
        quota, perform a redirect.

        This is not possible with current user journeys but this is included for
        security and test purposes.
        """
        try:
            self.association
        except models.QuotaAssociation.DoesNotExist:
            return HttpResponseRedirect(
                reverse(
                    "quota-ui-list",
                ),
            )
        return super().dispatch(request, *args, **kwargs)


class QuotaAssociationDelete(
    CreateTaricDeleteView,
):
    form_class = delete_form_for(models.QuotaAssociation)
    template_name = "quota-associations/delete.jinja"
    model = models.QuotaAssociation

    def form_valid(self, form):
        messages.success(
            self.request,
            f"Quota association between {self.object.main_quota.sid} and {self.object.sub_quota.sid} has been deleted",
        )
        return super().form_valid(form)

    def get_queryset(self):
        return models.QuotaAssociation.objects.current()

    def get_success_url(self):
        return reverse(
            "quota_association-ui-confirm-delete",
            kwargs={"sid": self.object.sub_quota.sid},
        )


class QuotaAssociationConfirmDelete(
    TrackedModelDetailView,
):
    template_name = "quota-associations/confirm-delete.jinja"
    model = models.QuotaDefinition
