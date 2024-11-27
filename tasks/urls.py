from django.urls import include
from django.urls import path

from tasks import views

app_name = "workflow"

task_ui_patterns = [
    # Task urls
    path("", views.TaskListView.as_view(), name="task-ui-list"),
    path("<int:pk>/", views.TaskDetailView.as_view(), name="task-ui-detail"),
    path("create/", views.TaskCreateView.as_view(), name="task-ui-create"),
    path(
        "<int:pk>/confirm-create/",
        views.TaskConfirmCreateView.as_view(),
        name="task-ui-confirm-create",
    ),
    path("<int:pk>/update/", views.TaskUpdateView.as_view(), name="task-ui-update"),
    path(
        "<int:pk>/confirm-update/",
        views.TaskConfirmUpdateView.as_view(),
        name="task-ui-confirm-update",
    ),
    path("<int:pk>/delete/", views.TaskDeleteView.as_view(), name="task-ui-delete"),
    path(
        "<int:pk>/confirm-delete/",
        views.TaskConfirmDeleteView.as_view(),
        name="task-ui-confirm-delete",
    ),
    # Subtask urls
    path(
        "<int:parent_task_pk>/subtasks/create/",
        views.SubTaskCreateView.as_view(),
        name="subtask-ui-create",
    ),
    path(
        "subtasks/<int:pk>/delete",
        views.SubTaskDeleteView.as_view(),
        name="subtask-ui-delete",
    ),
    path(
        "subtasks/<int:pk>/confirm-delete",
        views.SubTaskConfirmDeleteView.as_view(),
        name="subtask-ui-confirm-delete",
    ),
    path(
        "subtasks/<int:pk>/confirm-create/",
        views.SubTaskConfirmCreateView.as_view(),
        name="subtask-ui-confirm-create",
    ),
    path(
        "subtasks/<int:pk>/delete",
        views.SubTaskDeleteView.as_view(),
        name="subtask-ui-delete",
    ),
    path(
        "subtasks/<int:pk>/confirm-delete",
        views.SubTaskConfirmDeleteView.as_view(),
        name="subtask-ui-confirm-delete",
    ),
    path(
        "subtasks/<int:pk>/update/",
        views.SubTaskUpdateView.as_view(),
        name="subtask-ui-update",
    ),
    path(
        "subtasks/confirm-update/<int:pk>/",
        views.SubTaskConfirmUpdateView.as_view(),
        name="subtask-ui-confirm-update",
    ),
]


workflow_ui_patterns = [
    path(
        "<int:pk>/",
        views.TaskWorkflowDetailView.as_view(),
        name="task-workflow-ui-detail",
    ),
    path(
        "create/",
        views.TaskWorkflowCreateView.as_view(),
        name="task-workflow-ui-create",
    ),
    path(
        "<int:pk>/confirm-create/",
        views.TaskWorkflowConfirmCreateView.as_view(),
        name="task-workflow-ui-confirm-create",
    ),
]

workflow_template_ui_patterns = [
    path(
        "<int:pk>/",
        views.TaskWorkflowTemplateDetailView.as_view(),
        name="task-workflow-template-ui-detail",
    ),
    path(
        "create/",
        views.TaskWorkflowTemplateCreateView.as_view(),
        name="task-workflow-template-ui-create",
    ),
    path(
        "<int:pk>/confirm-create/",
        views.TaskWorkflowTemplateConfirmCreateView.as_view(),
        name="task-workflow-template-ui-confirm-create",
    ),
    path(
        "<int:pk>/update/",
        views.TaskWorkflowTemplateUpdateView.as_view(),
        name="task-workflow-template-ui-update",
    ),
    path(
        "<int:pk>/confirm-update/",
        views.TaskWorkflowTemplateConfirmUpdateView.as_view(),
        name="task-workflow-template-ui-confirm-update",
    ),
    path(
        "<int:pk>/delete/",
        views.TaskWorkflowTemplateDeleteView.as_view(),
        name="task-workflow-template-ui-delete",
    ),
    path(
        "<int:pk>/confirm-delete/",
        views.TaskWorkflowTemplateConfirmDeleteView.as_view(),
        name="task-workflow-template-ui-confirm-delete",
    ),
    path(
        "task-templates/<int:pk>/",
        views.TaskTemplateDetailView.as_view(),
        name="task-template-ui-detail",
    ),
    path(
        "<int:workflow_template_pk>/task-templates/create/",
        views.TaskTemplateCreateView.as_view(),
        name="task-template-ui-create",
    ),
    path(
        "task-templates/confirm-create/<int:pk>/",
        views.TaskTemplateConfirmCreateView.as_view(),
        name="task-template-ui-confirm-create",
    ),
    path(
        "task-templates/<int:pk>/update/",
        views.TaskTemplateUpdateView.as_view(),
        name="task-template-ui-update",
    ),
    path(
        "task-templates/confirm-update/<int:pk>/",
        views.TaskTemplateConfirmUpdateView.as_view(),
        name="task-template-ui-confirm-update",
    ),
    path(
        "<int:workflow_template_pk>/task-templates/<int:pk>/delete/",
        views.TaskTemplateDeleteView.as_view(),
        name="task-template-ui-delete",
    ),
    path(
        "<int:workflow_template_pk>/task-templates/<int:pk>/confirm-delete/",
        views.TaskTemplateConfirmDeleteView.as_view(),
        name="task-template-ui-confirm-delete",
    ),
]

urlpatterns = [
    path("tasks/", include(task_ui_patterns)),
    path("workflows/", include(workflow_ui_patterns)),
    path("workflow-templates/", include(workflow_template_ui_patterns)),
]
