import logging
from types import ModuleType
from typing import Collection

from django.urls import URLPattern
from django.urls import path

logger = logging.getLogger(__name__)


BULK_ACTIONS = {
    # <class_name_suffix>: <action_name>
    "List": "",
    "Create": "create",
}

OBJECT_ACTIONS = {
    # <class_name_suffix>: <action_name>
    "ConfirmCreate": "confirm-create",
    "Detail": "",
    "Update": "edit",
    "ConfirmUpdate": "confirm-update",
    "Delete": "delete",
}


def get_ui_paths(
    views: ModuleType,
    pattern: str,
    **subrecords: str,
) -> Collection[URLPattern]:
    """
    Return a set of routes auto-generated from the passed views module, based on
    a set of conventions for TrackedModels. This will attempt to create routes
    for the paths listed in BULK_ACTIONS and OBJECT_ACTIONS, for both a root
    record and a description record if the `description_detail` is passed. Any
    views that aren't implemented for the passed views module are ignored. The
    conventions are:

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
    app_name = views.__name__.split(".")[0]

    combinations = [
        (app_name[:-1], BULK_ACTIONS, ""),
        (app_name[:-1], OBJECT_ACTIONS, pattern),
    ]

    for name, pattern in subrecords.items():
        combinations.append((f"{app_name[:-1]}_{name}", OBJECT_ACTIONS, pattern))

    paths = []
    for prefix, actions, pattern in combinations:
        for class_suffix, pathname in actions.items():
            class_prefix = "".join(word.title() for word in prefix.split("_"))
            classname = class_prefix + class_suffix
            if hasattr(views, classname):
                view = getattr(views, classname)
                name = f"{prefix}-ui-{pathname if pathname else class_suffix.lower()}"
                url = pattern + ("/" if pattern else "") + pathname

                paths.append(path(url, view.as_view(), name=name))
            else:
                logger.debug("No action %s for %s", classname, app_name)

    return paths


def dunder_to_camel(dunderised):
    return "".join(word.title() for word in dunderised.split("_"))


def camel_to_dunder(capitalised):
    dunderised = ""
    for i, c in enumerate(capitalised):
        if c.isupper() and i == 0:
            dunderised += c.lower()
        elif c.isupper():
            dunderised += f"_{c.lower()}"
        else:
            dunderised += c
    return dunderised


"""
Notes:
* Because class entities and their child description classes are in the same
  view module we need a way to filter which views we're creating paths for, so
  the need for class_name_prefix param.
* Because the url can contain a the parent's url base, which can't be generated
  using view_module and class_name_prefix, we need to pass it in as url_base.
"""


def get_ui_paths_ext(
    view_module: ModuleType,
    class_name_prefix: str,
    object_id_pattern: str,
    url_base: str = "",
) -> Collection[URLPattern]:
    #   (actions, action_url_pattern)
    actions_pattern_map = [
        (BULK_ACTIONS, ""),
        (OBJECT_ACTIONS, object_id_pattern),
    ]

    paths = []

    # Iterate through all the actions and their patterns.
    for actions, action_url_pattern in actions_pattern_map:
        for class_name_suffix, action_name in actions.items():

            class_name = class_name_prefix + class_name_suffix

            if hasattr(view_module, class_name):
                view_class = getattr(view_module, class_name)

                # Create path name.
                path_name_suffix = action_name
                if not path_name_suffix:
                    path_name_suffix = class_name_suffix.lower()
                dundered_prefix = camel_to_dunder(class_name_prefix)
                path_name = f"{dundered_prefix}-ui-{path_name_suffix}"

                # Create URL.
                url_prefix = ""
                if action_url_pattern:
                    url_prefix = action_url_pattern + "/"
                url = url_base + url_prefix + action_name

                # Create path instance and append to paths list.
                paths.append(
                    path(url, view_class.as_view(), name=path_name),
                )
            else:
                logger.debug(
                    f"No action {class_name} for {view_module.__name__.split('.')[0]}",
                )

    return paths
