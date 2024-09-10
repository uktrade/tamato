from django.contrib import admin

from tasks.models import TaskCategory
from tasks.models import TaskProgressState


class TaskCategoryAdmin(admin.ModelAdmin):
    ordering = ["name"]
    search_fields = ["name"]


class TaskProgressStateAdmin(admin.ModelAdmin):
    ordering = ["name"]
    search_fields = ["name"]


admin.site.register(TaskCategory, TaskCategoryAdmin)

admin.site.register(TaskProgressState, TaskProgressStateAdmin)
