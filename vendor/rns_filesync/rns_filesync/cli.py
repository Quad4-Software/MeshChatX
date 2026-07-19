"""Command-line interface for RNS FileSync."""

from __future__ import annotations

import argparse
import os
import sys
import time

import RNS

from rns_filesync._meta import version_string
from rns_filesync.config import (
    allowed_sidecar_paths,
    config_get,
    load_config,
    parse_csv_hashes,
)
from rns_filesync.constants import ANNOUNCE_INTERVAL_DEFAULT, APP_NAME
from rns_filesync.permissions import PermissionStore
from rns_filesync.service import FileSyncService


def load_or_create_identity(identity_name: str, identity_dir: str):
    os.makedirs(identity_dir, exist_ok=True)
    identity_path = os.path.join(identity_dir, identity_name)
    if os.path.isfile(identity_path):
        identity = RNS.Identity.from_file(identity_path)
        RNS.log(f"Loaded identity {identity_name}", RNS.LOG_INFO)
    else:
        identity = RNS.Identity()
        identity.to_file(identity_path)
        RNS.log(f"Created identity {identity_name}", RNS.LOG_INFO)
    return identity


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="RNS FileSync - peer-to-peer file sync over Reticulum",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=version_string(),
        help="print version, build date, and commit then exit",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="FileSync config directory (default: ~/.rns_filesync)",
    )
    parser.add_argument(
        "--rnsconfig",
        default=None,
        help="Reticulum config directory (default: ~/.reticulum)",
    )
    parser.add_argument(
        "-d",
        "--directory",
        default=None,
        help="directory to synchronize (overrides config)",
    )
    parser.add_argument(
        "-i",
        "--identity",
        default=None,
        help="identity name (stored under FileSync config dir)",
    )
    parser.add_argument(
        "-p",
        "--peer",
        action="append",
        dest="peers",
        help="peer identity hash (destination hash accepted as fallback)",
    )
    parser.add_argument(
        "-n",
        "--no-monitor",
        action="store_true",
        help="disable file monitoring",
    )
    parser.add_argument(
        "-a",
        "--announce-interval",
        type=int,
        default=None,
        help="announce interval in seconds",
    )
    parser.add_argument(
        "--allowed",
        default=None,
        help="path to .allowed ACL file (rngit-style permission:target lines)",
    )
    parser.add_argument(
        "--permissions-file",
        default=None,
        help="alias for --allowed (legacy name)",
    )
    parser.add_argument(
        "--allow",
        action="append",
        dest="allowed_peers",
        help="ACL rule (r:hash) or bare identity hash used with --perms",
    )
    parser.add_argument(
        "--perms",
        default="rwd",
        help="legacy shorthand for bare --allow hashes (r, w, d, rw, rwd)",
    )
    parser.add_argument(
        "--verbose",
        action="count",
        default=0,
        help="increase logging (use --verbose, repeat for more)",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="reduce logging")
    parser.add_argument(
        "--no-repl",
        action="store_true",
        help="run without interactive command prompt",
    )
    return parser


def _set_loglevel(verbose: int, quiet: bool, config_level: int | None) -> None:
    if quiet:
        RNS.loglevel = RNS.LOG_ERROR
        return
    if verbose == 1:
        RNS.loglevel = RNS.LOG_VERBOSE
    elif verbose == 2:
        RNS.loglevel = RNS.LOG_DEBUG
    elif verbose >= 3:
        RNS.loglevel = RNS.LOG_EXTREME
    elif config_level is not None:
        RNS.loglevel = int(config_level)
    else:
        RNS.loglevel = RNS.LOG_INFO


def _print_help() -> None:
    print(
        "commands: status peers connect <hash> disconnect <id> browse <id> "
        "download <id> <path> announce files quit",
    )


