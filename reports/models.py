from django.db import models


class Report(models.Model):
    class Meta:
        db_table = "report"


class EUDataModel(models.Model):
    goods_code = models.CharField(max_length=255, null=True, blank=True)
    add_code = models.CharField(max_length=255, null=True, blank=True)
    order_no = models.CharField(max_length=255, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    red_ind = models.CharField(max_length=255, null=True, blank=True)
    origin = models.CharField(max_length=255, null=True, blank=True)
    measure_type = models.CharField(max_length=255, null=True, blank=True)
    legal_base = models.CharField(max_length=255, null=True, blank=True)
    duty = models.CharField(max_length=255, null=True, blank=True)
    origin_code = models.CharField(max_length=255, null=True, blank=True)
    meas_type_code = models.CharField(max_length=255, null=True, blank=True)
    goods_nomenclature_exists = models.CharField(max_length=255, null=True, blank=True)
    geographical_area_exists = models.CharField(max_length=255, null=True, blank=True)
    measure_type_exists = models.CharField(max_length=255, null=True, blank=True)
    measure_exists = models.CharField(max_length=255, null=True, blank=True)
