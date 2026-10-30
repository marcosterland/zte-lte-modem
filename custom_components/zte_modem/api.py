"""HTTP client for ZTE goform API."""

from __future__ import annotations

import base64
import logging
from typing import Any

import aiohttp
from aiohttp import ClientError

from .const import GOFORM_CONNECT, GOFORM_DISCONNECT, GOFORM_GET, GOFORM_LOGIN, GOFORM_REBOOT, GOFORM_SET

_LOGGER = logging.getLogger(__name__)

_MODEM_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


class ZteModemAuthError(Exception):
    """Login or session rejected by the modem."""


class ZteModemConnectionError(Exception):
    """Network or HTTP failure talking to the modem."""


class ZteModem:
    """Async client for MF79U-style ZTE goform endpoints."""

    def __init__(self, session: aiohttp.ClientSession, host: str, password: str) -> None:
        self._session = session
        self._host = host.strip()
        self._password = password
        self._base = f"http://{self._host}"

    def _headers(self, *, with_origin: bool = False) -> dict[str, str]:
        h = dict(_MODEM_HEADERS)
        h["Referer"] = f"{self._base}/index.html"
        if with_origin:
            h["Origin"] = self._base
        return h

    @staticmethod
    def _b64_password(password: str) -> str:
        return base64.b64encode(password.encode("utf-8")).decode("utf-8")

    async def login(self) -> None:
        """Authenticate and store stok cookie on the session."""
        url = f"{self._base}{GOFORM_SET}"
        data = {
            "isTest": "false",
            "goformId": GOFORM_LOGIN,
            "password": self._b64_password(self._password),
        }
        try:
            async with self._session.post(
                url, data=data, headers=self._headers(with_origin=True)
            ) as resp:
                resp.raise_for_status()
                body = await resp.json(content_type=None)
        except (ClientError, aiohttp.ClientResponseError) as err:
            raise ZteModemConnectionError(str(err)) from err
        except (ValueError, TypeError) as err:
            raise ZteModemConnectionError("Invalid login response") from err

        if str(body.get("result")) != "0":
            raise ZteModemAuthError("Login failed")
        if not resp.cookies.get("stok"):
            raise ZteModemAuthError("Missing stok cookie")

    async def get(self, fields: list[str] | tuple[str, ...]) -> dict[str, Any]:
        """Read modem fields; relogin once if session looks expired."""
        return await self._get_once(fields, allow_relogin=True)

    async def _get_once(
        self, fields: list[str] | tuple[str, ...], *, allow_relogin: bool
    ) -> dict[str, Any]:
        params = {
            "isTest": "false",
            "cmd": ",".join(fields),
            "multi_data": "1",
        }
        url = f"{self._base}{GOFORM_GET}"
        try:
            async with self._session.get(
                url, params=params, headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except (ClientError, aiohttp.ClientResponseError) as err:
            raise ZteModemConnectionError(str(err)) from err
        except (ValueError, TypeError) as err:
            raise ZteModemConnectionError("Invalid get response") from err

        if not isinstance(data, dict):
            raise ZteModemConnectionError("Unexpected get payload")

        # ponytail: naive session-expired heuristic; upgrade path is parse loginfo field
        if allow_relogin and self._session_expired(data, fields):
            await self.login()
            return await self._get_once(fields, allow_relogin=False)

        return data

    @staticmethod
    def _session_expired(data: dict[str, Any], fields: list[str] | tuple[str, ...]) -> bool:
        if data.get("result") not in (None, "0", 0):
            return True
        for key in fields:
            val = data.get(key)
            if val not in (None, "", "null"):
                return False
        return True

    async def sms(self, limit: int = 20) -> list[dict[str, Any]]:
        """Fetch SMS list with decoded message bodies."""
        params = {
            "isTest": "false",
            "cmd": "sms_data_total",
            "page": "0",
            "data_per_page": str(limit),
            "mem_store": "1",
            "tags": "10",
            "order_by": "order by id desc",
        }
        url = f"{self._base}{GOFORM_GET}"
        try:
            async with self._session.get(
                url, params=params, headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except (ClientError, aiohttp.ClientResponseError) as err:
            raise ZteModemConnectionError(str(err)) from err
        except (ValueError, TypeError) as err:
            raise ZteModemConnectionError("Invalid SMS response") from err

        if not isinstance(data, dict):
            return []

        messages = data.get("messages") or []
        out: list[dict[str, Any]] = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            item = dict(msg)
            content = item.get("content")
            if isinstance(content, str) and content:
                try:
                    item["content"] = bytes.fromhex(content).decode("utf-16-be")
                except (ValueError, UnicodeDecodeError):
                    pass
            out.append(item)
        return out

    async def command(self, goform_id: str) -> None:
        """Send a goform set command (reboot, connect, disconnect)."""
        url = f"{self._base}{GOFORM_SET}"
        data = {"isTest": "false", "goformId": goform_id}
        try:
            async with self._session.post(
                url, data=data, headers=self._headers(with_origin=True)
            ) as resp:
                resp.raise_for_status()
                body = await resp.json(content_type=None)
        except (ClientError, aiohttp.ClientResponseError) as err:
            raise ZteModemConnectionError(str(err)) from err
        except (ValueError, TypeError) as err:
            raise ZteModemConnectionError("Invalid command response") from err

        if str(body.get("result")) != "0":
            raise ZteModemConnectionError(f"Command {goform_id} failed")

    async def reboot(self) -> None:
        await self.command(GOFORM_REBOOT)

    async def connect_network(self) -> None:
        await self.command(GOFORM_CONNECT)

    async def disconnect_network(self) -> None:
        await self.command(GOFORM_DISCONNECT)
