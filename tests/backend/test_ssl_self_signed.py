# SPDX-License-Identifier: 0BSD

from pathlib import Path

from cryptography import x509
from cryptography.hazmat.backends import default_backend

from meshchatx.src.ssl_self_signed import (
    collect_tls_san_entries,
    generate_ssl_certificate,
)


def test_collect_tls_san_entries_includes_loopback():
    entries = collect_tls_san_entries()
    dns = {e.value for e in entries if isinstance(e, x509.DNSName)}
    ips = {str(e.value) for e in entries if isinstance(e, x509.IPAddress)}
    assert "localhost" in dns
    assert "127.0.0.1" in ips
    assert "::1" in ips


def test_generate_ssl_certificate_writes_san_loopback(tmp_path: Path):
    cert_path = tmp_path / "cert.pem"
    key_path = tmp_path / "key.pem"
    generate_ssl_certificate(str(cert_path), str(key_path))
    pem = cert_path.read_bytes()
    cert = x509.load_pem_x509_certificate(pem, default_backend())
    san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    dns = set(san.get_values_for_type(x509.DNSName))
    ips = {str(ip) for ip in san.get_values_for_type(x509.IPAddress)}
    assert "localhost" in dns
    assert "127.0.0.1" in ips
    assert "::1" in ips
    assert key_path.read_bytes().startswith(b"-----BEGIN")
