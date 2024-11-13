from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.views.generic.list import ListView
from rest_framework import permissions
from rest_framework import viewsets

from common.business_rules import UniqueIdentifyingFields
from common.business_rules import UpdateValidity
from common.forms import delete_form_for
from common.tariffs_api import get_quota_definitions_data
from common.views import SortingMixin
from common.views import TrackedModelDetailMixin
from common.views import TrackedModelDetailView
from quotas import business_rules
from quotas import forms
from quotas import models
from quotas import serializers
from quotas.models import QuotaAssociation
from quotas.models import QuotaBlocking
from quotas.models import QuotaSuspension
from workbaskets.models import WorkBasket
from workbaskets.views.decorators import require_current_workbasket
from workbaskets.views.generic import CreateTaricCreateView
from workbaskets.views.generic import CreateTaricDeleteView
from workbaskets.views.generic import CreateTaricUpdateView
from workbaskets.views.generic import EditTaricView


class QuotaDefinitionViewset(viewsets.ReadOnlyModelViewSet):
    queryset = models.QuotaDefinition.objects.has_approved_state()
    serializer_class = serializers.QuotaDefinitionSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["sid", "order_number__order_number", "description"]


@method_decorator(require_current_workbasket, name="dispatch")
class QuotaDefinitionList(SortingMixin, ListView):
    template_name = "quotas/definitions.jinja"
    model = models.QuotaDefinition
    sort_by_fields = ["sid", "valid_between"]

    def get_queryset(self):
        queryset = (
            models.QuotaDefinition.objects.filter(
                order_number__sid=self.quota.sid,
            )
            .current()
            .order_by("pk")
        )

        ordering = self.get_ordering()
        if ordering:
            if isinstance(ordering, str):
                ordering = (ordering,)
            queryset = queryset.order_by(*ordering)

        return queryset

    @property
    def blocking_periods(self):
        return (
            QuotaBlocking.objects.current()
            .filter(
                quota_definition__order_number=self.quota,
            )
            .order_by("quota_definition__sid")
        )

    @property
    def suspension_periods(self):
        return (
            QuotaSuspension.objects.current()
            .filter(quota_definition__order_number=self.quota)
            .order_by("quota_definition__sid")
        )

    @property
    def sub_quotas(self):
        return (
            QuotaAssociation.objects.current()
            .filter(main_quota__order_number=self.quota)
            .order_by("sub_quota__sid")
        )

    @property
    def main_quotas(self):
        main_quotas = QuotaAssociation.objects.current().filter(
            sub_quota__order_number=self.quota,
        )
        return main_quotas

    @cached_property
    def quota_data(self):
        if not self.kwargs.get("quota_type"):
            return get_quota_definitions_data(self.quota.order_number, self.object_list)
        return None

    @property
    def quota(self):
        return models.QuotaOrderNumber.objects.current().get(sid=self.kwargs["sid"])

    def get_context_data(self, *args, **kwargs):
        return super().get_context_data(
            quota=self.quota,
            quota_type=self.kwargs.get("quota_type"),
            quota_data=self.quota_data,
            blocking_periods=self.blocking_periods,
            suspension_periods=self.suspension_periods,
            sub_quotas=self.sub_quotas,
            main_quotas=self.main_quotas,
            *args,
            **kwargs,
        )


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


class QuotaDefinitionCreate(QuotaDefinitionUpdateMixin, CreateTaricCreateView):
    template_name = "quota-definitions/create.jinja"
    form_class = forms.QuotaDefinitionCreateForm

    def form_valid(self, form):
        quota = models.QuotaOrderNumber.objects.current().get(sid=self.kwargs["sid"])
        form.instance.order_number = quota
        return super().form_valid(form)


class QuotaDefinitionConfirmCreate(
    QuotaDefinitionMixin,
    TrackedModelDetailView,
):
    template_name = "quota-definitions/confirm-create.jinja"


class QuotaDefinitionDelete(
    QuotaDefinitionUpdateMixin,
    CreateTaricDeleteView,
):
    form_class = delete_form_for(models.QuotaDefinition)
    template_name = "quota-definitions/delete.jinja"

    @property
    def related_associations(self):
        return models.QuotaAssociation.objects.current().filter(
            Q(main_quota__sid=self.object.sid) | Q(sub_quota__sid=self.object.sid),
        )

    @transaction.atomic
    def get_result_object(self, form):
        """Delete the definition and any linked associations."""
        definition_instance = super().get_result_object(form)
        for association in self.related_associations:
            association_form = forms.QuotaAssociationUpdateForm(
                instance=association,
            )
            association_form.instance.new_version(
                workbasket=self.workbasket,
                update_type=self.update_type,
                transaction=definition_instance.transaction,
            )

        return definition_instance

    def form_valid(self, form):
        messages.success(
            self.request,
            f"Quota definition period {self.object.sid} has been deleted",
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "quota_definition-ui-confirm-delete",
            kwargs={"sid": self.object.order_number.sid},
        )


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


