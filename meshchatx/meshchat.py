#!/usr/bin/env python

import argparse
import asyncio
import base64
import copy
import io
import ipaddress
import json
import os
import platform
import secrets
import shutil
import ssl
import sys
import tempfile
import threading
import time
import webbrowser
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import bcrypt
import LXMF
import LXST
import psutil
import RNS

# Patch LXST LinkSource to have a samplerate attribute if missing
# This avoids AttributeError in sinks that expect it
try:
    import LXST.Network

    if hasattr(LXST.Network, "LinkSource"):
        original_init = LXST.Network.LinkSource.__init__

        def patched_init(self, *args, **kwargs):
            self.samplerate = 48000  # Default fallback
            original_init(self, *args, **kwargs)

        LXST.Network.LinkSource.__init__ = patched_init
except Exception as e:
    print(f"Failed to patch LXST LinkSource: {e}")

import RNS.vendor.umsgpack as msgpack
from aiohttp import WSCloseCode, WSMessage, WSMsgType, web
from aiohttp_session import get_session
from aiohttp_session import setup as setup_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from LXMF import LXMRouter
from serial.tools import list_ports

from meshchatx.src.backend.announce_handler import AnnounceHandler
from meshchatx.src.backend.announce_manager import AnnounceManager
from meshchatx.src.backend.archiver_manager import ArchiverManager
from meshchatx.src.backend.async_utils import AsyncUtils
from meshchatx.src.backend.colour_utils import ColourUtils
from meshchatx.src.backend.config_manager import ConfigManager
from meshchatx.src.backend.database import Database
from meshchatx.src.backend.forwarding_manager import ForwardingManager
from meshchatx.src.backend.interface_config_parser import InterfaceConfigParser
from meshchatx.src.backend.interface_editor import InterfaceEditor
from meshchatx.src.backend.lxmf_message_fields import (
    LxmfAudioField,
    LxmfFileAttachment,
    LxmfFileAttachmentsField,
    LxmfImageField,
)
from meshchatx.src.backend.map_manager import MapManager
from meshchatx.src.backend.message_handler import MessageHandler
from meshchatx.src.backend.ringtone_manager import RingtoneManager
from meshchatx.src.backend.rncp_handler import RNCPHandler
from meshchatx.src.backend.rnprobe_handler import RNProbeHandler
from meshchatx.src.backend.rnstatus_handler import RNStatusHandler
from meshchatx.src.backend.sideband_commands import SidebandCommands
from meshchatx.src.backend.telemetry_utils import Telemeter
from meshchatx.src.backend.telephone_manager import TelephoneManager
from meshchatx.src.backend.translator_handler import TranslatorHandler
from meshchatx.src.backend.voicemail_manager import VoicemailManager
from meshchatx.src.version import __version__ as app_version


# NOTE: this is required to be able to pack our app with cxfreeze as an exe, otherwise it can't access bundled assets
# this returns a file path based on if we are running meshchat.py directly, or if we have packed it as an exe with cxfreeze
# https://cx-freeze.readthedocs.io/en/latest/faq.html#using-data-files
# bearer:disable python_lang_path_traversal
def get_file_path(filename):
    # Remove trailing slashes for path joining consistency
    filename = filename.rstrip("/\\")
    
    if getattr(sys, "frozen", False):
        datadir = os.path.dirname(sys.executable)
        return os.path.join(datadir, filename)

    # Assets live inside the meshchatx package when installed from a wheel
    package_dir = os.path.dirname(__file__)
    package_path = os.path.join(package_dir, filename)
    if os.path.exists(package_path):
        return package_path

    # When running from the repository, fall back to the project root
    repo_root = os.path.dirname(package_dir)
    repo_path = os.path.join(repo_root, filename)
    if os.path.exists(repo_path):
        return repo_path

    return package_path


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
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                    x509.IPAddress(ipaddress.IPv6Address("::1")),
                ],
            ),
            critical=False,
        )
        .sign(private_key, hashes.SHA256(), default_backend())
    )

    cert_dir = os.path.dirname(cert_path)
    if cert_dir:
        os.makedirs(cert_dir, exist_ok=True)

    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    with open(key_path, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ),
        )


