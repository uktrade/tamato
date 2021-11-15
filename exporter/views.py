from collections import defaultdict
from typing import Dict
from typing import List
from typing import Type

from django.http import HttpRequest
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_GET

from common.models import TrackedModel
from common.models.tracked_utils import get_models_linked_to
from common.serializers import TrackedModelSerializer
from common.util import get_identifying_fields


def get_latest_tracked_models(request, per_page: int = 20) -> List[TrackedModel]:
    """
    Get the latest current objects in PK order. Paginate via the PK.

    Django Polymorphic struggles to use select_related across the inherited models.
    To get around this this function fetches the raw data from the TrackedModel table
    with the polymorphic_ctype (so the actual class we want) - 1 query.

    It then collects all these into a dictionary mapped against the actual class we
    want. Another query is then made against each class to get their data and related
    objects in one - 1 query per class.

    Query total = 1 + n (n = number of actual tracked classes involved).
    """
    starting_pk = request.GET.get("start")

    tracked_models = (
        TrackedModel.objects.latest_approved()
        .select_related("polymorphic_ctype")
        .order_by("-pk")
        .non_polymorphic()
    )

    if starting_pk:
        tracked_models = tracked_models.filter(pk__lt=starting_pk)

    obj_map: Dict[Type[TrackedModel], List[int]] = defaultdict(list)

    for obj in tracked_models[:per_page]:
        obj_map[obj.polymorphic_ctype.model_class()].append(obj.pk)

    full_tracked_models = []

    for tracked_class, pk_list in obj_map.items():
        full_tracked_models.extend(
            tracked_class.objects.filter(pk__in=pk_list).select_related(),
        )

    full_tracked_models.sort(key=lambda x: -x.pk)
    return full_tracked_models


def get_activity_stream_item_type(obj: TrackedModel) -> str:
    return f"dit:TaMaTo:{obj.__class__.__name__}"


def get_activity_stream_item_id(obj: TrackedModel) -> str:
    item_type = get_activity_stream_item_type(obj)
    return f"{item_type}:{''.join(str(value) for value in get_identifying_fields(obj).values())}"


def tracked_model_to_activity_stream_item(obj: TrackedModel):
    """
    Convert a TrackedModel into a data object suitable for consumption by
    Activity Stream as outlined in https://www.w3.org/TR/activitystreams-core/

    Instead of providing the full nested data for every related object the
    relations are removed and provided as their equivalent ActivityStream IDs.
    """

    item_type = get_activity_stream_item_type(obj)
    item_id = get_activity_stream_item_id(obj)
    published = obj.transaction.updated_at.isoformat()

    # Find all the relations to remove and replace with activity stream IDs.
    exclusions = []
    extra_data = {}
    for relation, _ in get_models_linked_to(type(obj)).items():
        exclusions.append(relation.name)
        relation_obj = getattr(obj, relation.name, None)
        if relation_obj:
            extra_data[f"{item_type}:{relation.name}"] = get_activity_stream_item_id(
                relation_obj,
            )

    obj_data = {
        f"{item_type}:{key}": value
        for key, value in TrackedModelSerializer(
            obj,
            read_only=True,
            context={"format": "json"},
            child_kwargs={"omit": exclusions},
        ).data.items()
    }

    if f"{item_type}:valid_between" in obj_data:
        # DITs Elastic system has these as keywords:
        # https://github.com/uktrade/activity-stream/blob/e6fc63f/core/app/app_outgoing_elasticsearch.py#L335
        extra_data["startTime"] = obj_data[f"{item_type}:valid_between"].get("lower")
        extra_data["endTime"] = obj_data[f"{item_type}:valid_between"].get("upper")

    obj_data.update(**extra_data)

    data = {
        "id": item_id,
        "published": published,
        "object": {
            "id": item_id,
            "type": item_type,
            "name": str(obj),
            **obj_data,
        },
    }

    return data


def next_url(tracked_model: TrackedModel, request: HttpRequest) -> str:
    return request.build_absolute_uri(
        reverse("activity-stream") + f"?start={tracked_model.pk}",
    )


@require_GET
def activity_stream(request):
    """
    Build an activity stream response of the latest and current TrackedModels.

    TrackedModels are provided in reverse PK order. If a starting PK is provided
    in the request then only TrackedModels with PK less than the provided one
    are given.

    The response conforms to the ActivityStream format defined at
    https://www.w3.org/TR/activitystreams-core/
    """
    per_page = 50

    tracked_models = get_latest_tracked_models(request, per_page)

    page = {
        "@context": [
            "https://www.w3.org/ns/activitystreams",
            {"dit": "https://www.trade.gov.uk/ns/activitystreams/v1"},
        ],
        "type": "Collection",
        "orderedItems": [
            tracked_model_to_activity_stream_item(tracked_object)
            for tracked_object in tracked_models
        ],
        **(
            {"next": next_url(tracked_models[-1], request)}
            if len(tracked_models) == per_page
            else {}
        ),
    }

    return JsonResponse(
        data=page,
        status=200,
    )
