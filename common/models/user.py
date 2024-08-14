from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model."""

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
        help_text="This field is populated by via our Staff SSO authentication backend override.",
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
