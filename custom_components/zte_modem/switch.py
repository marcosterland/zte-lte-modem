"""Switch platform for ZTE LTE Modem."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PPP_CONNECTED
from .sensor import _device_info
from . import ZteModemDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up switches from a config entry."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator: ZteModemDataUpdateCoordinator = runtime["coordinator"]
    async_add_entities([ZteModemMobileDataSwitch(runtime["api"], coordinator, entry)])


class ZteModemMobileDataSwitch(CoordinatorEntity[ZteModemDataUpdateCoordinator], SwitchEntity):
    """Toggle mobile data connection."""

    _attr_has_entity_name = True
    _attr_translation_key = "mobile_data"

    def __init__(self, api, coordinator: ZteModemDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._api = api
        self._entry = entry
        self._attr_unique_id = f"{entry.unique_id}_mobile_data"
        self._attr_device_info = _device_info(entry, coordinator)

    @property
    def is_on(self) -> bool:
        """Return true if PPP is connected."""
        status = (self.coordinator.data.get("fields") or {}).get("ppp_status")
        return str(status) == PPP_CONNECTED

    async def async_turn_on(self, **kwargs) -> None:
        """Connect mobile data."""
        await self._api.connect_network()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Disconnect mobile data."""
        await self._api.disconnect_network()
        await self.coordinator.async_request_refresh()