def run_repl(service: FileSyncService) -> None:
    _print_help()
    while True:
        try:
            line = input("filesync> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()
        if cmd in {"quit", "exit", "q"}:
            break
        if cmd in {"help", "?"}:
            _print_help()
        elif cmd == "status":
            print(service.get_status())
        elif cmd == "peers":
            for peer in service.list_peers():
                print(peer)
        elif cmd == "files":
            for item in service.list_files():
                print(f"{item['path']}\t{item['size']}\t{item['hash']}")
        elif cmd == "announce":
            service.announce_now()
            print("announced")
        elif cmd == "connect" and len(parts) >= 2:
            print(service.connect_peer(parts[1]))
        elif cmd == "disconnect" and len(parts) >= 2:
            service.disconnect_peer(parts[1])
            print("disconnected")
        elif cmd == "browse" and len(parts) >= 2:
            for item in service.browse_peer(parts[1]):
                print(item)
        elif cmd == "download" and len(parts) >= 3:
            print(service.download_file(parts[1], parts[2]))
        else:
            print("unknown command")
            _print_help()


def build_permissions(
    *,
    config,
    sync_directory: str,
    allowed_path: str | None,
    allow_args: list[str] | None,
    perms_shorthand: str,
) -> PermissionStore:
    store = PermissionStore()

    aliases = config.get("aliases") or {}
    if isinstance(aliases, dict):
        store.set_aliases(
            {str(k): str(v) for k, v in aliases.items() if not str(k).startswith("#")},
        )

    blocked = config_get(config, "filesync", "blocked_identities", None)
    store.set_blocked(parse_csv_hashes(blocked))

    access = config.get("access") or {}
    if isinstance(access, dict):
        for key, value in access.items():
            if str(key).startswith("#"):
                continue
            store.load_access_value(value)

    for path in allowed_sidecar_paths(sync_directory):
        if os.path.isfile(path):
            loaded = store.load_file(path)
            if loaded:
                RNS.log(f"Loaded {loaded} ACL rules from {path}", RNS.LOG_INFO)

    if allowed_path:
        store.load_file(allowed_path)

    if allow_args:
        for item in allow_args:
            item = item.strip()
            if ":" in item:
                store.add_rule(item)
            else:
                # Bare hash: apply --perms shorthand as rngit-style rule(s).
                shorthand = perms_shorthand.strip().lower()
                if shorthand in {"r", "w", "d", "rw", "rwd", "adm", "admin"}:
                    store.add_rule(f"{shorthand}:{item}")
                else:
                    # Comma list of long names
                    store.grant(item, [p.strip() for p in shorthand.split(",")])

    return store


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config_dir, config = load_config(args.config)
    config_level = config_get(config, "logging", "loglevel", None)
    try:
        config_level = int(config_level) if config_level is not None else None
    except (TypeError, ValueError):
        config_level = None
    _set_loglevel(args.verbose, args.quiet, config_level)

    directory = args.directory or config_get(config, "filesync", "directory", None)
    if not directory:
        parser.error(
            "sync directory required via -d/--directory or config [filesync] directory",
        )
    directory = os.path.realpath(os.path.expanduser(str(directory)))

    identity_name = args.identity or config_get(
        config,
        "filesync",
        "identity",
        APP_NAME,
    )
    announce_interval = args.announce_interval
    if announce_interval is None:
        raw = config_get(
            config,
            "filesync",
            "announce_interval",
            ANNOUNCE_INTERVAL_DEFAULT,
        )
        try:
            announce_interval = int(raw)
        except (TypeError, ValueError):
            announce_interval = ANNOUNCE_INTERVAL_DEFAULT

    peers = list(args.peers or [])
    peers.extend(parse_csv_hashes(config_get(config, "filesync", "peers", None)))

    allowed_path = args.allowed or args.permissions_file
    permissions = build_permissions(
        config=config,
        sync_directory=directory,
        allowed_path=allowed_path,
        allow_args=args.allowed_peers,
        perms_shorthand=args.perms,
    )

    rnsconfig = args.rnsconfig
    reticulum = RNS.Reticulum(rnsconfig)
    identity = load_or_create_identity(
        str(identity_name),
        os.path.join(config_dir, "identities"),
    )

    service = FileSyncService(
        identity=identity,
        sync_directory=directory,
        reticulum=reticulum,
        configpath=rnsconfig,
        permissions=permissions,
        own_reticulum=True,
    )
    dest = service.start(
        monitor=not args.no_monitor,
        announce_interval=announce_interval,
    )
    print(f"config={config_dir}")
    print(f"identity={service.get_status()['identity_hash']}")
    print(f"destination={dest}")
    print(f"directory={directory}")
    if permissions.enabled:
        print("acl=enforced (deny by default)")
    else:
        print("acl=open (no rules configured)")

    if peers:
        time.sleep(1.0)
        for peer in peers:
            result = service.connect_peer(peer)
            print(f"connect {peer}: {result}")

    try:
        if args.no_repl:
            while True:
                time.sleep(1.0)
        else:
            run_repl(service)
    finally:
        service.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
