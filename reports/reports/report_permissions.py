from django.db.models import Model


class ReportPermissions(Model):
    class Meta:
        managed = False  # No database table creation or deletion  \
        # operations will be performed for this model.

        default_permissions = ()  # disable "add", "change", "delete"
        # and "view" default permissions

        permissions = (
            ("view_report_index", "View Reports Index"),
            ("view_report", "View Report"),
        )
