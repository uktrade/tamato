# Generated by Django 3.2.18 on 2023-03-28 15:39
import logging

from django.conf import settings
from django.core.paginator import Paginator
from django.db import migrations
from django.db.transaction import atomic

logger = logging.getLogger(__name__)


@atomic
def generate_timestamps(apps, schema_editor):
    TrackedModel = apps.get_model("common", "trackedmodel")
    all_models = TrackedModel.objects.select_related("transaction").all()
    paginator = Paginator(all_models, settings.DATA_MIGRATION_BATCH_SIZE)
    logger.info(
        "Running Tracked Model migration in batches, total batches: %s.",
        paginator.num_pages,
    )
    for page_num in range(1, paginator.num_pages + 1):
        logger.info("Batch number: %s", page_num)
        for tracked_model in paginator.page(page_num).object_list:
            tracked_model.created_at = tracked_model.transaction.created_at
            tracked_model.save()


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0009_tracked_model_timestamp"),
    ]

    operations = [
        migrations.RunPython(
            generate_timestamps,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
