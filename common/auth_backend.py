from authbroker_client.backends import AuthbrokerBackend
from django.contrib.auth import get_user_model

UserModel = get_user_model()


class CustomAuthbrokerBackend(AuthbrokerBackend):
    def user_create_mapping(self, profile):
        return {
            "is_active": True,
            "first_name": profile.get("first_name"),
            "last_name": profile.get("last_name"),
            "sso_uuid": profile.get("user_id"),
        }

    def set_sso_uuid(self, user, profile):
        if not user.sso_uuid:
            user.sso_uuid = profile.get("user_id")
            user.save()

    def get_or_create_user(self, profile):
        user = super().get_or_create_user(profile)
        self.set_sso_uuid(user, profile)
        return user
