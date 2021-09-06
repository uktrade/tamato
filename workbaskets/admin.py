from django.contrib import admin
from workbaskets.models import WorkBasket

class WorkBasketAdmin(admin.ModelAdmin):
    pass
admin.site.register(WorkBasket, WorkBasketAdmin)