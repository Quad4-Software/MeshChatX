# SPDX-License-Identifier: 0BSD

import tempfile
from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend.integrity_manager import (
    CriticalIntegrityError,
    select_critical_integrity_issues,
)


def test_select_critical_integrity_issues_filters_security_markers():
    issues = [
        "Last integrity snapshot: 2026-01-01",
        "Critical security component integrity compromised: identity",
        "File signature mismatch: stickers/foo.json",
    ]
    critical = select_critical_integrity_issues(issues)
    assert critical == ["Critical security component integrity compromised: identity"]


def test_identity_context_blocks_startup_on_critical_integrity_failure():
    from meshchatx.src.backend.identity_context import IdentityContext

    app = MagicMock()
    app.emergency = False
    app.auto_recover = False
    app.integrity_issues = []
    app.cleanup_rns_state_for_identity = MagicMock()

    identity = MagicMock()
    identity.hash = b"a" * 16
    identity.get_private_key.return_value = b"private-key"

    with tempfile.TemporaryDirectory() as tmp:
        app.storage_dir = tmp
        ctx = IdentityContext(identity, app)
        ctx.integrity_manager.check_integrity = MagicMock(
            return_value=(
                False,
                [
                    "Critical security component integrity compromised: identity",
                ],
            ),
        )

        with pytest.raises(CriticalIntegrityError):
            ctx.setup()


def test_non_critical_integrity_issues_do_not_block_selector():
    issues = ["File signature mismatch: stickers/foo.json"]
    assert select_critical_integrity_issues(issues) == []
