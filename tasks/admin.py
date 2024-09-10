from django.contrib import admin

from tasks.models import TaskCategory


class TaskCategoryAdmin(admin.ModelAdmin):
    ordering = ["name"]
    search_fields = ["name"]


admin.site.register(TaskCategory, TaskCategoryAdmin)
