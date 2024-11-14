import datetime
from decimal import Decimal

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import FormView
from django.views.generic import TemplateView
from formtools.wizard.views import NamedUrlSessionWizardView

from common.serializers import serialize_date
from common.validators import UpdateType
from common.views import BusinessRulesMixin
from quotas import forms
from quotas import models
from quotas.serializers import deserialize_definition_data
from settings.common import DATE_FORMAT
from workbaskets.models import WorkBasket
from workbaskets.views.decorators import require_current_workbasket


@method_decorator(require_current_workbasket, name="dispatch")
class DuplicateDefinitionsWizard(
    PermissionRequiredMixin,
    NamedUrlSessionWizardView,
):
    """
    Multipart form wizard for duplicating QuotaDefinitionPeriods from a parent
    QuotaOrderNumber to a child QuotaOrderNumber.

    https://django-formtools.readthedocs.io/en/latest/wizard.html
    """

    storage_name = "quotas.wizard.QuotaDefinitionDuplicatorSessionStorage"
    permission_required = ["common.add_trackedmodel"]

    START = "start"
    QUOTA_ORDER_NUMBERS = "quota_order_numbers"
    SELECT_DEFINITION_PERIODS = "select_definition_periods"
    SELECTED_DEFINITIONS = "selected_definition_periods"
    COMPLETE = "complete"

    form_list = [
        (START, forms.DuplicateQuotaDefinitionPeriodStartForm),
        (QUOTA_ORDER_NUMBERS, forms.QuotaOrderNumbersSelectForm),
        (SELECT_DEFINITION_PERIODS, forms.SelectSubQuotaDefinitionsForm),
        (SELECTED_DEFINITIONS, forms.SelectedDefinitionsForm),
    ]

    templates = {
        START: "quota-definitions/sub-quota-duplicate-definitions-start.jinja",
        QUOTA_ORDER_NUMBERS: "quota-definitions/sub-quota-definitions-select-order-numbers.jinja",
        SELECT_DEFINITION_PERIODS: "quota-definitions/sub-quota-definitions-select-definition-period.jinja",
        SELECTED_DEFINITIONS: "quota-definitions/sub-quota-definitions-selected.jinja",
        COMPLETE: "quota-definitions/sub-quota-definitions-done.jinja",
    }

    step_metadata = {
        START: {
            "title": "Duplicate quota definitions",
            "link_text": "Start",
        },
        QUOTA_ORDER_NUMBERS: {
            "title": "Create associations",
            "link_text": "Order numbers",
        },
        SELECT_DEFINITION_PERIODS: {
            "title": "Select definition periods",
            "link_text": "Definition periods",
        },
        SELECTED_DEFINITIONS: {
            "title": "Provide updates and details for duplicated definitions",
            "link_text": "Selected definitions",
        },
        COMPLETE: {"title": "Finished", "link_text": "Success"},
    }

    @property
    def workbasket(self) -> WorkBasket:
        return WorkBasket.current(self.request)

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context["step_metadata"] = self.step_metadata
        return context

    def get_template_names(self):
        template = self.templates.get(
            self.steps.current,
            "quota-definitions/sub-quota-duplicate-definitions-step.jinja",
        )
        return template

    def get_cleaned_data_for_step(self, step):
        """
        Returns cleaned data for a given `step`.

        Note: This patched version of `super().get_cleaned_data_for_step` temporarily saves the cleaned_data
        to provide quick retrieval should another call for it be made in the same request (as happens in
        `get_form_kwargs()`) to avoid revalidating forms unnecessarily.
        """
        self.cleaned_data = getattr(self, "cleaned_data", {})
        if step in self.cleaned_data:
            return self.cleaned_data[step]

        self.cleaned_data[step] = super().get_cleaned_data_for_step(step)
        return self.cleaned_data[step]

    def format_date(self, date_str):
        """Parses and converts a date string from that used for storing data to
        the one used in the TAP UI."""
        if date_str:
            date_object = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            return date_object.strftime(DATE_FORMAT)
        return ""

    def get_staged_definition_data(self):
        return self.request.session["staged_definition_data"]

    def get_main_definition(self, main_definition_pk):
        return models.QuotaDefinition.objects.get(pk=main_definition_pk)

    def get_form_kwargs(self, step):
        kwargs = {}
        if step == self.SELECT_DEFINITION_PERIODS:
            main_quota_order_number_sid = self.get_cleaned_data_for_step(
                self.QUOTA_ORDER_NUMBERS,
            )["main_quota_order_number"].sid
            main_quota_definitions = (
                models.QuotaDefinition.objects.filter(
                    order_number__sid=main_quota_order_number_sid,
                )
                .current()
                .order_by("pk")
            )
            kwargs["request"] = self.request
            kwargs["objects"] = main_quota_definitions

        elif step == self.SELECTED_DEFINITIONS:
            kwargs["request"] = self.request

        return kwargs

    def status_tag_generator(self, definition) -> dict:
        """
        Based on the status_tag_generator() for the Measure create Process
        queue.

        Returns a dict with text and a CSS class for a label for a duplicated
        definition.
        """
        if definition["status"]:
            return {
                "text": "Edited",
                "tag_class": "tamato-badge-light-green",
            }
        else:
            return {
                "text": "Unedited",
                "tag_class": "tamato-badge-light-blue",
            }

    def done(self, form_list, **kwargs):
        cleaned_data = self.get_all_cleaned_data()

        with transaction.atomic():
            for definition in cleaned_data["staged_definitions"]:
                self.create_definition(definition)
        sub_quota_view_url = reverse(
            "quota_definition-ui-list",
            kwargs={"sid": cleaned_data["main_quota_order_number"].sid},
        )
        sub_quota_view_query_string = "quota_type=sub_quotas&submit="
        self.request.session["success_data"] = {
            "main_quota": cleaned_data["main_quota_order_number"].order_number,
            "sub_quota": cleaned_data["sub_quota_order_number"].order_number,
            "definition_view_url": (
                f"{sub_quota_view_url}?{sub_quota_view_query_string}"
            ),
        }

        return redirect("sub_quota_definitions-ui-success")

    def create_definition(self, definition):
        staged_data = deserialize_definition_data(
            self,
            definition["sub_definition_staged_data"],
        )
        transaction = self.workbasket.new_transaction()
        instance = models.QuotaDefinition.objects.create(
            **staged_data,
            transaction=transaction,
        )
        models.QuotaAssociation.objects.create(
            main_quota=models.QuotaDefinition.objects.get(
                pk=definition["main_definition"],
            ),
            sub_quota=instance,
            coefficient=Decimal(
                definition["sub_definition_staged_data"]["coefficient"],
            ),
            sub_quota_relation_type=definition["sub_definition_staged_data"][
                "relationship_type"
            ],
            update_type=UpdateType.CREATE,
            transaction=transaction,
        )


