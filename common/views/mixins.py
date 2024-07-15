from typing import Optional
from typing import Tuple
from typing import Type

from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.paginator import Paginator
from django.db.models import Model
from django.db.models import QuerySet
from django.http import Http404

from common.business_rules import BusinessRule
from common.business_rules import BusinessRuleViolation
from common.models import TrackedModel
from common.pagination import build_pagination_list


class WithPaginationListMixin:
    """Mixin that can be inherited by a ListView subclass to enable this
    project's pagination capabilities."""

    paginator_class = Paginator
    paginate_by = settings.REST_FRAMEWORK["PAGE_SIZE"]

    def get_context_data(self, *, object_list=None, **kwargs):
        """Adds a page link list to the context."""
        data = super().get_context_data(object_list=object_list, **kwargs)
        page_obj = data["page_obj"]
        page_number = page_obj.number
        data["page_links"] = build_pagination_list(
            page_number,
            page_obj.paginator.num_pages,
        )
        return data


class RequiresSuperuserMixin(UserPassesTestMixin):
    """Only allow superusers to see this view."""

    def test_func(self):
        return self.request.user.is_superuser


class TrackedModelDetailMixin:
    """Allows detail URLs to use <Identifying-Fields> instead of <pk>"""

    model: Type[TrackedModel]
    required_url_kwargs = None

    def get_object(self, queryset: Optional[QuerySet] = None) -> Model:
        """
        Fetch the model instance by primary key or by identifying_fields in the
        URL.

        :param queryset Optional[QuerySet]: Get the object from this queryset
        :rtype: Model
        """
        if queryset is None:
            queryset = self.get_queryset()

        required_url_kwargs = self.required_url_kwargs or self.model.identifying_fields

        if any(key not in self.kwargs for key in required_url_kwargs):
            raise AttributeError(
                f"{self.__class__.__name__} must be called with {', '.join(required_url_kwargs)} in the URLconf.",
            )

        queryset = queryset.filter(**self.kwargs)

        try:
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404(f"No {self.model.__name__} matching the query {self.kwargs}")

        return obj


class BusinessRulesMixin:
    """Check business rules on form_submission."""

    validate_business_rules: Tuple[Type[BusinessRule], ...] = tuple()

    def form_violates(self, form, transaction=None) -> bool:
        """
        If any of the specified business rules are violated, reshow the form
        with the violations as form errors.

        :param form: The submitted form
        :param transaction: The transaction containing the version of the object to be validated. Defaults to `self.object.transaction`
        """
        violations = False
        transaction = transaction or self.object.transaction

        for rule in self.validate_business_rules:
            try:
                rule(transaction).validate(self.object)
            except BusinessRuleViolation as v:
                form.add_error(None, v.args[0])
                violations = True

        return violations

    def form_valid(self, form):
        if self.form_violates(form):
            return self.form_invalid(form)

        return super().form_valid(form)


class DescriptionDeleteMixin:
    """Prevents the only description of the described object from being
    deleted."""

    def form_valid(self, form):
        described_object = self.object.get_described_object()
        if described_object.get_descriptions().count() == 1:
            form.add_error(
                None,
                "This description cannot be deleted because at least one description record is mandatory.",
            )
            return self.form_invalid(form)
        return super().form_valid(form)


class SortingMixin:
    """
    Can be used to sort a queryset in a view using GET params. Checks the GET
    param against sort_by_fields to pass a valid field to .order_by(). If the
    GET param doesn't match the desired .order_by() field, a dictionary mapping
    can be added as custom_sorting.

    Example usage:

    class YourModelListView(SortingMixin, ListView):
        sort_by_fields = ["sid", "model", "valid_between"]
        custom_sorting = {
            "model": "model__polymorphic_ctype",
        }

        def get_queryset(self):
            self.queryset = YourModel.objects.all()
            return super().get_queryset()
    """

    def get_ordering(self):
        sort_by = self.request.GET.get("sort_by")
        ordered = self.request.GET.get("ordered")
        assert hasattr(
            self,
            "sort_by_fields",
        ), "SortingMixin requires class attribute sort_by_fields to be set"
        assert isinstance(self.sort_by_fields, list), "sort_by_fields must be a list"

        if sort_by and sort_by in self.sort_by_fields:
            if hasattr(self, "custom_sorting") and self.custom_sorting.get(sort_by):
                sort_by = self.custom_sorting.get(sort_by)

            if ordered == "desc":
                sort_by = f"-{sort_by}"

            return sort_by

        else:
            return None
