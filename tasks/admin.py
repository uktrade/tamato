from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from tasks.models import Category
from tasks.models import ProgressState
from tasks.models import Task
from tasks.models import TaskAssignee
from tasks.models import TaskLog


class TaskAdminMixin:
    def link_to_task(self, task: Task):
        task_url = reverse(
            "admin:tasks_task_change",
            args=(task.pk,),
        )
        return mark_safe(
            f'<a href="{task_url}">{task.pk}</a>',
        )

    def link_to_workbasket(self, workbasket):
        workbasket_url = reverse(
            "admin:workbaskets_workbasket_change",
            args=(workbasket.pk,),
        )
        return mark_safe(
            f'<a href="{workbasket_url}">{workbasket.pk}</a>',
        )


class TaskAdmin(TaskAdminMixin, admin.ModelAdmin):
    list_display = [
        "id",
        "title",
        "description",
        "category",
        "progress_state",
        "parent_task_id",
        "workbasket_id",
        "creator",
    ]
    search_fields = ["id", "title", "description"]
    list_filter = ["category", "progress_state"]

    def parent_task_id(self, obj):
        if not obj.parent_task:
            return None
        return self.link_to_task(obj.parent_task)

    def workbasket_id(self, obj):
        if not obj.workbasket:
            return "-"
        return self.link_to_workbasket(obj.workbasket)


class CategoryAdmin(admin.ModelAdmin):
    search_fields = ["name"]


class ProgressStateAdmin(admin.ModelAdmin):
    search_fields = ["name"]


class TaskAssigneeAdmin(TaskAdminMixin, admin.ModelAdmin):
    list_display = ["id", "assignee", "assignment_type", "task_id", "unassigned_at"]
    search_fields = ["user__username", "assignment_type", "task__id"]

    @admin.display(description="User")
    def assignee(self, obj):
        if not obj.user:
            return "Missing user!"
        return obj.user.get_displayname()

    def task_id(self, obj):
        if not obj.task:
            return "Missing task!"
        return self.link_to_task(obj.task)


class TaskLogAdmin(admin.ModelAdmin):
    list_display = ["task", "action", "created_at"]
    list_filter = ["action"]
    readonly_fields = [
        "id",
        "action",
        "description",
        "task",
        "instigator",
        "created_at",
    ]


admin.site.register(Task, TaskAdmin)

admin.site.register(Category, CategoryAdmin)

admin.site.register(ProgressState, ProgressStateAdmin)

admin.site.register(TaskAssignee, TaskAssigneeAdmin)

admin.site.register(TaskLog, TaskLogAdmin)
