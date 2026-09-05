# SPDX-License-Identifier: 0BSD

"""Load or create the Reticulum identity used at process startup."""

from __future__ import annotations

import base64
import os
from typing import Any

import RNS


def write_identity_private_key(path: str, identity: RNS.Identity) -> None:
    """Persist an identity private key to path (binary)."""
    with open(path, "wb") as handle:
        handle.write(identity.get_private_key() or b"")


def generate_identity_to_file(path: str) -> RNS.Identity | None:
    """Create a new identity file. Returns None if path already exists."""
    if os.path.exists(path):
        print("Refusing to overwrite an existing identity file.")
        return None
    identity = RNS.Identity(create_keys=True)
    write_identity_private_key(path, identity)
    print(f"Saved new Reticulum identity to {path}")
    return identity


def print_new_identity_base64() -> None:
    """Generate a throwaway identity and print its private key as base64."""
    identity = RNS.Identity(create_keys=True)
    print(base64.b64encode(identity.get_private_key() or b"").decode("utf-8"))


def load_identity_from_file(path: str) -> RNS.Identity:
    identity = RNS.Identity(create_keys=False)
    identity.load(path)
    print(f"Loaded Reticulum identity <{identity.hash.hex()}> from {path}")
    return identity


def load_identity_from_encoded_key(
    *,
    identity_base64: str | None,
    identity_base32: str | None,
    storage_dir: str | None,
) -> tuple[RNS.Identity, str]:
    """Load from base64/base32 and ensure a default identity file exists."""
    identity = RNS.Identity(create_keys=False)
    if identity_base64 is not None:
        identity.load_private_key(base64.b64decode(identity_base64))
    elif identity_base32 is not None:
        try:
            identity.load_private_key(
                base64.b32decode(identity_base32, casefold=True),
            )
        except Exception as exc:
            msg = f"Invalid base32 identity: {exc}"
            raise ValueError(msg) from exc
    else:
        raise ValueError("Must provide either base64 or base32 identity")

    base_storage = storage_dir or os.path.join("storage")
    os.makedirs(base_storage, exist_ok=True)
    default_path = os.path.join(base_storage, "identity")
    if not os.path.exists(default_path):
        write_identity_private_key(default_path, identity)
    print(f"Loaded Reticulum identity <{identity.hash.hex()}> from provided key")
    return identity, default_path


def load_or_create_default_identity(
    storage_dir: str | None,
) -> tuple[RNS.Identity, str]:
    """Load storage/identity or create one when missing."""
    base_storage = storage_dir or os.path.join("storage")
    os.makedirs(base_storage, exist_ok=True)
    default_path = os.path.join(base_storage, "identity")
    if not os.path.exists(default_path):
        identity = RNS.Identity(create_keys=True)
        write_identity_private_key(default_path, identity)
        print(
            f"Created Reticulum identity <{identity.hash.hex()}> at {default_path}",
        )
    identity = RNS.Identity(create_keys=False)
    identity.load(default_path)
    print(f"Loaded Reticulum identity <{identity.hash.hex()}> from {default_path}")
    return identity, default_path


def resolve_startup_identity(args: Any) -> tuple[RNS.Identity | None, str | None]:
    """Resolve identity from CLI args. Returns (None, None) for generate-and-exit."""
    if args.generate_identity_file is not None:
        generate_identity_to_file(args.generate_identity_file)
        return None, None
    if args.generate_identity_base64 is True:
        print_new_identity_base64()
        return None, None
    if args.identity_file is not None:
        return load_identity_from_file(args.identity_file), args.identity_file
    if args.identity_base64 is not None or args.identity_base32 is not None:
        identity, path = load_identity_from_encoded_key(
            identity_base64=args.identity_base64,
            identity_base32=args.identity_base32,
            storage_dir=args.storage_dir,
        )
        return identity, path
    return load_or_create_default_identity(args.storage_dir)
