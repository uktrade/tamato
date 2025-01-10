"""WorkBasket models."""

import importlib
import logging
from abc import ABCMeta
from abc import abstractmethod
from os import urandom
from typing import Optional
from typing import Tuple

from celery.result import AsyncResult
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Case
from django.db.models import DateField
from django.db.models import F
from django.db.models import Max
from django.db.models import QuerySet
from django.db.models import Subquery
from django.db.models import Value
from django.db.models import When
from django_fsm import FSMField
from django_fsm import transition

from checks.models import TrackedModelCheck
from checks.models import TransactionCheck
from common.models.mixins import TimestampedMixin
from common.models.mixins.validity import ValidityMixin
from common.models.tracked_qs import TrackedModelQuerySet
from common.models.trackedmodel import TrackedModel
from common.models.transactions import Transaction
from common.models.transactions import TransactionPartition
from common.models.transactions import TransactionQueryset
from measures.models import Measure
from measures.querysets import MeasuresQuerySet
from workbaskets.util import serialize_uploaded_data
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)

User = get_user_model()


class TransactionPartitionScheme:
    """
    TransactionPartitionScheme schemes store settings that change how
    transactions are partitioned in relation to Workbaskets.

    This needs references to both Transaction and Workbasket so currently lives
    in the workbaskets django app.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def get_approved_partition(self) -> TransactionPartition:
        pass

    @abstractmethod
    def get_partition(self, status: WorkflowStatus) -> TransactionPartition:
        pass


class SeedFirstTransactionPartitionScheme(TransactionPartitionScheme):
    """In the SeedFirstTransactionPartitionScheme the first approved workbasket
    maps to SEED_FILE transactions and all following approved workbaskets map to
    REVISION transactions."""

    description = "First workbasket contains SEED_FILE transactions, following workbaskets are REVISION."

    def get_approved_partition(self) -> TransactionPartition:
        """
        :return REVISION: if any approved workbaskets exist otherwise SEED_FILE.

        Implements the policy where approved transactions in the first workbasket are from the seed file
        and the rest of the approved transactions are revisions.

        Usage note:   This must to be called before workbasket status is changed otherwise it will only
                      ever return REVISION.
        """
        if WorkBasket.objects.filter(
            status__in=WorkflowStatus.approved_statuses(),
        ).exists():
            return TransactionPartition.REVISION
        return TransactionPartition.SEED_FILE

    def get_partition(self, status: WorkflowStatus) -> TransactionPartition:
        """
        :param status:  Workbasket status
        :return:  TransactionPartition that maps to the workbasket status.
        """
        if status not in WorkflowStatus.approved_statuses():
            # Bail out early if not approved and avoid query in the next if block.
            return TransactionPartition.DRAFT

        return self.get_approved_partition()


class UserTransactionPartitionScheme(TransactionPartitionScheme):
    """
    UserTransactionPartitionScheme allows the caller to specify which partition
    to map approved workbaskets to.

    If the user specifies SEED_FILE transaction where a REVISION transactions
    already exists, a ValueError is raised.
    """

    def __init__(self, approved_partition, description):
        """
        :param approved_partition:  TransactionPartition to map approved workbaskets to.
        :param description: Description of this scheme, displayed on the commandline.
        """
        self.approved_partition = approved_partition
        self.description = description
        if self.approved_partition not in TransactionPartition.approved_partitions():
            raise ValueError(
                f"partition_scheme {self.approved_partition} is not one of {TransactionPartition.approved_partitions()}",
            )

    def get_approved_partition(self) -> TransactionPartition:
        """Return approved_partition, raises a ValueError in the case where
        approved_partition is SEED_FILE, and a REVISION partition already
        exists, to avoid changing the global order of transactions."""
        if (
            self.approved_partition == TransactionPartition.SEED_FILE
            and Transaction.objects.filter(
                partition=TransactionPartition.REVISION,
            ).exists()
        ):
            raise ValueError(
                "Revision transactions exist, extra seed partitions may cause transaction ordering issues.",
            )

        return self.approved_partition

    def get_partition(self, status: WorkflowStatus) -> TransactionPartition:
        """
        :param status:  Workbasket status
        :return:  TransactionPartition that maps to the workbasket status.
        """
        if status not in WorkflowStatus.approved_statuses():
            # Bail out early if not approved and avoid query in the next if block.
            return TransactionPartition.DRAFT

        return self.get_approved_partition()

    def __eq__(self, other):
        if not type(other) == UserTransactionPartitionScheme:
            return False

        return other.approved_partition == self.approved_partition

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} approved_partition={self.approved_partition}>"
        )


# SEED_FIRST, REVISION_ONLY, SEED_ONLY can all be specified from the TRANSACTION_SCHEMA setting / environment variable.
SEED_FIRST = SeedFirstTransactionPartitionScheme()
REVISION_ONLY = UserTransactionPartitionScheme(
    TransactionPartition.REVISION,
    "Create REVISION transactions",
)
SEED_ONLY = UserTransactionPartitionScheme(
    TransactionPartition.SEED_FILE,
    "Create SEED_FILE transactions (disallowed if any REVISION transactions exist)",
)
# Dict of transaction partition schemas by keyed name, for reference from management commands.
TRANSACTION_PARTITION_SCHEMES = {
    "SEED_FIRST": SEED_FIRST,
    "SEED_ONLY": SEED_ONLY,
    "REVISION_ONLY": REVISION_ONLY,
}


def get_partition_scheme(scheme: Optional[str] = None) -> TransactionPartitionScheme:
    """
    :param scheme: Optional scheme, if None then settings.TRANSACTION_SCHEME is the default.

    Resolve transaction schema instance from string or setting which can
    either be a short name that is a key in TRANSACTION_PARTITION_SCHEMES or a fully
    qualified name that is a reference to an instance of TransactionPartitionScheme,
    for example one of:

      "workbaskets.models.SEED_FIRST"
      "workbaskets.models.SEED_ONLY"
      "workbaskets.models.REVISION"

    Celery is the use-case for passing strings instead of TransactionPartitionScheme instances as
    they are not serializable by the default json serializer.
    """
    error_msg = (
        f"{'settings.TRANSACTION_SCHEMA' if scheme is None else f'scheme parameter: {scheme}'}"
        " should be a string referencing an instance of"
        " workbasket.models.TransactionPartitionScheme such as 'workbaskets.models.SEED_FIRST'"
    )

    if scheme is None:
        # Default to settings.TRANSACTION_SCHEMA, verifying it is actually present.
        if not hasattr(settings, "TRANSACTION_SCHEMA"):
            # Setting must exist and contain a dot.
            raise ImproperlyConfigured(error_msg)
        scheme = settings.TRANSACTION_SCHEMA

    if not isinstance(scheme, str):
        raise ValueError(error_msg)

    if scheme in TRANSACTION_PARTITION_SCHEMES:
        # Short aliases SEED_FIRST, SEED_ONLY, REVISION_ONLY are an affordance for the command-line.
        return TRANSACTION_PARTITION_SCHEMES[scheme]

    # Resolve fully qualified scheme names, to allow use of schemes TRANSACTION_PARTITION_SCHEMES
    if "." not in scheme:
        raise ValueError(error_msg)

    module_name, class_name = scheme.rsplit(".", 1)
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        logger.error(e)
        raise ValueError(error_msg)

    schema = getattr(module, class_name, None)
    if not isinstance(schema, TransactionPartitionScheme):
        raise ValueError(error_msg)

    # All the sane ways this might be mis-configured should have been covered.
    return schema


class WorkBasketQueryset(QuerySet):
    def ordered_transactions(self):
        """
        This Workbaskets transactions in creation order.

        Note: tracked_models are ordered by record_code, subrecord_code by TransactionManager
        """
        workbasket_pks = self.values_list("pk", flat=True)
        return Transaction.objects.filter(
            workbasket__pk__in=Subquery(workbasket_pks),
        )

    def is_approved(self):
        return self.filter(
            status__in=WorkflowStatus.approved_statuses(),
            approver__isnull=False,
        )

    def is_not_approved(self):
        return self.exclude(
            status__in=WorkflowStatus.approved_statuses(),
            approver__isnull=False,
        )

    def editable(self):
        return self.filter(
            status=WorkflowStatus.EDITING,
        )

    def exclude_importing_imports(self):
        """Exclude workbaskets that currently have a related import status of
        IMPORTING."""
        from importer.models import ImportBatchStatus

        return self.exclude(importbatch__status=ImportBatchStatus.IMPORTING)

    def exclude_failed_imports(self):
        """Exclude workbaskets that have a related import status of FAILED."""
        from importer.models import ImportBatchStatus

        return self.exclude(importbatch__status=ImportBatchStatus.FAILED)


class TransactionPurgeException(Exception):
    """Raised under invalid conditions when purging transactions from a
    WorkBasket."""


class WorkBasket(TimestampedMixin):
    """
    A WorkBasket groups tariff edits which will be applied at the same time.

    WorkBasket
    fmt: off
    statusssian.net/wiki/spaces/TARIFFSALPHA/pages/953581609/a.+Workbasket+workflow /PS-IGNORE
    fmt: on
    """

    objects: WorkBasketQueryset = WorkBasketQueryset.as_manager()

    title = models.CharField(
        max_length=255,
        help_text="Short name for this workbasket",
        db_index=True,
        unique=True,
    )
    reason = models.TextField(
        blank=True,
        help_text="Reason for the changes to the tariff",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        editable=False,
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        editable=False,
        null=True,
        related_name="approved_workbaskets",
    )
    status = FSMField(
        default=WorkflowStatus.EDITING,
        choices=WorkflowStatus.choices,
        db_index=True,
        # Ideally, we would protect the status field from being modified except by the
        # transition methods, otherwise the workbasket contents can be left in an
        # invalid state.  Unfortunately if `protected` is True the `clean` method raises
        # an exception.
        protected=False,
        editable=False,
    )
    rule_check_task_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        unique=True,
    )

    transactions: TransactionQueryset

    def terminate_rule_check(self):
        """Terminate any task associated with the WorkBasket's rule checking, as
        identified by its rule_check_task_id."""

        logger.info(
            f"Attempting rule check termination for WorkBasket " f"pk={self.pk}.",
        )
        if not self.rule_check_task_id:
            logger.info(
                f"Unable to terminate rule check for WorkBasket "
                f"pk={self.pk} - "
                f"empty rule_check_task_id.",
            )
            return

        task_result = AsyncResult(self.rule_check_task_id)
        if not task_result:
            logger.info(
                f"Unable to terminate rule check for WorkBasket "
                f"pk={self.pk}, "
                f"rule_check_task_id={self.rule_check_task_id} - "
                f"task result is unavailable.",
            )
            return

        task_result.revoke()
        self.delete_checks()
        self.rule_check_task_id = None
        self.save()
        logger.info(
            f"Terminated rule check for WorkBasket pk={self.pk}.",
        )

    @property
    def rule_check_task_status(self):
        """Return the status of the WorkBasket's rule check task if it is
        available, otherwise return None."""
        if not self.rule_check_task_id:
            return None
        task_result = AsyncResult(self.rule_check_task_id)
        if not task_result:
            return None
        return task_result.status

    def rule_check_progress(self) -> Tuple[int, int]:
        """
        Provides progress of a rule check for the WorkBasket.

        Returns:
            num_completed: the number of transaction checks already completed
            total: the total number of transactions to be checked
        """
        transaction_checks = TransactionCheck.objects.filter(
            transaction__workbasket=self,
            completed=True,
        )
        num_completed = transaction_checks.count()

        transactions = Transaction.objects.filter(
            workbasket=self,
        )
        total = transactions.count()

        return num_completed, total

    @property
    def approved(self):
        return self.status in WorkflowStatus.approved_statuses()

    @property
    def autocomplete_label(self):
        return f"({self.pk})  {self.title} - {self.reason}"

    def __str__(self):
        return f"({self.pk}) [{self.status}]"

    def archive_workbasket_condition_is_empty(self) -> bool:
        """Django FSM condition: workbasket must be empty (no tracked models and no transactions) to transition to ARCHIVED status."""
        return not self.tracked_models.exists() and not self.transactions.exists()

    def is_fully_assigned(self) -> bool:
        """Returns True if a workbasket has been assigned to both a worker and a
        reviewer, otherwise False."""
        return self.worker_assignments.exists() and self.reviewer_assignments.exists()

    @transition(
        field=status,
        source=WorkflowStatus.EDITING,
        target=WorkflowStatus.ARCHIVED,
        conditions=[archive_workbasket_condition_is_empty],
        custom={"label": "Archive"},
    )
    def archive(self):
        """Mark a workbasket as no longer in use."""

    @transition(
        field=status,
        source=WorkflowStatus.ARCHIVED,
        target=WorkflowStatus.EDITING,
        custom={"label": "Unarchive"},
    )
    def unarchive(self):
        """Restore a workbasket to an in use state."""

    def approve(self, user: int, scheme_name: str):
        """
        Sets the approver_id to a user pk and moves all transactions to the
        specified partition.

        (This will normally mean a move from DRAFT to REVISION).
        """
        self.approver_id = user

        # Move transactions from the DRAFT partition into the REVISION partition.
        partition_scheme = get_partition_scheme(scheme_name)
        self.transactions.save_drafts(partition_scheme)

    @transition(
        field=status,
        source=WorkflowStatus.EDITING,
        target=WorkflowStatus.QUEUED,
        conditions=[is_fully_assigned],
        custom={"label": "Add to packaging queue."},
    )
    def queue(self, user: int, scheme_name: str):
        """Add workbasket to packaging queue."""
        self.full_clean()

        if not self.transactions.exists():
            return

        if self.unchecked_or_errored_transactions.exists():
            raise ValidationError(
                "Transactions have not yet been fully checked or contain errors",
            )

        self.approve(user, scheme_name)

    @transition(
        field=status,
        source=WorkflowStatus.QUEUED,
        target=WorkflowStatus.EDITING,
        custom={"label": "Restore a queued workbasket to an in use state."},
    )
    def dequeue(self):
        """A queued workbasket not yet downloaded by CDS requires further
        changes to be added."""

        self.transactions.move_to_draft()

    @transition(
        field=status,
        source=WorkflowStatus.QUEUED,
        target=WorkflowStatus.PUBLISHED,
        custom={"label": "Publish"},
    )
    def cds_confirmed(self):
        """HMRC CDS has accepted the changes to the tariff."""

    @transition(
        field=status,
        source=WorkflowStatus.QUEUED,
        target=WorkflowStatus.ERRORED,
        custom={"label": "Mark as in error"},
    )
    def cds_error(self):
        """If a workbasket, after approval, is then rejected by CDS it is
        important to roll back the current models to the previous approved
        version and revert transaction partition to DRAFT."""
        self.transactions.move_to_draft()

    @transition(
        field=status,
        source=WorkflowStatus.ERRORED,
        target=WorkflowStatus.EDITING,
        custom={"label": "Restore for further editing."},
    )
    def restore(self):
        """WorkBasket is ready to be worked on again after being rejected by
        CDS."""

    def set_as_current(self, user) -> None:
        """Set as the user's current workbasket."""
        user.current_workbasket = self
        user.save()

    @property
    def tracked_models(self) -> TrackedModelQuerySet:
        return TrackedModel.objects.filter(transaction__workbasket=self)

    @property
    def measures(self) -> MeasuresQuerySet:
        return Measure.objects.filter(transaction__workbasket=self)

    @classmethod
    def current(cls, request):
        """Get the user's current workbasket."""
        try:
            workbasket = request.user.current_workbasket
        except AttributeError:
            return None

        if workbasket is not None:
            if workbasket.status != WorkflowStatus.EDITING:
                request.user.remove_current_workbasket()
                return None
            return workbasket
        else:
            return None

    @classmethod
    def get_current_transaction(cls, request):
        workbasket = cls.current(request)
        if workbasket:
            return workbasket.current_transaction

        return Transaction.approved.last()

    def new_transaction(self, **kwargs):
        """Create a new transaction in this workbasket."""
        if "order" not in kwargs:
            txn = self.current_transaction
            kwargs["order"] = ((txn and txn.order) or 0) + 1

        if "partition" not in kwargs:
            # If partition was not specified, choose a partition scheme as configured from
            # settings and use that to determine which partition this is.
            partition_scheme = get_partition_scheme()
            kwargs["partition"] = partition_scheme.get_partition(
                self.status,
            )

        if "composite_key" not in kwargs:
            # Forms a composite key of a zero-padded 5 digit workbasket id + a randomly generated hexadecimal 11 character string.
            # The probability of a collision is miniscule. It becomes 1% around 600,000 transactions and likely (>50%) at around 5 million.
            if len(str(self.pk)) > 5:
                raise ValueError(
                    "Workbasket PK cannot be bigger than 5 digits for composite_key generation.",
                )
            workbasket_pk = str(self.pk).zfill(5)

            hex_string_11_digit = f"{urandom(6).hex()}"[:11]
            kwargs["composite_key"] = f"{workbasket_pk}{hex_string_11_digit}"

        # Get Transaction model via transactions.model to avoid circular import.
        return self.transactions.model.objects.create(workbasket=self, **kwargs)

    def purge_empty_transactions(self) -> int:
        """
        Delete any empty transactions associated with the workbasket. A
        workbasket must have a `status` of EDITING and will otherwise raise a
        TransactionPurgeException.

        Returns the number of transactions deleted.
        """
        if self.status != WorkflowStatus.EDITING:
            raise TransactionPurgeException(
                "Transactions may only be purged from WorkBaskets with a "
                "`status` value of `WorkflowStatus.EDITING`.",
            )
        count, _ = self.transactions.filter(tracked_models__isnull=True).delete()
        return count

    @property
    def current_transaction(self) -> Transaction:
        """
        Returns the most recent transaction according to the workbasket.

        The value returned is the transaction that should be used as input to
        `approved_up_to_transaction` and friends when data in the workbasket is
        being considered.

        This is last transaction ordered by partition and order, or the most
        recent approved transaction if no transactions are in the workbasket.
        """
        return self.transactions.last() or Transaction.approved.last()

    @property
    def tracked_model_checks(self):
        return TrackedModelCheck.objects.filter(
            transaction_check__transaction__workbasket=self,
        )

    @property
    def tracked_model_check_errors(self):
        return self.tracked_model_checks.filter(successful=False)

    def delete_checks(self):
        """Delete all TrackedModelCheck and TransactionCheck instances related
        to the WorkBasket."""
        TrackedModelCheck.objects.filter(
            transaction_check__transaction__workbasket=self,
        ).delete()
        TransactionCheck.objects.filter(
            transaction__workbasket=self,
        ).delete()

    @property
    def unchecked_or_errored_transactions(self):
        """
        Returns unchecked, errored or out of date transactions from the
        workbaskets.

        The query excludes transactions which have a corresponding transaction
        check which has been completed, successful and was created after the
        latest updated_at in the transactions tracked models. Lasted is
        retrieved by annotating all the transactions for the workbasket with the
        latest updated for its containing tracked models then we aggregate the
        latest time from all the transactions.
        """
        latest = (
            self.transactions.all()
            .annotate(latest_updated_in_transaction=Max("tracked_models__updated_at"))
            .aggregate(Max("latest_updated_in_transaction"))
        )
        returned = self.transactions.exclude(
            pk__in=TransactionCheck.objects.requires_update(False)
            .filter(
                completed=True,
                successful=True,
                transaction__workbasket=self,
                created_at__gt=latest["latest_updated_in_transaction__max"],
            )
            .values("transaction__pk"),
        )
        return returned

    @property
    def worker_assignments(self):
        """Returns a queryset of associated `TaskAssignee` instances filtered to
        match `AssignmentType.WORKBASKET_WORKER`."""
        from tasks.models import TaskAssignee

        return (
            TaskAssignee.objects.filter(task__workbasket=self)
            .workbasket_workers()
            .assigned()
        )

    @property
    def reviewer_assignments(self):
        """Returns a queryset of associated `TaskAssignee` instances filtered to
        match `AssignmentType.WORKBASKET_REVIEWER`."""
        from tasks.models import TaskAssignee

        return (
            TaskAssignee.objects.filter(task__workbasket=self)
            .workbasket_reviewers()
            .assigned()
        )

    @property
    def user_assignments(self):
        """Returns a queryset of associated `TaskAssignee` instances."""
        assignments = self.worker_assignments | self.reviewer_assignments
        return assignments

    @property
    def assigned_workers(self):
        """Returns a queryset of `User` instances assigned as workers."""
        user_ids = self.worker_assignments.values_list("user_id", flat=True)
        return User.objects.filter(id__in=user_ids)

    @property
    def assigned_reviewers(self):
        """Returns a queryset of `User` instances assigned as reviewers."""
        user_ids = self.reviewer_assignments.values_list("user_id", flat=True)
        return User.objects.filter(id__in=user_ids)

    def get_measures_to_end_date(self) -> QuerySet:
        """
        Returns a queryset of measures on end-dated commodities in the
        workbasket along with those commodities' end-dates.

        It filters out measures which have already ended.
        """

        from commodities.models.orm import GoodsNomenclature

        end_dated_commodities = GoodsNomenclature.objects.current().filter(
            transaction__workbasket=self,
            valid_between__upper_inf=False,
        )
        commodity_dict = {
            commodity.sid: commodity.valid_between
            for commodity in end_dated_commodities
        }
        measures_on_commodities = Measure.objects.current().filter(
            goods_nomenclature__sid__in=commodity_dict.keys(),
        )
        conditions = [
            When(
                goods_nomenclature__sid=commodity_sid,
                then=Value(commodity_valid_between),
            )
            for commodity_sid, commodity_valid_between in commodity_dict.items()
        ]
        measures = measures_on_commodities.annotate(
            commodity_valid_between=Case(
                *conditions,
                output_field=DateField(),
            ),
        )

        return measures.with_effective_valid_between().exclude(
            db_effective_valid_between__not_gt=F("commodity_valid_between"),
        )

    class Meta:
        verbose_name = "workbasket"
        verbose_name_plural = "workbaskets"


class DataUpload(models.Model):
    raw_data = models.TextField()
    workbasket = models.ForeignKey(
        WorkBasket,
        on_delete=models.CASCADE,
        editable=False,
        null=True,
    )

    @property
    def serialized(self):
        return serialize_uploaded_data(self.raw_data)


class DataRow(ValidityMixin, models.Model):
    data_upload = models.ForeignKey(
        DataUpload,
        on_delete=models.CASCADE,
        null=True,
        related_name="rows",
    )
    commodity = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    duty_sentence = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
