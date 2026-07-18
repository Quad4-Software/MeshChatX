# SPDX-License-Identifier: 0BSD
"""Unit tests for diagnostic log redaction."""

from meshchatx.src.backend.log_redaction import REDACTED, redact_diagnostic_text


def test_redact_paths_hashes_email_ip():
    full = "aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899"
    text = f"fail at /tmp/secret/db for {full} user@example.com from 203.0.113.9"
    out = redact_diagnostic_text(text)
    assert "/tmp/" not in out.lower()
    assert full not in out
    assert "user@example.com" not in out
    assert "203.0.113.9" not in out
    assert out.count(REDACTED) >= 3


def test_redact_run_media_and_windows_drives():
    out = redact_diagnostic_text(
        "fail at /run/media/user1/projects/db and D:\\Users\\user1\\AppData\\id",
    )
    assert "/run/media/" not in out.lower()
    assert "D:\\Users" not in out
    assert REDACTED in out


def test_redact_pem_bearer_and_secret_assigns():
    pem = "-----BEGIN PRIVATE KEY-----\nMIIEowIBAAKCAQEA\n-----END PRIVATE KEY-----"
    out = redact_diagnostic_text(
        f"{pem} Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.aaa.bbb "
        "alias_identity_private_key=YWJjZGVm "
        "Authorization: Basic dXNlcjpwYXNz",
    )
    assert "BEGIN PRIVATE KEY" not in out
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in out
    assert "YWJjZGVm" not in out
    assert "dXNlcjpwYXNz" not in out
    assert "Bearer" in out
    assert REDACTED in out


def test_redact_preserves_short_hash():
    short = "aabbccddeeff00112233445566778899"
    out = redact_diagnostic_text(f"peer {short}")
    assert short in out


def test_redact_empty():
    assert redact_diagnostic_text("") == ""
    assert redact_diagnostic_text(None) is None  # type: ignore[arg-type]
