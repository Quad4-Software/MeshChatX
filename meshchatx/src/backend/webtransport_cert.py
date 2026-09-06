# SPDX-License-Identifier: 0BSD
"""Short-lived ECDSA P-256 certificates for experimental WebTransport."""

from __future__ import annotations

import base64
import hashlib
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from meshchatx.src.ssl_self_signed import collect_tls_san_entries

WT_CERT_MAX_DAYS = 10
WT_CERT_FILENAME = "cert.pem"
WT_KEY_FILENAME = "key.pem"


def wt_cert_dir(storage_path: str | os.PathLike[str]) -> Path:
    return Path(storage_path) / "ssl" / "webtransport"


def validate_webtransport_cert_material(
    *,
    public_key,
    not_valid_before: datetime,
    not_valid_after: datetime,
) -> str | None:
    """Return None if valid, else a machine reason string."""
    if not isinstance(public_key, ec.EllipticCurvePublicKey):
        return "not_ecdsa"
    if public_key.curve.name != "secp256r1":
        return "not_p256"
    start = not_valid_before
    end = not_valid_after
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    lifetime = end - start
    if lifetime > timedelta(days=14) or lifetime <= timedelta(0):
        return "invalid_lifetime"
    return None


def generate_webtransport_certificate(
    cert_path: str | os.PathLike[str],
    key_path: str | os.PathLike[str],
    *,
    days: int = WT_CERT_MAX_DAYS,
    force: bool = False,
) -> None:
    """Write a short-lived P-256 self-signed cert suitable for serverCertificateHashes."""
    cert_path = Path(cert_path)
    key_path = Path(key_path)
    if not force and cert_path.is_file() and key_path.is_file():
        if not webtransport_cert_needs_rotation(cert_path):
            return

    days = max(1, min(int(days), 13))
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Reticulum MeshChatX"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ],
    )
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=days))
        .add_extension(
            x509.SubjectAlternativeName(collect_tls_san_entries()),
            critical=False,
        )
        .sign(private_key, hashes.SHA256(), default_backend())
    )
    reason = validate_webtransport_cert_material(
        public_key=cert.public_key(),
        not_valid_before=cert.not_valid_before_utc,
        not_valid_after=cert.not_valid_after_utc,
    )
    if reason is not None:
        raise ValueError(f"generated webtransport cert failed validation: {reason}")

    cert_path.parent.mkdir(parents=True, exist_ok=True)
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(
            key_fd,
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ),
        )
    finally:
        os.close(key_fd)


def load_webtransport_cert(cert_path: str | os.PathLike[str]) -> x509.Certificate:
    data = Path(cert_path).read_bytes()
    return x509.load_pem_x509_certificate(data, default_backend())


def webtransport_cert_needs_rotation(
    cert_path: str | os.PathLike[str],
    *,
    renew_before: timedelta = timedelta(days=1),
) -> bool:
    try:
        cert = load_webtransport_cert(cert_path)
    except Exception:
        return True
    reason = validate_webtransport_cert_material(
        public_key=cert.public_key(),
        not_valid_before=cert.not_valid_before_utc,
        not_valid_after=cert.not_valid_after_utc,
    )
    if reason is not None:
        return True
    return datetime.now(UTC) >= (cert.not_valid_after_utc - renew_before)


def cert_sha256_der_b64(cert: x509.Certificate) -> str:
    der = cert.public_bytes(serialization.Encoding.DER)
    digest = hashlib.sha256(der).digest()
    return base64.b64encode(digest).decode("ascii")


def ensure_webtransport_cert_pair(
    storage_path: str | os.PathLike[str],
) -> tuple[Path, Path, str]:
    """Ensure cert/key exist under storage. Returns (cert, key, sha256_b64)."""
    directory = wt_cert_dir(storage_path)
    cert_path = directory / WT_CERT_FILENAME
    key_path = directory / WT_KEY_FILENAME
    generate_webtransport_certificate(cert_path, key_path)
    cert = load_webtransport_cert(cert_path)
    return cert_path, key_path, cert_sha256_der_b64(cert)
