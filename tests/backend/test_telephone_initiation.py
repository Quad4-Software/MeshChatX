import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest
import RNS
from meshchatx.src.backend.telephone_manager import TelephoneManager


@pytest.fixture
def telephone_manager():
    identity = MagicMock(spec=RNS.Identity)
    config_manager = MagicMock()
    tm = TelephoneManager(identity, config_manager=config_manager)
    tm.telephone = MagicMock()
    tm.telephone.busy = False
    return tm


@pytest.mark.asyncio
async def test_initiation_status_updates(telephone_manager):
    statuses = []

    def status_callback(status, target_hash):
        statuses.append((status, target_hash))

    telephone_manager.on_initiation_status_callback = status_callback
    destination_hash = b"\x01" * 32
    destination_hash_hex = destination_hash.hex()

    # Mock RNS.Identity.recall to return an identity immediately
    with patch.object(RNS.Identity, "recall") as mock_recall:
        mock_identity = MagicMock(spec=RNS.Identity)
        mock_recall.return_value = mock_identity

        # Mock Transport to avoid Reticulum internal errors
        with patch.object(RNS.Transport, "has_path", return_value=True):
            with patch.object(RNS.Transport, "request_path"):
                # Mock asyncio.to_thread to return immediately
                with patch("asyncio.to_thread", return_value=None):
                    await telephone_manager.initiate(destination_hash)

    # Check statuses: Resolving -> Dialing -> None
    # Filter out None updates at the end for verification if they happen multiple times
    final_statuses = [s[0] for s in statuses if s[0] is not None]
    assert "Resolving identity..." in final_statuses
    assert "Dialing..." in final_statuses

    # Check that it cleared at the end
    assert telephone_manager.initiation_status is None
    assert statuses[-1] == (None, None)


@pytest.mark.asyncio
async def test_initiation_path_discovery_status(telephone_manager):
    statuses = []

    def status_callback(status, target_hash):
        statuses.append((status, target_hash))

    telephone_manager.on_initiation_status_callback = status_callback
    destination_hash = b"\x02" * 32

    # Mock RNS.Identity.recall to return None first, then an identity
    with patch.object(RNS.Identity, "recall") as mock_recall:
        mock_identity = MagicMock(spec=RNS.Identity)
        mock_recall.side_effect = [None, None, mock_identity]

        with patch.object(RNS.Transport, "has_path", return_value=False):
            with patch.object(RNS.Transport, "request_path") as mock_request_path:
                with patch("asyncio.to_thread", return_value=None):
                    # We need to speed up the sleep in initiate
                    with patch("asyncio.sleep", return_value=None):
                        await telephone_manager.initiate(destination_hash)

                mock_request_path.assert_called_with(destination_hash)

    final_statuses = [s[0] for s in statuses if s[0] is not None]
    assert "Resolving identity..." in final_statuses
    assert "Discovering path/identity..." in final_statuses
    assert "Dialing..." in final_statuses


@pytest.mark.asyncio
async def test_initiation_failure_status(telephone_manager):
    statuses = []

    def status_callback(status, target_hash):
        statuses.append((status, target_hash))

    telephone_manager.on_initiation_status_callback = status_callback
    destination_hash = b"\x03" * 32

    # Mock failure
    with patch.object(RNS.Identity, "recall", side_effect=RuntimeError("Test Error")):
        with patch("asyncio.sleep", return_value=None):
            with pytest.raises(RuntimeError, match="Test Error"):
                await telephone_manager.initiate(destination_hash)

    # Should have a failure status
    failure_statuses = [s[0] for s in statuses if s[0] and s[0].startswith("Failed:")]
    assert len(failure_statuses) > 0
    assert "Failed: Test Error" in failure_statuses[0]

    # Should still clear at the end
    assert telephone_manager.initiation_status is None