class ReticulumMeshChat:
    def __init__(
        self,
        identity: RNS.Identity,
        storage_dir,
        reticulum_config_dir,
        auto_recover: bool = False,
        identity_file_path: str | None = None,
        auth_enabled: bool = False,
    ):
        self.running = True
        self.reticulum_config_dir = reticulum_config_dir
        # when providing a custom storage_dir, files will be saved as
        # <storage_dir>/identities/<identity_hex>/
        # <storage_dir>/identities/<identity_hex>/database.db

        # if storage_dir is not provided, we will use ./storage instead
        # ./storage/identities/<identity_hex>/
        # ./storage/identities/<identity_hex>/database.db

        # ensure a storage path exists for the loaded identity
        self.running = True
        self.reticulum_config_dir = reticulum_config_dir
        self.storage_dir = storage_dir or os.path.join("storage")
        self.identity_file_path = identity_file_path
        self.auto_recover = auto_recover
        self.auth_enabled_initial = auth_enabled
        self.websocket_clients: list[web.WebSocketResponse] = []

        # track announce timestamps for rate calculation
        self.announce_timestamps = []

        # track download speeds for nomadnetwork files
        self.download_speeds = []

        # track active downloads
        self.active_downloads = {}
        self.download_id_counter = 0

        self.setup_identity(identity)

    def setup_identity(self, identity: RNS.Identity):
        # assign a unique session ID to this identity instance to help background threads exit
        if not hasattr(self, "_identity_session_id"):
            self._identity_session_id = 0
        self._identity_session_id += 1
        session_id = self._identity_session_id

        # ensure a storage path exists for the loaded identity
        self.storage_path = os.path.join(
            self.storage_dir,
            "identities",
            identity.hash.hex(),
        )
        print(f"Using Storage Path: {self.storage_path}")
        os.makedirs(self.storage_path, exist_ok=True)

        # Safety: Before setting up a new identity, ensure no destinations for this identity
        # are currently registered in Transport. This prevents the "Attempt to register
        # an already registered destination" error during hotswap.
        self.cleanup_rns_state_for_identity(identity.hash)

        # ensure identity is saved in its specific directory for multi-identity support
        identity_backup_file = os.path.join(self.storage_path, "identity")
        if not os.path.exists(identity_backup_file):
            with open(identity_backup_file, "wb") as f:
                f.write(identity.get_private_key())

        # define path to files based on storage path
        self.database_path = os.path.join(self.storage_path, "database.db")
        lxmf_router_path = os.path.join(self.storage_path, "lxmf_router")

        # init database
        self.database = Database(self.database_path)
        self.db = (
            self.database
        )  # keep for compatibility with parts I haven't changed yet

        try:
            self.database.initialize()
            # Try to auto-migrate from legacy database if this is a fresh start
            self.database.migrate_from_legacy(
                self.reticulum_config_dir, identity.hash.hex()
            )
            self._tune_sqlite_pragmas()
        except Exception as exc:
            if not self.auto_recover:
                raise

            print(f"Database initialization failed, attempting auto recovery: {exc}")
            self._run_startup_auto_recovery()
            # retry once after recovery
            self.database.initialize()
            self._tune_sqlite_pragmas()

        # init config
        self.config = ConfigManager(self.database)

        # init managers
        self.message_handler = MessageHandler(self.database)
        self.announce_manager = AnnounceManager(self.database)
        self.archiver_manager = ArchiverManager(self.database)
        self.map_manager = MapManager(self.config, self.storage_dir)
        self.forwarding_manager = None  # will init after lxmf router

        # remember if authentication is enabled
        self.auth_enabled = self.auth_enabled_initial or self.config.auth_enabled.get()

        # migrate database
        # The new initialize() handles migrations automatically, but we still update the config if needed
        self.config.database_version.set(self.database.schema.LATEST_VERSION)

        # vacuum database on start to shrink its file size
        self.database.provider.vacuum()

        # lxmf messages in outbound or sending state should be marked as failed when app starts as they are no longer being processed
        self.database.messages.mark_stuck_messages_as_failed()

        # init reticulum
        if not hasattr(self, "reticulum"):
            self.reticulum = RNS.Reticulum(self.reticulum_config_dir)
        self.identity = identity

        # init lxmf router
        # get propagation node stamp cost from config (only used if running a propagation node)
        propagation_stamp_cost = self.config.lxmf_propagation_node_stamp_cost.get()
        self.message_router = LXMF.LXMRouter(
            identity=self.identity,
            storagepath=lxmf_router_path,
            propagation_cost=propagation_stamp_cost,
        )
        self.message_router.PROCESSING_INTERVAL = 1

        # increase limit for incoming lxmf messages (received over a resource), to allow receiving larger attachments
        # the lxmf router expects delivery_per_transfer_limit to be provided in kilobytes, so we will do that...
        self.message_router.delivery_per_transfer_limit = (
            self.config.lxmf_delivery_transfer_limit_in_bytes.get() / 1000
        )

        # register lxmf identity
        inbound_stamp_cost = self.config.lxmf_inbound_stamp_cost.get()
        self.local_lxmf_destination = self.message_router.register_delivery_identity(
            identity=self.identity,
            display_name=self.config.display_name.get(),
            stamp_cost=inbound_stamp_cost,
        )

        # load and register all forwarding alias identities
        self.forwarding_manager = ForwardingManager(
            self.database,
            lxmf_router_path,
            self.on_lxmf_delivery,
            config=self.config,
        )
        self.forwarding_manager.load_aliases()

        # set a callback for when an lxmf message is received
        self.message_router.register_delivery_callback(self.on_lxmf_delivery)

        # update active propagation node
        self.set_active_propagation_node(
            self.config.lxmf_preferred_propagation_node_destination_hash.get(),
        )

        # enable propagation node (we don't call with false if disabled, as no need to announce disabled state every launch)
        if self.config.lxmf_local_propagation_node_enabled.get():
            self.enable_local_propagation_node()

        # handle received announces based on aspect
        RNS.Transport.register_announce_handler(
            AnnounceHandler("lxst.telephony", self.on_telephone_announce_received),
        )
        RNS.Transport.register_announce_handler(
            AnnounceHandler("lxmf.delivery", self.on_lxmf_announce_received),
        )
        RNS.Transport.register_announce_handler(
            AnnounceHandler(
                "lxmf.propagation",
                self.on_lxmf_propagation_announce_received,
            ),
        )
        RNS.Transport.register_announce_handler(
            AnnounceHandler(
                "nomadnetwork.node",
                self.on_nomadnet_node_announce_received,
            ),
        )

        # register audio call identity
        # init telephone manager
        self.telephone_manager = TelephoneManager(
            identity=self.identity,
            config_manager=self.config,
        )
        self.telephone_manager.register_ringing_callback(
            self.on_incoming_telephone_call,
        )
        self.telephone_manager.register_established_callback(
            self.on_telephone_call_established,
        )
        self.telephone_manager.register_ended_callback(
            self.on_telephone_call_ended,
        )
        self.telephone_manager.init_telephone()

        # init Voicemail Manager
        self.voicemail_manager = VoicemailManager(
            db=self.database,
            config=self.config,
            telephone_manager=self.telephone_manager,
            storage_dir=self.storage_path,
        )
        # Monkey patch VoicemailManager to use our get_name_for_identity_hash
        self.voicemail_manager.get_name_for_identity_hash = (
            self.get_name_for_identity_hash
        )
        self.voicemail_manager.on_new_voicemail_callback = (
            self.on_new_voicemail_received
        )

        # init Ringtone Manager
        self.ringtone_manager = RingtoneManager(
            config=self.config,
            storage_dir=self.storage_path,
        )

        # init RNCP handler
        self.rncp_handler = RNCPHandler(
            reticulum_instance=self.reticulum,
            identity=self.identity,
            storage_dir=self.storage_dir,
        )

        # init RNStatus handler
        self.rnstatus_handler = RNStatusHandler(reticulum_instance=self.reticulum)

        # init RNProbe handler
        self.rnprobe_handler = RNProbeHandler(
            reticulum_instance=self.reticulum,
            identity=self.identity,
        )

        # init Translator handler
        libretranslate_url = self.config.get("libretranslate_url", None)
        self.translator_handler = TranslatorHandler(
            libretranslate_url=libretranslate_url,
        )

        # start background thread for auto announce loop
        thread = threading.Thread(
            target=asyncio.run, args=(self.announce_loop(session_id),)
        )
        thread.daemon = True
        thread.start()

        # start background thread for auto syncing propagation nodes
        thread = threading.Thread(
            target=asyncio.run,
            args=(self.announce_sync_propagation_nodes(session_id),),
        )
        thread.daemon = True
        thread.start()

        # start background thread for crawler loop
        thread = threading.Thread(
            target=asyncio.run,
            args=(self.crawler_loop(session_id),),
        )
        thread.daemon = True
        thread.start()

    def _tune_sqlite_pragmas(self):
        try:
            self.db.execute_sql("PRAGMA wal_autocheckpoint=1000")
            self.db.execute_sql("PRAGMA temp_store=MEMORY")
            self.db.execute_sql("PRAGMA journal_mode=WAL")
        except Exception as exc:
            print(f"SQLite pragma setup failed: {exc}")

    def _get_pragma_value(self, pragma: str, default=None):
        try:
            cursor = self.db.execute_sql(f"PRAGMA {pragma}")
            row = cursor.fetchone()
            if row is None:
                return default
            return row[0]
        except Exception:
            return default

    def _get_database_file_stats(self):
        def size_for(path):
            try:
                return os.path.getsize(path)
            except OSError:
                return 0

        wal_path = f"{self.database_path}-wal"
        shm_path = f"{self.database_path}-shm"

        main_bytes = size_for(self.database_path)
        wal_bytes = size_for(wal_path)
        shm_bytes = size_for(shm_path)

        return {
            "main_bytes": main_bytes,
            "wal_bytes": wal_bytes,
            "shm_bytes": shm_bytes,
            "total_bytes": main_bytes + wal_bytes + shm_bytes,
        }

    def _database_paths(self):
        return {
            "main": self.database_path,
            "wal": f"{self.database_path}-wal",
            "shm": f"{self.database_path}-shm",
        }

    def get_database_health_snapshot(self):
        page_size = self._get_pragma_value("page_size", 0) or 0
        page_count = self._get_pragma_value("page_count", 0) or 0
        freelist_pages = self._get_pragma_value("freelist_count", 0) or 0
        free_bytes = (
            page_size * freelist_pages if page_size > 0 and freelist_pages > 0 else 0
        )

        return {
            "quick_check": self._get_pragma_value("quick_check", "unknown"),
            "journal_mode": self._get_pragma_value("journal_mode", "unknown"),
            "synchronous": self._get_pragma_value("synchronous", None),
            "wal_autocheckpoint": self._get_pragma_value("wal_autocheckpoint", None),
            "auto_vacuum": self._get_pragma_value("auto_vacuum", None),
            "page_size": page_size,
            "page_count": page_count,
            "freelist_pages": freelist_pages,
            "estimated_free_bytes": free_bytes,
            "files": self._get_database_file_stats(),
        }

    def _checkpoint_wal(self, mode: str = "TRUNCATE"):
        return self.db.execute_sql(f"PRAGMA wal_checkpoint({mode})").fetchall()

    def run_database_vacuum(self):
        checkpoint = self._checkpoint_wal()
        self.db.execute_sql("VACUUM")
        self._tune_sqlite_pragmas()

        return {
            "checkpoint": checkpoint,
            "health": self.get_database_health_snapshot(),
        }

    def run_database_recovery(self):
        actions = []

        actions.append(
            {
                "step": "quick_check_before",
                "result": self._get_pragma_value("quick_check", "unknown"),
            },
        )

        actions.append({"step": "wal_checkpoint", "result": self._checkpoint_wal()})

        integrity_rows = self.database.provider.integrity_check()
        integrity = [row[0] for row in integrity_rows] if integrity_rows else []
        actions.append({"step": "integrity_check", "result": integrity})

        self.database.provider.vacuum()
        self._tune_sqlite_pragmas()

        actions.append(
            {
                "step": "quick_check_after",
                "result": self._get_pragma_value("quick_check", "unknown"),
            },
        )

        return {
            "actions": actions,
            "health": self.get_database_health_snapshot(),
        }

    def _checkpoint_and_close(self):
        try:
            self._checkpoint_wal()
        except Exception as e:
            print(f"Failed to checkpoint WAL: {e}")
        try:
            self.database.close()
        except Exception as e:
            print(f"Failed to close database: {e}")

    def _backup_to_zip(self, backup_path: str):
        paths = self._database_paths()
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        # ensure WAL is checkpointed to get a consistent snapshot
        self._checkpoint_wal()

        with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(paths["main"], arcname="database.db")
            if os.path.exists(paths["wal"]):
                zf.write(paths["wal"], arcname="database.db-wal")
            if os.path.exists(paths["shm"]):
                zf.write(paths["shm"], arcname="database.db-shm")

        return {
            "path": backup_path,
            "size": os.path.getsize(backup_path),
        }

    def backup_database(self, backup_path: str | None = None):
        default_dir = os.path.join(self.storage_path, "database-backups")
        os.makedirs(default_dir, exist_ok=True)
        if backup_path is None:
            timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            backup_path = os.path.join(default_dir, f"backup-{timestamp}.zip")

        return self._backup_to_zip(backup_path)

    def restore_database(self, backup_path: str):
        if not os.path.exists(backup_path):
            msg = f"Backup not found at {backup_path}"
            raise FileNotFoundError(msg)

        paths = self._database_paths()
        self._checkpoint_and_close()

        # clean existing files
        for p in paths.values():
            if os.path.exists(p):
                os.remove(p)

        if zipfile.is_zipfile(backup_path):
            with zipfile.ZipFile(backup_path, "r") as zf:
                zf.extractall(os.path.dirname(paths["main"]))
        else:
            shutil.copy2(backup_path, paths["main"])

        # reopen and retune
        self.database.initialize()
        self._tune_sqlite_pragmas()
        integrity = self.database.provider.integrity_check()

        return {
            "restored_from": backup_path,
            "integrity_check": integrity,
            "health": self.get_database_health_snapshot(),
        }

    def _get_identity_bytes(self) -> bytes:
        return self.identity.get_private_key()

    def cleanup_rns_state_for_identity(self, identity_hash):
        if not identity_hash:
            return

        if isinstance(identity_hash, str):
            identity_hash_bytes = bytes.fromhex(identity_hash)
            identity_hash_hex = identity_hash
        else:
            identity_hash_bytes = identity_hash
            identity_hash_hex = identity_hash.hex()

        print(f"Aggressively cleaning up RNS state for identity {identity_hash_hex}")

        # 1. Deregister destinations
        try:
            # We iterate over a copy of the list because we are modifying it
            for destination in list(RNS.Transport.destinations):
                match = False
                # check identity hash
                if hasattr(destination, "identity") and destination.identity:
                    if destination.identity.hash == identity_hash_bytes:
                        match = True

                if match:
                    print(
                        f"Deregistering RNS destination {destination} ({RNS.prettyhexrep(destination.hash)})"
                    )
                    RNS.Transport.deregister_destination(destination)
        except Exception as e:
            print(f"Error while cleaning up RNS destinations: {e}")

        # 2. Teardown active links
        try:
            for link in list(RNS.Transport.active_links):
                match = False
                # check if local identity or destination matches
                if hasattr(link, "destination") and link.destination:
                    if (
                        hasattr(link.destination, "identity")
                        and link.destination.identity
                    ):
                        if link.destination.identity.hash == identity_hash_bytes:
                            match = True

                if match:
                    print(f"Tearing down RNS link {link}")
                    try:
                        link.teardown()
                    except Exception:
                        pass
        except Exception as e:
            print(f"Error while cleaning up RNS links: {e}")

    def teardown_identity(self):
        print("Tearing down current identity instance...")
        self.running = False

        # 1. Deregister destinations and links from RNS Transport
        try:
            # Get current identity hash for matching
            current_identity_hash = (
                self.identity.hash
                if hasattr(self, "identity") and self.identity
                else None
            )

            # Explicitly deregister known destinations from managers first
            if hasattr(self, "message_router") and self.message_router:
                # Deregister delivery destinations
                if hasattr(self.message_router, "delivery_destinations"):
                    for dest_hash in list(
                        self.message_router.delivery_destinations.keys()
                    ):
                        dest = self.message_router.delivery_destinations[dest_hash]
                        RNS.Transport.deregister_destination(dest)

                # Deregister propagation destination
                if (
                    hasattr(self.message_router, "propagation_destination")
                    and self.message_router.propagation_destination
                ):
                    RNS.Transport.deregister_destination(
                        self.message_router.propagation_destination
                    )

            if hasattr(self, "telephone_manager") and self.telephone_manager:
                if (
                    hasattr(self.telephone_manager, "telephone")
                    and self.telephone_manager.telephone
                ):
                    if (
                        hasattr(self.telephone_manager.telephone, "destination")
                        and self.telephone_manager.telephone.destination
                    ):
                        RNS.Transport.deregister_destination(
                            self.telephone_manager.telephone.destination
                        )

            # Use the global helper for thorough cleanup
            if current_identity_hash:
                self.cleanup_rns_state_for_identity(current_identity_hash)

        except Exception as e:
            print(f"Error while deregistering destinations or links: {e}")

        # 2. Unregister all announce handlers from Transport
        try:
            for handler in list(RNS.Transport.announce_handlers):
                should_deregister = False

                # check if it's one of our AnnounceHandler instances
                if (
                    (
                        hasattr(handler, "aspect_filter")
                        and hasattr(handler, "received_announce_callback")
                    )
                    or (
                        hasattr(handler, "router")
                        and hasattr(self, "message_router")
                        and handler.router == self.message_router
                    )
                    or "LXMFDeliveryAnnounceHandler" in str(type(handler))
                    or "LXMFPropagationAnnounceHandler" in str(type(handler))
                ):
                    should_deregister = True

                if should_deregister:
                    RNS.Transport.deregister_announce_handler(handler)
        except Exception as e:
            print(f"Error while deregistering announce handlers: {e}")

        # 3. Stop the LXMRouter job loop (hacking it to stop)
        if hasattr(self, "message_router") and self.message_router:
            try:
                # Replacing jobs with a no-op so the thread just sleeps
                self.message_router.jobs = lambda: None

                # Try to call exit_handler to persist state
                if hasattr(self.message_router, "exit_handler"):
                    self.message_router.exit_handler()
            except Exception as e:
                print(f"Error while tearing down LXMRouter: {e}")

        # 4. Stop telephone and voicemail
        if hasattr(self, "telephone_manager") and self.telephone_manager:
            try:
                # use teardown instead of shutdown
                if hasattr(self.telephone_manager, "teardown"):
                    self.telephone_manager.teardown()
                elif hasattr(self.telephone_manager, "shutdown"):
                    self.telephone_manager.shutdown()
            except Exception as e:
                print(f"Error while tearing down telephone: {e}")

        if hasattr(self, "voicemail_manager") and self.voicemail_manager:
            try:
                self.voicemail_manager.stop_recording()
            except Exception:
                pass

        # 5. Close database
        if hasattr(self, "database") and self.database:
            try:
                self.database.close()
            except Exception:
                pass

    async def hotswap_identity(self, identity_hash):
        try:
            # load the new identity
            identity_dir = os.path.join(self.storage_dir, "identities", identity_hash)
            identity_file = os.path.join(identity_dir, "identity")
            if not os.path.exists(identity_file):
                raise ValueError("Identity file not found")

            new_identity = RNS.Identity.from_file(identity_file)

            # 1. teardown old identity
            self.teardown_identity()

            # Wait a moment for threads to notice self.running=False and destinations to clear
            await asyncio.sleep(3)

            # 2. update main identity file
            main_identity_file = self.identity_file_path or os.path.join(
                self.storage_dir, "identity"
            )
            import shutil

            shutil.copy2(identity_file, main_identity_file)

            # 3. reset state and setup new identity
            self.running = True
            self.setup_identity(new_identity)

            # 4. broadcast update to clients
            await self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "identity_switched",
                        "identity_hash": identity_hash,
                        "display_name": self.config.display_name.get(),
                    }
                ),
            )

            return True
        except Exception as e:
            print(f"Hotswap failed: {e}")
            import traceback

            traceback.print_exc()
            return False

    def backup_identity(self):
        identity_bytes = self._get_identity_bytes()
        target_path = self.identity_file_path or os.path.join(
            self.storage_dir,
            "identity",
        )
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "wb") as f:
            f.write(identity_bytes)
        return {
            "path": target_path,
            "size": os.path.getsize(target_path),
        }

    def backup_identity_base32(self) -> str:
        return base64.b32encode(self._get_identity_bytes()).decode("utf-8")

    def list_identities(self):
        identities = []
        identities_base_dir = os.path.join(self.storage_dir, "identities")
        if not os.path.exists(identities_base_dir):
            return identities

        for identity_hash in os.listdir(identities_base_dir):
            identity_path = os.path.join(identities_base_dir, identity_hash)
            if not os.path.isdir(identity_path):
                continue

            db_path = os.path.join(identity_path, "database.db")
            if not os.path.exists(db_path):
                continue

            # try to get config from database
            display_name = "Anonymous Peer"
            icon_name = None
            icon_foreground_colour = None
            icon_background_colour = None

            try:
                # use a temporary provider to avoid messing with current DB
                from meshchatx.src.backend.database.config import ConfigDAO
                from meshchatx.src.backend.database.provider import DatabaseProvider

                temp_provider = DatabaseProvider(db_path)
                temp_config_dao = ConfigDAO(temp_provider)
                display_name = temp_config_dao.get("display_name", "Anonymous Peer")
                icon_name = temp_config_dao.get("lxmf_user_icon_name")
                icon_foreground_colour = temp_config_dao.get(
                    "lxmf_user_icon_foreground_colour"
                )
                icon_background_colour = temp_config_dao.get(
                    "lxmf_user_icon_background_colour"
                )
                temp_provider.close()
            except Exception as e:
                print(f"Error reading config for {identity_hash}: {e}")

            identities.append(
                {
                    "hash": identity_hash,
                    "display_name": display_name,
                    "icon_name": icon_name,
                    "icon_foreground_colour": icon_foreground_colour,
                    "icon_background_colour": icon_background_colour,
                    "is_current": identity_hash == self.identity.hash.hex(),
                }
            )
        return identities

    def create_identity(self, display_name=None):
        new_identity = RNS.Identity(create_keys=True)
        identity_hash = new_identity.hash.hex()

        identity_dir = os.path.join(self.storage_dir, "identities", identity_hash)
        os.makedirs(identity_dir, exist_ok=True)

        # save identity file in its own directory
        identity_file = os.path.join(identity_dir, "identity")
        with open(identity_file, "wb") as f:
            f.write(new_identity.get_private_key())

        # initialize its database and set display name
        db_path = os.path.join(identity_dir, "database.db")

        # Avoid using the Database class singleton behavior
        from meshchatx.src.backend.database.config import ConfigDAO
        from meshchatx.src.backend.database.provider import DatabaseProvider
        from meshchatx.src.backend.database.schema import DatabaseSchema

        new_provider = DatabaseProvider(db_path)
        new_schema = DatabaseSchema(new_provider)
        new_schema.initialize()

        if display_name:
            new_config_dao = ConfigDAO(new_provider)
            new_config_dao.set("display_name", display_name)

        new_provider.close()

        return {
            "hash": identity_hash,
            "display_name": display_name or "Anonymous Peer",
        }

    def delete_identity(self, identity_hash):
        if identity_hash == self.identity.hash.hex():
            raise ValueError("Cannot delete the current active identity")

        identity_dir = os.path.join(self.storage_dir, "identities", identity_hash)
        if os.path.exists(identity_dir):
            import shutil

            shutil.rmtree(identity_dir)
            return True
        return False

    def restore_identity_from_bytes(self, identity_bytes: bytes):
        target_path = self.identity_file_path or os.path.join(
            self.storage_dir,
            "identity",
        )
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "wb") as f:
            f.write(identity_bytes)
        return {"path": target_path, "size": os.path.getsize(target_path)}

    def restore_identity_from_base32(self, base32_value: str):
        try:
            identity_bytes = base64.b32decode(base32_value, casefold=True)
        except Exception as exc:
            msg = f"Invalid base32 identity: {exc}"
            raise ValueError(msg) from exc

        return self.restore_identity_from_bytes(identity_bytes)

    def _run_startup_auto_recovery(self):
        try:
            self.database.initialize()
            print("Attempting SQLite auto recovery on startup...")
            actions = []
            actions.append(
                {
                    "step": "wal_checkpoint",
                    "result": self.database.provider.checkpoint(),
                },
            )
            actions.append(
                {
                    "step": "integrity_check",
                    "result": self.database.provider.integrity_check(),
                },
            )
            self.database.provider.vacuum()
            self._tune_sqlite_pragmas()
            actions.append(
                {
                    "step": "quick_check_after",
                    "result": self.database.provider.quick_check(),
                },
            )
            print(f"Auto recovery completed: {actions}")
        finally:
            try:
                self.database.close()
            except Exception as e:
                print(f"Failed to close database during recovery: {e}")

    # gets app version from the synchronized Python version helper
    @staticmethod
    def get_app_version() -> str:
        return app_version

    # automatically announces based on user config
    async def announce_loop(self, session_id):
        while self.running and self._identity_session_id == session_id:
            should_announce = False

            # check if auto announce is enabled
            if self.config.auto_announce_enabled.get():
                # check if we have announced recently
                last_announced_at = self.config.last_announced_at.get()
                if last_announced_at is not None:
                    # determine when next announce should be sent
                    auto_announce_interval_seconds = (
                        self.config.auto_announce_interval_seconds.get()
                    )
                    next_announce_at = (
                        last_announced_at + auto_announce_interval_seconds
                    )

                    # we should announce if current time has passed next announce at timestamp
                    if time.time() > next_announce_at:
                        should_announce = True

                else:
                    # last announced at is null, so we have never announced, lets do it now
                    should_announce = True

            # announce
            if should_announce:
                await self.announce()

                # also announce forwarding aliases if any
                if self.forwarding_manager:
                    await asyncio.to_thread(self.forwarding_manager.announce_aliases)

            # wait 1 second before next loop
            await asyncio.sleep(1)

    # automatically syncs propagation nodes based on user config
    async def announce_sync_propagation_nodes(self, session_id):
        while self.running and self._identity_session_id == session_id:
            should_sync = False

            # check if auto sync is enabled
            auto_sync_interval_seconds = self.config.lxmf_preferred_propagation_node_auto_sync_interval_seconds.get()
            if auto_sync_interval_seconds > 0:
                # check if we have synced recently
                last_synced_at = (
                    self.config.lxmf_preferred_propagation_node_last_synced_at.get()
                )
                if last_synced_at is not None:
                    # determine when next sync should happen
                    next_sync_at = last_synced_at + auto_sync_interval_seconds

                    # we should sync if current time has passed next sync at timestamp
                    if time.time() > next_sync_at:
                        should_sync = True

                else:
                    # last synced at is null, so we have never synced, lets do it now
                    should_sync = True

            # sync
            if should_sync:
                await self.sync_propagation_nodes()

            # wait 1 second before next loop
            await asyncio.sleep(1)

    async def crawler_loop(self, session_id):
        while self.running and self._identity_session_id == session_id:
            try:
                if self.config.crawler_enabled.get():
                    # Proactively queue any known nodes from the database that haven't been queued yet
                    # get known propagation nodes from database
                    known_nodes = self.database.announces.get_announces(
                        aspect="nomadnetwork.node",
                    )
                    for node in known_nodes:
                        if not self.running or self._identity_session_id != session_id:
                            break
                        self.queue_crawler_task(
                            node["destination_hash"],
                            "/page/index.mu",
                        )

                    # process pending or failed tasks
                    # ensure we handle potential string comparison issues in SQLite
                    tasks = self.database.misc.get_pending_or_failed_crawl_tasks(
                        max_retries=self.config.crawler_max_retries.get(),
                        max_concurrent=self.config.crawler_max_concurrent.get(),
                    )

                    # process tasks concurrently up to the limit
                    if tasks and self.running:
                        await asyncio.gather(
                            *[self.process_crawler_task(task) for task in tasks],
                        )

            except Exception as e:
                print(f"Error in crawler loop: {e}")

            # wait 30 seconds before checking again
            for _ in range(30):
                if not self.running or self._identity_session_id != session_id:
                    return
                await asyncio.sleep(1)

    async def process_crawler_task(self, task):
        # mark as crawling
        task_id = task["id"]
        self.database.misc.update_crawl_task(
            task_id,
            status="crawling",
            last_retry_at=datetime.now(UTC),
        )

        destination_hash = task["destination_hash"]
        page_path = task["page_path"]

        print(
            f"Crawler: Archiving {destination_hash}:{page_path} (Attempt {task['retry_count'] + 1})",
        )

        # completion event
        done_event = asyncio.Event()
        success = [False]
        content_received = [None]
        failure_reason = ["timeout"]

        def on_success(content):
            success[0] = True
            content_received[0] = content
            done_event.set()

        def on_failure(reason):
            failure_reason[0] = reason
            done_event.set()

        def on_progress(progress):
            pass

        # start downloader
        downloader = NomadnetPageDownloader(
            destination_hash=bytes.fromhex(destination_hash),
            page_path=page_path,
            data=None,
            on_page_download_success=on_success,
            on_page_download_failure=on_failure,
            on_progress_update=on_progress,
            timeout=120,
        )

        try:
            # use a dedicated task for the download so we can wait for it
            download_task = asyncio.create_task(downloader.download())

            # wait for completion event
            try:
                await asyncio.wait_for(done_event.wait(), timeout=180)
            except TimeoutError:
                failure_reason[0] = "timeout"
                downloader.cancel()

            await download_task
        except Exception as e:
            print(
                f"Crawler: Error during download for {destination_hash}:{page_path}: {e}",
            )
            failure_reason[0] = str(e)
            done_event.set()

        if success[0]:
            print(f"Crawler: Successfully archived {destination_hash}:{page_path}")
            self.archive_page(
                destination_hash,
                page_path,
                content_received[0],
                is_manual=False,
            )
            task.status = "completed"
            task.save()
        else:
            print(
                f"Crawler: Failed to archive {destination_hash}:{page_path} - {failure_reason[0]}",
            )
            task.retry_count += 1
            task.status = "failed"

            # calculate next retry time
            retry_delay = self.config.crawler_retry_delay_seconds.get()
            # simple backoff
            backoff_delay = retry_delay * (2 ** (task.retry_count - 1))
            task.next_retry_at = datetime.now(UTC) + timedelta(seconds=backoff_delay)
            task.save()

    # uses the provided destination hash as the active propagation node
    def set_active_propagation_node(self, destination_hash: str | None):
        # set outbound propagation node
        if destination_hash is not None and destination_hash != "":
            try:
                self.message_router.set_outbound_propagation_node(
                    bytes.fromhex(destination_hash),
                )
            except Exception:
                # failed to set propagation node, clear it to ensure we don't use an old one by mistake
                self.remove_active_propagation_node()

        # stop using propagation node
        else:
            self.remove_active_propagation_node()

    # stops the in progress propagation node sync
    def stop_propagation_node_sync(self):
        self.message_router.cancel_propagation_node_requests()

    # stops and removes the active propagation node
    def remove_active_propagation_node(self):
        # fixme: it's possible for internal transfer state to get stuck if we change propagation node during a sync
        # this still happens even if we cancel the propagation node requests
        # for now, the user can just manually cancel syncing in the ui if they think it's stuck...
        self.stop_propagation_node_sync()
        self.message_router.outbound_propagation_node = None

    # enables or disables the local lxmf propagation node
    def enable_local_propagation_node(self, enabled: bool = True):
        try:
            if enabled:
                self.message_router.enable_propagation()
            else:
                self.message_router.disable_propagation()
        except Exception:
            print("failed to enable or disable propagation node")

    def _get_reticulum_section(self):
        try:
            reticulum_config = self.reticulum.config["reticulum"]
        except Exception:
            reticulum_config = None

        if not isinstance(reticulum_config, dict):
            reticulum_config = {}
            self.reticulum.config["reticulum"] = reticulum_config

        return reticulum_config

    def _get_interfaces_section(self):
        try:
            interfaces = self.reticulum.config["interfaces"]
        except Exception:
            interfaces = None

        if not isinstance(interfaces, dict):
            interfaces = {}
            self.reticulum.config["interfaces"] = interfaces

        return interfaces

    def _get_interfaces_snapshot(self):
        snapshot = {}
        interfaces = self._get_interfaces_section()
        for name, interface in interfaces.items():
            try:
                snapshot[name] = copy.deepcopy(dict(interface))
            except Exception:
                try:
                    snapshot[name] = copy.deepcopy(interface)
                except Exception:
                    snapshot[name] = {}
        return snapshot

    def _write_reticulum_config(self):
        try:
            self.reticulum.config.write()
            return True
        except Exception as e:
            print(f"Failed to write Reticulum config: {e}")
            return False

    def build_user_guidance_messages(self):
        guidance = []

        interfaces = self._get_interfaces_section()
        if len(interfaces) == 0:
            guidance.append(
                {
                    "id": "no_interfaces",
                    "title": "No Reticulum interfaces configured",
                    "description": "Add at least one Reticulum interface so MeshChat can talk to your radio or transport.",
                    "action_route": "/interfaces/add",
                    "action_label": "Add Interface",
                    "severity": "warning",
                },
            )

        if not self.reticulum.transport_enabled():
            guidance.append(
                {
                    "id": "transport_disabled",
                    "title": "Transport mode is disabled",
                    "description": "Enable transport to allow MeshChat to relay traffic over your configured interfaces.",
                    "action_route": "/settings",
                    "action_label": "Open Settings",
                    "severity": "info",
                },
            )

        if not self.config.auto_announce_enabled.get():
            guidance.append(
                {
                    "id": "announce_disabled",
                    "title": "Auto announcements are turned off",
                    "description": "Automatic announces make it easier for other peers to discover you. Enable them if you want to stay visible.",
                    "action_route": "/settings",
                    "action_label": "Manage Announce Settings",
                    "severity": "info",
                },
            )

        return guidance

    # returns the latest message for the provided destination hash
    def get_conversation_latest_message(self, destination_hash: str):
        local_hash = self.identity.hexhash
        messages = self.message_handler.get_conversation_messages(
            local_hash,
            destination_hash,
            limit=1,
        )
        return messages[0] if messages else None

    # returns true if the conversation with the provided destination hash has any attachments
    def conversation_has_attachments(self, destination_hash: str):
        local_hash = self.identity.hexhash
        messages = self.message_handler.get_conversation_messages(
            local_hash,
            destination_hash,
        )
        for message in messages:
            if self.message_fields_have_attachments(message["fields"]):
                return True
        return False

    @staticmethod
    def message_fields_have_attachments(fields_json: str | None):
        if not fields_json:
            return False
        try:
            fields = json.loads(fields_json)
        except Exception:
            return False
        if "image" in fields or "audio" in fields:
            return True
        if "file_attachments" in fields and isinstance(
            fields["file_attachments"],
            list,
        ):
            return len(fields["file_attachments"]) > 0
        return False

    def search_destination_hashes_by_message(self, search_term: str):
        if search_term is None or search_term.strip() == "":
            return set()

        local_hash = self.local_lxmf_destination.hexhash
        search_term = search_term.strip()
        matches = set()

        query_results = self.message_handler.search_messages(local_hash, search_term)

        for message in query_results:
            if message["source_hash"] == local_hash:
                matches.add(message["destination_hash"])
            else:
                matches.add(message["source_hash"])

        # also check custom display names
        custom_names = (
            self.database.announces.get_announces()
        )  # Or more specific if needed
        for announce in custom_names:
            custom_name = self.database.announces.get_custom_display_name(
                announce["destination_hash"],
            )
            if custom_name and search_term.lower() in custom_name.lower():
                matches.add(announce["destination_hash"])

        return matches

    @staticmethod
    def parse_bool_query_param(value: str | None) -> bool:
        if value is None:
            return False
        value = value.lower()
        return value in {"1", "true", "yes", "on"}

    def on_new_voicemail_received(self, remote_hash, remote_name, duration):
        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "new_voicemail",
                        "remote_identity_hash": remote_hash,
                        "remote_identity_name": remote_name,
                        "duration": duration,
                        "timestamp": time.time(),
                    },
                ),
            ),
        )

    # handle receiving a new audio call
    def on_incoming_telephone_call(self, caller_identity: RNS.Identity):
        caller_hash = caller_identity.hash.hex()

        # Check if caller is blocked
        if self.is_destination_blocked(caller_hash):
            print(f"Rejecting incoming call from blocked source: {caller_hash}")
            if self.telephone_manager.telephone:
                self.telephone_manager.telephone.hangup()
            return

        # Check for Do Not Disturb
        if self.config.do_not_disturb_enabled.get():
            print(f"Rejecting incoming call due to Do Not Disturb: {caller_hash}")
            if self.telephone_manager.telephone:
                # Use a small delay to ensure LXST state is ready for hangup
                threading.Timer(
                    0.5, lambda: self.telephone_manager.telephone.hangup()
                ).start()
            return

        # Check if only allowing calls from contacts
        if self.config.telephone_allow_calls_from_contacts_only.get():
            contact = self.database.contacts.get_contact_by_identity_hash(caller_hash)
            if not contact:
                print(f"Rejecting incoming call from non-contact: {caller_hash}")
                if self.telephone_manager.telephone:
                    threading.Timer(
                        0.5, lambda: self.telephone_manager.telephone.hangup()
                    ).start()
                return

        # Trigger voicemail handling
        self.voicemail_manager.handle_incoming_call(caller_identity)

        print(f"on_incoming_telephone_call: {caller_identity.hash.hex()}")
        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "telephone_ringing",
                    },
                ),
            ),
        )

    def on_telephone_call_established(self, caller_identity: RNS.Identity):
        print(f"on_telephone_call_established: {caller_identity.hash.hex()}")
        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "telephone_call_established",
                    },
                ),
            ),
        )

    def on_telephone_call_ended(self, caller_identity: RNS.Identity):
        # Stop voicemail recording if active
        self.voicemail_manager.stop_recording()

        print(
            f"on_telephone_call_ended: {caller_identity.hash.hex() if caller_identity else 'Unknown'}",
        )

        # Record call history
        if caller_identity:
            remote_identity_hash = caller_identity.hash.hex()
            remote_identity_name = self.get_name_for_identity_hash(remote_identity_hash)

            is_incoming = self.telephone_manager.call_is_incoming
            status_code = self.telephone_manager.call_status_at_end

            status_map = {
                0: "Busy",
                1: "Rejected",
                2: "Calling",
                3: "Available",
                4: "Ringing",
                5: "Connecting",
                6: "Completed",
            }
            status_text = status_map.get(status_code, f"Status {status_code}")

            duration = 0
            if self.telephone_manager.call_start_time:
                duration = int(time.time() - self.telephone_manager.call_start_time)

            self.database.telephone.add_call_history(
                remote_identity_hash=remote_identity_hash,
                remote_identity_name=remote_identity_name,
                is_incoming=is_incoming,
                status=status_text,
                duration_seconds=duration,
                timestamp=time.time(),
            )

            # Trigger missed call notification if it was an incoming call that ended while ringing
            if is_incoming and status_code == 4:
                # Check if we should suppress the notification/websocket message
                # If DND was on, we still record it but maybe skip the noisy websocket?
                # Actually, persistent notification is good.

                self.database.misc.add_notification(
                    type="telephone_missed_call",
                    remote_hash=remote_identity_hash,
                    title="Missed Call",
                    content=f"You missed a call from {remote_identity_name or remote_identity_hash}",
                )

                # Skip websocket broadcast if DND or contacts-only was likely the reason
                is_filtered = False
                if self.config.do_not_disturb_enabled.get():
                    is_filtered = True
                elif self.config.telephone_allow_calls_from_contacts_only.get():
                    contact = self.database.contacts.get_contact_by_identity_hash(
                        remote_identity_hash
                    )
                    if not contact:
                        is_filtered = True

                if not is_filtered:
                    AsyncUtils.run_async(
                        self.websocket_broadcast(
                            json.dumps(
                                {
                                    "type": "telephone_missed_call",
                                    "remote_identity_hash": remote_identity_hash,
                                    "remote_identity_name": remote_identity_name,
                                    "timestamp": time.time(),
                                },
                            ),
                        ),
                    )

        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "telephone_call_ended",
                    },
                ),
            ),
        )

    # web server has shutdown, likely ctrl+c, but if we don't do the following, the script never exits
    async def shutdown(self, app):
        # force close websocket clients
        for websocket_client in self.websocket_clients:
            await websocket_client.close(code=WSCloseCode.GOING_AWAY)

        # stop reticulum
        RNS.Transport.detach_interfaces()
        self.reticulum.exit_handler()
        RNS.exit()

    def run(self, host, port, launch_browser: bool, enable_https: bool = True):
        # create route table
        routes = web.RouteTableDef()

        ssl_context = None
        use_https = enable_https
        if enable_https:
            cert_dir = os.path.join(self.storage_path, "ssl")
            cert_path = os.path.join(cert_dir, "cert.pem")
            key_path = os.path.join(cert_dir, "key.pem")

            try:
                generate_ssl_certificate(cert_path, key_path)
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ssl_context.load_cert_chain(cert_path, key_path)
                print(f"HTTPS enabled with certificate at {cert_path}")
            except Exception as e:
                print(f"Failed to generate SSL certificate: {e}")
                print("Falling back to HTTP")
                use_https = False

        # session secret for encrypted cookies (generate once and store in shared storage)
        session_secret_path = os.path.join(self.storage_dir, "session_secret")
        self.session_secret_key = None

        if os.path.exists(session_secret_path):
            try:
                with open(session_secret_path) as f:
                    self.session_secret_key = f.read().strip()
            except Exception as e:
                print(f"Failed to read session secret from {session_secret_path}: {e}")

        if not self.session_secret_key:
            # try to migrate from current identity config if available
            self.session_secret_key = self.config.auth_session_secret.get()
            if not self.session_secret_key:
                self.session_secret_key = secrets.token_urlsafe(32)

            try:
                with open(session_secret_path, "w") as f:
                    f.write(self.session_secret_key)
            except Exception as e:
                print(f"Failed to write session secret to {session_secret_path}: {e}")

        # ensure it's also in the current config for consistency
        self.config.auth_session_secret.set(self.session_secret_key)

        # authentication middleware
        @web.middleware
        async def auth_middleware(request, handler):
            if not self.auth_enabled:
                return await handler(request)

            path = request.path

            # allow access to auth endpoints and setup page
            public_paths = [
                "/api/v1/status",
                "/api/v1/auth/setup",
                "/api/v1/auth/login",
                "/api/v1/auth/status",
                "/api/v1/auth/logout",
                "/manifest.json",
                "/service-worker.js",
            ]

            # check if path is public
            is_public = any(path.startswith(public) for public in public_paths)

            # check if requesting setup page (index.html will show setup if needed)
            if (
                path == "/"
                or path.startswith("/assets/")
                or path.startswith("/favicons/")
            ):
                is_public = True

            if is_public:
                return await handler(request)

            # check authentication
            try:
                session = await get_session(request)
            except Exception as e:
                print(f"Session decryption failed: {e}")
                # If decryption fails, we must treat as unauthenticated
                if path.startswith("/api/"):
                    return web.json_response(
                        {"error": "Session expired or invalid. Please login again."},
                        status=401,
                    )
                return web.Response(
                    text="Authentication required",
                    status=401,
                    headers={"Content-Type": "text/html"},
                )

            is_authenticated = session.get("authenticated", False)
            session_identity = session.get("identity_hash")

            # Check if authenticated AND matches current identity
            if not is_authenticated or session_identity != self.identity.hash.hex():
                if path.startswith("/api/"):
                    return web.json_response(
                        {"error": "Authentication required"},
                        status=401,
                    )
                return web.Response(
                    text="Authentication required",
                    status=401,
                    headers={"Content-Type": "text/html"},
                )

            return await handler(request)

        # serve index.html
        @routes.get("/")
        async def index(request):
            return web.FileResponse(
                path=get_file_path("public/index.html"),
                headers={
                    # don't allow browser to store page in cache, otherwise new app versions may get stale ui
                    "Cache-Control": "no-cache, no-store",
                },
            )

        # allow serving manifest.json and service-worker.js directly at root
        @routes.get("/manifest.json")
        async def manifest(request):
            return web.FileResponse(get_file_path("public/manifest.json"))

        @routes.get("/service-worker.js")
        async def service_worker(request):
            return web.FileResponse(get_file_path("public/service-worker.js"))

        # serve ping
        @routes.get("/api/v1/status")
        async def status(request):
            return web.json_response(
                {
                    "status": "ok",
                },
            )

        # auth status
        @routes.get("/api/v1/auth/status")
        async def auth_status(request):
            try:
                session = await get_session(request)
                is_authenticated = session.get("authenticated", False)
                session_identity = session.get("identity_hash")

                # Verify that authentication is for the CURRENT active identity
                actually_authenticated = is_authenticated and (
                    session_identity == self.identity.hash.hex()
                )

                return web.json_response(
                    {
                        "auth_enabled": self.auth_enabled,
                        "password_set": self.config.auth_password_hash.get()
                        is not None,
                        "authenticated": actually_authenticated,
                    },
                )
            except Exception as e:
                # Handle decryption failure gracefully by reporting as unauthenticated
                return web.json_response(
                    {
                        "auth_enabled": self.auth_enabled,
                        "password_set": self.config.auth_password_hash.get()
                        is not None,
                        "authenticated": False,
                        "error": str(e),
                    },
                )

        # auth setup
        @routes.post("/api/v1/auth/setup")
        async def auth_setup(request):
            # check if password already set
            if self.config.auth_password_hash.get() is not None:
                return web.json_response(
                    {"error": "Initial setup already completed"},
                    status=403,
                )

            data = await request.json()
            password = data.get("password")

            if not password or len(password) < 8:
                return web.json_response(
                    {"error": "Password must be at least 8 characters long"},
                    status=400,
                )

            # hash password
            password_hash = bcrypt.hashpw(
                password.encode("utf-8"),
                bcrypt.gensalt(),
            ).decode("utf-8")

            # save to config
            self.config.auth_password_hash.set(password_hash)

            # set authenticated in session for THIS identity
            session = await get_session(request)
            session["authenticated"] = True
            session["identity_hash"] = self.identity.hash.hex()

            return web.json_response({"message": "Setup completed successfully"})

        # auth login
        @routes.post("/api/v1/auth/login")
        async def auth_login(request):
            data = await request.json()
            password = data.get("password")

            password_hash = self.config.auth_password_hash.get()
            if password_hash is None:
                return web.json_response(
                    {"error": "Auth not setup"},
                    status=403,
                )

            if not password:
                return web.json_response(
                    {"error": "Password required"},
                    status=400,
                )

            # verify password
            if bcrypt.checkpw(
                password.encode("utf-8"),
                password_hash.encode("utf-8"),
            ):
                # set authenticated in session for THIS identity
                session = await get_session(request)
                session["authenticated"] = True
                session["identity_hash"] = self.identity.hash.hex()
                return web.json_response({"message": "Login successful"})

            return web.json_response(
                {"error": "Invalid password"},
                status=401,
            )

        # auth logout
        @routes.post("/api/v1/auth/logout")
        async def auth_logout(request):
            session = await get_session(request)
            session["authenticated"] = False
            return web.json_response({"message": "Logged out successfully"})

        # fetch com ports
        @routes.get("/api/v1/comports")
        async def comports(request):
            comports = [
                {
                    "device": comport.device,
                    "product": comport.product,
                    "serial_number": comport.serial_number,
                }
                for comport in list_ports.comports()
            ]

            return web.json_response(
                {
                    "comports": comports,
                },
            )

        # fetch reticulum interfaces
        @routes.get("/api/v1/reticulum/interfaces")
        async def reticulum_interfaces(request):
            interfaces = self._get_interfaces_snapshot()

            processed_interfaces = {}
            for interface_name, interface in interfaces.items():
                interface_data = copy.deepcopy(interface)

                # handle sub-interfaces for RNodeMultiInterface
                if interface_data.get("type") == "RNodeMultiInterface":
                    sub_interfaces = []
                    for sub_name, sub_config in interface_data.items():
                        if sub_name not in {
                            "type",
                            "port",
                            "interface_enabled",
                            "selected_interface_mode",
                            "configured_bitrate",
                        }:
                            if isinstance(sub_config, dict):
                                sub_config["name"] = sub_name
                                sub_interfaces.append(sub_config)

                    # add sub-interfaces to the main interface data
                    interface_data["sub_interfaces"] = sub_interfaces

                    for sub in sub_interfaces:
                        del interface_data[sub["name"]]

                processed_interfaces[interface_name] = interface_data

            return web.json_response(
                {
                    "interfaces": processed_interfaces,
                },
            )

        # enable reticulum interface
        @routes.post("/api/v1/reticulum/interfaces/enable")
        async def reticulum_interfaces_enable(request):
            # get request data
            data = await request.json()
            interface_name = data.get("name")

            if interface_name is None or interface_name == "":
                return web.json_response(
                    {
                        "message": "Interface name is required",
                    },
                    status=422,
                )

            # enable interface
            interfaces = self._get_interfaces_section()
            if interface_name not in interfaces:
                return web.json_response(
                    {
                        "message": "Interface not found",
                    },
                    status=404,
                )
            interface = interfaces[interface_name]
            if "enabled" in interface:
                interface["enabled"] = "true"
            if "interface_enabled" in interface:
                interface["interface_enabled"] = "true"

            keys_to_remove = []
            for key, value in interface.items():
                if value is None:
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del interface[key]

            # save config
            if not self._write_reticulum_config():
                return web.json_response(
                    {
                        "message": "Failed to write Reticulum config",
                    },
                    status=500,
                )

            return web.json_response(
                {
                    "message": "Interface is now enabled",
                },
            )

        # disable reticulum interface
        @routes.post("/api/v1/reticulum/interfaces/disable")
        async def reticulum_interfaces_disable(request):
            # get request data
            data = await request.json()
            interface_name = data.get("name")

            if interface_name is None or interface_name == "":
                return web.json_response(
                    {
                        "message": "Interface name is required",
                    },
                    status=422,
                )

            # disable interface
            interfaces = self._get_interfaces_section()
            if interface_name not in interfaces:
                return web.json_response(
                    {
                        "message": "Interface not found",
                    },
                    status=404,
                )
            interface = interfaces[interface_name]
            if "enabled" in interface:
                interface["enabled"] = "false"
            if "interface_enabled" in interface:
                interface["interface_enabled"] = "false"

            keys_to_remove = []
            for key, value in interface.items():
                if value is None:
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del interface[key]

            # save config
            if not self._write_reticulum_config():
                return web.json_response(
                    {
                        "message": "Failed to write Reticulum config",
                    },
                    status=500,
                )

            return web.json_response(
                {
                    "message": "Interface is now disabled",
                },
            )

        # delete reticulum interface
        @routes.post("/api/v1/reticulum/interfaces/delete")
        async def reticulum_interfaces_delete(request):
            # get request data
            data = await request.json()
            interface_name = data.get("name")

            if interface_name is None or interface_name == "":
                return web.json_response(
                    {
                        "message": "Interface name is required",
                    },
                    status=422,
                )

            interfaces = self._get_interfaces_section()
            if interface_name not in interfaces:
                return web.json_response(
                    {
                        "message": "Interface not found",
                    },
                    status=404,
                )

            # delete interface
            del interfaces[interface_name]

            # save config
            if not self._write_reticulum_config():
                return web.json_response(
                    {
                        "message": "Failed to write Reticulum config",
                    },
                    status=500,
                )

            return web.json_response(
                {
                    "message": "Interface has been deleted",
                },
            )

        # add reticulum interface
        @routes.post("/api/v1/reticulum/interfaces/add")
        async def reticulum_interfaces_add(request):
            # get request data
            data = await request.json()
            interface_name = data.get("name")
            interface_type = data.get("type")
            allow_overwriting_interface = data.get("allow_overwriting_interface", False)

            # ensure name is provided
            if interface_name is None or interface_name == "":
                return web.json_response(
                    {
                        "message": "Name is required",
                    },
                    status=422,
                )

            # ensure type name provided
            if interface_type is None or interface_type == "":
                return web.json_response(
                    {
                        "message": "Type is required",
                    },
                    status=422,
                )

            # get existing interfaces
            interfaces = self._get_interfaces_section()

            # ensure name is not for an existing interface, to prevent overwriting
            if allow_overwriting_interface is False and interface_name in interfaces:
                return web.json_response(
                    {
                        "message": "Name is already in use by another interface",
                    },
                    status=422,
                )

            # get existing interface details if available
            interface_details = {}
            if interface_name in interfaces:
                interface_details = interfaces[interface_name]

            # update interface details
            interface_details["type"] = interface_type

            # if interface doesn't have enabled or interface_enabled setting already, enable it by default
            if (
                "enabled" not in interface_details
                and "interface_enabled" not in interface_details
            ):
                interface_details["interface_enabled"] = "true"

            # handle AutoInterface
            if interface_type == "AutoInterface":
                # set optional AutoInterface options
                InterfaceEditor.update_value(interface_details, data, "group_id")
                InterfaceEditor.update_value(
                    interface_details,
                    data,
                    "multicast_address_type",
                )
                InterfaceEditor.update_value(interface_details, data, "devices")
                InterfaceEditor.update_value(interface_details, data, "ignored_devices")
                InterfaceEditor.update_value(interface_details, data, "discovery_scope")
                InterfaceEditor.update_value(interface_details, data, "discovery_port")
                InterfaceEditor.update_value(interface_details, data, "data_port")

            # handle TCPClientInterface
            if interface_type == "TCPClientInterface":
                # ensure target host provided
                interface_target_host = data.get("target_host")
                if interface_target_host is None or interface_target_host == "":
                    return web.json_response(
                        {
                            "message": "Target Host is required",
                        },
                        status=422,
                    )

                # ensure target port provided
                interface_target_port = data.get("target_port")
                if interface_target_port is None or interface_target_port == "":
                    return web.json_response(
                        {
                            "message": "Target Port is required",
                        },
                        status=422,
                    )

                # set required TCPClientInterface options
                interface_details["target_host"] = interface_target_host
                interface_details["target_port"] = interface_target_port

                # set optional TCPClientInterface options
                InterfaceEditor.update_value(interface_details, data, "kiss_framing")
                InterfaceEditor.update_value(interface_details, data, "i2p_tunneled")

            # handle I2P interface
            if interface_type == "I2PInterface":
                interface_details["connectable"] = "True"
                InterfaceEditor.update_value(interface_details, data, "peers")

            # handle tcp server interface
            if interface_type == "TCPServerInterface":
                # ensure listen ip provided
                interface_listen_ip = data.get("listen_ip")
                if interface_listen_ip is None or interface_listen_ip == "":
                    return web.json_response(
                        {
                            "message": "Listen IP is required",
                        },
                        status=422,
                    )

                # ensure listen port provided
                interface_listen_port = data.get("listen_port")
                if interface_listen_port is None or interface_listen_port == "":
                    return web.json_response(
                        {
                            "message": "Listen Port is required",
                        },
                        status=422,
                    )

                # set required TCPServerInterface options
                interface_details["listen_ip"] = interface_listen_ip
                interface_details["listen_port"] = interface_listen_port

                # set optional TCPServerInterface options
                InterfaceEditor.update_value(interface_details, data, "device")
                InterfaceEditor.update_value(interface_details, data, "prefer_ipv6")

            # handle udp interface
            if interface_type == "UDPInterface":
                # ensure listen ip provided
                interface_listen_ip = data.get("listen_ip")
                if interface_listen_ip is None or interface_listen_ip == "":
                    return web.json_response(
                        {
                            "message": "Listen IP is required",
                        },
                        status=422,
                    )

                # ensure listen port provided
                interface_listen_port = data.get("listen_port")
                if interface_listen_port is None or interface_listen_port == "":
                    return web.json_response(
                        {
                            "message": "Listen Port is required",
                        },
                        status=422,
                    )

                # ensure forward ip provided
                interface_forward_ip = data.get("forward_ip")
                if interface_forward_ip is None or interface_forward_ip == "":
                    return web.json_response(
                        {
                            "message": "Forward IP is required",
                        },
                        status=422,
                    )

                # ensure forward port provided
                interface_forward_port = data.get("forward_port")
                if interface_forward_port is None or interface_forward_port == "":
                    return web.json_response(
                        {
                            "message": "Forward Port is required",
                        },
                        status=422,
                    )

                # set required UDPInterface options
                interface_details["listen_ip"] = interface_listen_ip
                interface_details["listen_port"] = interface_listen_port
                interface_details["forward_ip"] = interface_forward_ip
                interface_details["forward_port"] = interface_forward_port

                # set optional UDPInterface options
                InterfaceEditor.update_value(interface_details, data, "device")

            # handle RNodeInterface
            if interface_type == "RNodeInterface":
                # ensure port provided
                interface_port = data.get("port")
                if interface_port is None or interface_port == "":
                    return web.json_response(
                        {
                            "message": "Port is required",
                        },
                        status=422,
                    )

                # ensure frequency provided
                interface_frequency = data.get("frequency")
                if interface_frequency is None or interface_frequency == "":
                    return web.json_response(
                        {
                            "message": "Frequency is required",
                        },
                        status=422,
                    )

                # ensure bandwidth provided
                interface_bandwidth = data.get("bandwidth")
                if interface_bandwidth is None or interface_bandwidth == "":
                    return web.json_response(
                        {
                            "message": "Bandwidth is required",
                        },
                        status=422,
                    )

                # ensure txpower provided
                interface_txpower = data.get("txpower")
                if interface_txpower is None or interface_txpower == "":
                    return web.json_response(
                        {
                            "message": "TX power is required",
                        },
                        status=422,
                    )

                # ensure spreading factor provided
                interface_spreadingfactor = data.get("spreadingfactor")
                if interface_spreadingfactor is None or interface_spreadingfactor == "":
                    return web.json_response(
                        {
                            "message": "Spreading Factor is required",
                        },
                        status=422,
                    )

                # ensure coding rate provided
                interface_codingrate = data.get("codingrate")
                if interface_codingrate is None or interface_codingrate == "":
                    return web.json_response(
                        {
                            "message": "Coding Rate is required",
                        },
                        status=422,
                    )

                # set required RNodeInterface options
                interface_details["port"] = interface_port
                interface_details["frequency"] = interface_frequency
                interface_details["bandwidth"] = interface_bandwidth
                interface_details["txpower"] = interface_txpower
                interface_details["spreadingfactor"] = interface_spreadingfactor
                interface_details["codingrate"] = interface_codingrate

                # set optional RNodeInterface options
                InterfaceEditor.update_value(interface_details, data, "callsign")
                InterfaceEditor.update_value(interface_details, data, "id_interval")
                InterfaceEditor.update_value(
                    interface_details,
                    data,
                    "airtime_limit_long",
                )
                InterfaceEditor.update_value(
                    interface_details,
                    data,
                    "airtime_limit_short",
                )

            # handle RNodeMultiInterface
            if interface_type == "RNodeMultiInterface":
                # required settings
                interface_port = data.get("port")
                sub_interfaces = data.get("sub_interfaces", [])

                # ensure port provided
                if interface_port is None or interface_port == "":
                    return web.json_response(
                        {
                            "message": "Port is required",
                        },
                        status=422,
                    )

                # ensure sub interfaces provided
                if not isinstance(sub_interfaces, list) or not sub_interfaces:
                    return web.json_response(
                        {
                            "message": "At least one sub-interface is required",
                        },
                        status=422,
                    )

                # set required RNodeMultiInterface options
                interface_details["port"] = interface_port

                # remove any existing sub interfaces, which can be found by finding keys that contain a dict value
                # this allows us to replace all sub interfaces with the ones we are about to add, while also ensuring
                # that we do not remove any existing config values from the main interface config
                for key in list(interface_details.keys()):
                    value = interface_details[key]
                    if isinstance(value, dict):
                        del interface_details[key]

                # process each provided sub interface
                required_subinterface_fields = [
                    "name",
                    "frequency",
                    "bandwidth",
                    "txpower",
                    "spreadingfactor",
                    "codingrate",
                    "vport",
                ]
                for idx, sub_interface in enumerate(sub_interfaces):
                    # ensure required fields for sub-interface provided
                    missing_fields = [
                        field
                        for field in required_subinterface_fields
                        if (
                            field not in sub_interface
                            or sub_interface.get(field) is None
                            or sub_interface.get(field) == ""
                        )
                    ]
                    if missing_fields:
                        return web.json_response(
                            {
                                "message": f"Sub-interface {idx + 1} is missing required field(s): {', '.join(missing_fields)}",
                            },
                            status=422,
                        )

                    sub_interface_name = sub_interface.get("name")
                    interface_details[sub_interface_name] = {
                        "interface_enabled": "true",
                        "frequency": int(sub_interface["frequency"]),
                        "bandwidth": int(sub_interface["bandwidth"]),
                        "txpower": int(sub_interface["txpower"]),
                        "spreadingfactor": int(sub_interface["spreadingfactor"]),
                        "codingrate": int(sub_interface["codingrate"]),
                        "vport": int(sub_interface["vport"]),
                    }

                interfaces[interface_name] = interface_details

            # handle SerialInterface, KISSInterface, and AX25KISSInterface
            if interface_type in (
                "SerialInterface",
                "KISSInterface",
                "AX25KISSInterface",
            ):
                # ensure port provided
                interface_port = data.get("port")
                if interface_port is None or interface_port == "":
                    return web.json_response(
                        {
                            "message": "Port is required",
                        },
                        status=422,
                    )

                # set required options
                interface_details["port"] = interface_port

                # set optional options
                InterfaceEditor.update_value(interface_details, data, "speed")
                InterfaceEditor.update_value(interface_details, data, "databits")
                InterfaceEditor.update_value(interface_details, data, "parity")
                InterfaceEditor.update_value(interface_details, data, "stopbits")

                # Handle KISS and AX25KISS specific options
                if interface_type in ("KISSInterface", "AX25KISSInterface"):
                    # set optional options
                    InterfaceEditor.update_value(interface_details, data, "preamble")
                    InterfaceEditor.update_value(interface_details, data, "txtail")
                    InterfaceEditor.update_value(interface_details, data, "persistence")
                    InterfaceEditor.update_value(interface_details, data, "slottime")
                    InterfaceEditor.update_value(interface_details, data, "callsign")
                    InterfaceEditor.update_value(interface_details, data, "ssid")

            # FIXME: move to own sections
            # RNode Airtime limits and station ID
            InterfaceEditor.update_value(interface_details, data, "callsign")
            InterfaceEditor.update_value(interface_details, data, "id_interval")
            InterfaceEditor.update_value(interface_details, data, "airtime_limit_long")
            InterfaceEditor.update_value(interface_details, data, "airtime_limit_short")

            # handle Pipe Interface
            if interface_type == "PipeInterface":
                # ensure command provided
                interface_command = data.get("command")
                if interface_command is None or interface_command == "":
                    return web.json_response(
                        {
                            "message": "Command is required",
                        },
                        status=422,
                    )

                # ensure command provided
                interface_respawn_delay = data.get("respawn_delay")
                if interface_respawn_delay is None or interface_respawn_delay == "":
                    return web.json_response(
                        {
                            "message": "Respawn delay is required",
                        },
                        status=422,
                    )

                # set required options
                interface_details["command"] = interface_command
                interface_details["respawn_delay"] = interface_respawn_delay

            # set common interface options
            InterfaceEditor.update_value(interface_details, data, "bitrate")
            InterfaceEditor.update_value(interface_details, data, "mode")
            InterfaceEditor.update_value(interface_details, data, "network_name")
            InterfaceEditor.update_value(interface_details, data, "passphrase")
            InterfaceEditor.update_value(interface_details, data, "ifac_size")

            # merge new interface into existing interfaces
            interfaces[interface_name] = interface_details
            # save config
            if not self._write_reticulum_config():
                return web.json_response(
                    {
                        "message": "Failed to write Reticulum config",
                    },
                    status=500,
                )

            if allow_overwriting_interface:
                return web.json_response(
                    {
                        "message": "Interface has been saved. Please restart MeshChat for these changes to take effect.",
                    },
                )
            return web.json_response(
                {
                    "message": "Interface has been added. Please restart MeshChat for these changes to take effect.",
                },
            )

        # export interfaces
        @routes.post("/api/v1/reticulum/interfaces/export")
        async def export_interfaces(request):
            try:
                # get request data
                selected_interface_names = None
                try:
                    data = await request.json()
                    selected_interface_names = data.get("selected_interface_names")
                except Exception as e:
                    # request data was not json, but we don't care
                    print(f"Request data was not JSON: {e}")

                # format interfaces for export
                output = []
                interfaces = self._get_interfaces_snapshot()
                for interface_name, interface in interfaces.items():
                    # skip interface if not selected
                    if (
                        selected_interface_names is not None
                        and selected_interface_names != ""
                    ):
                        if interface_name not in selected_interface_names:
                            continue

                    # add interface to output
                    output.append(f"[[{interface_name}]]")
                    for key, value in interface.items():
                        if not isinstance(value, dict):
                            output.append(f"    {key} = {value}")
                    output.append("")

                    # Handle sub-interfaces for RNodeMultiInterface
                    if interface.get("type") == "RNodeMultiInterface":
                        for sub_name, sub_config in interface.items():
                            if sub_name in {"type", "port", "interface_enabled"}:
                                continue
                            if isinstance(sub_config, dict):
                                output.append(f"  [[[{sub_name}]]]")
                                for sub_key, sub_value in sub_config.items():
                                    output.append(f"      {sub_key} = {sub_value}")
                                output.append("")

                return web.Response(
                    text="\n".join(output),
                    content_type="text/plain",
                    headers={
                        "Content-Disposition": "attachment; filename=meshchat_interfaces",
                    },
                )

            except Exception as e:
                return web.json_response(
                    {
                        "message": f"Failed to export interfaces: {e!s}",
                    },
                    status=500,
                )

        # preview importable interfaces
        @routes.post("/api/v1/reticulum/interfaces/import-preview")
        async def import_interfaces_preview(request):
            try:
                # get request data
                data = await request.json()
                config = data.get("config")

                # parse interfaces from config
                interfaces = InterfaceConfigParser.parse(config)

                return web.json_response(
                    {
                        "interfaces": interfaces,
                    },
                )

            except Exception as e:
                return web.json_response(
                    {
                        "message": f"Failed to parse config file: {e!s}",
                    },
                    status=500,
                )

        # import interfaces from config
        @routes.post("/api/v1/reticulum/interfaces/import")
        async def import_interfaces(request):
            try:
                # get request data
                data = await request.json()
                config = data.get("config")
                selected_interface_names = data.get("selected_interface_names")

                # parse interfaces from config
                interfaces = InterfaceConfigParser.parse(config)

                # find selected interfaces
                selected_interfaces = [
                    interface
                    for interface in interfaces
                    if interface["name"] in selected_interface_names
                ]

                # convert interfaces to object
                interface_config = {}
                for interface in selected_interfaces:
                    # add interface and keys/values
                    interface_name = interface["name"]
                    interface_config[interface_name] = {}
                    for key, value in interface.items():
                        interface_config[interface_name][key] = value

                    # unset name which isn't part of the config
                    del interface_config[interface_name]["name"]

                    # force imported interface to be enabled by default
                    interface_config[interface_name]["interface_enabled"] = "true"

                    # remove enabled config value in favour of interface_enabled
                    if "enabled" in interface_config[interface_name]:
                        del interface_config[interface_name]["enabled"]

                # update reticulum config with new interfaces
                interfaces = self._get_interfaces_section()
                interfaces.update(interface_config)
                if not self._write_reticulum_config():
                    return web.json_response(
                        {
                            "message": "Failed to write Reticulum config",
                        },
                        status=500,
                    )

                return web.json_response(
                    {
                        "message": "Interfaces imported successfully",
                    },
                )

            except Exception as e:
                return web.json_response(
                    {
                        "message": f"Failed to import interfaces: {e!s}",
                    },
                    status=500,
                )

        # handle websocket clients
        @routes.get("/ws")
        async def ws(request):
            # prepare websocket response
            websocket_response = web.WebSocketResponse(
                # set max message size accepted by server to 50 megabytes
                max_msg_size=50 * 1024 * 1024,
            )
            await websocket_response.prepare(request)

            # add client to connected clients list
            self.websocket_clients.append(websocket_response)

            # send config to all clients
            await self.send_config_to_websocket_clients()

            # handle websocket messages until disconnected
            async for msg in websocket_response:
                msg: WSMessage = msg
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self.on_websocket_data_received(websocket_response, data)
                    except Exception as e:
                        # ignore errors while handling message
                        print("failed to process client message")
                        print(e)
                elif msg.type == WSMsgType.ERROR:
                    # ignore errors while handling message
                    print(f"ws connection error {websocket_response.exception()}")

            # websocket closed
            self.websocket_clients.remove(websocket_response)

            return websocket_response

        # get app info
        @routes.get("/api/v1/app/info")
        async def app_info(request):
            # Get memory usage for current process
            process = psutil.Process()
            memory_info = process.memory_info()

            # Get network I/O statistics
            net_io = psutil.net_io_counters()

            # Get total paths
            path_table = self.reticulum.get_path_table()
            total_paths = len(path_table)

            # Calculate announce rates
            current_time = time.time()
            announces_per_second = len(
                [t for t in self.announce_timestamps if current_time - t <= 1.0],
            )
            announces_per_minute = len(
                [t for t in self.announce_timestamps if current_time - t <= 60.0],
            )
            announces_per_hour = len(
                [t for t in self.announce_timestamps if current_time - t <= 3600.0],
            )

            # Clean up old announce timestamps (older than 1 hour)
            self.announce_timestamps = [
                t for t in self.announce_timestamps if current_time - t <= 3600.0
            ]

            # Calculate average download speed
            avg_download_speed_bps = None
            if self.download_speeds:
                total_bytes = sum(size for size, _ in self.download_speeds)
                total_duration = sum(duration for _, duration in self.download_speeds)
                if total_duration > 0:
                    avg_download_speed_bps = total_bytes / total_duration

            db_files = self._get_database_file_stats()

            return web.json_response(
                {
                    "app_info": {
                        "version": self.get_app_version(),
                        "lxmf_version": LXMF.__version__,
                        "rns_version": RNS.__version__,
                        "python_version": platform.python_version(),
                        "storage_path": self.storage_path,
                        "database_path": self.database_path,
                        "database_file_size": db_files["main_bytes"],
                        "database_files": db_files,
                        "sqlite": {
                            "journal_mode": self._get_pragma_value(
                                "journal_mode",
                                "unknown",
                            ),
                            "synchronous": self._get_pragma_value(
                                "synchronous",
                                None,
                            ),
                            "wal_autocheckpoint": self._get_pragma_value(
                                "wal_autocheckpoint",
                                None,
                            ),
                            "busy_timeout": self._get_pragma_value(
                                "busy_timeout",
                                None,
                            ),
                        },
                        "reticulum_config_path": self.reticulum.configpath,
                        "is_connected_to_shared_instance": self.reticulum.is_connected_to_shared_instance,
                        "is_transport_enabled": self.reticulum.transport_enabled(),
                        "memory_usage": {
                            "rss": memory_info.rss,  # Resident Set Size (bytes)
                            "vms": memory_info.vms,  # Virtual Memory Size (bytes)
                        },
                        "network_stats": {
                            "bytes_sent": net_io.bytes_sent,
                            "bytes_recv": net_io.bytes_recv,
                            "packets_sent": net_io.packets_sent,
                            "packets_recv": net_io.packets_recv,
                        },
                        "reticulum_stats": {
                            "total_paths": total_paths,
                            "announces_per_second": announces_per_second,
                            "announces_per_minute": announces_per_minute,
                            "announces_per_hour": announces_per_hour,
                        },
                        "download_stats": {
                            "avg_download_speed_bps": avg_download_speed_bps,
                        },
                        "user_guidance": self.build_user_guidance_messages(),
                    },
                },
            )

        @routes.get("/api/v1/database/health")
        async def database_health(request):
            try:
                return web.json_response(
                    {
                        "database": self.get_database_health_snapshot(),
                    },
                )
            except Exception as e:
                return web.json_response(
                    {
                        "message": f"Failed to fetch database health: {e!s}",
                    },
                    status=500,
                )

        @routes.post("/api/v1/database/vacuum")
        async def database_vacuum(request):
            try:
                result = self.run_database_vacuum()
                return web.json_response(
                    {
                        "message": "Database vacuum completed",
                        "database": result,
                    },
                )
            except Exception as e:
                return web.json_response(
                    {
                        "message": f"Failed to vacuum database: {e!s}",
                    },
                    status=500,
                )

        @routes.post("/api/v1/database/recover")
        async def database_recover(request):
            try:
                result = self.run_database_recovery()
                return web.json_response(
                    {
                        "message": "Database recovery routine completed",
                        "database": result,
                    },
                )
            except Exception as e:
                return web.json_response(
                    {
                        "message": f"Failed to recover database: {e!s}",
                    },
                    status=500,
                )

        @routes.post("/api/v1/database/backup")
        async def database_backup(request):
            try:
                result = self.backup_database()
                return web.json_response(
                    {
                        "message": "Database backup created",
                        "backup": result,
                    },
                )
            except Exception as e:
                return web.json_response(
                    {
                        "message": f"Failed to create database backup: {e!s}",
                    },
                    status=500,
                )

        @routes.get("/api/v1/database/backup/download")
        async def database_backup_download(request):
            try:
                backup_info = self.backup_database()
                file_path = backup_info["path"]
                with open(file_path, "rb") as f:
                    data = f.read()
                return web.Response(
                    body=data,
                    headers={
                        "Content-Type": "application/zip",
                        "Content-Disposition": f'attachment; filename="{os.path.basename(file_path)}"',
                    },
                )
            except Exception as e:
                return web.json_response(
                    {
                        "message": f"Failed to create database backup: {e!s}",
                    },
                    status=500,
                )

        @routes.get("/api/v1/identity/backup/download")
        async def identity_backup_download(request):
            try:
                info = self.backup_identity()
                with open(info["path"], "rb") as f:
                    data = f.read()
                return web.Response(
                    body=data,
                    headers={
                        "Content-Type": "application/octet-stream",
                        "Content-Disposition": 'attachment; filename="identity"',
                    },
                )
            except Exception as e:
                return web.json_response(
                    {
                        "message": f"Failed to create identity backup: {e!s}",
                    },
                    status=500,
                )

        @routes.get("/api/v1/identity/backup/base32")
        async def identity_backup_base32(request):
            try:
                return web.json_response(
                    {
                        "identity_base32": self.backup_identity_base32(),
                    },
                )
            except Exception as e:
                return web.json_response(
                    {
                        "message": f"Failed to export identity: {e!s}",
                    },
                    status=500,
                )

        @routes.post("/api/v1/database/restore")
        async def database_restore(request):
            try:
                reader = await request.multipart()
                field = await reader.next()
                if field is None or field.name != "file":
                    return web.json_response(
                        {
                            "message": "Restore file is required",
                        },
                        status=400,
                    )

                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    while True:
                        chunk = await field.read_chunk()
                        if not chunk:
                            break
                        tmp.write(chunk)
                    temp_path = tmp.name

                result = self.restore_database(temp_path)
                os.remove(temp_path)

                return web.json_response(
                    {
                        "message": "Database restored successfully",
                        "database": result,
                    },
                )
            except Exception as e:
                return web.json_response(
                    {
                        "message": f"Failed to restore database: {e!s}",
                    },
                    status=500,
                )

        @routes.post("/api/v1/identity/restore")
        async def identity_restore(request):
            try:
                content_type = request.headers.get("Content-Type", "")
                # multipart file upload
                if "multipart/form-data" in content_type:
                    reader = await request.multipart()
                    field = await reader.next()
                    if field is None or field.name != "file":
                        return web.json_response(
                            {"message": "Identity file is required"},
                            status=400,
                        )
                    with tempfile.NamedTemporaryFile(delete=False) as tmp:
                        while True:
                            chunk = await field.read_chunk()
                            if not chunk:
                                break
                            tmp.write(chunk)
                        temp_path = tmp.name
                    with open(temp_path, "rb") as f:
                        identity_bytes = f.read()
                    os.remove(temp_path)
                    result = self.restore_identity_from_bytes(identity_bytes)
                else:
                    data = await request.json()
                    base32_value = data.get("base32")
                    if not base32_value:
                        return web.json_response(
                            {"message": "base32 value is required"},
                            status=400,
                        )
                    result = self.restore_identity_from_base32(base32_value)

                return web.json_response(
                    {
                        "message": "Identity restored. Restart app to use the new identity.",
                        "identity": result,
                    },
                )
            except Exception as e:
                return web.json_response(
                    {
                        "message": f"Failed to restore identity: {e!s}",
                    },
                    status=500,
                )

        @routes.get("/api/v1/identities")
        async def identities_list(request):
            try:
                return web.json_response(
                    {
                        "identities": self.list_identities(),
                    },
                )
            except Exception as e:
                return web.json_response(
                    {
                        "message": f"Failed to list identities: {e!s}",
                    },
                    status=500,
                )

        @routes.post("/api/v1/identities/create")
        async def identities_create(request):
            try:
                data = await request.json()
                display_name = data.get("display_name")
                result = self.create_identity(display_name)
                return web.json_response(
                    {
                        "message": "Identity created successfully",
                        "identity": result,
                    },
                )
            except Exception as e:
                return web.json_response(
                    {
                        "message": f"Failed to create identity: {e!s}",
                    },
                    status=500,
                )

        @routes.delete("/api/v1/identities/{identity_hash}")
        async def identities_delete(request):
            try:
                identity_hash = request.match_info.get("identity_hash")
                if self.delete_identity(identity_hash):
                    return web.json_response(
                        {
                            "message": "Identity deleted successfully",
                        },
                    )
                return web.json_response(
                    {
                        "message": "Identity not found",
                    },
                    status=404,
                )
            except Exception as e:
                return web.json_response(
                    {
                        "message": f"Failed to delete identity: {e!s}",
                    },
                    status=500,
                )

        @routes.post("/api/v1/identities/switch")
        async def identities_switch(request):
            try:
                data = await request.json()
                identity_hash = data.get("identity_hash")

                # attempt hotswap first
                success = await self.hotswap_identity(identity_hash)

                if success:
                    return web.json_response(
                        {
                            "message": "Identity switched successfully.",
                            "hotswapped": True,
                        },
                    )
                # fallback to restart if hotswap failed
                # (this part should probably be unreachable if hotswap is reliable)
                main_identity_file = self.identity_file_path or os.path.join(
                    self.storage_dir, "identity"
                )
                identity_dir = os.path.join(
                    self.storage_dir, "identities", identity_hash
                )
                identity_file = os.path.join(identity_dir, "identity")
                import shutil

                shutil.copy2(identity_file, main_identity_file)

                def restart():
                    import os
                    import sys
                    import time

                    time.sleep(1)
                    try:
                        os.execv(sys.executable, [sys.executable] + sys.argv)
                    except Exception as e:
                        print(f"Failed to restart: {e}")
                        os._exit(0)

                import threading

                threading.Thread(target=restart).start()

                return web.json_response(
                    {
                        "message": "Identity switch scheduled. Application will restart.",
                        "hotswapped": False,
                        "should_restart": True,
                    },
                )
            except Exception as e:
                return web.json_response(
                    {
                        "message": f"Failed to switch identity: {e!s}",
                    },
                    status=500,
                )

        # get config
        @routes.get("/api/v1/config")
        async def config_get(request):
            return web.json_response(
                {
                    "config": self.get_config_dict(),
                },
            )

        # update config
        @routes.patch("/api/v1/config")
        async def config_update(request):
            # get request body as json
            data = await request.json()

            # update config
            await self.update_config(data)

            return web.json_response(
                {
                    "config": self.get_config_dict(),
                },
            )

        # enable transport mode
        @routes.post("/api/v1/reticulum/enable-transport")
        async def reticulum_enable_transport(request):
            # enable transport mode
            reticulum_config = self._get_reticulum_section()
            reticulum_config["enable_transport"] = True
            if not self._write_reticulum_config():
                return web.json_response(
                    {
                        "message": "Failed to write Reticulum config",
                    },
                    status=500,
                )

            return web.json_response(
                {
                    "message": "Transport has been enabled. MeshChat must be restarted for this change to take effect.",
                },
            )

        # disable transport mode
        @routes.post("/api/v1/reticulum/disable-transport")
        async def reticulum_disable_transport(request):
            # disable transport mode
            reticulum_config = self._get_reticulum_section()
            reticulum_config["enable_transport"] = False
            if not self._write_reticulum_config():
                return web.json_response(
                    {
                        "message": "Failed to write Reticulum config",
                    },
                    status=500,
                )

            return web.json_response(
                {
                    "message": "Transport has been disabled. MeshChat must be restarted for this change to take effect.",
                },
            )

        # serve telephone status
        @routes.get("/api/v1/telephone/status")
        async def telephone_status(request):
            # make sure telephone is enabled
            if self.telephone_manager.telephone is None:
                return web.json_response(
                    {
                        "enabled": False,
                        "message": "Telephone is disabled",
                    },
                )

            # get active call info
            active_call = None
            telephone_active_call = self.telephone_manager.telephone.active_call
            if telephone_active_call is not None:
                # Filter out incoming calls if DND or contacts-only is active and call is ringing
                is_ringing = self.telephone_manager.telephone.call_status == 4
                if telephone_active_call.is_incoming and is_ringing:
                    if self.config.do_not_disturb_enabled.get():
                        # Don't report active call if DND is on and it's ringing
                        telephone_active_call = None
                    elif self.config.telephone_allow_calls_from_contacts_only.get():
                        caller_hash = (
                            telephone_active_call.get_remote_identity().hash.hex()
                        )
                        contact = self.database.contacts.get_contact_by_identity_hash(
                            caller_hash
                        )
                        if not contact:
                            # Don't report active call if contacts-only is on and caller is not a contact
                            telephone_active_call = None

            if telephone_active_call is not None:
                # get remote identity hash
                remote_identity_hash = None
                remote_identity_name = None
                remote_icon = None
                remote_identity = telephone_active_call.get_remote_identity()
                if remote_identity is not None:
                    remote_identity_hash = remote_identity.hash.hex()
                    remote_identity_name = self.get_name_for_identity_hash(
                        remote_identity_hash,
                    )

                    # get lxmf destination hash to look up icon
                    lxmf_destination_hash = RNS.Destination.hash(
                        remote_identity,
                        "lxmf",
                        "delivery",
                    ).hex()
                    remote_icon = self.database.misc.get_user_icon(
                        lxmf_destination_hash
                    )

                active_call = {
                    "hash": telephone_active_call.hash.hex(),
                    "status": self.telephone_manager.telephone.call_status,
                    "is_incoming": telephone_active_call.is_incoming,
                    "is_outgoing": telephone_active_call.is_outgoing,
                    "remote_identity_hash": remote_identity_hash,
                    "remote_identity_name": remote_identity_name,
                    "remote_icon": dict(remote_icon) if remote_icon else None,
                    "audio_profile_id": self.telephone_manager.telephone.transmit_codec.profile
                    if hasattr(
                        self.telephone_manager.telephone.transmit_codec,
                        "profile",
                    )
                    else None,
                    "tx_packets": getattr(telephone_active_call, "tx", 0),
                    "rx_packets": getattr(telephone_active_call, "rx", 0),
                    "tx_bytes": getattr(telephone_active_call, "txbytes", 0),
                    "rx_bytes": getattr(telephone_active_call, "rxbytes", 0),
                    "is_mic_muted": self.telephone_manager.telephone.transmit_muted,
                    "is_speaker_muted": self.telephone_manager.telephone.receive_muted,
                    "is_voicemail": self.voicemail_manager.is_recording,
                    "call_start_time": self.telephone_manager.call_start_time,
                    "is_contact": bool(
                        self.database.contacts.get_contact_by_identity_hash(
                            remote_identity_hash
                        )
                    )
                    if remote_identity_hash
                    else False,
                }

            return web.json_response(
                {
                    "enabled": True,
                    "is_busy": self.telephone_manager.telephone.busy,
                    "call_status": self.telephone_manager.telephone.call_status,
                    "active_call": active_call,
                    "is_mic_muted": self.telephone_manager.telephone.transmit_muted,
                    "is_speaker_muted": self.telephone_manager.telephone.receive_muted,
                    "voicemail": {
                        "is_recording": self.voicemail_manager.is_recording,
                        "unread_count": self.database.voicemails.get_unread_count(),
                    },
                },
            )

        # answer incoming telephone call
        @routes.get("/api/v1/telephone/answer")
        async def telephone_answer(request):
            # get incoming caller identity
            active_call = self.telephone_manager.telephone.active_call
            if not active_call:
                return web.json_response({"message": "No active call"}, status=404)

            caller_identity = active_call.get_remote_identity()

            # answer call
            await asyncio.to_thread(
                self.telephone_manager.telephone.answer,
                caller_identity,
            )

            return web.json_response(
                {
                    "message": "Answering call...",
                },
            )

        # hangup active telephone call
        @routes.get("/api/v1/telephone/hangup")
        async def telephone_hangup(request):
            await asyncio.to_thread(self.telephone_manager.telephone.hangup)
            return web.json_response(
                {
                    "message": "Hanging up call...",
                },
            )

        # send active call to voicemail
        @routes.get("/api/v1/telephone/send-to-voicemail")
        async def telephone_send_to_voicemail(request):
            active_call = self.telephone_manager.telephone.active_call
            if not active_call:
                return web.json_response({"message": "No active call"}, status=404)

            caller_identity = active_call.get_remote_identity()
            if not caller_identity:
                return web.json_response({"message": "No remote identity"}, status=400)

            # trigger voicemail session
            await asyncio.to_thread(
                self.voicemail_manager.start_voicemail_session,
                caller_identity,
            )

            return web.json_response(
                {
                    "message": "Call sent to voicemail",
                },
            )

        # mute/unmute transmit
        @routes.get("/api/v1/telephone/mute-transmit")
        async def telephone_mute_transmit(request):
            await asyncio.to_thread(self.telephone_manager.telephone.mute_transmit)
            return web.json_response({"message": "Microphone muted"})

        @routes.get("/api/v1/telephone/unmute-transmit")
        async def telephone_unmute_transmit(request):
            await asyncio.to_thread(self.telephone_manager.telephone.unmute_transmit)
            return web.json_response({"message": "Microphone unmuted"})

        # mute/unmute receive
        @routes.get("/api/v1/telephone/mute-receive")
        async def telephone_mute_receive(request):
            await asyncio.to_thread(self.telephone_manager.telephone.mute_receive)
            return web.json_response({"message": "Speaker muted"})

        @routes.get("/api/v1/telephone/unmute-receive")
        async def telephone_unmute_receive(request):
            await asyncio.to_thread(self.telephone_manager.telephone.unmute_receive)
            return web.json_response({"message": "Speaker unmuted"})

        # get call history
        @routes.get("/api/v1/telephone/history")
        async def telephone_history(request):
            limit = int(request.query.get("limit", 10))
            offset = int(request.query.get("offset", 0))
            search = request.query.get("search", None)
            history = self.database.telephone.get_call_history(
                search=search,
                limit=limit,
                offset=offset,
            )

            call_history = []
            for row in history:
                d = dict(row)
                remote_identity_hash = d.get("remote_identity_hash")
                if remote_identity_hash:
                    lxmf_hash = self.get_lxmf_destination_hash_for_identity_hash(
                        remote_identity_hash
                    )
                    if lxmf_hash:
                        icon = self.database.misc.get_user_icon(lxmf_hash)
                        if icon:
                            d["remote_icon"] = dict(icon)
                    d["is_contact"] = bool(
                        self.database.contacts.get_contact_by_identity_hash(
                            remote_identity_hash
                        )
                    )
                call_history.append(d)

            return web.json_response(
                {
                    "call_history": call_history,
                },
            )

        # clear call history
        @routes.delete("/api/v1/telephone/history")
        async def telephone_history_clear(request):
            self.database.telephone.clear_call_history()
            return web.json_response({"message": "ok"})

        # switch audio profile
        @routes.get("/api/v1/telephone/switch-audio-profile/{profile_id}")
        async def telephone_switch_audio_profile(request):
            profile_id = request.match_info.get("profile_id")
            try:
                await asyncio.to_thread(
                    self.telephone_manager.telephone.switch_profile,
                    int(profile_id),
                )
                return web.json_response(
                    {"message": f"Switched to profile {profile_id}"},
                )
            except Exception as e:
                return web.json_response({"message": str(e)}, status=500)

        # initiate a telephone call
        @routes.get("/api/v1/telephone/call/{identity_hash}")
        async def telephone_call(request):
            # make sure telephone enabled
            if self.telephone_manager.telephone is None:
                return web.json_response(
                    {
                        "message": "Telephone has been disabled.",
                    },
                    status=503,
                )

            # get path params
            identity_hash_hex = request.match_info.get("identity_hash", "")
            timeout_seconds = int(request.query.get("timeout", 15))

            # convert hash to bytes
            identity_hash_bytes = bytes.fromhex(identity_hash_hex)

            # try to find identity
            destination_identity = self.recall_identity(identity_hash_hex)

            # if identity not found, try to resolve it by requesting a path
            if destination_identity is None:
                # determine identity hash
                # if the provided hash is a known destination, get its identity hash
                announce = self.database.announces.get_announce_by_hash(
                    identity_hash_hex,
                )
                if announce:
                    identity_hash_bytes = bytes.fromhex(announce["identity_hash"])

                # calculate telephony destination hash
                telephony_destination_hash = (
                    RNS.Destination.hash_from_name_and_identity(
                        f"{LXST.APP_NAME}.telephony",
                        identity_hash_bytes,
                    )
                )

                # request path to telephony destination
                if not RNS.Transport.has_path(telephony_destination_hash):
                    print(
                        f"Requesting path to telephony destination: {telephony_destination_hash.hex()}",
                    )
                    RNS.Transport.request_path(telephony_destination_hash)

                    # wait for path
                    timeout_after_seconds = time.time() + timeout_seconds
                    while (
                        not RNS.Transport.has_path(telephony_destination_hash)
                        and time.time() < timeout_after_seconds
                    ):
                        await asyncio.sleep(0.1)

                # try to recall again now that we might have a path/announce
                destination_identity = self.recall_identity(identity_hash_hex)
                if destination_identity is None:
                    # try recalling by telephony destination hash
                    destination_identity = self.recall_identity(
                        telephony_destination_hash.hex(),
                    )

            # ensure identity was found
            if destination_identity is None:
                return web.json_response(
                    {
                        "message": "Call Failed: Destination identity not found.",
                    },
                    status=503,
                )

            # initiate call
            await asyncio.to_thread(
                self.telephone_manager.telephone.call,
                destination_identity,
            )

            return web.json_response(
                {
                    "message": "Calling...",
                },
            )

        # serve list of available audio profiles
        @routes.get("/api/v1/telephone/audio-profiles")
        async def telephone_audio_profiles(request):
            from LXST.Primitives.Telephony import Profiles

            # get audio profiles
            audio_profiles = []
            for available_profile in Profiles.available_profiles():
                audio_profiles.append(
                    {
                        "id": available_profile,
                        "name": Profiles.profile_name(available_profile),
                    },
                )

            return web.json_response(
                {
                    "default_audio_profile_id": Profiles.DEFAULT_PROFILE,
                    "audio_profiles": audio_profiles,
                },
            )

        # voicemail status
        @routes.get("/api/v1/telephone/voicemail/status")
        async def telephone_voicemail_status(request):
            greeting_path = os.path.join(
                self.voicemail_manager.greetings_dir,
                "greeting.opus",
            )
            return web.json_response(
                {
                    "has_espeak": self.voicemail_manager.has_espeak,
                    "has_ffmpeg": self.voicemail_manager.has_ffmpeg,
                    "is_recording": self.voicemail_manager.is_recording,
                    "is_greeting_recording": self.voicemail_manager.is_greeting_recording,
                    "has_greeting": os.path.exists(greeting_path),
                },
            )

        # start recording greeting from mic
        @routes.post("/api/v1/telephone/voicemail/greeting/record/start")
        async def telephone_voicemail_greeting_record_start(request):
            self.voicemail_manager.start_greeting_recording()
            return web.json_response({"message": "Started recording greeting"})

        # stop recording greeting from mic
        @routes.post("/api/v1/telephone/voicemail/greeting/record/stop")
        async def telephone_voicemail_greeting_record_stop(request):
            self.voicemail_manager.stop_greeting_recording()
            return web.json_response({"message": "Stopped recording greeting"})

        # list voicemails
        @routes.get("/api/v1/telephone/voicemails")
        async def telephone_voicemails(request):
            search = request.query.get("search")
            limit = int(request.query.get("limit", 50))
            offset = int(request.query.get("offset", 0))
            voicemails_rows = self.database.voicemails.get_voicemails(
                search=search,
                limit=limit,
                offset=offset,
            )

            voicemails = []
            for row in voicemails_rows:
                d = dict(row)
                remote_identity_hash = d.get("remote_identity_hash")
                if remote_identity_hash:
                    lxmf_hash = self.get_lxmf_destination_hash_for_identity_hash(
                        remote_identity_hash
                    )
                    if lxmf_hash:
                        icon = self.database.misc.get_user_icon(lxmf_hash)
                        if icon:
                            d["remote_icon"] = dict(icon)
                voicemails.append(d)

            return web.json_response(
                {
                    "voicemails": voicemails,
                    "unread_count": self.database.voicemails.get_unread_count(),
                },
            )

        # mark voicemail as read
        @routes.post("/api/v1/telephone/voicemails/{id}/read")
        async def telephone_voicemail_mark_read(request):
            voicemail_id = request.match_info.get("id")
            self.database.voicemails.mark_as_read(voicemail_id)
            return web.json_response({"message": "Voicemail marked as read"})

        # delete voicemail
        @routes.delete("/api/v1/telephone/voicemails/{id}")
        async def telephone_voicemail_delete(request):
            voicemail_id = request.match_info.get("id")
            voicemail = self.database.voicemails.get_voicemail(voicemail_id)
            if voicemail:
                filepath = os.path.join(
                    self.voicemail_manager.recordings_dir,
                    voicemail["filename"],
                )
                if os.path.exists(filepath):
                    os.remove(filepath)
                self.database.voicemails.delete_voicemail(voicemail_id)
                return web.json_response({"message": "Voicemail deleted"})
            return web.json_response({"message": "Voicemail not found"}, status=404)

        # serve greeting audio
        @routes.get("/api/v1/telephone/voicemail/greeting/audio")
        async def telephone_voicemail_greeting_audio(request):
            filepath = os.path.join(
                self.voicemail_manager.greetings_dir,
                "greeting.opus",
            )
            if os.path.exists(filepath):
                return web.FileResponse(filepath)
            return web.json_response(
                {"message": "Greeting audio not found"},
                status=404,
            )

        # serve voicemail audio
        @routes.get("/api/v1/telephone/voicemails/{id}/audio")
        async def telephone_voicemail_audio(request):
            voicemail_id = request.match_info.get("id")
            voicemail = self.database.voicemails.get_voicemail(voicemail_id)
            if voicemail:
                filepath = os.path.join(
                    self.voicemail_manager.recordings_dir,
                    voicemail["filename"],
                )
                if os.path.exists(filepath):
                    return web.FileResponse(filepath)
                RNS.log(
                    f"Voicemail: Recording file missing for ID {voicemail_id}: {filepath}",
                    RNS.LOG_ERROR,
                )
            return web.json_response(
                {"message": "Voicemail audio not found"},
                status=404,
            )

        # generate greeting
        @routes.post("/api/v1/telephone/voicemail/generate-greeting")
        async def telephone_voicemail_generate_greeting(request):
            try:
                text = self.config.voicemail_greeting.get()
                path = await asyncio.to_thread(
                    self.voicemail_manager.generate_greeting,
                    text,
                )
                return web.json_response(
                    {"message": "Greeting generated", "path": path},
                )
            except Exception as e:
                return web.json_response({"message": str(e)}, status=500)

        # upload greeting
        @routes.post("/api/v1/telephone/voicemail/greeting/upload")
        async def telephone_voicemail_greeting_upload(request):
            try:
                reader = await request.multipart()
                field = await reader.next()
                if field.name != "file":
                    return web.json_response(
                        {"message": "File field required"},
                        status=400,
                    )

                filename = field.filename
                extension = os.path.splitext(filename)[1].lower()
                if extension not in [".mp3", ".ogg", ".wav", ".m4a", ".flac"]:
                    return web.json_response(
                        {"message": f"Unsupported file type: {extension}"},
                        status=400,
                    )

                # Save temp file
                with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as f:
                    temp_path = f.name
                    while True:
                        chunk = await field.read_chunk()
                        if not chunk:
                            break
                        f.write(chunk)

                try:
                    # Convert to greeting
                    path = await asyncio.to_thread(
                        self.voicemail_manager.convert_to_greeting,
                        temp_path,
                    )
                    return web.json_response(
                        {"message": "Greeting uploaded and converted", "path": path},
                    )
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

            except Exception as e:
                return web.json_response({"message": str(e)}, status=500)

        # delete greeting
        @routes.delete("/api/v1/telephone/voicemail/greeting")
        async def telephone_voicemail_greeting_delete(request):
            try:
                self.voicemail_manager.remove_greeting()
                return web.json_response({"message": "Greeting deleted"})
            except Exception as e:
                return web.json_response({"message": str(e)}, status=500)

        # ringtone routes
        @routes.get("/api/v1/telephone/ringtones")
        async def telephone_ringtones_get(request):
            ringtones = self.database.ringtones.get_all()
            return web.json_response(
                [
                    {
                        "id": r["id"],
                        "filename": r["filename"],
                        "display_name": r["display_name"],
                        "is_primary": bool(r["is_primary"]),
                        "created_at": r["created_at"],
                    }
                    for r in ringtones
                ],
            )

        @routes.get("/api/v1/telephone/ringtones/status")
        async def telephone_ringtone_status(request):
            primary = self.database.ringtones.get_primary()
            return web.json_response(
                {
                    "has_custom_ringtone": primary is not None,
                    "enabled": self.config.custom_ringtone_enabled.get(),
                    "filename": primary["filename"] if primary else None,
                    "id": primary["id"] if primary else None,
                },
            )

        @routes.get("/api/v1/telephone/ringtones/{id}/audio")
        async def telephone_ringtone_audio(request):
            ringtone_id = int(request.match_info["id"])
            ringtone = self.database.ringtones.get_by_id(ringtone_id)
            if not ringtone:
                return web.json_response({"message": "Ringtone not found"}, status=404)

            filepath = self.ringtone_manager.get_ringtone_path(
                ringtone["storage_filename"]
            )
            if os.path.exists(filepath):
                return web.FileResponse(filepath)
            return web.json_response(
                {"message": "Ringtone audio file not found"}, status=404
            )

        @routes.post("/api/v1/telephone/ringtones/upload")
        async def telephone_ringtone_upload(request):
            try:
                reader = await request.multipart()
                field = await reader.next()
                if field.name != "file":
                    return web.json_response(
                        {"message": "File field required"}, status=400
                    )

                filename = field.filename
                extension = os.path.splitext(filename)[1].lower()
                if extension not in [".mp3", ".ogg", ".wav", ".m4a", ".flac"]:
                    return web.json_response(
                        {"message": f"Unsupported file type: {extension}"},
                        status=400,
                    )

                # Save temp file
                with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as f:
                    temp_path = f.name
                    while True:
                        chunk = await field.read_chunk()
                        if not chunk:
                            break
                        f.write(chunk)

                try:
                    # Convert to ringtone
                    storage_filename = await asyncio.to_thread(
                        self.ringtone_manager.convert_to_ringtone,
                        temp_path,
                    )

                    # Add to database
                    ringtone_id = self.database.ringtones.add(
                        filename=filename,
                        storage_filename=storage_filename,
                    )

                    return web.json_response(
                        {
                            "message": "Ringtone uploaded and converted",
                            "id": ringtone_id,
                            "filename": filename,
                            "storage_filename": storage_filename,
                        },
                    )
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

            except Exception as e:
                return web.json_response({"message": str(e)}, status=500)

        @routes.patch("/api/v1/telephone/ringtones/{id}")
        async def telephone_ringtone_patch(request):
            try:
                ringtone_id = int(request.match_info["id"])
                data = await request.json()

                display_name = data.get("display_name")
                is_primary = 1 if data.get("is_primary") else None

                self.database.ringtones.update(
                    ringtone_id,
                    display_name=display_name,
                    is_primary=is_primary,
                )

                return web.json_response({"message": "Ringtone updated"})
            except Exception as e:
                return web.json_response({"message": str(e)}, status=500)

        @routes.delete("/api/v1/telephone/ringtones/{id}")
        async def telephone_ringtone_delete(request):
            try:
                ringtone_id = int(request.match_info["id"])
                ringtone = self.database.ringtones.get_by_id(ringtone_id)
                if ringtone:
                    self.ringtone_manager.remove_ringtone(ringtone["storage_filename"])
                    self.database.ringtones.delete(ringtone_id)
                return web.json_response({"message": "Ringtone deleted"})
            except Exception as e:
                return web.json_response({"message": str(e)}, status=500)

        # contacts routes
        @routes.get("/api/v1/telephone/contacts")
        async def telephone_contacts_get(request):
            search = request.query.get("search")
            limit = int(request.query.get("limit", 100))
            offset = int(request.query.get("offset", 0))
            contacts_rows = self.database.contacts.get_contacts(
                search=search,
                limit=limit,
                offset=offset,
            )

            contacts = []
            for row in contacts_rows:
                d = dict(row)
                remote_identity_hash = d.get("remote_identity_hash")
                if remote_identity_hash:
                    lxmf_hash = self.get_lxmf_destination_hash_for_identity_hash(
                        remote_identity_hash
                    )
                    if lxmf_hash:
                        icon = self.database.misc.get_user_icon(lxmf_hash)
                        if icon:
                            d["remote_icon"] = dict(icon)
                contacts.append(d)

            return web.json_response(contacts)

        @routes.post("/api/v1/telephone/contacts")
        async def telephone_contacts_post(request):
            data = await request.json()
            name = data.get("name")
            remote_identity_hash = data.get("remote_identity_hash")

            if not name or not remote_identity_hash:
                return web.json_response(
                    {"message": "Name and identity hash required"}, status=400
                )

            self.database.contacts.add_contact(name, remote_identity_hash)
            return web.json_response({"message": "Contact added"})

        @routes.patch("/api/v1/telephone/contacts/{id}")
        async def telephone_contacts_patch(request):
            contact_id = int(request.match_info["id"])
            data = await request.json()
            name = data.get("name")
            remote_identity_hash = data.get("remote_identity_hash")

            self.database.contacts.update_contact(
                contact_id, name, remote_identity_hash
            )
            return web.json_response({"message": "Contact updated"})

        @routes.delete("/api/v1/telephone/contacts/{id}")
        async def telephone_contacts_delete(request):
            contact_id = int(request.match_info["id"])
            self.database.contacts.delete_contact(contact_id)
            return web.json_response({"message": "Contact deleted"})

        @routes.get("/api/v1/telephone/contacts/check/{identity_hash}")
        async def telephone_contacts_check(request):
            identity_hash = request.match_info["identity_hash"]
            contact = self.database.contacts.get_contact_by_identity_hash(identity_hash)
            return web.json_response(
                {
                    "is_contact": contact is not None,
                    "contact": dict(contact) if contact else None,
                }
            )

        # announce
        @routes.get("/api/v1/announce")
        async def announce_trigger(request):
            await self.announce()

            return web.json_response(
                {
                    "message": "announcing",
                },
            )

        # serve announces
        @routes.get("/api/v1/announces")
        async def announces_get(request):
            # get query params
            aspect = request.query.get("aspect", None)
            identity_hash = request.query.get("identity_hash", None)
            destination_hash = request.query.get("destination_hash", None)
            search_query = request.query.get("search", None)
            limit = request.query.get("limit", None)
            offset = request.query.get("offset", None)
            include_blocked = (
                request.query.get("include_blocked", "false").lower() == "true"
            )

            blocked_identity_hashes = None
            if not include_blocked:
                blocked = self.database.misc.get_blocked_destinations()
                blocked_identity_hashes = [b["destination_hash"] for b in blocked]

            # fetch announces from database
            results = self.announce_manager.get_filtered_announces(
                aspect=aspect,
                identity_hash=identity_hash,
                destination_hash=destination_hash,
                query=None,  # We filter in Python to support name search
                blocked_identity_hashes=blocked_identity_hashes,
            )

            # process all announces to get display names and associated LXMF hashes
            all_announces = [
                self.convert_db_announce_to_dict(announce) for announce in results
            ]

            # apply search query filter if provided
            if search_query:
                q = search_query.lower()
                filtered = []
                for a in all_announces:
                    if (
                        (a.get("display_name") and q in a["display_name"].lower())
                        or (
                            a.get("destination_hash")
                            and q in a["destination_hash"].lower()
                        )
                        or (a.get("identity_hash") and q in a["identity_hash"].lower())
                        or (
                            a.get("lxmf_destination_hash")
                            and q in a["lxmf_destination_hash"].lower()
                        )
                    ):
                        filtered.append(a)
                all_announces = filtered

            # apply pagination
            total_count = len(all_announces)
            if offset is not None or limit is not None:
                start = int(offset) if offset else 0
                end = start + int(limit) if limit else total_count
                paginated_results = all_announces[start:end]
            else:
                paginated_results = all_announces

            return web.json_response(
                {
                    "announces": paginated_results,
                    "total_count": total_count,
                },
            )

        # serve favourites
        @routes.get("/api/v1/favourites")
        async def favourites_get(request):
            # get query params
            aspect = request.query.get("aspect", None)

            # get favourites from database
            results = self.database.announces.get_favourites(aspect=aspect)

            # process favourites
            favourites = [
                self.convert_db_favourite_to_dict(favourite) for favourite in results
            ]

            return web.json_response(
                {
                    "favourites": favourites,
                },
            )

        # add favourite
        @routes.post("/api/v1/favourites/add")
        async def favourites_add(request):
            # get request data
            data = await request.json()
            destination_hash = data.get("destination_hash", None)
            display_name = data.get("display_name", None)
            aspect = data.get("aspect", None)

            # destination hash is required
            if destination_hash is None:
                return web.json_response(
                    {
                        "message": "destination_hash is required",
                    },
                    status=422,
                )

            # display name is required
            if display_name is None:
                return web.json_response(
                    {
                        "message": "display_name is required",
                    },
                    status=422,
                )

            # aspect is required
            if aspect is None:
                return web.json_response(
                    {
                        "message": "aspect is required",
                    },
                    status=422,
                )

            # upsert favourite
            self.database.announces.upsert_favourite(
                destination_hash,
                display_name,
                aspect,
            )
            return web.json_response(
                {
                    "message": "Favourite has been added!",
                },
            )

        # rename favourite
        @routes.post("/api/v1/favourites/{destination_hash}/rename")
        async def favourites_rename(request):
            # get path params
            destination_hash = request.match_info.get("destination_hash", "")

            # get request data
            data = await request.json()
            display_name = data.get("display_name")

            # update display name if provided
            if len(display_name) > 0:
                self.database.announces.upsert_custom_display_name(
                    destination_hash,
                    display_name,
                )

            return web.json_response(
                {
                    "message": "Favourite has been renamed",
                },
            )

        # delete favourite
        @routes.delete("/api/v1/favourites/{destination_hash}")
        async def favourites_delete(request):
            # get path params
            destination_hash = request.match_info.get("destination_hash", "")

            # delete favourite
            self.database.announces.delete_favourite(destination_hash)
            return web.json_response(
                {
                    "message": "Favourite has been deleted!",
                },
            )

        # serve archived pages
        @routes.get("/api/v1/nomadnet/archives")
        async def get_all_archived_pages(request):
            # get search query and pagination from request
            query = request.query.get("q", "").strip()
            page = int(request.query.get("page", 1))
            limit = int(request.query.get("limit", 15))
            offset = (page - 1) * limit

            # fetch archived pages from database
            all_archives = self.database.misc.get_archived_pages_paginated(
                query=query,
            )
            total_count = len(all_archives)
            total_pages = (total_count + limit - 1) // limit

            # apply pagination
            archives_results = all_archives[offset : offset + limit]

            # return results
            archives = []
            for archive in archives_results:
                # find node name from announces or custom display names
                node_name = self.get_custom_destination_display_name(
                    archive["destination_hash"],
                )
                if not node_name:
                    db_announce = self.database.announces.get_announce_by_hash(
                        archive["destination_hash"],
                    )
                    if db_announce and db_announce["aspect"] == "nomadnetwork.node":
                        node_name = (
                            ReticulumMeshChat.parse_nomadnetwork_node_display_name(
                                db_announce["app_data"],
                            )
                        )

                archives.append(
                    {
                        "id": archive["id"],
                        "destination_hash": archive["destination_hash"],
                        "node_name": node_name or "Unknown Node",
                        "page_path": archive["page_path"],
                        "content": archive["content"],
                        "hash": archive["hash"],
                        "created_at": archive["created_at"],
                    },
                )

            return web.json_response(
                {
                    "archives": archives,
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total_count": total_count,
                        "total_pages": total_pages,
                    },
                },
            )

        @routes.get("/api/v1/lxmf/propagation-node/status")
        async def propagation_node_status(request):
            return web.json_response(
                {
                    "propagation_node_status": {
                        "state": self.convert_propagation_node_state_to_string(
                            self.message_router.propagation_transfer_state,
                        ),
                        "progress": self.message_router.propagation_transfer_progress
                        * 100,  # convert to percentage
                        "messages_received": self.message_router.propagation_transfer_last_result,
                    },
                },
            )

        # sync propagation node
        @routes.get("/api/v1/lxmf/propagation-node/sync")
        async def propagation_node_sync(request):
            # ensure propagation node is configured before attempting to sync
            if self.message_router.get_outbound_propagation_node() is None:
                return web.json_response(
                    {
                        "message": "A propagation node must be configured to sync messages.",
                    },
                    status=400,
                )

            # request messages from propagation node
            await self.sync_propagation_nodes()

            return web.json_response(
                {
                    "message": "Sync is starting",
                },
            )

        # stop syncing propagation node
        @routes.get("/api/v1/lxmf/propagation-node/stop-sync")
        async def propagation_node_stop_sync(request):
            self.stop_propagation_node_sync()

            return web.json_response(
                {
                    "message": "Sync is stopping",
                },
            )

        # serve propagation nodes
        @routes.get("/api/v1/lxmf/propagation-nodes")
        async def propagation_nodes_get(request):
            # get query params
            limit = request.query.get("limit", None)

            # get lxmf.propagation announces
            results = self.database.announces.get_announces(aspect="lxmf.propagation")

            # limit results
            if limit is not None:
                results = results[: int(limit)]

            # process announces
            lxmf_propagation_nodes = []
            for announce in results:
                # find an lxmf.delivery announce for the same identity hash, so we can use that as an "operater by" name
                lxmf_delivery_results = self.database.announces.get_filtered_announces(
                    aspect="lxmf.delivery",
                    identity_hash=announce["identity_hash"],
                )
                lxmf_delivery_announce = (
                    lxmf_delivery_results[0] if lxmf_delivery_results else None
                )

                # find a nomadnetwork.node announce for the same identity hash, so we can use that as an "operated by" name
                nomadnetwork_node_results = (
                    self.database.announces.get_filtered_announces(
                        aspect="nomadnetwork.node",
                        identity_hash=announce["identity_hash"],
                    )
                )
                nomadnetwork_node_announce = (
                    nomadnetwork_node_results[0] if nomadnetwork_node_results else None
                )

                # get a display name from other announces belonging to the propagation nodes identity
                operator_display_name = None
                if (
                    lxmf_delivery_announce is not None
                    and lxmf_delivery_announce["app_data"] is not None
                ):
                    operator_display_name = self.parse_lxmf_display_name(
                        lxmf_delivery_announce["app_data"],
                        None,
                    )
                elif (
                    nomadnetwork_node_announce is not None
                    and nomadnetwork_node_announce["app_data"] is not None
                ):
                    operator_display_name = (
                        ReticulumMeshChat.parse_nomadnetwork_node_display_name(
                            nomadnetwork_node_announce["app_data"],
                            None,
                        )
                    )

                # parse app_data so we can see if propagation is enabled or disabled for this node
                is_propagation_enabled = None
                per_transfer_limit = None
                propagation_node_data = (
                    ReticulumMeshChat.parse_lxmf_propagation_node_app_data(
                        announce["app_data"],
                    )
                )
                if propagation_node_data is not None:
                    is_propagation_enabled = propagation_node_data["enabled"]
                    per_transfer_limit = propagation_node_data["per_transfer_limit"]

                lxmf_propagation_nodes.append(
                    {
                        "destination_hash": announce["destination_hash"],
                        "identity_hash": announce["identity_hash"],
                        "operator_display_name": operator_display_name,
                        "is_propagation_enabled": is_propagation_enabled,
                        "per_transfer_limit": per_transfer_limit,
                        "created_at": announce["created_at"],
                        "updated_at": announce["updated_at"],
                    },
                )

            return web.json_response(
                {
                    "lxmf_propagation_nodes": lxmf_propagation_nodes,
                },
            )

        # get path to destination
        @routes.get("/api/v1/destination/{destination_hash}/path")
        async def destination_path(request):
            # get path params
            destination_hash = request.match_info.get("destination_hash", "")

            # convert destination hash to bytes
            destination_hash = bytes.fromhex(destination_hash)

            # check if user wants to request the path from the network right now
            request_query_param = request.query.get("request", "false")
            should_request_now = request_query_param in ("true", "1")
            if should_request_now:
                # determine how long we should wait for a path response
                timeout_seconds = int(request.query.get("timeout", 15))
                timeout_after_seconds = time.time() + timeout_seconds

                # request path if we don't have it
                if not RNS.Transport.has_path(destination_hash):
                    RNS.Transport.request_path(destination_hash)

                # wait until we have a path, or give up after the configured timeout
                while (
                    not RNS.Transport.has_path(destination_hash)
                    and time.time() < timeout_after_seconds
                ):
                    await asyncio.sleep(0.1)

            # ensure path is known
            if not RNS.Transport.has_path(destination_hash):
                return web.json_response(
                    {
                        "path": None,
                    },
                )

            # determine next hop and hop count
            hops = RNS.Transport.hops_to(destination_hash)
            next_hop_bytes = self.reticulum.get_next_hop(destination_hash)

            # ensure next hop provided
            if next_hop_bytes is None:
                return web.json_response(
                    {
                        "path": None,
                    },
                )

            next_hop = next_hop_bytes.hex()
            next_hop_interface = self.reticulum.get_next_hop_if_name(destination_hash)

            return web.json_response(
                {
                    "path": {
                        "hops": hops,
                        "next_hop": next_hop,
                        "next_hop_interface": next_hop_interface,
                    },
                },
            )

        # drop path to destination
        @routes.post("/api/v1/destination/{destination_hash}/drop-path")
        async def destination_drop_path(request):
            # get path params
            destination_hash = request.match_info.get("destination_hash", "")

            # convert destination hash to bytes
            destination_hash = bytes.fromhex(destination_hash)

            # drop path
            self.reticulum.drop_path(destination_hash)

            return web.json_response(
                {
                    "message": "Path has been dropped",
                },
            )

        # get signal metrics for a destination by checking the latest announce or lxmf message received from them
        @routes.get("/api/v1/destination/{destination_hash}/signal-metrics")
        async def destination_signal_metrics(request):
            # get path params
            destination_hash = request.match_info.get("destination_hash", "")

            # signal metrics to return
            snr = None
            rssi = None
            quality = None
            updated_at = None

            # get latest announce from database for the provided destination hash
            latest_announce = self.database.announces.get_announce_by_hash(
                destination_hash,
            )

            # get latest lxmf message from database sent to us from the provided destination hash
            local_hash = self.local_lxmf_destination.hexhash
            messages = self.message_handler.get_conversation_messages(
                local_hash,
                destination_hash,
                limit=1,
            )
            # Filter for incoming messages only
            latest_lxmf_message = next(
                (m for m in messages if m["source_hash"] == destination_hash),
                None,
            )

            # determine when latest announce was received
            latest_announce_at = None
            if latest_announce is not None:
                latest_announce_at = datetime.fromisoformat(
                    latest_announce["updated_at"],
                )
                if latest_announce_at.tzinfo is not None:
                    latest_announce_at = latest_announce_at.replace(tzinfo=None)

            # determine when latest lxmf message was received
            latest_lxmf_message_at = None
            if latest_lxmf_message is not None:
                latest_lxmf_message_at = datetime.fromisoformat(
                    latest_lxmf_message["created_at"],
                )
                if latest_lxmf_message_at.tzinfo is not None:
                    latest_lxmf_message_at = latest_lxmf_message_at.replace(tzinfo=None)

            # get signal metrics from latest announce
            if latest_announce is not None:
                snr = latest_announce["snr"]
                rssi = latest_announce["rssi"]
                quality = latest_announce["quality"]
                # using updated_at from announce because this is when the latest announce was received
                updated_at = latest_announce["updated_at"]

            # get signal metrics from latest lxmf message if it's more recent than the announce
            if latest_lxmf_message is not None and (
                latest_announce_at is None
                or latest_lxmf_message_at > latest_announce_at
            ):
                snr = latest_lxmf_message["snr"]
                rssi = latest_lxmf_message["rssi"]
                quality = latest_lxmf_message["quality"]
                # using created_at from lxmf message because this is when the message was received
                updated_at = latest_lxmf_message["created_at"]

            return web.json_response(
                {
                    "signal_metrics": {
                        "snr": snr,
                        "rssi": rssi,
                        "quality": quality,
                        "updated_at": updated_at,
                    },
                },
            )

        # pings an lxmf.delivery destination by sending empty data and waiting for the recipient to send a proof back
        # the lxmf router proves all received packets, then drops them if they can't be decoded as lxmf messages
        # this allows us to ping/probe any active lxmf.delivery destination and get rtt/snr/rssi data on demand
        # https://github.com/markqvist/LXMF/blob/9ff76c0473e9d4107e079f266dd08144bb74c7c8/LXMF/LXMRouter.py#L234
        # https://github.com/markqvist/LXMF/blob/9ff76c0473e9d4107e079f266dd08144bb74c7c8/LXMF/LXMRouter.py#L1374
        @routes.get("/api/v1/ping/{destination_hash}/lxmf.delivery")
        async def ping_lxmf_delivery(request):
            # get path params
            destination_hash_str = request.match_info.get("destination_hash", "")

            # convert destination hash to bytes
            destination_hash = bytes.fromhex(destination_hash_str)

            # determine how long until we should time out
            timeout_seconds = int(request.query.get("timeout", 15))
            timeout_after_seconds = time.time() + timeout_seconds

            # request path if we don't have it
            if not RNS.Transport.has_path(destination_hash):
                RNS.Transport.request_path(destination_hash)

            # wait until we have a path, or give up after the configured timeout
            while (
                not RNS.Transport.has_path(destination_hash)
                and time.time() < timeout_after_seconds
            ):
                await asyncio.sleep(0.1)

            # find destination identity (pass string hash, not bytes)
            destination_identity = self.recall_identity(destination_hash_str)
            if destination_identity is None:
                return web.json_response(
                    {
                        "message": "Ping failed. Could not find path to destination.",
                    },
                    status=503,
                )

            # create outbound destination
            request_destination = RNS.Destination(
                destination_identity,
                RNS.Destination.OUT,
                RNS.Destination.SINGLE,
                "lxmf",
                "delivery",
            )

            # send empty packet to destination
            packet = RNS.Packet(request_destination, b"")
            receipt = packet.send()

            # wait until delivered, or give up after time out
            while (
                receipt.status != RNS.PacketReceipt.DELIVERED
                and time.time() < timeout_after_seconds
            ):
                await asyncio.sleep(0.1)

            # ping failed if not delivered
            if receipt.status != RNS.PacketReceipt.DELIVERED:
                return web.json_response(
                    {
                        "message": f"Ping failed. Timed out after {timeout_seconds} seconds.",
                    },
                    status=503,
                )

            # get number of hops to destination and back from destination
            hops_there = RNS.Transport.hops_to(destination_hash)
            hops_back = receipt.proof_packet.hops

            # get rssi
            rssi = receipt.proof_packet.rssi
            if rssi is None:
                rssi = self.reticulum.get_packet_rssi(receipt.proof_packet.packet_hash)

            # get snr
            snr = receipt.proof_packet.snr
            if snr is None:
                snr = self.reticulum.get_packet_snr(receipt.proof_packet.packet_hash)

            # get signal quality
            quality = receipt.proof_packet.q
            if quality is None:
                quality = self.reticulum.get_packet_q(receipt.proof_packet.packet_hash)

            # get and format round trip time
            rtt = receipt.get_rtt()
            rtt_milliseconds = round(rtt * 1000, 3)
            rtt_duration_string = f"{rtt_milliseconds} ms"

            return web.json_response(
                {
                    "message": f"Valid reply from {receipt.destination.hash.hex()}\nDuration: {rtt_duration_string}\nHops There: {hops_there}\nHops Back: {hops_back}",
                    "ping_result": {
                        "rtt": rtt,
                        "hops_there": hops_there,
                        "hops_back": hops_back,
                        "rssi": rssi,
                        "snr": snr,
                        "quality": quality,
                        "receiving_interface": str(
                            receipt.proof_packet.receiving_interface,
                        ),
                    },
                },
            )

        @routes.post("/api/v1/rncp/send")
        async def rncp_send(request):
            data = await request.json()
            destination_hash_str = data.get("destination_hash", "")
            file_path = data.get("file_path", "")
            timeout = float(data.get("timeout", RNS.Transport.PATH_REQUEST_TIMEOUT))
            no_compress = bool(data.get("no_compress", False))

            try:
                destination_hash = bytes.fromhex(destination_hash_str)
            except Exception as e:
                return web.json_response(
                    {"message": f"Invalid destination hash: {e}"},
                    status=400,
                )

            transfer_id = None

            def on_progress(progress):
                if transfer_id:
                    AsyncUtils.run_async(
                        self._broadcast_websocket_message(
                            {
                                "type": "rncp.transfer.progress",
                                "transfer_id": transfer_id,
                                "progress": progress,
                            },
                        ),
                    )

            try:
                result = await self.rncp_handler.send_file(
                    destination_hash=destination_hash,
                    file_path=file_path,
                    timeout=timeout,
                    on_progress=on_progress,
                    no_compress=no_compress,
                )
                transfer_id = result["transfer_id"]
                return web.json_response(result)
            except Exception as e:
                return web.json_response(
                    {"message": str(e)},
                    status=500,
                )

        @routes.post("/api/v1/rncp/fetch")
        async def rncp_fetch(request):
            data = await request.json()
            destination_hash_str = data.get("destination_hash", "")
            file_path = data.get("file_path", "")
            timeout = float(data.get("timeout", RNS.Transport.PATH_REQUEST_TIMEOUT))
            save_path = data.get("save_path")
            allow_overwrite = bool(data.get("allow_overwrite", False))

            try:
                destination_hash = bytes.fromhex(destination_hash_str)
            except Exception as e:
                return web.json_response(
                    {"message": f"Invalid destination hash: {e}"},
                    status=400,
                )

            transfer_id = None

            def on_progress(progress):
                if transfer_id:
                    AsyncUtils.run_async(
                        self._broadcast_websocket_message(
                            {
                                "type": "rncp.transfer.progress",
                                "transfer_id": transfer_id,
                                "progress": progress,
                            },
                        ),
                    )

            try:
                result = await self.rncp_handler.fetch_file(
                    destination_hash=destination_hash,
                    file_path=file_path,
                    timeout=timeout,
                    on_progress=on_progress,
                    save_path=save_path,
                    allow_overwrite=allow_overwrite,
                )
                return web.json_response(result)
            except Exception as e:
                return web.json_response(
                    {"message": str(e)},
                    status=500,
                )

        @routes.get("/api/v1/rncp/transfer/{transfer_id}")
        async def rncp_transfer_status(request):
            transfer_id = request.match_info.get("transfer_id", "")
            status = self.rncp_handler.get_transfer_status(transfer_id)
            if status:
                return web.json_response(status)
            return web.json_response(
                {"message": "Transfer not found"},
                status=404,
            )

        @routes.post("/api/v1/rncp/listen")
        async def rncp_listen(request):
            data = await request.json()
            allowed_hashes = data.get("allowed_hashes", [])
            fetch_allowed = bool(data.get("fetch_allowed", False))
            fetch_jail = data.get("fetch_jail")
            allow_overwrite = bool(data.get("allow_overwrite", False))

            try:
                destination_hash = self.rncp_handler.setup_receive_destination(
                    allowed_hashes=allowed_hashes,
                    fetch_allowed=fetch_allowed,
                    fetch_jail=fetch_jail,
                    allow_overwrite=allow_overwrite,
                )
                return web.json_response(
                    {
                        "destination_hash": destination_hash,
                        "message": "RNCP listener started",
                    },
                )
            except Exception as e:
                return web.json_response(
                    {"message": str(e)},
                    status=500,
                )

        @routes.get("/api/v1/rnstatus")
        async def rnstatus(request):
            include_link_stats = request.query.get("include_link_stats", "false") in (
                "true",
                "1",
            )
            sorting = request.query.get("sorting")
            sort_reverse = request.query.get("sort_reverse", "false") in ("true", "1")

            try:
                status = self.rnstatus_handler.get_status(
                    include_link_stats=include_link_stats,
                    sorting=sorting,
                    sort_reverse=sort_reverse,
                )
                return web.json_response(status)
            except Exception as e:
                return web.json_response(
                    {"message": str(e)},
                    status=500,
                )

        @routes.post("/api/v1/rnprobe")
        async def rnprobe(request):
            data = await request.json()
            destination_hash_str = data.get("destination_hash", "")
            full_name = data.get("full_name", "")
            size = int(data.get("size", RNProbeHandler.DEFAULT_PROBE_SIZE))
            timeout = float(data.get("timeout", 0)) or None
            wait = float(data.get("wait", 0))
            probes = int(data.get("probes", 1))

            try:
                destination_hash = bytes.fromhex(destination_hash_str)
            except Exception as e:
                return web.json_response(
                    {"message": f"Invalid destination hash: {e}"},
                    status=400,
                )

            if not full_name:
                return web.json_response(
                    {"message": "full_name is required"},
                    status=400,
                )

            try:
                result = await self.rnprobe_handler.probe_destination(
                    destination_hash=destination_hash,
                    full_name=full_name,
                    size=size,
                    timeout=timeout,
                    wait=wait,
                    probes=probes,
                )
                return web.json_response(result)
            except Exception as e:
                return web.json_response(
                    {"message": str(e)},
                    status=500,
                )

        @routes.get("/api/v1/translator/languages")
        async def translator_languages(request):
            try:
                libretranslate_url = request.query.get("libretranslate_url")
                languages = self.translator_handler.get_supported_languages(
                    libretranslate_url=libretranslate_url,
                )
                return web.json_response(
                    {
                        "languages": languages,
                        "has_argos": self.translator_handler.has_argos,
                        "has_argos_lib": self.translator_handler.has_argos_lib,
                        "has_argos_cli": self.translator_handler.has_argos_cli,
                    },
                )
            except Exception as e:
                return web.json_response(
                    {"message": str(e)},
                    status=500,
                )

        @routes.post("/api/v1/translator/translate")
        async def translator_translate(request):
            data = await request.json()
            text = data.get("text", "")
            source_lang = data.get("source_lang", "auto")
            target_lang = data.get("target_lang", "")
            use_argos = bool(data.get("use_argos", False))
            libretranslate_url = data.get("libretranslate_url")

            if not text:
                return web.json_response(
                    {"message": "Text cannot be empty"},
                    status=400,
                )

            if not target_lang:
                return web.json_response(
                    {"message": "Target language is required"},
                    status=400,
                )

            try:
                result = self.translator_handler.translate_text(
                    text=text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    use_argos=use_argos,
                    libretranslate_url=libretranslate_url,
                )
                return web.json_response(result)
            except Exception as e:
                return web.json_response(
                    {"message": str(e)},
                    status=500,
                )

        @routes.post("/api/v1/translator/install-languages")
        async def translator_install_languages(request):
            data = await request.json()
            package_name = data.get("package", "translate")

            try:
                result = self.translator_handler.install_language_package(package_name)
                return web.json_response(result)
            except Exception as e:
                return web.json_response(
                    {"message": str(e)},
                    status=500,
                )

        # get custom destination display name
        @routes.get("/api/v1/destination/{destination_hash}/custom-display-name")
        async def destination_custom_display_name_get(request):
            # get path params
            destination_hash = request.match_info.get("destination_hash", "")

            return web.json_response(
                {
                    "custom_display_name": self.get_custom_destination_display_name(
                        destination_hash,
                    ),
                },
            )

        # set custom destination display name
        @routes.post(
            "/api/v1/destination/{destination_hash}/custom-display-name/update",
        )
        async def destination_custom_display_name_update(request):
            # get path params
            destination_hash = request.match_info.get("destination_hash", "")

            # get request data
            data = await request.json()
            display_name = data.get("display_name")

            # update display name if provided
            if len(display_name) > 0:
                self.database.announces.upsert_custom_display_name(
                    destination_hash,
                    display_name,
                )
                return web.json_response(
                    {
                        "message": "Custom display name has been updated",
                    },
                )

            # otherwise remove display name
            self.database.announces.delete_custom_display_name(destination_hash)
            return web.json_response(
                {
                    "message": "Custom display name has been removed",
                },
            )

        # get lxmf stamp cost for the provided lxmf.delivery destination hash
        @routes.get("/api/v1/destination/{destination_hash}/lxmf-stamp-info")
        async def destination_lxmf_stamp_info(request):
            # get path params
            destination_hash = request.match_info.get("destination_hash", "")

            # convert destination hash to bytes
            destination_hash_bytes = bytes.fromhex(destination_hash)

            # get lxmf stamp cost from announce in database
            lxmf_stamp_cost = None
            announce = self.database.announces.get_announce_by_hash(destination_hash)
            if announce is not None:
                lxmf_stamp_cost = ReticulumMeshChat.parse_lxmf_stamp_cost(
                    announce["app_data"],
                )

            # get outbound ticket expiry for this lxmf destination
            lxmf_outbound_ticket_expiry = (
                self.message_router.get_outbound_ticket_expiry(destination_hash_bytes)
            )

            return web.json_response(
                {
                    "lxmf_stamp_info": {
                        "stamp_cost": lxmf_stamp_cost,
                        "outbound_ticket_expiry": lxmf_outbound_ticket_expiry,
                    },
                },
            )

        # get interface stats
        @routes.get("/api/v1/interface-stats")
        async def interface_stats(request):
            # get interface stats
            interface_stats = self.reticulum.get_interface_stats()

            # ensure transport_id is hex as json_response can't serialize bytes
            if "transport_id" in interface_stats:
                interface_stats["transport_id"] = interface_stats["transport_id"].hex()

            # ensure probe_responder is hex as json_response can't serialize bytes
            if (
                "probe_responder" in interface_stats
                and interface_stats["probe_responder"] is not None
            ):
                interface_stats["probe_responder"] = interface_stats[
                    "probe_responder"
                ].hex()

            # ensure ifac_signature is hex as json_response can't serialize bytes
            for interface in interface_stats["interfaces"]:
                if "short_name" in interface:
                    interface["interface_name"] = interface["short_name"]

                if (
                    "parent_interface_name" in interface
                    and interface["parent_interface_name"] is not None
                ):
                    interface["parent_interface_hash"] = interface[
                        "parent_interface_hash"
                    ].hex()

                if interface.get("ifac_signature"):
                    interface["ifac_signature"] = interface["ifac_signature"].hex()

                if interface.get("hash"):
                    interface["hash"] = interface["hash"].hex()

            return web.json_response(
                {
                    "interface_stats": interface_stats,
                },
            )

        # get path table
        @routes.get("/api/v1/path-table")
        async def path_table(request):
            limit = request.query.get("limit", None)
            offset = request.query.get("offset", None)

            # get path table, making sure hash and via are in hex as json_response can't serialize bytes
            all_paths = self.reticulum.get_path_table()
            total_count = len(all_paths)

            # apply pagination if requested
            if limit is not None or offset is not None:
                try:
                    start = int(offset) if offset else 0
                    end = (start + int(limit)) if limit else total_count
                    paginated_paths = all_paths[start:end]
                except (ValueError, TypeError):
                    paginated_paths = all_paths
            else:
                paginated_paths = all_paths

            path_table = []
            for path in paginated_paths:
                path["hash"] = path["hash"].hex()
                path["via"] = path["via"].hex()
                path_table.append(path)

            return web.json_response(
                {
                    "path_table": path_table,
                    "total_count": total_count,
                },
            )

        # send lxmf message
        @routes.post("/api/v1/lxmf-messages/send")
        async def lxmf_messages_send(request):
            # get request body as json
            data = await request.json()

            # get delivery method
            delivery_method = None
            if "delivery_method" in data:
                delivery_method = data["delivery_method"]

            # get data from json
            destination_hash = data["lxmf_message"]["destination_hash"]
            content = data["lxmf_message"]["content"]
            fields = {}
            if "fields" in data["lxmf_message"]:
                fields = data["lxmf_message"]["fields"]

            # parse image field
            image_field = None
            if "image" in fields:
                image_type = data["lxmf_message"]["fields"]["image"]["image_type"]
                image_bytes = base64.b64decode(
                    data["lxmf_message"]["fields"]["image"]["image_bytes"],
                )
                image_field = LxmfImageField(image_type, image_bytes)

            # parse audio field
            audio_field = None
            if "audio" in fields:
                audio_mode = data["lxmf_message"]["fields"]["audio"]["audio_mode"]
                audio_bytes = base64.b64decode(
                    data["lxmf_message"]["fields"]["audio"]["audio_bytes"],
                )
                audio_field = LxmfAudioField(audio_mode, audio_bytes)

            # parse file attachments field
            file_attachments_field = None
            if "file_attachments" in fields:
                file_attachments = []
                for file_attachment in data["lxmf_message"]["fields"][
                    "file_attachments"
                ]:
                    file_name = file_attachment["file_name"]
                    file_bytes = base64.b64decode(file_attachment["file_bytes"])
                    file_attachments.append(LxmfFileAttachment(file_name, file_bytes))

                file_attachments_field = LxmfFileAttachmentsField(file_attachments)

            # parse telemetry field
            telemetry_data = None
            if "telemetry" in fields:
                telemetry_val = fields["telemetry"]
                if isinstance(telemetry_val, dict):
                    # Frontend sent raw dict, pack it here
                    telemetry_data = Telemeter.pack(location=telemetry_val)
                elif isinstance(telemetry_val, str):
                    # Frontend sent base64 packed data
                    telemetry_data = base64.b64decode(telemetry_val)

            # parse commands field
            commands = None
            if "commands" in fields:
                # convert dict keys back to ints if they look like hex or int strings
                commands = []
                for cmd in fields["commands"]:
                    new_cmd = {}
                    for k, v in cmd.items():
                        try:
                            if k.startswith("0x"):
                                new_cmd[int(k, 16)] = v
                            else:
                                new_cmd[int(k)] = v
                        except (ValueError, TypeError):
                            new_cmd[k] = v
                    commands.append(new_cmd)

            try:
                # send lxmf message to destination
                lxmf_message = await self.send_message(
                    destination_hash=destination_hash,
                    content=content,
                    image_field=image_field,
                    audio_field=audio_field,
                    file_attachments_field=file_attachments_field,
                    telemetry_data=telemetry_data,
                    commands=commands,
                    delivery_method=delivery_method,
                )

                return web.json_response(
                    {
                        "lxmf_message": self.convert_lxmf_message_to_dict(
                            lxmf_message,
                            include_attachments=False,
                        ),
                    },
                )

            except Exception as e:
                return web.json_response(
                    {
                        "message": f"Sending Failed: {e!s}",
                    },
                    status=503,
                )

        # cancel sending lxmf message
        @routes.post("/api/v1/lxmf-messages/{hash}/cancel")
        async def lxmf_messages_cancel(request):
            # get path params
            message_hash = request.match_info.get("hash", None)

            # convert hash to bytes
            hash_as_bytes = bytes.fromhex(message_hash)

            # cancel outbound message by lxmf message hash
            self.message_router.cancel_outbound(hash_as_bytes)

            # get lxmf message from database
            lxmf_message = None
            db_lxmf_message = self.database.messages.get_lxmf_message_by_hash(
                message_hash,
            )
            if db_lxmf_message is not None:
                lxmf_message = self.convert_db_lxmf_message_to_dict(db_lxmf_message)

            return web.json_response(
                {
                    "message": "ok",
                    "lxmf_message": lxmf_message,
                },
            )

        # identify self on existing nomadnetwork link
        @routes.post("/api/v1/nomadnetwork/{destination_hash}/identify")
        async def nomadnetwork_identify(request):
            # get path params
            destination_hash = request.match_info.get("destination_hash", "")

            # convert destination hash to bytes
            destination_hash = bytes.fromhex(destination_hash)

            # identify to existing active link
            if destination_hash in nomadnet_cached_links:
                link = nomadnet_cached_links[destination_hash]
                if link.status is RNS.Link.ACTIVE:
                    link.identify(self.identity)
                    return web.json_response(
                        {
                            "message": "Identity has been sent!",
                        },
                    )

            # failed to identify
            return web.json_response(
                {
                    "message": "Failed to identify. No active link to destination.",
                },
                status=500,
            )

        # delete lxmf message
        @routes.delete("/api/v1/lxmf-messages/{hash}")
        async def lxmf_messages_delete(request):
            # get path params
            message_hash = request.match_info.get("hash", None)

            # hash is required
            if message_hash is None:
                return web.json_response(
                    {
                        "message": "hash is required",
                    },
                    status=422,
                )

            # delete lxmf messages from db where hash matches
            self.database.messages.delete_lxmf_message_by_hash(message_hash)

            return web.json_response(
                {
                    "message": "ok",
                },
            )

        # serve lxmf messages for conversation
        @routes.get("/api/v1/lxmf-messages/conversation/{destination_hash}")
        async def lxmf_messages_conversation(request):
            # get path params
            destination_hash = request.match_info.get("destination_hash", "")
            order = request.query.get("order", "asc")
            count = request.query.get("count")
            after_id = request.query.get("after_id")

            # get source hash from local lxmf destination
            local_hash = self.local_lxmf_destination.hash.hex()

            # fetch messages from database
            results = self.message_handler.get_conversation_messages(
                local_hash,
                destination_hash,
                limit=int(count) if count else 100,
                after_id=after_id if order == "asc" else None,
                before_id=after_id if order == "desc" else None,
            )

            # convert to response json
            lxmf_messages = [
                self.convert_db_lxmf_message_to_dict(db_lxmf_message)
                for db_lxmf_message in results
            ]

            return web.json_response(
                {
                    "lxmf_messages": lxmf_messages,
                },
            )

        # fetch lxmf message attachment
        @routes.get("/api/v1/lxmf-messages/attachment/{message_hash}/{attachment_type}")
        async def lxmf_message_attachment(request):
            message_hash = request.match_info.get("message_hash")
            attachment_type = request.match_info.get("attachment_type")
            file_index = request.query.get("file_index")

            # find message from database
            db_lxmf_message = self.database.messages.get_lxmf_message_by_hash(
                message_hash,
            )
            if db_lxmf_message is None:
                return web.json_response({"message": "Message not found"}, status=404)

            # parse fields
            fields = json.loads(db_lxmf_message["fields"])

            # handle image
            if attachment_type == "image" and "image" in fields:
                image_data = base64.b64decode(fields["image"]["image_bytes"])
                image_type = fields["image"]["image_type"]
                return web.Response(body=image_data, content_type=f"image/{image_type}")

            # handle audio
            if attachment_type == "audio" and "audio" in fields:
                audio_data = base64.b64decode(fields["audio"]["audio_bytes"])
                return web.Response(
                    body=audio_data,
                    content_type="application/octet-stream",
                )

            # handle file attachments
            if attachment_type == "file" and "file_attachments" in fields:
                if file_index is not None:
                    try:
                        index = int(file_index)
                        file_attachment = fields["file_attachments"][index]
                        file_data = base64.b64decode(file_attachment["file_bytes"])
                        return web.Response(
                            body=file_data,
                            content_type="application/octet-stream",
                            headers={
                                "Content-Disposition": f'attachment; filename="{file_attachment["file_name"]}"',
                            },
                        )
                    except (ValueError, IndexError):
                        pass

            return web.json_response({"message": "Attachment not found"}, status=404)

        # delete lxmf messages for conversation
        @routes.delete("/api/v1/lxmf-messages/conversation/{destination_hash}")
        async def lxmf_messages_conversation_delete(request):
            # get path params
            destination_hash = request.match_info.get("destination_hash", "")

            # get source hash from local lxmf destination
            local_hash = self.local_lxmf_destination.hash.hex()

            # delete lxmf messages from db where "source to destination" or "destination to source"
            self.message_handler.delete_conversation(local_hash, destination_hash)

            return web.json_response(
                {
                    "message": "ok",
                },
            )

        # get lxmf conversations
        @routes.get("/api/v1/lxmf/conversations")
        async def lxmf_conversations_get(request):
            # get query params
            search_query = request.query.get("q", None)
            filter_unread = ReticulumMeshChat.parse_bool_query_param(
                request.query.get(
                    "unread",
                    request.query.get("filter_unread", "false"),
                ),
            )
            filter_failed = ReticulumMeshChat.parse_bool_query_param(
                request.query.get(
                    "failed",
                    request.query.get("filter_failed", "false"),
                ),
            )
            filter_has_attachments = ReticulumMeshChat.parse_bool_query_param(
                request.query.get(
                    "has_attachments",
                    request.query.get("filter_has_attachments", "false"),
                ),
            )

            local_hash = self.local_lxmf_destination.hexhash
            search_destination_hashes = set()
            if search_query is not None and search_query != "":
                search_destination_hashes = self.search_destination_hashes_by_message(
                    search_query,
                )

            # fetch conversations from database
            db_conversations = self.message_handler.get_conversations(local_hash)

            conversations = []
            for db_message in db_conversations:
                # determine other user hash
                if db_message["source_hash"] == local_hash:
                    other_user_hash = db_message["destination_hash"]
                else:
                    other_user_hash = db_message["source_hash"]

                # determine latest message data
                latest_message_title = db_message["title"]
                latest_message_preview = db_message["content"]
                latest_message_timestamp = db_message["timestamp"]
                latest_message_has_attachments = self.message_fields_have_attachments(
                    db_message["fields"],
                )

                # using timestamp (sent time) for updated_at as it is more reliable across restarts
                # and represents the actual time the message was created by the sender.
                # we convert it to ISO format for the frontend.
                updated_at = datetime.fromtimestamp(
                    latest_message_timestamp,
                    UTC,
                ).isoformat()

                # check if conversation has attachments
                has_attachments = self.conversation_has_attachments(other_user_hash)

                # find user icon from database
                lxmf_user_icon = None
                db_lxmf_user_icon = self.database.misc.get_user_icon(other_user_hash)
                if db_lxmf_user_icon:
                    lxmf_user_icon = {
                        "icon_name": db_lxmf_user_icon["icon_name"],
                        "foreground_colour": db_lxmf_user_icon["foreground_colour"],
                        "background_colour": db_lxmf_user_icon["background_colour"],
                    }

                # add to conversations
                conversations.append(
                    {
                        "display_name": self.get_lxmf_conversation_name(
                            other_user_hash,
                        ),
                        "custom_display_name": self.get_custom_destination_display_name(
                            other_user_hash,
                        ),
                        "destination_hash": other_user_hash,
                        "is_unread": self.database.messages.is_conversation_unread(
                            other_user_hash,
                        ),
                        "failed_messages_count": self.lxmf_conversation_failed_messages_count(
                            other_user_hash,
                        ),
                        "has_attachments": has_attachments,
                        "latest_message_title": latest_message_title,
                        "latest_message_preview": latest_message_preview,
                        "latest_message_created_at": latest_message_timestamp,
                        "latest_message_has_attachments": latest_message_has_attachments,
                        "lxmf_user_icon": lxmf_user_icon,
                        "updated_at": updated_at,
                    },
                )

            if search_query is not None and search_query != "":
                lowered_query = search_query.lower()
                filtered = []
                for conversation in conversations:
                    matches_display = (
                        conversation["display_name"]
                        and lowered_query in conversation["display_name"].lower()
                    )
                    matches_custom = (
                        conversation["custom_display_name"]
                        and lowered_query in conversation["custom_display_name"].lower()
                    )
                    matches_destination = (
                        conversation["destination_hash"]
                        and lowered_query in conversation["destination_hash"].lower()
                    )
                    matches_latest_title = (
                        conversation["latest_message_title"]
                        and lowered_query
                        in conversation["latest_message_title"].lower()
                    )
                    matches_latest_preview = (
                        conversation["latest_message_preview"]
                        and lowered_query
                        in conversation["latest_message_preview"].lower()
                    )
                    matches_history = (
                        conversation["destination_hash"] in search_destination_hashes
                    )
                    if (
                        matches_display
                        or matches_custom
                        or matches_destination
                        or matches_latest_title
                        or matches_latest_preview
                        or matches_history
                    ):
                        filtered.append(conversation)
                conversations = filtered

            if filter_unread:
                conversations = [c for c in conversations if c["is_unread"]]
                # Filter out notifications that have been viewed
                filtered_conversations = []
                for c in conversations:
                    message_timestamp = c["latest_message_created_at"]
                    if not self.database.messages.is_notification_viewed(
                        c["destination_hash"],
                        message_timestamp,
                    ):
                        filtered_conversations.append(c)
                conversations = filtered_conversations

            if filter_failed:
                conversations = [
                    c for c in conversations if c["failed_messages_count"] > 0
                ]

            if filter_has_attachments:
                conversations = [c for c in conversations if c["has_attachments"]]

            return web.json_response(
                {
                    "conversations": conversations,
                },
            )

        # mark lxmf conversation as read
        @routes.get("/api/v1/lxmf/conversations/{destination_hash}/mark-as-read")
        async def lxmf_conversations_mark_read(request):
            # get path params
            destination_hash = request.match_info.get("destination_hash", "")

            # mark lxmf conversation as read
            self.database.messages.mark_conversation_as_read(destination_hash)

            return web.json_response(
                {
                    "message": "ok",
                },
            )

        # mark notifications as viewed
        @routes.post("/api/v1/notifications/mark-as-viewed")
        async def notifications_mark_as_viewed(request):
            data = await request.json()
            destination_hashes = data.get("destination_hashes", [])
            notification_ids = data.get("notification_ids", [])

            if destination_hashes:
                # mark LXMF conversations as viewed
                self.database.messages.mark_all_notifications_as_viewed(
                    destination_hashes
                )

            if notification_ids:
                # mark system notifications as viewed
                self.database.misc.mark_notifications_as_viewed(notification_ids)

            return web.json_response(
                {
                    "message": "ok",
                },
            )

        @routes.get("/api/v1/notifications")
        async def notifications_get(request):
            try:
                filter_unread = ReticulumMeshChat.parse_bool_query_param(
                    request.query.get("unread", "false")
                )
                limit = int(request.query.get("limit", 50))

                # 1. Fetch system notifications
                system_notifications = self.database.misc.get_notifications(
                    filter_unread=filter_unread, limit=limit
                )

                # 2. Fetch unread LXMF conversations if requested
                conversations = []
                if filter_unread:
                    local_hash = self.local_lxmf_destination.hexhash
                    db_conversations = self.message_handler.get_conversations(
                        local_hash, filter_unread=True
                    )
                    for db_message in db_conversations:
                        # Convert to dict if needed
                        if not isinstance(db_message, dict):
                            db_message = dict(db_message)

                        # determine other user hash
                        if db_message["source_hash"] == local_hash:
                            other_user_hash = db_message["destination_hash"]
                        else:
                            other_user_hash = db_message["source_hash"]

                        # Determine display name
                        display_name = self.get_name_for_lxmf_destination_hash(
                            other_user_hash
                        )
                        custom_display_name = (
                            self.database.announces.get_custom_display_name(
                                other_user_hash
                            )
                        )

                        # Determine latest message data
                        latest_message_data = {
                            "content": db_message.get("content", ""),
                            "timestamp": db_message.get("timestamp", 0),
                            "is_incoming": db_message.get("is_incoming") == 1,
                        }

                        icon = self.database.misc.get_user_icon(other_user_hash)

                        conversations.append(
                            {
                                "type": "lxmf_message",
                                "destination_hash": other_user_hash,
                                "display_name": display_name,
                                "custom_display_name": custom_display_name,
                                "lxmf_user_icon": dict(icon) if icon else None,
                                "latest_message_preview": latest_message_data[
                                    "content"
                                ][:100],
                                "updated_at": datetime.fromtimestamp(
                                    latest_message_data["timestamp"] or 0, UTC
                                ).isoformat(),
                            }
                        )

                # Combine and sort by timestamp
                all_notifications = []

                for n in system_notifications:
                    # Convert to dict if needed
                    if not isinstance(n, dict):
                        n = dict(n)

                    # Get remote user info if possible
                    display_name = "Unknown"
                    icon = None
                    if n["remote_hash"]:
                        # Try to find associated LXMF hash for telephony identity hash
                        lxmf_hash = self.get_lxmf_destination_hash_for_identity_hash(
                            n["remote_hash"]
                        )
                        if not lxmf_hash:
                            # Fallback to direct name lookup by identity hash
                            display_name = (
                                self.get_name_for_identity_hash(n["remote_hash"])
                                or n["remote_hash"]
                            )
                        else:
                            display_name = self.get_name_for_lxmf_destination_hash(
                                lxmf_hash
                            )
                            icon = self.database.misc.get_user_icon(lxmf_hash)

                    all_notifications.append(
                        {
                            "id": n["id"],
                            "type": n["type"],
                            "destination_hash": n["remote_hash"],
                            "display_name": display_name,
                            "lxmf_user_icon": dict(icon) if icon else None,
                            "title": n["title"],
                            "content": n["content"],
                            "is_viewed": n["is_viewed"] == 1,
                            "updated_at": datetime.fromtimestamp(
                                n["timestamp"] or 0, UTC
                            ).isoformat(),
                        }
                    )

                all_notifications.extend(conversations)

                # Sort by updated_at descending
                all_notifications.sort(key=lambda x: x["updated_at"], reverse=True)

                # Calculate actual unread count
                unread_count = self.database.misc.get_unread_notification_count()

                # Add LXMF unread count
                lxmf_unread_count = 0
                local_hash = self.local_lxmf_destination.hexhash
                unread_conversations = self.message_handler.get_conversations(
                    local_hash, filter_unread=True
                )
                if unread_conversations:
                    lxmf_unread_count = len(unread_conversations)

                total_unread_count = unread_count + lxmf_unread_count

                return web.json_response(
                    {
                        "notifications": all_notifications[:limit],
                        "unread_count": total_unread_count,
                    }
                )
            except Exception as e:
                RNS.log(f"Error in notifications_get: {e}", RNS.LOG_ERROR)
                import traceback

                traceback.print_exc()
                return web.json_response({"error": str(e)}, status=500)

        # get blocked destinations
        @routes.get("/api/v1/blocked-destinations")
        async def blocked_destinations_get(request):
            blocked = self.database.misc.get_blocked_destinations()
            blocked_list = [
                {
                    "destination_hash": b["destination_hash"],
                    "created_at": b["created_at"],
                }
                for b in blocked
            ]
            return web.json_response(
                {
                    "blocked_destinations": blocked_list,
                },
            )

        # add blocked destination
        @routes.post("/api/v1/blocked-destinations")
        async def blocked_destinations_add(request):
            data = await request.json()
            destination_hash = data.get("destination_hash", "")
            if not destination_hash or len(destination_hash) != 32:
                return web.json_response(
                    {"error": "Invalid destination hash"},
                    status=400,
                )

            try:
                self.database.misc.add_blocked_destination(destination_hash)
                # drop any existing paths to this destination
                try:
                    self.reticulum.drop_path(bytes.fromhex(destination_hash))
                except Exception as e:
                    print(f"Failed to drop path for blocked destination: {e}")
                return web.json_response({"message": "ok"})
            except Exception:
                return web.json_response(
                    {"error": "Destination already blocked"},
                    status=400,
                )

        # remove blocked destination
        @routes.delete("/api/v1/blocked-destinations/{destination_hash}")
        async def blocked_destinations_delete(request):
            destination_hash = request.match_info.get("destination_hash", "")
            if not destination_hash or len(destination_hash) != 32:
                return web.json_response(
                    {"error": "Invalid destination hash"},
                    status=400,
                )

            try:
                self.database.misc.delete_blocked_destination(destination_hash)
                return web.json_response({"message": "ok"})
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        # get spam keywords
        @routes.get("/api/v1/spam-keywords")
        async def spam_keywords_get(request):
            keywords = self.database.misc.get_spam_keywords()
            keyword_list = [
                {
                    "id": k["id"],
                    "keyword": k["keyword"],
                    "created_at": k["created_at"],
                }
                for k in keywords
            ]
            return web.json_response(
                {
                    "spam_keywords": keyword_list,
                },
            )

        # add spam keyword
        @routes.post("/api/v1/spam-keywords")
        async def spam_keywords_add(request):
            data = await request.json()
            keyword = data.get("keyword", "").strip()
            if not keyword:
                return web.json_response({"error": "Keyword is required"}, status=400)

            try:
                self.database.misc.add_spam_keyword(keyword)
                return web.json_response({"message": "ok"})
            except Exception:
                return web.json_response(
                    {"error": "Keyword already exists"},
                    status=400,
                )

        # remove spam keyword
        @routes.delete("/api/v1/spam-keywords/{keyword_id}")
        async def spam_keywords_delete(request):
            keyword_id = request.match_info.get("keyword_id", "")
            try:
                keyword_id = int(keyword_id)
            except (ValueError, TypeError):
                return web.json_response({"error": "Invalid keyword ID"}, status=400)

            try:
                self.database.misc.delete_spam_keyword(keyword_id)
                return web.json_response({"message": "ok"})
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        # mark message as spam or not spam
        @routes.post("/api/v1/lxmf-messages/{hash}/spam")
        async def lxmf_messages_spam(request):
            message_hash = request.match_info.get("hash", "")
            data = await request.json()
            is_spam = data.get("is_spam", False)

            try:
                message = self.database.messages.get_lxmf_message_by_hash(message_hash)
                if message:
                    message_data = dict(message)
                    message_data["is_spam"] = 1 if is_spam else 0
                    self.database.messages.upsert_lxmf_message(message_data)
                    return web.json_response({"message": "ok"})
                return web.json_response({"error": "Message not found"}, status=404)
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        # get offline map metadata
        @routes.get("/api/v1/map/offline")
        async def get_map_offline_metadata(request):
            metadata = self.map_manager.get_metadata()
            if metadata:
                return web.json_response(metadata)
            return web.json_response({"error": "No offline map loaded"}, status=404)

        # get map tile
        @routes.get("/api/v1/map/tiles/{z}/{x}/{y}")
        async def get_map_tile(request):
            try:
                z = int(request.match_info.get("z"))
                x = int(request.match_info.get("x"))
                y_str = request.match_info.get("y")
                # remove .png if present
                y_str = y_str.removesuffix(".png")
                y = int(y_str)

                tile_data = self.map_manager.get_tile(z, x, y)
                if tile_data:
                    return web.Response(body=tile_data, content_type="image/png")
                return web.Response(status=404)
            except Exception:
                return web.Response(status=400)

        # list available MBTiles files
        @routes.get("/api/v1/map/mbtiles")
        async def list_mbtiles(request):
            return web.json_response(self.map_manager.list_mbtiles())

        # delete an MBTiles file
        @routes.delete("/api/v1/map/mbtiles/{filename}")
        async def delete_mbtiles(request):
            filename = request.match_info.get("filename")
            if self.map_manager.delete_mbtiles(filename):
                return web.json_response({"message": "File deleted"})
            return web.json_response({"error": "File not found"}, status=404)

        # set active MBTiles file
        @routes.post("/api/v1/map/mbtiles/active")
        async def set_active_mbtiles(request):
            data = await request.json()
            filename = data.get("filename")
            if not filename:
                self.config.map_offline_path.set(None)
                self.config.map_offline_enabled.set(False)
                return web.json_response({"message": "Offline map disabled"})

            mbtiles_dir = self.map_manager.get_mbtiles_dir()
            file_path = os.path.join(mbtiles_dir, filename)
            if os.path.exists(file_path):
                self.map_manager.close()
                self.config.map_offline_path.set(file_path)
                self.config.map_offline_enabled.set(True)
                return web.json_response(
                    {
                        "message": "Active map updated",
                        "metadata": self.map_manager.get_metadata(),
                    },
                )
            return web.json_response({"error": "File not found"}, status=404)

        # get latest telemetry for all peers
        @routes.get("/api/v1/telemetry/peers")
        async def get_all_latest_telemetry(request):
            results = self.database.telemetry.get_all_latest_telemetry()
            telemetry_list = []
            for r in results:
                unpacked = Telemeter.from_packed(r["data"])
                telemetry_list.append(
                    {
                        "destination_hash": r["destination_hash"],
                        "timestamp": r["timestamp"],
                        "telemetry": unpacked,
                        "physical_link": json.loads(r["physical_link"])
                        if r["physical_link"]
                        else None,
                        "updated_at": r["updated_at"],
                    },
                )
            return web.json_response({"telemetry": telemetry_list})

        # get telemetry history for a destination
        @routes.get("/api/v1/telemetry/history/{destination_hash}")
        async def get_telemetry_history(request):
            destination_hash = request.match_info.get("destination_hash")
            limit = int(request.query.get("limit", 100))
            offset = int(request.query.get("offset", 0))

            results = self.database.telemetry.get_telemetry_history(
                destination_hash,
                limit,
                offset,
            )
            telemetry_list = []
            for r in results:
                unpacked = Telemeter.from_packed(r["data"])
                telemetry_list.append(
                    {
                        "destination_hash": r["destination_hash"],
                        "timestamp": r["timestamp"],
                        "telemetry": unpacked,
                        "physical_link": json.loads(r["physical_link"])
                        if r["physical_link"]
                        else None,
                        "updated_at": r["updated_at"],
                    },
                )
            return web.json_response({"telemetry": telemetry_list})

        # get latest telemetry for a destination
        @routes.get("/api/v1/telemetry/latest/{destination_hash}")
        async def get_latest_telemetry(request):
            destination_hash = request.match_info.get("destination_hash")
            r = self.database.telemetry.get_latest_telemetry(destination_hash)
            if not r:
                return web.json_response({"error": "No telemetry found"}, status=404)

            unpacked = Telemeter.from_packed(r["data"])
            return web.json_response(
                {
                    "destination_hash": r["destination_hash"],
                    "timestamp": r["timestamp"],
                    "telemetry": unpacked,
                    "physical_link": json.loads(r["physical_link"])
                    if r["physical_link"]
                    else None,
                    "updated_at": r["updated_at"],
                },
            )

        # upload offline map
        @routes.post("/api/v1/map/offline")
        async def upload_map_offline(request):
            try:
                reader = await request.multipart()
                field = await reader.next()
                if field.name != "file":
                    return web.json_response({"error": "No file field"}, status=400)

                filename = field.filename
                if not filename.endswith(".mbtiles"):
                    return web.json_response(
                        {"error": "Invalid file format, must be .mbtiles"},
                        status=400,
                    )

                # save to mbtiles dir
                mbtiles_dir = self.map_manager.get_mbtiles_dir()
                if not os.path.exists(mbtiles_dir):
                    os.makedirs(mbtiles_dir)

                dest_path = os.path.join(mbtiles_dir, filename)

                size = 0
                with open(dest_path, "wb") as f:
                    while True:
                        chunk = await field.read_chunk()
                        if not chunk:
                            break
                        size += len(chunk)
                        f.write(chunk)

                # close old connection and clear cache before update
                self.map_manager.close()

                # update config
                self.config.map_offline_path.set(dest_path)
                self.config.map_offline_enabled.set(True)

                # validate
                metadata = self.map_manager.get_metadata()
                if not metadata:
                    # delete if invalid
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    self.config.map_offline_path.set(None)
                    self.config.map_offline_enabled.set(False)
                    return web.json_response(
                        {
                            "error": "Invalid MBTiles file or unsupported format (vector maps not supported)",
                        },
                        status=400,
                    )

                return web.json_response(
                    {
                        "message": "Map uploaded successfully",
                        "metadata": metadata,
                    },
                )
            except Exception as e:
                RNS.log(f"Error uploading map: {e}", RNS.LOG_ERROR)
                return web.json_response({"error": str(e)}, status=500)

        # start map export
        @routes.post("/api/v1/map/export")
        async def start_map_export(request):
            try:
                data = await request.json()
                bbox = data.get("bbox")  # [min_lon, min_lat, max_lon, max_lat]
                min_zoom = int(data.get("min_zoom", 0))
                max_zoom = int(data.get("max_zoom", 10))
                name = data.get("name", "Exported Map")

                if not bbox or len(bbox) != 4:
                    return web.json_response({"error": "Invalid bbox"}, status=400)

                export_id = secrets.token_hex(8)
                self.map_manager.start_export(export_id, bbox, min_zoom, max_zoom, name)

                return web.json_response({"export_id": export_id})
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        # get map export status
        @routes.get("/api/v1/map/export/{export_id}")
        async def get_map_export_status(request):
            export_id = request.match_info.get("export_id")
            status = self.map_manager.get_export_status(export_id)
            if status:
                return web.json_response(status)
            return web.json_response({"error": "Export not found"}, status=404)

        # download exported map
        @routes.get("/api/v1/map/export/{export_id}/download")
        async def download_map_export(request):
            export_id = request.match_info.get("export_id")
            status = self.map_manager.get_export_status(export_id)
            if status and status.get("status") == "completed":
                file_path = status.get("file_path")
                if os.path.exists(file_path):
                    return web.FileResponse(
                        path=file_path,
                        headers={
                            "Content-Disposition": f'attachment; filename="map_export_{export_id}.mbtiles"',
                        },
                    )
            return web.json_response(
                {"error": "File not ready or not found"},
                status=404,
            )

        # cancel/delete map export
        @routes.delete("/api/v1/map/export/{export_id}")
        async def delete_map_export(request):
            export_id = request.match_info.get("export_id")
            if self.map_manager.cancel_export(export_id):
                return web.json_response({"message": "Export cancelled/deleted"})
            return web.json_response({"error": "Export not found"}, status=404)

        # MIME type fix middleware - ensures JavaScript files have correct Content-Type
        @web.middleware
        async def mime_type_middleware(request, handler):
            response = await handler(request)
            path = request.path
            if path.endswith(".js") or path.endswith(".mjs"):
                response.headers["Content-Type"] = (
                    "application/javascript; charset=utf-8"
                )
            elif path.endswith(".css"):
                response.headers["Content-Type"] = "text/css; charset=utf-8"
            elif path.endswith(".json"):
                response.headers["Content-Type"] = "application/json; charset=utf-8"
            elif path.endswith(".wasm"):
                response.headers["Content-Type"] = "application/wasm"
            elif path.endswith(".html"):
                response.headers["Content-Type"] = "text/html; charset=utf-8"
            return response

        # security headers middleware
        @web.middleware
        async def security_middleware(request, handler):
            response = await handler(request)
            # Add security headers to all responses
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            # CSP: allow localhost for development and Electron, websockets, and blob URLs
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob: https://*.tile.openstreetmap.org https://tile.openstreetmap.org; "
                "font-src 'self' data:; "
                "connect-src 'self' ws://localhost:* wss://localhost:* blob: https://*.tile.openstreetmap.org https://tile.openstreetmap.org https://nominatim.openstreetmap.org; "
                "media-src 'self' blob:; "
                "worker-src 'self' blob:; "
                "object-src 'none'; "
                "base-uri 'self';"
            )
            response.headers["Content-Security-Policy"] = csp
            return response

        # called when web app has started
        async def on_startup(app):
            # remember main event loop
            AsyncUtils.set_main_loop(asyncio.get_event_loop())

            # auto launch web browser
            if launch_browser:
                try:
                    protocol = "https" if use_https else "http"
                    webbrowser.open(f"{protocol}://127.0.0.1:{port}")
                except Exception:
                    print("failed to launch web browser")

        # create and run web app
        app = web.Application(
            client_max_size=1024 * 1024 * 50,
        )  # allow uploading files up to 50mb

        # setup session storage
        # aiohttp_session.setup must be called before other middlewares that use sessions

        # Ensure we have a valid 32-byte key for Fernet
        try:
            # First try decoding as base64 (since secrets.token_urlsafe produces base64)
            secret_key_bytes = base64.urlsafe_b64decode(self.session_secret_key + "===")
            if len(secret_key_bytes) < 32:
                # If too short, pad it
                secret_key_bytes = secret_key_bytes.ljust(32, b"\0")
            elif len(secret_key_bytes) > 32:
                # If too long, truncate it
                secret_key_bytes = secret_key_bytes[:32]
        except Exception:
            # Fallback to direct encoding and hashing to get exactly 32 bytes
            import hashlib

            secret_key_bytes = hashlib.sha256(
                self.session_secret_key.encode("utf-8")
            ).digest()

        setup_session(
            app,
            EncryptedCookieStorage(secret_key_bytes),
        )

        # add other middlewares
        app.middlewares.extend(
            [auth_middleware, mime_type_middleware, security_middleware],
        )

        app.add_routes(routes)
        
        # serve anything else from public folder
        # we use add_static here as it's more robust for serving directories
        public_dir = get_file_path("public")
        if os.path.exists(public_dir):
            app.router.add_static("/", public_dir, name="static", follow_symlinks=True)
        else:
            print(f"Warning: Static files directory not found at {public_dir}")

        app.on_shutdown.append(
            self.shutdown,
        )  # need to force close websockets and stop reticulum now
        app.on_startup.append(on_startup)

        protocol = "https" if use_https else "http"
        print(f"Starting web server on {protocol}://{host}:{port}")

        if use_https and ssl_context:
            web.run_app(app, host=host, port=port, ssl_context=ssl_context)
        else:
            web.run_app(app, host=host, port=port)

    # handle announcing
    async def announce(self):
        # update last announced at timestamp
        self.config.last_announced_at.set(int(time.time()))

        # send announce for lxmf (ensuring name is updated before announcing)
        self.local_lxmf_destination.display_name = self.config.display_name.get()
        self.message_router.announce(destination_hash=self.local_lxmf_destination.hash)

        # send announce for local propagation node (if enabled)
        if self.config.lxmf_local_propagation_node_enabled.get():
            self.message_router.announce_propagation_node()

        # send announce for telephone
        self.telephone_manager.announce()

        # tell websocket clients we just announced
        await self.send_announced_to_websocket_clients()

    # handle syncing propagation nodes
    async def sync_propagation_nodes(self):
        # update last synced at timestamp
        self.config.lxmf_preferred_propagation_node_last_synced_at.set(int(time.time()))

        # request messages from propagation node
        self.message_router.request_messages_from_propagation_node(self.identity)

        # send config to websocket clients (used to tell ui last synced at)
        await self.send_config_to_websocket_clients()

    # helper to parse boolean from possible string or bool
    @staticmethod
    def _parse_bool(value):
        if value is None:
            return False
        if isinstance(value, str):
            return value.lower() == "true"
        return bool(value)

    async def update_config(self, data):
        # update display name in config
        if "display_name" in data and data["display_name"] != "":
            self.config.display_name.set(data["display_name"])

        # update theme in config
        if "theme" in data and data["theme"] != "":
            self.config.theme.set(data["theme"])

        # update language in config
        if "language" in data and data["language"] != "":
            self.config.language.set(data["language"])

        # update auto announce interval
        if "auto_announce_interval_seconds" in data:
            # auto auto announce interval
            auto_announce_interval_seconds = int(data["auto_announce_interval_seconds"])
            self.config.auto_announce_interval_seconds.set(
                data["auto_announce_interval_seconds"],
            )

            # enable or disable auto announce based on interval
            if auto_announce_interval_seconds > 0:
                self.config.auto_announce_enabled.set(True)
            else:
                self.config.auto_announce_enabled.set(False)

        if "auto_resend_failed_messages_when_announce_received" in data:
            value = self._parse_bool(
                data["auto_resend_failed_messages_when_announce_received"]
            )
            self.config.auto_resend_failed_messages_when_announce_received.set(value)

        if "allow_auto_resending_failed_messages_with_attachments" in data:
            value = self._parse_bool(
                data["allow_auto_resending_failed_messages_with_attachments"]
            )
            self.config.allow_auto_resending_failed_messages_with_attachments.set(value)

        if "auto_send_failed_messages_to_propagation_node" in data:
            value = self._parse_bool(
                data["auto_send_failed_messages_to_propagation_node"]
            )
            self.config.auto_send_failed_messages_to_propagation_node.set(value)

        if "show_suggested_community_interfaces" in data:
            value = self._parse_bool(data["show_suggested_community_interfaces"])
            self.config.show_suggested_community_interfaces.set(value)

        if "lxmf_preferred_propagation_node_destination_hash" in data:
            # update config value
            value = data["lxmf_preferred_propagation_node_destination_hash"]
            self.config.lxmf_preferred_propagation_node_destination_hash.set(value)

            # update active propagation node
            self.set_active_propagation_node(value)

        # update inbound stamp cost (for direct delivery messages)
        if "lxmf_inbound_stamp_cost" in data:
            value = int(data["lxmf_inbound_stamp_cost"])
            # validate stamp cost (must be between 1 and 254)
            if value < 1:
                value = None
            elif value >= 255:
                value = 254
            self.config.lxmf_inbound_stamp_cost.set(value)
            # update the inbound stamp cost on the delivery destination
            self.message_router.set_inbound_stamp_cost(
                self.local_lxmf_destination.hash,
                value,
            )
            # re-announce to update the stamp cost in announces
            self.local_lxmf_destination.display_name = self.config.display_name.get()
            self.message_router.announce(
                destination_hash=self.local_lxmf_destination.hash,
            )

        # update propagation node stamp cost (for messages propagated through your node)
        if "lxmf_propagation_node_stamp_cost" in data:
            value = int(data["lxmf_propagation_node_stamp_cost"])
            # validate stamp cost (must be at least 13, per LXMF minimum)
            if value < 13:
                value = 13
            elif value >= 255:
                value = 254
            self.config.lxmf_propagation_node_stamp_cost.set(value)
            # update the propagation stamp cost on the router
            self.message_router.propagation_stamp_cost = value
            # re-announce propagation node if enabled
            if self.config.lxmf_local_propagation_node_enabled.get():
                self.message_router.announce_propagation_node()

        # update auto sync interval
        if "lxmf_preferred_propagation_node_auto_sync_interval_seconds" in data:
            value = int(
                data["lxmf_preferred_propagation_node_auto_sync_interval_seconds"],
            )
            self.config.lxmf_preferred_propagation_node_auto_sync_interval_seconds.set(
                value,
            )

        if "lxmf_local_propagation_node_enabled" in data:
            # update config value
            value = self._parse_bool(data["lxmf_local_propagation_node_enabled"])
            self.config.lxmf_local_propagation_node_enabled.set(value)

            # enable or disable local propagation node
            self.enable_local_propagation_node(value)

        # update lxmf user icon name in config
        if "lxmf_user_icon_name" in data:
            self.config.lxmf_user_icon_name.set(data["lxmf_user_icon_name"])

        # update lxmf user icon foreground colour in config
        if "lxmf_user_icon_foreground_colour" in data:
            self.config.lxmf_user_icon_foreground_colour.set(
                data["lxmf_user_icon_foreground_colour"],
            )

        # update lxmf user icon background colour in config
        if "lxmf_user_icon_background_colour" in data:
            self.config.lxmf_user_icon_background_colour.set(
                data["lxmf_user_icon_background_colour"],
            )

        # update archiver settings
        if "page_archiver_enabled" in data:
            self.config.page_archiver_enabled.set(
                self._parse_bool(data["page_archiver_enabled"])
            )

        if "page_archiver_max_versions" in data:
            self.config.page_archiver_max_versions.set(
                int(data["page_archiver_max_versions"]),
            )

        if "archives_max_storage_gb" in data:
            self.config.archives_max_storage_gb.set(
                int(data["archives_max_storage_gb"]),
            )

        # update crawler settings
        if "crawler_enabled" in data:
            self.config.crawler_enabled.set(self._parse_bool(data["crawler_enabled"]))

        if "crawler_max_retries" in data:
            self.config.crawler_max_retries.set(int(data["crawler_max_retries"]))

        if "crawler_retry_delay_seconds" in data:
            self.config.crawler_retry_delay_seconds.set(
                int(data["crawler_retry_delay_seconds"]),
            )

        if "crawler_max_concurrent" in data:
            self.config.crawler_max_concurrent.set(int(data["crawler_max_concurrent"]))

        if "auth_enabled" in data:
            value = self._parse_bool(data["auth_enabled"])
            self.config.auth_enabled.set(value)
            self.auth_enabled = value

            # if disabling auth, also remove the password hash from config
            if not value:
                self.config.auth_password_hash.set(None)

        # update map settings
        if "map_offline_enabled" in data:
            self.config.map_offline_enabled.set(
                self._parse_bool(data["map_offline_enabled"])
            )

        if "map_default_lat" in data:
            self.config.map_default_lat.set(str(data["map_default_lat"]))

        if "map_default_lon" in data:
            self.config.map_default_lon.set(str(data["map_default_lon"]))

        if "map_default_zoom" in data:
            self.config.map_default_zoom.set(int(data["map_default_zoom"]))

        if "map_mbtiles_dir" in data:
            self.config.map_mbtiles_dir.set(data["map_mbtiles_dir"])

        if "map_tile_cache_enabled" in data:
            self.config.map_tile_cache_enabled.set(
                self._parse_bool(data["map_tile_cache_enabled"])
            )

        if "map_tile_server_url" in data:
            self.config.map_tile_server_url.set(data["map_tile_server_url"])

        if "map_nominatim_api_url" in data:
            self.config.map_nominatim_api_url.set(data["map_nominatim_api_url"])

        # update voicemail settings
        if "voicemail_enabled" in data:
            self.config.voicemail_enabled.set(
                self._parse_bool(data["voicemail_enabled"])
            )

        if "voicemail_greeting" in data:
            self.config.voicemail_greeting.set(data["voicemail_greeting"])

        if "voicemail_auto_answer_delay_seconds" in data:
            self.config.voicemail_auto_answer_delay_seconds.set(
                int(data["voicemail_auto_answer_delay_seconds"]),
            )

        if "voicemail_max_recording_seconds" in data:
            self.config.voicemail_max_recording_seconds.set(
                int(data["voicemail_max_recording_seconds"]),
            )

        # update ringtone settings
        if "custom_ringtone_enabled" in data:
            self.config.custom_ringtone_enabled.set(
                self._parse_bool(data["custom_ringtone_enabled"])
            )

        # send config to websocket clients
        await self.send_config_to_websocket_clients()

    # converts nomadnetwork page variables from a string to a map
    # converts: "field1=123|field2=456"
    # to the following map:
    # - var_field1: 123
    # - var_field2: 456
    @staticmethod
    def convert_nomadnet_string_data_to_map(path_data: str | None):
        data = {}
        if path_data is not None:
            for field in path_data.split("|"):
                if "=" in field:
                    variable_name, variable_value = field.split("=")
                    data[f"var_{variable_name}"] = variable_value
                else:
                    print(f"unhandled field: {field}")
        return data

    @staticmethod
    def convert_nomadnet_field_data_to_map(field_data):
        data = {}
        if field_data is not None or "{}":
            try:
                json_data = field_data
                if isinstance(json_data, dict):
                    # add the prefixed keys to the result dictionary
                    data = {f"field_{key}": value for key, value in json_data.items()}
                else:
                    return None
            except Exception as e:
                print(f"skipping invalid field data: {e}")

        return data

    # archives a page version
    def archive_page(
        self,
        destination_hash: str,
        page_path: str,
        content: str,
        is_manual: bool = False,
    ):
        if not is_manual and not self.config.page_archiver_enabled.get():
            return

        self.archiver_manager.archive_page(
            destination_hash,
            page_path,
            content,
            max_versions=self.config.page_archiver_max_versions.get(),
            max_storage_gb=self.config.archives_max_storage_gb.get(),
        )

    # returns archived page versions for a given destination and path
    def get_archived_page_versions(self, destination_hash: str, page_path: str):
        return self.database.misc.get_archived_page_versions(
            destination_hash,
            page_path,
        )

    # flushes all archived pages
    def flush_all_archived_pages(self):
        self.database.misc.delete_archived_pages()

    # handle data received from websocket client
    async def on_websocket_data_received(self, client, data):
        # get type from client data
        _type = data["type"]

        # handle ping
        if _type == "ping":
            AsyncUtils.run_async(
                client.send_str(
                    json.dumps(
                        {
                            "type": "pong",
                        },
                    ),
                ),
            )

        # handle updating config
        elif _type == "config.set":
            # get config from websocket
            config = data["config"]

            # update config
            await self.update_config(config)

        # handle canceling a download
        elif _type == "nomadnet.download.cancel":
            # get data from websocket client
            download_id = data["download_id"]

            # cancel the download
            if download_id in self.active_downloads:
                downloader = self.active_downloads[download_id]
                downloader.cancel()
                del self.active_downloads[download_id]

                # notify client
                AsyncUtils.run_async(
                    client.send_str(
                        json.dumps(
                            {
                                "type": "nomadnet.download.cancelled",
                                "download_id": download_id,
                            },
                        ),
                    ),
                )

        # handle getting page archives
        elif _type == "nomadnet.page.archives.get":
            destination_hash = data["destination_hash"]
            page_path = data["page_path"]
            archives = self.get_archived_page_versions(destination_hash, page_path)

            AsyncUtils.run_async(
                client.send_str(
                    json.dumps(
                        {
                            "type": "nomadnet.page.archives",
                            "destination_hash": destination_hash,
                            "page_path": page_path,
                            "archives": [
                                {
                                    "id": archive.id,
                                    "hash": archive.hash,
                                    "created_at": archive.created_at.isoformat()
                                    if hasattr(archive.created_at, "isoformat")
                                    else str(archive.created_at),
                                }
                                for archive in archives
                            ],
                        },
                    ),
                ),
            )

        # handle loading a specific archived page version
        elif _type == "nomadnet.page.archive.load":
            archive_id = data["archive_id"]
            archive = self.database.misc.get_archived_page_by_id(archive_id)

            if archive:
                AsyncUtils.run_async(
                    client.send_str(
                        json.dumps(
                            {
                                "type": "nomadnet.page.download",
                                "download_id": data.get("download_id"),
                                "nomadnet_page_download": {
                                    "status": "success",
                                    "destination_hash": archive["destination_hash"],
                                    "page_path": archive["page_path"],
                                    "page_content": archive["content"],
                                    "is_archived_version": True,
                                    "archived_at": archive["created_at"],
                                },
                            },
                        ),
                    ),
                )

        # handle flushing all archived pages
        elif _type == "nomadnet.page.archive.flush":
            self.flush_all_archived_pages()
            # notify config updated
            AsyncUtils.run_async(self.send_config_to_websocket_clients())

        # handle manual page archiving
        elif _type == "nomadnet.page.archive.add":
            destination_hash = data["destination_hash"]
            page_path = data["page_path"]
            content = data["content"]
            self.archive_page(destination_hash, page_path, content, is_manual=True)

            # notify client that page was archived
            AsyncUtils.run_async(
                client.send_str(
                    json.dumps(
                        {
                            "type": "nomadnet.page.archive.added",
                            "destination_hash": destination_hash,
                            "page_path": page_path,
                        },
                    ),
                ),
            )

        # handle downloading a file from a nomadnet node
        elif _type == "nomadnet.file.download":
            # get data from websocket client
            destination_hash = data["nomadnet_file_download"]["destination_hash"]
            file_path = data["nomadnet_file_download"]["file_path"]

            # convert destination hash to bytes
            destination_hash = bytes.fromhex(destination_hash)

            # generate download id
            self.download_id_counter += 1
            download_id = self.download_id_counter

            # handle successful file download
            def on_file_download_success(file_name, file_bytes):
                # remove from active downloads
                if download_id in self.active_downloads:
                    del self.active_downloads[download_id]

                # Track download speed
                download_size = len(file_bytes)
                if hasattr(downloader, "start_time") and downloader.start_time:
                    download_duration = time.time() - downloader.start_time
                    if download_duration > 0:
                        self.download_speeds.append((download_size, download_duration))
                        # Keep only last 100 downloads for average calculation
                        if len(self.download_speeds) > 100:
                            self.download_speeds.pop(0)

                AsyncUtils.run_async(
                    client.send_str(
                        json.dumps(
                            {
                                "type": "nomadnet.file.download",
                                "download_id": download_id,
                                "nomadnet_file_download": {
                                    "status": "success",
                                    "destination_hash": destination_hash.hex(),
                                    "file_path": file_path,
                                    "file_name": file_name,
                                    "file_bytes": base64.b64encode(file_bytes).decode(
                                        "utf-8",
                                    ),
                                },
                            },
                        ),
                    ),
                )

            # handle file download failure
            def on_file_download_failure(failure_reason):
                # remove from active downloads
                if download_id in self.active_downloads:
                    del self.active_downloads[download_id]

                AsyncUtils.run_async(
                    client.send_str(
                        json.dumps(
                            {
                                "type": "nomadnet.file.download",
                                "download_id": download_id,
                                "nomadnet_file_download": {
                                    "status": "failure",
                                    "failure_reason": failure_reason,
                                    "destination_hash": destination_hash.hex(),
                                    "file_path": file_path,
                                },
                            },
                        ),
                    ),
                )

            # handle file download progress
            def on_file_download_progress(progress):
                AsyncUtils.run_async(
                    client.send_str(
                        json.dumps(
                            {
                                "type": "nomadnet.file.download",
                                "download_id": download_id,
                                "nomadnet_file_download": {
                                    "status": "progress",
                                    "progress": progress,
                                    "destination_hash": destination_hash.hex(),
                                    "file_path": file_path,
                                },
                            },
                        ),
                    ),
                )

            # download the file
            downloader = NomadnetFileDownloader(
                destination_hash,
                file_path,
                on_file_download_success,
                on_file_download_failure,
                on_file_download_progress,
            )
            downloader.start_time = time.time()
            self.active_downloads[download_id] = downloader

            # notify client download started
            AsyncUtils.run_async(
                client.send_str(
                    json.dumps(
                        {
                            "type": "nomadnet.file.download",
                            "download_id": download_id,
                            "nomadnet_file_download": {
                                "status": "started",
                                "destination_hash": destination_hash.hex(),
                                "file_path": file_path,
                            },
                        },
                    ),
                ),
            )

            AsyncUtils.run_async(downloader.download())

        # handle downloading a page from a nomadnet node
        elif _type == "nomadnet.page.download":
            # get data from websocket client
            destination_hash = data["nomadnet_page_download"]["destination_hash"]
            page_path = data["nomadnet_page_download"]["page_path"]
            field_data = data["nomadnet_page_download"]["field_data"]

            # generate download id
            self.download_id_counter += 1
            download_id = self.download_id_counter

            combined_data = {}
            # parse data from page path
            # example: hash:/page/index.mu`field1=123|field2=456
            page_data = None
            page_path_to_download = page_path
            if "`" in page_path:
                page_path_parts = page_path.split("`")
                page_path_to_download = page_path_parts[0]
                page_data = self.convert_nomadnet_string_data_to_map(page_path_parts[1])

            # Field data
            field_data = self.convert_nomadnet_field_data_to_map(field_data)

            # Combine page data and field data
            if page_data is not None:
                combined_data.update(page_data)
            if field_data is not None:
                combined_data.update(field_data)

            # convert destination hash to bytes
            destination_hash = bytes.fromhex(destination_hash)

            # handle successful page download
            def on_page_download_success(page_content):
                # remove from active downloads
                if download_id in self.active_downloads:
                    del self.active_downloads[download_id]

                # archive the page if enabled
                self.archive_page(destination_hash.hex(), page_path, page_content)

                AsyncUtils.run_async(
                    client.send_str(
                        json.dumps(
                            {
                                "type": "nomadnet.page.download",
                                "download_id": download_id,
                                "nomadnet_page_download": {
                                    "status": "success",
                                    "destination_hash": destination_hash.hex(),
                                    "page_path": page_path,
                                    "page_content": page_content,
                                },
                            },
                        ),
                    ),
                )

            # handle page download failure
            def on_page_download_failure(failure_reason):
                # remove from active downloads
                if download_id in self.active_downloads:
                    del self.active_downloads[download_id]

                # check if there are any archived versions
                has_archives = (
                    len(
                        self.get_archived_page_versions(
                            destination_hash.hex(),
                            page_path,
                        ),
                    )
                    > 0
                )

                AsyncUtils.run_async(
                    client.send_str(
                        json.dumps(
                            {
                                "type": "nomadnet.page.download",
                                "download_id": download_id,
                                "nomadnet_page_download": {
                                    "status": "failure",
                                    "failure_reason": failure_reason,
                                    "destination_hash": destination_hash.hex(),
                                    "page_path": page_path,
                                    "has_archives": has_archives,
                                },
                            },
                        ),
                    ),
                )

            # handle page download progress
            def on_page_download_progress(progress):
                AsyncUtils.run_async(
                    client.send_str(
                        json.dumps(
                            {
                                "type": "nomadnet.page.download",
                                "download_id": download_id,
                                "nomadnet_page_download": {
                                    "status": "progress",
                                    "progress": progress,
                                    "destination_hash": destination_hash.hex(),
                                    "page_path": page_path,
                                },
                            },
                        ),
                    ),
                )

            # download the page
            downloader = NomadnetPageDownloader(
                destination_hash,
                page_path_to_download,
                combined_data,
                on_page_download_success,
                on_page_download_failure,
                on_page_download_progress,
            )
            self.active_downloads[download_id] = downloader

            # notify client download started
            AsyncUtils.run_async(
                client.send_str(
                    json.dumps(
                        {
                            "type": "nomadnet.page.download",
                            "download_id": download_id,
                            "nomadnet_page_download": {
                                "status": "started",
                                "destination_hash": destination_hash.hex(),
                                "page_path": page_path,
                            },
                        },
                    ),
                ),
            )

            AsyncUtils.run_async(downloader.download())

        # handle lxmf forwarding rules
        elif _type == "lxmf.forwarding.rules.get":
            rules = self.database.misc.get_forwarding_rules()
            AsyncUtils.run_async(
                client.send_str(
                    json.dumps(
                        {
                            "type": "lxmf.forwarding.rules",
                            "rules": [
                                {
                                    "id": rule["id"],
                                    "identity_hash": rule["identity_hash"],
                                    "forward_to_hash": rule["forward_to_hash"],
                                    "source_filter_hash": rule["source_filter_hash"],
                                    "is_active": bool(rule["is_active"]),
                                }
                                for rule in rules
                            ],
                        },
                    ),
                ),
            )

        elif _type == "lxmf.forwarding.rule.add":
            rule_data = data["rule"]
            self.database.misc.create_forwarding_rule(
                identity_hash=rule_data.get("identity_hash"),
                forward_to_hash=rule_data["forward_to_hash"],
                source_filter_hash=rule_data.get("source_filter_hash"),
                is_active=rule_data.get("is_active", True),
                name=rule_data.get("name"),
            )
            # notify updated
            AsyncUtils.run_async(
                self.on_websocket_data_received(
                    client,
                    {"type": "lxmf.forwarding.rules.get"},
                ),
            )

        elif _type == "lxmf.forwarding.rule.delete":
            rule_id = data["id"]
            self.database.misc.delete_forwarding_rule(rule_id)
            # notify updated
            AsyncUtils.run_async(
                self.on_websocket_data_received(
                    client,
                    {"type": "lxmf.forwarding.rules.get"},
                ),
            )

        elif _type == "lxmf.forwarding.rule.toggle":
            rule_id = data["id"]
            self.database.misc.toggle_forwarding_rule(rule_id)
            # notify updated
            AsyncUtils.run_async(
                self.on_websocket_data_received(
                    client,
                    {"type": "lxmf.forwarding.rules.get"},
                ),
            )

        # unhandled type
        else:
            print("unhandled client message type: " + _type)

    # broadcast provided data to all connected websocket clients
    async def websocket_broadcast(self, data):
        for websocket_client in self.websocket_clients:
            try:
                await websocket_client.send_str(data)
            except Exception as e:
                # do nothing if failed to broadcast to a specific websocket client
                print(f"Failed to broadcast to websocket client: {e}")

    # broadcasts config to all websocket clients
    async def send_config_to_websocket_clients(self):
        await self.websocket_broadcast(
            json.dumps(
                {
                    "type": "config",
                    "config": self.get_config_dict(),
                },
            ),
        )

    # broadcasts to all websocket clients that we just announced
    async def send_announced_to_websocket_clients(self):
        await self.websocket_broadcast(
            json.dumps(
                {
                    "type": "announced",
                },
            ),
        )

    # returns a dictionary of config
    def get_config_dict(self):
        return {
            "display_name": self.config.display_name.get(),
            "identity_hash": self.identity.hexhash,
            "lxmf_address_hash": self.local_lxmf_destination.hexhash,
            "telephone_address_hash": self.telephone_manager.telephone.destination.hexhash
            if self.telephone_manager.telephone
            else None,
            "is_transport_enabled": self.reticulum.transport_enabled(),
            "auto_announce_enabled": self.config.auto_announce_enabled.get(),
            "auto_announce_interval_seconds": self.config.auto_announce_interval_seconds.get(),
            "last_announced_at": self.config.last_announced_at.get(),
            "theme": self.config.theme.get(),
            "language": self.config.language.get(),
            "auto_resend_failed_messages_when_announce_received": self.config.auto_resend_failed_messages_when_announce_received.get(),
            "allow_auto_resending_failed_messages_with_attachments": self.config.allow_auto_resending_failed_messages_with_attachments.get(),
            "auto_send_failed_messages_to_propagation_node": self.config.auto_send_failed_messages_to_propagation_node.get(),
            "show_suggested_community_interfaces": self.config.show_suggested_community_interfaces.get(),
            "lxmf_local_propagation_node_enabled": self.config.lxmf_local_propagation_node_enabled.get(),
            "lxmf_local_propagation_node_address_hash": self.message_router.propagation_destination.hexhash,
            "lxmf_preferred_propagation_node_destination_hash": self.config.lxmf_preferred_propagation_node_destination_hash.get(),
            "lxmf_preferred_propagation_node_auto_sync_interval_seconds": self.config.lxmf_preferred_propagation_node_auto_sync_interval_seconds.get(),
            "lxmf_preferred_propagation_node_last_synced_at": self.config.lxmf_preferred_propagation_node_last_synced_at.get(),
            "lxmf_user_icon_name": self.config.lxmf_user_icon_name.get(),
            "lxmf_user_icon_foreground_colour": self.config.lxmf_user_icon_foreground_colour.get(),
            "lxmf_user_icon_background_colour": self.config.lxmf_user_icon_background_colour.get(),
            "lxmf_inbound_stamp_cost": self.config.lxmf_inbound_stamp_cost.get(),
            "lxmf_propagation_node_stamp_cost": self.config.lxmf_propagation_node_stamp_cost.get(),
            "page_archiver_enabled": self.config.page_archiver_enabled.get(),
            "page_archiver_max_versions": self.config.page_archiver_max_versions.get(),
            "archives_max_storage_gb": self.config.archives_max_storage_gb.get(),
            "crawler_enabled": self.config.crawler_enabled.get(),
            "crawler_max_retries": self.config.crawler_max_retries.get(),
            "crawler_retry_delay_seconds": self.config.crawler_retry_delay_seconds.get(),
            "crawler_max_concurrent": self.config.crawler_max_concurrent.get(),
            "auth_enabled": self.auth_enabled,
            "voicemail_enabled": self.config.voicemail_enabled.get(),
            "voicemail_greeting": self.config.voicemail_greeting.get(),
            "voicemail_auto_answer_delay_seconds": self.config.voicemail_auto_answer_delay_seconds.get(),
            "voicemail_max_recording_seconds": self.config.voicemail_max_recording_seconds.get(),
            "custom_ringtone_enabled": self.config.custom_ringtone_enabled.get(),
            "ringtone_filename": self.config.ringtone_filename.get(),
            "map_offline_enabled": self.config.map_offline_enabled.get(),
            "map_mbtiles_dir": self.config.map_mbtiles_dir.get(),
            "map_tile_cache_enabled": self.config.map_tile_cache_enabled.get(),
            "map_default_lat": self.config.map_default_lat.get(),
            "map_default_lon": self.config.map_default_lon.get(),
            "map_default_zoom": self.config.map_default_zoom.get(),
            "map_tile_server_url": self.config.map_tile_server_url.get(),
            "map_nominatim_api_url": self.config.map_nominatim_api_url.get(),
        }

    # try and get a name for the provided identity hash
    def get_name_for_identity_hash(self, identity_hash: str):
        # 1. try recall identity and calculate lxmf destination hash
        identity = self.recall_identity(identity_hash)
        if identity is not None:
            # get lxmf.delivery destination hash
            lxmf_destination_hash = RNS.Destination.hash(
                identity,
                "lxmf",
                "delivery",
            ).hex()

            # use custom name if available
            custom_name = self.database.announces.get_custom_display_name(
                lxmf_destination_hash,
            )
            if custom_name is not None:
                return custom_name

            # use lxmf name if available
            lxmf_name = self.get_lxmf_conversation_name(
                lxmf_destination_hash,
                default_name=None,
            )
            if lxmf_name is not None:
                return lxmf_name

        # 2. if identity recall failed, or we couldn't find a name for the calculated hash
        # try to look up an lxmf.delivery announce with this identity_hash in the database
        announces = self.database.announces.get_filtered_announces(
            aspect="lxmf.delivery",
            search_term=identity_hash,
        )
        if announces:
            for announce in announces:
                # search_term matches destination_hash OR identity_hash in the DAO.
                # We want to be sure it's the identity_hash we're looking for.
                if announce["identity_hash"] == identity_hash:
                    lxmf_destination_hash = announce["destination_hash"]

                    # check custom name for this hash
                    custom_name = self.database.announces.get_custom_display_name(
                        lxmf_destination_hash,
                    )
                    if custom_name is not None:
                        return custom_name

                    # check lxmf name from app_data
                    if announce["app_data"] is not None:
                        lxmf_name = ReticulumMeshChat.parse_lxmf_display_name(
                            app_data_base64=announce["app_data"],
                            default_value=None,
                        )
                        if lxmf_name is not None:
                            return lxmf_name

        # couldn't find a name for this identity
        return None

    # recall identity from reticulum or database
    def get_lxmf_destination_hash_for_identity_hash(self, identity_hash: str):
        identity = self.recall_identity(identity_hash)
        if identity is not None:
            return RNS.Destination.hash(identity, "lxmf", "delivery").hex()

        # fallback to announces
        announces = self.database.announces.get_filtered_announces(
            aspect="lxmf.delivery",
            search_term=identity_hash,
        )
        if announces:
            for announce in announces:
                if announce["identity_hash"] == identity_hash:
                    return announce["destination_hash"]
        return None

    def recall_identity(self, hash_hex: str) -> RNS.Identity | None:
        try:
            # 1. try reticulum recall (works for both identity and destination hashes)
            hash_bytes = bytes.fromhex(hash_hex)
            identity = RNS.Identity.recall(hash_bytes)
            if identity:
                return identity

            # 2. try database lookup
            # lookup by destination hash first
            announce = self.database.announces.get_announce_by_hash(hash_hex)
            if announce:
                announce = dict(announce)

            if not announce:
                # lookup by identity hash
                results = self.database.announces.get_filtered_announces(
                    search_term=hash_hex,
                )
                if results:
                    # find first one with a public key
                    for res in results:
                        res_dict = dict(res)
                        if res_dict.get("identity_public_key"):
                            announce = res_dict
                            break

            if announce and announce.get("identity_public_key"):
                public_key = base64.b64decode(announce["identity_public_key"])
                identity = RNS.Identity(create_keys=False)
                if identity.load_public_key(public_key):
                    return identity

        except Exception as e:
            print(f"Error recalling identity for {hash_hex}: {e}")

        return None

    # convert an lxmf message to a dictionary, for sending over websocket
    def convert_lxmf_message_to_dict(
        self,
        lxmf_message: LXMF.LXMessage,
        include_attachments: bool = True,
    ):
        # handle fields
        fields = {}
        message_fields = lxmf_message.get_fields()
        for field_type in message_fields:
            value = message_fields[field_type]

            # handle file attachments field
            if field_type == LXMF.FIELD_FILE_ATTACHMENTS:
                # process file attachments
                file_attachments = []
                for file_attachment in value:
                    file_name = file_attachment[0]
                    file_bytes = None
                    if include_attachments:
                        file_bytes = base64.b64encode(file_attachment[1]).decode(
                            "utf-8",
                        )

                    file_attachments.append(
                        {
                            "file_name": file_name,
                            "file_bytes": file_bytes,
                        },
                    )

                # add to fields
                fields["file_attachments"] = file_attachments

            # handle image field
            if field_type == LXMF.FIELD_IMAGE:
                image_type = value[0]
                image_bytes = None
                if include_attachments:
                    image_bytes = base64.b64encode(value[1]).decode("utf-8")

                fields["image"] = {
                    "image_type": image_type,
                    "image_bytes": image_bytes,
                }

            # handle audio field
            if field_type == LXMF.FIELD_AUDIO:
                audio_mode = value[0]
                audio_bytes = None
                if include_attachments:
                    audio_bytes = base64.b64encode(value[1]).decode("utf-8")

                fields["audio"] = {
                    "audio_mode": audio_mode,
                    "audio_bytes": audio_bytes,
                }

            # handle telemetry field
            if field_type == LXMF.FIELD_TELEMETRY:
                fields["telemetry"] = Telemeter.from_packed(value)

        # convert 0.0-1.0 progress to 0.00-100 percentage
        progress_percentage = round(lxmf_message.progress * 100, 2)

        # get rssi
        rssi = lxmf_message.rssi
        if rssi is None:
            rssi = self.reticulum.get_packet_rssi(lxmf_message.hash)

        # get snr
        snr = lxmf_message.snr
        if snr is None:
            snr = self.reticulum.get_packet_snr(lxmf_message.hash)

        # get quality
        quality = lxmf_message.q
        if quality is None:
            quality = self.reticulum.get_packet_q(lxmf_message.hash)

        return {
            "hash": lxmf_message.hash.hex(),
            "source_hash": lxmf_message.source_hash.hex(),
            "destination_hash": lxmf_message.destination_hash.hex(),
            "is_incoming": lxmf_message.incoming,
            "state": self.convert_lxmf_state_to_string(lxmf_message),
            "progress": progress_percentage,
            "method": self.convert_lxmf_method_to_string(lxmf_message),
            "delivery_attempts": lxmf_message.delivery_attempts,
            "next_delivery_attempt_at": getattr(
                lxmf_message,
                "next_delivery_attempt",
                None,
            ),  # attribute may not exist yet
            "title": lxmf_message.title.decode("utf-8") if lxmf_message.title else "",
            "content": lxmf_message.content.decode("utf-8")
            if lxmf_message.content
            else "",
            "fields": fields,
            "timestamp": lxmf_message.timestamp,
            "rssi": rssi,
            "snr": snr,
            "quality": quality,
        }

    # convert lxmf state to a human friendly string
    @staticmethod
    def convert_lxmf_state_to_string(lxmf_message: LXMF.LXMessage):
        # convert state to string
        lxmf_message_state = "unknown"
        if lxmf_message.state == LXMF.LXMessage.GENERATING:
            lxmf_message_state = "generating"
        elif lxmf_message.state == LXMF.LXMessage.OUTBOUND:
            lxmf_message_state = "outbound"
        elif lxmf_message.state == LXMF.LXMessage.SENDING:
            lxmf_message_state = "sending"
        elif lxmf_message.state == LXMF.LXMessage.SENT:
            lxmf_message_state = "sent"
        elif lxmf_message.state == LXMF.LXMessage.DELIVERED:
            lxmf_message_state = "delivered"
        elif lxmf_message.state == LXMF.LXMessage.REJECTED:
            lxmf_message_state = "rejected"
        elif lxmf_message.state == LXMF.LXMessage.CANCELLED:
            lxmf_message_state = "cancelled"
        elif lxmf_message.state == LXMF.LXMessage.FAILED:
            lxmf_message_state = "failed"

        return lxmf_message_state

    # convert lxmf method to a human friendly string
    @staticmethod
    def convert_lxmf_method_to_string(lxmf_message: LXMF.LXMessage):
        # convert method to string
        lxmf_message_method = "unknown"
        if lxmf_message.method == LXMF.LXMessage.OPPORTUNISTIC:
            lxmf_message_method = "opportunistic"
        elif lxmf_message.method == LXMF.LXMessage.DIRECT:
            lxmf_message_method = "direct"
        elif lxmf_message.method == LXMF.LXMessage.PROPAGATED:
            lxmf_message_method = "propagated"
        elif lxmf_message.method == LXMF.LXMessage.PAPER:
            lxmf_message_method = "paper"

        return lxmf_message_method

    @staticmethod
    def convert_propagation_node_state_to_string(state):
        # map states to strings
        state_map = {
            LXMRouter.PR_IDLE: "idle",
            LXMRouter.PR_PATH_REQUESTED: "path_requested",
            LXMRouter.PR_LINK_ESTABLISHING: "link_establishing",
            LXMRouter.PR_LINK_ESTABLISHED: "link_established",
            LXMRouter.PR_REQUEST_SENT: "request_sent",
            LXMRouter.PR_RECEIVING: "receiving",
            LXMRouter.PR_RESPONSE_RECEIVED: "response_received",
            LXMRouter.PR_COMPLETE: "complete",
            LXMRouter.PR_NO_PATH: "no_path",
            LXMRouter.PR_LINK_FAILED: "link_failed",
            LXMRouter.PR_TRANSFER_FAILED: "transfer_failed",
            LXMRouter.PR_NO_IDENTITY_RCVD: "no_identity_received",
            LXMRouter.PR_NO_ACCESS: "no_access",
            LXMRouter.PR_FAILED: "failed",
        }

        # return string for state, or fallback to unknown
        if state in state_map:
            return state_map[state]
        return "unknown"

    # convert database announce to a dictionary
    def convert_db_announce_to_dict(self, announce):
        # convert to dict if it's a sqlite3.Row
        if not isinstance(announce, dict):
            announce = dict(announce)

        # parse display name from announce
        display_name = None
        if announce["aspect"] == "lxmf.delivery":
            display_name = self.parse_lxmf_display_name(announce["app_data"])
        elif announce["aspect"] == "nomadnetwork.node":
            display_name = ReticulumMeshChat.parse_nomadnetwork_node_display_name(
                announce["app_data"],
            )
        elif announce["aspect"] == "lxst.telephony":
            display_name = announce.get("display_name") or "Anonymous Peer"

        # Try to find associated LXMF destination hash if this is a telephony announce
        lxmf_destination_hash = None
        if announce["aspect"] == "lxst.telephony" and announce.get("identity_hash"):
            # 1. Check if we already have an LXMF announce for this identity
            lxmf_announces = self.database.announces.get_filtered_announces(
                aspect="lxmf.delivery",
                search_term=announce["identity_hash"],
            )
            if lxmf_announces:
                for lxmf_a in lxmf_announces:
                    if lxmf_a["identity_hash"] == announce["identity_hash"]:
                        lxmf_destination_hash = lxmf_a["destination_hash"]
                        # Also update display name if telephony one was empty
                        if not display_name or display_name == "Anonymous Peer":
                            display_name = self.parse_lxmf_display_name(
                                lxmf_a["app_data"]
                            )
                        break

            # 2. If not found in announces, try to recall identity and calculate LXMF hash
            if not lxmf_destination_hash:
                try:
                    identity_hash_bytes = bytes.fromhex(announce["identity_hash"])
                    identity = RNS.Identity.recall(identity_hash_bytes)
                    if not identity and announce.get("identity_public_key"):
                        # Try to load from public key if recall failed
                        public_key = base64.b64decode(announce["identity_public_key"])
                        identity = RNS.Identity(create_keys=False)
                        if not identity.load_public_key(public_key):
                            identity = None

                    if identity:
                        lxmf_destination_hash = RNS.Destination.hash(
                            identity,
                            "lxmf",
                            "delivery",
                        ).hex()
                except Exception:
                    pass

        # find lxmf user icon from database
        lxmf_user_icon = None
        # Try multiple potential hashes for the icon
        icon_hashes_to_check = []
        if lxmf_destination_hash:
            icon_hashes_to_check.append(lxmf_destination_hash)
        icon_hashes_to_check.append(announce["destination_hash"])

        db_lxmf_user_icon = None
        for icon_hash in icon_hashes_to_check:
            db_lxmf_user_icon = self.database.misc.get_user_icon(icon_hash)
            if db_lxmf_user_icon:
                break

        if db_lxmf_user_icon:
            lxmf_user_icon = {
                "icon_name": db_lxmf_user_icon["icon_name"],
                "foreground_colour": db_lxmf_user_icon["foreground_colour"],
                "background_colour": db_lxmf_user_icon["background_colour"],
            }

        # get current hops away
        hops = RNS.Transport.hops_to(bytes.fromhex(announce["destination_hash"]))

        # ensure created_at and updated_at have Z suffix for UTC if they don't have a timezone
        created_at = str(announce["created_at"])
        if created_at and "+" not in created_at and "Z" not in created_at:
            created_at += "Z"

        updated_at = str(announce["updated_at"])
        if updated_at and "+" not in updated_at and "Z" not in updated_at:
            updated_at += "Z"

        return {
            "id": announce["id"],
            "destination_hash": announce["destination_hash"],
            "aspect": announce["aspect"],
            "identity_hash": announce["identity_hash"],
            "identity_public_key": announce["identity_public_key"],
            "app_data": announce["app_data"],
            "hops": hops,
            "rssi": announce["rssi"],
            "snr": announce["snr"],
            "quality": announce["quality"],
            "display_name": display_name,
            "lxmf_destination_hash": lxmf_destination_hash,
            "custom_display_name": self.get_custom_destination_display_name(
                announce["destination_hash"],
            ),
            "lxmf_user_icon": lxmf_user_icon,
            "created_at": created_at,
            "updated_at": updated_at,
        }

    # convert database favourite to a dictionary
    @staticmethod
    def convert_db_favourite_to_dict(favourite):
        # ensure created_at and updated_at have Z suffix for UTC if they don't have a timezone
        created_at = str(favourite["created_at"])
        if created_at and "+" not in created_at and "Z" not in created_at:
            created_at += "Z"

        updated_at = str(favourite["updated_at"])
        if updated_at and "+" not in updated_at and "Z" not in updated_at:
            updated_at += "Z"

        return {
            "id": favourite["id"],
            "destination_hash": favourite["destination_hash"],
            "display_name": favourite["display_name"],
            "aspect": favourite["aspect"],
            "created_at": created_at,
            "updated_at": updated_at,
        }

    # convert database lxmf message to a dictionary
    @staticmethod
    def convert_db_lxmf_message_to_dict(
        db_lxmf_message,
        include_attachments: bool = False,
    ):
        fields = json.loads(db_lxmf_message["fields"])

        # strip attachments if requested
        if not include_attachments:
            if "image" in fields:
                # keep type but strip bytes
                image_size = 0
                if fields["image"].get("image_bytes"):
                    try:
                        image_size = len(
                            base64.b64decode(fields["image"]["image_bytes"]),
                        )
                    except Exception as e:
                        print(f"Failed to decode image bytes: {e}")
                fields["image"] = {
                    "image_type": fields["image"].get("image_type"),
                    "image_size": image_size,
                    "image_bytes": None,
                }
            if "audio" in fields:
                # keep mode but strip bytes
                audio_size = 0
                if fields["audio"].get("audio_bytes"):
                    try:
                        audio_size = len(
                            base64.b64decode(fields["audio"]["audio_bytes"]),
                        )
                    except Exception as e:
                        print(f"Failed to decode audio bytes: {e}")
                fields["audio"] = {
                    "audio_mode": fields["audio"].get("audio_mode"),
                    "audio_size": audio_size,
                    "audio_bytes": None,
                }
            if "file_attachments" in fields:
                # keep file names but strip bytes
                for i in range(len(fields["file_attachments"])):
                    file_size = 0
                    if fields["file_attachments"][i].get("file_bytes"):
                        try:
                            file_size = len(
                                base64.b64decode(
                                    fields["file_attachments"][i]["file_bytes"],
                                ),
                            )
                        except Exception as e:
                            print(f"Failed to decode file attachment bytes: {e}")
                    fields["file_attachments"][i] = {
                        "file_name": fields["file_attachments"][i].get("file_name"),
                        "file_size": file_size,
                        "file_bytes": None,
                    }

        # ensure created_at and updated_at have Z suffix for UTC if they don't have a timezone
        created_at = str(db_lxmf_message["created_at"])
        if created_at and "+" not in created_at and "Z" not in created_at:
            created_at += "Z"

        updated_at = str(db_lxmf_message["updated_at"])
        if updated_at and "+" not in updated_at and "Z" not in updated_at:
            updated_at += "Z"

        return {
            "id": db_lxmf_message["id"],
            "hash": db_lxmf_message["hash"],
            "source_hash": db_lxmf_message["source_hash"],
            "destination_hash": db_lxmf_message["destination_hash"],
            "is_incoming": bool(db_lxmf_message["is_incoming"]),
            "state": db_lxmf_message["state"],
            "progress": db_lxmf_message["progress"],
            "method": db_lxmf_message["method"],
            "delivery_attempts": db_lxmf_message["delivery_attempts"],
            "next_delivery_attempt_at": db_lxmf_message["next_delivery_attempt_at"],
            "title": db_lxmf_message["title"],
            "content": db_lxmf_message["content"],
            "fields": fields,
            "timestamp": db_lxmf_message["timestamp"],
            "rssi": db_lxmf_message["rssi"],
            "snr": db_lxmf_message["snr"],
            "quality": db_lxmf_message["quality"],
            "is_spam": bool(db_lxmf_message["is_spam"]),
            "created_at": created_at,
            "updated_at": updated_at,
        }

    # updates the lxmf user icon for the provided destination hash
    @staticmethod
    def update_lxmf_user_icon(
        self,
        destination_hash: str,
        icon_name: str,
        foreground_colour: str,
        background_colour: str,
    ):
        # log
        print(
            f"updating lxmf user icon for {destination_hash} to icon_name={icon_name}, foreground_colour={foreground_colour}, background_colour={background_colour}",
        )

        self.database.misc.update_lxmf_user_icon(
            destination_hash,
            icon_name,
            foreground_colour,
            background_colour,
        )

    # check if a destination is blocked
    def is_destination_blocked(self, destination_hash: str) -> bool:
        try:
            return self.database.misc.is_destination_blocked(destination_hash)
        except Exception:
            return False

    # check if message content matches spam keywords
    def check_spam_keywords(self, title: str, content: str) -> bool:
        try:
            return self.database.misc.check_spam_keywords(title, content)
        except Exception:
            return False

    # check if message has attachments and should be rejected
    @staticmethod
    def has_attachments(lxmf_fields: dict) -> bool:
        try:
            if LXMF.FIELD_FILE_ATTACHMENTS in lxmf_fields:
                return len(lxmf_fields[LXMF.FIELD_FILE_ATTACHMENTS]) > 0
            if LXMF.FIELD_IMAGE in lxmf_fields:
                return True
            if LXMF.FIELD_AUDIO in lxmf_fields:
                return True
            return False
        except Exception:
            return False

    # handle an lxmf delivery from reticulum
    # NOTE: cant be async, as Reticulum doesn't await it
    def on_lxmf_delivery(self, lxmf_message: LXMF.LXMessage):
        try:
            source_hash = lxmf_message.source_hash.hex()

            # check if source is blocked - reject immediately
            if self.is_destination_blocked(source_hash):
                print(f"Rejecting LXMF message from blocked source: {source_hash}")
                return

            # check if this lxmf message contains a telemetry request command from sideband
            is_sideband_telemetry_request = False
            lxmf_fields = lxmf_message.get_fields()
            if LXMF.FIELD_COMMANDS in lxmf_fields:
                for command in lxmf_fields[LXMF.FIELD_COMMANDS]:
                    if SidebandCommands.TELEMETRY_REQUEST in command:
                        is_sideband_telemetry_request = True

            # respond to telemetry requests from sideband
            if is_sideband_telemetry_request:
                print(f"Responding to telemetry request from {source_hash}")
                self.handle_telemetry_request(source_hash)
                return

            # check for spam keywords
            is_spam = False
            message_title = lxmf_message.title if hasattr(lxmf_message, "title") else ""
            message_content = (
                lxmf_message.content if hasattr(lxmf_message, "content") else ""
            )

            # check spam keywords
            if self.check_spam_keywords(message_title, message_content):
                is_spam = True
                print(
                    f"Marking LXMF message as spam due to keyword match: {source_hash}",
                )

            # reject attachments from blocked sources (already checked above, but double-check)
            if self.has_attachments(lxmf_fields):
                if self.is_destination_blocked(source_hash):
                    print(
                        f"Rejecting LXMF message with attachments from blocked source: {source_hash}",
                    )
                    return
                # reject attachments from spam sources
                if is_spam:
                    print(
                        f"Rejecting LXMF message with attachments from spam source: {source_hash}",
                    )
                    return

            # upsert lxmf message to database with spam flag
            self.db_upsert_lxmf_message(lxmf_message, is_spam=is_spam)

            # handle forwarding
            self.handle_forwarding(lxmf_message)

            # handle telemetry
            try:
                message_fields = lxmf_message.get_fields()
                if LXMF.FIELD_TELEMETRY in message_fields:
                    telemetry_data = message_fields[LXMF.FIELD_TELEMETRY]
                    # unpack to get timestamp
                    unpacked = Telemeter.from_packed(telemetry_data)
                    if unpacked and "time" in unpacked:
                        timestamp = unpacked["time"]["utc"]

                        # physical link info
                        physical_link = {
                            "rssi": self.reticulum.get_packet_rssi(lxmf_message.hash),
                            "snr": self.reticulum.get_packet_snr(lxmf_message.hash),
                            "q": self.reticulum.get_packet_q(lxmf_message.hash),
                        }

                        self.database.telemetry.upsert_telemetry(
                            destination_hash=source_hash,
                            timestamp=timestamp,
                            data=telemetry_data,
                            received_from=self.local_lxmf_destination.hexhash,
                            physical_link=physical_link,
                        )

                        # broadcast telemetry update via websocket
                        AsyncUtils.run_async(
                            self.websocket_broadcast(
                                json.dumps(
                                    {
                                        "type": "lxmf.telemetry",
                                        "destination_hash": source_hash,
                                        "timestamp": timestamp,
                                        "telemetry": unpacked,
                                    },
                                ),
                            ),
                        )
            except Exception as e:
                print(f"Failed to handle telemetry in LXMF message: {e}")

            # update lxmf user icon if icon appearance field is available
            try:
                message_fields = lxmf_message.get_fields()
                if LXMF.FIELD_ICON_APPEARANCE in message_fields:
                    icon_appearance = message_fields[LXMF.FIELD_ICON_APPEARANCE]
                    icon_name = icon_appearance[0]
                    foreground_colour = "#" + icon_appearance[1].hex()
                    background_colour = "#" + icon_appearance[2].hex()
                    self.update_lxmf_user_icon(
                        lxmf_message.source_hash.hex(),
                        icon_name,
                        foreground_colour,
                        background_colour,
                    )
            except Exception as e:
                print("failed to update lxmf user icon from lxmf message")
                print(e)

            # find message from database
            db_lxmf_message = self.database.messages.get_lxmf_message_by_hash(
                lxmf_message.hash.hex(),
            )
            if not db_lxmf_message:
                return

            # send received lxmf message data to all websocket clients
            AsyncUtils.run_async(
                self.websocket_broadcast(
                    json.dumps(
                        {
                            "type": "lxmf.delivery",
                            "lxmf_message": self.convert_db_lxmf_message_to_dict(
                                db_lxmf_message,
                                include_attachments=False,
                            ),
                        },
                    ),
                ),
            )

        except Exception as e:
            # do nothing on error
            print(f"lxmf_delivery error: {e}")

    # handles lxmf message forwarding logic
    def handle_forwarding(self, lxmf_message: LXMF.LXMessage):
        try:
            source_hash = lxmf_message.source_hash.hex()
            destination_hash = lxmf_message.destination_hash.hex()

            # extract fields for potential forwarding
            lxmf_fields = lxmf_message.get_fields()
            image_field = None
            audio_field = None
            file_attachments_field = None

            if LXMF.FIELD_IMAGE in lxmf_fields:
                val = lxmf_fields[LXMF.FIELD_IMAGE]
                image_field = LxmfImageField(val[0], val[1])

            if LXMF.FIELD_AUDIO in lxmf_fields:
                val = lxmf_fields[LXMF.FIELD_AUDIO]
                audio_field = LxmfAudioField(val[0], val[1])

            if LXMF.FIELD_FILE_ATTACHMENTS in lxmf_fields:
                attachments = []
                for val in lxmf_fields[LXMF.FIELD_FILE_ATTACHMENTS]:
                    attachments.append(LxmfFileAttachment(val[0], val[1]))
                file_attachments_field = LxmfFileAttachmentsField(attachments)

            # check if this message is for an alias identity (REPLY PATH)
            mapping = self.database.messages.get_forwarding_mapping(
                alias_hash=destination_hash,
            )

            if mapping:
                # this is a reply from User C to User B (alias). Forward to User A.
                print(
                    f"Forwarding reply from {source_hash} back to original sender {mapping['original_sender_hash']}",
                )
                AsyncUtils.run_async(
                    self.send_message(
                        destination_hash=mapping["original_sender_hash"],
                        content=lxmf_message.content,
                        title=lxmf_message.title
                        if hasattr(lxmf_message, "title")
                        else "",
                        image_field=image_field,
                        audio_field=audio_field,
                        file_attachments_field=file_attachments_field,
                    ),
                )
                return

            # check if this message matches a forwarding rule (FORWARD PATH)
            # we check for rules that apply to the destination of this message
            rules = self.database.misc.get_forwarding_rules(
                identity_hash=destination_hash,
                active_only=True,
            )

            for rule in rules:
                # check source filter if set
                if (
                    rule["source_filter_hash"]
                    and rule["source_filter_hash"] != source_hash
                ):
                    continue

                # find or create mapping for this (Source, Final Recipient) pair
                mapping = self.forwarding_manager.get_or_create_mapping(
                    source_hash,
                    rule["forward_to_hash"],
                    destination_hash,
                )

                # forward to User C from Alias Identity
                print(
                    f"Forwarding message from {source_hash} to {rule['forward_to_hash']} via alias {mapping['alias_hash']}",
                )
                AsyncUtils.run_async(
                    self.send_message(
                        destination_hash=rule["forward_to_hash"],
                        content=lxmf_message.content,
                        title=lxmf_message.title
                        if hasattr(lxmf_message, "title")
                        else "",
                        sender_identity_hash=mapping["alias_hash"],
                        image_field=image_field,
                        audio_field=audio_field,
                        file_attachments_field=file_attachments_field,
                    ),
                )
        except Exception as e:
            print(f"Error in handle_forwarding: {e}")
            import traceback

            traceback.print_exc()

    # handle delivery status update for an outbound lxmf message
    def on_lxmf_sending_state_updated(self, lxmf_message):
        # upsert lxmf message to database
        self.db_upsert_lxmf_message(lxmf_message)

        # send lxmf message state to all websocket clients
        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "lxmf_message_state_updated",
                        "lxmf_message": self.convert_lxmf_message_to_dict(
                            lxmf_message,
                            include_attachments=False,
                        ),
                    },
                ),
            ),
        )

    # handle delivery failed for an outbound lxmf message
    def on_lxmf_sending_failed(self, lxmf_message):
        # check if this failed message should fall back to sending via a propagation node
        if (
            lxmf_message.state == LXMF.LXMessage.FAILED
            and hasattr(lxmf_message, "try_propagation_on_fail")
            and lxmf_message.try_propagation_on_fail
        ):
            self.send_failed_message_via_propagation_node(lxmf_message)

        # update state
        self.on_lxmf_sending_state_updated(lxmf_message)

    # sends a previously failed message via a propagation node
    def send_failed_message_via_propagation_node(self, lxmf_message: LXMF.LXMessage):
        # reset internal message state
        lxmf_message.packed = None
        lxmf_message.delivery_attempts = 0
        if hasattr(lxmf_message, "next_delivery_attempt"):
            del lxmf_message.next_delivery_attempt

        # this message should now be sent via a propagation node
        lxmf_message.desired_method = LXMF.LXMessage.PROPAGATED
        lxmf_message.try_propagation_on_fail = False

        # resend message
        source_hash = lxmf_message.source_hash.hex()
        router = self.message_router
        if (
            self.forwarding_manager
            and source_hash in self.forwarding_manager.forwarding_routers
        ):
            router = self.forwarding_manager.forwarding_routers[source_hash]
        router.handle_outbound(lxmf_message)

    # upserts the provided lxmf message to the database
    def db_upsert_lxmf_message(
        self,
        lxmf_message: LXMF.LXMessage,
        is_spam: bool = False,
    ):
        # convert lxmf message to dict
        lxmf_message_dict = self.convert_lxmf_message_to_dict(lxmf_message)
        lxmf_message_dict["is_spam"] = 1 if is_spam else 0
        self.database.messages.upsert_lxmf_message(lxmf_message_dict)

    # upserts the provided announce to the database
    # handle sending an lxmf message to reticulum
    async def send_message(
        self,
        destination_hash: str,
        content: str,
        image_field: LxmfImageField = None,
        audio_field: LxmfAudioField = None,
        file_attachments_field: LxmfFileAttachmentsField = None,
        telemetry_data: bytes = None,
        commands: list = None,
        delivery_method: str = None,
        title: str = "",
        sender_identity_hash: str = None,
        no_display: bool = False,
    ) -> LXMF.LXMessage:
        # convert destination hash to bytes
        destination_hash_bytes = bytes.fromhex(destination_hash)

        # determine when to timeout finding path
        timeout_after_seconds = time.time() + 10

        # check if we have a path to the destination
        if not RNS.Transport.has_path(destination_hash_bytes):
            # we don't have a path, so we need to request it
            RNS.Transport.request_path(destination_hash_bytes)

            # wait until we have a path, or give up after the configured timeout
            while (
                not RNS.Transport.has_path(destination_hash_bytes)
                and time.time() < timeout_after_seconds
            ):
                await asyncio.sleep(0.1)

        # find destination identity from hash
        destination_identity = RNS.Identity.recall(destination_hash_bytes)
        if destination_identity is None:
            # we have to bail out of sending, since we don't have the identity/path yet
            msg = "Could not find path to destination. Try again later."
            raise Exception(msg)

        # create destination for recipients lxmf delivery address
        lxmf_destination = RNS.Destination(
            destination_identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            "lxmf",
            "delivery",
        )

        # determine how the user wants to send the message
        desired_delivery_method = None
        if delivery_method == "direct":
            desired_delivery_method = LXMF.LXMessage.DIRECT
        elif delivery_method == "opportunistic":
            desired_delivery_method = LXMF.LXMessage.OPPORTUNISTIC
        elif delivery_method == "propagated":
            desired_delivery_method = LXMF.LXMessage.PROPAGATED

        # determine how to send the message if the user didn't provide a method
        if desired_delivery_method is None:
            # send messages over a direct link by default
            desired_delivery_method = LXMF.LXMessage.DIRECT
            if (
                not self.message_router.delivery_link_available(destination_hash_bytes)
                and RNS.Identity.current_ratchet_id(destination_hash_bytes) is not None
            ):
                # since there's no link established to the destination, it's faster to send opportunistically
                # this is because it takes several packets to establish a link, and then we still have to send the message over it
                # oppotunistic mode will send the message in a single packet (if the message is small enough, otherwise it falls back to a direct link)
                # we will only do this if an encryption ratchet is available, so single packet delivery is more secure
                desired_delivery_method = LXMF.LXMessage.OPPORTUNISTIC

        # determine which identity to send from
        source_destination = self.local_lxmf_destination
        if sender_identity_hash is not None:
            if (
                self.forwarding_manager
                and sender_identity_hash
                in self.forwarding_manager.forwarding_destinations
            ):
                source_destination = self.forwarding_manager.forwarding_destinations[
                    sender_identity_hash
                ]
            else:
                print(
                    f"Warning: requested sender identity {sender_identity_hash} not found, using default.",
                )

        # create lxmf message
        lxmf_message = LXMF.LXMessage(
            lxmf_destination,
            source_destination,
            content,
            title=title,
            desired_method=desired_delivery_method,
        )
        lxmf_message.try_propagation_on_fail = (
            self.config.auto_send_failed_messages_to_propagation_node.get()
        )

        lxmf_message.fields = {}

        # add file attachments field
        if file_attachments_field is not None:
            # create array of [[file_name, file_bytes], [file_name, file_bytes], ...]
            file_attachments = [
                [file_attachment.file_name, file_attachment.file_bytes]
                for file_attachment in file_attachments_field.file_attachments
            ]

            # set field attachments field
            lxmf_message.fields[LXMF.FIELD_FILE_ATTACHMENTS] = file_attachments

        # add image field
        if image_field is not None:
            lxmf_message.fields[LXMF.FIELD_IMAGE] = [
                image_field.image_type,
                image_field.image_bytes,
            ]

        # add audio field
        if audio_field is not None:
            lxmf_message.fields[LXMF.FIELD_AUDIO] = [
                audio_field.audio_mode,
                audio_field.audio_bytes,
            ]

        # add telemetry field
        if telemetry_data is not None:
            lxmf_message.fields[LXMF.FIELD_TELEMETRY] = telemetry_data

        # add commands field
        if commands is not None:
            lxmf_message.fields[LXMF.FIELD_COMMANDS] = commands

        # add icon appearance if configured
        # fixme: we could save a tiny amount of bandwidth here, but this requires more effort...
        # we could keep track of when the icon appearance was last sent to this destination, and when it last changed
        # we could save 6 bytes for the 2x colours, and also however long the icon name is, but not today!
        lxmf_user_icon_name = self.config.lxmf_user_icon_name.get()
        lxmf_user_icon_foreground_colour = (
            self.config.lxmf_user_icon_foreground_colour.get()
        )
        lxmf_user_icon_background_colour = (
            self.config.lxmf_user_icon_background_colour.get()
        )
        if (
            lxmf_user_icon_name is not None
            and lxmf_user_icon_foreground_colour is not None
            and lxmf_user_icon_background_colour is not None
        ):
            lxmf_message.fields[LXMF.FIELD_ICON_APPEARANCE] = [
                lxmf_user_icon_name,
                ColourUtils.hex_colour_to_byte_array(lxmf_user_icon_foreground_colour),
                ColourUtils.hex_colour_to_byte_array(lxmf_user_icon_background_colour),
            ]

        # register delivery callbacks
        lxmf_message.register_delivery_callback(self.on_lxmf_sending_state_updated)
        lxmf_message.register_failed_callback(self.on_lxmf_sending_failed)

        # determine which router to use
        router = self.message_router
        if (
            sender_identity_hash is not None
            and sender_identity_hash in self.forwarding_manager.forwarding_routers
        ):
            router = self.forwarding_manager.forwarding_routers[sender_identity_hash]

        # send lxmf message to be routed to destination
        router.handle_outbound(lxmf_message)

        # upsert lxmf message to database
        if not no_display:
            self.db_upsert_lxmf_message(lxmf_message)

        # tell all websocket clients that old failed message was deleted so it can remove from ui
        if not no_display:
            await self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "lxmf_message_created",
                        "lxmf_message": self.convert_lxmf_message_to_dict(
                            lxmf_message,
                            include_attachments=False,
                        ),
                    },
                ),
            )

        # handle lxmf message progress loop without blocking or awaiting
        # otherwise other incoming websocket packets will not be processed until sending is complete
        # which results in the next message not showing up until the first message is finished
        if not no_display:
            AsyncUtils.run_async(self.handle_lxmf_message_progress(lxmf_message))

        return lxmf_message

    def handle_telemetry_request(self, to_addr_hash: str):
        # get our location from config
        lat = self.database.config.get("map_default_lat")
        lon = self.database.config.get("map_default_lon")

        if lat is None or lon is None:
            print(
                f"Cannot respond to telemetry request from {to_addr_hash}: No location set",
            )
            return

        try:
            location = {
                "latitude": float(lat),
                "longitude": float(lon),
                "altitude": 0,
                "speed": 0,
                "bearing": 0,
                "accuracy": 0,
                "last_update": int(time.time()),
            }

            telemetry_data = Telemeter.pack(location=location)

            # send as an LXMF message with no content, only telemetry field
            # use no_display=True to avoid showing in chat UI
            AsyncUtils.run_async(
                self.send_message(
                    destination_hash=to_addr_hash,
                    content="",
                    telemetry_data=telemetry_data,
                    delivery_method="opportunistic",
                    no_display=True,
                ),
            )
        except Exception as e:
            print(f"Failed to respond to telemetry request: {e}")

    # updates lxmf message in database and broadcasts to websocket until it's delivered, or it fails
    async def handle_lxmf_message_progress(self, lxmf_message):
        # FIXME: there's no register_progress_callback on the lxmf message, so manually send progress until delivered, propagated or failed
        # we also can't use on_lxmf_sending_state_updated method to do this, because of async/await issues...
        should_update_message = True
        while should_update_message:
            # wait 1 second between sending updates
            await asyncio.sleep(1)

            # upsert lxmf message to database (as we want to update the progress in database too)
            self.db_upsert_lxmf_message(lxmf_message)

            # send update to websocket clients
            await self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "lxmf_message_state_updated",
                        "lxmf_message": self.convert_lxmf_message_to_dict(
                            lxmf_message,
                            include_attachments=False,
                        ),
                    },
                ),
            )

            # check message state
            has_delivered = lxmf_message.state == LXMF.LXMessage.DELIVERED
            has_propagated = (
                lxmf_message.state == LXMF.LXMessage.SENT
                and lxmf_message.method == LXMF.LXMessage.PROPAGATED
            )
            has_failed = lxmf_message.state == LXMF.LXMessage.FAILED
            is_cancelled = lxmf_message.state == LXMF.LXMessage.CANCELLED

            # check if we should stop updating
            if has_delivered or has_propagated or has_failed or is_cancelled:
                should_update_message = False

    # handle an announce received from reticulum, for a telephone address
    # NOTE: cant be async, as Reticulum doesn't await it
    def on_telephone_announce_received(
        self,
        aspect,
        destination_hash,
        announced_identity,
        app_data,
        announce_packet_hash,
    ):
        # check if source is blocked - drop announce and path if blocked
        identity_hash = announced_identity.hash.hex()
        if self.is_destination_blocked(identity_hash):
            print(f"Dropping telephone announce from blocked source: {identity_hash}")
            self.reticulum.drop_path(destination_hash)
            return

        # log received announce
        print(
            "Received an announce from "
            + RNS.prettyhexrep(destination_hash)
            + " for [lxst.telephony]",
        )

        # track announce timestamp
        self.announce_timestamps.append(time.time())

        # upsert announce to database
        self.announce_manager.upsert_announce(
            self.reticulum,
            announced_identity,
            destination_hash,
            aspect,
            app_data,
            announce_packet_hash,
        )

        # find announce from database
        announce = self.database.announces.get_announce_by_hash(destination_hash.hex())
        if not announce:
            return

        # send database announce to all websocket clients
        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "announce",
                        "announce": self.convert_db_announce_to_dict(announce),
                    },
                ),
            ),
        )

    # handle an announce received from reticulum, for an lxmf address
    # NOTE: cant be async, as Reticulum doesn't await it
    def on_lxmf_announce_received(
        self,
        aspect,
        destination_hash,
        announced_identity,
        app_data,
        announce_packet_hash,
    ):
        # check if source is blocked - drop announce and path if blocked
        identity_hash = announced_identity.hash.hex()
        if self.is_destination_blocked(identity_hash):
            print(f"Dropping announce from blocked source: {identity_hash}")
            self.reticulum.drop_path(destination_hash)
            return

        # log received announce
        print(
            "Received an announce from "
            + RNS.prettyhexrep(destination_hash)
            + " for [lxmf.delivery]",
        )

        # track announce timestamp
        self.announce_timestamps.append(time.time())

        # upsert announce to database
        self.announce_manager.upsert_announce(
            self.reticulum,
            announced_identity,
            destination_hash,
            aspect,
            app_data,
            announce_packet_hash,
        )

        # find announce from database
        announce = self.database.announces.get_announce_by_hash(destination_hash.hex())
        if not announce:
            return

        # send database announce to all websocket clients
        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "announce",
                        "announce": self.convert_db_announce_to_dict(announce),
                    },
                ),
            ),
        )

        # resend all failed messages that were intended for this destination
        if self.config.auto_resend_failed_messages_when_announce_received.get():
            AsyncUtils.run_async(
                self.resend_failed_messages_for_destination(destination_hash.hex()),
            )

    # handle an announce received from reticulum, for an lxmf propagation node address
    # NOTE: cant be async, as Reticulum doesn't await it
    def on_lxmf_propagation_announce_received(
        self,
        aspect,
        destination_hash,
        announced_identity,
        app_data,
        announce_packet_hash,
    ):
        # log received announce
        print(
            "Received an announce from "
            + RNS.prettyhexrep(destination_hash)
            + " for [lxmf.propagation]",
        )

        # track announce timestamp
        self.announce_timestamps.append(time.time())

        # upsert announce to database
        self.announce_manager.upsert_announce(
            self.reticulum,
            announced_identity,
            destination_hash,
            aspect,
            app_data,
            announce_packet_hash,
        )

        # find announce from database
        announce = self.database.announces.get_announce_by_hash(destination_hash.hex())
        if not announce:
            return

        # send database announce to all websocket clients
        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "announce",
                        "announce": self.convert_db_announce_to_dict(announce),
                    },
                ),
            ),
        )

    # resends all messages that previously failed to send to the provided destination hash
    async def resend_failed_messages_for_destination(self, destination_hash: str):
        # get messages that failed to send to this destination
        failed_messages = self.database.messages.get_failed_messages_for_destination(
            destination_hash,
        )

        # resend failed messages
        for failed_message in failed_messages:
            try:
                # parse fields as json
                fields = json.loads(failed_message["fields"])

                # parse image field
                image_field = None
                if "image" in fields:
                    image_field = LxmfImageField(
                        fields["image"]["image_type"],
                        base64.b64decode(fields["image"]["image_bytes"]),
                    )

                # parse audio field
                audio_field = None
                if "audio" in fields:
                    audio_field = LxmfAudioField(
                        fields["audio"]["audio_mode"],
                        base64.b64decode(fields["audio"]["audio_bytes"]),
                    )

                # parse file attachments field
                file_attachments_field = None
                if "file_attachments" in fields:
                    file_attachments = [
                        LxmfFileAttachment(
                            file_attachment["file_name"],
                            base64.b64decode(file_attachment["file_bytes"]),
                        )
                        for file_attachment in fields["file_attachments"]
                    ]
                    file_attachments_field = LxmfFileAttachmentsField(file_attachments)

                # don't resend message with attachments if not allowed
                if not self.config.allow_auto_resending_failed_messages_with_attachments.get():
                    if (
                        image_field is not None
                        or audio_field is not None
                        or file_attachments_field is not None
                    ):
                        print(
                            "Not resending failed message with attachments, as setting is disabled",
                        )
                        continue

                # send new message with failed message content
                await self.send_message(
                    failed_message["destination_hash"],
                    failed_message["content"],
                    image_field=image_field,
                    audio_field=audio_field,
                    file_attachments_field=file_attachments_field,
                )

                # remove original failed message from database
                self.database.messages.delete_lxmf_message_by_hash(
                    failed_message["hash"],
                )

                # tell all websocket clients that old failed message was deleted so it can remove from ui
                await self.websocket_broadcast(
                    json.dumps(
                        {
                            "type": "lxmf_message_deleted",
                            "hash": failed_message["hash"],
                        },
                    ),
                )

            except Exception as e:
                print("Error resending failed message: " + str(e))

    # handle an announce received from reticulum, for a nomadnet node
    # NOTE: cant be async, as Reticulum doesn't await it
    def on_nomadnet_node_announce_received(
        self,
        aspect,
        destination_hash,
        announced_identity,
        app_data,
        announce_packet_hash,
    ):
        # check if source is blocked - drop announce and path if blocked
        identity_hash = announced_identity.hash.hex()
        if self.is_destination_blocked(identity_hash):
            print(f"Dropping announce from blocked source: {identity_hash}")
            self.reticulum.drop_path(destination_hash)
            return

        # log received announce
        print(
            "Received an announce from "
            + RNS.prettyhexrep(destination_hash)
            + " for [nomadnetwork.node]",
        )

        # track announce timestamp
        self.announce_timestamps.append(time.time())

        # upsert announce to database
        self.announce_manager.upsert_announce(
            self.reticulum,
            announced_identity,
            destination_hash,
            aspect,
            app_data,
            announce_packet_hash,
        )

        # find announce from database
        announce = self.database.announces.get_announce_by_hash(destination_hash.hex())
        if announce is None:
            return

        # send database announce to all websocket clients
        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "announce",
                        "announce": self.convert_db_announce_to_dict(announce),
                    },
                ),
            ),
        )

        # queue crawler task (existence check in queue_crawler_task handles duplicates)
        self.queue_crawler_task(destination_hash.hex(), "/page/index.mu")

    # queues a crawler task for the provided destination and path
    def queue_crawler_task(self, destination_hash: str, page_path: str):
        self.database.misc.upsert_crawl_task(destination_hash, page_path)

    # gets the custom display name a user has set for the provided destination hash
    def get_custom_destination_display_name(self, destination_hash: str):
        db_destination_display_name = self.database.announces.get_custom_display_name(
            destination_hash,
        )
        if db_destination_display_name is not None:
            return db_destination_display_name

        return None

    # get name to show for an lxmf conversation
    # currently, this will use the app data from the most recent announce
    # TODO: we should fetch this from our contacts database, when it gets implemented, and if not found, fallback to app data
    def get_lxmf_conversation_name(
        self,
        destination_hash,
        default_name: str | None = "Anonymous Peer",
    ):
        # get lxmf.delivery announce from database for the provided destination hash
        results = self.database.announces.get_announces(aspect="lxmf.delivery")
        lxmf_announce = next(
            (a for a in results if a["destination_hash"] == destination_hash),
            None,
        )

        # if app data is available in database, it should be base64 encoded text that was announced
        # we will return the parsed lxmf display name as the conversation name
        if lxmf_announce is not None and lxmf_announce["app_data"] is not None:
            return ReticulumMeshChat.parse_lxmf_display_name(
                app_data_base64=lxmf_announce["app_data"],
            )

        # announce did not have app data, so provide a fallback name
        return default_name

    # reads the lxmf display name from the provided base64 app data
    @staticmethod
    def parse_lxmf_display_name(
        app_data_base64: str | None,
        default_value: str | None = "Anonymous Peer",
    ):
        if app_data_base64 is None:
            return default_value

        try:
            app_data_bytes = base64.b64decode(app_data_base64)
            display_name = LXMF.display_name_from_app_data(app_data_bytes)
            if display_name is not None:
                return display_name
        except Exception as e:
            print(f"Failed to parse LXMF display name: {e}")

        return default_value

    # reads the lxmf stamp cost from the provided base64 app data
    @staticmethod
    def parse_lxmf_stamp_cost(app_data_base64: str | None):
        if app_data_base64 is None:
            return None

        try:
            app_data_bytes = base64.b64decode(app_data_base64)
            return LXMF.stamp_cost_from_app_data(app_data_bytes)
        except Exception as e:
            print(f"Failed to parse LXMF stamp cost: {e}")
            return None

    # reads the nomadnetwork node display name from the provided base64 app data
    @staticmethod
    def parse_nomadnetwork_node_display_name(
        app_data_base64: str | None,
        default_value: str | None = "Anonymous Node",
    ):
        if app_data_base64 is None:
            return default_value

        try:
            app_data_bytes = base64.b64decode(app_data_base64)
            return app_data_bytes.decode("utf-8")
        except Exception as e:
            print(f"Failed to parse NomadNetwork display name: {e}")
            return default_value

    # parses lxmf propagation node app data
    @staticmethod
    def parse_lxmf_propagation_node_app_data(app_data_base64: str | None):
        if app_data_base64 is None:
            return None

        try:
            app_data_bytes = base64.b64decode(app_data_base64)
            data = msgpack.unpackb(app_data_bytes)

            # ensure data is a list and has enough elements
            if not isinstance(data, list) or len(data) < 4:
                return None

            return {
                "enabled": bool(data[2]) if data[2] is not None else False,
                "timebase": int(data[1]) if data[1] is not None else 0,
                "per_transfer_limit": int(data[3]) if data[3] is not None else 0,
            }
        except Exception as e:
            print(f"Failed to parse LXMF propagation node app data: {e}")
            return None

    # returns true if the conversation has messages newer than the last read at timestamp
    @staticmethod
    def is_lxmf_conversation_unread(self, destination_hash):
        return self.database.messages.is_conversation_unread(destination_hash)

    # returns number of messages that failed to send in a conversation
    def lxmf_conversation_failed_messages_count(self, destination_hash: str):
        return self.database.messages.get_failed_messages_count(destination_hash)

    # find an interface by name
    @staticmethod
    def find_interface_by_name(name: str):
        for interface in RNS.Transport.interfaces:
            interface_name = str(interface)
            if name == interface_name:
                return interface

        return None


