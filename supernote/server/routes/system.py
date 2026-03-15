import asyncio
import json
import logging
import secrets

import aiohttp
from aiohttp import web

from supernote.models.base import BaseResponse
from supernote.models.system import ReferenceInfoVO, ReferenceRespVO

from .decorators import public_route

logger = logging.getLogger(__name__)

routes = web.RouteTableDef()

DEFAULT_PARAMS = {
    "MAX_ERR_COUNTS": "5",  # 5 errors
    "UPLOAD_MAX": "10",  # 10 files
    "FILE_MAX": "2147483648",  # 2GB
    "COPY_MAX": "50",  # 50 files
    "DOWNLOAD_MAX_NUMBER": "20",  # 20 files
    "FILE_TYPE": "note,pdf,mark,png,jpg,jpeg,bmp,gif,epub,txt,doc,docx,ppt,pptx,xls,xlsx,zip,tar.gz,rar",
}


@routes.get("/api/health")
@public_route
async def handle_health(request: web.Request) -> web.Response:
    return web.Response(text="Supernote Private Cloud Server")


@routes.post("/api/official/system/base/param")
@public_route
async def handle_base_param(request: web.Request) -> web.Response:
    # Endpoint: GET /api/official/system/base/param
    # Purpose: Device checks if the server is a valid Supernote Private Cloud instance.
    return web.json_response(
        ReferenceRespVO(
            param_list=[
                ReferenceInfoVO(name=k, value=v) for k, v in DEFAULT_PARAMS.items()
            ]
        ).to_dict()
    )


@routes.get("/api/file/query/server")
@public_route
async def handle_query_server(request: web.Request) -> web.Response:
    # Endpoint: GET /api/file/query/server
    # Purpose: Device checks if the server is a valid Supernote Private Cloud instance.
    return web.json_response(BaseResponse().to_dict())


@routes.get("/socket.io/")
@public_route
async def handle_socketio(request: web.Request) -> web.WebSocketResponse:
    # The device connects via Socket.IO (Engine.IO v3) for push notifications.
    # We don't push anything, but we must accept the connection and maintain
    # ping/pong keepalive — otherwise the device reports sync failure.
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    sid = secrets.token_hex(8)
    ping_interval = 25  # seconds

    # Engine.IO v3 OPEN packet
    open_payload = json.dumps(
        {
            "sid": sid,
            "upgrades": [],
            "pingInterval": ping_interval * 1000,
            "pingTimeout": 5000,
        }
    )
    await ws.send_str(f"0{open_payload}")
    # Socket.IO v2 connect to default namespace
    await ws.send_str("40")

    async def _ping_loop() -> None:
        while not ws.closed:
            await asyncio.sleep(ping_interval)
            try:
                await ws.send_str("2")  # Engine.IO PING
            except Exception:
                break

    ping_task = asyncio.create_task(_ping_loop())
    try:
        async for msg in ws:
            if msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                break
    except Exception as exc:
        logger.debug("socket.io connection error for sid=%s: %s", sid, exc)
    finally:
        ping_task.cancel()
        try:
            await ping_task
        except asyncio.CancelledError:
            pass

    return ws


@routes.get("/api/csrf")
@public_route
async def handle_csrf(request: web.Request) -> web.Response:
    # Endpoint: GET /api/csrf
    token = secrets.token_urlsafe(16)
    resp = web.Response(text="CSRF Token")
    resp.headers["X-XSRF-TOKEN"] = token
    return resp
