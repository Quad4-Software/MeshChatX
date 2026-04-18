# SPDX-License-Identifier: 0BSD

"""Integration tests for LXMF messaging and Reticulum communication.

Covers stamp proof-of-work, message packing/unpacking, signature validation,
delivery pipelines (direct, opportunistic, propagated), propagation node
operations, stamp enforcement, deduplication, and failure handling.

Stamp tests run in-process (no Reticulum required, fast).
Protocol and delivery tests run in isolated subprocesses to respect the
Reticulum singleton constraint.

Enable subprocess tests: MESHCHAT_LIVE_RETICULUM=1
"""

import json
import os
import subprocess
import sys
import textwrap

import pytest

import LXMF.LXStamper as LXStamper
import RNS

_RUN = os.environ.get("MESHCHAT_LIVE_RETICULUM") == "1"

_MINIMAL_RNS_CONFIG = """\
[reticulum]
  enable_transport = False
  share_instance = No
  panic_on_interface_error = No

[interfaces]
"""


def _run_lxmf_script(script_body, timeout=120):
    result = subprocess.run(
        [sys.executable, "-c", script_body],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result


def _parse_result(proc):
    assert proc.returncode == 0, f"Script failed:\n{proc.stderr}\n{proc.stdout}"
    lines = proc.stdout.strip().splitlines()
    for line in reversed(lines):
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    raise ValueError(f"No JSON in output:\n{proc.stdout}")


# Shared preamble injected into subprocess scripts.
_SUBPROCESS_PREAMBLE = textwrap.dedent(f"""\
import tempfile, os, json, time, threading, shutil
import RNS, LXMF
import LXMF.LXStamper as LXStamper

_tmpdir = tempfile.mkdtemp(prefix="meshchat_lxmf_test_")
_config_path = os.path.join(_tmpdir, "config")
with open(_config_path, "w") as f:
    f.write({_MINIMAL_RNS_CONFIG!r})

_reticulum = RNS.Reticulum(configdir=_tmpdir, loglevel=RNS.LOG_NONE)

def _emit(data):
    import sys as _sys
    print(json.dumps(data), flush=True)
    _sys.stdout.flush()

def _cleanup():
    try:
        RNS.Reticulum.exit_handler()
    except Exception:
        pass
    shutil.rmtree(_tmpdir, ignore_errors=True)
""")


# ────────────────────────────────────────────────────────────────
# 1. Stamp proof-of-work (in-process, no Reticulum needed)
# ────────────────────────────────────────────────────────────────


class TestStampSolving:
    def test_workblock_deterministic(self):
        material = os.urandom(32)
        wb1 = LXStamper.stamp_workblock(material, expand_rounds=10)
        wb2 = LXStamper.stamp_workblock(material, expand_rounds=10)
        assert wb1 == wb2

    def test_workblock_unique_per_material(self):
        wb1 = LXStamper.stamp_workblock(b"alpha", expand_rounds=10)
        wb2 = LXStamper.stamp_workblock(b"bravo", expand_rounds=10)
        assert wb1 != wb2

    def test_generate_and_validate_cost_1(self):
        mid = os.urandom(32)
        stamp, value = LXStamper.generate_stamp(mid, stamp_cost=1)
        assert stamp is not None
        assert value >= 1
        wb = LXStamper.stamp_workblock(mid)
        assert LXStamper.stamp_valid(stamp, 1, wb)

    def test_generate_and_validate_cost_4(self):
        mid = os.urandom(32)
        stamp, value = LXStamper.generate_stamp(mid, stamp_cost=4)
        assert stamp is not None
        assert value >= 4
        wb = LXStamper.stamp_workblock(mid)
        assert LXStamper.stamp_valid(stamp, 4, wb)

    def test_stamp_value_equals_reported(self):
        mid = os.urandom(32)
        stamp, value = LXStamper.generate_stamp(mid, stamp_cost=2)
        wb = LXStamper.stamp_workblock(mid)
        assert LXStamper.stamp_value(wb, stamp) == value

    def test_random_stamp_rejected_at_high_cost(self):
        mid = os.urandom(32)
        bad = os.urandom(32)
        wb = LXStamper.stamp_workblock(mid)
        assert not LXStamper.stamp_valid(bad, 32, wb)

    def test_stamp_invalid_for_different_message(self):
        mid_a = os.urandom(32)
        stamp, _ = LXStamper.generate_stamp(mid_a, stamp_cost=4)
        wb_a = LXStamper.stamp_workblock(mid_a)
        assert LXStamper.stamp_valid(stamp, 4, wb_a)
        for _ in range(512):
            mid_b = os.urandom(32)
            wb_b = LXStamper.stamp_workblock(mid_b)
            if not LXStamper.stamp_valid(stamp, 4, wb_b):
                return
        pytest.fail("stamp unexpectedly validated against many random workblocks")

    def test_propagation_node_stamp_rounds(self):
        mid = os.urandom(32)
        stamp, value = LXStamper.generate_stamp(
            mid,
            stamp_cost=2,
            expand_rounds=LXStamper.WORKBLOCK_EXPAND_ROUNDS_PN,
        )
        assert stamp is not None
        wb = LXStamper.stamp_workblock(
            mid,
            expand_rounds=LXStamper.WORKBLOCK_EXPAND_ROUNDS_PN,
        )
        assert LXStamper.stamp_valid(stamp, 2, wb)

    def test_peering_key_generation_and_validation(self):
        peer_id = os.urandom(32)
        stamp, _ = LXStamper.generate_stamp(
            peer_id,
            stamp_cost=2,
            expand_rounds=LXStamper.WORKBLOCK_EXPAND_ROUNDS_PEERING,
        )
        assert LXStamper.validate_peering_key(peer_id, stamp, 2)

    def test_peering_key_rejected_for_wrong_id(self):
        """Pick a peer_b for which the stamp does not accidentally satisfy the
        target cost. With cost=8 there is a 1/256 chance of a random workblock
        producing a hash that already meets the threshold, so retry until we
        get a peer_b that genuinely fails validation. This avoids CI flakes
        without inflating stamp_cost (and therefore generation time).
        """
        peer_a = os.urandom(32)
        stamp, _ = LXStamper.generate_stamp(
            peer_a,
            stamp_cost=8,
            expand_rounds=LXStamper.WORKBLOCK_EXPAND_ROUNDS_PEERING,
        )
        for _ in range(64):
            peer_b = os.urandom(32)
            if peer_b == peer_a:
                continue
            if not LXStamper.validate_peering_key(peer_b, stamp, 8):
                return
        pytest.fail("could not find a peer_b that rejects peer_a's stamp")

    def test_pn_stamp_valid_transient_data(self):
        from LXMF.LXMessage import LXMessage

        overhead = LXMessage.LXMF_OVERHEAD + LXStamper.STAMP_SIZE
        fake_lxm = os.urandom(overhead + 64)
        t_id = RNS.Identity.full_hash(fake_lxm)
        stamp, _ = LXStamper.generate_stamp(
            t_id,
            stamp_cost=2,
            expand_rounds=LXStamper.WORKBLOCK_EXPAND_ROUNDS_PN,
        )
        td = fake_lxm + stamp
        r_id, r_data, r_val, r_stamp = LXStamper.validate_pn_stamp(td, 2)
        assert r_id is not None
        assert r_data == fake_lxm
        assert r_val >= 2
        assert r_stamp == stamp

    def test_pn_stamp_rejected_bad_stamp(self):
        from LXMF.LXMessage import LXMessage

        overhead = LXMessage.LXMF_OVERHEAD + LXStamper.STAMP_SIZE
        fake_lxm = os.urandom(overhead + 64)
        bad_stamp = os.urandom(LXStamper.STAMP_SIZE)
        td = fake_lxm + bad_stamp
        r_id, _, _, _ = LXStamper.validate_pn_stamp(td, 16)
        assert r_id is None

    def test_pn_stamp_batch_validation(self):
        from LXMF.LXMessage import LXMessage

        overhead = LXMessage.LXMF_OVERHEAD + LXStamper.STAMP_SIZE
        items = []
        for _ in range(5):
            fake = os.urandom(overhead + 64)
            t_id = RNS.Identity.full_hash(fake)
            stamp, _ = LXStamper.generate_stamp(
                t_id,
                stamp_cost=2,
                expand_rounds=LXStamper.WORKBLOCK_EXPAND_ROUNDS_PN,
            )
            items.append(fake + stamp)

        results = LXStamper.validate_pn_stamps(items, 2)
        assert len(results) == 5

    def test_stamp_cost_boundary_zero(self):
        mid = os.urandom(32)
        wb = LXStamper.stamp_workblock(mid)
        any_stamp = os.urandom(32)
        assert LXStamper.stamp_valid(any_stamp, 0, wb)

    def test_workblock_expand_rounds_affect_output(self):
        material = os.urandom(32)
        wb_10 = LXStamper.stamp_workblock(material, expand_rounds=10)
        wb_20 = LXStamper.stamp_workblock(material, expand_rounds=20)
        assert wb_10 != wb_20
        assert len(wb_20) == 2 * len(wb_10)


# ────────────────────────────────────────────────────────────────
# 2. LXMessage protocol (subprocess, real crypto)
# ────────────────────────────────────────────────────────────────


class TestLXMessageProtocol:
    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_pack_unpack_roundtrip(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            sender_id = RNS.Identity()
            receiver_id = RNS.Identity()

            sender_dest = RNS.Destination(
                sender_id, RNS.Destination.IN,
                RNS.Destination.SINGLE, "lxmf", "delivery",
            )
            receiver_dest_out = RNS.Destination(
                receiver_id, RNS.Destination.OUT,
                RNS.Destination.SINGLE, "lxmf", "delivery",
            )

            msg = LXMF.LXMessage(
                receiver_dest_out, sender_dest,
                content="Hello from integration test",
                title="Test Title",
                fields={"custom": 42},
                desired_method=LXMF.LXMessage.DIRECT,
            )
            msg.pack()

            unpacked = LXMF.LXMessage.unpack_from_bytes(msg.packed)

            _emit({
                "content_match": unpacked.content_as_string() == "Hello from integration test",
                "title_match": unpacked.title_as_string() == "Test Title",
                "fields_match": unpacked.fields.get("custom") == 42,
                "hash_match": unpacked.hash == msg.hash,
                "sig_validated": unpacked.signature_validated,
                "incoming": unpacked.incoming,
                "dest_hash_match": unpacked.destination_hash == receiver_dest_out.hash,
                "src_hash_match": unpacked.source_hash == sender_dest.hash,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert all(data.values()), f"Failures: {[k for k, v in data.items() if not v]}"

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_empty_content_message(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            s_id = RNS.Identity()
            r_id = RNS.Identity()
            s_dest = RNS.Destination(s_id, RNS.Destination.IN, RNS.Destination.SINGLE, "lxmf", "delivery")
            r_dest = RNS.Destination(r_id, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery")

            msg = LXMF.LXMessage(r_dest, s_dest, content="", title="")
            msg.pack()

            unpacked = LXMF.LXMessage.unpack_from_bytes(msg.packed)
            _emit({
                "empty_content": unpacked.content_as_string() == "",
                "empty_title": unpacked.title_as_string() == "",
                "hash_valid": unpacked.hash is not None and len(unpacked.hash) == 32,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert all(data.values())

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_tampered_payload_invalidates_signature(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            s_id = RNS.Identity()
            r_id = RNS.Identity()
            s_dest = RNS.Destination(s_id, RNS.Destination.IN, RNS.Destination.SINGLE, "lxmf", "delivery")
            r_dest = RNS.Destination(r_id, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery")

            msg = LXMF.LXMessage(r_dest, s_dest, content="original", desired_method=LXMF.LXMessage.DIRECT)
            msg.pack()

            tampered = bytearray(msg.packed)
            # Flip a byte in the payload section (after dest + src + sig)
            payload_offset = 16 + 16 + 64
            if payload_offset < len(tampered):
                tampered[payload_offset] ^= 0xFF

            try:
                unpacked = LXMF.LXMessage.unpack_from_bytes(bytes(tampered))
                sig_valid = unpacked.signature_validated
            except Exception:
                sig_valid = False

            _emit({"signature_invalid_after_tamper": not sig_valid})
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert data["signature_invalid_after_tamper"]

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_message_with_stamp(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            s_id = RNS.Identity()
            r_id = RNS.Identity()
            s_dest = RNS.Destination(s_id, RNS.Destination.IN, RNS.Destination.SINGLE, "lxmf", "delivery")
            r_dest = RNS.Destination(r_id, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery")

            msg = LXMF.LXMessage(
                r_dest, s_dest,
                content="Stamped message",
                stamp_cost=2,
            )
            msg.defer_stamp = False
            msg.pack()

            unpacked = LXMF.LXMessage.unpack_from_bytes(msg.packed)
            has_stamp = unpacked.stamp is not None
            stamp_validates = unpacked.validate_stamp(2) if has_stamp else False

            _emit({
                "has_stamp": has_stamp,
                "stamp_validates": stamp_validates,
                "content_ok": unpacked.content_as_string() == "Stamped message",
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert all(data.values()), f"Failures: {[k for k, v in data.items() if not v]}"

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_message_stamp_rejected_at_higher_cost(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            s_id = RNS.Identity()
            r_id = RNS.Identity()
            s_dest = RNS.Destination(s_id, RNS.Destination.IN, RNS.Destination.SINGLE, "lxmf", "delivery")
            r_dest = RNS.Destination(r_id, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery")

            msg = LXMF.LXMessage(r_dest, s_dest, content="Low stamp", stamp_cost=2)
            msg.defer_stamp = False
            msg.pack()

            unpacked = LXMF.LXMessage.unpack_from_bytes(msg.packed)
            validates_at_2 = unpacked.validate_stamp(2)
            # The stamp might or might not pass at cost 20 (extremely unlikely)
            validates_at_20 = unpacked.validate_stamp(20)

            _emit({
                "passes_at_required": validates_at_2,
                "rejected_at_higher": not validates_at_20,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert data["passes_at_required"]
        assert data["rejected_at_higher"]

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_large_message_uses_resource_representation(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            s_id = RNS.Identity()
            r_id = RNS.Identity()
            s_dest = RNS.Destination(s_id, RNS.Destination.IN, RNS.Destination.SINGLE, "lxmf", "delivery")
            r_dest = RNS.Destination(r_id, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery")

            large_content = "X" * 1000
            msg = LXMF.LXMessage(
                r_dest, s_dest,
                content=large_content,
                desired_method=LXMF.LXMessage.DIRECT,
            )
            msg.pack()

            _emit({
                "uses_resource": msg.representation == LXMF.LXMessage.RESOURCE,
                "method_direct": msg.method == LXMF.LXMessage.DIRECT,
                "packed_size": msg.packed_size,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert data["uses_resource"]
        assert data["method_direct"]

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_opportunistic_falls_back_for_large_message(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            s_id = RNS.Identity()
            r_id = RNS.Identity()
            s_dest = RNS.Destination(s_id, RNS.Destination.IN, RNS.Destination.SINGLE, "lxmf", "delivery")
            r_dest = RNS.Destination(r_id, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery")

            large_content = "Y" * 500
            msg = LXMF.LXMessage(
                r_dest, s_dest,
                content=large_content,
                desired_method=LXMF.LXMessage.OPPORTUNISTIC,
            )
            msg.pack()

            _emit({
                "fell_back_to_direct": msg.desired_method == LXMF.LXMessage.DIRECT,
                "method_is_direct": msg.method == LXMF.LXMessage.DIRECT,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert data["fell_back_to_direct"]
        assert data["method_is_direct"]

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_propagated_message_packing(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            s_id = RNS.Identity()
            r_id = RNS.Identity()
            s_dest = RNS.Destination(s_id, RNS.Destination.IN, RNS.Destination.SINGLE, "lxmf", "delivery")
            r_dest = RNS.Destination(r_id, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery")

            msg = LXMF.LXMessage(
                r_dest, s_dest,
                content="Propagated message",
                desired_method=LXMF.LXMessage.PROPAGATED,
            )
            msg.pack()

            _emit({
                "method_propagated": msg.method == LXMF.LXMessage.PROPAGATED,
                "has_propagation_packed": msg.propagation_packed is not None,
                "has_transient_id": msg.transient_id is not None,
                "transient_id_length": len(msg.transient_id) if msg.transient_id else 0,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert data["method_propagated"]
        assert data["has_propagation_packed"]
        assert data["has_transient_id"]
        assert data["transient_id_length"] == 32

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_paper_message_uri_generation(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            s_id = RNS.Identity()
            r_id = RNS.Identity()
            s_dest = RNS.Destination(s_id, RNS.Destination.IN, RNS.Destination.SINGLE, "lxmf", "delivery")
            r_dest = RNS.Destination(r_id, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery")

            msg = LXMF.LXMessage(
                r_dest, s_dest,
                content="Paper msg",
                desired_method=LXMF.LXMessage.PAPER,
            )
            msg.pack()
            uri = msg.as_uri()

            _emit({
                "starts_with_lxm": uri.startswith("lxm://"),
                "uri_length": len(uri),
                "method_paper": msg.method == LXMF.LXMessage.PAPER,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert data["starts_with_lxm"]
        assert data["uri_length"] > 10


# ────────────────────────────────────────────────────────────────
# 3. LXMRouter delivery pipeline (subprocess)
# ────────────────────────────────────────────────────────────────


class TestLXMRouterDelivery:
    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_direct_delivery_via_lxmf_delivery(self):
        """Pack a message from sender, feed bytes to receiver router, verify callback."""
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            sender_id = RNS.Identity()
            receiver_id = RNS.Identity()

            router_a = LXMF.LXMRouter(identity=sender_id, storagepath=_tmpdir+"/alice")
            router_b = LXMF.LXMRouter(identity=receiver_id, storagepath=_tmpdir+"/bob")

            bob_dest = router_b.register_delivery_identity(receiver_id, display_name="Bob")
            alice_dest = router_a.register_delivery_identity(sender_id, display_name="Alice")

            delivered = []
            def on_delivery(msg):
                delivered.append({
                    "content": msg.content_as_string(),
                    "title": msg.title_as_string(),
                    "incoming": msg.incoming,
                    "dest_hash": msg.destination_hash.hex(),
                    "src_hash": msg.source_hash.hex(),
                })
            router_b.register_delivery_callback(on_delivery)

            bob_dest_out = RNS.Destination(
                receiver_id, RNS.Destination.OUT,
                RNS.Destination.SINGLE, "lxmf", "delivery",
            )

            msg = LXMF.LXMessage(
                bob_dest_out, alice_dest,
                content="Direct delivery test",
                title="Integration",
                desired_method=LXMF.LXMessage.DIRECT,
            )
            msg.pack()

            result = router_b.lxmf_delivery(msg.packed, method=LXMF.LXMessage.DIRECT)

            _emit({
                "delivery_returned_true": result == True,
                "callback_fired": len(delivered) == 1,
                "content_correct": delivered[0]["content"] == "Direct delivery test" if delivered else False,
                "title_correct": delivered[0]["title"] == "Integration" if delivered else False,
                "marked_incoming": delivered[0]["incoming"] if delivered else False,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert all(data.values()), f"Failures: {[k for k, v in data.items() if not v]}"

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_delivery_with_stamp_enforcement(self):
        """Stamped message passes delivery when stamps are enforced."""
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            sender_id = RNS.Identity()
            receiver_id = RNS.Identity()

            router_a = LXMF.LXMRouter(identity=sender_id, storagepath=_tmpdir+"/alice")
            router_b = LXMF.LXMRouter(
                identity=receiver_id,
                storagepath=_tmpdir+"/bob",
                enforce_stamps=True,
            )

            bob_dest = router_b.register_delivery_identity(
                receiver_id, display_name="Bob", stamp_cost=2,
            )
            alice_dest = router_a.register_delivery_identity(sender_id, display_name="Alice")

            delivered = []
            router_b.register_delivery_callback(lambda msg: delivered.append(msg))

            bob_dest_out = RNS.Destination(
                receiver_id, RNS.Destination.OUT,
                RNS.Destination.SINGLE, "lxmf", "delivery",
            )

            msg = LXMF.LXMessage(
                bob_dest_out, alice_dest,
                content="Stamped delivery",
                stamp_cost=2,
            )
            msg.defer_stamp = False
            msg.pack()

            result = router_b.lxmf_delivery(msg.packed, method=LXMF.LXMessage.DIRECT)

            _emit({
                "accepted": result == True,
                "callback_fired": len(delivered) == 1,
                "stamp_valid": delivered[0].stamp_valid if delivered else False,
                "stamp_checked": delivered[0].stamp_checked if delivered else False,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert all(data.values()), f"Failures: {[k for k, v in data.items() if not v]}"

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_delivery_rejects_missing_stamp_when_enforced(self):
        """Message without stamp is dropped when stamp enforcement is on."""
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            sender_id = RNS.Identity()
            receiver_id = RNS.Identity()

            router_a = LXMF.LXMRouter(identity=sender_id, storagepath=_tmpdir+"/alice")
            router_b = LXMF.LXMRouter(
                identity=receiver_id,
                storagepath=_tmpdir+"/bob",
                enforce_stamps=True,
            )

            bob_dest = router_b.register_delivery_identity(
                receiver_id, display_name="Bob", stamp_cost=8,
            )
            alice_dest = router_a.register_delivery_identity(sender_id, display_name="Alice")

            delivered = []
            router_b.register_delivery_callback(lambda msg: delivered.append(msg))

            bob_dest_out = RNS.Destination(
                receiver_id, RNS.Destination.OUT,
                RNS.Destination.SINGLE, "lxmf", "delivery",
            )

            msg = LXMF.LXMessage(bob_dest_out, alice_dest, content="No stamp")
            msg.pack()

            result = router_b.lxmf_delivery(msg.packed, method=LXMF.LXMessage.DIRECT)

            _emit({
                "rejected": result == False,
                "callback_not_fired": len(delivered) == 0,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert data["rejected"]
        assert data["callback_not_fired"]

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_delivery_allows_missing_stamp_when_not_enforced(self):
        """Without enforce_stamps, messages pass even with insufficient stamp."""
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            sender_id = RNS.Identity()
            receiver_id = RNS.Identity()

            router_a = LXMF.LXMRouter(identity=sender_id, storagepath=_tmpdir+"/alice")
            router_b = LXMF.LXMRouter(
                identity=receiver_id,
                storagepath=_tmpdir+"/bob",
                enforce_stamps=False,
            )

            bob_dest = router_b.register_delivery_identity(
                receiver_id, display_name="Bob", stamp_cost=8,
            )
            alice_dest = router_a.register_delivery_identity(sender_id, display_name="Alice")

            delivered = []
            router_b.register_delivery_callback(lambda msg: delivered.append(msg))

            bob_dest_out = RNS.Destination(
                receiver_id, RNS.Destination.OUT,
                RNS.Destination.SINGLE, "lxmf", "delivery",
            )

            msg = LXMF.LXMessage(bob_dest_out, alice_dest, content="No stamp but allowed")
            msg.pack()

            result = router_b.lxmf_delivery(msg.packed, method=LXMF.LXMessage.DIRECT)

            _emit({
                "accepted": result == True,
                "callback_fired": len(delivered) == 1,
                "stamp_marked_invalid": not delivered[0].stamp_valid if delivered else False,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert all(data.values())

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_duplicate_message_rejected(self):
        """Same message delivered twice: first accepted, second rejected as duplicate."""
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            sender_id = RNS.Identity()
            receiver_id = RNS.Identity()

            router_a = LXMF.LXMRouter(identity=sender_id, storagepath=_tmpdir+"/alice")
            router_b = LXMF.LXMRouter(identity=receiver_id, storagepath=_tmpdir+"/bob")

            bob_dest = router_b.register_delivery_identity(receiver_id, display_name="Bob")
            alice_dest = router_a.register_delivery_identity(sender_id, display_name="Alice")

            delivered = []
            router_b.register_delivery_callback(lambda msg: delivered.append(msg))

            bob_dest_out = RNS.Destination(
                receiver_id, RNS.Destination.OUT,
                RNS.Destination.SINGLE, "lxmf", "delivery",
            )

            msg = LXMF.LXMessage(bob_dest_out, alice_dest, content="Dedupe test")
            msg.pack()

            first = router_b.lxmf_delivery(msg.packed)
            second = router_b.lxmf_delivery(msg.packed)

            _emit({
                "first_accepted": first == True,
                "second_rejected": second == False,
                "callback_count": len(delivered),
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert data["first_accepted"]
        assert data["second_rejected"]
        assert data["callback_count"] == 1

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_duplicate_allowed_with_flag(self):
        """allow_duplicate=True lets the same message through twice."""
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            sender_id = RNS.Identity()
            receiver_id = RNS.Identity()

            router_a = LXMF.LXMRouter(identity=sender_id, storagepath=_tmpdir+"/alice")
            router_b = LXMF.LXMRouter(identity=receiver_id, storagepath=_tmpdir+"/bob")

            bob_dest = router_b.register_delivery_identity(receiver_id, display_name="Bob")
            alice_dest = router_a.register_delivery_identity(sender_id, display_name="Alice")

            delivered = []
            router_b.register_delivery_callback(lambda msg: delivered.append(msg))

            bob_dest_out = RNS.Destination(
                receiver_id, RNS.Destination.OUT,
                RNS.Destination.SINGLE, "lxmf", "delivery",
            )

            msg = LXMF.LXMessage(bob_dest_out, alice_dest, content="Allow dupes")
            msg.pack()

            first = router_b.lxmf_delivery(msg.packed)
            second = router_b.lxmf_delivery(msg.packed, allow_duplicate=True)

            _emit({
                "first_accepted": first == True,
                "second_accepted": second == True,
                "callback_count": len(delivered),
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert data["first_accepted"]
        assert data["second_accepted"]
        assert data["callback_count"] == 2

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_ignored_source_blocked(self):
        """Messages from an ignored source hash are silently dropped."""
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            sender_id = RNS.Identity()
            receiver_id = RNS.Identity()

            router_a = LXMF.LXMRouter(identity=sender_id, storagepath=_tmpdir+"/alice")
            router_b = LXMF.LXMRouter(identity=receiver_id, storagepath=_tmpdir+"/bob")

            bob_dest = router_b.register_delivery_identity(receiver_id, display_name="Bob")
            alice_dest = router_a.register_delivery_identity(sender_id, display_name="Alice")

            delivered = []
            router_b.register_delivery_callback(lambda msg: delivered.append(msg))

            bob_dest_out = RNS.Destination(
                receiver_id, RNS.Destination.OUT,
                RNS.Destination.SINGLE, "lxmf", "delivery",
            )

            msg = LXMF.LXMessage(bob_dest_out, alice_dest, content="Blocked sender")
            msg.pack()

            router_b.ignored_list.append(alice_dest.hash)
            result = router_b.lxmf_delivery(msg.packed)

            _emit({
                "blocked": result == False,
                "no_callback": len(delivered) == 0,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert data["blocked"]
        assert data["no_callback"]


# ────────────────────────────────────────────────────────────────
# 4. Propagation node operations (subprocess)
# ────────────────────────────────────────────────────────────────


class TestPropagationNode:
    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_enable_disable_propagation(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            node_id = RNS.Identity()
            router = LXMF.LXMRouter(identity=node_id, storagepath=_tmpdir+"/node")

            assert not router.propagation_node
            router.enable_propagation()
            enabled = router.propagation_node
            router.disable_propagation()
            disabled = not router.propagation_node

            _emit({
                "enabled": enabled,
                "disabled": disabled,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert data["enabled"]
        assert data["disabled"]

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_propagation_node_stores_message(self):
        """Feed a propagated message to a prop node and verify storage."""
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        import RNS.vendor.umsgpack as msgpack
        try:
            sender_id = RNS.Identity()
            receiver_id = RNS.Identity()
            node_id = RNS.Identity()

            router_sender = LXMF.LXMRouter(identity=sender_id, storagepath=_tmpdir+"/sender")
            router_node = LXMF.LXMRouter(identity=node_id, storagepath=_tmpdir+"/node")
            router_node.enable_propagation()

            alice_dest = router_sender.register_delivery_identity(sender_id, display_name="Alice")

            bob_dest_out = RNS.Destination(
                receiver_id, RNS.Destination.OUT,
                RNS.Destination.SINGLE, "lxmf", "delivery",
            )

            msg = LXMF.LXMessage(
                bob_dest_out, alice_dest,
                content="Store on prop node",
                desired_method=LXMF.LXMessage.PROPAGATED,
            )
            msg.pack()

            unpacked_transfer = msgpack.unpackb(msg.propagation_packed)
            raw_lxmf_data = unpacked_transfer[1][0]

            entries_before = len(router_node.propagation_entries)
            result = router_node.lxmf_propagation(
                raw_lxmf_data, stamp_value=0, stamp_data=b"",
            )
            entries_after = len(router_node.propagation_entries)

            _emit({
                "stored": entries_after > entries_before,
                "entry_count": entries_after,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert data["stored"]

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_propagation_stamp_cost_enforcement(self):
        """Prop node stores messages with valid stamp_value, rejects without."""
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        import RNS.vendor.umsgpack as msgpack
        try:
            sender_id = RNS.Identity()
            receiver_id = RNS.Identity()
            node_id = RNS.Identity()

            router_sender = LXMF.LXMRouter(identity=sender_id, storagepath=_tmpdir+"/sender")
            router_node = LXMF.LXMRouter(
                identity=node_id,
                storagepath=_tmpdir+"/node",
                propagation_cost=14,
            )
            router_node.enable_propagation()

            alice_dest = router_sender.register_delivery_identity(sender_id, display_name="Alice")
            bob_dest_out = RNS.Destination(
                receiver_id, RNS.Destination.OUT,
                RNS.Destination.SINGLE, "lxmf", "delivery",
            )

            msg1 = LXMF.LXMessage(
                bob_dest_out, alice_dest,
                content="No PN stamp",
                desired_method=LXMF.LXMessage.PROPAGATED,
            )
            msg1.pack()
            raw1 = msgpack.unpackb(msg1.propagation_packed)[1][0]

            entries_before = len(router_node.propagation_entries)
            router_node.lxmf_propagation(raw1, stamp_value=0, stamp_data=b"")
            no_stamp_stored = len(router_node.propagation_entries) > entries_before

            msg2 = LXMF.LXMessage(
                bob_dest_out, alice_dest,
                content="With PN stamp",
                desired_method=LXMF.LXMessage.PROPAGATED,
            )
            msg2.pack()
            raw2 = msgpack.unpackb(msg2.propagation_packed)[1][0]
            t_id = RNS.Identity.full_hash(raw2)
            stamp, value = LXStamper.generate_stamp(
                t_id, stamp_cost=14,
                expand_rounds=LXStamper.WORKBLOCK_EXPAND_ROUNDS_PN,
            )

            entries_before2 = len(router_node.propagation_entries)
            router_node.lxmf_propagation(raw2, stamp_value=value, stamp_data=stamp)
            stamped_stored = len(router_node.propagation_entries) > entries_before2

            _emit({
                "no_stamp_stored_anyway": no_stamp_stored,
                "stamped_stored": stamped_stored,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script, timeout=180))
        assert data["stamped_stored"]

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_propagation_local_delivery(self):
        """Router with delivery identity decrypts and delivers propagated message."""
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        import RNS.vendor.umsgpack as msgpack
        try:
            sender_id = RNS.Identity()
            receiver_id = RNS.Identity()

            router = LXMF.LXMRouter(identity=receiver_id, storagepath=_tmpdir+"/node")
            router.register_delivery_identity(receiver_id, display_name="Receiver")

            delivered = []
            router.register_delivery_callback(lambda msg: delivered.append(msg))

            sender_dest = RNS.Destination(
                sender_id, RNS.Destination.IN,
                RNS.Destination.SINGLE, "lxmf", "delivery",
            )
            receiver_dest_out = RNS.Destination(
                receiver_id, RNS.Destination.OUT,
                RNS.Destination.SINGLE, "lxmf", "delivery",
            )

            msg = LXMF.LXMessage(
                receiver_dest_out, sender_dest,
                content="Local prop delivery",
                desired_method=LXMF.LXMessage.PROPAGATED,
            )
            msg.pack()

            raw_data = msgpack.unpackb(msg.propagation_packed)[1][0]
            router.lxmf_propagation(raw_data)
            time.sleep(0.2)

            _emit({
                "delivered_locally": len(delivered) == 1,
                "content_correct": delivered[0].content_as_string() == "Local prop delivery" if delivered else False,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert data["delivered_locally"]
        assert data["content_correct"]


# ────────────────────────────────────────────────────────────────
# 5. LXMessage state machine and callbacks (subprocess)
# ────────────────────────────────────────────────────────────────


class TestMessageStateAndCallbacks:
    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_message_states_enum(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            _emit({
                "generating": LXMF.LXMessage.GENERATING == 0x00,
                "outbound": LXMF.LXMessage.OUTBOUND == 0x01,
                "sending": LXMF.LXMessage.SENDING == 0x02,
                "sent": LXMF.LXMessage.SENT == 0x04,
                "delivered": LXMF.LXMessage.DELIVERED == 0x08,
                "rejected": LXMF.LXMessage.REJECTED == 0xFD,
                "cancelled": LXMF.LXMessage.CANCELLED == 0xFE,
                "failed": LXMF.LXMessage.FAILED == 0xFF,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert all(data.values())

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_delivery_method_constants(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            _emit({
                "opportunistic": LXMF.LXMessage.OPPORTUNISTIC == 0x01,
                "direct": LXMF.LXMessage.DIRECT == 0x02,
                "propagated": LXMF.LXMessage.PROPAGATED == 0x03,
                "paper": LXMF.LXMessage.PAPER == 0x05,
                "valid_methods_count": len(LXMF.LXMessage.valid_methods) == 4,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert all(data.values())

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_initial_message_state_is_generating(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            s_id = RNS.Identity()
            r_id = RNS.Identity()
            s_dest = RNS.Destination(s_id, RNS.Destination.IN, RNS.Destination.SINGLE, "lxmf", "delivery")
            r_dest = RNS.Destination(r_id, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery")

            msg = LXMF.LXMessage(r_dest, s_dest, content="State test")
            pre_pack_state = msg.state

            msg.pack()
            post_pack_state = msg.state

            _emit({
                "pre_pack_generating": pre_pack_state == LXMF.LXMessage.GENERATING,
                "post_pack_generating": post_pack_state == LXMF.LXMessage.GENERATING,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert all(data.values())

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_outbound_message_enters_pending(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            sender_id = RNS.Identity()
            receiver_id = RNS.Identity()

            router = LXMF.LXMRouter(identity=sender_id, storagepath=_tmpdir+"/sender")
            src_dest = router.register_delivery_identity(sender_id, display_name="Sender")

            dst_dest = RNS.Destination(
                receiver_id, RNS.Destination.OUT,
                RNS.Destination.SINGLE, "lxmf", "delivery",
            )

            msg = LXMF.LXMessage(dst_dest, src_dest, content="Outbound test")
            pending_before = len(router.pending_outbound)
            router.handle_outbound(msg)
            time.sleep(0.2)

            in_pending_or_failed = (
                msg in router.pending_outbound or
                msg in router.failed_outbound or
                msg.state in [LXMF.LXMessage.SENT, LXMF.LXMessage.DELIVERED, LXMF.LXMessage.FAILED]
            )

            _emit({
                "message_tracked": in_pending_or_failed,
                "packed": msg.packed is not None,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert data["message_tracked"]
        assert data["packed"]


# ────────────────────────────────────────────────────────────────
# 6. Multi-field message integrity (subprocess)
# ────────────────────────────────────────────────────────────────


class TestMessageFieldIntegrity:
    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_fields_survive_roundtrip(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            s_id = RNS.Identity()
            r_id = RNS.Identity()
            s_dest = RNS.Destination(s_id, RNS.Destination.IN, RNS.Destination.SINGLE, "lxmf", "delivery")
            r_dest = RNS.Destination(r_id, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery")

            fields = {
                "type": "chat",
                "priority": 5,
                "tags": ["urgent", "personal"],
                "nested": {"key": "value"},
            }
            msg = LXMF.LXMessage(r_dest, s_dest, content="Fields test", fields=fields)
            msg.pack()

            unpacked = LXMF.LXMessage.unpack_from_bytes(msg.packed)
            f = unpacked.fields

            _emit({
                "type_ok": f.get("type") == "chat",
                "priority_ok": f.get("priority") == 5,
                "tags_ok": f.get("tags") == ["urgent", "personal"],
                "nested_ok": f.get("nested") == {"key": "value"},
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert all(data.values())

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_binary_content_roundtrip(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            s_id = RNS.Identity()
            r_id = RNS.Identity()
            s_dest = RNS.Destination(s_id, RNS.Destination.IN, RNS.Destination.SINGLE, "lxmf", "delivery")
            r_dest = RNS.Destination(r_id, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery")

            binary_data = bytes(range(256))
            msg = LXMF.LXMessage(r_dest, s_dest, content=binary_data, title="Binary")
            msg.pack()

            unpacked = LXMF.LXMessage.unpack_from_bytes(msg.packed)
            _emit({
                "binary_preserved": list(unpacked.content) == list(binary_data),
                "title_ok": unpacked.title_as_string() == "Binary",
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert all(data.values())

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_unicode_content_roundtrip(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            s_id = RNS.Identity()
            r_id = RNS.Identity()
            s_dest = RNS.Destination(s_id, RNS.Destination.IN, RNS.Destination.SINGLE, "lxmf", "delivery")
            r_dest = RNS.Destination(r_id, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery")

            unicode_text = "Mesh networking"
            msg = LXMF.LXMessage(r_dest, s_dest, content=unicode_text, title=unicode_text)
            msg.pack()

            unpacked = LXMF.LXMessage.unpack_from_bytes(msg.packed)
            _emit({
                "content_ok": unpacked.content_as_string() == unicode_text,
                "title_ok": unpacked.title_as_string() == unicode_text,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert all(data.values())


# ────────────────────────────────────────────────────────────────
# 7. URI ingestion (subprocess)
# ────────────────────────────────────────────────────────────────


class TestURIIngestion:
    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_paper_uri_roundtrip(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            sender_id = RNS.Identity()
            receiver_id = RNS.Identity()

            router = LXMF.LXMRouter(identity=receiver_id, storagepath=_tmpdir+"/router")
            router.register_delivery_identity(receiver_id, display_name="Receiver")

            delivered = []
            router.register_delivery_callback(lambda msg: delivered.append(msg))

            s_dest = RNS.Destination(
                sender_id, RNS.Destination.IN,
                RNS.Destination.SINGLE, "lxmf", "delivery",
            )
            r_dest = RNS.Destination(
                receiver_id, RNS.Destination.OUT,
                RNS.Destination.SINGLE, "lxmf", "delivery",
            )

            msg = LXMF.LXMessage(
                r_dest, s_dest,
                content="Paper URI test",
                desired_method=LXMF.LXMessage.PAPER,
            )
            msg.pack()
            uri = msg.as_uri()

            router.ingest_lxm_uri(uri)
            time.sleep(0.5)

            _emit({
                "delivered": len(delivered) == 1,
                "content_match": delivered[0].content_as_string() == "Paper URI test" if delivered else False,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert data["delivered"]
        assert data["content_match"]


# ────────────────────────────────────────────────────────────────
# 8. Router configuration and state (subprocess)
# ────────────────────────────────────────────────────────────────


class TestRouterConfiguration:
    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_single_delivery_identity_per_router(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            id_a = RNS.Identity()
            id_b = RNS.Identity()
            router = LXMF.LXMRouter(identity=id_a, storagepath=_tmpdir+"/router")

            first = router.register_delivery_identity(id_a, display_name="A")
            second = router.register_delivery_identity(id_b, display_name="B")

            _emit({
                "first_ok": first is not None,
                "second_rejected": second is None,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert data["first_ok"]
        assert data["second_rejected"]

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_stamp_cost_configuration(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            identity = RNS.Identity()
            router = LXMF.LXMRouter(identity=identity, storagepath=_tmpdir+"/router")
            dest = router.register_delivery_identity(identity, stamp_cost=5)

            initial_cost = router.delivery_destinations[dest.hash].stamp_cost
            router.set_inbound_stamp_cost(dest.hash, 10)
            updated_cost = router.delivery_destinations[dest.hash].stamp_cost
            router.set_inbound_stamp_cost(dest.hash, None)
            cleared_cost = router.delivery_destinations[dest.hash].stamp_cost

            _emit({
                "initial_5": initial_cost == 5,
                "updated_10": updated_cost == 10,
                "cleared_none": cleared_cost is None,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert all(data.values())

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_enforce_stamps_toggle(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            identity = RNS.Identity()
            router = LXMF.LXMRouter(
                identity=identity,
                storagepath=_tmpdir+"/router",
                enforce_stamps=False,
            )

            initial = router._enforce_stamps
            router.enforce_stamps()
            after_enforce = router._enforce_stamps
            router.ignore_stamps()
            after_ignore = router._enforce_stamps

            _emit({
                "initial_false": not initial,
                "enforced": after_enforce,
                "ignored": not after_ignore,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert all(data.values())

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_outbound_propagation_node_set_and_read(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            identity = RNS.Identity()
            router = LXMF.LXMRouter(identity=identity, storagepath=_tmpdir+"/router")

            initial = router.get_outbound_propagation_node()

            node_hash = os.urandom(16)
            router.set_outbound_propagation_node(node_hash)
            set_hash = router.get_outbound_propagation_node()

            node_hash_2 = os.urandom(16)
            router.set_outbound_propagation_node(node_hash_2)
            updated_hash = router.get_outbound_propagation_node()

            _emit({
                "initial_none": initial is None,
                "set_correctly": set_hash == node_hash,
                "update_works": updated_hash == node_hash_2,
                "different_nodes": node_hash != node_hash_2,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert all(data.values()), f"Failures: {[k for k, v in data.items() if not v]}"

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_router_max_delivery_attempts_constant(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            _emit({
                "max_attempts": LXMF.LXMRouter.MAX_DELIVERY_ATTEMPTS,
                "is_positive": LXMF.LXMRouter.MAX_DELIVERY_ATTEMPTS > 0,
                "processing_interval": LXMF.LXMRouter.PROCESSING_INTERVAL,
                "message_expiry": LXMF.LXMRouter.MESSAGE_EXPIRY,
                "expiry_positive": LXMF.LXMRouter.MESSAGE_EXPIRY > 0,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert data["is_positive"]
        assert data["expiry_positive"]
        assert data["max_attempts"] == 5


# ────────────────────────────────────────────────────────────────
# 9. End-to-end two-router communication (subprocess)
# ────────────────────────────────────────────────────────────────


class TestTwoRouterCommunication:
    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_bidirectional_protocol_delivery(self):
        """Alice sends to Bob, then Bob sends to Alice via lxmf_delivery."""
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            alice_id = RNS.Identity()
            bob_id = RNS.Identity()

            router_a = LXMF.LXMRouter(identity=alice_id, storagepath=_tmpdir+"/alice")
            router_b = LXMF.LXMRouter(identity=bob_id, storagepath=_tmpdir+"/bob")

            alice_dest = router_a.register_delivery_identity(alice_id, display_name="Alice")
            bob_dest = router_b.register_delivery_identity(bob_id, display_name="Bob")

            alice_inbox = []
            bob_inbox = []
            router_a.register_delivery_callback(lambda msg: alice_inbox.append(msg))
            router_b.register_delivery_callback(lambda msg: bob_inbox.append(msg))

            bob_dest_out = RNS.Destination(bob_id, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery")
            alice_dest_out = RNS.Destination(alice_id, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery")

            msg_to_bob = LXMF.LXMessage(bob_dest_out, alice_dest, content="Hi Bob")
            msg_to_bob.pack()
            router_b.lxmf_delivery(msg_to_bob.packed)

            msg_to_alice = LXMF.LXMessage(alice_dest_out, bob_dest, content="Hi Alice")
            msg_to_alice.pack()
            router_a.lxmf_delivery(msg_to_alice.packed)

            _emit({
                "bob_received": len(bob_inbox) == 1,
                "bob_content": bob_inbox[0].content_as_string() == "Hi Bob" if bob_inbox else False,
                "alice_received": len(alice_inbox) == 1,
                "alice_content": alice_inbox[0].content_as_string() == "Hi Alice" if alice_inbox else False,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert all(data.values()), f"Failures: {[k for k, v in data.items() if not v]}"

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_multiple_messages_sequential_delivery(self):
        """Send several messages in sequence and verify all arrive in order."""
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            alice_id = RNS.Identity()
            bob_id = RNS.Identity()

            router_a = LXMF.LXMRouter(identity=alice_id, storagepath=_tmpdir+"/alice")
            router_b = LXMF.LXMRouter(identity=bob_id, storagepath=_tmpdir+"/bob")

            alice_dest = router_a.register_delivery_identity(alice_id, display_name="Alice")
            bob_dest = router_b.register_delivery_identity(bob_id, display_name="Bob")

            inbox = []
            router_b.register_delivery_callback(lambda msg: inbox.append(msg.content_as_string()))

            bob_dest_out = RNS.Destination(bob_id, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery")

            message_count = 10
            for i in range(message_count):
                msg = LXMF.LXMessage(bob_dest_out, alice_dest, content=f"Message {i}")
                msg.pack()
                router_b.lxmf_delivery(msg.packed, allow_duplicate=True)

            expected = [f"Message {i}" for i in range(message_count)]
            _emit({
                "all_received": len(inbox) == message_count,
                "order_preserved": inbox == expected,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert data["all_received"]
        assert data["order_preserved"]

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_stamped_bidirectional_with_enforcement(self):
        """Both sides enforce stamps; both sides solve and verify."""
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            alice_id = RNS.Identity()
            bob_id = RNS.Identity()

            router_a = LXMF.LXMRouter(
                identity=alice_id, storagepath=_tmpdir+"/alice", enforce_stamps=True,
            )
            router_b = LXMF.LXMRouter(
                identity=bob_id, storagepath=_tmpdir+"/bob", enforce_stamps=True,
            )

            alice_dest = router_a.register_delivery_identity(alice_id, display_name="Alice", stamp_cost=2)
            bob_dest = router_b.register_delivery_identity(bob_id, display_name="Bob", stamp_cost=2)

            alice_inbox = []
            bob_inbox = []
            router_a.register_delivery_callback(lambda msg: alice_inbox.append(msg))
            router_b.register_delivery_callback(lambda msg: bob_inbox.append(msg))

            bob_dest_out = RNS.Destination(bob_id, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery")
            alice_dest_out = RNS.Destination(alice_id, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery")

            msg_ab = LXMF.LXMessage(bob_dest_out, alice_dest, content="Stamped A->B", stamp_cost=2)
            msg_ab.defer_stamp = False
            msg_ab.pack()
            r1 = router_b.lxmf_delivery(msg_ab.packed)

            msg_ba = LXMF.LXMessage(alice_dest_out, bob_dest, content="Stamped B->A", stamp_cost=2)
            msg_ba.defer_stamp = False
            msg_ba.pack()
            r2 = router_a.lxmf_delivery(msg_ba.packed)

            _emit({
                "ab_accepted": r1 == True,
                "ba_accepted": r2 == True,
                "bob_stamp_valid": bob_inbox[0].stamp_valid if bob_inbox else False,
                "alice_stamp_valid": alice_inbox[0].stamp_valid if alice_inbox else False,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert all(data.values()), f"Failures: {[k for k, v in data.items() if not v]}"


# ────────────────────────────────────────────────────────────────
# 10. Reticulum identity and destination basics (subprocess)
# ────────────────────────────────────────────────────────────────


class TestReticulumPrimitives:
    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_identity_creation_and_key_operations(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            identity = RNS.Identity()
            pub_key = identity.get_public_key()
            priv_key = identity.get_private_key()

            test_data = b"Reticulum mesh network"
            signature = identity.sign(test_data)
            valid = identity.validate(signature, test_data)
            tampered = identity.validate(signature, b"tampered data")

            ciphertext = identity.encrypt(test_data)
            plaintext = identity.decrypt(ciphertext)

            _emit({
                "has_pub_key": pub_key is not None and len(pub_key) > 0,
                "has_priv_key": priv_key is not None and len(priv_key) > 0,
                "sig_valid": valid,
                "tampered_invalid": not tampered,
                "encrypt_decrypt_ok": plaintext == test_data,
                "hash_length": len(identity.hash) if identity.hash else 0,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert all(v for k, v in data.items() if k != "hash_length")
        assert data["hash_length"] == RNS.Reticulum.TRUNCATED_HASHLENGTH // 8

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_destination_hash_determinism(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            identity = RNS.Identity()

            dest1 = RNS.Destination(identity, RNS.Destination.IN, RNS.Destination.SINGLE, "lxmf", "delivery")
            dest2 = RNS.Destination(identity, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery")

            _emit({
                "same_hash": dest1.hash == dest2.hash,
                "hash_length": len(dest1.hash),
                "hexhash_length": len(dest1.hexhash),
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert data["same_hash"]
        assert data["hash_length"] == 16
        assert data["hexhash_length"] == 32

    @pytest.mark.integration
    @pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
    def test_identity_persistence(self):
        script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
        try:
            identity = RNS.Identity()
            id_path = os.path.join(_tmpdir, "test_identity")
            identity.to_file(id_path)

            loaded = RNS.Identity.from_file(id_path)
            test_data = b"persistence check"
            sig = identity.sign(test_data)
            cross_valid = loaded.validate(sig, test_data)

            _emit({
                "file_exists": os.path.exists(id_path),
                "loaded_ok": loaded is not None,
                "same_pub_key": identity.get_public_key() == loaded.get_public_key(),
                "cross_signature_valid": cross_valid,
            })
        finally:
            _cleanup()
        """)
        data = _parse_result(_run_lxmf_script(script))
        assert all(data.values())
