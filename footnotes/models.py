from django.db import models


class Footnote(models.Model):
    description = models.TextField()
