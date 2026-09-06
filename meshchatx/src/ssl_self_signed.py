# SPDX-License-Identifier: 0BSD

"""Self-signed TLS certificate generation for local HTTPS."""

import ipaddress
import os
import socket
from datetime import UTC, datetime, timedelta

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

_SKIP_IPS = {
    ipaddress.ip_address("0.0.0.0"),  # nosec: BAN-B104
    ipaddress.ip_address("255.255.255.255"),
    ipaddress.ip_address("::"),
}


def _dns_name(value: str):
    host = (value or "").strip().rstrip(".").lower()
    if not host or host in {"localhost", "(none)"}:
        return None
    try:
        ipaddress.ip_address(host)
        return None
    except ValueError:
        pass
    if any(ch.isspace() for ch in host) or "*" in host:
        return None
    try:
        return x509.DNSName(host)
    except (ValueError, TypeError):
        return None


def _ip_name(value):
    try:
        if isinstance(value, str):
            text = value.strip()
            if "%" in text:
                text = text.split("%", 1)[0]
            addr = ipaddress.ip_address(text)
        else:
            addr = value
    except ValueError:
        return None
    if addr in _SKIP_IPS or addr.is_unspecified or addr.is_multicast:
        return None
    return x509.IPAddress(addr)


def collect_tls_san_entries():
    """SAN names for loopback, hostname, and local interface addresses."""
    entries = [
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        x509.IPAddress(ipaddress.IPv6Address("::1")),
    ]
    seen = {("dns", "localhost"), ("ip", "127.0.0.1"), ("ip", "::1")}

    def _add(entry):
        if entry is None:
            return
        if isinstance(entry, x509.DNSName):
            key = ("dns", entry.value)
        else:
            key = ("ip", str(entry.value))
        if key in seen:
            return
        seen.add(key)
        entries.append(entry)

    hostnames = []
    for getter in (socket.gethostname, socket.getfqdn):
        try:
            name = getter()
        except OSError:
            name = ""
        if name:
            hostnames.append(name)
            if "." not in name.strip().rstrip("."):
                hostnames.append(f"{name}.local")
    for name in hostnames:
        _add(_dns_name(name))
        _add(_ip_name(name))

    for name in list(hostnames) + ["localhost"]:
        try:
            infos = socket.getaddrinfo(name, None)
        except OSError:
            continue
        for info in infos:
            sockaddr = info[4]
            if not sockaddr:
                continue
            _add(_ip_name(sockaddr[0]))

    return entries


def generate_ssl_certificate(cert_path: str, key_path: str):
    """Generate a self-signed SSL certificate for local HTTPS.

    Args:
        cert_path: Path where the certificate will be saved
        key_path: Path where the private key will be saved

    """
    if os.path.exists(cert_path) and os.path.exists(key_path):
        return

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Local"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Local"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Reticulum MeshChatX"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ],
    )

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC))
        .not_valid_after(datetime.now(UTC) + timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName(collect_tls_san_entries()),
            critical=False,
        )
        .sign(private_key, hashes.SHA256(), default_backend())
    )

    cert_dir = os.path.dirname(cert_path)
    if cert_dir:
        os.makedirs(cert_dir, exist_ok=True)

    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

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
