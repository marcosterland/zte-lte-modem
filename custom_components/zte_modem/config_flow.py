"""Config flow for ZTE LTE Modem."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from aiohttp import CookieJar
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .api import ZteModem, ZteModemAuthError, ZteModemConnectionError
from .const import CONF_HOST, DEFAULT_HOST, DEFAULT_PASSWORD, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
    }
)


class CannotConnect(HomeAssistantError):
    """Unable to connect to the modem."""


class InvalidAuth(HomeAssistantError):
    """Invalid authentication."""


async def _validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    jar = CookieJar(unsafe=True)
    connector = aiohttp.TCPConnector(ssl=False)
    session = aiohttp.ClientSession(connector=connector, cookie_jar=jar)
    api = ZteModem(session, data[CONF_HOST], data[CONF_PASSWORD])
    try:
        await api.login()
        fields = await api.get(["imei"])
    except ZteModemAuthError as err:
        raise InvalidAuth from err
    except ZteModemConnectionError as err:
        raise CannotConnect from err
    finally:
        await session.close()

    imei = fields.get("imei")
    if not imei:
        raise CannotConnect("Modem did not return IMEI")

    return {"title": f"ZTE LTE Modem ({imei})", "unique_id": str(imei)}


class ZteModemConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ZTE LTE Modem."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await _validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["unique_id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
