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

    class Meta:
        db_table = "auth_user"

    def remove_current_workbasket(self):
        """Remove the user's assigned current workbasket."""
        try:
            self.current_workbasket = None
            self.save()
        except User.DoesNotExist:
            pass
