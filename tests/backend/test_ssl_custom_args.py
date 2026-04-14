"""CLI validation for custom TLS certificate paths."""

import sys
from unittest.mock import patch

import pytest

import meshchatx.meshchat as meshchat_module


def test_ssl_cert_without_key_exits():
    argv = ["meshchat", "--ssl-cert", "/tmp/custom-cert.pem"]
    with patch.object(sys, "argv", argv), pytest.raises(SystemExit) as exc_info:
        meshchat_module.main()
    assert exc_info.value.code == 2


def test_ssl_key_without_cert_exits():
    argv = ["meshchat", "--ssl-key", "/tmp/custom-key.pem"]
    with patch.object(sys, "argv", argv), pytest.raises(SystemExit) as exc_info:
        meshchat_module.main()
    assert exc_info.value.code == 2
