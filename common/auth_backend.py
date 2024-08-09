from authbroker_client.backends import AuthbrokerBackend

# from common.models import User


class CustomAuthbrokerBackend(AuthbrokerBackend):
    def user_create_mapping(self, profile):
        return {
            "is_active": True,
            "first_name": profile["first_name"],
            "last_name": profile["last_name"],
            "sso_uuid": profile["user_id"],
        }
