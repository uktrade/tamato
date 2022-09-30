import logging
from types import ModuleType
from typing import Collection

from django.urls import URLPattern
from django.urls import path

logger = logging.getLogger(__name__)


BULK_ACTIONS = {
    "List": "",
    "Create": "create",
}
"""Map of view class name suffixes to URL path action names, used to handle
class-level actions."""


OBJECT_ACTIONS = {
    "ConfirmCreate": "confirm-create",
    "Detail": "",
    "Update": "edit",
    "ConfirmUpdate": "confirm-update",
    "Delete": "delete",
    "DescriptionCreate": "description-create",
}
"""Map of view class name suffixes to URL path action names, used to handle
object-level actions."""


def get_ui_paths(
    views: ModuleType,
    pattern: str,
    **subrecords: str,
) -> Collection[URLPattern]:
    """
    Return a set of routes auto-generated from the passed views module, based on
    a set of conventions for TrackedModels.

    This will attempt to create routes for the paths listed in BULK_ACTIONS and
    OBJECT_ACTIONS, for both a root record and a description record if the
    `description_detail` is passed. Any views that aren't implemented for the
    passed views module are ignored.

    The conventions are:

    * View classes in the views module begin with the singular of the app name
      (additional_codes -> AdditionalCode)
    * View classes in the views module end with one of the keys of BULK_ACTIONS
      or OBJECT_ACTIONS
    * The view class should be mapped to a URL that is the corresponding value
      of BULK_ACTIONS or OBJECT_ACTIONS
    * OBJECT_ACTIONS have URLs that are prefixed with a `pattern`
    * Subrecords have URLs that are prefixed with both `subrecord` patterns
    * The name of the path is the same as the URL, apart from if the URL is
      blank, in which case it is the lowercase of the action key.

    E.g. when passed `additional_codes.views` with the pattern `<sid:sid>`, will
    return routes for:

    * Name "additional_code-ui-list" mapped to URL "" using view
      `AdditionalCodeList`
    * Name "additional_code-ui-detail" mapped to URL "<sid:sid>/" using view
      `AdditionalCodeDetail`
    * Name "additional_code-ui-update" mapped to URL "<sid:sid>/edit/" using
      view `AdditionalCodeUpdate`

    etc.
    """

    app_name_singular = views.__name__.split(".")[0][:-1]

    view_info = [
        # Bulk action patterns.
        (app_name_singular, class_suffix, pathname, "")
        for class_suffix, pathname in BULK_ACTIONS.items()
    ] + [
        # Object action patterns.
        (app_name_singular, class_suffix, pathname, pattern)
        for class_suffix, pathname in OBJECT_ACTIONS.items()
    ]
    for subrecord_name, pattern in subrecords.items():
        view_info += [
            # Object action patterns for subrecords.
            (f"{app_name_singular}_{subrecord_name}", class_suffix, pathname, pattern)
            for class_suffix, pathname in OBJECT_ACTIONS.items()
        ]
    """
    view_info is a list of 4-tuples, each comprising:
    (app_name_singular, class_suffix, pathname, pattern)
    """

    paths = []
    for app_name_singular, class_suffix, pathname, pattern in view_info:
        classname = get_view_class_prefix(app_name_singular) + class_suffix
        if hasattr(views, classname):
            view = getattr(views, classname)
            name = f"{app_name_singular}-ui-{pathname if pathname else class_suffix.lower()}"
            url = pattern + ("/" if pattern else "") + pathname

            paths.append(path(url, view.as_view(), name=name))
        else:
            # logger.debug(f"No view matching {views.__name__}.{classname}")
            pass

    return paths


def get_view_class_prefix(app_name_singular):
    """Given one of Tamato's Django app names - in its singular format, for
    instance additional_code - get the prefix portion of the view class name for
    that application."""
    return "".join(word.title() for word in app_name_singular.split("_"))
