from django.conf import settings
from django.utils.module_loading import import_string

from publishing.tariff_api.interface import TariffAPIBase
from publishing.tariff_api.interface import TariffAPIStubbed


def get_tariff_api_interface() -> TariffAPIBase:
    """Get the Tariff API interface from the TARIFF_API_INTERFACE setting."""
    if not settings.TARIFF_API_INTERFACE:
        return TariffAPIStubbed()

    interface_class = import_string(settings.TARIFF_API_INTERFACE)
    if not issubclass(interface_class, TariffAPIBase):
        raise ValueError("TARIFF_API_INTERFACE must inherit from TariffAPIBase")

    return interface_class()
