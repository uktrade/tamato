from django.db import models


class Report(models.Model):
    class Meta:
        # Define the name for the database table (optional)
        db_table = "report"
