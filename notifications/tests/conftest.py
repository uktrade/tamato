import pytest

from common.tests import factories
from importer.models import ImportBatchStatus
from publishing.models import PackagedWorkBasket


@pytest.fixture()
def goods_report_notification():
    present_email = f"goods_report@email.co.uk"  # /PS-IGNORE
    not_present_email = f"no_goods_report@email.co.uk"  # /PS-IGNORE
    factories.NotifiedUserFactory(
        email=present_email,
        enrol_packaging=False,
        enrol_goods_report=True,
    )
    factories.NotifiedUserFactory(
        email=not_present_email,
    )
    import_batch = factories.ImportBatchFactory.create(
        status=ImportBatchStatus.SUCCEEDED,
        goods_import=True,
        taric_file="goods.xml",
    )

    return (
        factories.GoodsSuccessfulImportNotificationFactory(
            notified_object_pk=import_batch.id,
        ),
        present_email,
        not_present_email,
    )


@pytest.fixture()
def ready_for_packaging_notification(published_envelope_factory):
    present_email = f"packaging@email.co.uk"  # /PS-IGNORE
    not_present_email = f"no_packaging@email.co.uk"  # /PS-IGNORE
    factories.NotifiedUserFactory(
        email=present_email,
    )
    factories.NotifiedUserFactory(
        email=not_present_email,
        enrol_packaging=False,
    )
    packaged_wb = published_envelope_factory()
    return (
        factories.EnvelopeReadyForProcessingNotificationFactory(
            notified_object_pk=packaged_wb.id,
        ),
        present_email,
        not_present_email,
    )


@pytest.fixture()
def successful_publishing_notification(crown_dependencies_envelope_factory):
    present_email = f"publishing@email.co.uk"  # /PS-IGNORE
    not_present_email = f"no_publishing@email.co.uk"  # /PS-IGNORE
    factories.NotifiedUserFactory(
        email=present_email,
        enrol_packaging=False,
        enrol_api_publishing=True,
    )
    factories.NotifiedUserFactory(
        email=not_present_email,
    )
    cde = crown_dependencies_envelope_factory()
    return (
        factories.CrownDependenciesEnvelopeSuccessNotificationFactory(
            notified_object_pk=cde.id,
        ),
        present_email,
        not_present_email,
    )


@pytest.fixture()
def failed_publishing_notification(successful_envelope_factory, settings):
    present_email = f"publishing@email.co.uk"  # /PS-IGNORE
    not_present_email = f"no_publishing@email.co.uk"  # /PS-IGNORE
    factories.NotifiedUserFactory(
        email=present_email,
        enrol_packaging=False,
        enrol_api_publishing=True,
    )
    factories.NotifiedUserFactory(
        email=not_present_email,
    )

    settings.ENABLE_PACKAGING_NOTIFICATIONS = False
    successful_envelope_factory()
    pwb = PackagedWorkBasket.objects.get_unpublished_to_api().last()
    crown_dependencies_envelope = factories.CrownDependenciesEnvelopeFactory(
        packaged_work_basket=pwb,
    )

    crown_dependencies_envelope.publishing_failed()
    return (
        factories.CrownDependenciesEnvelopeFailedNotificationFactory(
            notified_object_pk=crown_dependencies_envelope.id,
        ),
        present_email,
        not_present_email,
    )


@pytest.fixture()
def accepted_packaging_notification(successful_envelope_factory, settings):
    present_email = f"packaging@email.co.uk"  # /PS-IGNORE
    not_present_email = f"no_packaging@email.co.uk"  # /PS-IGNORE
    factories.NotifiedUserFactory(
        email=present_email,
    )
    factories.NotifiedUserFactory(
        email=not_present_email,
        enrol_packaging=False,
    )

    ### disable so it doesn't create it's own notification
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False
    envelope = successful_envelope_factory()
    packaged_wb = PackagedWorkBasket.objects.get(
        envelope=envelope,
    )
    return (
        factories.EnvelopeAcceptedNotificationFactory(
            notified_object_pk=packaged_wb.id,
        ),
        present_email,
        not_present_email,
    )


@pytest.fixture()
def rejected_packaging_notification(failed_envelope_factory, settings):
    present_email = f"packaging@email.co.uk"  # /PS-IGNORE
    not_present_email = f"no_packaging@email.co.uk"  # /PS-IGNORE
    factories.NotifiedUserFactory(
        email=present_email,
    )
    factories.NotifiedUserFactory(
        email=not_present_email,
        enrol_packaging=False,
    )

    ### disable so it doesn't create it's own notification
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False
    envelope = failed_envelope_factory()
    packaged_wb = PackagedWorkBasket.objects.get(
        envelope=envelope,
    )
    return (
        factories.EnvelopeRejectedNotificationFactory(
            notified_object_pk=packaged_wb.id,
        ),
        present_email,
        not_present_email,
    )
