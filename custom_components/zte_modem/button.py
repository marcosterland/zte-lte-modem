"""Button platform for ZTE LTE Modem."""

from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .sensor import _device_info
from . import ZteModemDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up buttons from a config entry."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator: ZteModemDataUpdateCoordinator = runtime["coordinator"]
    async_add_entities([ZteModemRebootButton(runtime["api"], coordinator, entry)])


class ZteModemRebootButton(ButtonEntity):
    """Reboot the LTE modem."""

    _attr_has_entity_name = True
    _attr_translation_key = "reboot"
    _attr_device_class = ButtonDeviceClass.RESTART

    def __init__(self, api, coordinator: ZteModemDataUpdateCoordinator, entry: ConfigEntry) -> None:
        self._api = api
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.unique_id}_reboot"
        self._attr_device_info = _device_info(entry, coordinator)

    async def async_press(self) -> None:
        """Trigger modem reboot."""
        await self._api.reboot()
        await self._coordinator.async_request_refresh()
