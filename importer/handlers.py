from __future__ import annotations

import logging
from copy import deepcopy
from typing import Iterable
from typing import List
from typing import Set
from typing import Type

from django.conf import settings
from django.utils.functional import classproperty
from rest_framework.serializers import ModelSerializer

from common.models import TrackedModel
from common.validators import UpdateType
from importer.nursery import TariffObjectNursery
from importer.utils import DispatchedObjectType
from importer.utils import LinksType
from importer.utils import generate_key

logger = logging.getLogger(__name__)


class MismatchedSerializerError(Exception):
    pass


class BaseHandlerMeta(type):
    """
    BaseHandler Metaclass to add validation and registration of each new Handler
    class.

    Handlers have relatively strict requirements for them to function.

    Firstly there are two required attributes:

    1. "tag" - a string which is what matches the handler against the incoming data.
    2. "serializer_class" - a ModelSerializer which is used to validate and create the database object.

    Without these attributes the class cannot function properly. To ensure these are defined the metaclass
    checks for their existence and type. If they aren't properly defined then an error is raised at compile
    time (i.e. on import).

    The second requirement is that handlers need to be attached to the nursery. This is so that the nursery
    can match them against the incoming data. To accommodate this all handlers are automatically registered
    with the nursery class once validated. This reduces boilerplate code.
    """

    def __new__(cls, name: str, bases: tuple, dct: dict):
        handler_class = super().__new__(cls, name, bases, dct)
        if not bases:
            # This is a top level class, we only want to register and validate subclasses
            return handler_class

        if dct.get("abstract"):
            return handler_class

        handler_class.abstract = False

        if not isinstance(getattr(handler_class, "tag"), str):
            raise AttributeError(f'{name} requires attribute "tag" to be a str.')

        if not issubclass(
            getattr(handler_class, "serializer_class", type),
            ModelSerializer,
        ):
            raise AttributeError(
                f'{name} requires attribute "serializer_class" to be a subclass of "ModelSerializer".',
            )

        TariffObjectNursery.register_handler(handler_class)
        return handler_class


