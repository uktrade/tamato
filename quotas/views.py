from datetime import date
from urllib.parse import urlencode

from django.db import transaction
from django.urls import reverse
from django.utils.functional import cached_property
from django.views.generic.edit import FormMixin
from django.views.generic.list import ListView
from rest_framework import permissions
from rest_framework import viewsets

from common.business_rules import UniqueIdentifyingFields
from common.business_rules import UpdateValidity
from common.serializers import AutoCompleteSerializer
from common.tariffs_api import get_quota_data
from common.tariffs_api import get_quota_definitions_data
from common.validators import UpdateType
from common.views import SortingMixin
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from geo_areas.utils import get_all_members_of_geo_groups
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


class QuotaDefinitionViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaDefinition.objects.has_approved_state()
    serializer_class = serializers.QuotaDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["sid", "order_number__order_number", "description"]


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


class QuotaList(QuotaOrderNumberMixin, TamatoListView):
    """Returns a list of QuotaOrderNumber objects."""

    template_name = "quotas/list.jinja"
    filterset_class = QuotaFilter


class QuotaDetail(QuotaOrderNumberMixin, TrackedModelDetailView, SortingMixin):
    template_name = "quotas/detail.jinja"
    sort_by_fields = ["goods_nomenclature"]

    @property
    def quota_data(self):
        data = get_quota_data(self.object.order_number)
        if not data or data["meta"]["pagination"]["total_count"] == 0:
            return None
        return data.get("data")[0]

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        definitions = self.object.definitions.current()

        current_definition = definitions.as_at_and_beyond(date.today()).first()
        context["current_definition"] = current_definition

        context[
            "quota_associations"
        ] = QuotaAssociation.objects.latest_approved().filter(
            main_quota=current_definition,
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


class QuotaDefinitionList(FormMixin, SortingMixin, ListView):
    template_name = "quotas/definitions.jinja"
    model = models.QuotaDefinition
    sort_by_fields = ["sid", "valid_between"]
    form_class = forms.QuotaDefinitionFilterForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["object_sid"] = self.quota.sid
        kwargs["form_initial"] = self.quota_type
        return kwargs

    def get_queryset(self):
        return models.QuotaDefinition.objects.filter(
            order_number__sid=self.quota.sid,
        ).current()

    @property
    def blocking_periods(self):
        return QuotaBlocking.objects.filter(quota_definition__order_number=self.quota)

    @property
    def suspension_periods(self):
        return QuotaSuspension.objects.filter(quota_definition__order_number=self.quota)

    @property
    def sub_quotas(self):
        return QuotaAssociation.objects.filter(main_quota__order_number=self.quota)

    @cached_property
    def quota_data(self):
        if not self.quota_type:
            return get_quota_definitions_data(self.quota.order_number, self.object_list)
        return None

    @property
    def quota(self):
        return models.QuotaOrderNumber.objects.current().get(sid=self.kwargs["sid"])

    @property
    def quota_type(self):
        return (
            self.request.GET.get("quota_type")
            if self.request.GET.get("quota_type")
            in ["sub_quotas", "blocking_periods", "suspension_periods"]
            else None
        )

    def get_context_data(self, *args, **kwargs):
        return super().get_context_data(
            quota=self.quota,
            quota_type=self.quota_type,
            quota_data=self.quota_data,
            blocking_periods=self.blocking_periods,
            suspension_periods=self.suspension_periods,
            sub_quotas=self.sub_quotas,
            form_url=reverse("quota-definitions", kwargs={"sid": self.quota.sid}),
            *args,
            **kwargs,
        )


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

    @transaction.atomic
    def get_result_object(self, form):
        object = super().get_result_object(form)

        existing_origins = (
            models.QuotaOrderNumberOrigin.objects.approved_up_to_transaction(
                object.transaction,
            ).filter(
                order_number__sid=object.sid,
            )
        )

        # this will be needed even if origins have not been edited in the form
        for origin in existing_origins:
            origin.new_version(
                workbasket=WorkBasket.current(self.request),
                transaction=object.transaction,
                order_number=object,
            )

        return object


class QuotaUpdate(
    QuotaUpdateMixin,
    CreateTaricUpdateView,
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


class QuotaDefinitionMixin:
    model = models.QuotaDefinition

    def get_queryset(self):
        tx = WorkBasket.get_current_transaction(self.request)
        return models.QuotaDefinition.objects.approved_up_to_transaction(tx)


class QuotaDefinitionUpdateMixin(
    QuotaDefinitionMixin,
    TrackedModelDetailMixin,
):
    form_class = forms.QuotaDefinitionUpdateForm
    permission_required = ["common.change_trackedmodel"]
    template_name = "quota-definitions/edit.jinja"

    validate_business_rules = (
        business_rules.QD7,
        business_rules.QD8,
        business_rules.QD10,
        business_rules.QD11,
        UniqueIdentifyingFields,
        UpdateValidity,
    )

    @transaction.atomic
    def get_result_object(self, form):
        object = super().get_result_object(form)
        return object


class QuotaDefinitionUpdate(
    QuotaDefinitionUpdateMixin,
    CreateTaricUpdateView,
):
    pass


class QuotaDefinitionEditUpdate(
    QuotaDefinitionUpdateMixin,
    EditTaricView,
):
    pass


class QuotaDefinitionConfirmUpdate(
    QuotaDefinitionMixin,
    TrackedModelDetailView,
):
    template_name = "quota-definitions/confirm-update.jinja"
