from __future__ import annotations

import logging
from typing import Dict
from typing import Iterable
from typing import Optional
from typing import Type
from typing import TypeVar

from django.conf import settings
from django.db import models
from django.db.models import Manager
from django.db.models import Model
from polymorphic.managers import PolymorphicManager

from checks.querysets import BusinessRuleModelQuerySet
from checks.querysets import BusinessRuleResultQuerySet
from checks.querysets import BusinessRuleResultStatus
from checks.querysets import TrackedModelCheckQueryset
from common.business_rules import ALL_RULES
from common.business_rules import BusinessRule
from common.models.celerytask import TaskModel
from common.models.trackedmodel import TrackedModel
from common.models.transactions import Transaction

logger = logging.getLogger(__name__)

Self = TypeVar("Self", bound="BusinessRuleModel")


class BusinessRuleResult(models.Model):
    """
    Result of running a business rule.

    Links to the rule itself, in the case of FAILED or ERROR, a message is appended.

    See `BusinessRuleResultStatus` for information on the possible values.
    """

    objects = Manager.from_queryset(BusinessRuleResultQuerySet)()

    rule = models.ForeignKey("BusinessRuleModel", on_delete=models.SET_NULL, null=True)
    status = models.PositiveSmallIntegerField(choices=BusinessRuleResultStatus.choices)
    message = models.TextField(null=True, blank=True)

    @classmethod
    def from_pass(cls, rule_model: BusinessRuleModel) -> BusinessRuleResult:
        """Return a BusinessRuleResult  with a PASSED status."""
        return cls(
            rule=rule_model,
            status=BusinessRuleResultStatus.PASSED,
            message=None,
        )

    @classmethod
    def from_error(cls, rule, error):
        """
        Return a BusinessRuleResult from a BusinessRuleViolation or ordinary
        Exception.

        Users can optionally raise BusinessRuleViolations and Errors as
        exceptions by setting RAISE_BUSINESS_RULE_FAILURES or
        RAISE_BUSINESS_RULE_ERRORS
        """
        from common.business_rules import BusinessRuleViolation

        if isinstance(error, BusinessRuleViolation):
            if settings.RAISE_BUSINESS_RULE_FAILURES:
                # During development can be useful to raise business rule failures as exceptions.
                raise error

            return cls(
                rule=rule,
                status=BusinessRuleResultStatus.FAILED,
                message=error.args[0],
            )

        if settings.RAISE_BUSINESS_RULE_ERRORS:
            # During debugging can be useful to raise business rule errors as exceptions.
            raise error
        return cls(rule=rule, status=BusinessRuleResultStatus.ERROR, message=str(error))

    def __str__(self):
        status = BusinessRuleResultStatus(self.status).name
        if status == BusinessRuleResultStatus.PASSED:
            return f"{self.rule} [{status}]"
        return f"{self.rule} [{status}] \"{self.message or ''}\""

    def __repr__(self):
        return f"<BusinessRuleResult {self.rule} {BusinessRuleResultStatus(self.status).name} \"{self.message or ''}\">"


