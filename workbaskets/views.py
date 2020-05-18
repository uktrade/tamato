from django.shortcuts import render
from rest_framework import permissions
from rest_framework import renderers
from rest_framework import viewsets

from workbaskets.models import WorkBasket
from workbaskets.models import WorkBasketItem
from workbaskets.serializers import WorkBasketItemSerializer
from workbaskets.serializers import WorkBasketSerializer


class WorkBasketViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows workbaskets to be viewed and edited.
    """

    queryset = WorkBasket.objects.all()
    serializer_class = WorkBasketSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["title"]


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
        items = self.get_object().items.prefetch_related("existing_record").all()
        groups = dict()
        for item in items:
            group_name = item.existing_record.__class__._meta.verbose_name_plural
            groups.setdefault(group_name, []).append(item.existing_record)
        groups = sorted(list(groups.items()), key=lambda tup: tup[0])
        return render(
            request,
            "workbaskets/detail.jinja",
            context={"workbasket": self.get_object(), "workbasketitem_groups": groups},
        )


class WorkBasketItemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows workbasket items to be viewed.
    """

    queryset = WorkBasketItem.objects.all()
    serializer_class = WorkBasketItemSerializer
    permission_classes = [permissions.IsAuthenticated]
