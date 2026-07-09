# SPDX-License-Identifier: 0BSD

from meshchatx.src.backend.plugin_rsg import SignatureInfo
from meshchatx.src.backend.plugin_security_scan import (
    assess_plugin,
    assess_sideband_script,
)


def test_findings_for_unsigned_network_and_eval(tmp_path):
    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir()
    (plugin_dir / "main.js").write_text(
        "eval('1'); fetch('https://evil.example/x')", encoding="utf-8"
    )
    manifest = {
        "id": "com.example.risky",
        "permissions": {"network": "fetch"},
        "network": {"endpoints": []},
    }
    assessment = assess_plugin(manifest, str(plugin_dir), signature=SignatureInfo())
    ids = {item.id for item in assessment.findings}
    assert "unsigned-network" in ids
    assert "js-eval" in ids
    assert assessment.risk_level in {"medium", "high"}


def test_sideband_findings():
    assessment = assess_sideband_script(
        "demo.py",
        "import subprocess\nimport socket\neval('1')\n",
        SignatureInfo(),
    )
    ids = {item.id for item in assessment.findings}
    assert "sideband-full-access" in ids
    assert "py-eval" in ids
    assert "py-subprocess" in ids
    assert "py-socket" in ids