class SubQuotaDefinitionAssociationMixin:
    template_name = "quota-definitions/sub-quota-definitions-updates.jinja"
    form_class = forms.SubQuotaDefinitionAssociationUpdateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["sid"] = self.kwargs["sid"]
        kwargs["request"] = self.request
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        """
        Should a user land on the form for a definition which is not a sub-
        quota, perform a redirect.

        This is not possible with current user journeys but this is included for
        security and test purposes.
        """
        try:
            self.association
        except models.QuotaAssociation.DoesNotExist:
            return HttpResponseRedirect(
                reverse(
                    "quota-ui-detail",
                    kwargs={"sid": self.sub_quota.order_number.sid},
                ),
            )
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            "sub_quota_definition-confirm-update",
            kwargs={"sid": self.kwargs["sid"]},
        )

    @property
    def last_transaction(self):
        return self.workbasket.transactions.last()

    @property
    def sub_quota(self):
        return models.QuotaDefinition.objects.current().get(sid=self.kwargs["sid"])

    @property
    def association(self):
        return models.QuotaAssociation.objects.current().get(
            sub_quota__sid=self.sub_quota.sid,
        )

    def get_main_definition(self):
        return self.association.main_quota


class SubQuotaDefinitionAssociationUpdate(
    SubQuotaDefinitionAssociationMixin,
    QuotaDefinitionUpdate,
):

    @transaction.atomic
    def get_result_object(self, form):
        self.original_association = self.association
        instance = super().get_result_object(form)

        sub_quota_relation_type = form.cleaned_data.get("relationship_type")
        coefficient = form.cleaned_data.get("coefficient")

        self.update_association(instance, sub_quota_relation_type, coefficient)

        return instance

    def update_association(self, instance, sub_quota_relation_type, coefficient):
        "Update the association too if there is updated data submitted."
        form_data = {
            "main_quota": self.get_main_definition(),
            "sub_quota": self.sub_quota,
            "coefficient": coefficient,
            "sub_quota_relation_type": sub_quota_relation_type,
        }

        form = forms.QuotaAssociationUpdateForm(
            data=form_data,
            instance=self.original_association,
        )

        form.instance.new_version(
            workbasket=WorkBasket.current(self.request),
            transaction=instance.transaction,
            sub_quota=instance,
            main_quota=self.get_main_definition(),
            coefficient=coefficient,
            sub_quota_relation_type=sub_quota_relation_type,
        )


class SubQuotaDefinitionAssociationEditUpdate(
    SubQuotaDefinitionAssociationMixin,
    QuotaDefinitionEditUpdate,
):

    @transaction.atomic
    def get_result_object(self, form):
        instance = super().get_result_object(form)

        sub_quota_relation_type = form.cleaned_data.get("relationship_type")
        coefficient = form.cleaned_data.get("coefficient")

        self.update_association(instance, sub_quota_relation_type, coefficient)

        return instance

    def update_association(self, instance, sub_quota_relation_type, coefficient):
        "Update the association too if there is updated data submitted."
        current_instance = self.association.version_at(self.last_transaction)
        form_data = {
            "main_quota": self.get_main_definition(),
            "sub_quota": instance,
            "coefficient": coefficient,
            "sub_quota_relation_type": sub_quota_relation_type,
        }

        form = forms.QuotaAssociationUpdateForm(
            data=form_data,
            instance=current_instance,
        )
        form.save()


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


class QuotaBlockingUpdateMixin(TrackedModelDetailMixin):
    model = QuotaBlocking
    template_name = "quota-blocking/edit.jinja"
    form_class = forms.QuotaBlockingUpdateForm
    permission_required = ["common.change_trackedmodel"]

    def get_success_url(self):
        return reverse(
            "quota_blocking-ui-confirm-update",
            kwargs={"sid": self.object.sid},
        )


class QuotaBlockingUpdate(
    QuotaBlockingUpdateMixin,
    CreateTaricUpdateView,
):
    pass


class QuotaBlockingEditCreate(
    QuotaBlockingUpdateMixin,
    EditTaricView,
):
    pass


class QuotaBlockingEditUpdate(
    QuotaBlockingUpdateMixin,
    EditTaricView,
):
    pass


class QuotaBlockingConfirmUpdate(TrackedModelDetailView):
    model = models.QuotaBlocking
    template_name = "quota-blocking/confirm-update.jinja"


class QuotaBlockingDelete(TrackedModelDetailMixin, CreateTaricDeleteView):
    form_class = forms.QuotaBlockingDeleteForm
    model = models.QuotaBlocking
    template_name = "quota-blocking/delete.jinja"

    def get_success_url(self):
        return reverse(
            "quota_blocking-ui-confirm-delete",
            kwargs={"sid": self.object.sid},
        )


class QuotaBlockingConfirmDelete(TrackedModelDetailView):
    model = QuotaBlocking
    template_name = "quota-blocking/confirm-delete.jinja"

    @property
    def deleted_blocking_period(self):
        return QuotaBlocking.objects.filter(sid=self.kwargs["sid"]).last()

    def get_queryset(self):
        """
        Returns a queryset with one single version of the blocking period in
        question.

        Done this way so the sid can be rendered on the confirm delete page and
        generic tests don't fail which try to load the page without having
        deleted anything.
        """
        return QuotaBlocking.objects.filter(pk=self.deleted_blocking_period)
