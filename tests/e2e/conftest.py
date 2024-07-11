import os

import pytest
from django.conf import settings
from playwright.sync_api import Page

from checks.tests.factories import TrackedModelCheckFactory
from commodities.models import GoodsNomenclature
from common.models.transactions import Transaction
from common.models.utils import override_current_transaction
from common.tests import factories
from common.validators import ApplicabilityCode
from footnotes.models import Footnote
from footnotes.models import FootnoteType
from measures.models import MeasureType
from measures.validators import MeasureExplosionLevel
from publishing.models import OperationalStatus
from publishing.models import PackagedWorkBasket
from regulations.models import Regulation
from tasks.models import UserAssignment

from .utils import get_unique_id
from .utils import login

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


@pytest.fixture(scope="session")
def django_db_setup():
    """
    Enables an existing, external database to be used instead of a temporary
    test database.  Defaults to `settings.DATABASES["default"]`.

    To avoid flushing the database during `TransactionTestCase` teardown, a no-op function replaces the default flush command.
    """
    env = settings.ENV
    if env.startswith("prod"):
        pytest.exit(
            f"{env} is an unsuitable environment for running end-to-end tests that may have enduring side effects.",
        )

    def no_op(obj, **options):
        pass

    from django.core.management.commands import flush

    flush.Command.handle = no_op


@pytest.fixture(scope="session")
def base_url():
    """Returns the base URL of the server under test from
    `settings.BASE_SERVICE_URL`."""
    return settings.BASE_SERVICE_URL


@pytest.fixture
def page(page: Page, user, base_url):
    """Returns a Playwright browser page with a logged-in user."""
    login(page, user, base_url)
    return page


def clear_and_delete_workbasket(workbasket):
    """Deletes `workbasket` and all associated objects."""
    PackagedWorkBasket.objects.filter(workbasket=workbasket).delete()
    tracked_models = workbasket.tracked_models.all().record_ordering().reverse()
    for obj in tracked_models:
        obj.delete()
    workbasket.purge_empty_transactions()
    workbasket.tasks.all().delete()
    workbasket.delete_checks()
    workbasket.delete()


def create_user_assignments(workbasket):
    """Assigns a worker and reviewer to `workbasket`."""
    factories.UserAssignmentFactory.create(
        user=workbasket.author,
        assigned_by=workbasket.author,
        assignment_type=UserAssignment.AssignmentType.WORKBASKET_WORKER,
        task__workbasket=workbasket,
    )
    factories.UserAssignmentFactory.create(
        user=workbasket.author,
        assigned_by=workbasket.author,
        assignment_type=UserAssignment.AssignmentType.WORKBASKET_REVIEWER,
        task__workbasket=workbasket,
    )


def create_tracked_model_checks(tracked_models):
    """Creates a `TrackedModelCheck` for each object in `tracked_models`."""
    for obj in tracked_models:
        TrackedModelCheckFactory.create(
            model=obj,
            transaction_check__transaction=obj.transaction,
            transaction_check__latest_tracked_model=obj,
            transaction_check__head_transaction=obj.transaction,
            successful=True,
        )


@pytest.fixture
def user(django_user_model):
    """Returns an instance of the user specified in `settings.E2E_TEST_USER`."""
    return django_user_model.objects.get(username=settings.E2E_TEST_USER)


@pytest.fixture
def empty_current_workbasket(transactional_db, user):
    """Yields an empty, unassigned workbasket that has been set as the user's
    current workbasket."""
    workbasket = factories.WorkBasketFactory.create(
        title=get_unique_id(),
        reason=f"End-to-end test by {user.get_displayname()}",
        author=user,
    )
    workbasket.set_as_current(user)

    yield workbasket

    clear_and_delete_workbasket(workbasket)


@pytest.fixture
def current_workbasket(empty_current_workbasket):
    """Returns an unassigned workbasket (containing a tracked model) that has
    been set as the user's current workbasket."""
    current_workbasket = empty_current_workbasket
    factories.FootnoteDescriptionFactory.create(
        sid=None,
        described_footnote=Footnote.objects.as_at_today_and_beyond()
        .order_by("?")
        .first(),
        transaction=current_workbasket.new_transaction(),
    )
    return current_workbasket


@pytest.fixture
def workbasket_ready_for_queue(current_workbasket):
    """Returns an assigned workbasket that has passed a rule check and is ready
    to proceed through packaging queue."""
    create_tracked_model_checks(current_workbasket.tracked_models.all())
    create_user_assignments(current_workbasket)
    return current_workbasket


@pytest.fixture
def paused_queue(transactional_db, user):
    """Ensures the packaging queue is paused."""
    return OperationalStatus.pause_queue(user)


@pytest.fixture
def unpaused_queue(transactional_db, user):
    """Ensures the packaging queue is unpaused."""
    return OperationalStatus.unpause_queue(user)


@pytest.fixture
def commodity():
    """Returns the latest version of a currently active `GoodsNomenclature` at
    random."""
    with override_current_transaction(Transaction.objects.last()):
        return (
            GoodsNomenclature.objects.filter(suffix=80)
            .current()
            .as_at_today_and_beyond()
            .order_by("?")
            .first()
        )


@pytest.fixture
def footnote_type():
    """Returns the latest version of a currently active `FootnoteType` at
    random."""
    with override_current_transaction(Transaction.objects.last()):
        return (
            FootnoteType.objects.current()
            .as_at_today_and_beyond()
            .order_by("?")
            .first()
        )


@pytest.fixture
def measure_type():
    """Returns the latest version of a currently active `MeasureType` at
    random."""
    with override_current_transaction(Transaction.objects.last()):
        return (
            MeasureType.objects.filter(
                measure_component_applicability_code=ApplicabilityCode.PERMITTED,
                measure_explosion_level=MeasureExplosionLevel.TARIC,
            )
            .current()
            .as_at_today_and_beyond()
            .order_by("?")
            .first()
        )


@pytest.fixture
def regulation():
    """Returns the latest version of a currently active `Regulation` at
    random."""
    with override_current_transaction(Transaction.objects.last()):
        return (
            Regulation.objects.current().as_at_today_and_beyond().order_by("?").first()
        )