class QuotaDefinitionDuplicateUpdates(
    FormView,
    BusinessRulesMixin,
):
    """UI endpoint for any updates to duplicated definitions."""

    template_name = "quota-definitions/sub-quota-definitions-updates.jinja"
    form_class = forms.SubQuotaDefinitionsUpdatesForm
    permission_required = "common.add_trackedmodel"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["pk"] = self.kwargs["pk"]
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["page_title"] = "Update definition and association details"
        context["quota_order_number"] = self.kwargs["pk"]
        return context

    def get_main_definition(self):
        return models.QuotaDefinition.objects.current().get(
            trackedmodel_ptr_id=self.kwargs["pk"],
        )

    def form_valid(self, form):
        main_definition = self.get_main_definition()
        cleaned_data = form.cleaned_data
        updated_serialized_data = {
            "initial_volume": str(cleaned_data["initial_volume"]),
            "volume": str(cleaned_data["volume"]),
            "measurement_unit_code": cleaned_data["measurement_unit"].code,
            "start_date": serialize_date(cleaned_data["valid_between"].lower),
            "end_date": serialize_date(cleaned_data["valid_between"].upper),
            "status": True,
            "coefficient": str(cleaned_data["coefficient"]),
            "relationship_type": cleaned_data["relationship_type"],
        }
        staged_definition_data = self.request.session["staged_definition_data"]
        list(
            filter(
                lambda staged_definition_data: staged_definition_data["main_definition"]
                == main_definition.pk,
                staged_definition_data,
            ),
        )[0]["sub_definition_staged_data"] = updated_serialized_data

        return redirect(reverse("sub_quota_definitions-ui-create"))


class QuotaDefinitionDuplicatorSuccess(TemplateView):
    template_name = "quota-definitions/sub-quota-definitions-done.jinja"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        success_data = self.request.session["success_data"]
        context["main_quota"] = success_data["main_quota"]
        context["sub_quota"] = success_data["sub_quota"]
        context["definition_view_url"] = success_data["definition_view_url"]
        return context
