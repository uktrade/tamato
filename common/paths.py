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
    # Edits on taric objects that are in a WorkBasket with status=EDITING.
    "EditCreate": "edit-create",
    "EditUpdate": "edit-update",
}
"""Map of view class name suffixes to URL path action names, used to handle
object-level actions."""


def get_ui_paths(
    views: ModuleType,
    detail_pattern: str,
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
    * OBJECT_ACTIONS have URLs that are prefixed with a `detail_pattern`
    * Subrecords have URLs that are prefixed with both `subrecord` patterns
    * The name of the path is the same as the URL, apart from if the URL is
      blank, in which case it is the lowercase of the action key.

    E.g. when passed `additional_codes.views` with the detail_pattern
    `<sid:sid>`, will return routes for:

    * Name "additional_code-ui-list" mapped to URL "" using view
      `AdditionalCodeList`
    * Name "additional_code-ui-detail" mapped to URL "<sid:sid>/" using view
      `AdditionalCodeDetail`
    * Name "additional_code-ui-update" mapped to URL "<sid:sid>/edit/" using
      view `AdditionalCodeUpdate`

    etc.
    """

    app_name_singular = views.__name__.split(".")[0][:-1]

    views_info = [
        # Bulk actions info.
        (app_name_singular, class_suffix, pathname, "")
        for class_suffix, pathname in BULK_ACTIONS.items()
    ] + [
        # Object actions info.
        (app_name_singular, class_suffix, pathname, detail_pattern)
        for class_suffix, pathname in OBJECT_ACTIONS.items()
    ]
    for subrecord_name, detail_pattern in subrecords.items():
        views_info += [
            # Object actions info for subrecords.
            (
                f"{app_name_singular}_{subrecord_name}",
                class_suffix,
                pathname,
                detail_pattern,
            )
            for class_suffix, pathname in OBJECT_ACTIONS.items()
        ]
    """
    views_info is a list of 4-tuples providing each providing the necessary
    details to construct a path for each type of possible view. A tuple
    comprises:
        (app_name_singular, class_suffix, pathname, detail_pattern)
    """

    paths = []
    for app_name_singular, class_suffix, pathname, detail_pattern in views_info:
        classname = get_view_class_prefix(app_name_singular) + class_suffix
        if hasattr(views, classname):
            view = getattr(views, classname)
            name = (
                f"{app_name_singular}-ui-"
                f"{pathname if pathname else class_suffix.lower()}"
            )
            url = detail_pattern + ("/" if detail_pattern else "") + pathname

            paths.append(path(url, view.as_view(), name=name))
        # else:
        #    logger.debug(f"No view matching {views.__name__}.{classname}")

    return paths


def get_view_class_prefix(app_name_singular):
    """Given one of Tamato's Django app names - in its singular format, for
    instance, additional_code - get the prefix portion of the view class's name
    for that application. The returned prefix follows the conventions for
    naming view classes for Tamato's TrackedModels."""
    return "".join(word.title() for word in app_name_singular.split("_"))