# class to manage config stored in database
# FIXME: we should probably set this as an instance variable of ReticulumMeshChat so it has a proper home, and pass it in to the constructor?
nomadnet_cached_links = {}


class NomadnetDownloader:
    def __init__(
        self,
        destination_hash: bytes,
        path: str,
        data: str | None,
        on_download_success: Callable[[RNS.RequestReceipt], None],
        on_download_failure: Callable[[str], None],
        on_progress_update: Callable[[float], None],
        timeout: int | None = None,
    ):
        self.app_name = "nomadnetwork"
        self.aspects = "node"
        self.destination_hash = destination_hash
        self.path = path
        self.data = data
        self.timeout = timeout
        self._download_success_callback = on_download_success
        self._download_failure_callback = on_download_failure
        self.on_progress_update = on_progress_update
        self.request_receipt = None
        self.is_cancelled = False
        self.link = None

    # cancel the download
    def cancel(self):
        self.is_cancelled = True

        # cancel the request if it exists
        if self.request_receipt is not None:
            try:
                self.request_receipt.cancel()
            except Exception as e:
                print(f"Failed to cancel request: {e}")

        # clean up the link if we created it
        if self.link is not None:
            try:
                self.link.teardown()
            except Exception as e:
                print(f"Failed to teardown link: {e}")

        # notify that download was cancelled
        self._download_failure_callback("cancelled")

    # setup link to destination and request download
    async def download(
        self,
        path_lookup_timeout: int = 15,
        link_establishment_timeout: int = 15,
    ):
        # check if cancelled before starting
        if self.is_cancelled:
            return

        # use existing established link if it's active
        if self.destination_hash in nomadnet_cached_links:
            link = nomadnet_cached_links[self.destination_hash]
            if link.status is RNS.Link.ACTIVE:
                print("[NomadnetDownloader] using existing link for request")
                self.link_established(link)
                return

        # determine when to timeout
        timeout_after_seconds = time.time() + path_lookup_timeout

        # check if we have a path to the destination
        if not RNS.Transport.has_path(self.destination_hash):
            # we don't have a path, so we need to request it
            RNS.Transport.request_path(self.destination_hash)

            # wait until we have a path, or give up after the configured timeout
            while (
                not RNS.Transport.has_path(self.destination_hash)
                and time.time() < timeout_after_seconds
            ):
                # check if cancelled during path lookup
                if self.is_cancelled:
                    return
                await asyncio.sleep(0.1)

        # if we still don't have a path, we can't establish a link, so bail out
        if not RNS.Transport.has_path(self.destination_hash):
            self._download_failure_callback("Could not find path to destination.")
            return

        # check if cancelled before establishing link
        if self.is_cancelled:
            return

        # create destination to nomadnet node
        identity = RNS.Identity.recall(self.destination_hash)
        destination = RNS.Destination(
            identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            self.app_name,
            self.aspects,
        )

        # create link to destination
        print("[NomadnetDownloader] establishing new link for request")
        link = RNS.Link(destination, established_callback=self.link_established)
        self.link = link

        # determine when to timeout
        timeout_after_seconds = time.time() + link_establishment_timeout

        # wait until we have established a link, or give up after the configured timeout
        while (
            link.status is not RNS.Link.ACTIVE and time.time() < timeout_after_seconds
        ):
            # check if cancelled during link establishment
            if self.is_cancelled:
                return
            await asyncio.sleep(0.1)

        # if we still haven't established a link, bail out
        if link.status is not RNS.Link.ACTIVE:
            self._download_failure_callback("Could not establish link to destination.")

    # link to destination was established, we should now request the download
    def link_established(self, link):
        # check if cancelled before requesting
        if self.is_cancelled:
            return

        # cache link for using in future requests
        nomadnet_cached_links[self.destination_hash] = link

        # request download over link
        self.request_receipt = link.request(
            self.path,
            data=self.data,
            response_callback=self.on_response,
            failed_callback=self.on_failed,
            progress_callback=self.on_progress,
            timeout=self.timeout,
        )

    # handle successful download
    def on_response(self, request_receipt: RNS.RequestReceipt):
        self._download_success_callback(request_receipt)

    # handle failure
    def on_failed(self, request_receipt=None):
        self._download_failure_callback("request_failed")

    # handle download progress
    def on_progress(self, request_receipt):
        self.on_progress_update(request_receipt.progress)


