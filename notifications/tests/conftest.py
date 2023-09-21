import pytest

from common.tests import factories
from importer.models import ImportBatchStatus
from publishing.models import PackagedWorkBasket


@pytest.fixture()
def goods_report_notification():
    factories.NotifiedUserFactory(
        email="goods_report@email.co.uk",  # /PS-IGNORE
        enrol_packaging=False,
        enrol_goods_report=True,
    )
    factories.NotifiedUserFactory(
        email="no_goods_report@email.co.uk",  # /PS-IGNORE
    )
    import_batch = factories.ImportBatchFactory.create(
        status=ImportBatchStatus.SUCCEEDED,
        goods_import=True,
        taric_file="goods.xml",
    )

    return factories.GoodsSuccessfulImportNotificationFactory(
        notified_object_pk=import_batch.id,
    )


@pytest.fixture()
def ready_for_packaging_notification(published_envelope_factory):
    factories.NotifiedUserFactory(
        email="packaging@email.co.uk",  # /PS-IGNORE
    )
    factories.NotifiedUserFactory(
        email="no_packaging@email.co.uk",  # /PS-IGNORE
        enrol_packaging=False,
    )
    packaged_wb = published_envelope_factory()
    return factories.EnvelopeReadyForProcessingNotificationFactory(
        notified_object_pk=packaged_wb.id,
    )


@pytest.fixture()
def successful_publishing_notification(crown_dependencies_envelope_factory):
    factories.NotifiedUserFactory(
        email="publishing@email.co.uk",  # /PS-IGNORE
        enrol_packaging=False,
        enrol_api_publishing=True,
    )
    factories.NotifiedUserFactory(
        email="no_publishing@email.co.uk",  # /PS-IGNORE
    )
    cde = crown_dependencies_envelope_factory()
    return factories.CrownDependenciesEnvelopeSuccessNotificationFactory(
        notified_object_pk=cde.id,
    )


@pytest.fixture()
def accepted_packaging_notification(successful_envelope_factory, settings):
    factories.NotifiedUserFactory(
        email="packaging@email.co.uk",  # /PS-IGNORE
    )
    factories.NotifiedUserFactory(
        email="no_packaging@email.co.uk",  # /PS-IGNORE
        enrol_packaging=False,
    )

    ### disable so it doesn't create it's own notification
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False
    packaged_wb = successful_envelope_factory()
    return factories.EnvelopeAcceptedNotificationFactory(
        notified_object_pk=packaged_wb.id,
    )


@pytest.fixture()
def rejected_packaging_notification(published_envelope_factory, settings):
    factories.NotifiedUserFactory(
        email="packaging@email.co.uk",  # /PS-IGNORE
    )
    factories.NotifiedUserFactory(
        email="no_packaging@email.co.uk",  # /PS-IGNORE
        enrol_packaging=False,
    )

    ### disable so it doesn't create it's own notification
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False
    envelope = published_envelope_factory()
    packaged_wb = PackagedWorkBasket.objects.get(
        envelope=envelope,
    )
    packaged_wb.begin_processing()

    factories.LoadingReportFactory.create(packaged_workbasket=packaged_wb)
    packaged_wb.processing_failed()
    packaged_wb.save()
    return factories.EnvelopeRejectedNotificationFactory(
        notified_object_pk=packaged_wb.id,
    )
