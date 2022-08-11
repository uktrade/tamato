from common.app_config import CommonConfig


class ImporterConfig(CommonConfig):
    name = "importer"

    def ready(self):
        from common.xml import namespaces

        namespaces.register()

        return super().ready()
