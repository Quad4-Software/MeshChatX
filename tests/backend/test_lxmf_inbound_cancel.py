# SPDX-License-Identifier: 0BSD

"""Inbound LXMF delivery cancel helpers (LXMF 1.1 / RNS 1.4)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from meshchatx.src.backend.meshchat_utils import (
    cancel_inbound_deliveries,
    list_inbound_deliveries,
)


def test_list_inbound_deliveries_empty_without_router():
    assert list_inbound_deliveries(None) == []


def test_list_inbound_deliveries_serializes_active_resources():
    resource = MagicMock()
    resource.hash = bytes.fromhex("ab" * 16)
    resource.get_data_size.return_value = 1024
    resource.get_transfer_size.return_value = 1100
    resource.get_progress.return_value = 0.5
    router = MagicMock()
    router.inbound_resources.return_value = [resource]

    items = list_inbound_deliveries(router)
    assert len(items) == 1
    assert items[0]["hash"] == "ab" * 16
    assert items[0]["size_bytes"] == 1024
    assert items[0]["progress"] == 50.0


def test_cancel_all_inbound_deliveries():
    router = MagicMock()
    router.cancel_all_inbound.return_value = 2
    result = cancel_inbound_deliveries(router)
    assert result["ok"] is True
    assert result["cancelled"] == 2
    router.cancel_all_inbound.assert_called_once_with()


def test_cancel_one_inbound_delivery():
    router = MagicMock()
    router.cancel_inbound.return_value = True
    result = cancel_inbound_deliveries(router, resource_hash="cd" * 16)
    assert result["ok"] is True
    assert result["cancelled"] == 1
    router.cancel_inbound.assert_called_once_with(bytes.fromhex("cd" * 16))


def test_cancel_inbound_rejects_bad_hash():
    router = MagicMock()
    result = cancel_inbound_deliveries(router, resource_hash="not-hex")
    assert result["ok"] is False
    assert result["cancelled"] == 0
    router.cancel_inbound.assert_not_called()


def test_cancel_inbound_unavailable_without_api():
    router = SimpleNamespace()
    result = cancel_inbound_deliveries(router)
    assert result["ok"] is False
    assert "unavailable" in result["error"]
