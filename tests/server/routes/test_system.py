"""Tests for system route handlers."""

import json

import aiohttp
import pytest
from aiohttp.test_utils import TestClient


@pytest.mark.asyncio
async def test_socketio_websocket_handshake(client: TestClient) -> None:
    """Device receives Engine.IO OPEN packet and Socket.IO namespace connect."""
    async with client.ws_connect("/socket.io/") as ws:
        # First message: Engine.IO v3 OPEN packet
        open_msg = await ws.receive_str()
        assert open_msg.startswith("0"), (
            f"Expected Engine.IO OPEN packet, got: {open_msg!r}"
        )
        open_data = json.loads(open_msg[1:])
        assert "sid" in open_data
        assert open_data["upgrades"] == []
        assert open_data["pingInterval"] > 0
        assert open_data["pingTimeout"] > 0

        # Second message: Socket.IO v2 connect to default namespace
        connect_msg = await ws.receive_str()
        assert connect_msg == "40", f"Expected Socket.IO CONNECT, got: {connect_msg!r}"

        await ws.close()


@pytest.mark.asyncio
async def test_socketio_pong_accepted(client: TestClient) -> None:
    """Server accepts pong replies without error."""
    async with client.ws_connect("/socket.io/") as ws:
        # Consume handshake packets
        await ws.receive_str()  # OPEN
        await ws.receive_str()  # CONNECT

        # Send a pong — server should not close the connection
        await ws.send_str("3")

        # Connection should still be open (send another pong and check no error)
        await ws.send_str("3")
        assert not ws.closed

        await ws.close()


@pytest.mark.asyncio
async def test_socketio_each_connection_gets_unique_sid(client: TestClient) -> None:
    """Each connection receives a different session ID."""
    async with client.ws_connect("/socket.io/") as ws1:
        open1 = await ws1.receive_str()
        sid1 = json.loads(open1[1:])["sid"]
        await ws1.receive_str()  # consume CONNECT

        async with client.ws_connect("/socket.io/") as ws2:
            open2 = await ws2.receive_str()
            sid2 = json.loads(open2[1:])["sid"]
            await ws2.receive_str()  # consume CONNECT

            assert sid1 != sid2

            await ws2.close()
        await ws1.close()


@pytest.mark.asyncio
async def test_socketio_close_is_clean(client: TestClient) -> None:
    """Client-initiated close does not raise."""
    async with client.ws_connect("/socket.io/") as ws:
        await ws.receive_str()  # OPEN
        await ws.receive_str()  # CONNECT
        await ws.close()
        assert ws.closed


@pytest.mark.asyncio
async def test_health_endpoint(client: TestClient) -> None:
    resp = await client.get("/api/health")
    assert resp.status == aiohttp.web.HTTPOk.status_code
    text = await resp.text()
    assert "Supernote" in text
