# SPDX-License-Identifier: 0BSD
"""Adversarial X-Forwarded-For handling for request_client_ip."""

from types import SimpleNamespace

from meshchatx.src.path_utils import request_client_ip


def req(remote, xff=None):
    headers = {"X-Forwarded-For": xff} if xff is not None else {}
    return SimpleNamespace(headers=headers, remote=remote)


TRUSTED = "10.0.0.0/8"


class TestForwardedForSpoofing:
    def test_attacker_injected_first_entry_not_trusted(self):
        # Appending proxy: attacker sent "XFF: 1.2.3.4", proxy appended
        # the real peer address. The trusted entry is the one the proxy
        # appended (rightmost), not the attacker controlled leftmost.
        r = req("10.0.0.9", "1.2.3.4, 203.0.113.50")
        assert request_client_ip(r, TRUSTED) == "203.0.113.50"

    def test_attacker_cannot_spoof_allowlisted_ip(self):
        r = req("10.0.0.9", "10.1.2.3, 203.0.113.50")
        # Leftmost claims a trusted-network address and must be skipped,
        # not returned as the client.
        assert request_client_ip(r, TRUSTED) != "10.1.2.3"

    def test_single_entry_from_appending_proxy(self):
        r = req("10.0.0.9", "203.0.113.50")
        assert request_client_ip(r, TRUSTED) == "203.0.113.50"

    def test_all_entries_trusted_falls_back_to_remote(self):
        r = req("10.0.0.9", "10.1.1.1, 10.2.2.2")
        assert request_client_ip(r, TRUSTED) == "10.0.0.9"

    def test_garbage_entries_do_not_spoof(self):
        r = req("10.0.0.9", "garbage, not-an-ip, 203.0.113.50")
        assert request_client_ip(r, TRUSTED) == "203.0.113.50"

    def test_empty_xff_ignored(self):
        assert request_client_ip(req("10.0.0.9", ""), TRUSTED) == "10.0.0.9"
        assert request_client_ip(req("10.0.0.9", "   "), TRUSTED) == "10.0.0.9"

    def test_no_trusted_proxies_ignores_xff(self):
        r = req("198.51.100.7", "1.2.3.4")
        assert request_client_ip(r, "") == "198.51.100.7"
        assert request_client_ip(r, None) == "198.51.100.7"

    def test_untrusted_remote_ignores_xff(self):
        r = req("198.51.100.7", "10.1.2.3, 1.2.3.4")
        assert request_client_ip(r, TRUSTED) == "198.51.100.7"

    def test_trusted_chain_walks_past_trusted_hops(self):
        # client -> untrusted CDN -> trusted edge -> app. XFF is
        # [claimed, client, cdn]. The rightmost untrusted entry is the CDN.
        r = req("10.0.0.9", "9.9.9.9, 203.0.113.1, 10.0.0.5, 203.0.113.7")
        assert request_client_ip(r, TRUSTED) == "203.0.113.7"
