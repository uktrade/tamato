from django.core.management import BaseCommand
from django.core.management.base import CommandError

from importer.models import ImportBatch
from notifications.models import GoodsSuccessfulImportNotification


def send_notifcation(
    import_id: int,
):
    try:
        import_batch = ImportBatch.objects.get(
            pk=import_id,
        )
    except ImportBatch.DoesNotExist:
        raise CommandError(
            f"No ImportBatch instance found with pk={import_id}",
        )

    notification = GoodsSuccessfulImportNotification(
        notified_object_pk=import_batch.id,
    )
    notification.save()
    notification.synchronous_send_emails()


class Command(BaseCommand):
    help = "Send a good report notifcation for a give Id"

    def add_arguments(self, parser):
        parser.add_argument(
            "--import-batch-id",
            help=(
                "The primary key ID of ImportBatch instance for which a report "
                "should be generated."
            ),
            type=int,
        )

    def handle(self, *args, **options):
        send_notifcation(
            import_id=options["import_batch_id"],
        )
