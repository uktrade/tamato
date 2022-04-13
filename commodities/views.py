from datetime import date

from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import FormView
from django.views.generic import TemplateView
from rest_framework import permissions
from rest_framework import viewsets

from commodities.filters import GoodsNomenclatureFilterBackend
from commodities.forms import CommodityImportForm
from commodities.models import GoodsNomenclature
from common.serializers import AutoCompleteSerializer
from workbaskets.models import WorkBasket
from workbaskets.views.decorators import require_current_workbasket
from workbaskets.views.mixins import WithCurrentWorkBasket


class GoodsNomenclatureViewset(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows Goods Nomenclature to be viewed."""

    serializer_class = AutoCompleteSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [GoodsNomenclatureFilterBackend]

    def get_queryset(self):
        """
        API endpoint for autocomplete as used by the MeasureCreationWizard.

        Only return valid names that are products (suffix=80)
        """
        tx = WorkBasket.get_current_transaction(self.request)
        return (
            GoodsNomenclature.objects.approved_up_to_transaction(
                tx,
            )
            .prefetch_related("descriptions")
            .as_at(date.today())
            .filter(suffix=80)
        )


@method_decorator(require_current_workbasket, name="dispatch")
class CommodityImportView(FormView, WithCurrentWorkBasket):
    template_name = "commodities/import.jinja"
    form_class = CommodityImportForm
    success_url = reverse_lazy("commodities-import-success")

    def form_valid(self, form):
        form.save(user=self.request.user, workbasket_id=self.workbasket.id)
        return super().form_valid(form)


class CommodityImportSuccessView(TemplateView):
    template_name = "commodities/import-success.jinja"
