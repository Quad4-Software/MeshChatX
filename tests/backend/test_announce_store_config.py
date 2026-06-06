# SPDX-License-Identifier: 0BSD

import pytest


@pytest.mark.asyncio
async def test_update_config_sets_announce_store_flags(mock_app):
    await mock_app.update_config(
        {
            "announce_store_lxmf_delivery": False,
            "announce_store_lxst_telephony": True,
            "announce_store_nomadnetwork_node": False,
            "announce_store_lxmf_propagation": True,
        }
    )
    c = mock_app.config
    assert c.announce_store_lxmf_delivery.get() is False
    assert c.announce_store_lxst_telephony.get() is True
    assert c.announce_store_nomadnetwork_node.get() is False
    assert c.announce_store_lxmf_propagation.get() is True
