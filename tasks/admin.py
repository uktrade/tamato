from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from tasks.models import Category
from tasks.models import ProgressState
from tasks.models import Task
from tasks.models import TaskAssignee
from tasks.models import TaskLog
from tasks.models import TaskTemplate
from tasks.models import TaskWorkflow
from tasks.models import TaskWorkflowTemplate


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


class SubtaskFilter(admin.SimpleListFilter):
    title = "Subtasks"
    parameter_name = "is_subtask"

    def lookups(self, request, model_admin):
        return (
            ("TRUE", "Subtasks"),
            ("FALSE", "Tasks"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "TRUE":
            return queryset.subtasks()
        elif value == "FALSE":
            return queryset.parents()


class TaskAdmin(TaskAdminMixin, admin.ModelAdmin):
    list_display = [
        "id",
        "title",
        "is_subtask",
        "description",
        "category",
        "progress_state",
        "parent_task_id",
        "workbasket_id",
        "creator",
    ]
    search_fields = ["id", "title", "description"]
    list_filter = (
        SubtaskFilter,
        "category",
        "progress_state",
    )

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


class TaskWorkflowTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "description",
        "creator",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class TaskTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "description",
        "taskworkflowtemplate_id",
    )

    @admin.display(description="Task Workflow Template")
    def taskworkflowtemplate_id(self, obj):
        if not obj.taskitemtemplate:
            return "-"
        return self.link_to_task_workflow_template(obj.taskitemtemplate)

    def link_to_task_workflow_template(self, task_item_template):
        workflow_template_pk = task_item_template.workflow_template.pk
        task_workflow_template_url = reverse(
            "admin:tasks_taskworkflowtemplate_change",
            args=(workflow_template_pk,),
        )
        return mark_safe(
            f'<a href="{task_workflow_template_url}">{workflow_template_pk}</a>',
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class TaskWorflowAdmin(admin.ModelAdmin):
    search_fields = ["summary_task__title"]
    list_display = [
        "id",
        "title",
        "description",
        "creator_template",
    ]


admin.site.register(Task, TaskAdmin)

admin.site.register(Category, CategoryAdmin)

admin.site.register(ProgressState, ProgressStateAdmin)

admin.site.register(TaskAssignee, TaskAssigneeAdmin)

admin.site.register(TaskLog, TaskLogAdmin)

admin.site.register(TaskWorkflowTemplate, TaskWorkflowTemplateAdmin)

admin.site.register(TaskTemplate, TaskTemplateAdmin)
admin.site.register(TaskWorkflow, TaskWorflowAdmin)
