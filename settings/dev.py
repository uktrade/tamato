from settings.common import *

# Enable debugging
DEBUG = True

# Allow all hostnames to access the server
ALLOWED_HOSTS = ["*"]

INTERNAL_IPS = ["127.0.0.1"]

# Enable Django debug toolbar
if is_truthy(os.environ.get("ENABLE_DJANGO_DEBUG_TOOLBAR")):
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    INSTALLED_APPS.extend(["debug_toolbar", "whitenoise.runserver_nostatic"])
    DEBUG_TOOLBAR_PANELS = [
        "debug_toolbar.panels.versions.VersionsPanel",
        "debug_toolbar.panels.timer.TimerPanel",
        "debug_toolbar.panels.settings.SettingsPanel",
        "debug_toolbar.panels.headers.HeadersPanel",
        "debug_toolbar.panels.request.RequestPanel",
        "debug_toolbar.panels.sql.SQLPanel",
        "debug_toolbar.panels.staticfiles.StaticFilesPanel",
        "debug_toolbar.panels.templates.TemplatesPanel",
        "debug_toolbar.panels.cache.CachePanel",
        "debug_toolbar.panels.signals.SignalsPanel",
        "debug_toolbar.panels.logging.LoggingPanel",
        "debug_toolbar.panels.redirects.RedirectsPanel",
    ]

    # Required for using debug in docker
    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": lambda request: True,
    }


CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 1209600

CELERY_TASK_ALWAYS_EAGER = is_truthy(os.environ.get("CELERY_TASK_ALWAYS_EAGER"))

# Set to True if you need to upload documents and you are not running
# the ClamAV service locally.
SKIP_CLAM_AV_FILE_UPLOAD = False

if SKIP_CLAM_AV_FILE_UPLOAD:
    FILE_UPLOAD_HANDLERS = ()
