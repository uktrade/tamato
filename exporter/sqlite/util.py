import logging
from datetime import datetime
from datetime import timedelta

import boto3
from django.conf import settings

logger = logging.getLogger(__name__)


def sqlite_dumps(
    days_past: int = 30,
    max_objects: int = 100,
) -> list[dict[str, int, datetime]]:
    """
    Return a list of S3 object information for the most recent sqlite dumps from
    S3. Information for each object is held in dictionary format:

        {
            "file_name": str,
            "file_size": int,   # size in bytes, None if value is unavailable.
            "created_datetime": datetime.datetime,
        }

    :param days_past: sets the maximum number of days of object history to
    retrieve.

    :param max_objects: sets the maximum number of objects to retrieve.
    """

    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.SQLITE_S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.SQLITE_S3_SECRET_ACCESS_KEY,
        endpoint_url=settings.SQLITE_S3_ENDPOINT_URL,
    )
    paginator = s3_client.get_paginator("list_objects_v2")
    page_iterator = paginator.paginate(
        Bucket=settings.SQLITE_STORAGE_BUCKET_NAME,
        Prefix=settings.SQLITE_STORAGE_DIRECTORY,
        Delimiter="/",
        PaginationConfig={"PageSize": max_objects},
    )

    start_day = (datetime.today() - timedelta(days=days_past)).strftime("%Y-%m-%d")
    last_modified_filter = f"to_string(LastModified)>='\"{start_day} 00:00:00+00:00\"'"
    filter_string = (
        # GTE filter projection - https://jmespath.org/tutorial.html#filter-projections
        f"Contents[?{last_modified_filter}]"
        # Pipe to reverse builtin - https://jmespath.org/specification.html#reverse
        " | reverse(sort_by(@, &to_string(LastModified)))"
    )

    try:
        results = []
        for obj in page_iterator.search(filter_string):
            file_name = (
                obj["Key"].split("/", 1)[1]
                if "Key" in obj and isinstance(obj["Key"], str)
                else "Unknown"
            )

            try:
                file_size = int(obj["Size"]) if "Size" in obj else None
            except ValueError:
                file_size = None

            created_datetime = (
                obj["LastModified"]
                if "LastModified" in obj and isinstance(obj["LastModified"], datetime)
                else None
            )

            results.append(
                {
                    "file_name": file_name,
                    "file_size": file_size,
                    "created_datetime": created_datetime,
                },
            )
        return results
    except Exception as e:
        logging.warn(f"Sqlite S3 query raised exception: {e}")
        return []
