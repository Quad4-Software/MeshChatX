# SPDX-License-Identifier: 0BSD

"""Security and fuzz tests for meshchatx://map and related lxm.ingest_uri deep links."""

import asyncio
import json
from unittest.mock import MagicMock, patch
from urllib.parse import quote, urlencode

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


def _await_map_ingest(mock_app, uri: str):
    mock_client = MagicMock()
    mock_client.send_str = MagicMock(return_value=asyncio.sleep(0))
    mock_app.message_router.ingest_lxm_uri = MagicMock()

    async def _run():
        with patch(
            "meshchatx.meshchat.AsyncUtils.run_async",
            side_effect=lambda coro: asyncio.create_task(coro),
        ):
            await mock_app.on_websocket_data_received(
                mock_client,
                {"type": "lxm.ingest_uri", "uri": uri},
            )
        await asyncio.sleep(0)

    asyncio.get_event_loop_policy().get_event_loop().run_until_complete(_run())
    return mock_client


@pytest.mark.asyncio
async def test_lxm_ingest_map_uri_success(mock_app):
    mock_client = MagicMock()
    mock_client.send_str = MagicMock(return_value=asyncio.sleep(0))
    mock_app.message_router.ingest_lxm_uri = MagicMock()

    with patch(
        "meshchatx.meshchat.AsyncUtils.run_async",
        side_effect=lambda coro: asyncio.create_task(coro),
    ):
        await mock_app.on_websocket_data_received(
            mock_client,
            {
                "type": "lxm.ingest_uri",
                "uri": "meshchatx://map?lat=12.5&lon=-45&z=7&layers=discovered&label=HQ",
            },
        )
        await asyncio.sleep(0)

    mock_app.message_router.ingest_lxm_uri.assert_not_called()
    mock_client.send_str.assert_called_once()
    payload = json.loads(mock_client.send_str.call_args[0][0])
    assert payload["type"] == "lxm.ingest_uri.result"
    assert payload["status"] == "success"
    assert payload["ingest_type"] == "map_view"
    mq = payload["map_query"]
    assert mq["lat"] == 12.5
    assert mq["lon"] == -45.0
    assert mq["zoom"] == 7
    assert mq["layers"] == "discovered"
    assert mq["label"] == "HQ"


@pytest.mark.asyncio
async def test_lxm_ingest_map_meshchat_alias(mock_app):
    mock_client = MagicMock()
    mock_client.send_str = MagicMock(return_value=asyncio.sleep(0))
    mock_app.message_router.ingest_lxm_uri = MagicMock()

    with patch(
        "meshchatx.meshchat.AsyncUtils.run_async",
        side_effect=lambda coro: asyncio.create_task(coro),
    ):
        await mock_app.on_websocket_data_received(
            mock_client,
            {"type": "lxm.ingest_uri", "uri": "meshchat://map?lat=0&lon=1&z=2"},
        )
        await asyncio.sleep(0)

    payload = json.loads(mock_client.send_str.call_args[0][0])
    assert payload["ingest_type"] == "map_view"
    assert payload["map_query"]["lat"] == 0.0
    assert payload["map_query"]["lon"] == 1.0


@pytest.mark.asyncio
async def test_lxm_ingest_map_zoom_clamped(mock_app):
    mock_client = MagicMock()
    mock_client.send_str = MagicMock(return_value=asyncio.sleep(0))
    mock_app.message_router.ingest_lxm_uri = MagicMock()

    with patch(
        "meshchatx.meshchat.AsyncUtils.run_async",
        side_effect=lambda coro: asyncio.create_task(coro),
    ):
        await mock_app.on_websocket_data_received(
            mock_client,
            {"type": "lxm.ingest_uri", "uri": "meshchatx://map?lat=0&lon=0&z=999"},
        )
        await asyncio.sleep(0)

    payload = json.loads(mock_client.send_str.call_args[0][0])
    assert payload["map_query"]["zoom"] == 22


@pytest.mark.asyncio
async def test_lxm_ingest_map_invalid_lat_lon(mock_app):
    mock_client = MagicMock()
    mock_client.send_str = MagicMock(return_value=asyncio.sleep(0))
    mock_app.message_router.ingest_lxm_uri = MagicMock()

    with patch(
        "meshchatx.meshchat.AsyncUtils.run_async",
        side_effect=lambda coro: asyncio.create_task(coro),
    ):
        await mock_app.on_websocket_data_received(
            mock_client,
            {"type": "lxm.ingest_uri", "uri": "meshchatx://map?lat=x&lon=1&z=3"},
        )
        await asyncio.sleep(0)

    payload = json.loads(mock_client.send_str.call_args[0][0])
    assert payload["status"] == "error"
    assert "map" in payload["message"].lower()
    mock_app.message_router.ingest_lxm_uri.assert_not_called()


