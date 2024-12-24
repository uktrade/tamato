import logging
import time

import exporter.report_exporter.exporters as exporters
from common.celery import app

logger = logging.getLogger(__name__)


@app.task
def export_and_upload_quotas_csv(local_path: str = None) -> bool:
    exporters.QuotaReportExporter(local_path).export_csv()


@app.task
def export_and_upload_commodities_csv(local_path: str = None) -> bool:
    logger.info("Starting...")
    start_time = time.time()
    exporters.CommoditiesReportExporter(local_path).export_csv()

    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.info(f"Export completed in {elapsed_time} seconds")


@app.task
def export_and_upload_measure_csv(local_path: str = None) -> bool:
    logger.info("Starting...")
    start_time = time.time()
    exporters.MeasuresReportExporter(local_path).export_csv()

    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.info(f"Export completed in {elapsed_time} seconds")
