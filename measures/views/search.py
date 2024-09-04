from typing import List
from urllib.parse import urlencode

from django.http import HttpResponseRedirect
from django.utils.functional import cached_property
from django.views.generic.edit import FormView
from django_filters.views import FilterView
from rest_framework.reverse import reverse

from additional_codes.models import AdditionalCode
from certificates.models import Certificate
from commodities.models.orm import GoodsNomenclature
from common.pagination import build_pagination_list
from common.views import SortingMixin
from common.views import TamatoListView
from footnotes.models import Footnote
from geo_areas.models import GeographicalArea
from measures import models
from measures.filters import MeasureFilter
from measures.pagination import MeasurePaginator
from regulations.models import Regulation
from workbaskets.forms import SelectableObjectsForm

from . import MeasureMixin
from . import MeasureSelectionMixin


class MeasureSearch(FilterView):
    """
    UI endpoint for filtering Measures.

    Does not list any measures. Redirects to MeasureList on form submit.
    """

    template_name = "measures/search.jinja"
    filterset_class = MeasureFilter

    def form_valid(self, form):
        return HttpResponseRedirect(reverse("measure-ui-list"))


class MeasureList(
    MeasureSelectionMixin,
    MeasureMixin,
    SortingMixin,
    FormView,
    TamatoListView,
):
    """UI endpoint for viewing and filtering Measures."""

    template_name = "measures/list.jinja"
    filterset_class = MeasureFilter
    form_class = SelectableObjectsForm
    sort_by_fields = ["sid", "measure_type", "geo_area", "start_date", "end_date"]
    custom_sorting = {
        "measure_type": "measure_type__sid",
        "geo_area": "geographical_area__area_id",
        "start_date": "valid_between",
        "end_date": "db_effective_end_date",
    }

    def dispatch(self, *args, **kwargs):
        if not self.request.GET:
            return HttpResponseRedirect(reverse("measure-ui-search"))
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()

        ordering = self.get_ordering()

        if ordering:
            if ordering in "-db_effective_end_date":
                queryset = queryset.with_effective_valid_between()

            ordering = (ordering,)
            queryset = queryset.order_by(*ordering)

        return queryset

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        page = self.paginator.get_page(self.request.GET.get("page", 1))
        kwargs["objects"] = page.object_list
        return kwargs

    def cleaned_query_params(self):
        # Remove the sort_by and ordered params in order to stop them being duplicated in the base url
        if "sort_by" and "ordered" in self.filterset.data:
            cleaned_filterset = self.filterset.data.copy()
            cleaned_filterset.pop("sort_by")
            cleaned_filterset.pop("ordered")
            return cleaned_filterset
        else:
            return self.filterset.data

    def selected_filter_formatter(self) -> List[List[str]]:
        """
        A function that formats the selected filter choices into nicely written
        up strings.

        Those strings are then split into nested lists of 7 items to prepare
        them for template rendering.
        """
        selected_filters = {k: v for k, v in self.filterset.data.items() if v}
        selected_filters_strings = []

        if "goods_nomenclature" in selected_filters:
            goods = GoodsNomenclature.objects.current().get(
                id=selected_filters["goods_nomenclature"],
            )
            selected_filters_strings.append(
                f"Commodity Code {goods.autocomplete_label}",
            )

        if "goods_nomenclature__item_id" in selected_filters:
            selected_filters_strings.append(
                f"Commodity Code starting with {selected_filters['goods_nomenclature__item_id']}",
            )

        if "order_number" in selected_filters:
            selected_filters_strings.append(
                f"Quota Order Number {selected_filters['order_number']}",
            )

        if "sid" in selected_filters:
            selected_filters_strings.append(f"ID {selected_filters['sid']}")

        if "additional_code" in selected_filters:
            code = AdditionalCode.objects.current().get(
                id=selected_filters["additional_code"],
            )
            selected_filters_strings.append(f"Additional Code {code.structure_code}")

        if "certificates" in selected_filters:
            certificate = Certificate.objects.current().get(
                id=selected_filters["certificates"],
            )
            selected_filters_strings.append(f"Certificate {certificate.structure_code}")

        if "regulation" in selected_filters:
            regulation = Regulation.objects.current().get(
                id=selected_filters["regulation"],
            )
            selected_filters_strings.append(
                f"Regulation {regulation.autocomplete_label}",
            )

        if "measure_type" in selected_filters:
            measure_type = models.MeasureType.objects.current().get(
                id=selected_filters["measure_type"],
            )
            selected_filters_strings.append(
                f"Measure Type {measure_type.autocomplete_label}",
            )

        if "geographical_area" in selected_filters:
            area = GeographicalArea.objects.current().get(
                id=selected_filters["geographical_area"],
            )
            selected_filters_strings.append(f"{area.autocomplete_label}")

        if "footnote" in selected_filters:
            footnote = Footnote.objects.current().get(id=selected_filters["footnote"])
            selected_filters_strings.append(f"Footnote {footnote.structure_code}")

        if all(
            sf in selected_filters
            for sf in ("start_date_0", "start_date_1", "start_date_1")
        ):
            if selected_filters["start_date_modifier"] == "exact":
                modifier = ""
            else:
                modifier = selected_filters["start_date_modifier"]
            selected_filters_strings.append(
                f"Start date: {modifier} {selected_filters['start_date_0']}/{selected_filters['start_date_1']}/{selected_filters['start_date_2']}",
            )

        if all(
            sf in selected_filters for sf in ("end_date_0", "end_date_1", "end_date_2")
        ):
            if selected_filters["end_date_modifier"] == "exact":
                modifier = ""
            else:
                modifier = selected_filters["end_date_modifier"]
            selected_filters_strings.append(
                f"End date: {modifier} {selected_filters['end_date_0']}/{selected_filters['end_date_1']}/{selected_filters['end_date_2']}",
            )

        if "modc" in selected_filters:
            selected_filters_strings.append("Include inherited measures")

        if "measure_filters_modifier" in selected_filters:
            selected_filters_strings.append("Filter by current workbasket")

        # This splits the selected_filter_strings into nested lists of 7 so that the lists can be shown side by side in the template.
        selected_filters_lists = [
            selected_filters_strings[x : x + 7]
            for x in range(0, len(selected_filters_strings), 7)
        ]

        return selected_filters_lists

    @cached_property
    def paginator(self):
        filterset_class = self.get_filterset_class()
        self.filterset = self.get_filterset(filterset_class)
        return MeasurePaginator(
            self.filterset.qs.select_related(
                "additional_code",
                "generating_regulation",
                "geographical_area",
                "goods_nomenclature",
                "measure_type",
                "order_number",
            ),
            per_page=40,
        )

    def get_context_data(self, **kwargs):
        # References to page or pagination in the template were heavily increasing load time. By setting everything we need in the context,
        # we can reduce load time
        page = self.paginator.get_page(self.request.GET.get("page", 1))
        context = {}
        context.update(
            {
                "filter": kwargs["filter"],
                "form": self.get_form(),
                "view": self,
                "is_paginated": True,
                "results_count": self.paginator.count,
                "results_limit_breached": self.paginator.limit_breached,
                "page_count": self.paginator.num_pages,
                "has_other_pages": page.has_other_pages(),
                "has_previous_page": page.has_previous(),
                "has_next_page": page.has_next(),
                "page_number": page.number,
                "list_items_count": self.paginator.per_page,
                "page_links": build_pagination_list(
                    page.number,
                    page.paginator.num_pages,
                ),
                "selected_filter_lists": self.selected_filter_formatter(),
            },
        )
        if context["has_previous_page"]:
            context["prev_page_number"] = page.previous_page_number()
        if context["has_next_page"]:
            context["next_page_number"] = page.next_page_number()

        context["measure_selections"] = models.Measure.objects.filter(
            pk__in=self.measure_selections,
        ).values_list("sid", flat=True)

        context["query_params"] = True
        context["base_url"] = (
            f'{reverse("measure-ui-list")}?{urlencode(self.cleaned_query_params())}'
        )
        return context

    def get_initial(self):
        return {**self.session_store.data}

    def form_valid(self, form):
        if form.data["form-action"] == "remove-selected":
            url = reverse("measure-ui-delete-multiple")
        elif form.data["form-action"] == "edit-selected":
            url = reverse("measure-ui-edit-multiple")
        elif form.data["form-action"] == "persist-selection":
            # keep selections from other pages. only update newly selected/removed measures from the current page
            selected_objects = {k: v for k, v in form.cleaned_data.items() if v}

            # clear this page from the session
            self.session_store.remove_items(form.cleaned_data)

            # then add the selected items
            self.session_store.add_items(selected_objects)

            params = urlencode(self.request.GET)
            url = reverse("measure-ui-list") + "?" + params
        else:
            url = reverse("measure-ui-list")

        return HttpResponseRedirect(url)
