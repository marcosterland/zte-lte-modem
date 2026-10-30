"""Self-check for ZTE modem API client against a fake goform server."""

from __future__ import annotations

import asyncio
import base64
import sys
from pathlib import Path

import aiohttp
from aiohttp import web
from aiohttp.test_utils import TestServer
from aiohttp import CookieJar

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "zte_modem"


def _load_api_module():
    import importlib.util
    import types

    pkg = types.ModuleType("zte_modem")
    pkg.__path__ = [str(COMPONENT)]
    sys.modules["zte_modem"] = pkg

    for name in ("const", "api"):
        path = COMPONENT / f"{name}.py"
        spec = importlib.util.spec_from_file_location(f"zte_modem.{name}", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[f"zte_modem.{name}"] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)
    return sys.modules["zte_modem.api"]


api_mod = _load_api_module()
ZteModem = api_mod.ZteModem

logged_in = False
get_calls = 0


async def handle_set(request: web.Request) -> web.Response:
    global logged_in
    data = await request.post()
    if data.get("goformId") == "LOGIN":
        pw = data.get("password")
        if pw != base64.b64encode(b"admin").decode("utf-8"):
            return web.json_response({"result": "1"})
        logged_in = True
        resp = web.json_response({"result": "0"})
        resp.set_cookie("stok", "testtoken")
        return resp
    if data.get("goformId") in ("REBOOT_DEVICE", "CONNECT_NETWORK", "DISCONNECT_NETWORK"):
        if not request.cookies.get("stok"):
            return web.json_response({"result": "1"})
        return web.json_response({"result": "0"})
    return web.json_response({"result": "1"})


async def handle_get(request: web.Request) -> web.Response:
    global get_calls, logged_in
    get_calls += 1
    if not request.cookies.get("stok"):
        return web.json_response({"result": "1"})
    cmd = request.query.get("cmd", "")
    if cmd == "sms_data_total":
        # "Hi" as UTF-16BE hex
        content = "00480069"
        return web.json_response(
            {
                "messages": [
                    {"number": "+1234", "date": "2024-01-01", "content": content, "read": "0"}
                ]
            }
        )
    if get_calls == 1 and cmd.startswith("lte_rsrp"):
        logged_in = False
        return web.json_response({"lte_rsrp": "", "lte_rsrq": ""})
    return web.json_response({"lte_rsrp": "-95", "imei": "123456789012345"})


async def run_checks() -> None:
    global logged_in, get_calls
    app = web.Application()
    app.router.add_post("/goform/goform_set_cmd_process", handle_set)
    app.router.add_get("/goform/goform_get_cmd_process", handle_get)

    async with TestServer(app) as server:
        host = server.host
        port = server.port
        jar = CookieJar(unsafe=True)
        async with aiohttp.ClientSession(cookie_jar=jar) as session:
            api = ZteModem(session, f"{host}:{port}", "admin")
            await api.login()
            assert jar.filter_cookies(server.make_url("/")).get("stok")

            data = await api.get(["lte_rsrp", "imei"])
            assert data["lte_rsrp"] == "-95"
            assert data["imei"] == "123456789012345"
            assert get_calls >= 2  # relogin path

            messages = await api.sms(5)
            assert messages[0]["content"] == "Hi"

            await api.reboot()


if __name__ == "__main__":
    asyncio.run(run_checks())
    print("check_api: ok")
