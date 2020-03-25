from settings.common import *


# Enable debugging
DEBUG = True

# Allow all hostnames to access the server
ALLOWED_HOSTS = "*"

# Enable Django debug toolbar
if os.environ.get("ENABLE_DJANGO_DEBUG_TOOLBAR"):
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    INSTALLED_APPS.extend(
        ["debug_toolbar", "requests_toolbar", "elastic_panel",]
    )
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

INTERNAL_IPS = ["127.0.0.1"]

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
