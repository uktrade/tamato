from django.contrib import admin

from tasks.models import TaskAssignee
from tasks.models import TaskCategory
from tasks.models import TaskProgressState


class TaskCategoryAdmin(admin.ModelAdmin):
    ordering = ["name"]
    search_fields = ["name"]


class TaskProgressStateAdmin(admin.ModelAdmin):
    ordering = ["name"]
    search_fields = ["name"]


class TaskAssigneeAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "assignment_type", "task_title", "unassigned_at"]
    search_fields = ["user", "assignment_type", "task"]

    def task_title(self, obj):
        if not obj.task:
            return "Missing task!"
        return obj.task.title


admin.site.register(TaskCategory, TaskCategoryAdmin)

admin.site.register(TaskProgressState, TaskProgressStateAdmin)

admin.site.register(TaskAssignee, TaskAssigneeAdmin)
