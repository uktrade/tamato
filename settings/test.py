from settings.common import *


ENV = "test"

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

INSTALLED_APPS.append("common.tests")