class BusinessRuleModel(Model):
    """
    Database representation of Business Rules.

    This table is maintained by the sync_business_rules management command to match the ALL_RULES dict
    it is inadvisable to edit this table directly outside of unit tests.

    Since BusinessRule is a widely already used class in the system, this model is named with the Model suffix.

    Note:  If BusinessRules implementation class is renamed, then a data migration may be required to carry on associating
    data to the business rule.
    """

    CACHED_RULE_MODELS: Dict[str, Type[Self]] = {}

    objects = Manager.from_queryset(BusinessRuleModelQuerySet)()

    name = models.CharField(max_length=255, unique=True)
    """The name of the business rule"""

    current = models.BooleanField(default=True)

    def get_implementation(self):
        return ALL_RULES[self.name]

    @classmethod
    def from_rule(cls: Self, rule: Type[BusinessRule]) -> Self:
        """
        Given a BusinessRule fetch it's corresponding model from the cache or
        database.

        If the model is not found it in the cache it will be fetched from the
        database and cached before returning.
        """
        instance = cls.CACHED_RULE_MODELS.get(rule.__name__)
        if instance is not None:
            return instance

        new_instance = BusinessRuleModel.objects.get(cls.__name__)
        cls.CACHED_RULE_MODELS[cls.__name__] = new_instance
        return new_instance

    @classmethod
    def from_rules(cls, rules: Iterable[Type[BusinessRule]]):
        """
        Fetch rule models, already in the cache will be returned, others will be
        fetched from the database and added to the cache before being returned.

        If the rules are not found in the cache or database a ValueError will be
        raised.
        """
        rule_names = [rule.__name__ for rule in rules]
        new_names = set(rule_names)

        # Yield the cached rules first, removing each one from the new_names set
        for rule_name in rule_names:
            if rule_name in cls.CACHED_RULE_MODELS:
                new_names.remove(rule_name)
                yield cls.CACHED_RULE_MODELS[rule_name]

        # Remaining rules must not be cached.
        instances = BusinessRuleModel.objects.filter(name__in=new_names)
        for instance in instances:
            cls.CACHED_RULE_MODELS[instance.name] = instance
            new_names.remove(instance.name)
            yield instance

        if new_names:
            raise ValueError(f"{[*new_names]} not found in cache or database.")

    def get_result(self, transaction, model):
        """
        Run a business rule on a model and return the result as a
        BusinessRuleResult.

        The result is not yet saved, this enables it to be used in bulk
        operations.
        """
        logger.debug(f"run_rule %s %s %s", model, self.name, transaction.pk)
        rule = self.get_implementation()
        try:
            rule(transaction).validate(model)
            return BusinessRuleResult.from_pass(self)
        except Exception as ex:
            return BusinessRuleResult.from_error(self, ex)

    def __str__(self):
        return self.name

    def __repr__(self):
        if not self.current:
            return f"<BusinessRuleModel {self.name} (removed)>"
        return f"<BusinessRuleModel {self.name}>"


class TrackedModelCheck(TaskModel):
    """
    Represents the result of running a single check against a single model.

    Stores `content_hash`, a hash of the content for validity checking of the
    stored result.
    """

    class Meta:
        unique_together = (("model", "head_transaction"),)

    objects = PolymorphicManager.from_queryset(TrackedModelCheckQueryset)()

    results = models.ManyToManyField(BusinessRuleResult)
    """Results of running requested business rules, if the check can be considered complete when there is a request 
    for each business rule to be checked. """

    model = models.OneToOneField(
        TrackedModel,
        related_name="trackedmodel_check",
        on_delete=models.SET_NULL,
        null=True,
    )
    content_hash = models.BinaryField(max_length=32, null=True)
    """
    Hash of the content ('copyable_fields') at the time the data was checked.
    """

    head_transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
    )
    """
    The latest transaction in the stream of approved transactions (i.e. in the
    REVISION partition) at the moment this check was carried out.

    Once new transactions are commited and the head transaction is no longer the
    latest, this check will no longer be an accurate signal of correctness
    because the new transactions could include new data which would invalidate
    the checks. (Unless the checked transaction < head transaction, in which
    case it will always be correct.)
    """
    # TODO ^ update this with info on caching strategies.

    def delete(self):
        self.content_hash = None
        super().delete()

    def report(self, rule_filter: Optional[BusinessRuleResultQuerySet] = None):
        """
        :param requested_rules: If provided, only report results for these rules.
        """
        if rule_filter:
            rule_filter = {
                "pk__in": rule_filter.values_list("pk", flat=True),
            }
        else:
            rule_filter = {}

        results = self.results.filter(**rule_filter)

        # Rules waiting to run.
        msg = f"[{self.model}] "

        msg += f"{results.passed().count()} passed"

        if not results.failed().count():
            msg += " 0 failed"

        if not results.errored().count():
            msg += " 0 errored"

        if results.failed():
            msg + "Failures:\n"
            for result in results.failed():
                msg += f"{result.rule.name}: {result.message}\n"

        if results.errored():
            msg + "Errors:\n"
            for result in results.errored():
                msg += f"{result.rule.name}: {result.message}\n"

        return msg