class NomadnetPageDownloader(NomadnetDownloader):
    def __init__(
        self,
        destination_hash: bytes,
        page_path: str,
        data: str | None,
        on_page_download_success: Callable[[str], None],
        on_page_download_failure: Callable[[str], None],
        on_progress_update: Callable[[float], None],
        timeout: int | None = None,
    ):
        self.on_page_download_success = on_page_download_success
        self.on_page_download_failure = on_page_download_failure
        super().__init__(
            destination_hash,
            page_path,
            data,
            self.on_download_success,
            self.on_download_failure,
            on_progress_update,
            timeout,
        )

    # page download was successful, decode the response and send to provided callback
    def on_download_success(self, request_receipt: RNS.RequestReceipt):
        micron_markup_response = request_receipt.response.decode("utf-8")
        self.on_page_download_success(micron_markup_response)

    # page download failed, send error to provided callback
    def on_download_failure(self, failure_reason):
        self.on_page_download_failure(failure_reason)


class NomadnetFileDownloader(NomadnetDownloader):
    def __init__(
        self,
        destination_hash: bytes,
        page_path: str,
        on_file_download_success: Callable[[str, bytes], None],
        on_file_download_failure: Callable[[str], None],
        on_progress_update: Callable[[float], None],
        timeout: int | None = None,
    ):
        self.on_file_download_success = on_file_download_success
        self.on_file_download_failure = on_file_download_failure
        super().__init__(
            destination_hash,
            page_path,
            None,
            self.on_download_success,
            self.on_download_failure,
            on_progress_update,
            timeout,
        )

    # file download was successful, decode the response and send to provided callback
    def on_download_success(self, request_receipt: RNS.RequestReceipt):
        # get response
        response = request_receipt.response

        # handle buffered reader response
        if isinstance(response, io.BufferedReader):
            # get file name from metadata
            file_name = "downloaded_file"
            metadata = request_receipt.metadata
            if metadata is not None and "name" in metadata:
                file_path = metadata["name"].decode("utf-8")
                file_name = os.path.basename(file_path)

            # get file data
            file_data: bytes = response.read()

            self.on_file_download_success(file_name, file_data)
            return

        # check for list response with bytes in position 0, and metadata dict in position 1
        # e.g: [file_bytes, {name: "filename.ext"}]
        if isinstance(response, list) and isinstance(response[1], dict):
            file_data: bytes = response[0]
            metadata: dict = response[1]

            # get file name from metadata
            file_name = "downloaded_file"
            if metadata is not None and "name" in metadata:
                file_path = metadata["name"].decode("utf-8")
                file_name = os.path.basename(file_path)

            self.on_file_download_success(file_name, file_data)
            return

        # try using original response format
        # unsure if this is actually used anymore now that a buffered reader is provided
        # have left here just in case...
        try:
            file_name: str = response[0]
            file_data: bytes = response[1]
            self.on_file_download_success(file_name, file_data)
        except Exception:
            self.on_download_failure("unsupported_response")

    # page download failed, send error to provided callback
    def on_download_failure(self, failure_reason):
        self.on_file_download_failure(failure_reason)


