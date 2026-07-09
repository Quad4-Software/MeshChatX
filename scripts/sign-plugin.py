#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from meshchatx.src.backend.plugin_signature import (  # noqa: E402
    SignatureInfo,
    canonical_dir_payload,
    verify_dir_signature,
    verify_wasm_signature,
    verify_zip_signature,
    write_dir_signature,
)
from meshchatx.src.backend.plugin_wasm_bundle import (  # noqa: E402
    append_wasm_signature,
    wasm_payload_without_signature,
)


def _sign_payload(identity: str, payload: bytes) -> bytes:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(payload)
        tmp_path = tmp.name
    rsg_path = tmp_path + ".rsg"
    try:
        rnid = os.environ.get("RNID", "rnid")
        subprocess.run(
            [rnid, "-i", identity, "-s", tmp_path],
            check=True,
        )
        with open(rsg_path, "rb") as handle:
            return handle.read()
    finally:
        for path in (tmp_path, rsg_path):
            try:
                os.remove(path)
            except OSError:
                pass


def _print_signature(info: SignatureInfo) -> int:
    if not info.present:
        print("unsigned")
        return 0
    if not info.valid:
        if info.error:
            print(f"invalid signature: {info.error}", file=sys.stderr)
        else:
            print("invalid signature", file=sys.stderr)
        return 1
    if info.trusted and info.signer_name:
        print(f"valid signer={info.signer} name={info.signer_name} trusted=yes")
    else:
        print(f"valid signer={info.signer} trusted=no")
    return 0


def cmd_sign(args: argparse.Namespace) -> int:
    if not args.identity:
        raise SystemExit("-identity is required")
    if args.dir:
        payload = canonical_dir_payload(args.dir)
        rsg = _sign_payload(args.identity, payload)
        write_dir_signature(args.dir, rsg)
        return 0
    if args.zip:
        import zipfile

        from meshchatx.src.backend.plugin_signature import canonical_zip_payload

        with zipfile.ZipFile(args.zip) as archive:
            payload = canonical_zip_payload(archive.infolist(), archive)
        rsg = _sign_payload(args.identity, payload)
        tmp_path = args.zip + ".signed"
        with (
            zipfile.ZipFile(args.zip) as reader,
            zipfile.ZipFile(tmp_path, "w") as writer,
        ):
            for info in reader.infolist():
                clean = os.path.normpath(info.filename).replace("\\", "/")
                if os.path.basename(clean) == "meshchatx.plugin.rsg":
                    continue
                writer.writestr(info, reader.read(info.filename))
            writer.writestr("meshchatx.plugin.rsg", rsg)
        os.replace(tmp_path, args.zip)
        return 0
    if args.wasm:
        with open(args.wasm, "rb") as handle:
            wasm = handle.read()
        payload = wasm_payload_without_signature(wasm)
        rsg = _sign_payload(args.identity, payload)
        signed = append_wasm_signature(wasm, rsg)
        out_path = args.output or args.wasm
        with open(out_path, "wb") as handle:
            handle.write(signed)
        return 0
    if args.py:
        with open(args.py, "rb") as handle:
            payload = handle.read()
        rsg = _sign_payload(args.identity, payload)
        with open(args.py + ".rsg", "wb") as handle:
            handle.write(rsg)
        return 0
    raise SystemExit("one of -dir, -zip, -wasm, or -py is required")


def cmd_verify(args: argparse.Namespace) -> int:
    if args.dir:
        return _print_signature(verify_dir_signature(args.dir))
    if args.zip:
        return _print_signature(verify_zip_signature(args.zip))
    if args.wasm:
        with open(args.wasm, "rb") as handle:
            data = handle.read()
        return _print_signature(verify_wasm_signature(data))
    if args.py:
        from meshchatx.src.backend.plugin_signature import verify_py_signature

        return _print_signature(verify_py_signature(args.py))
    raise SystemExit("one of -dir, -zip, -wasm, or -py is required")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sign or verify MeshChatX plugins")
    sub = parser.add_subparsers(dest="command", required=True)

    sign = sub.add_parser("sign")
    sign.add_argument("-identity", required=False)
    sign.add_argument("-dir")
    sign.add_argument("-zip")
    sign.add_argument("-wasm")
    sign.add_argument("-py")
    sign.add_argument("-output")
    sign.set_defaults(func=cmd_sign)

    verify = sub.add_parser("verify")
    verify.add_argument("-dir")
    verify.add_argument("-zip")
    verify.add_argument("-wasm")
    verify.add_argument("-py")
    verify.set_defaults(func=cmd_verify)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
