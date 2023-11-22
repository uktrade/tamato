# Create your views here.
from django.views.generic import TemplateView


class ReferenceDocumentsListView(TemplateView):
    template_name = "reference_documents/list.jinja"
