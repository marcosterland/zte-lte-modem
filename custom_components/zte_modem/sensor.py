"""Sensor platform for ZTE LTE Modem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfDataRate, UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_HOST, DOMAIN
from . import ZteModemDataUpdateCoordinator

SMS_INBOX_KEY = "sms_inbox"


@dataclass(frozen=True, kw_only=True)
class ZteModemSensorEntityDescription(SensorEntityDescription):
    """Describe a ZTE modem sensor backed by a goform field key."""

    field: str | None = None


SENSOR_DESCRIPTIONS: tuple[ZteModemSensorEntityDescription, ...] = (
    ZteModemSensorEntityDescription(
        key="lte_rsrp",
        field="lte_rsrp",
        native_unit_of_measurement="dBm",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZteModemSensorEntityDescription(
        key="lte_rsrq",
        field="lte_rsrq",
        native_unit_of_measurement="dB",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZteModemSensorEntityDescription(
        key="lte_rssi",
        field="lte_rssi",
        native_unit_of_measurement="dBm",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZteModemSensorEntityDescription(
        key="lte_snr",
        field="lte_snr",
        native_unit_of_measurement="dB",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZteModemSensorEntityDescription(
        key="signalbar",
        field="signalbar",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZteModemSensorEntityDescription(key="network_type", field="network_type"),
    ZteModemSensorEntityDescription(key="network_provider", field="network_provider"),
    ZteModemSensorEntityDescription(key="wan_active_band", field="wan_active_band"),
    ZteModemSensorEntityDescription(key="cell_id", field="cell_id"),
    ZteModemSensorEntityDescription(key="lte_pci", field="lte_pci"),
    ZteModemSensorEntityDescription(key="wan_ipaddr", field="wan_ipaddr"),
    ZteModemSensorEntityDescription(key="ppp_status", field="ppp_status"),
    ZteModemSensorEntityDescription(key="simcard_roam", field="simcard_roam"),
    ZteModemSensorEntityDescription(
        key="realtime_rx_thrpt",
        field="realtime_rx_thrpt",
        native_unit_of_measurement=UnitOfDataRate.KILOBITS_PER_SECOND,
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZteModemSensorEntityDescription(
        key="realtime_tx_thrpt",
        field="realtime_tx_thrpt",
        native_unit_of_measurement=UnitOfDataRate.KILOBITS_PER_SECOND,
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZteModemSensorEntityDescription(
        key="monthly_rx_bytes",
        field="monthly_rx_bytes",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    ZteModemSensorEntityDescription(
        key="monthly_tx_bytes",
        field="monthly_tx_bytes",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    ZteModemSensorEntityDescription(
        key="battery_vol_percent",
        field="battery_vol_percent",
        native_unit_of_measurement="%",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ZteModemSensorEntityDescription(
        key="sim_iccid",
        field="sim_iccid",
        entity_registry_enabled_default=False,
    ),
    ZteModemSensorEntityDescription(
        key="imei",
        field="imei",
        entity_registry_enabled_default=False,
    ),
    ZteModemSensorEntityDescription(
        key="hardware_version",
        field="hardware_version",
        entity_registry_enabled_default=False,
    ),
    ZteModemSensorEntityDescription(
        key="wa_inner_version",
        field="wa_inner_version",
        entity_registry_enabled_default=False,
    ),
    ZteModemSensorEntityDescription(key=SMS_INBOX_KEY, field=None),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors from a config entry."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator: ZteModemDataUpdateCoordinator = runtime["coordinator"]
    async_add_entities(
        ZteModemSensor(coordinator, entry, description) for description in SENSOR_DESCRIPTIONS
    )


class ZteModemSensor(CoordinatorEntity[ZteModemDataUpdateCoordinator], SensorEntity):
    """Representation of a ZTE modem sensor."""

    entity_description: ZteModemSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ZteModemDataUpdateCoordinator,
        entry: ConfigEntry,
        description: ZteModemSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_translation_key = description.key
        self._attr_unique_id = f"{entry.unique_id}_{description.key}"
        self._attr_device_info = _device_info(entry, coordinator)

    @property
    def native_value(self) -> str | int | float | None:
        """Return the state of the sensor."""
        if self.entity_description.key == SMS_INBOX_KEY:
            messages = self.coordinator.data.get("messages") or []
            unread = sum(1 for m in messages if str(m.get("read", "1")) == "0")
            return unread

        field = self.entity_description.field
        if not field:
            return None
        raw = (self.coordinator.data.get("fields") or {}).get(field)
        if raw in (None, ""):
            return None
        if self.entity_description.state_class in (
            SensorStateClass.MEASUREMENT,
            SensorStateClass.TOTAL_INCREASING,
        ):
            try:
                return float(raw)
            except (TypeError, ValueError):
                return None
        return str(raw)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return SMS message list for inbox sensor."""
        if self.entity_description.key != SMS_INBOX_KEY:
            return None
        messages = self.coordinator.data.get("messages") or []
        slim = [
            {
                "number": m.get("number"),
                "date": m.get("date"),
                "content": m.get("content"),
                "read": m.get("read"),
            }
            for m in messages[:20]
        ]
        return {"messages": slim}


def _device_info(entry: ConfigEntry, coordinator: ZteModemDataUpdateCoordinator) -> DeviceInfo:
    fields = coordinator.data.get("fields") or {}
    return DeviceInfo(
        identifiers={(DOMAIN, entry.unique_id)},
        name=entry.title,
        manufacturer="ZTE",
        model=fields.get("hardware_version") or "LTE Modem",
        sw_version=fields.get("wa_inner_version"),
        configuration_url=f"http://{entry.data[CONF_HOST]}",
    )
