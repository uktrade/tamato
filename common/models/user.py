from django.contrib.auth.models import AbstractUser
from django.db import models


class UserQuerySet(models.QuerySet):
    def tariff_managers(self):
        """Filter in active users who belong to one of the Tariff Manager
        profile groups or who are marked as a superuser."""
        return (
            self.filter(
                models.Q(groups__name__in=["Tariff Managers", "Tariff Lead Profile"])
                | models.Q(is_superuser=True),
            )
            .filter(is_active=True)
            .distinct()
        )


class User(AbstractUser):
    """Custom user model."""

    current_workbasket = models.ForeignKey(
        "workbaskets.WorkBasket",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    objects = UserQuerySet.as_manager()

    class Meta:
        db_table = "auth_user"

    def remove_current_workbasket(self):
        """Remove the user's assigned current workbasket."""
        self.current_workbasket = None
        self.save()
