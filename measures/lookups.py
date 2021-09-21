from ajax_select import LookupChannel
from ajax_select import register
from django.db.models import Q
from django.db.models import Value
from django.db.models.functions import Concat

from footnotes.models import Footnote


@register("footnotes")
class FootnotesLookup(LookupChannel):

    model = Footnote

    def get_query(self, q, request):
        qs = self.model.objects.annotate(
            id_fields_hyphen=Concat(
                "footnote_type__footnote_type_id",
                Value("-"),
                "footnote_id",
            ),
            id_fields=Concat("footnote_type__footnote_type_id", "footnote_id"),
        )
        return qs.filter(Q(id_fields_hyphen__icontains=q) | Q(id_fields__icontains=q))

    def format_match(self, obj):
        return obj.id_fields_hyphen

    def format_item_display(self, item):
        return f"<div class='govuk-body'><span class='footnote'>{item.footnote_type.footnote_type_id}-{item.footnote_id}</span></div>"
