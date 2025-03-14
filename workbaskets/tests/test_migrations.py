from random import choice

import factory
import pytest
from django.db.migrations.state import ProjectState

from tasks.models import AssignmentType

pytestmark = pytest.mark.django_db


def create_user_assignments(
    before_migration: ProjectState,
    object_count: int,
) -> list:
    """
    Create and return tasks.models.UserAssignment instances at ProjectState,
    before_migration.

    Each UserAssignment instance is created with newly created unique Task, User
    and WorkBasket instances.
    """

    Task = before_migration.apps.get_model("tasks", "Task")
    User = before_migration.apps.get_model("common", "User")
    UserAssignment = before_migration.apps.get_model("tasks", "UserAssignment")
    WorkBasket = before_migration.apps.get_model("workbaskets", "WorkBasket")

    user_assignments = []
    for _ in range(object_count):
        user = User.objects.create(
            username=factory.Faker("text", max_nb_chars=16),
            email=factory.Faker("email"),
            password=factory.Faker("uuid"),
            is_staff=True,
            is_superuser=True,
        )
        workbasket = WorkBasket.objects.create(
            title=factory.Faker("sentence", nb_words=4),
            author=user,
        )
        task = Task.objects.create(
            title=workbasket.title,
            description=workbasket.reason,
            workbasket=workbasket,
        )
        user_assignments.append(
            UserAssignment.objects.create(
                user=user,
                assigned_by=user,
                assignment_type=choice(AssignmentType.values),
                task=task,
            ),
        )

    return user_assignments


def create_comments(
    before_migration: ProjectState,
    object_count: int,
) -> list:
    """
    Create and return tasks.models.Comment instances at ProjectState,
    before_migration.

    Each Comment instance is created with newly created unique Task, User, and
    WorkBasket instances.
    """

    Comment = before_migration.apps.get_model("tasks", "Comment")
    Task = before_migration.apps.get_model("tasks", "Task")
    User = before_migration.apps.get_model("common", "User")
    WorkBasket = before_migration.apps.get_model("workbaskets", "WorkBasket")

    comments = []
    for _ in range(object_count):
        user = User.objects.create(
            username=factory.Faker("text", max_nb_chars=16),
            email=factory.Faker("email"),
            password=factory.Faker("uuid"),
            is_staff=True,
            is_superuser=True,
        )
        workbasket = WorkBasket.objects.create(
            title=factory.Faker("sentence", nb_words=4),
            author=user,
        )
        task = Task.objects.create(
            title=workbasket.title,
            description=workbasket.reason,
            workbasket=workbasket,
        )
        comments.append(
            Comment.objects.create(
                author=user,
                content=factory.Faker("sentence", nb_words=50),
                task=task,
            ),
        )

    return comments


def assert_user_assignment_to_workbasket_assignment_valid(
    user_assignment,
    workbasket_assignment,
) -> None:
    """
    Validate that the migrated UserAssignment instance has correctly migrated to
    the WorkbasketAssignment instance.

    An AssertError is raised if validation fails.
    """

    assert (
        workbasket_assignment.workbasket_id == user_assignment.task.workbasket_id
        and workbasket_assignment.user_id == user_assignment.user_id
        and workbasket_assignment.assigned_by_id == user_assignment.assigned_by_id
        and workbasket_assignment.assignment_type == user_assignment.assignment_type
        and workbasket_assignment.unassigned_at == user_assignment.unassigned_at
    )


def assert_comment_to_workbasket_comment_valid(
    comment,
    workbasket_comment,
) -> None:
    """
    Validate that the migrated Comment instance has correctly migrated to the
    WorkbasketComment instance.

    An AssertError is raised if validation fails.
    """

    assert (
        workbasket_comment.author_id == comment.author_id
        and str(workbasket_comment.content) == str(comment.content)
        and workbasket_comment.workbasket_id == comment.task.workbasket_id
    )


def test_0011_move_assignments_and_comments_data(migrator):
    """Test the 0011_move_assignments_and_comments_data data migration for
    correct data transfer."""

    OBJECT_COUNT = 5

    before_migration = migrator.apply_initial_migration(
        ("workbaskets", "0010_workbasketcomment_workbasketassignment"),
    )
    user_assignments = create_user_assignments(
        before_migration=before_migration,
        object_count=OBJECT_COUNT,
    )
    comments = create_comments(
        before_migration=before_migration,
        object_count=OBJECT_COUNT,
    )

    # Apply migration and validate.

    after_migration = migrator.apply_tested_migration(
        ("workbaskets", "0011_move_assignments_and_comments_data"),
    )

    # Validate data migration from tasks.models.UserAssignment to
    # workbasket.models.WorkBasketAssignment.
    UserAssignment = after_migration.apps.get_model("tasks", "UserAssignment")
    WorkBasketAssignment = after_migration.apps.get_model(
        "workbaskets",
        "WorkBasketAssignment",
    )
    assert UserAssignment.objects.count() == 0
    assert WorkBasketAssignment.objects.count() == OBJECT_COUNT
    for user_assignment in user_assignments:
        workbasket_assignment = WorkBasketAssignment.objects.get(
            workbasket_id=user_assignment.task.workbasket_id,
        )
        assert_user_assignment_to_workbasket_assignment_valid(
            user_assignment=user_assignment,
            workbasket_assignment=workbasket_assignment,
        )

    # Validate data migration from tasks.model.Comment to
    # workbasket.models.WorkBasketComment.
    Comment = after_migration.apps.get_model("tasks", "Comment")
    WorkBasketComment = after_migration.apps.get_model(
        "workbaskets",
        "WorkBasketComment",
    )
    assert Comment.objects.count() == 0
    assert WorkBasketComment.objects.count() == OBJECT_COUNT
    for comment in comments:
        workbasket_comment = WorkBasketComment.objects.get(
            workbasket_id=comment.task.workbasket_id,
        )
        assert_comment_to_workbasket_comment_valid(
            comment=comment,
            workbasket_comment=workbasket_comment,
        )
