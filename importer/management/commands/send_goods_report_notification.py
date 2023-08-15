from django.conf import settings
from django.core.management import BaseCommand
from django.core.management.base import CommandError

from importer.models import ImportBatch
from notifications.create_and_send_notification import create_and_send_notificaiton
from notifications.notification_type import GOODS_REPORT


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

    create_and_send_notificaiton(
        template_id=settings.GOODS_REPORT_TEMPLATE_ID,
        email_type=GOODS_REPORT,
        attachment_id=import_batch.id,
        personalisation={
            "tgb_id": import_batch.name,
        },
    )


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