def main():
    # parse command line args
    parser = argparse.ArgumentParser(description="ReticulumMeshChat")
    parser.add_argument(
        "--host",
        nargs="?",
        default="127.0.0.1",
        type=str,
        help="The address the web server should listen on.",
    )
    parser.add_argument(
        "--port",
        nargs="?",
        default="8000",
        type=int,
        help="The port the web server should listen on.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Web browser will not automatically launch when this flag is passed.",
    )
    parser.add_argument(
        "--identity-file",
        type=str,
        help="Path to a Reticulum Identity file to use as your LXMF address.",
    )
    parser.add_argument(
        "--identity-base64",
        type=str,
        help="A base64 encoded Reticulum Identity to use as your LXMF address.",
    )
    parser.add_argument(
        "--identity-base32",
        type=str,
        help="A base32 encoded Reticulum Identity to use as your LXMF address.",
    )
    parser.add_argument(
        "--generate-identity-file",
        type=str,
        help="Generates and saves a new Reticulum Identity to the provided file path and then exits.",
    )
    parser.add_argument(
        "--generate-identity-base64",
        action="store_true",
        help="Outputs a randomly generated Reticulum Identity as base64 and then exits.",
    )
    parser.add_argument(
        "--auto-recover",
        action="store_true",
        help="Attempt to automatically recover the SQLite database on startup before serving the app.",
    )
    parser.add_argument(
        "--auth",
        action="store_true",
        help="Enable basic authentication for the web interface.",
    )
    parser.add_argument(
        "--no-https",
        action="store_true",
        help="Disable HTTPS and use HTTP instead.",
    )
    parser.add_argument(
        "--backup-db",
        type=str,
        help="Create a database backup zip at the given path and exit.",
    )
    parser.add_argument(
        "--restore-db",
        type=str,
        help="Restore the database from the given path (zip or db file) and exit.",
    )
    parser.add_argument(
        "--reticulum-config-dir",
        type=str,
        help="Path to a Reticulum config directory for the RNS stack to use (e.g: ~/.reticulum)",
    )
    parser.add_argument(
        "--storage-dir",
        type=str,
        help="Path to a directory for storing databases and config files (default: ./storage)",
    )
    parser.add_argument(
        "--test-exception-message",
        type=str,
        help="Throws an exception. Used for testing the electron error dialog",
    )
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
    )  # allow unknown command line args
    args = parser.parse_args()

    # check if we want to test exception messages
    if args.test_exception_message is not None:
        raise Exception(args.test_exception_message)

    # util to generate reticulum identity and save to file without using rnid
    if args.generate_identity_file is not None:
        # do not overwrite existing files, otherwise user could lose existing keys
        if os.path.exists(args.generate_identity_file):
            print(
                "DANGER: the provided identity file path already exists, not overwriting!",
            )
            return

        # generate a new identity and save to provided file path
        identity = RNS.Identity(create_keys=True)
        with open(args.generate_identity_file, "wb") as file:
            file.write(identity.get_private_key())

        print(
            f"A new Reticulum Identity has been saved to: {args.generate_identity_file}",
        )
        return

    # util to generate reticulum identity as base64 without using rnid
    if args.generate_identity_base64 is True:
        identity = RNS.Identity(create_keys=True)
        print(base64.b64encode(identity.get_private_key()).decode("utf-8"))
        return

    identity_file_path = None

    # use provided identity, or fallback to a random one
    if args.identity_file is not None:
        identity = RNS.Identity(create_keys=False)
        identity.load(args.identity_file)
        identity_file_path = args.identity_file
        print(
            f"Reticulum Identity <{identity.hash.hex()}> has been loaded from file {args.identity_file}.",
        )
    elif args.identity_base64 is not None or args.identity_base32 is not None:
        identity = RNS.Identity(create_keys=False)
        if args.identity_base64 is not None:
            identity.load_private_key(base64.b64decode(args.identity_base64))
        else:
            try:
                identity.load_private_key(
                    base64.b32decode(args.identity_base32, casefold=True),
                )
            except Exception as exc:
                msg = f"Invalid base32 identity: {exc}"
                raise ValueError(msg) from exc
        base_storage_dir = args.storage_dir or os.path.join("storage")
        os.makedirs(base_storage_dir, exist_ok=True)
        default_identity_file = os.path.join(base_storage_dir, "identity")
        if not os.path.exists(default_identity_file):
            with open(default_identity_file, "wb") as file:
                file.write(identity.get_private_key())
        identity_file_path = default_identity_file
        print(
            f"Reticulum Identity <{identity.hash.hex()}> has been loaded from provided key.",
        )
    else:
        # ensure provided storage dir exists, or the default storage dir exists
        base_storage_dir = args.storage_dir or os.path.join("storage")
        os.makedirs(base_storage_dir, exist_ok=True)

        # configure path to default identity file
        default_identity_file = os.path.join(base_storage_dir, "identity")

        # if default identity file does not exist, generate a new identity and save it
        if not os.path.exists(default_identity_file):
            identity = RNS.Identity(create_keys=True)
            with open(default_identity_file, "wb") as file:
                file.write(identity.get_private_key())
            print(
                f"Reticulum Identity <{identity.hash.hex()}> has been randomly generated and saved to {default_identity_file}.",
            )

        # default identity file exists, load it
        identity = RNS.Identity(create_keys=False)
        identity.load(default_identity_file)
        identity_file_path = default_identity_file
        print(
            f"Reticulum Identity <{identity.hash.hex()}> has been loaded from file {default_identity_file}.",
        )

    # init app (allow optional one-shot backup/restore before running)
    reticulum_meshchat = ReticulumMeshChat(
        identity,
        args.storage_dir,
        args.reticulum_config_dir,
        auto_recover=args.auto_recover,
        identity_file_path=identity_file_path,
        auth_enabled=args.auth,
    )

    if args.backup_db:
        result = reticulum_meshchat.backup_database(args.backup_db)
        print(f"Backup written to {result['path']} ({result['size']} bytes)")
        return

    if args.restore_db:
        result = reticulum_meshchat.restore_database(args.restore_db)
        print(f"Restored database from {args.restore_db}")
        print(f"Integrity check: {result['integrity_check']}")
        return

    enable_https = not args.no_https
    reticulum_meshchat.run(
        args.host,
        args.port,
        launch_browser=args.headless is False,
        enable_https=enable_https,
    )


if __name__ == "__main__":
    main()
