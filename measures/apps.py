from common.app_config import CommonConfig


class MeasuresConfig(CommonConfig):
    name = "measures"

    def ready(self):
        from measures import signals  # connect receivers

        return super().ready()