class BaseHandler(metaclass=BaseHandlerMeta):
    """
    The Base class for import handlers.

    Handlers are designed to build objects which are then ready to be entered into the database.
    This effectively takes place in 8 stages:

    Init:

    1) The handler is initialised with the initial data.

    Build:

    2) The handler checks for dependencies and links. If there are none it goes to step 5.
    3) The handler searches for dependencies which may contain extra required data. If any can't be found it
       asks to be cached and resolved later, the process stops. If they are found it unifies the data.
    4) The handler searches for any links (foreign keys) that it needs. If any can't be found it asks to be
       cached and resolved later, the process stops. If they are found it stores them.

    Dispatch:

    5) The handler validates the complete data against the serializer.
    6) The handler runs any pre-save processing, including adding the foreign keys to the validated data.
    7) The handler saves the object to the database.
    8) The handler runs any post-save processing.

    Many models are likely to have some specific requirements and so customisation is a focus within this system.
    But many use cases should also be workable with just the base.
    Most steps within this process can be customised and overridden - every model is likely to have some
    specific custom demands.

    A few examples of different scenarios follow below.

    Example 1
    ---------

    Simple object, no dependencies or links.

    For very simple objects there should be almost no work to do, assuming the data comes in clean without
    any need for editing. In this case it should be enough to simply define a handler like so:

    .. code:: python

        class SimpleObjectHandler(BaseHandler):
            serializer_class = serializers.SimpleObjectSerializer
            tag = parsers.SimpleObjectParser.tag.name

    Any object like this would be immediately processed when run through the nursery as, without any dependencies
    or links, there should be nothing it needs to wait on.


    Example 2
    ---------
    An object with dependencies:

    .. code:: python

        class DependentModelAHandler(BaseHandler):
            serializer_class = serializers.DependentModelSerializer
            tag = parser.DependentModelAParser.tag.name


        @DependentModelAHandler.register_dependant
        class DependentModelBHandler(BaseHandler):
            dependencies = [DependentModelAHandler]
            serializer_class = serializers.DependentModelSerializer
            tag = parser.DependentModelBParser.tag.name

    Dependencies in this case means two pre-existing models have been merged into one. Sadly the data import
    doesn't account for this and therefore it is expected to receive the complete set of data for this object
    over several records. A handler must therefore be created for each expected record type. All records will
    then be stored in the nursery cache until they can be collected together for processing.

    As dependencies are supposed to all relate to the same model, they must all share the same serializer.

    Dependencies cascade. Consequentially if object A depends on object B, but object B depends on object C,
    then object A will also depend on object C. However, given the nature of the dependencies, it is more
    desirable to have all handlers be explicit about all dependencies they may rely on.

    Dependencies are assigned at class level. Due to the way compilation works this creates issues with
    forward-referencing. To handle this there are two mechanisms for registering dependencies. The first
    is simply a class level dependency list with the dependent classes within them. The latter is with a
    decorator which allows a class to decorate itself - therefore inserting itself into the aforementioned
    dependency list of a pre-existing class.

    With this defined the nursery will collect the data for each dependency. The dependencies can then query
    the nursery to collect all the data. If all the data is found the object is dispatched to the database
    and the nursery removes the relevant data from the cache.


    Example 3
    ---------

    An object with Foreign Key links.

    .. code:: python

        class LinkedObjectHandler(BaseHandler):
            links = (
                {
                    "model": models.LinkToModelA,
                    "name": "link_to_model_a",
                    "optional": True,
                },
                {
                    "model": models.LinkToModelB,
                    "name": "link_to_model_b",
                    "optional": False,
                    "identifying_fields": ("some_field", "some_other_model_id")
                },
            )

            def get_link_to_model_b_link(self, model, kwargs):
                other_model = models.SomeOtherModel(field2=kwargs.get(some_other_model_id)
                return model.objects.get_latest_version(other_model=other_model, **kargs)

    Foreign key links are more flexible than dependencies. Whilst dependencies denote records which hold
    part of the data for an object, links denote pre-existing objects which the current object needs to link
    to. The difficulty here is there is no guarantee that the pre-existing object has actually been created
    yet, nor that the object necessarily _needs_ to exist (the foreign key could be nullable).

    Therefore Handlers have the option of adding a `links` attribute, which should be an iterable of `LinksType`
    style dictionaries. This must define two keys:

    1) model - which is expected to be a `TrackedModel` instance
    2) name - a string, which is how the link data will be differentiated from the object data, as well as
       how it will be named in the data when saved to the database. More specifically incoming data for the
       linked field (specifically the models identifying fields) is expected to be prefixed with this name.
       So the parser must define fields with this prefix.

    Two other optional keys exist:

    3) optional - defines whether a link is optional. If it is optional the object will be saved even if the
       link can't be found. If it is not optional then the object will be cached until the link can be found.
    4) identifying_fields - On occasion the identifying fields from model.identifying_fields may not be
       appropriate, in this case they can be overridden here.

    With just these the Handler will automatically try to fetch the linked model with the identifying fields of
    the model (or those given in the link dictionary). Once fetched it will store the data with the given name.
    Once ready to save the links will be added to the object data with the given name and the object will be saved.

    In some cases this is not enough and further customisation is needed when fetching links. An example is a link
    where one of the identifying fields is a foreign key on that linked field (i.e. the linked field itself has
    another link). To allow for this a method can be added to fetch the link appropriately. This method must be named
    `get_{link_name}_link` and accept the arguments `model` and `kwargs`. This must then return whatever object is
    intended to go into the data with the same name as that given to the link.

    All of the above examples can be used together, e.g. a handler can have both dependencies and links.
    """

    dependencies: List[Type[BaseHandler]] = None
    identifying_fields: Iterable[str] = None
    links: Iterable[LinksType] = None
    serializer_class: Type[ModelSerializer] = None
    tag: str = None

    def __init__(
        self,
        dispatched_object: DispatchedObjectType,
        nursery: TariffObjectNursery,
    ):
        self.nursery = nursery

        self.data = dispatched_object["data"]
        if not self.identifying_fields:
            self.identifying_fields = self.model.identifying_fields
        self.transaction_id = dispatched_object["transaction_id"]

        self.key = generate_key(
            tag=self.tag,
            identifying_fields=self.identifying_fields,
            data=self.data,
        )

        self.dependency_keys = self._generate_dependency_keys()
        self.resolved_links = {}

    def _generate_dependency_keys(self) -> Set[str]:
        """
        Objects are stored in the cache using unique but identifiable IDs. Any
        dependant object must be able to figure out all the keys for its
        dependencies.

        This method fetches all the dependencies, builds their keys and then
        returns the keys as a set.
        """
        depends_on = set()
        if not self.dependencies:
            return depends_on
        for dependency in self.dependencies:
            if dependency.serializer_class != self.serializer_class:
                raise MismatchedSerializerError(
                    f"Dependent parsers must have the same serializer_class as their dependencies. "
                    f"Dependency {dependency.__name__} has "
                    f"serializer_class {dependency.serializer_class.__name__}. "
                    f"{self.__class__.__name__} has serializer_class {self.serializer_class.__name__}.",
                )
            depends_on.add(
                generate_key(
                    tag=dependency.tag,
                    identifying_fields=self.identifying_fields,
                    data=self.data,
                ),
            )
        return depends_on

    def resolve_dependencies(self) -> bool:
        """
        Search the cache for all object dependencies and attempt to resolve
        them.

        Previously found objects, which are dependent on the current object, should be
        stored in the cache. This method loops over the current objects dependencies and
        attempts to extract them from the cache. It then also searches for the dependencies
        of the extracted objects.

        All found dependencies are then merged into the current objects data. If at any point
        a dependency is not found the method returns False - to signify the object cannot be resolved.
        If all dependencies are found the method returns True.
        """
        dependencies = self.dependency_keys.copy()
        resolved_dependencies = {self.key}

        while dependencies:
            key = dependencies.pop()
            dependency = self.nursery.get_handler_from_cache(key)
            if not dependency:
                return False
            self.data.update(dependency.data)
            resolved_dependencies.add(key)
            dependencies.update(set(dependency.dependency_keys) - resolved_dependencies)
        return True

    def get_generic_link(self, model, kwargs):
        """
        Fallback method if no specific method is found for fetching a link.

        Raises DoesNotExist if no kwargs passed.

        First attempts to retrieve the object PK from the cache (saves queries). If this
        is not found a database query is made to find the object.
        """
        if not any(kwargs.values()):
            raise model.DoesNotExist

        if settings.USE_IMPORTER_CACHE:
            cached_object = self.nursery.get_obj_from_cache(
                model,
                kwargs.keys(),
                kwargs,
            )
            if cached_object and cached_object[1] == model.__name__:
                return cached_object[0], True

        try:
            if self.data["update_type"] == UpdateType.DELETE:
                return (
                    model.objects.get_versions(**kwargs).current_deleted().get(),
                    False,
                )
            return model.objects.get_latest_version(**kwargs), False
        except model.DoesNotExist as e:
            if self.data["update_type"] == UpdateType.DELETE:
                return model.objects.get_latest_version(**kwargs), False
            raise e

    def load_link(self, name, model, identifying_fields=None, optional=False):
        """
        Load a given link for a handler.

        This method first attempts to find any custom method existing on the handler
        for finding the specific link. The custom method must be named:

            get_{LINK_NAME}_link

        If no custom method is found then :py:meth:`.BaseHandler.get_generic_link` is used.

        If no object matching the given link is found and the link is non-optional then a
        DoesNotExist error is raised.
        """
        identifying_fields = identifying_fields or model.identifying_fields
        try:
            linked_object_identifiers = {
                key: self.data.get(f"{name}__{key}") for key in identifying_fields
            }

            get_link_func = getattr(self, f"get_{name}_link", self.get_generic_link)

            linked_object = get_link_func(model, linked_object_identifiers)

            if isinstance(linked_object, tuple) and len(linked_object) > 1:
                if linked_object[1]:
                    self.resolved_links[f"{name}_id"] = linked_object[0]
                else:
                    self.resolved_links[name] = linked_object[0]
            else:
                self.resolved_links[name] = linked_object
        except model.DoesNotExist:
            if not optional:
                return False
        return True

    def resolve_links(self) -> bool:
        """
        Extract data specific to links and use this to search the database for
        the relevant objects.

        Once found attach the object to the `resolved_links` dictionary.

        If a non-optional object can't be found return False. This signifies the links cannot be resolved.
        If all non-optional objects are found then return True.
        """
        if not self.links:
            return True
        for link in self.links:
            if not self.load_link(**link):
                return False
        return True

    def clean(self, data: dict) -> dict:
        """Validate the data against the serializer and return the validated
        data."""
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def pre_save(self, data: dict, links: dict) -> dict:
        """
        Pre-processing before the object is saved to the database.

        Generally this is used for adding the links to the object (as these cannot
        be easily validated against the serializer).

        Return the final dataset to be used when saving to the database.
        """
        data = deepcopy(data)
        data.update(**links)
        return data

    def save(self, data: dict):
        return self.serializer_class().create(data)

    def post_save(self, obj):
        """
        Post-processing after the object has been saved to the database.

        By default this caches any new saved object.
        """
        self.nursery.cache_object(obj)

    def build(self) -> Set[str]:
        """
        Build up all the data for the object.

        This method co-ordinates the attempts to fetch the dependent data as well as the linked
        data. If at any point one of these steps fails an empty set returns (signifying failure).

        if all steps are deemed successful the object is dispatched to the database automatically.
        On success a set of all the keys for any objects used which may be in the cache is returned.
        """
        if not self.dependency_keys and not self.links:
            self.dispatch()
            return {self.key}

        if not self.resolve_dependencies() or not self.resolve_links():
            return set()

        self.dispatch()
        self.dependency_keys.add(self.key)
        return self.dependency_keys

    def dispatch(self) -> TrackedModel:
        """
        Save the data into the database.

        This method initially validates all collected data. If valid it then
        runs some pre-processing before saving. Once saved an opportunity is
        given for post-processing.
        """
        data = self.clean(self.data)
        data.update(transaction_id=self.transaction_id)

        logger.debug(f"Creating {self.model}: {data}")
        data = self.pre_save(data, self.resolved_links)
        obj = self.save(data)
        self.post_save(obj)

        return obj

    def serialize(self) -> DispatchedObjectType:
        """
        Provides a serializable dict of the object to be stored in the cache.

        Should hold all the necessary data required to rebuild the object
        """
        return {
            "data": self.data,
            "tag": self.tag,
            "transaction_id": self.transaction_id,
        }

    @classmethod
    def register_dependant(cls, dependant: Type[BaseHandler]):
        """
        Allow a handler to retrospectively assign itself to another handlers
        list of dependencies.

        This solves the issue of forward referencing - where a class cannot reference another class
        before that class has been defined.
        """
        if not cls.dependencies:
            cls.dependencies = [dependant]
        else:
            cls.dependencies.append(dependant)

        return dependant

    @classproperty
    def model(self) -> Type[TrackedModel]:
        return self.serializer_class.Meta.model
