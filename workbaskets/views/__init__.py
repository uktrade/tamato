from django.shortcuts import redirect
from django.shortcuts import render
from rest_framework import renderers
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.reverse import reverse

from common.renderers import TaricXMLRenderer
from workbaskets.models import WorkBasket
from workbaskets.models import WorkflowStatus
from workbaskets.serializers import WorkBasketSerializer
from workbaskets.validators import WorkflowStatus


class WorkBasketViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows workbaskets to be viewed and edited.
    """

    queryset = WorkBasket.objects.all()
    serializer_class = WorkBasketSerializer
    renderer_classes = [
        renderers.JSONRenderer,
        renderers.BrowsableAPIRenderer,
        TaricXMLRenderer,
    ]
    search_fields = ["title"]
    template_name = "workbaskets/taric/transaction_list.xml"

    def get_template_names(self, *args, **kwargs):
        if self.detail:
            return ["workbaskets/taric/transaction_detail.xml"]
        return ["workbaskets/taric/transaction_list.xml"]


class WorkBasketUIViewSet(WorkBasketViewSet):
    """
    UI endpoint that allows workbaskets to be viewed and edited.
    """

    renderer_classes = [renderers.TemplateHTMLRenderer]

    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        return render(
            request, "workbaskets/list.jinja", context={"workbaskets": queryset}
        )

    def retrieve(self, request, *args, **kwargs):
        # XXX needs updating to use TrackedModel
        # items = self.get_object().items.prefetch_related("existing_record").all()
        # groups = dict()
        # for item in items:
        #     group_name = item.existing_record.__class__._meta.verbose_name_plural
        #     groups.setdefault(group_name, []).append(item.existing_record)
        # groups = sorted(list(groups.items()), key=lambda tup: tup[0])
        groups = []
        return render(
            request,
            "workbaskets/detail.jinja",
            context={"workbasket": self.get_object(), "workbasketitem_groups": groups},
        )

    @action(detail=False, methods=["get"])
    def choose_or_create(self, request):
        queryset = self.filter_queryset(self.get_queryset()).filter(
            status__in=[WorkflowStatus.NEW_IN_PROGRESS, WorkflowStatus.EDITING,],
        )
        return render(
            request, "workbaskets/choose-or-create.jinja", context={"objects": queryset}
        )

    @action(detail=False, methods=["post"])
    def set_current_workbasket(self, request):
        if request.data["workbasket"] == "new":
            workbasket = WorkBasket.objects.create(
                title=request.data["title"],
                reason=request.data["reason"],
                author=request.user,
            )
        else:
            workbasket = WorkBasket.objects.get(pk=int(request.data["workbasket"]))

        request.session["workbasket"] = workbasket.to_json()
        return redirect(request.session.get("return_to", reverse("index")))
