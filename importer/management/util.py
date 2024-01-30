from django.contrib.auth import get_user_model
from django.core.exceptions import MultipleObjectsReturned
from django.core.exceptions import ObjectDoesNotExist

User = get_user_model()


class ImporterCommandMixin:
    def get_user(self, username):
        """Get the user that corresponds to the username (email)."""
        try:
            user = User.objects.get(email=username)
        except ObjectDoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f'User with email "{username}" not found. Exiting.',
                ),
            )
            exit(1)
        except MultipleObjectsReturned:
            self.stdout.write(
                self.style.ERROR(
                    f'Multiple users found with email "{username}". Exiting.',
                ),
            )
            exit(1)
        return user
