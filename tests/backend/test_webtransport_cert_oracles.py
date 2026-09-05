# SPDX-License-Identifier: 0BSD

"""Oracle tests for experimental WebTransport certificates."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import ec, rsa
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.webtransport_cert import (
    cert_sha256_der_b64,
    ensure_webtransport_cert_pair,
    generate_webtransport_certificate,
    load_webtransport_cert,
    validate_webtransport_cert_material,
)


def test_ensure_pair_is_p256_short_lived(tmp_path: Path):
    cert_path, key_path, sha_b64 = ensure_webtransport_cert_pair(tmp_path)
    assert cert_path.is_file()
    assert key_path.is_file()
    cert = load_webtransport_cert(cert_path)
    reason = validate_webtransport_cert_material(
        public_key=cert.public_key(),
        not_valid_before=cert.not_valid_before_utc,
        not_valid_after=cert.not_valid_after_utc,
    )
    assert reason is None
    assert sha_b64 == cert_sha256_der_b64(cert)
    lifetime = cert.not_valid_after_utc - cert.not_valid_before_utc
    assert lifetime <= timedelta(days=14)
    assert isinstance(cert.public_key(), ec.EllipticCurvePublicKey)


def test_rsa_rejected_by_validator():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(UTC)
    reason = validate_webtransport_cert_material(
        public_key=key.public_key(),
        not_valid_before=now,
        not_valid_after=now + timedelta(days=7),
    )
    assert reason == "not_ecdsa"


@given(days=st.integers(min_value=15, max_value=400))
@settings(max_examples=20, deadline=None)
def test_long_lifetime_rejected(days):
    key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.now(UTC)
    reason = validate_webtransport_cert_material(
        public_key=key.public_key(),
        not_valid_before=now,
        not_valid_after=now + timedelta(days=days),
    )
    assert reason == "invalid_lifetime"


def test_generate_force_rotates(tmp_path: Path):
    cert = tmp_path / "c.pem"
    key = tmp_path / "k.pem"
    generate_webtransport_certificate(cert, key, days=5)
    first = cert_sha256_der_b64(load_webtransport_cert(cert))
    generate_webtransport_certificate(cert, key, days=5, force=True)
    second = cert_sha256_der_b64(load_webtransport_cert(cert))
    assert first != second
