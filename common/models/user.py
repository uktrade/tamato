from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager
from django.db import models


class UserQuerySet(models.QuerySet):
    def active_tms(self) -> models.QuerySet | list["User"]:
        """Return a QuerySet of active users that may take the tariff manager
        role."""
        return (
            self.filter(
                models.Q(groups__name__in=["Tariff Managers", "Tariff Lead Profile"])
                | models.Q(is_superuser=True),
            )
            .filter(is_active=True)
            .distinct()
            .order_by("first_name", "last_name")
        )


class User(AbstractUser):
    """Custom user model."""

    objects = UserManager.from_queryset(UserQuerySet)()

    current_workbasket = models.ForeignKey(
        "workbaskets.WorkBasket",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    sso_uuid = models.UUIDField(
        unique=True,
        null=True,
        blank=True,
        help_text="This field is populated by the Staff SSO authentication backend override.",
    )

    class Meta:
        db_table = "auth_user"

    def remove_current_workbasket(self):
        """Remove the user's assigned current workbasket."""
        self.current_workbasket = None
        self.save()

    def get_displayname(self):
        """Best effort at getting a useful representation of a User's name for
        general display purposes."""

        return self.get_full_name() or self.email or str(self)
