# SPDX-License-Identifier: 0BSD
"""Properties for diagnostic log redaction: idempotent, secrets never survive."""

from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.log_redaction import redact_diagnostic_text


class TestRedaction:
    @given(text=st.text(max_size=300))
    @settings(max_examples=150, deadline=3000)
    def test_never_raises_and_returns_str(self, text):
        out = redact_diagnostic_text(text)
        assert isinstance(out, str)

    @given(text=st.text(max_size=300))
    @settings(max_examples=150, deadline=3000)
    def test_idempotent(self, text):
        once = redact_diagnostic_text(text)
        assert redact_diagnostic_text(once) == once

    @given(
        key=st.sampled_from(
            ["password", "token", "private_key", "api_key", "authorization", "passwd"]
        ),
        value=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=6, max_size=20
        ),
    )
    @settings(max_examples=80, deadline=3000)
    def test_secret_assignment_value_removed(self, key, value):
        for template in ("{k}={v}", "{k}: {v}", "{k}:{v}"):
            text = template.format(k=key, v=value)
            out = redact_diagnostic_text(text)
            assert value not in out, (text, out)

    def test_ipv4_removed(self):
        out = redact_diagnostic_text("host 203.0.113.44 spoke")
        assert "203.0.113.44" not in out

    def test_full_hex_hash_removed_prefix_kept(self):
        h = "ab" * 32
        out = redact_diagnostic_text(f"dest {h} ok")
        assert h not in out
        short = "ab" * 8
        assert short in redact_diagnostic_text(f"dest {short} ok")

    def test_bearer_and_pem_removed(self):
        assert "abc123xyz" not in redact_diagnostic_text("Bearer abc123xyzTOKEN")
        pem = "-----BEGIN RSA PRIVATE KEY-----\nABC\n-----END RSA PRIVATE KEY-----"
        assert "ABC" not in redact_diagnostic_text(f"pre {pem} post")
