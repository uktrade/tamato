from common.celery import app


@app.task
def bulk_create_edit():
    # Add a parameter for a PK or similar. This will be a PK ref to e.g. CreateMeasures table
    pass