@pytest.mark.parametrize(
    "layers,label",
    [
        ("<script>alert(1)</script>", "safe"),
        ("discovered", "<img src=x onerror=alert(1)>"),
        ("javascript:alert(1)", "ping"),
        ("';DROP TABLE map;--", '"><svg/onload=alert(1)>'),
        ("a" * 4000, "b" * 4000),
    ],
)
@pytest.mark.asyncio
async def test_lxm_ingest_map_xss_like_strings_roundtrip_json(
    mock_app,
    layers,
    label,
):
    q = urlencode(
        {"lat": "1", "lon": "2", "z": "4", "layers": layers, "label": label},
        quote_via=quote,
    )
    uri = f"meshchatx://map?{q}"
    mock_client = MagicMock()
    mock_client.send_str = MagicMock(return_value=asyncio.sleep(0))
    mock_app.message_router.ingest_lxm_uri = MagicMock()

    with patch(
        "meshchatx.meshchat.AsyncUtils.run_async",
        side_effect=lambda coro: asyncio.create_task(coro),
    ):
        await mock_app.on_websocket_data_received(
            mock_client,
            {"type": "lxm.ingest_uri", "uri": uri},
        )
        await asyncio.sleep(0)

    raw = mock_client.send_str.call_args[0][0]
    payload = json.loads(raw)
    assert payload["status"] == "success"
    mq = payload["map_query"]
    assert mq["layers"] == layers.strip()
    assert mq["label"] == label.strip()
    json.loads(raw)


@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,
    max_examples=80,
)
@given(
    tail=st.text(min_size=0, max_size=800),
)
def test_meshchatx_map_query_tail_fuzzing(mock_app, tail):
    uri = "meshchatx://map?" + tail
    mock_client = MagicMock()
    mock_client.send_str = MagicMock(return_value=asyncio.sleep(0))
    mock_app.message_router.ingest_lxm_uri = MagicMock()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run():
            with patch(
                "meshchatx.meshchat.AsyncUtils.run_async",
                side_effect=lambda coro: asyncio.create_task(coro),
            ):
                await mock_app.on_websocket_data_received(
                    mock_client,
                    {"type": "lxm.ingest_uri", "uri": uri},
                )
            await asyncio.sleep(0)

        loop.run_until_complete(_run())
    finally:
        loop.close()

    mock_client.send_str.assert_called()
    raw = mock_client.send_str.call_args[0][0]
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return
    assert payload["type"] == "lxm.ingest_uri.result"
    assert payload["status"] in ("success", "error")


@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,
    max_examples=60,
)
@given(
    lat=st.floats(
        min_value=-90.0, max_value=90.0, allow_nan=False, allow_infinity=False
    ),
    lon=st.floats(
        min_value=-180.0, max_value=180.0, allow_nan=False, allow_infinity=False
    ),
    z=st.integers(min_value=-50, max_value=50),
    extra=st.dictionaries(
        keys=st.text(max_size=8), values=st.text(max_size=40), max_size=6
    ),
)
def test_meshchatx_map_numeric_params_fuzzing(mock_app, lat, lon, z, extra):
    q = {"lat": str(lat), "lon": str(lon), "z": str(z)}
    for k, v in extra.items():
        if k and k not in q:
            q[k] = v
    uri = "meshchatx://map?" + urlencode(q, quote_via=quote)
    mock_client = MagicMock()
    mock_client.send_str = MagicMock(return_value=asyncio.sleep(0))
    mock_app.message_router.ingest_lxm_uri = MagicMock()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run():
            with patch(
                "meshchatx.meshchat.AsyncUtils.run_async",
                side_effect=lambda coro: asyncio.create_task(coro),
            ):
                await mock_app.on_websocket_data_received(
                    mock_client,
                    {"type": "lxm.ingest_uri", "uri": uri},
                )
            await asyncio.sleep(0)

        loop.run_until_complete(_run())
    finally:
        loop.close()

    payload = json.loads(mock_client.send_str.call_args[0][0])
    assert payload["type"] == "lxm.ingest_uri.result"
    if payload["status"] == "success":
        mq = payload["map_query"]
        assert isinstance(mq["lat"], float)
        assert isinstance(mq["lon"], float)
        assert isinstance(mq["zoom"], int)
        assert 0 <= mq["zoom"] <= 22


def test_telemetry_pack_location_xss_like_strings_return_none():
    from meshchatx.src.backend.telemetry_utils import Telemeter

    assert Telemeter.pack_location(latitude="<script>", longitude=1.0) is None
    assert Telemeter.pack_location(latitude=1.0, longitude="'; DROP--;") is None
