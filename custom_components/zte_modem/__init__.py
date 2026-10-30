"""The ZTE LTE Modem integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

import aiohttp
from aiohttp import CookieJar
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ZteModem, ZteModemAuthError, ZteModemConnectionError
from .const import CONF_HOST, CONF_PASSWORD, DOMAIN, POLL_FIELDS, SMS_LIMIT, UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BUTTON, Platform.SWITCH]

ZteModemDataUpdateCoordinator = DataUpdateCoordinator[dict[str, Any]]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ZTE LTE Modem from a config entry."""
    host = entry.data[CONF_HOST]
    password = entry.data[CONF_PASSWORD]

    jar = CookieJar(unsafe=True)
    connector = aiohttp.TCPConnector(ssl=False)
    session = aiohttp.ClientSession(
        connector=connector,
        cookie_jar=jar,
        trust_env=True,
    )

    api = ZteModem(session, host, password)
    try:
        await api.login()
    except ZteModemAuthError as err:
        await session.close()
        raise ConfigEntryAuthFailed(str(err)) from err
    except ZteModemConnectionError as err:
        await session.close()
        raise ConfigEntryNotReady(str(err)) from err

    async def async_update_data() -> dict[str, Any]:
        try:
            fields = await api.get(POLL_FIELDS)
            messages = await api.sms(SMS_LIMIT)
        except ZteModemAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ZteModemConnectionError as err:
            raise UpdateFailed(str(err)) from err
        return {"fields": fields, "messages": messages}

    coordinator: ZteModemDataUpdateCoordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        update_method=async_update_data,
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = {"api": api, "coordinator": coordinator, "session": session}
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.runtime_data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        runtime = hass.data[DOMAIN].pop(entry.entry_id, None)
        if runtime and (session := runtime.get("session")):
            await session.close()
    return unload_ok
