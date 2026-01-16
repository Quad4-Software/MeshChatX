#!/usr/bin/env python

import argparse
import asyncio
import atexit
import base64
import configparser
import copy
import gc
import hashlib
import importlib.metadata
import ipaddress
import json
import logging
import os
import platform
import secrets
import shutil
import socket
import ssl
import sys
import tempfile
import threading
import time
import traceback
import webbrowser
from datetime import UTC, datetime, timedelta
from logging.handlers import RotatingFileHandler
from urllib.parse import urlparse

import aiohttp
import bcrypt
import LXMF
import LXST
import psutil
import RNS
from aiohttp import WSCloseCode, WSMessage, WSMsgType, web
from aiohttp_session import get_session
from aiohttp_session import setup as setup_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from RNS.Discovery import InterfaceDiscovery
from serial.tools import list_ports

from meshchatx.src.backend.async_utils import AsyncUtils
from meshchatx.src.backend.colour_utils import ColourUtils
from meshchatx.src.backend.identity_context import IdentityContext
from meshchatx.src.backend.identity_manager import IdentityManager
from meshchatx.src.backend.interface_config_parser import InterfaceConfigParser
from meshchatx.src.backend.interface_editor import InterfaceEditor
from meshchatx.src.backend.lxmf_message_fields import (
    LxmfAudioField,
    LxmfFileAttachment,
    LxmfFileAttachmentsField,
    LxmfImageField,
)
from meshchatx.src.backend.lxmf_utils import (
    convert_db_lxmf_message_to_dict,
    convert_lxmf_message_to_dict,
)
from meshchatx.src.backend.map_manager import TRANSPARENT_TILE
from meshchatx.src.backend.markdown_renderer import MarkdownRenderer
from meshchatx.src.backend.meshchat_utils import (
    convert_db_favourite_to_dict,
    convert_propagation_node_state_to_string,
    has_attachments,
    message_fields_have_attachments,
    parse_bool_query_param,
    parse_lxmf_display_name,
    parse_lxmf_propagation_node_app_data,
    parse_lxmf_stamp_cost,
    parse_nomadnetwork_node_display_name,
)
from meshchatx.src.backend.nomadnet_downloader import (
    NomadnetFileDownloader,
    NomadnetPageDownloader,
    nomadnet_cached_links,
)
from meshchatx.src.backend.nomadnet_utils import (
    convert_nomadnet_field_data_to_map,
    convert_nomadnet_string_data_to_map,
)
from meshchatx.src.backend.persistent_log_handler import PersistentLogHandler
from meshchatx.src.backend.recovery import CrashRecovery
from meshchatx.src.backend.rnprobe_handler import RNProbeHandler
from meshchatx.src.backend.sideband_commands import SidebandCommands
from meshchatx.src.backend.telemetry_utils import Telemeter
from meshchatx.src.backend.web_audio_bridge import WebAudioBridge
from meshchatx.src.version import __version__ as app_version


def resolve_log_dir():
    """Choose a writable log directory across container, desktop, and Windows."""
    env_dir = os.environ.get("MESHCHAT_LOG_DIR")
    candidates = []
    if env_dir:
        candidates.append(env_dir)

    candidates.append("/config/logs")

    if os.name == "nt":
        appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if appdata:
            candidates.append(os.path.join(appdata, "MeshChatX", "logs"))

    home_dir = os.path.expanduser("~")
    candidates.append(os.path.join(home_dir, ".reticulum-meshchatx", "logs"))
    candidates.append(os.path.join(tempfile.gettempdir(), "meshchatx", "logs"))

    for path in candidates:
        if not path:
            continue
        try:
            os.makedirs(path, exist_ok=True)
            return path
        except PermissionError:
            continue
        except OSError:
            continue

    return None


# Global log handler
memory_log_handler = PersistentLogHandler()
log_dir = resolve_log_dir()
handlers = [memory_log_handler]

if log_dir:
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "meshchatx.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handlers.append(file_handler)
else:
    handlers.append(logging.StreamHandler(sys.stdout))

logging.basicConfig(level=logging.INFO, handlers=handlers)
logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
logger = logging.getLogger("meshchatx")


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
        public_dir: str | None = None,
        emergency: bool = False,
        gitea_base_url: str | None = None,
        docs_download_urls: str | None = None,
    ):
        self.running = True
        self.reticulum_config_dir = reticulum_config_dir
        self.storage_dir = storage_dir or os.path.join("storage")
        self.identity_file_path = identity_file_path
        self.auto_recover = auto_recover
        self.emergency = emergency
        self.auth_enabled_initial = auth_enabled
        self.public_dir_override = public_dir
        self.gitea_base_url_override = gitea_base_url
        self.docs_download_urls_override = docs_download_urls
        self.websocket_clients: list[web.WebSocketResponse] = []

        # track announce timestamps for rate calculation
        self.announce_timestamps = []

        # track download speeds for nomadnetwork files
        self.download_speeds = []

        # track active downloads
        self.active_downloads = {}
        self.download_id_counter = 0

        self.identity_manager = IdentityManager(self.storage_dir, identity_file_path)

        # Multi-identity support
        self.contexts: dict[str, IdentityContext] = {}
        self.current_context: IdentityContext | None = None

        self.setup_identity(identity)
        self.web_audio_bridge = WebAudioBridge(None, None)

    # Proxy properties for backward compatibility
    @property
    def identity(self):
        return self.current_context.identity if self.current_context else None

    @identity.setter
    def identity(self, value):
        if self.current_context:
            self.current_context.identity = value

    @property
    def database(self):
        return self.current_context.database if self.current_context else None

    @database.setter
    def database(self, value):
        if self.current_context:
            self.current_context.database = value

    @property
    def db(self):
        return self.database

    @db.setter
    def db(self, value):
        self.database = value

    @property
    def config(self):
        return self.current_context.config if self.current_context else None

    @config.setter
    def config(self, value):
        if self.current_context:
            self.current_context.config = value

    @property
    def message_handler(self):
        return self.current_context.message_handler if self.current_context else None

    @message_handler.setter
    def message_handler(self, value):
        if self.current_context:
            self.current_context.message_handler = value

    @property
    def announce_manager(self):
        return self.current_context.announce_manager if self.current_context else None

    @announce_manager.setter
    def announce_manager(self, value):
        if self.current_context:
            self.current_context.announce_manager = value

    @property
    def archiver_manager(self):
        return self.current_context.archiver_manager if self.current_context else None

    @archiver_manager.setter
    def archiver_manager(self, value):
        if self.current_context:
            self.current_context.archiver_manager = value

    @property
    def map_manager(self):
        return self.current_context.map_manager if self.current_context else None

    @map_manager.setter
    def map_manager(self, value):
        if self.current_context:
            self.current_context.map_manager = value

    @property
    def docs_manager(self):
        return self.current_context.docs_manager if self.current_context else None

    @docs_manager.setter
    def docs_manager(self, value):
        if self.current_context:
            self.current_context.docs_manager = value

    @property
    def nomadnet_manager(self):
        return self.current_context.nomadnet_manager if self.current_context else None

    @nomadnet_manager.setter
    def nomadnet_manager(self, value):
        if self.current_context:
            self.current_context.nomadnet_manager = value

    @property
    def message_router(self):
        return self.current_context.message_router if self.current_context else None

    @message_router.setter
    def message_router(self, value):
        if self.current_context:
            self.current_context.message_router = value

    @property
    def telephone_manager(self):
        return self.current_context.telephone_manager if self.current_context else None

    @telephone_manager.setter
    def telephone_manager(self, value):
        if self.current_context:
            self.current_context.telephone_manager = value

    @property
    def voicemail_manager(self):
        return self.current_context.voicemail_manager if self.current_context else None

    @voicemail_manager.setter
    def voicemail_manager(self, value):
        if self.current_context:
            self.current_context.voicemail_manager = value

    @property
    def ringtone_manager(self):
        return self.current_context.ringtone_manager if self.current_context else None

    @ringtone_manager.setter
    def ringtone_manager(self, value):
        if self.current_context:
            self.current_context.ringtone_manager = value

    @property
    def rncp_handler(self):
        return self.current_context.rncp_handler if self.current_context else None

    @rncp_handler.setter
    def rncp_handler(self, value):
        if self.current_context:
            self.current_context.rncp_handler = value

    @property
    def rnstatus_handler(self):
        return self.current_context.rnstatus_handler if self.current_context else None

    @rnstatus_handler.setter
    def rnstatus_handler(self, value):
        if self.current_context:
            self.current_context.rnstatus_handler = value

    @property
    def rnpath_handler(self):
        return self.current_context.rnpath_handler if self.current_context else None

    @rnpath_handler.setter
    def rnpath_handler(self, value):
        if self.current_context:
            self.current_context.rnpath_handler = value

    @property
    def rnpath_trace_handler(self):
        return (
            self.current_context.rnpath_trace_handler if self.current_context else None
        )

    @rnpath_trace_handler.setter
    def rnpath_trace_handler(self, value):
        if self.current_context:
            self.current_context.rnpath_trace_handler = value

    @property
    def rnprobe_handler(self):
        return self.current_context.rnprobe_handler if self.current_context else None

    @rnprobe_handler.setter
    def rnprobe_handler(self, value):
        if self.current_context:
            self.current_context.rnprobe_handler = value

    @property
    def translator_handler(self):
        return self.current_context.translator_handler if self.current_context else None

    @translator_handler.setter
    def translator_handler(self, value):
        if self.current_context:
            self.current_context.translator_handler = value

    @property
    def bot_handler(self):
        return self.current_context.bot_handler if self.current_context else None

    @bot_handler.setter
    def bot_handler(self, value):
        if self.current_context:
            self.current_context.bot_handler = value

    @property
    def forwarding_manager(self):
        return self.current_context.forwarding_manager if self.current_context else None

    @forwarding_manager.setter
    def forwarding_manager(self, value):
        if self.current_context:
            self.current_context.forwarding_manager = value

    @property
    def community_interfaces_manager(self):
        return (
            self.current_context.community_interfaces_manager
            if self.current_context
            else None
        )

    @community_interfaces_manager.setter
    def community_interfaces_manager(self, value):
        if self.current_context:
            self.current_context.community_interfaces_manager = value

    @property
    def local_lxmf_destination(self):
        return (
            self.current_context.local_lxmf_destination
            if self.current_context
            else None
        )

    @local_lxmf_destination.setter
    def local_lxmf_destination(self, value):
        if self.current_context:
            self.current_context.local_lxmf_destination = value

    @property
    def auth_enabled(self):
        if self.config:
            return self.config.auth_enabled.get()
        return self.auth_enabled_initial

    @property
    def storage_path(self):
        return (
            self.current_context.storage_path
            if self.current_context
            else self.storage_dir
        )

    @storage_path.setter
    def storage_path(self, value):
        if self.current_context:
            self.current_context.storage_path = value

    @property
    def database_path(self):
        return self.current_context.database_path if self.current_context else None

    @property
    def _identity_session_id(self):
        return self.current_context.session_id if self.current_context else 0

    @_identity_session_id.setter
    def _identity_session_id(self, value):
        if self.current_context:
            self.current_context.session_id = value

    def get_public_path(self, filename=""):
        if self.public_dir_override:
            return os.path.join(self.public_dir_override, filename)
        return get_file_path(os.path.join("public", filename))

    def backup_database(self, backup_path=None):
        if not self.database:
            raise RuntimeError("Database not initialized")
        return self.database.backup_database(self.storage_dir, backup_path)

    def restore_database(self, backup_path):
        if not self.database:
            raise RuntimeError("Database not initialized")
        return self.database.restore_database(backup_path)

    def _ensure_reticulum_config(self):
        """Ensures that a valid Reticulum config file exists at the expected location.
        If the config is missing or invalid, it creates a sane default one.
        """
        config_dir = self.reticulum_config_dir or RNS.Reticulum.configpath
        config_file = os.path.join(config_dir, "config")

        should_recreate = False

        if not os.path.exists(config_file):
            should_recreate = True
            print(
                f"Reticulum config file not found at {config_file}, creating a default one...",
            )
        else:
            try:
                with open(config_file) as f:
                    content = f.read()
                    if "[reticulum]" not in content or "[interfaces]" not in content:
                        print(
                            f"Reticulum config file at {config_file} is invalid (missing essential sections), recreating...",
                        )
                        should_recreate = True
            except Exception as e:
                print(
                    f"Failed to read Reticulum config at {config_file} ({e}), recreating...",
                )
                should_recreate = True

        if should_recreate:
            try:
                if not os.path.exists(config_dir):
                    os.makedirs(config_dir, exist_ok=True)

                default_config = """# This is the default Reticulum config file.
# You should probably edit it to include any additional,
# interfaces and settings you might need.

# Only the most basic options are included in this default
# configuration. To see a more verbose, and much longer,
# configuration example, you can run the command:
# rnsd --exampleconfig


[reticulum]
  
  # If you enable Transport, your system will route traffic
  # for other peers, pass announces and serve path requests.
  # This should only be done for systems that are suited to
  # act as transport nodes, ie. if they are stationary and
  # always-on. This directive is optional and can be removed
  # for brevity.
  
  enable_transport = False
  
  
  # By default, the first program to launch the Reticulum
  # Network Stack will create a shared instance, that other
  # programs can communicate with. Only the shared instance
  # opens all the configured interfaces directly, and other
  # local programs communicate with the shared instance over
  # a local socket. This is completely transparent to the
  # user, and should generally be turned on. This directive
  # is optional and can be removed for brevity.
  
  share_instance = Yes
  
  
  # If you want to run multiple *different* shared instances
  # on the same system, you will need to specify different
  # instance names for each. On platforms supporting domain
  # sockets, this can be done with the instance_name option:
  
  instance_name = default
  discover_interfaces = True
  autoconnect_discovered_interfaces = 3
  required_discovery_value = 16

# Some platforms don't support domain sockets, and if that
# is the case, you can isolate different instances by
# specifying a unique set of ports for each:

# shared_instance_port = 37428
# instance_control_port = 37429


# If you want to explicitly use TCP for shared instance
# communication, instead of domain sockets, this is also
# possible, by using the following option:

# shared_instance_type = tcp


# You can configure Reticulum to panic and forcibly close
# if an unrecoverable interface error occurs, such as the
# hardware device for an interface disappearing. This is
# an optional directive, and can be left out for brevity.
# This behaviour is disabled by default.

# panic_on_interface_error = No


[logging]
  # Valid log levels are 0 through 7:
  #   0: Log only critical information
  #   1: Log errors and lower log levels
  #   2: Log warnings and lower log levels
  #   3: Log notices and lower log levels
  #   4: Log info and lower (this is the default)
  #   5: Verbose logging
  #   6: Debug logging
  #   7: Extreme logging
  
  loglevel = 4


# The interfaces section defines the physical and virtual
# interfaces Reticulum will use to communicate on. This
# section will contain examples for a variety of interface
# types. You can modify these or use them as a basis for
# your own config, or simply remove the unused ones.

[interfaces]
  
  # This interface enables communication with other
  # link-local Reticulum nodes over UDP. It does not
  # need any functional IP infrastructure like routers
  # or DHCP servers, but will require that at least link-
  # local IPv6 is enabled in your operating system, which
  # should be enabled by default in almost any OS. See
  # the Reticulum Manual for more configuration options.
  
  [[Default Interface]]
    type = AutoInterface
    enabled = false
    name = Default Interface
    selected_interface_mode = 1
"""
                with open(config_file, "w") as f:
                    f.write(default_config)
                print(f"Default Reticulum config created at {config_file}")
            except Exception as e:
                print(
                    f"Failed to create default Reticulum config at {config_file}: {e}",
                )

    def setup_identity(self, identity: RNS.Identity):
        identity_hash = identity.hash.hex()

        self.running = True

        # Check if we already have a context for this identity
        if identity_hash in self.contexts:
            self.current_context = self.contexts[identity_hash]
            if not self.current_context.running:
                self.current_context.setup()
            self.web_audio_bridge = WebAudioBridge(
                self.current_context.telephone_manager,
                self.current_context.config,
            )
            return

        # Initialize Reticulum if not already done
        if not hasattr(self, "reticulum"):
            self._ensure_reticulum_config()
            self.reticulum = RNS.Reticulum(self.reticulum_config_dir)

        # Create new context
        context = IdentityContext(identity, self)
        self.contexts[identity_hash] = context
        self.current_context = context
        context.setup()
        self.web_audio_bridge = WebAudioBridge(
            context.telephone_manager,
            context.config,
        )

        # Link database to memory log handler
        memory_log_handler.set_database(context.database)

    def _checkpoint_and_close(self):
        # delegated to database instance
        self.database._checkpoint_and_close()

    def _get_identity_bytes(self) -> bytes:
        return self.identity_manager.get_identity_bytes(self.identity)

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
                        f"Deregistering RNS destination {destination} ({RNS.prettyhexrep(destination.hash)})",
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
                    except Exception:  # noqa: S110
                        pass
        except Exception as e:
            print(f"Error while cleaning up RNS links: {e}")

    def teardown_identity(self):
        if self.current_context:
            self.running = False
            identity_hash = self.current_context.identity_hash
            self.current_context.teardown()
            if identity_hash in self.contexts:
                del self.contexts[identity_hash]
            self.current_context = None

    async def reload_reticulum(self):
        print("Hot reloading Reticulum stack...")
        # Keep reference to old reticulum instance for cleanup
        old_reticulum = getattr(self, "reticulum", None)

        try:
            # Signal background loops to exit
            self._identity_session_id += 1

            # Teardown current identity state and managers
            # This also calls cleanup_rns_state_for_identity
            self.teardown_identity()

            # Give loops a moment to finish
            await asyncio.sleep(2)

            # Close RNS instance first to let it detach interfaces naturally
            try:
                # Use class method to ensure all instances are cleaned up if any
                RNS.Reticulum.exit_handler()
            except Exception as e:
                print(f"Warning during RNS exit: {e}")

            # Aggressively close RNS interfaces to release sockets if they didn't close
            try:
                interfaces = []
                if hasattr(RNS.Transport, "interfaces"):
                    interfaces.extend(RNS.Transport.interfaces)
                if hasattr(RNS.Transport, "local_client_interfaces"):
                    interfaces.extend(RNS.Transport.local_client_interfaces)

                for interface in interfaces:
                    try:
                        # Generic socketserver shutdown
                        if hasattr(interface, "server") and interface.server:
                            try:
                                interface.server.shutdown()
                                interface.server.server_close()
                            except Exception:  # noqa: S110
                                pass

                        # AutoInterface specific
                        if hasattr(interface, "interface_servers"):
                            for server in interface.interface_servers.values():
                                try:
                                    server.shutdown()
                                    server.server_close()
                                except Exception:  # noqa: S110
                                    pass

                        # For LocalServerInterface which Reticulum doesn't close properly
                        if hasattr(interface, "server") and interface.server:
                            try:
                                interface.server.shutdown()
                                interface.server.server_close()
                            except Exception:  # noqa: S110
                                pass

                        # TCPClientInterface/etc
                        if hasattr(interface, "socket") and interface.socket:
                            try:
                                # Check if socket is still valid before shutdown
                                if (
                                    hasattr(interface.socket, "fileno")
                                    and interface.socket.fileno() != -1
                                ):
                                    try:
                                        interface.socket.shutdown(socket.SHUT_RDWR)
                                    except Exception:  # noqa: S110
                                        pass
                                    try:
                                        interface.socket.close()
                                    except Exception:  # noqa: S110
                                        pass
                            except Exception:  # noqa: S110
                                pass

                        interface.detach()
                        interface.detached = True
                    except Exception as e:
                        print(f"Warning closing interface during reload: {e}")
            except Exception as e:
                print(f"Warning during aggressive interface cleanup: {e}")

            # Close RPC listener if it exists on the instance
            if old_reticulum:
                # Reticulum uses private attributes for the listener
                rpc_listener_names = [
                    "rpc_listener",
                    "_Reticulum__rpc_listener",
                    "_rpc_listener",
                ]
                for attr_name in rpc_listener_names:
                    if hasattr(old_reticulum, attr_name):
                        listener = getattr(old_reticulum, attr_name)
                        if listener:
                            try:
                                print(
                                    f"Forcing closure of RPC listener in {attr_name}...",
                                )
                                if hasattr(listener, "close"):
                                    listener.close()
                                setattr(old_reticulum, attr_name, None)
                            except Exception as e:
                                print(f"Warning closing RPC listener {attr_name}: {e}")

            # Clear RNS singleton and internal state to allow re-initialization
            try:
                # Reticulum uses private variables for singleton and state control
                # We need to clear them so we can create a new instance
                if hasattr(RNS.Reticulum, "_Reticulum__instance"):
                    RNS.Reticulum._Reticulum__instance = None
                if hasattr(RNS.Reticulum, "_Reticulum__exit_handler_ran"):
                    RNS.Reticulum._Reticulum__exit_handler_ran = False
                if hasattr(RNS.Reticulum, "_Reticulum__interface_detach_ran"):
                    RNS.Reticulum._Reticulum__interface_detach_ran = False

                # Also clear Transport caches and globals
                RNS.Transport.interfaces = []
                RNS.Transport.local_client_interfaces = []
                RNS.Transport.destinations = []
                RNS.Transport.active_links = []
                RNS.Transport.pending_links = []
                RNS.Transport.announce_handlers = []
                RNS.Transport.jobs_running = False

                # Clear Identity globals
                RNS.Identity.known_destinations = {}
                RNS.Identity.known_ratchets = {}

                # Unregister old exit handlers from atexit if possible
                try:
                    # Reticulum uses a staticmethod exit_handler
                    atexit.unregister(RNS.Reticulum.exit_handler)
                except Exception:  # noqa: S110
                    pass

            except Exception as e:
                print(f"Warning clearing RNS state: {e}")

            # Remove reticulum instance from self
            if hasattr(self, "reticulum"):
                del self.reticulum

            # Wait another moment for sockets to definitely be released by OS
            # Also give some time for the RPC listener port to settle
            print("Waiting for ports to settle...")
            await asyncio.sleep(4)

            # Detect RPC type from reticulum instance if possible, otherwise default to both
            rpc_addrs = []
            if old_reticulum:
                if hasattr(old_reticulum, "rpc_addr") and old_reticulum.rpc_addr:
                    rpc_addrs.append(
                        (
                            old_reticulum.rpc_addr,
                            getattr(old_reticulum, "rpc_type", "AF_INET"),
                        ),
                    )

            # Also check the config file for ports
            try:
                config_dir = getattr(self, "reticulum_config_dir", None)
                if not config_dir:
                    if hasattr(RNS.Reticulum, "configdir") and RNS.Reticulum.configdir:
                        config_dir = RNS.Reticulum.configdir
                    else:
                        config_dir = os.path.expanduser("~/.reticulum")

                config_path = os.path.join(config_dir, "config")
                if os.path.isfile(config_path):
                    cp = configparser.ConfigParser()
                    cp.read(config_path)
                    if cp.has_section("reticulum"):
                        rpc_port = cp.getint("reticulum", "rpc_port", fallback=37429)
                        rpc_bind = cp.get("reticulum", "rpc_bind", fallback="127.0.0.1")
                        shared_port = cp.getint(
                            "reticulum",
                            "shared_instance_port",
                            fallback=37428,
                        )
                        shared_bind = cp.get(
                            "reticulum",
                            "shared_instance_bind",
                            fallback="127.0.0.1",
                        )

                        # Only add if not already there
                        if not any(
                            addr == (rpc_bind, rpc_port) for addr, _ in rpc_addrs
                        ):
                            rpc_addrs.append(((rpc_bind, rpc_port), "AF_INET"))
                        if not any(
                            addr == (shared_bind, shared_port) for addr, _ in rpc_addrs
                        ):
                            rpc_addrs.append(((shared_bind, shared_port), "AF_INET"))
            except Exception as e:
                print(f"Warning reading Reticulum config for ports: {e}")

            if not rpc_addrs:
                # Defaults
                rpc_addrs.append((("127.0.0.1", 37429), "AF_INET"))
                rpc_addrs.append((("127.0.0.1", 37428), "AF_INET"))
                if platform.system() == "Linux":
                    rpc_addrs.append(("\0rns/default/rpc", "AF_UNIX"))

            for i in range(15):
                all_free = True
                for addr, family_str in rpc_addrs:
                    try:
                        family = (
                            socket.AF_INET
                            if family_str == "AF_INET"
                            else socket.AF_UNIX
                        )
                        s = socket.socket(family, socket.SOCK_STREAM)
                        s.settimeout(0.5)
                        try:
                            # Use SO_REUSEADDR to check if we can actually bind
                            if family == socket.AF_INET:
                                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                            s.bind(addr)
                            s.close()
                        except OSError:
                            addr_display = addr
                            if (
                                family == socket.AF_UNIX
                                and isinstance(addr, str)
                                and addr.startswith("\0")
                            ):
                                addr_display = addr[1:] + " (abstract)"

                            print(
                                f"RPC addr {addr_display} still in use... (attempt {i + 1}/15)",
                            )
                            s.close()
                            all_free = False

                            # If we are stuck, try to force close the connection manually
                            if i > 1:
                                try:
                                    current_process = psutil.Process()
                                    # We use kind='all' to catch both TCP and UNIX sockets
                                    for conn in current_process.connections(kind="all"):
                                        try:
                                            match = False
                                            if conn.laddr:
                                                if (
                                                    family_str == "AF_INET"
                                                    and isinstance(conn.laddr, tuple)
                                                ):
                                                    # Match IP and port for IPv4
                                                    if conn.laddr.port == addr[1] and (
                                                        conn.laddr.ip == addr[0]
                                                        or addr[0] == "0.0.0.0"  # noqa: S104
                                                    ):
                                                        match = True
                                                elif family_str == "AF_UNIX":
                                                    # Match path for UNIX sockets, including abstract
                                                    # Psutil sometimes returns abstract addresses as strings or bytes,
                                                    # with or without the leading null byte.
                                                    laddr = conn.laddr

                                                    # Normalize both to bytes for comparison
                                                    target_addr = (
                                                        addr
                                                        if isinstance(addr, bytes)
                                                        else addr.encode()
                                                        if isinstance(addr, str)
                                                        else b""
                                                    )
                                                    current_laddr = (
                                                        laddr
                                                        if isinstance(laddr, bytes)
                                                        else laddr.encode()
                                                        if isinstance(laddr, str)
                                                        else b""
                                                    )

                                                    if (
                                                        current_laddr == target_addr
                                                        or (
                                                            target_addr.startswith(
                                                                b"\0",
                                                            )
                                                            and current_laddr
                                                            == target_addr[1:]
                                                        )
                                                        or (
                                                            current_laddr.startswith(
                                                                b"\0",
                                                            )
                                                            and target_addr
                                                            == current_laddr[1:]
                                                        )
                                                    ):
                                                        match = True
                                                    elif (
                                                        target_addr in current_laddr
                                                        or current_laddr in target_addr
                                                    ):
                                                        # Last resort: partial match
                                                        if (
                                                            len(target_addr) > 5
                                                            and len(current_laddr) > 5
                                                        ):
                                                            match = True

                                            if match:
                                                # If we found a match, force close the file descriptor
                                                # to tell the OS to release the socket immediately.
                                                status_str = getattr(
                                                    conn,
                                                    "status",
                                                    "UNKNOWN",
                                                )
                                                print(
                                                    f"Force closing lingering {family_str} connection {conn.laddr} (status: {status_str})",
                                                )

                                                try:
                                                    if (
                                                        hasattr(conn, "fd")
                                                        and conn.fd != -1
                                                    ):
                                                        try:
                                                            os.close(conn.fd)
                                                        except Exception as fd_err:
                                                            print(
                                                                f"Failed to close FD {getattr(conn, 'fd', 'N/A')}: {fd_err}",
                                                            )
                                                except Exception:  # noqa: S110
                                                    pass
                                        except Exception:  # noqa: S110
                                            pass
                                except Exception as e:
                                    print(
                                        f"Error during manual RPC connection kill: {e}",
                                    )

                            break
                    except Exception as e:
                        print(f"Error checking RPC addr {addr}: {e}")

                if all_free:
                    print("All RNS ports/sockets are free.")
                    break

                await asyncio.sleep(1)

            if not all_free:
                # One last attempt with a very short sleep before failing
                await asyncio.sleep(2)
                # Check again one last time
                last_check_all_free = True
                for addr, family_str in rpc_addrs:
                    try:
                        family = (
                            socket.AF_INET
                            if family_str == "AF_INET"
                            else socket.AF_UNIX
                        )
                        s = socket.socket(family, socket.SOCK_STREAM)
                        try:
                            s.bind(addr)
                            s.close()
                        except OSError:
                            last_check_all_free = False
                            s.close()
                            break
                        except Exception:  # noqa: S110
                            pass
                    except Exception:  # noqa: S110
                        pass

                if not last_check_all_free:
                    raise OSError(
                        "Timeout waiting for RNS ports to be released. Cannot restart.",
                    )
                print("RNS ports finally free after last-second check.")

            # Final GC to ensure everything is released
            gc.collect()

            # Re-setup identity (this starts background loops again)
            self.running = True
            self.setup_identity(self.identity)

            return True
        except Exception as e:
            print(f"Hot reload failed: {e}")

            traceback.print_exc()

            # Try to recover if possible
            if not hasattr(self, "reticulum"):
                try:
                    self.setup_identity(self.identity)
                except Exception:  # noqa: S110
                    pass

            return False

    async def hotswap_identity(self, identity_hash, keep_alive=False):
        old_identity = self.identity

        main_identity_file = self.identity_file_path or os.path.join(
            self.storage_dir,
            "identity",
        )
        backup_identity_file = main_identity_file + ".bak"
        backup_created = False

        try:
            # load the new identity
            identity_dir = os.path.join(self.storage_dir, "identities", identity_hash)
            identity_file = os.path.join(identity_dir, "identity")
            if not os.path.exists(identity_file):
                raise ValueError("Identity file not found")

            # Validate that the identity file can be loaded
            new_identity = RNS.Identity.from_file(identity_file)
            if not new_identity:
                raise ValueError("Identity file corrupted or invalid")

            # 1. Backup current identity file
            if os.path.exists(main_identity_file):
                shutil.copy2(main_identity_file, backup_identity_file)
                backup_created = True

            # 2. teardown old identity if not keeping alive
            if not keep_alive:
                self.teardown_identity()
                # Give a moment for destinations to clear from transport
                await asyncio.sleep(2)

            # 3. update main identity file
            shutil.copy2(identity_file, main_identity_file)

            # 4. setup new identity
            self.running = True
            # setup_identity initializes context if needed and sets it as current
            self.setup_identity(new_identity)

            # 5. broadcast update to clients
            await self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "identity_switched",
                        "identity_hash": identity_hash,
                        "display_name": (
                            self.config.display_name.get()
                            if hasattr(self, "config")
                            else "Unknown"
                        ),
                    },
                ),
            )

            # Clean up backup on success
            if backup_created and os.path.exists(backup_identity_file):
                os.remove(backup_identity_file)

            return True
        except Exception as e:
            print(f"Hotswap failed: {e}")
            traceback.print_exc()

            # RECOVERY: Try to switch back to last identity
            try:
                print("Attempting to restore previous identity...")
                if backup_created and os.path.exists(backup_identity_file):
                    shutil.copy2(backup_identity_file, main_identity_file)
                    os.remove(backup_identity_file)

                self.running = True
                if old_identity:
                    self.setup_identity(old_identity)
            except Exception as recovery_err:
                print(f"Recovery failed: {recovery_err}")
                traceback.print_exc()

                # FINAL FAILSAFE: Create a brand new identity
                try:
                    print(
                        "CRITICAL: Restoration of previous identity failed. Creating a brand new emergency identity...",
                    )
                    new_id_data = self.create_identity(
                        display_name="Emergency Recovery",
                    )
                    new_id_hash = new_id_data["hash"]

                    # Try to load the newly created identity
                    emergency_identity_file = os.path.join(
                        self.storage_dir,
                        "identities",
                        new_id_hash,
                        "identity",
                    )
                    emergency_id = RNS.Identity.from_file(emergency_identity_file)

                    if emergency_id:
                        # Copy to main identity file
                        shutil.copy2(emergency_identity_file, main_identity_file)
                        self.running = True
                        self.setup_identity(emergency_id)
                        print(f"Emergency identity created and loaded: {new_id_hash}")
                    else:
                        raise RuntimeError(
                            "Failed to load newly created emergency identity",
                        )

                except Exception as final_err:
                    print(
                        f"ULTIMATE FAILURE: Could not even create emergency identity: {final_err}",
                    )
                    traceback.print_exc()

            return False

    def backup_identity(self):
        return self.identity_manager.backup_identity(self.identity)

    def backup_identity_base32(self) -> str:
        return self.identity_manager.backup_identity_base32(self.identity)

    def list_identities(self):
        return self.identity_manager.list_identities(
            self.identity.hash.hex()
            if hasattr(self, "identity") and self.identity
            else None,
        )

    def create_identity(self, display_name=None):
        return self.identity_manager.create_identity(display_name)

    def delete_identity(self, identity_hash):
        current_hash = (
            self.identity.hash.hex()
            if hasattr(self, "identity") and self.identity
            else None
        )
        return self.identity_manager.delete_identity(identity_hash, current_hash)

    def restore_identity_from_bytes(self, identity_bytes: bytes):
        return self.identity_manager.restore_identity_from_bytes(identity_bytes)

    def restore_identity_from_base32(self, base32_value: str):
        return self.identity_manager.restore_identity_from_base32(base32_value)

    def update_identity_metadata_cache(self):
        if not hasattr(self, "identity") or not self.identity:
            return

        identity_hash = self.identity.hash.hex()
        metadata = {
            "display_name": self.config.display_name.get(),
            "icon_name": self.config.lxmf_user_icon_name.get(),
            "icon_foreground_colour": self.config.lxmf_user_icon_foreground_colour.get(),
            "icon_background_colour": self.config.lxmf_user_icon_background_colour.get(),
            "lxmf_address": self.config.lxmf_address_hash.get(),
            "lxst_address": self.config.lxst_address_hash.get(),
        }
        self.identity_manager.update_metadata_cache(identity_hash, metadata)

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
            self.database._tune_sqlite_pragmas()
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

    @staticmethod
    def get_package_version(package_name: str, default: str = "unknown") -> str:
        try:
            return importlib.metadata.version(package_name)
        except Exception:
            try:
                # try to import the package and get __version__
                # some packages use underscores instead of hyphens in module names
                module_name = package_name.replace("-", "_")
                module = __import__(module_name)
                return getattr(module, "__version__", default)
            except Exception:
                return default

    def get_lxst_version(self) -> str:
        return self.get_package_version("lxst", getattr(LXST, "__version__", "unknown"))

    # automatically announces based on user config
    async def announce_loop(self, session_id, context=None):
        ctx = context or self.current_context
        if not ctx:
            return

        while self.running and ctx.running and ctx.session_id == session_id:
            should_announce = False

            # check if auto announce is enabled
            if ctx.config.auto_announce_enabled.get():
                # check if we have announced recently
                last_announced_at = ctx.config.last_announced_at.get()
                if last_announced_at is not None:
                    # determine when next announce should be sent
                    auto_announce_interval_seconds = (
                        ctx.config.auto_announce_interval_seconds.get()
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
                await self.announce(context=ctx)

                # also announce forwarding aliases if any
                if ctx.forwarding_manager:
                    await asyncio.to_thread(ctx.forwarding_manager.announce_aliases)

            # wait 1 second before next loop
            await asyncio.sleep(1)

    # automatically syncs propagation nodes based on user config
    async def announce_sync_propagation_nodes(self, session_id, context=None):
        ctx = context or self.current_context
        if not ctx:
            return

        while self.running and ctx.running and ctx.session_id == session_id:
            should_sync = False

            # check if auto sync is enabled
            auto_sync_interval_seconds = ctx.config.lxmf_preferred_propagation_node_auto_sync_interval_seconds.get()
            if auto_sync_interval_seconds > 0:
                # check if we have synced recently
                last_synced_at = (
                    ctx.config.lxmf_preferred_propagation_node_last_synced_at.get()
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
                await self.sync_propagation_nodes(context=ctx)

            # wait 1 second before next loop
            await asyncio.sleep(1)

    async def crawler_loop(self, session_id, context=None):
        ctx = context or self.current_context
        if not ctx:
            return

        while self.running and ctx.running and ctx.session_id == session_id:
            try:
                if ctx.config.crawler_enabled.get():
                    # Proactively queue any known nodes from the database that haven't been queued yet
                    # get known propagation nodes from database
                    known_nodes = ctx.database.announces.get_announces(
                        aspect="nomadnetwork.node",
                    )
                    for node in known_nodes:
                        if (
                            not self.running
                            or not ctx.running
                            or ctx.session_id != session_id
                        ):
                            break
                        self.queue_crawler_task(
                            node["destination_hash"],
                            "/page/index.mu",
                            context=ctx,
                        )

                    # process pending or failed tasks
                    # ensure we handle potential string comparison issues in SQLite
                    tasks = ctx.database.misc.get_pending_or_failed_crawl_tasks(
                        max_retries=ctx.config.crawler_max_retries.get(),
                        max_concurrent=ctx.config.crawler_max_concurrent.get(),
                    )

                    # process tasks concurrently up to the limit
                    if tasks and self.running and ctx.running:
                        await asyncio.gather(
                            *[
                                self.process_crawler_task(task, context=ctx)
                                for task in tasks
                            ],
                        )

            except Exception as e:
                print(f"Error in crawler loop for {ctx.identity_hash}: {e}")

            # wait 30 seconds before checking again
            for _ in range(30):
                if not self.running or not ctx.running or ctx.session_id != session_id:
                    return
                await asyncio.sleep(1)

    async def process_crawler_task(self, task, context=None):
        ctx = context or self.current_context
        if not ctx:
            return

        # mark as crawling
        task_id = task["id"]
        ctx.database.misc.update_crawl_task(
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
                context=ctx,
            )
            ctx.database.misc.update_crawl_task(
                task_id,
                status="completed",
                updated_at=datetime.now(UTC),
            )
        else:
            print(
                f"Crawler: Failed to archive {destination_hash}:{page_path} - {failure_reason[0]}",
            )
            retry_count = task["retry_count"] + 1

            # calculate next retry time
            retry_delay = ctx.config.crawler_retry_delay_seconds.get()
            # simple backoff
            backoff_delay = retry_delay * (2 ** (retry_count - 1))
            next_retry_at = datetime.now(UTC) + timedelta(seconds=backoff_delay)

            ctx.database.misc.update_crawl_task(
                task_id,
                status="failed",
                retry_count=retry_count,
                next_retry_at=next_retry_at,
                updated_at=datetime.now(UTC),
            )

    # uses the provided destination hash as the active propagation node
    def set_active_propagation_node(self, destination_hash: str | None, context=None):
        ctx = context or self.current_context
        if not ctx:
            return

        # set outbound propagation node
        if destination_hash is not None and destination_hash != "":
            try:
                ctx.message_router.set_outbound_propagation_node(
                    bytes.fromhex(destination_hash),
                )
            except Exception:
                # failed to set propagation node, clear it to ensure we don't use an old one by mistake
                self.remove_active_propagation_node(context=ctx)

        # stop using propagation node
        else:
            self.remove_active_propagation_node(context=ctx)

    # stops the in progress propagation node sync
    def stop_propagation_node_sync(self, context=None):
        ctx = context or self.current_context
        if not ctx:
            return
        ctx.message_router.cancel_propagation_node_requests()

    # stops and removes the active propagation node
    def remove_active_propagation_node(self, context=None):
        ctx = context or self.current_context
        if not ctx:
            return
        # fixme: it's possible for internal transfer state to get stuck if we change propagation node during a sync
        # this still happens even if we cancel the propagation node requests
        # for now, the user can just manually cancel syncing in the ui if they think it's stuck...
        self.stop_propagation_node_sync(context=ctx)
        ctx.message_router.outbound_propagation_node = None

    # enables or disables the local lxmf propagation node
    def enable_local_propagation_node(self, enabled: bool = True, context=None):
        ctx = context or self.current_context
        if not ctx:
            return
        try:
            if enabled:
                ctx.message_router.enable_propagation()
            else:
                ctx.message_router.disable_propagation()
        except Exception:
            print(
                f"failed to enable or disable propagation node for {ctx.identity_hash}",
            )

    def _get_reticulum_section(self):
        try:
            if hasattr(self, "reticulum") and self.reticulum:
                reticulum_config = self.reticulum.config["reticulum"]
            else:
                return {}
        except Exception:
            reticulum_config = None

        if not isinstance(reticulum_config, dict):
            reticulum_config = {}
            if hasattr(self, "reticulum") and self.reticulum:
                self.reticulum.config["reticulum"] = reticulum_config

        return reticulum_config

    def _get_interfaces_section(self):
        try:
            if hasattr(self, "reticulum") and self.reticulum:
                interfaces = self.reticulum.config["interfaces"]
            else:
                return {}
        except Exception:
            interfaces = None

        if not isinstance(interfaces, dict):
            interfaces = {}
            if hasattr(self, "reticulum") and self.reticulum:
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
            if hasattr(self, "reticulum") and self.reticulum:
                self.reticulum.config.write()
                return True
            return False
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

        if (
            hasattr(self, "reticulum")
            and self.reticulum
            and not self.reticulum.transport_enabled()
        ):
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
        local_hash = self.identity.hash.hex()
        messages = self.message_handler.get_conversation_messages(
            local_hash,
            destination_hash,
            limit=1,
        )
        return messages[0] if messages else None

    # returns true if the conversation with the provided destination hash has any attachments
    def conversation_has_attachments(self, destination_hash: str):
        local_hash = self.identity.hash.hex()
        messages = self.message_handler.get_conversation_messages(
            local_hash,
            destination_hash,
        )
        for message in messages:
            if message_fields_have_attachments(message["fields"]):
                return True
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

    def on_new_voicemail_received(
        self,
        remote_hash,
        remote_name,
        duration,
        context=None,
    ):
        ctx = context or self.current_context
        if not ctx:
            return
        # Add system notification
        self.database.misc.add_notification(
            notification_type="telephone_voicemail",
            remote_hash=remote_hash,
            title="New Voicemail",
            content=f"New voicemail from {remote_name or remote_hash} ({duration}s)",
        )

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
    def on_incoming_telephone_call(self, caller_identity: RNS.Identity, context=None):
        ctx = context or self.current_context
        if not ctx:
            return

        if ctx.telephone_manager and ctx.telephone_manager.initiation_status:
            print(
                "on_incoming_telephone_call: Ignoring as we are currently initiating an outgoing call.",
            )
            return

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
                    0.5,
                    lambda: self.telephone_manager.telephone.hangup(),
                ).start()
            return

        # Check if only allowing calls from contacts
        if self.config.telephone_allow_calls_from_contacts_only.get():
            contact = self.database.contacts.get_contact_by_identity_hash(caller_hash)
            if not contact:
                print(f"Rejecting incoming call from non-contact: {caller_hash}")
                if self.telephone_manager.telephone:
                    threading.Timer(
                        0.5,
                        lambda: self.telephone_manager.telephone.hangup(),
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

    def on_telephone_call_established(
        self,
        caller_identity: RNS.Identity,
        context=None,
    ):
        ctx = context or self.current_context
        if not ctx:
            return
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

    def on_telephone_call_ended(self, caller_identity: RNS.Identity, context=None):
        ctx = context or self.current_context
        if not ctx:
            return
        # Stop voicemail recording if active
        self.voicemail_manager.stop_recording()

        print(
            f"on_telephone_call_ended: {caller_identity.hash.hex() if caller_identity else 'Unknown'}",
        )
        try:
            self.web_audio_bridge.on_call_ended()
        except Exception as e:
            logging.exception(f"Error in web_audio_bridge.on_call_ended: {e}")

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

            # Trigger missed call notification if it was an incoming call that ended without being established
            if is_incoming and not self.telephone_manager.call_was_established:
                # Check if we should suppress the notification/websocket message
                # If DND was on, we still record it but maybe skip the noisy websocket?
                # Actually, persistent notification is good.

                self.database.misc.add_notification(
                    notification_type="telephone_missed_call",
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
                        remote_identity_hash,
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

    def on_telephone_initiation_status(self, status, target_hash, context=None):
        ctx = context or self.current_context
        if not ctx:
            return

        target_name = None
        if target_hash:
            try:
                contact = ctx.database.contacts.get_contact_by_identity_hash(
                    target_hash,
                )
                if contact:
                    target_name = contact.name
            except Exception:  # noqa: S110
                pass

        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "telephone_initiation_status",
                        "status": status,
                        "target_hash": target_hash,
                        "target_name": target_name,
                    },
                ),
            ),
        )

    # web server has shutdown, likely ctrl+c, but if we don't do the following, the script never exits
    async def shutdown(self, app):
        # force close websocket clients
        for websocket_client in self.websocket_clients:
            try:
                await websocket_client.close(code=WSCloseCode.GOING_AWAY)
            except Exception:  # noqa: S110
                pass

        # stop reticulum
        try:
            RNS.Transport.detach_interfaces()
        except Exception:  # noqa: S110
            pass

        if hasattr(self, "reticulum") and self.reticulum:
            try:
                self.reticulum.exit_handler()
            except Exception:  # noqa: S110
                pass

        try:
            RNS.exit()
        except Exception:  # noqa: S110
            pass

    def exit_app(self, code=0):
        sys.exit(code)

    def get_routes(self):
        # This is a bit of a hack to get the routes without running the full server
        # It's mainly for testing purposes
        routes = web.RouteTableDef()

        # We need to mock some things that are usually setup in run()
        # but for just getting the route handlers, we can skip most of it
        self._define_routes(routes)
        return routes

    def _define_routes(self, routes):
        # authentication middleware
        @web.middleware
        async def auth_middleware(request, handler):
            if not self.current_context or not self.current_context.running:
                return web.json_response(
                    {"error": "Application is initializing or switching identity"},
                    status=503,
                )

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

            # Allow WebSocket connections without auth if it's the handshake/upgrade request
            # Real auth for WS happens inside the connection if needed, or by cookie
            if path == "/ws":
                return await handler(request)

            # check if requesting setup page (index.html will show setup if needed)
            if (
                path == "/"
                or path.startswith("/assets/")
                or path.startswith("/favicons/")
                or path.endswith(".js")
                or path.endswith(".css")
                or path.endswith(".json")
                or path.endswith(".wasm")
                or path.endswith(".png")
                or path.endswith(".jpg")
                or path.endswith(".jpeg")
                or path.endswith(".ico")
                or path.endswith(".svg")
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
            index_path = self.get_public_path("index.html")
            if not os.path.exists(index_path):
                return web.Response(
                    text="""
                    <html>
                        <head><title>MeshChatX - Frontend Missing</title></head>
                        <body style="font-family: sans-serif; padding: 2rem; line-height: 1.5; background: #0f172a; color: #f8fafc;">
                            <h1 style="color: #38bdf8;">Frontend Missing</h1>
                            <p>The MeshChatX web interface files were not found.</p>
                            <p>If you are running from source, you must build the frontend first:</p>
                            <pre style="background: #1e293b; padding: 1rem; border-radius: 4px; color: #e2e8f0; border: 1px solid #334155;">pnpm install && pnpm run build-frontend</pre>
                            <p>For more information, see the <a href="https://git.quad4.io/RNS-Things/MeshChatX" style="color: #38bdf8;">README</a>.</p>
                        </body>
                    </html>
                    """,
                    content_type="text/html",
                    status=500,
                )
            return web.FileResponse(
                path=index_path,
                headers={
                    # don't allow browser to store page in cache, otherwise new app versions may get stale ui
                    "Cache-Control": "no-cache, no-store",
                },
            )

        # allow serving manifest.json and service-worker.js directly at root
        @routes.get("/manifest.json")
        async def manifest(request):
            return web.FileResponse(self.get_public_path("manifest.json"))

        @routes.get("/service-worker.js")
        async def service_worker(request):
            return web.FileResponse(self.get_public_path("service-worker.js"))

        @routes.get("/call.html")
        async def call_html_redirect(request):
            return web.HTTPFound("/#/popout/call")

        # serve debug logs
        @routes.get("/api/v1/debug/logs")
        async def get_debug_logs(request):
            search = request.query.get("search")
            level = request.query.get("level")
            module = request.query.get("module")
            is_anomaly = parse_bool_query_param(request.query.get("is_anomaly"))
            limit = int(request.query.get("limit", 100))
            offset = int(request.query.get("offset", 0))

            logs = memory_log_handler.get_logs(
                limit=limit,
                offset=offset,
                search=search,
                level=level,
                module=module,
                is_anomaly=is_anomaly,
            )
            total = memory_log_handler.get_total_count(
                search=search,
                level=level,
                module=module,
                is_anomaly=is_anomaly,
            )

            return web.json_response(
                {
                    "logs": logs,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                },
            )

        @routes.post("/api/v1/database/snapshot")
        async def create_db_snapshot(request):
            try:
                data = await request.json()
                name = data.get("name", f"snapshot-{int(time.time())}")
                result = self.database.create_snapshot(self.storage_dir, name)
                return web.json_response({"status": "success", "result": result})
            except Exception as e:
                return web.json_response(
                    {"status": "error", "message": str(e)},
                    status=500,
                )

        @routes.get("/api/v1/database/snapshots")
        async def list_db_snapshots(request):
            try:
                limit = int(request.query.get("limit", 100))
                offset = int(request.query.get("offset", 0))
                snapshots = self.database.list_snapshots(self.storage_dir)
                total = len(snapshots)
                paginated_snapshots = snapshots[offset : offset + limit]
                return web.json_response(
                    {
                        "snapshots": paginated_snapshots,
                        "total": total,
                        "limit": limit,
                        "offset": offset,
                    },
                )
            except Exception as e:
                return web.json_response(
                    {"status": "error", "message": str(e)},
                    status=500,
                )

        @routes.delete("/api/v1/database/snapshots/{filename}")
        async def delete_db_snapshot(request):
            try:
                filename = request.match_info.get("filename")
                if not filename.endswith(".zip"):
                    filename += ".zip"
                self.database.delete_snapshot_or_backup(
                    self.storage_dir,
                    filename,
                    is_backup=False,
                )
                return web.json_response({"status": "success"})
            except Exception as e:
                return web.json_response(
                    {"status": "error", "message": str(e)},
                    status=500,
                )

        @routes.post("/api/v1/database/restore")
        async def restore_db_snapshot(request):
            try:
                data = await request.json()
                path = data.get("path")
                if not path:
                    return web.json_response(
                        {"status": "error", "message": "No path provided"},
                        status=400,
                    )

                # Verify path is within storage_dir/snapshots or provided directly
                if not os.path.exists(path):
                    # Try relative to snapshots dir
                    potential_path = os.path.join(self.storage_dir, "snapshots", path)
                    if os.path.exists(potential_path):
                        path = potential_path
                    elif os.path.exists(potential_path + ".zip"):
                        path = potential_path + ".zip"
                    else:
                        return web.json_response(
                            {"status": "error", "message": "Snapshot not found"},
                            status=404,
                        )

                result = self.database.restore_database(path)
                # Note: This might require an app relaunch to be fully effective
                return web.json_response(
                    {"status": "success", "result": result, "requires_relaunch": True},
                )
            except Exception as e:
                return web.json_response(
                    {"status": "error", "message": str(e)},
                    status=500,
                )

        @routes.get("/api/v1/database/backups")
        async def list_db_backups(request):
            try:
                limit = int(request.query.get("limit", 100))
                offset = int(request.query.get("offset", 0))
                backup_dir = os.path.join(self.storage_dir, "database-backups")
                if not os.path.exists(backup_dir):
                    return web.json_response(
                        {"backups": [], "total": 0, "limit": limit, "offset": offset},
                    )

                backups = []
                for file in os.listdir(backup_dir):
                    if file.endswith(".zip"):
                        full_path = os.path.join(backup_dir, file)
                        stats = os.stat(full_path)
                        backups.append(
                            {
                                "name": file,
                                "path": full_path,
                                "size": stats.st_size,
                                "created_at": datetime.fromtimestamp(
                                    stats.st_mtime,
                                    UTC,
                                ).isoformat(),
                            },
                        )
                sorted_backups = sorted(
                    backups,
                    key=lambda x: x["created_at"],
                    reverse=True,
                )
                total = len(sorted_backups)
                paginated_backups = sorted_backups[offset : offset + limit]
                return web.json_response(
                    {
                        "backups": paginated_backups,
                        "total": total,
                        "limit": limit,
                        "offset": offset,
                    },
                )
            except Exception as e:
                return web.json_response(
                    {"status": "error", "message": str(e)},
                    status=500,
                )

        @routes.delete("/api/v1/database/backups/{filename}")
        async def delete_db_backup(request):
            try:
                filename = request.match_info.get("filename")
                if not filename.endswith(".zip"):
                    filename += ".zip"
                self.database.delete_snapshot_or_backup(
                    self.storage_dir,
                    filename,
                    is_backup=True,
                )
                return web.json_response({"status": "success"})
            except Exception as e:
                return web.json_response(
                    {"status": "error", "message": str(e)},
                    status=500,
                )

        @routes.get("/api/v1/database/backups/{filename}/download")
        async def download_db_backup(request):
            try:
                filename = request.match_info.get("filename")
                if not filename.endswith(".zip"):
                    filename += ".zip"
                backup_dir = os.path.join(self.storage_dir, "database-backups")
                full_path = os.path.join(backup_dir, filename)

                if not os.path.exists(full_path) or not full_path.startswith(
                    backup_dir,
                ):
                    return web.json_response(
                        {"status": "error", "message": "Backup not found"},
                        status=404,
                    )

                return web.FileResponse(
                    path=full_path,
                    headers={
                        "Content-Disposition": f'attachment; filename="{filename}"',
                    },
                )
            except Exception as e:
                return web.json_response(
                    {"status": "error", "message": str(e)},
                    status=500,
                )

        @routes.get("/api/v1/database/snapshots/{filename}/download")
        async def download_db_snapshot(request):
            try:
                filename = request.match_info.get("filename")
                if not filename.endswith(".zip"):
                    filename += ".zip"
                snapshot_dir = os.path.join(self.storage_dir, "snapshots")
                full_path = os.path.join(snapshot_dir, filename)

                if not os.path.exists(full_path) or not full_path.startswith(
                    snapshot_dir,
                ):
                    return web.json_response(
                        {"status": "error", "message": "Snapshot not found"},
                        status=404,
                    )

                return web.FileResponse(
                    path=full_path,
                    headers={
                        "Content-Disposition": f'attachment; filename="{filename}"',
                    },
                )
            except Exception as e:
                return web.json_response(
                    {"status": "error", "message": str(e)},
                    status=500,
                )

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

        @routes.get("/api/v1/tools/rnode/download_firmware")
        async def tools_rnode_download_firmware(request):
            url = request.query.get("url")
            if not url:
                return web.json_response({"error": "URL is required"}, status=400)

            # Restrict to allowed sources for safety
            gitea_url = "https://git.quad4.io"
            if self.current_context and self.current_context.config:
                gitea_url = self.current_context.config.gitea_base_url.get()

            if (
                not url.startswith(gitea_url + "/")
                and not url.startswith("https://git.quad4.io/")
                and not url.startswith("https://github.com/")
                and not url.startswith("https://objects.githubusercontent.com/")
            ):
                return web.json_response({"error": "Invalid download URL"}, status=403)

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, allow_redirects=True) as response:
                        if response.status != 200:
                            return web.json_response(
                                {"error": f"Failed to download: {response.status}"},
                                status=response.status,
                            )

                        data = await response.read()
                        filename = url.split("/")[-1]

                        return web.Response(
                            body=data,
                            content_type="application/zip",
                            headers={
                                "Content-Disposition": f'attachment; filename="{filename}"',
                            },
                        )
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

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

        # fetch community interfaces
        @routes.get("/api/v1/community-interfaces")
        async def community_interfaces(request):
            interfaces = await self.community_interfaces_manager.get_interfaces()
            return web.json_response({"interfaces": interfaces})

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
                    "message": "Interface deleted",
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

            # handle RNodeInterface and RNodeIPInterface
            if interface_type in ("RNodeInterface", "RNodeIPInterface"):
                # map RNodeIPInterface to RNodeInterface for Reticulum config
                interface_details["type"] = "RNodeInterface"

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

            # interface discovery options
            for discovery_key in (
                "discoverable",
                "discovery_name",
                "announce_interval",
                "reachable_on",
                "discovery_stamp_value",
                "discovery_encrypt",
                "publish_ifac",
                "latitude",
                "longitude",
                "height",
                "discovery_frequency",
                "discovery_bandwidth",
                "discovery_modulation",
            ):
                InterfaceEditor.update_value(interface_details, data, discovery_key)

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
                        "message": "Interface has been saved",
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

        @routes.get("/ws/telephone/audio")
        async def telephone_audio_ws(request):
            websocket_response = web.WebSocketResponse(
                max_msg_size=5 * 1024 * 1024,
            )
            await websocket_response.prepare(request)

            # Early guard on config
            if not self.web_audio_bridge.config_enabled():
                await websocket_response.send_str(
                    json.dumps(
                        {"type": "error", "message": "Web audio is disabled in config"},
                    ),
                )
            else:
                await self.web_audio_bridge.send_status(websocket_response)
                attached = self.web_audio_bridge.attach_client(websocket_response)
                if not attached:
                    await websocket_response.send_str(
                        json.dumps(
                            {"type": "error", "message": "No active call to attach"},
                        ),
                    )

            async for msg in websocket_response:
                msg: WSMessage = msg
                if msg.type == WSMsgType.BINARY:
                    self.web_audio_bridge.push_client_frame(msg.data)
                elif msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        if data.get("type") == "attach":
                            self.web_audio_bridge.attach_client(websocket_response)
                        elif data.get("type") == "ping":
                            await websocket_response.send_str(
                                json.dumps({"type": "pong"}),
                            )
                    except Exception as e:
                        logging.exception(
                            f"Error processing websocket text message: {e}",
                        )
                elif msg.type == WSMsgType.ERROR:
                    print(f"telephone audio ws error {websocket_response.exception()}")

            self.web_audio_bridge.detach_client(websocket_response)
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
            total_paths = 0
            is_connected_to_shared_instance = False
            shared_instance_address = None
            if hasattr(self, "reticulum") and self.reticulum:
                try:
                    path_table = self.reticulum.get_path_table()
                    total_paths = len(path_table)
                except Exception:  # noqa: S110
                    pass

                is_connected_to_shared_instance = getattr(
                    self.reticulum,
                    "is_connected_to_shared_instance",
                    False,
                )

                if is_connected_to_shared_instance:
                    # Try to find the shared instance address from active connections
                    try:
                        for conn in process.connections(kind="all"):
                            if conn.status == psutil.CONN_ESTABLISHED and conn.raddr:
                                # Check for common Reticulum shared instance ports or UNIX sockets
                                if (
                                    isinstance(conn.raddr, tuple)
                                    and conn.raddr[1] == 37428
                                ):
                                    shared_instance_address = (
                                        f"{conn.raddr[0]}:{conn.raddr[1]}"
                                    )
                                    break
                                if (
                                    isinstance(conn.raddr, str)
                                    and (
                                        "rns" in conn.raddr or "reticulum" in conn.raddr
                                    )
                                    and ".sock" in conn.raddr
                                ):
                                    shared_instance_address = conn.raddr
                                    break
                    except Exception:  # noqa: S110
                        pass

                    # Fallback to reading config if not found via connections
                    if not shared_instance_address:
                        try:
                            config_dir = getattr(self, "reticulum_config_dir", None)
                            if not config_dir:
                                config_dir = getattr(
                                    RNS.Reticulum,
                                    "configdir",
                                    os.path.expanduser("~/.reticulum"),
                                )

                            config_path = os.path.join(config_dir, "config")
                            if os.path.isfile(config_path):
                                cp = configparser.ConfigParser()
                                cp.read(config_path)
                                if cp.has_section("reticulum"):
                                    shared_port = cp.getint(
                                        "reticulum",
                                        "shared_instance_port",
                                        fallback=37428,
                                    )
                                    shared_bind = cp.get(
                                        "reticulum",
                                        "shared_instance_bind",
                                        fallback="127.0.0.1",
                                    )
                                    shared_instance_address = (
                                        f"{shared_bind}:{shared_port}"
                                    )
                        except Exception:  # noqa: S110
                            pass

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

            db_files = self.database._get_database_file_stats()

            return web.json_response(
                {
                    "app_info": {
                        "version": self.get_app_version(),
                        "lxmf_version": LXMF.__version__,
                        "rns_version": RNS.__version__,
                        "lxst_version": self.get_lxst_version(),
                        "python_version": platform.python_version(),
                        "dependencies": {
                            "aiohttp": self.get_package_version("aiohttp"),
                            "aiohttp_session": self.get_package_version(
                                "aiohttp-session",
                            ),
                            "cryptography": self.get_package_version("cryptography"),
                            "psutil": self.get_package_version("psutil"),
                            "requests": self.get_package_version("requests"),
                            "websockets": self.get_package_version("websockets"),
                            "audioop_lts": (
                                self.get_package_version("audioop-lts")
                                if sys.version_info >= (3, 13)
                                else "n/a"
                            ),
                            "ply": self.get_package_version("ply"),
                            "bcrypt": self.get_package_version("bcrypt"),
                            "lxmfy": self.get_package_version("lxmfy"),
                        },
                        "storage_path": self.storage_path,
                        "database_path": self.database_path,
                        "database_file_size": db_files["main_bytes"],
                        "database_files": db_files,
                        "sqlite": {
                            "journal_mode": self.database._get_pragma_value(
                                "journal_mode",
                                "unknown",
                            ),
                            "synchronous": self.database._get_pragma_value(
                                "synchronous",
                                None,
                            ),
                            "wal_autocheckpoint": self.database._get_pragma_value(
                                "wal_autocheckpoint",
                                None,
                            ),
                            "busy_timeout": self.database._get_pragma_value(
                                "busy_timeout",
                                None,
                            ),
                        },
                        "reticulum_config_path": (
                            getattr(self.reticulum, "configpath", None)
                            if hasattr(self, "reticulum") and self.reticulum
                            else None
                        ),
                        "is_connected_to_shared_instance": is_connected_to_shared_instance,
                        "shared_instance_address": shared_instance_address,
                        "is_transport_enabled": (
                            self.reticulum.transport_enabled()
                            if hasattr(self, "reticulum") and self.reticulum
                            else False
                        ),
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
                        "is_reticulum_running": hasattr(self, "reticulum")
                        and self.reticulum is not None,
                        "download_stats": {
                            "avg_download_speed_bps": avg_download_speed_bps,
                        },
                        "emergency": getattr(self, "emergency", False),
                        "integrity_issues": getattr(self, "integrity_issues", []),
                        "user_guidance": self.build_user_guidance_messages(),
                        "tutorial_seen": self.config.get("tutorial_seen", "false")
                        == "true",
                        "changelog_seen_version": self.config.get(
                            "changelog_seen_version",
                            "0.0.0",
                        ),
                    },
                },
            )

        # get changelog
        @routes.get("/api/v1/app/changelog")
        async def app_changelog(request):
            changelog_path = get_file_path("CHANGELOG.md")
            if not os.path.exists(changelog_path):
                # try in public folder
                changelog_path = get_file_path("public/CHANGELOG.md")

            if not os.path.exists(changelog_path):
                # try project root if not found in package
                changelog_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    "CHANGELOG.md",
                )

            if not os.path.exists(changelog_path):
                return web.json_response({"error": "Changelog not found"}, status=404)

            try:
                with open(changelog_path) as f:
                    content = f.read()

                # Render markdown to HTML
                html_content = MarkdownRenderer.render(content)

                return web.json_response(
                    {
                        "changelog": content,
                        "html": html_content,
                        "version": app_version,
                    },
                )
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        # mark tutorial as seen
        @routes.post("/api/v1/app/tutorial/seen")
        async def app_tutorial_seen(request):
            self.config.set("tutorial_seen", True)
            return web.json_response({"message": "Tutorial marked as seen"})

        # acknowledge and reset integrity issues
        @routes.post("/api/v1/app/integrity/acknowledge")
        async def app_integrity_acknowledge(request):
            if self.current_context:
                self.current_context.integrity_manager.save_manifest()
            self.integrity_issues = []
            return web.json_response(
                {"message": "Integrity issues acknowledged and manifest reset"},
            )

        # mark changelog as seen
        @routes.post("/api/v1/app/changelog/seen")
        async def app_changelog_seen(request):
            data = await request.json()
            version = data.get("version")
            if not version:
                return web.json_response({"error": "Version required"}, status=400)

            self.config.set("changelog_seen_version", version)
            return web.json_response(
                {"message": f"Changelog version {version} marked as seen"},
            )

        # shutdown app
        @routes.post("/api/v1/app/shutdown")
        async def app_shutdown(request):
            # perform shutdown in a separate task so we can respond to the request
            async def do_shutdown():
                await asyncio.sleep(0.5)  # give some time for the response to be sent
                await self.shutdown(None)
                self.exit_app(0)

            asyncio.create_task(do_shutdown())
            return web.json_response({"message": "Shutting down..."})

        # get docs status
        @routes.get("/api/v1/docs/status")
        async def docs_status(request):
            return web.json_response(self.docs_manager.get_status())

        # update docs
        @routes.post("/api/v1/docs/update")
        async def docs_update(request):
            version = request.query.get("version", "latest")
            success = self.docs_manager.update_docs(version=version)
            return web.json_response({"success": success})

        # upload docs zip
        @routes.post("/api/v1/docs/upload")
        async def docs_upload(request):
            try:
                reader = await request.multipart()
                field = await reader.next()
                if field.name != "file":
                    return web.json_response(
                        {"error": "No file field in multipart request"},
                        status=400,
                    )

                version = request.query.get("version")
                if not version:
                    # use timestamp if no version provided
                    version = f"upload-{int(time.time())}"

                zip_data = await field.read()
                success = self.docs_manager.upload_zip(zip_data, version)
                return web.json_response({"success": success, "version": version})
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        # switch docs version
        @routes.post("/api/v1/docs/switch")
        async def docs_switch(request):
            try:
                data = await request.json()
                version = data.get("version")
                if not version:
                    return web.json_response(
                        {"error": "No version provided"},
                        status=400,
                    )

                success = self.docs_manager.switch_version(version)
                return web.json_response({"success": success})
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        # delete docs version
        @routes.delete("/api/v1/docs/version/{version}")
        async def docs_delete_version(request):
            try:
                version = request.match_info.get("version")
                if not version:
                    return web.json_response(
                        {"error": "No version provided"},
                        status=400,
                    )

                success = self.docs_manager.delete_version(version)
                return web.json_response({"success": success})
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        # clear reticulum docs
        @routes.delete("/api/v1/maintenance/docs/reticulum")
        async def docs_clear(request):
            try:
                success = self.docs_manager.clear_reticulum_docs()
                return web.json_response({"success": success})
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        # search docs
        @routes.get("/api/v1/docs/search")
        async def docs_search(request):
            query = request.query.get("q", "")
            lang = request.query.get("lang", "en")
            results = self.docs_manager.search(query, lang)
            return web.json_response({"results": results})

        # get meshchatx docs list
        @routes.get("/api/v1/meshchatx-docs/list")
        async def meshchatx_docs_list(request):
            return web.json_response(self.docs_manager.get_meshchatx_docs_list())

        # get meshchatx doc content
        @routes.get("/api/v1/meshchatx-docs/content")
        async def meshchatx_doc_content(request):
            path = request.query.get("path")
            if not path:
                return web.json_response({"error": "No path provided"}, status=400)

            content = self.docs_manager.get_doc_content(path)
            if not content:
                return web.json_response({"error": "Document not found"}, status=404)

            return web.json_response(content)

        # export docs
        @routes.get("/api/v1/docs/export")
        async def docs_export(request):
            try:
                zip_data = self.docs_manager.export_docs()
                filename = (
                    f"meshchatx_docs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                )
                return web.Response(
                    body=zip_data,
                    content_type="application/zip",
                    headers={
                        "Content-Disposition": f'attachment; filename="{filename}"',
                    },
                )
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        @routes.get("/api/v1/database/health")
        async def database_health(request):
            try:
                return web.json_response(
                    {
                        "database": self.database.get_database_health_snapshot(),
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
                result = self.database.run_database_vacuum()
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
                result = self.database.run_database_recovery()
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
                result = self.database.backup_database(self.storage_path)
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
                backup_info = self.database.backup_database(self.storage_path)
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

                result = self.database.restore_database(temp_path)
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
                keep_alive = data.get("keep_alive", False)

                # attempt hotswap first
                success = await self.hotswap_identity(
                    identity_hash,
                    keep_alive=keep_alive,
                )

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
                    self.storage_dir,
                    "identity",
                )
                identity_dir = os.path.join(
                    self.storage_dir,
                    "identities",
                    identity_hash,
                )
                identity_file = os.path.join(identity_dir, "identity")

                shutil.copy2(identity_file, main_identity_file)

                def restart():
                    time.sleep(1)
                    try:
                        os.execv(sys.executable, [sys.executable] + sys.argv)  # noqa: S606
                    except Exception as e:
                        print(f"Failed to restart: {e}")
                        os._exit(0)

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

        # maintenance - clear messages
        @routes.delete("/api/v1/maintenance/messages")
        async def maintenance_clear_messages(request):
            self.database.messages.delete_all_lxmf_messages()
            return web.json_response({"message": "All messages cleared"})

        # maintenance - clear announces
        @routes.delete("/api/v1/maintenance/announces")
        async def maintenance_clear_announces(request):
            aspect = request.query.get("aspect")
            self.database.announces.delete_all_announces(aspect=aspect)
            return web.json_response(
                {
                    "message": f"Announces cleared{' for aspect ' + aspect if aspect else ''}",
                },
            )

        # maintenance - clear favorites
        @routes.delete("/api/v1/maintenance/favourites")
        async def maintenance_clear_favourites(request):
            aspect = request.query.get("aspect")
            self.database.announces.delete_all_favourites(aspect=aspect)
            return web.json_response(
                {
                    "message": f"Favourites cleared{' for aspect ' + aspect if aspect else ''}",
                },
            )

        # maintenance - clear archives
        @routes.delete("/api/v1/maintenance/archives")
        async def maintenance_clear_archives(request):
            self.database.misc.delete_archived_pages()
            return web.json_response({"message": "All archived pages cleared"})

        # maintenance - clear LXMF icons
        @routes.delete("/api/v1/maintenance/lxmf-icons")
        async def maintenance_clear_lxmf_icons(request):
            self.database.misc.delete_all_user_icons()
            return web.json_response({"message": "All LXMF icons cleared"})

        # maintenance - export messages
        @routes.get("/api/v1/maintenance/messages/export")
        async def maintenance_export_messages(request):
            messages = self.database.messages.get_all_lxmf_messages()
            # Convert sqlite3.Row to dict if necessary
            messages_list = [dict(m) for m in messages]
            return web.json_response({"messages": messages_list})

        # maintenance - import messages
        @routes.post("/api/v1/maintenance/messages/import")
        async def maintenance_import_messages(request):
            try:
                data = await request.json()
                messages = data.get("messages", [])
                for msg in messages:
                    self.database.messages.upsert_lxmf_message(msg)
                return web.json_response(
                    {"message": f"Successfully imported {len(messages)} messages"},
                )
            except Exception as e:
                return web.json_response({"error": str(e)}, status=400)

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
            try:
                data = await request.json()
                await self.update_config(data)
                try:
                    AsyncUtils.run_async(self.send_config_to_websocket_clients())
                except Exception as e:
                    print(f"Failed to broadcast config update: {e}")

                return web.json_response(
                    {
                        "config": self.get_config_dict(),
                    },
                )
            except Exception:
                import traceback

                print("config_update failed:\n" + traceback.format_exc())
                return web.json_response({"error": "config_update_failed"}, status=500)

        # get or update reticulum discovery configuration
        @routes.get("/api/v1/reticulum/discovery")
        async def reticulum_discovery_get(request):
            reticulum_config = self._get_reticulum_section()
            discovery_config = {
                "discover_interfaces": reticulum_config.get("discover_interfaces"),
                "interface_discovery_sources": reticulum_config.get(
                    "interface_discovery_sources",
                ),
                "required_discovery_value": reticulum_config.get(
                    "required_discovery_value",
                ),
                "autoconnect_discovered_interfaces": reticulum_config.get(
                    "autoconnect_discovered_interfaces",
                ),
                "network_identity": reticulum_config.get("network_identity"),
            }

            return web.json_response({"discovery": discovery_config})

        @routes.patch("/api/v1/reticulum/discovery")
        async def reticulum_discovery_patch(request):
            try:
                data = await request.json()
            except Exception:
                return web.json_response(
                    {"message": "Invalid request body"},
                    status=400,
                )

            reticulum_config = self._get_reticulum_section()

            def update_config_value(key):
                if key not in data:
                    return
                value = data.get(key)
                if value is None or value == "":
                    reticulum_config.pop(key, None)
                else:
                    reticulum_config[key] = value

            for key in (
                "discover_interfaces",
                "interface_discovery_sources",
                "required_discovery_value",
                "autoconnect_discovered_interfaces",
                "network_identity",
            ):
                update_config_value(key)

            if not self._write_reticulum_config():
                return web.json_response(
                    {"message": "Failed to write Reticulum config"},
                    status=500,
                )

            discovery_config = {
                "discover_interfaces": reticulum_config.get("discover_interfaces"),
                "interface_discovery_sources": reticulum_config.get(
                    "interface_discovery_sources",
                ),
                "required_discovery_value": reticulum_config.get(
                    "required_discovery_value",
                ),
                "autoconnect_discovered_interfaces": reticulum_config.get(
                    "autoconnect_discovered_interfaces",
                ),
                "network_identity": reticulum_config.get("network_identity"),
            }

            return web.json_response({"discovery": discovery_config})

        @routes.get("/api/v1/reticulum/discovered-interfaces")
        async def reticulum_discovered_interfaces(request):
            try:
                discovery = InterfaceDiscovery(discover_interfaces=False)
                interfaces = discovery.list_discovered_interfaces()
                active = []
                try:
                    if hasattr(self, "reticulum") and self.reticulum:
                        stats = self.reticulum.get_interface_stats().get(
                            "interfaces",
                            [],
                        )
                        active = []
                        for s in stats:
                            name = s.get("name") or ""
                            parsed_host = None
                            parsed_port = None
                            if "/" in name:
                                try:
                                    host_port = name.split("/")[-1].strip("[]")
                                    if ":" in host_port:
                                        parsed_host, parsed_port = host_port.rsplit(
                                            ":",
                                            1,
                                        )
                                        try:
                                            parsed_port = int(parsed_port)
                                        except Exception:
                                            parsed_port = None
                                    else:
                                        parsed_host = host_port
                                except Exception:
                                    parsed_host = None
                                    parsed_port = None

                            host = (
                                s.get("target_host") or s.get("remote") or parsed_host
                            )
                            port = (
                                s.get("target_port")
                                or s.get("listen_port")
                                or parsed_port
                            )
                            transport_id = s.get("transport_id")
                            if isinstance(transport_id, (bytes, bytearray)):
                                transport_id = transport_id.hex()

                            active.append(
                                {
                                    "name": name,
                                    "short_name": s.get("short_name"),
                                    "type": s.get("type"),
                                    "target_host": host,
                                    "target_port": port,
                                    "listen_ip": s.get("listen_ip"),
                                    "connected": s.get("connected"),
                                    "online": s.get("online"),
                                    "transport_id": transport_id,
                                    "network_id": s.get("network_id"),
                                },
                            )
                except Exception as e:
                    logger.debug(f"Failed to get interface stats: {e}")

                def to_jsonable(obj):
                    if isinstance(obj, bytes):
                        return obj.hex()
                    if isinstance(obj, dict):
                        return {k: to_jsonable(v) for k, v in obj.items()}
                    if isinstance(obj, list):
                        return [to_jsonable(v) for v in obj]
                    return obj

                return web.json_response(
                    {
                        "interfaces": to_jsonable(interfaces),
                        "active": to_jsonable(active),
                    },
                )
            except Exception as e:
                return web.json_response(
                    {"message": f"Failed to load discovered interfaces: {e!s}"},
                    status=500,
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

        @routes.post("/api/v1/reticulum/reload")
        async def reticulum_reload(request):
            success = await self.reload_reticulum()
            if success:
                return web.json_response({"message": "Reticulum reloaded successfully"})
            return web.json_response(
                {"error": "Failed to reload Reticulum"},
                status=500,
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
                        remote_identity = telephone_active_call.get_remote_identity()
                        if remote_identity:
                            caller_hash = remote_identity.hash.hex()
                            contact = (
                                self.database.contacts.get_contact_by_identity_hash(
                                    caller_hash,
                                )
                            )
                            if not contact:
                                # Don't report active call if contacts-only is on and caller is not a contact
                                telephone_active_call = None
                        else:
                            # Don't report active call if we cannot identify the caller
                            telephone_active_call = None

            if telephone_active_call is not None:
                remote_identity = telephone_active_call.get_remote_identity()
                if remote_identity is None:
                    telephone_active_call = None

            if telephone_active_call is not None:
                # remote_identity is already fetched and checked for None above
                remote_hash = remote_identity.hash.hex()
                remote_destination_hash = RNS.Destination.hash(
                    remote_identity,
                    "lxmf",
                    "delivery",
                ).hex()
                remote_telephony_hash = self.get_lxst_telephony_hash_for_identity_hash(
                    remote_hash,
                )
                remote_name = None
                if self.telephone_manager.get_name_for_identity_hash:
                    remote_name = self.telephone_manager.get_name_for_identity_hash(
                        remote_hash,
                    )

                # get lxmf destination hash to look up icon
                lxmf_destination_hash = RNS.Destination.hash(
                    remote_identity,
                    "lxmf",
                    "delivery",
                ).hex()

                remote_icon = self.database.misc.get_user_icon(lxmf_destination_hash)

                # Check if contact and get custom image
                contact = self.database.contacts.get_contact_by_identity_hash(
                    remote_hash,
                )
                custom_image = contact["custom_image"] if contact else None

                active_call = {
                    "hash": telephone_active_call.hash.hex(),
                    "remote_identity_hash": remote_hash,
                    "remote_destination_hash": remote_destination_hash,
                    "remote_identity_name": remote_name,
                    "remote_icon": dict(remote_icon) if remote_icon else None,
                    "custom_image": custom_image,
                    "is_incoming": telephone_active_call.is_incoming,
                    "status": self.telephone_manager.telephone.call_status,
                    "remote_telephony_hash": remote_telephony_hash,
                    "audio_profile_id": self.telephone_manager.telephone.transmit_codec.profile
                    if hasattr(
                        self.telephone_manager.telephone.transmit_codec,
                        "profile",
                    )
                    else None,
                    "is_recording": self.telephone_manager.is_recording,
                    "is_voicemail": self.voicemail_manager.is_recording,
                    "call_start_time": self.telephone_manager.call_start_time,
                    "is_contact": contact is not None,
                    "tx_bytes": 0,
                    "rx_bytes": 0,
                    "tx_packets": 0,
                    "rx_packets": 0,
                }
                link = getattr(self.telephone_manager, "call_stats", {}).get("link")
                if link:
                    active_call["tx_bytes"] = getattr(link, "txbytes", 0)
                    active_call["rx_bytes"] = getattr(link, "rxbytes", 0)
                    active_call["tx_packets"] = getattr(link, "tx", 0)
                    active_call["rx_packets"] = getattr(link, "rx", 0)

            initiation_target_hash = self.telephone_manager.initiation_target_hash
            initiation_target_name = None
            if initiation_target_hash:
                try:
                    contact = self.database.contacts.get_contact_by_identity_hash(
                        initiation_target_hash,
                    )
                    if contact:
                        initiation_target_name = contact.name
                except Exception:  # noqa: S110
                    pass

            return web.json_response(
                {
                    "enabled": True,
                    "is_busy": self.telephone_manager.telephone.busy,
                    "call_status": self.telephone_manager.telephone.call_status,
                    "active_call": active_call,
                    "is_mic_muted": self.telephone_manager.transmit_muted,
                    "is_speaker_muted": self.telephone_manager.receive_muted,
                    "voicemail": {
                        "is_recording": self.voicemail_manager.is_recording,
                        "unread_count": self.database.voicemails.get_unread_count(),
                        "latest_id": self.database.voicemails.get_latest_voicemail_id(),
                    },
                    "initiation_status": self.telephone_manager.initiation_status,
                    "initiation_target_hash": initiation_target_hash,
                    "initiation_target_name": initiation_target_name,
                    "web_audio": {
                        "enabled": getattr(
                            self.config.telephone_web_audio_enabled,
                            "get",
                            lambda: False,
                        )(),
                        "allow_fallback": getattr(
                            self.config.telephone_web_audio_allow_fallback,
                            "get",
                            lambda: True,
                        )(),
                        "has_client": bool(
                            getattr(self.web_audio_bridge, "clients", []),
                        ),
                        "frame_ms": getattr(
                            self.telephone_manager.telephone,
                            "target_frame_time_ms",
                            None,
                        ),
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
            if not caller_identity:
                return web.json_response(
                    {"message": "Caller identity not found"},
                    status=404,
                )

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
            await asyncio.to_thread(self.telephone_manager.hangup)

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
            await asyncio.to_thread(self.telephone_manager.mute_transmit)
            return web.json_response({"message": "Microphone muted"})

        @routes.get("/api/v1/telephone/unmute-transmit")
        async def telephone_unmute_transmit(request):
            await asyncio.to_thread(self.telephone_manager.unmute_transmit)
            return web.json_response({"message": "Microphone unmuted"})

        # mute/unmute receive
        @routes.get("/api/v1/telephone/mute-receive")
        async def telephone_mute_receive(request):
            await asyncio.to_thread(self.telephone_manager.mute_receive)
            return web.json_response({"message": "Speaker muted"})

        @routes.get("/api/v1/telephone/unmute-receive")
        async def telephone_unmute_receive(request):
            await asyncio.to_thread(self.telephone_manager.unmute_receive)
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
                    # try to resolve name if unknown or missing
                    if (
                        not d.get("remote_identity_name")
                        or d.get("remote_identity_name") == "Unknown"
                    ):
                        resolved_name = self.get_name_for_identity_hash(
                            remote_identity_hash,
                        )
                        if resolved_name:
                            d["remote_identity_name"] = resolved_name

                    lxmf_hash = self.get_lxmf_destination_hash_for_identity_hash(
                        remote_identity_hash,
                    )
                    tele_hash = self.get_lxst_telephony_hash_for_identity_hash(
                        remote_identity_hash,
                    )
                    if lxmf_hash:
                        d["remote_destination_hash"] = lxmf_hash
                        icon = self.database.misc.get_user_icon(lxmf_hash)
                        if icon:
                            d["remote_icon"] = dict(icon)
                    if tele_hash:
                        d["remote_telephony_hash"] = tele_hash

                    contact = self.database.contacts.get_contact_by_identity_hash(
                        remote_identity_hash,
                    )
                    d["is_contact"] = contact is not None
                    if contact:
                        d["contact_image"] = contact.get("custom_image")
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
                if self.telephone_manager.telephone is None:
                    return web.json_response(
                        {"message": "Telephone not initialized"},
                        status=400,
                    )

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
        # initiate outgoing telephone call
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

            # check if busy, but ignore stale busy when no active call
            is_busy = self.telephone_manager.telephone.busy
            if is_busy and not self.telephone_manager.telephone.active_call:
                # If there's no active call and we're not currently initiating,
                # we shouldn't be busy.
                if not self.telephone_manager.initiation_status:
                    is_busy = False

            if is_busy or self.telephone_manager.initiation_status:
                return web.json_response(
                    {
                        "message": "Telephone is busy",
                    },
                    status=400,
                )

            # get path params
            identity_hash_hex = request.match_info.get("identity_hash", "")
            timeout_seconds = int(request.query.get("timeout", 15))

            try:
                # convert hash to bytes
                identity_hash_bytes = bytes.fromhex(identity_hash_hex)
            except Exception:
                return web.json_response(
                    {
                        "message": "Invalid identity hash",
                    },
                    status=400,
                )

            # initiate call in background to be non-blocking for the UI
            async def _initiate():
                try:
                    await self.telephone_manager.initiate(
                        identity_hash_bytes,
                        timeout_seconds=timeout_seconds,
                    )
                except Exception as e:
                    print(f"Failed to initiate call to {identity_hash_hex}: {e}")

            asyncio.create_task(_initiate())

            return web.json_response(
                {
                    "message": "Call initiation started",
                },
            )

        # serve list of available audio profiles
        @routes.get("/api/v1/telephone/audio-profiles")
        async def telephone_audio_profiles(request):
            from LXST.Primitives.Telephony import Profiles

            # get audio profiles
            audio_profiles = [
                {
                    "id": available_profile,
                    "name": Profiles.profile_name(available_profile),
                }
                for available_profile in Profiles.available_profiles()
            ]

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
                        remote_identity_hash,
                    )
                    tele_hash = self.get_lxst_telephony_hash_for_identity_hash(
                        remote_identity_hash,
                    )
                    if lxmf_hash:
                        d["remote_destination_hash"] = lxmf_hash
                        icon = self.database.misc.get_user_icon(lxmf_hash)
                        if icon:
                            d["remote_icon"] = dict(icon)
                    if tele_hash:
                        d["remote_telephony_hash"] = tele_hash
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
                return web.FileResponse(
                    filepath,
                    headers={"Content-Type": "audio/opus"},
                )
            return web.json_response(
                {"message": "Greeting audio not found"},
                status=404,
            )

        # serve voicemail audio
        @routes.get("/api/v1/telephone/voicemails/{id}/audio")
        async def telephone_voicemail_audio(request):
            voicemail_id = request.match_info.get("id")
            try:
                voicemail_id = int(voicemail_id)
            except (ValueError, TypeError):
                return web.json_response(
                    {"message": "Invalid voicemail ID"},
                    status=400,
                )

            if not self.voicemail_manager:
                return web.json_response(
                    {"message": "Voicemail manager not available"},
                    status=503,
                )

            voicemail = self.database.voicemails.get_voicemail(voicemail_id)
            if voicemail:
                filepath = os.path.join(
                    self.voicemail_manager.recordings_dir,
                    voicemail["filename"],
                )
                if os.path.exists(filepath):
                    # Browsers might need a proper content type for .opus files
                    return web.FileResponse(
                        filepath,
                        headers={"Content-Type": "audio/opus"},
                    )
                RNS.log(
                    f"Voicemail: Recording file missing for ID {voicemail_id}: {filepath}",
                    RNS.LOG_ERROR,
                )
            return web.json_response(
                {"message": "Voicemail audio not found"},
                status=404,
            )

        # list call recordings
        @routes.get("/api/v1/telephone/recordings")
        async def telephone_recordings(request):
            search = request.query.get("search", None)
            limit = int(request.query.get("limit", 10))
            offset = int(request.query.get("offset", 0))
            recordings_rows = self.database.telephone.get_call_recordings(
                search=search,
                limit=limit,
                offset=offset,
            )
            recordings = []
            for row in recordings_rows:
                d = dict(row)
                remote_identity_hash = d.get("remote_identity_hash")
                if remote_identity_hash:
                    lxmf_hash = self.get_lxmf_destination_hash_for_identity_hash(
                        remote_identity_hash,
                    )
                    if lxmf_hash:
                        icon = self.database.misc.get_user_icon(lxmf_hash)
                        if icon:
                            d["remote_icon"] = dict(icon)
                recordings.append(d)

            return web.json_response({"recordings": recordings})

        # serve call recording audio
        @routes.get("/api/v1/telephone/recordings/{id}/audio/{side}")
        async def telephone_recording_audio(request):
            recording_id = request.match_info.get("id")
            try:
                recording_id = int(recording_id)
            except (ValueError, TypeError):
                return web.json_response(
                    {"message": "Invalid recording ID"},
                    status=400,
                )

            side = request.match_info.get("side")  # rx or tx
            recording = self.database.telephone.get_call_recording(recording_id)
            if recording:
                filename = recording[f"filename_{side}"]
                if not filename:
                    return web.json_response(
                        {"message": f"No {side} recording found"},
                        status=404,
                    )

                filepath = os.path.join(
                    self.telephone_manager.recordings_dir,
                    filename,
                )
                if os.path.exists(filepath):
                    return web.FileResponse(
                        filepath,
                        headers={"Content-Type": "audio/opus"},
                    )

            return web.json_response({"message": "Recording not found"}, status=404)

        # delete call recording
        @routes.delete("/api/v1/telephone/recordings/{id}")
        async def telephone_recording_delete(request):
            recording_id = request.match_info.get("id")
            recording = self.database.telephone.get_call_recording(recording_id)
            if recording:
                for side in ["rx", "tx"]:
                    filename = recording[f"filename_{side}"]
                    if filename:
                        filepath = os.path.join(
                            self.telephone_manager.recordings_dir,
                            filename,
                        )
                        if os.path.exists(filepath):
                            os.remove(filepath)
                self.database.telephone.delete_call_recording(recording_id)
            return web.json_response({"message": "ok"})

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
            try:
                caller_hash = request.query.get("caller_hash")

                ringtone_id = None

                # 1. check contact preferred ringtone
                if caller_hash:
                    contact = self.database.contacts.get_contact_by_identity_hash(
                        caller_hash,
                    )
                    if contact and contact.get("preferred_ringtone_id"):
                        ringtone_id = contact["preferred_ringtone_id"]

                # 2. check global preferred for non-contacts
                if ringtone_id is None:
                    preferred_id = self.config.ringtone_preferred_id.get()
                    if preferred_id:
                        ringtone_id = preferred_id

                # 3. fallback to primary
                if ringtone_id is None:
                    primary = self.database.ringtones.get_primary()
                    if primary:
                        ringtone_id = primary["id"]

                # 4. handle random if selected (-1)
                if ringtone_id == -1:
                    import random

                    ringtones = self.database.ringtones.get_all()
                    if ringtones:
                        ringtone_id = random.choice(ringtones)["id"]  # noqa: S311
                    else:
                        ringtone_id = None

                has_custom = ringtone_id is not None
                ringtone = (
                    self.database.ringtones.get_by_id(ringtone_id)
                    if has_custom
                    else None
                )

                return web.json_response(
                    {
                        "has_custom_ringtone": has_custom and ringtone is not None,
                        "enabled": self.config.custom_ringtone_enabled.get(),
                        "filename": ringtone["filename"] if ringtone else None,
                        "id": ringtone_id if ringtone_id != -1 else None,
                        "volume": self.config.ringtone_volume.get() / 100.0,
                    },
                )
            except Exception as e:
                logger.error(f"Error in telephone_ringtone_status: {e}")
                return web.json_response(
                    {
                        "has_custom_ringtone": False,
                        "enabled": self.config.custom_ringtone_enabled.get(),
                        "filename": None,
                        "id": None,
                        "volume": self.config.ringtone_volume.get() / 100.0,
                    },
                )

        @routes.get("/api/v1/telephone/ringtones/{id}/audio")
        async def telephone_ringtone_audio(request):
            ringtone_id = int(request.match_info["id"])
            ringtone = self.database.ringtones.get_by_id(ringtone_id)
            if not ringtone:
                return web.json_response({"message": "Ringtone not found"}, status=404)

            download = request.query.get("download") == "1"

            filepath = self.ringtone_manager.get_ringtone_path(
                ringtone["storage_filename"],
            )
            if os.path.exists(filepath):
                if download:
                    return web.FileResponse(
                        filepath,
                        headers={
                            "Content-Disposition": f'attachment; filename="{ringtone["filename"]}"',
                        },
                    )
                return web.FileResponse(filepath)
            return web.json_response(
                {"message": "Ringtone audio file not found"},
                status=404,
            )

        @routes.post("/api/v1/telephone/ringtones/upload")
        async def telephone_ringtone_upload(request):
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
                        remote_identity_hash,
                    )
                    tele_hash = self.get_lxst_telephony_hash_for_identity_hash(
                        remote_identity_hash,
                    )
                    if lxmf_hash:
                        d["remote_destination_hash"] = lxmf_hash
                        icon = self.database.misc.get_user_icon(lxmf_hash)
                        if icon:
                            d["remote_icon"] = dict(icon)
                    if tele_hash:
                        d["remote_telephony_hash"] = tele_hash
                contacts.append(d)

            return web.json_response(contacts)

        @routes.post("/api/v1/telephone/contacts")
        async def telephone_contacts_post(request):
            data = await request.json()
            name = data.get("name")
            remote_identity_hash = data.get("remote_identity_hash")
            lxmf_address = data.get("lxmf_address")
            lxst_address = data.get("lxst_address")
            preferred_ringtone_id = data.get("preferred_ringtone_id")
            custom_image = data.get("custom_image")
            is_telemetry_trusted = data.get("is_telemetry_trusted", 0)

            if not name:
                return web.json_response(
                    {"message": "Name is required"},
                    status=400,
                )

            if not remote_identity_hash:
                # Try to derive identity from LXMF or LXST address
                lookup_hash = lxmf_address or lxst_address
                if lookup_hash:
                    announce = self.database.announces.get_announce_by_hash(lookup_hash)
                    if announce:
                        remote_identity_hash = announce.get("identity_hash")
                    else:
                        # try to recall identity from RNS
                        ident = self.recall_identity(lookup_hash)
                        if ident:
                            remote_identity_hash = ident.hash.hex()

            if not remote_identity_hash:
                return web.json_response(
                    {"message": "Identity hash is required or could not be derived"},
                    status=400,
                )

            self.database.contacts.add_contact(
                name,
                remote_identity_hash,
                lxmf_address=lxmf_address,
                lxst_address=lxst_address,
                preferred_ringtone_id=preferred_ringtone_id,
                custom_image=custom_image,
                is_telemetry_trusted=is_telemetry_trusted,
            )
            return web.json_response({"message": "Contact added"})

        @routes.patch("/api/v1/telephone/contacts/{id}")
        async def telephone_contacts_patch(request):
            contact_id = int(request.match_info["id"])
            data = await request.json()
            name = data.get("name")
            remote_identity_hash = data.get("remote_identity_hash")
            lxmf_address = data.get("lxmf_address")
            lxst_address = data.get("lxst_address")
            preferred_ringtone_id = data.get("preferred_ringtone_id")
            custom_image = data.get("custom_image")
            clear_image = data.get("clear_image", False)
            is_telemetry_trusted = data.get("is_telemetry_trusted")

            self.database.contacts.update_contact(
                contact_id,
                name=name,
                remote_identity_hash=remote_identity_hash,
                lxmf_address=lxmf_address,
                lxst_address=lxst_address,
                preferred_ringtone_id=preferred_ringtone_id,
                custom_image=custom_image,
                clear_image=clear_image,
                is_telemetry_trusted=is_telemetry_trusted,
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
                },
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

            try:
                limit = request.query.get("limit")
                limit = int(limit) if limit is not None else None
            except ValueError:
                limit = None

            try:
                offset = request.query.get("offset")
                offset = int(offset) if offset is not None else 0
            except ValueError:
                offset = 0

            include_blocked = (
                request.query.get("include_blocked", "false").lower() == "true"
            )

            blocked_identity_hashes = None
            if not include_blocked:
                blocked = self.database.misc.get_blocked_destinations()
                blocked_identity_hashes = [b["destination_hash"] for b in blocked]

            # fetch announces from database
            # If we don't have a search query, we can paginate at the database level
            # which is much faster than fetching thousands of records and then paginating in Python.
            db_limit = limit if not search_query else None
            db_offset = offset if not search_query else 0

            results = self.announce_manager.get_filtered_announces(
                aspect=aspect,
                identity_hash=identity_hash,
                destination_hash=destination_hash,
                query=None,  # We filter in Python to support name search
                blocked_identity_hashes=blocked_identity_hashes,
                limit=db_limit,
                offset=db_offset,
            )

            # fetch total count if we paginated in DB
            total_count = 0
            if not search_query:
                # Get the count from the database for the same filters
                # We should probably add a get_filtered_announces_count method to announce_manager
                if db_limit is None:
                    total_count = len(results)
                else:
                    # We need the total count for pagination to work in the frontend
                    total_count = self.announce_manager.get_filtered_announces_count(
                        aspect=aspect,
                        identity_hash=identity_hash,
                        destination_hash=destination_hash,
                        query=None,
                        blocked_identity_hashes=blocked_identity_hashes,
                    )

            # ... rest of processing ...

            # pre-fetch icons and other data to avoid N+1 queries in convert_db_announce_to_dict
            other_user_hashes = [r["destination_hash"] for r in results]
            user_icons = {}
            if other_user_hashes:
                db_icons = self.database.misc.get_user_icons(other_user_hashes)
                for icon in db_icons:
                    user_icons[icon["destination_hash"]] = {
                        "icon_name": icon["icon_name"],
                        "foreground_colour": icon["foreground_colour"],
                        "background_colour": icon["background_colour"],
                    }

            # fetch custom display names
            custom_names = {}
            lxmf_names_for_telephony = {}
            if other_user_hashes:
                db_custom_names = self.database.provider.fetchall(
                    f"SELECT destination_hash, display_name FROM custom_destination_display_names WHERE destination_hash IN ({','.join(['?'] * len(other_user_hashes))})",  # noqa: S608
                    other_user_hashes,
                )
                for row in db_custom_names:
                    custom_names[row["destination_hash"]] = row["display_name"]

                # If we're looking for telephony announces, pre-fetch LXMF announces for the same identities
                if aspect == "lxst.telephony":
                    identity_hashes = list(
                        set(
                            [
                                r["identity_hash"]
                                for r in results
                                if r.get("identity_hash")
                            ],
                        ),
                    )
                    if identity_hashes:
                        lxmf_results = self.database.announces.provider.fetchall(
                            f"SELECT identity_hash, app_data FROM announces WHERE aspect = 'lxmf.delivery' AND identity_hash IN ({','.join(['?'] * len(identity_hashes))})",  # noqa: S608
                            identity_hashes,
                        )
                        for row in lxmf_results:
                            lxmf_names_for_telephony[row["identity_hash"]] = (
                                parse_lxmf_display_name(row["app_data"])
                            )

            # process all announces
            all_announces = []
            for announce in results:
                # Optimized convert_db_announce_to_dict logic inline to use pre-fetched data
                if not isinstance(announce, dict):
                    announce = dict(announce)

                # parse display name from announce
                display_name = None
                is_local = (
                    self.current_context
                    and announce["identity_hash"] == self.current_context.identity_hash
                )

                if announce["aspect"] == "lxmf.delivery":
                    display_name = parse_lxmf_display_name(announce["app_data"])
                elif announce["aspect"] == "nomadnetwork.node":
                    display_name = parse_nomadnetwork_node_display_name(
                        announce["app_data"],
                    )
                elif announce["aspect"] == "lxst.telephony":
                    display_name = parse_lxmf_display_name(announce["app_data"])
                    if not display_name or display_name == "Anonymous Peer":
                        # Try pre-fetched LXMF name
                        display_name = lxmf_names_for_telephony.get(
                            announce["identity_hash"],
                        )

                if not display_name or display_name == "Anonymous Peer":
                    if is_local and self.current_context:
                        display_name = self.current_context.config.display_name.get()
                    else:
                        # try to resolve name from identity hash (checks contacts too)
                        display_name = (
                            self.get_name_for_identity_hash(announce["identity_hash"])
                            or "Anonymous Peer"
                        )

                # get current hops away
                hops = RNS.Transport.hops_to(
                    bytes.fromhex(announce["destination_hash"]),
                )

                # ensure created_at and updated_at have Z suffix
                created_at = str(announce["created_at"])
                if created_at and "+" not in created_at and "Z" not in created_at:
                    created_at += "Z"
                updated_at = str(announce["updated_at"])
                if updated_at and "+" not in updated_at and "Z" not in updated_at:
                    updated_at += "Z"

                all_announces.append(
                    {
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
                        "created_at": created_at,
                        "updated_at": updated_at,
                        "display_name": display_name,
                        "custom_display_name": custom_names.get(
                            announce["destination_hash"],
                        ),
                        "lxmf_user_icon": user_icons.get(announce["destination_hash"]),
                        "contact_image": announce.get("contact_image"),
                    },
                )

            # apply search query filter if provided
            if search_query:
                q = search_query.lower()
                all_announces = [
                    a
                    for a in all_announces
                    if (
                        (a.get("display_name") and q in a["display_name"].lower())
                        or (
                            a.get("destination_hash")
                            and q in a["destination_hash"].lower()
                        )
                        or (a.get("identity_hash") and q in a["identity_hash"].lower())
                        or (
                            a.get("custom_display_name")
                            and q in a["custom_display_name"].lower()
                        )
                    )
                ]

                # Re-calculate total_count after search filter
                total_count = len(all_announces)
                # apply pagination after search
                start = offset
                end = start + (limit if limit is not None else total_count)
                paginated_results = all_announces[start:end]
            else:
                # We already paginated in DB, and total_count was calculated before processing
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
                convert_db_favourite_to_dict(favourite) for favourite in results
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
                        node_name = parse_nomadnetwork_node_display_name(
                            db_announce["app_data"],
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

        # delete archived pages
        @routes.delete("/api/v1/nomadnet/archives")
        async def delete_archived_pages(request):
            # get archive IDs from body
            data = await request.json()
            ids = data.get("ids", [])

            if not ids:
                return web.json_response(
                    {
                        "message": "No archive IDs provided!",
                    },
                    status=400,
                )

            # delete archives from database
            self.database.misc.delete_archived_pages(ids=ids)

            return web.json_response(
                {
                    "message": f"Deleted {len(ids)} archives!",
                },
            )

        @routes.get("/api/v1/lxmf/propagation-node/status")
        async def propagation_node_status(request):
            return web.json_response(
                {
                    "propagation_node_status": {
                        "state": convert_propagation_node_state_to_string(
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
                try:
                    results = results[: int(limit)]
                except (ValueError, TypeError):
                    pass

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
                    operator_display_name = parse_lxmf_display_name(
                        lxmf_delivery_announce["app_data"],
                        None,
                    )
                elif (
                    nomadnetwork_node_announce is not None
                    and nomadnetwork_node_announce["app_data"] is not None
                ):
                    operator_display_name = parse_nomadnetwork_node_display_name(
                        nomadnetwork_node_announce["app_data"],
                        None,
                    )

                # parse app_data so we can see if propagation is enabled or disabled for this node
                is_propagation_enabled = None
                per_transfer_limit = None
                propagation_node_data = parse_lxmf_propagation_node_app_data(
                    announce["app_data"],
                )
                if propagation_node_data is not None:
                    is_propagation_enabled = propagation_node_data["enabled"]
                    per_transfer_limit = propagation_node_data["per_transfer_limit"]

                # ensure created_at and updated_at have Z suffix for UTC if they don't have a timezone
                created_at = str(announce["created_at"])
                if created_at and "+" not in created_at and "Z" not in created_at:
                    created_at += "Z"

                updated_at = str(announce["updated_at"])
                if updated_at and "+" not in updated_at and "Z" not in updated_at:
                    updated_at += "Z"

                lxmf_propagation_nodes.append(
                    {
                        "destination_hash": announce["destination_hash"],
                        "identity_hash": announce["identity_hash"],
                        "operator_display_name": operator_display_name,
                        "is_propagation_enabled": is_propagation_enabled,
                        "per_transfer_limit": per_transfer_limit,
                        "created_at": created_at,
                        "updated_at": updated_at,
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
            next_hop_bytes = None
            next_hop_interface = None
            if hasattr(self, "reticulum") and self.reticulum:
                next_hop_bytes = self.reticulum.get_next_hop(destination_hash)
                next_hop_interface = self.reticulum.get_next_hop_if_name(
                    destination_hash,
                )

            # ensure next hop provided
            if next_hop_bytes is None:
                return web.json_response(
                    {
                        "path": None,
                    },
                )

            next_hop = next_hop_bytes.hex()
            next_hop_interface = (
                self.reticulum.get_next_hop_if_name(destination_hash)
                if hasattr(self, "reticulum") and self.reticulum
                else None
            )

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
            if hasattr(self, "reticulum") and self.reticulum:
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
            if rssi is None and hasattr(self, "reticulum") and self.reticulum:
                rssi = self.reticulum.get_packet_rssi(receipt.proof_packet.packet_hash)

            # get snr
            snr = receipt.proof_packet.snr
            if snr is None and hasattr(self, "reticulum") and self.reticulum:
                snr = self.reticulum.get_packet_snr(receipt.proof_packet.packet_hash)

            # get signal quality
            quality = receipt.proof_packet.q
            if quality is None and hasattr(self, "reticulum") and self.reticulum:
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

        @routes.get("/api/v1/rnpath/table")
        async def rnpath_table(request):
            max_hops = request.query.get("max_hops")
            if max_hops:
                max_hops = int(max_hops)

            search = request.query.get("search")
            interface = request.query.get("interface")
            hops = request.query.get("hops")
            if hops:
                hops = int(hops)

            page = int(request.query.get("page", 1))
            limit = int(request.query.get("limit", 50))

            try:
                result = self.rnpath_handler.get_path_table(
                    max_hops=max_hops,
                    search=search,
                    interface=interface,
                    hops=hops,
                    page=page,
                    limit=limit,
                )
                return web.json_response(result)
            except Exception as e:
                return web.json_response({"message": str(e)}, status=500)

        @routes.get("/api/v1/rnpath/rates")
        async def rnpath_rates(request):
            try:
                rates = self.rnpath_handler.get_rate_table()
                return web.json_response({"rates": rates})
            except Exception as e:
                return web.json_response({"message": str(e)}, status=500)

        @routes.post("/api/v1/rnpath/drop")
        async def rnpath_drop(request):
            data = await request.json()
            destination_hash = data.get("destination_hash")
            if not destination_hash:
                return web.json_response(
                    {"message": "destination_hash is required"},
                    status=400,
                )
            try:
                success = self.rnpath_handler.drop_path(destination_hash)
                return web.json_response({"success": success})
            except Exception as e:
                return web.json_response({"message": str(e)}, status=500)

        @routes.post("/api/v1/rnpath/drop-via")
        async def rnpath_drop_via(request):
            data = await request.json()
            transport_instance_hash = data.get("transport_instance_hash")
            if not transport_instance_hash:
                return web.json_response(
                    {"message": "transport_instance_hash is required"},
                    status=400,
                )
            try:
                success = self.rnpath_handler.drop_all_via(transport_instance_hash)
                return web.json_response({"success": success})
            except Exception as e:
                return web.json_response({"message": str(e)}, status=500)

        @routes.post("/api/v1/rnpath/drop-queues")
        async def rnpath_drop_queues(request):
            try:
                self.rnpath_handler.drop_announce_queues()
                return web.json_response({"success": True})
            except Exception as e:
                return web.json_response({"message": str(e)}, status=500)

        @routes.post("/api/v1/rnpath/request")
        async def rnpath_request(request):
            data = await request.json()
            destination_hash = data.get("destination_hash")
            if not destination_hash:
                return web.json_response(
                    {"message": "destination_hash is required"},
                    status=400,
                )
            try:
                success = self.rnpath_handler.request_path(destination_hash)
                return web.json_response({"success": success})
            except Exception as e:
                return web.json_response({"message": str(e)}, status=500)

        @routes.get("/api/v1/rnpath/trace/{destination_hash}")
        async def rnpath_trace(request):
            destination_hash = request.match_info.get("destination_hash")
            if not destination_hash:
                return web.json_response(
                    {"error": "destination_hash is required"},
                    status=400,
                )
            try:
                if not self.rnpath_trace_handler:
                    return web.json_response(
                        {
                            "error": "RNPathTraceHandler not initialized for current context",
                        },
                        status=503,
                    )
                result = await self.rnpath_trace_handler.trace_path(destination_hash)
                return web.json_response(result)
            except Exception as e:
                import traceback

                error_msg = f"Trace route failed: {e}\n{traceback.format_exc()}"
                print(error_msg)
                return web.json_response({"error": error_msg}, status=500)

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

        @routes.get("/api/v1/bots/status")
        async def bots_status(request):
            try:
                status = self.bot_handler.get_status()
                templates = self.bot_handler.get_available_templates()
                return web.json_response(
                    {
                        "status": status,
                        "templates": templates,
                        "detection_error": status.get("detection_error"),
                    },
                )
            except Exception as e:
                return web.json_response(
                    {"message": str(e)},
                    status=500,
                )

        @routes.post("/api/v1/bots/start")
        async def bots_start(request):
            data = await request.json()
            template_id = data.get("template_id")
            name = data.get("name")
            bot_id = data.get("bot_id")

            if not template_id:
                return web.json_response(
                    {"message": "template_id is required"},
                    status=400,
                )

            try:
                bot_id = self.bot_handler.start_bot(
                    template_id,
                    name=name,
                    bot_id=bot_id,
                )
                return web.json_response({"bot_id": bot_id, "success": True})
            except Exception as e:
                return web.json_response(
                    {"message": str(e)},
                    status=500,
                )

        @routes.post("/api/v1/bots/stop")
        async def bots_stop(request):
            data = await request.json()
            bot_id = data.get("bot_id")

            if not bot_id:
                return web.json_response(
                    {"message": "bot_id is required"},
                    status=400,
                )

            try:
                success = self.bot_handler.stop_bot(bot_id)
                return web.json_response({"success": success})
            except Exception as e:
                return web.json_response(
                    {"message": str(e)},
                    status=500,
                )

        @routes.post("/api/v1/bots/restart")
        async def bots_restart(request):
            data = await request.json()
            bot_id = data.get("bot_id")

            if not bot_id:
                return web.json_response(
                    {"message": "bot_id is required"},
                    status=400,
                )

            try:
                new_id = self.bot_handler.restart_bot(bot_id)
                return web.json_response({"bot_id": new_id, "success": True})
            except Exception as e:
                return web.json_response(
                    {"message": str(e)},
                    status=500,
                )

        @routes.post("/api/v1/bots/delete")
        async def bots_delete(request):
            data = await request.json()
            bot_id = data.get("bot_id")

            if not bot_id:
                return web.json_response(
                    {"message": "bot_id is required"},
                    status=400,
                )

            try:
                success = self.bot_handler.delete_bot(bot_id)
                return web.json_response({"success": success})
            except Exception as e:
                return web.json_response(
                    {"message": str(e)},
                    status=500,
                )

        @routes.get("/api/v1/bots/export")
        async def bots_export(request):
            bot_id = request.query.get("bot_id")

            if not bot_id:
                return web.json_response(
                    {"message": "bot_id is required"},
                    status=400,
                )

            try:
                id_path = self.bot_handler.get_bot_identity_path(bot_id)
                if not id_path or not os.path.exists(id_path):
                    return web.json_response(
                        {"message": "Identity file not found"},
                        status=404,
                    )

                return web.FileResponse(
                    id_path,
                    headers={
                        "Content-Disposition": f'attachment; filename="bot_{bot_id}_identity"',
                    },
                )
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
                lxmf_stamp_cost = parse_lxmf_stamp_cost(
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
            interface_stats = {"interfaces": []}
            if hasattr(self, "reticulum") and self.reticulum:
                try:
                    interface_stats = self.reticulum.get_interface_stats()

                    # ensure transport_id is hex as json_response can't serialize bytes
                    if "transport_id" in interface_stats:
                        interface_stats["transport_id"] = interface_stats[
                            "transport_id"
                        ].hex()

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
                            interface["ifac_signature"] = interface[
                                "ifac_signature"
                            ].hex()

                        try:
                            if interface.get("hash"):
                                interface["hash"] = interface["hash"].hex()
                        except Exception:  # noqa: S110
                            pass
                except Exception:  # noqa: S110
                    pass

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
            all_paths = []
            if hasattr(self, "reticulum") and self.reticulum:
                try:
                    all_paths = self.reticulum.get_path_table()
                except Exception:  # noqa: S110
                    pass

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
                        "lxmf_message": convert_lxmf_message_to_dict(
                            lxmf_message,
                            include_attachments=False,
                            reticulum=self.reticulum,
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
                lxmf_message = convert_db_lxmf_message_to_dict(db_lxmf_message)

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
                convert_db_lxmf_message_to_dict(db_lxmf_message)
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

        @routes.get("/api/v1/lxmf-messages/{message_hash}/uri")
        async def lxmf_message_uri(request):
            message_hash = request.match_info.get("message_hash")

            # check if message exists in router's internal storage first
            # as it might still be in outbound queue or recent received cache
            lxm = self.message_router.get_message(bytes.fromhex(message_hash))

            if not lxm:
                # if not in router, we can't easily recreate it with same signatures
                # unless we stored the raw bytes. MeshChatX seems to store fields.
                return web.json_response(
                    {
                        "message": "Original message bytes not available for URI generation",
                    },
                    status=404,
                )

            try:
                # change delivery method to paper so as_uri works
                original_method = lxm.method
                lxm.method = LXMF.LXMessage.PAPER
                uri = lxm.as_uri()
                lxm.method = original_method  # restore

                return web.json_response({"uri": uri})
            except Exception as e:
                return web.json_response({"message": str(e)}, status=500)

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
            search_query = request.query.get("search", request.query.get("q", None))
            filter_unread = parse_bool_query_param(
                request.query.get(
                    "unread",
                    request.query.get("filter_unread", "false"),
                ),
            )
            filter_failed = parse_bool_query_param(
                request.query.get(
                    "failed",
                    request.query.get("filter_failed", "false"),
                ),
            )
            filter_has_attachments = parse_bool_query_param(
                request.query.get(
                    "has_attachments",
                    request.query.get("filter_has_attachments", "false"),
                ),
            )
            folder_id = request.query.get("folder_id")
            if folder_id is not None:
                try:
                    folder_id = int(folder_id)
                except ValueError:
                    folder_id = None

            # get pagination params
            try:
                limit = request.query.get("limit")
                limit = int(limit) if limit is not None else None
            except ValueError:
                limit = None

            try:
                offset = request.query.get("offset")
                offset = int(offset) if offset is not None else 0
            except ValueError:
                offset = 0

            local_hash = self.local_lxmf_destination.hexhash

            # fetch conversations from database with optimized query
            db_conversations = self.message_handler.get_conversations(
                local_hash,
                search=search_query,
                filter_unread=filter_unread,
                filter_failed=filter_failed,
                filter_has_attachments=filter_has_attachments,
                folder_id=folder_id,
                limit=limit,
                offset=offset,
            )

            conversations = []
            for row in db_conversations:
                other_user_hash = row["peer_hash"]

                # determine display name
                display_name = "Anonymous Peer"
                if row["peer_app_data"]:
                    display_name = parse_lxmf_display_name(
                        app_data_base64=row["peer_app_data"],
                    )

                # user icon
                user_icon = None
                if row["icon_name"]:
                    user_icon = {
                        "icon_name": row["icon_name"],
                        "foreground_colour": row["foreground_colour"],
                        "background_colour": row["background_colour"],
                    }

                # contact image
                contact_image = (
                    row["contact_image"] if "contact_image" in row.keys() else None
                )

                # check if is_unread (using last_read_at from join)
                is_unread = False
                if not row["last_read_at"]:
                    is_unread = True
                else:
                    last_read_at = datetime.fromisoformat(row["last_read_at"])
                    if last_read_at.tzinfo is None:
                        last_read_at = last_read_at.replace(tzinfo=UTC)
                    is_unread = row["timestamp"] > last_read_at.timestamp()

                # Add extra check for notification viewed state if unread
                if is_unread and filter_unread:
                    if self.database.messages.is_notification_viewed(
                        other_user_hash,
                        row["timestamp"],
                    ):
                        is_unread = False
                        if filter_unread:
                            continue  # Skip this conversation if filtering unread and it's actually viewed

                # add to conversations
                conversations.append(
                    {
                        "display_name": display_name,
                        "custom_display_name": row["custom_display_name"],
                        "contact_image": contact_image,
                        "destination_hash": other_user_hash,
                        "is_unread": is_unread,
                        "is_tracking": self.database.telemetry.is_tracking(
                            other_user_hash,
                        ),
                        "failed_messages_count": row["failed_count"],
                        "has_attachments": message_fields_have_attachments(
                            row["fields"],
                        ),
                        "latest_message_title": row["title"],
                        "latest_message_preview": row["content"],
                        "latest_message_created_at": row["timestamp"],
                        "lxmf_user_icon": user_icon,
                        "updated_at": datetime.fromtimestamp(
                            row["timestamp"],
                            UTC,
                        ).isoformat(),
                    },
                )

            return web.json_response(
                {
                    "conversations": conversations,
                },
            )

        @routes.get("/api/v1/lxmf/folders")
        async def lxmf_folders_get(request):
            folders = self.database.messages.get_all_folders()
            return web.json_response([dict(f) for f in folders])

        @routes.post("/api/v1/lxmf/folders")
        async def lxmf_folders_post(request):
            data = await request.json()
            name = data.get("name")
            if not name:
                return web.json_response({"message": "Name is required"}, status=400)
            try:
                self.database.messages.create_folder(name)
                return web.json_response({"message": "Folder created"})
            except Exception as e:
                return web.json_response({"message": str(e)}, status=500)

        @routes.patch("/api/v1/lxmf/folders/{id}")
        async def lxmf_folders_patch(request):
            folder_id = int(request.match_info["id"])
            data = await request.json()
            name = data.get("name")
            if not name:
                return web.json_response({"message": "Name is required"}, status=400)
            self.database.messages.rename_folder(folder_id, name)
            return web.json_response({"message": "Folder renamed"})

        @routes.delete("/api/v1/lxmf/folders/{id}")
        async def lxmf_folders_delete(request):
            folder_id = int(request.match_info["id"])
            self.database.messages.delete_folder(folder_id)
            return web.json_response({"message": "Folder deleted"})

        @routes.post("/api/v1/lxmf/conversations/move-to-folder")
        async def lxmf_conversations_move_to_folder(request):
            data = await request.json()
            peer_hashes = data.get("peer_hashes", [])
            folder_id = data.get("folder_id")  # Can be None to remove from folder
            if not peer_hashes:
                return web.json_response(
                    {"message": "peer_hashes is required"},
                    status=400,
                )
            self.database.messages.move_conversations_to_folder(peer_hashes, folder_id)
            return web.json_response({"message": "Conversations moved"})

        @routes.post("/api/v1/lxmf/conversations/bulk-mark-as-read")
        async def lxmf_conversations_bulk_mark_read(request):
            data = await request.json()
            destination_hashes = data.get("destination_hashes", [])
            if not destination_hashes:
                return web.json_response(
                    {"message": "destination_hashes is required"},
                    status=400,
                )
            self.database.messages.mark_conversations_as_read(destination_hashes)
            return web.json_response({"message": "Conversations marked as read"})

        @routes.post("/api/v1/lxmf/conversations/bulk-delete")
        async def lxmf_conversations_bulk_delete(request):
            data = await request.json()
            destination_hashes = data.get("destination_hashes", [])
            if not destination_hashes:
                return web.json_response(
                    {"message": "destination_hashes is required"},
                    status=400,
                )
            local_hash = self.local_lxmf_destination.hexhash
            for dest_hash in destination_hashes:
                self.message_handler.delete_conversation(local_hash, dest_hash)
            return web.json_response({"message": "Conversations deleted"})

        @routes.get("/api/v1/lxmf/folders/export")
        async def lxmf_folders_export(request):
            folders = [dict(f) for f in self.database.messages.get_all_folders()]
            mappings = [
                dict(m) for m in self.database.messages.get_all_conversation_folders()
            ]
            return web.json_response({"folders": folders, "mappings": mappings})

        @routes.post("/api/v1/lxmf/folders/import")
        async def lxmf_folders_import(request):
            data = await request.json()
            folders = data.get("folders", [])
            mappings = data.get("mappings", [])

            # We'll try to recreate folders by name to avoid ID conflicts
            folder_name_to_new_id = {}
            for f in folders:
                try:
                    self.database.messages.create_folder(f["name"])
                except Exception as e:
                    logger.debug(f"Folder '{f['name']}' likely already exists: {e}")

            # Refresh folder list to get new IDs
            all_folders = self.database.messages.get_all_folders()
            for f in all_folders:
                folder_name_to_new_id[f["name"]] = f["id"]

            # Map old IDs to new IDs if possible, or just use names if we had them
            # Since IDs might change, we should have exported names too
            # Let's assume the export had folder names in mappings or we match by old folder info
            old_id_to_name = {f["id"]: f["name"] for f in folders}

            for m in mappings:
                peer_hash = m["peer_hash"]
                old_folder_id = m["folder_id"]
                folder_name = old_id_to_name.get(old_folder_id)
                if folder_name and folder_name in folder_name_to_new_id:
                    new_folder_id = folder_name_to_new_id[folder_name]
                    self.database.messages.move_conversation_to_folder(
                        peer_hash,
                        new_folder_id,
                    )

            return web.json_response({"message": "Folders and mappings imported"})

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
                    destination_hashes,
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
                filter_unread = parse_bool_query_param(
                    request.query.get("unread", "false"),
                )
                limit = int(request.query.get("limit", 50))

                # 1. Fetch system notifications
                system_notifications = self.database.misc.get_notifications(
                    filter_unread=filter_unread,
                    limit=limit,
                )

                # 2. Fetch unread LXMF conversations if requested
                conversations = []
                if filter_unread:
                    local_hash = self.local_lxmf_destination.hexhash
                    db_conversations = self.message_handler.get_conversations(
                        local_hash,
                        filter_unread=True,
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
                        display_name = self.get_lxmf_conversation_name(
                            other_user_hash,
                        )
                        custom_display_name = (
                            self.database.announces.get_custom_display_name(
                                other_user_hash,
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
                                    latest_message_data["timestamp"] or 0,
                                    UTC,
                                ).isoformat(),
                            },
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
                            n["remote_hash"],
                        )
                        if not lxmf_hash:
                            # Fallback to direct name lookup by identity hash
                            display_name = (
                                self.get_name_for_identity_hash(n["remote_hash"])
                                or n["remote_hash"]
                            )
                        else:
                            display_name = self.get_lxmf_conversation_name(
                                lxmf_hash,
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
                                n["timestamp"] or 0,
                                UTC,
                            ).isoformat(),
                        },
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
                    local_hash,
                    filter_unread=True,
                )
                if unread_conversations:
                    lxmf_unread_count = len(unread_conversations)

                total_unread_count = unread_count + lxmf_unread_count

                return web.json_response(
                    {
                        "notifications": all_notifications[:limit],
                        "unread_count": total_unread_count,
                    },
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

                # add to Reticulum blackhole if available and enabled
                if self.config.blackhole_integration_enabled.get():
                    try:
                        if hasattr(self, "reticulum") and self.reticulum:
                            # Try to resolve identity hash from destination hash
                            identity_hash = None
                            announce = self.database.announces.get_announce_by_hash(
                                destination_hash,
                            )
                            if announce and announce.get("identity_hash"):
                                identity_hash = announce["identity_hash"]

                            # Use resolved identity hash or fallback to destination hash
                            target_hash = identity_hash or destination_hash
                            dest_bytes = bytes.fromhex(target_hash)

                            # Reticulum 1.1.0+
                            if hasattr(self.reticulum, "blackhole_identity"):
                                reason = (
                                    f"Blocked in MeshChatX (from {destination_hash})"
                                    if identity_hash
                                    else "Blocked in MeshChatX"
                                )
                                self.reticulum.blackhole_identity(
                                    dest_bytes,
                                    reason=reason,
                                )
                            else:
                                # fallback to dropping path
                                self.reticulum.drop_path(dest_bytes)
                    except Exception as e:
                        print(f"Failed to blackhole identity in Reticulum: {e}")
                else:
                    # fallback to just dropping path if integration disabled
                    try:
                        if hasattr(self, "reticulum") and self.reticulum:
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

                # remove from Reticulum blackhole if available and enabled
                if self.config.blackhole_integration_enabled.get():
                    try:
                        if hasattr(self, "reticulum") and self.reticulum:
                            # Try to resolve identity hash from destination hash
                            identity_hash = None
                            announce = self.database.announces.get_announce_by_hash(
                                destination_hash,
                            )
                            if announce and announce.get("identity_hash"):
                                identity_hash = announce["identity_hash"]

                            # Use resolved identity hash or fallback to destination hash
                            target_hash = identity_hash or destination_hash
                            dest_bytes = bytes.fromhex(target_hash)

                            if hasattr(self.reticulum, "unblackhole_identity"):
                                self.reticulum.unblackhole_identity(dest_bytes)
                    except Exception as e:
                        print(f"Failed to unblackhole identity in Reticulum: {e}")

                return web.json_response({"message": "ok"})
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        @routes.get("/api/v1/reticulum/blackhole")
        async def reticulum_blackhole_get(request):
            if not hasattr(self, "reticulum") or not self.reticulum:
                return web.json_response(
                    {"error": "Reticulum not initialized"},
                    status=503,
                )

            try:
                if hasattr(self.reticulum, "get_blackholed_identities"):
                    identities = self.reticulum.get_blackholed_identities()
                    # Convert bytes keys to hex strings
                    formatted = {}
                    for h, info in identities.items():
                        formatted[h.hex()] = {
                            "source": info.get("source", b"").hex()
                            if info.get("source")
                            else None,
                            "until": info.get("until"),
                            "reason": info.get("reason"),
                        }
                    return web.json_response({"blackholed_identities": formatted})
                return web.json_response({"blackholed_identities": {}})
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
            return web.json_response({"loaded": False})

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

                # If tile not found, return a transparent 1x1 PNG instead of 404
                # to avoid browser console errors in offline mode.
                return web.Response(body=TRANSPARENT_TILE, content_type="image/png")
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

        # map drawings
        @routes.get("/api/v1/map/drawings")
        async def get_map_drawings(request):
            identity_hash = self.identity.hash.hex()
            rows = self.database.map_drawings.get_drawings(identity_hash)
            drawings = [dict(row) for row in rows]
            return web.json_response({"drawings": drawings})

        @routes.post("/api/v1/map/drawings")
        async def save_map_drawing(request):
            identity_hash = self.identity.hash.hex()
            data = await request.json()
            name = data.get("name")
            drawing_data = data.get("data")
            self.database.map_drawings.upsert_drawing(identity_hash, name, drawing_data)
            return web.json_response({"message": "Drawing saved successfully"})

        @routes.delete("/api/v1/map/drawings/{drawing_id}")
        async def delete_map_drawing(request):
            drawing_id = request.match_info.get("drawing_id")
            self.database.map_drawings.delete_drawing(drawing_id)
            return web.json_response({"message": "Drawing deleted successfully"})

        @routes.patch("/api/v1/map/drawings/{drawing_id}")
        async def update_map_drawing(request):
            drawing_id = request.match_info.get("drawing_id")
            data = await request.json()
            name = data.get("name")
            drawing_data = data.get("data")
            self.database.map_drawings.update_drawing(drawing_id, name, drawing_data)
            return web.json_response({"message": "Drawing updated successfully"})

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
                        "is_tracking": self.database.telemetry.is_tracking(
                            r["destination_hash"],
                        ),
                    },
                )
            return web.json_response({"telemetry": telemetry_list})

        @routes.get("/api/v1/telemetry/trusted-peers")
        async def telemetry_trusted_peers_get(request):
            # get all contacts that are telemetry trusted
            contacts = self.database.provider.fetchall(
                "SELECT * FROM contacts WHERE is_telemetry_trusted = 1 ORDER BY name ASC",
            )
            return web.json_response({"trusted_peers": [dict(c) for c in contacts]})

        # toggle telemetry tracking for a destination
        @routes.post("/api/v1/telemetry/tracking/{destination_hash}/toggle")
        async def toggle_telemetry_tracking(request):
            destination_hash = request.match_info["destination_hash"]
            data = await request.json()
            is_tracking = data.get("is_tracking")

            new_status = self.database.telemetry.toggle_tracking(
                destination_hash,
                is_tracking,
            )
            return web.json_response({"status": "ok", "is_tracking": new_status})

        # get all tracked peers
        @routes.get("/api/v1/telemetry/tracking")
        async def get_tracked_peers(request):
            results = self.database.telemetry.get_tracked_peers()
            return web.json_response({"tracked_peers": results})

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
            if response is None:
                return None
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
            elif path.endswith(".opus"):
                response.headers["Content-Type"] = "audio/opus"
            elif path.endswith(".ogg"):
                response.headers["Content-Type"] = "audio/ogg"
            elif path.endswith(".wav"):
                response.headers["Content-Type"] = "audio/wav"
            elif path.endswith(".mp3"):
                response.headers["Content-Type"] = "audio/mpeg"
            return response

        # security headers middleware
        @web.middleware
        async def security_middleware(request, handler):
            response = await handler(request)
            if response is None:
                return None
            # Add security headers to all responses
            response.headers["X-Content-Type-Options"] = "nosniff"

            # Allow framing for docs and rnode flasher
            if request.path.startswith("/reticulum-docs/") or request.path.startswith(
                "/rnode-flasher/",
            ):
                response.headers["X-Frame-Options"] = "SAMEORIGIN"
            else:
                response.headers["X-Frame-Options"] = "DENY"

            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

            # CSP base configuration
            connect_sources = [
                "'self'",
                "ws://localhost:*",
                "wss://localhost:*",
                "blob:",
                "https://*.tile.openstreetmap.org",
                "https://tile.openstreetmap.org",
                "https://nominatim.openstreetmap.org",
                "https://*.cartocdn.com",
            ]

            img_sources = [
                "'self'",
                "data:",
                "blob:",
                "https://*.tile.openstreetmap.org",
                "https://tile.openstreetmap.org",
                "https://*.cartocdn.com",
            ]

            frame_sources = [
                "'self'",
                "https://reticulum.network",
            ]

            script_sources = ["'self'", "'unsafe-inline'", "'unsafe-eval'"]
            style_sources = ["'self'", "'unsafe-inline'"]

            if self.current_context and self.current_context.config:
                # Helper to add domain from URL
                def add_domain_from_url(url, target_list):
                    if not url:
                        return None
                    try:
                        parsed = urlparse(url)
                        if parsed.netloc:
                            domain = f"{parsed.scheme}://{parsed.netloc}"
                            if domain not in target_list:
                                target_list.append(domain)
                            return domain
                    except Exception:  # noqa: S110
                        pass
                    return None

                # Add configured Gitea base URL
                add_domain_from_url(
                    self.current_context.config.gitea_base_url.get(),
                    connect_sources,
                )

                # Add configured docs download URLs domains
                docs_urls_str = self.current_context.config.docs_download_urls.get()
                docs_urls = [
                    u.strip()
                    for u in docs_urls_str.replace("\n", ",").split(",")
                    if u.strip()
                ]
                for url in docs_urls:
                    domain = add_domain_from_url(url, connect_sources)
                    if domain and "github.com" in domain:
                        content_domain = "https://objects.githubusercontent.com"
                        if content_domain not in connect_sources:
                            connect_sources.append(content_domain)

                # Add map tile server domain
                map_tile_url = self.current_context.config.map_tile_server_url.get()
                add_domain_from_url(map_tile_url, img_sources)
                add_domain_from_url(map_tile_url, connect_sources)

                # Add nominatim API domain
                nominatim_url = self.current_context.config.map_nominatim_api_url.get()
                add_domain_from_url(nominatim_url, connect_sources)

                # Add custom CSP sources from config
                def add_extra_sources(extra_str, target_list):
                    if not extra_str:
                        return
                    sources = [
                        s.strip()
                        for s in extra_str.replace("\n", ",")
                        .replace(";", ",")
                        .split(",")
                        if s.strip()
                    ]
                    for s in sources:
                        if s not in target_list:
                            target_list.append(s)

                add_extra_sources(
                    self.current_context.config.csp_extra_connect_src.get(),
                    connect_sources,
                )
                add_extra_sources(
                    self.current_context.config.csp_extra_img_src.get(),
                    img_sources,
                )
                add_extra_sources(
                    self.current_context.config.csp_extra_frame_src.get(),
                    frame_sources,
                )
                add_extra_sources(
                    self.current_context.config.csp_extra_script_src.get(),
                    script_sources,
                )
                add_extra_sources(
                    self.current_context.config.csp_extra_style_src.get(),
                    style_sources,
                )

            csp = (
                "default-src 'self'; "
                f"script-src {' '.join(script_sources)}; "
                f"style-src {' '.join(style_sources)}; "
                f"img-src {' '.join(img_sources)}; "
                "font-src 'self' data:; "
                f"connect-src {' '.join(connect_sources)}; "
                "media-src 'self' blob:; "
                "worker-src 'self' blob:; "
                f"frame-src {' '.join(frame_sources)}; "
                "object-src 'none'; "
                "base-uri 'self';"
            )
            response.headers["Content-Security-Policy"] = csp
            return response

        return auth_middleware, mime_type_middleware, security_middleware

    def run(self, host, port, launch_browser: bool, enable_https: bool = True):
        # create route table
        routes = web.RouteTableDef()
        auth_middleware, mime_type_middleware, security_middleware = (
            self._define_routes(routes)
        )

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
            secret_key_bytes = hashlib.sha256(
                self.session_secret_key.encode("utf-8"),
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
        public_dir = self.get_public_path()

        # Handle documentation directories that might be in a writable storage location
        # (e.g. when running from a read-only AppImage)
        if self.current_context and hasattr(self.current_context, "docs_manager"):
            dm = self.current_context.docs_manager

            # Custom handler for reticulum docs to allow fallback to official website
            async def reticulum_docs_handler(request):
                path = request.match_info.get("filename", "index.html")
                if not path:
                    path = "index.html"
                if path.endswith("/"):
                    path += "index.html"

                local_path = os.path.join(dm.docs_dir, path)
                if os.path.exists(local_path) and os.path.isfile(local_path):
                    return web.FileResponse(local_path)

                # Fallback to official website
                return web.HTTPFound(f"https://reticulum.network/manual/{path}")

            app.router.add_get("/reticulum-docs/{filename:.*}", reticulum_docs_handler)

            if (
                dm.meshchatx_docs_dir
                and os.path.exists(dm.meshchatx_docs_dir)
                and not dm.meshchatx_docs_dir.startswith(public_dir)
            ):
                app.router.add_static(
                    "/meshchatx-docs/",
                    dm.meshchatx_docs_dir,
                    name="meshchatx_docs_storage",
                    follow_symlinks=True,
                )

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

    # auto backup loop
    async def auto_backup_loop(self, session_id, context=None):
        ctx = context or self.current_context
        if not ctx:
            return

        # wait 5 minutes before first backup
        await asyncio.sleep(300)

        while self.running and ctx.running and ctx.session_id == session_id:
            try:
                if not self.emergency:
                    print(
                        f"Performing scheduled auto-backup for {ctx.identity_hash}...",
                    )
                    max_count = ctx.config.backup_max_count.get()
                    ctx.database.backup_database(self.storage_dir, max_count=max_count)
            except Exception as e:
                print(f"Auto-backup failed: {e}")

            # Sleep for 12 hours
            await asyncio.sleep(12 * 3600)

    async def telemetry_tracking_loop(self, session_id, context=None):
        ctx = context or self.current_context
        if not ctx:
            return

        while self.running and ctx.running and ctx.session_id == session_id:
            try:
                # Only run if telemetry is enabled globally
                if not ctx.config.telemetry_enabled.get():
                    await asyncio.sleep(60)
                    continue

                # Get all tracked peers
                tracked_peers = ctx.database.telemetry.get_tracked_peers()
                now = time.time()

                for peer in tracked_peers:
                    dest_hash = peer["destination_hash"]
                    interval = peer.get("interval_seconds", 60)
                    last_req = peer.get("last_request_at")

                    if last_req is None or now - last_req >= interval:
                        print(f"Sending telemetry request to tracked peer: {dest_hash}")
                        # Send telemetry request
                        await self.send_message(
                            destination_hash=dest_hash,
                            content="",
                            commands=[{SidebandCommands.TELEMETRY_REQUEST: 0}],
                            delivery_method="opportunistic",
                            no_display=False,
                            context=ctx,
                        )
                        # Update last request time
                        ctx.database.telemetry.update_last_request_at(dest_hash, now)

            except Exception as e:
                print(f"Telemetry tracking loop error: {e}")

            # Check every 10 seconds
            await asyncio.sleep(10)

    # handle announcing
    async def announce(self, context=None):
        ctx = context or self.current_context
        if not ctx:
            return

        # update last announced at timestamp
        ctx.config.last_announced_at.set(int(time.time()))

        # send announce for lxmf (ensuring name is updated before announcing)
        ctx.local_lxmf_destination.display_name = ctx.config.display_name.get()
        ctx.message_router.announce(destination_hash=ctx.local_lxmf_destination.hash)

        # send announce for local propagation node (if enabled)
        if ctx.config.lxmf_local_propagation_node_enabled.get():
            ctx.message_router.announce_propagation_node()

        # send announce for telephone
        ctx.telephone_manager.announce(display_name=ctx.config.display_name.get())

        # tell websocket clients we just announced
        await self.send_announced_to_websocket_clients(context=ctx)

    # handle syncing propagation nodes
    async def sync_propagation_nodes(self, context=None):
        ctx = context or self.current_context
        if not ctx:
            return

        # update last synced at timestamp
        ctx.config.lxmf_preferred_propagation_node_last_synced_at.set(int(time.time()))

        # request messages from propagation node
        ctx.message_router.request_messages_from_propagation_node(ctx.identity)

        # send config to websocket clients (used to tell ui last synced at)
        await self.send_config_to_websocket_clients(context=ctx)

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
            # Update identity metadata cache
            self.update_identity_metadata_cache()

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
                data["auto_resend_failed_messages_when_announce_received"],
            )
            self.config.auto_resend_failed_messages_when_announce_received.set(value)

        if "allow_auto_resending_failed_messages_with_attachments" in data:
            value = self._parse_bool(
                data["allow_auto_resending_failed_messages_with_attachments"],
            )
            self.config.allow_auto_resending_failed_messages_with_attachments.set(value)

        if "auto_send_failed_messages_to_propagation_node" in data:
            value = self._parse_bool(
                data["auto_send_failed_messages_to_propagation_node"],
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

        if "lxmf_preferred_propagation_node_auto_select" in data:
            value = self._parse_bool(
                data["lxmf_preferred_propagation_node_auto_select"],
            )
            self.config.lxmf_preferred_propagation_node_auto_select.set(value)

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
            self.database.misc.clear_last_sent_icon_hashes()
            self.update_identity_metadata_cache()

        # update lxmf user icon foreground colour in config
        if "lxmf_user_icon_foreground_colour" in data:
            self.config.lxmf_user_icon_foreground_colour.set(
                data["lxmf_user_icon_foreground_colour"],
            )
            self.database.misc.clear_last_sent_icon_hashes()
            self.update_identity_metadata_cache()

        # update lxmf user icon background colour in config
        if "lxmf_user_icon_background_colour" in data:
            self.config.lxmf_user_icon_background_colour.set(
                data["lxmf_user_icon_background_colour"],
            )
            self.database.misc.clear_last_sent_icon_hashes()
            self.update_identity_metadata_cache()

        # update archiver settings
        if "page_archiver_enabled" in data:
            self.config.page_archiver_enabled.set(
                self._parse_bool(data["page_archiver_enabled"]),
            )

        if "page_archiver_max_versions" in data:
            self.config.page_archiver_max_versions.set(
                int(data["page_archiver_max_versions"]),
            )

        if "archives_max_storage_gb" in data:
            self.config.archives_max_storage_gb.set(
                int(data["archives_max_storage_gb"]),
            )

        if "backup_max_count" in data:
            try:
                value = int(data["backup_max_count"])
            except (TypeError, ValueError):
                value = self.config.backup_max_count.default_value
            value = max(1, min(value, 50))
            self.config.backup_max_count.set(value)

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

            # if disabling auth, also remove the password hash from config
            if not value:
                self.config.auth_password_hash.set(None)

        # update map settings
        if "map_offline_enabled" in data:
            self.config.map_offline_enabled.set(
                self._parse_bool(data["map_offline_enabled"]),
            )

        if "map_default_lat" in data:
            self.config.map_default_lat.set(str(data["map_default_lat"]))

        if "map_default_lon" in data:
            self.config.map_default_lon.set(str(data["map_default_lon"]))

        if "map_default_zoom" in data:
            try:
                value = int(data["map_default_zoom"])
            except (TypeError, ValueError):
                value = None
            if value is not None:
                self.config.map_default_zoom.set(value)

        if "map_mbtiles_dir" in data:
            self.config.map_mbtiles_dir.set(data["map_mbtiles_dir"])

        if "map_tile_cache_enabled" in data:
            self.config.map_tile_cache_enabled.set(
                self._parse_bool(data["map_tile_cache_enabled"]),
            )

        if "map_tile_server_url" in data:
            self.config.map_tile_server_url.set(data["map_tile_server_url"])

        if "map_nominatim_api_url" in data:
            self.config.map_nominatim_api_url.set(data["map_nominatim_api_url"])

        # update location settings
        if "location_source" in data:
            self.config.location_source.set(data["location_source"])

        if "location_manual_lat" in data:
            self.config.location_manual_lat.set(str(data["location_manual_lat"]))

        if "location_manual_lon" in data:
            self.config.location_manual_lon.set(str(data["location_manual_lon"]))

        if "location_manual_alt" in data:
            self.config.location_manual_alt.set(str(data["location_manual_alt"]))

        if "telemetry_enabled" in data:
            self.config.telemetry_enabled.set(
                self._parse_bool(data["telemetry_enabled"]),
            )

        # update banishment settings
        if "banished_effect_enabled" in data:
            self.config.banished_effect_enabled.set(
                self._parse_bool(data["banished_effect_enabled"]),
            )

        if "banished_text" in data:
            self.config.banished_text.set(data["banished_text"])

        if "banished_color" in data:
            self.config.banished_color.set(data["banished_color"])

        if "message_font_size" in data:
            try:
                value = int(data["message_font_size"])
            except (TypeError, ValueError):
                value = None
            if value is not None:
                self.config.message_font_size.set(value)

        if "message_icon_size" in data:
            try:
                value = int(data["message_icon_size"])
            except (TypeError, ValueError):
                value = None
            if value is not None:
                value = max(12, min(value, 96))
                self.config.message_icon_size.set(value)

        # update desktop settings
        if "desktop_open_calls_in_separate_window" in data:
            self.config.desktop_open_calls_in_separate_window.set(
                self._parse_bool(data["desktop_open_calls_in_separate_window"]),
            )

        if "desktop_hardware_acceleration_enabled" in data:
            enabled = self._parse_bool(data["desktop_hardware_acceleration_enabled"])
            self.config.desktop_hardware_acceleration_enabled.set(enabled)

            # write flag for electron to read on next launch
            try:
                disable_gpu_file = os.path.join(self.storage_dir, "disable-gpu")
                if not enabled:
                    with open(disable_gpu_file, "w") as f:
                        f.write("true")
                elif os.path.exists(disable_gpu_file):
                    os.remove(disable_gpu_file)
            except Exception as e:
                print(f"Failed to update GPU disable flag: {e}")

        if "blackhole_integration_enabled" in data:
            value = self._parse_bool(data["blackhole_integration_enabled"])
            self.config.blackhole_integration_enabled.set(value)

        # update csp extra sources
        if "csp_extra_connect_src" in data:
            self.config.csp_extra_connect_src.set(data["csp_extra_connect_src"])
        if "csp_extra_img_src" in data:
            self.config.csp_extra_img_src.set(data["csp_extra_img_src"])
        if "csp_extra_frame_src" in data:
            self.config.csp_extra_frame_src.set(data["csp_extra_frame_src"])
        if "csp_extra_script_src" in data:
            self.config.csp_extra_script_src.set(data["csp_extra_script_src"])
        if "csp_extra_style_src" in data:
            self.config.csp_extra_style_src.set(data["csp_extra_style_src"])

        # update voicemail settings
        if "voicemail_enabled" in data:
            self.config.voicemail_enabled.set(
                self._parse_bool(data["voicemail_enabled"]),
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

        if "voicemail_tts_speed" in data:
            self.config.voicemail_tts_speed.set(int(data["voicemail_tts_speed"]))

        if "voicemail_tts_pitch" in data:
            self.config.voicemail_tts_pitch.set(int(data["voicemail_tts_pitch"]))

        if "voicemail_tts_voice" in data:
            self.config.voicemail_tts_voice.set(data["voicemail_tts_voice"])

        if "voicemail_tts_word_gap" in data:
            self.config.voicemail_tts_word_gap.set(int(data["voicemail_tts_word_gap"]))

        # update ringtone settings
        if "custom_ringtone_enabled" in data:
            self.config.custom_ringtone_enabled.set(
                self._parse_bool(data["custom_ringtone_enabled"]),
            )
        if "ringtone_preferred_id" in data:
            self.config.ringtone_preferred_id.set(int(data["ringtone_preferred_id"]))
        if "ringtone_volume" in data:
            self.config.ringtone_volume.set(int(data["ringtone_volume"]))

        if "do_not_disturb_enabled" in data:
            self.config.do_not_disturb_enabled.set(
                self._parse_bool(data["do_not_disturb_enabled"]),
            )

        if "telephone_allow_calls_from_contacts_only" in data:
            self.config.telephone_allow_calls_from_contacts_only.set(
                self._parse_bool(data["telephone_allow_calls_from_contacts_only"]),
            )

        if "call_recording_enabled" in data:
            value = self._parse_bool(data["call_recording_enabled"])
            self.config.call_recording_enabled.set(value)
            # if a call is active, start or stop recording immediately
            if (
                self.telephone_manager
                and self.telephone_manager.telephone
                and self.telephone_manager.telephone.active_call
            ):
                if value:
                    self.telephone_manager.start_recording()
                else:
                    self.telephone_manager.stop_recording()

        if "telephone_tone_generator_enabled" in data:
            self.config.telephone_tone_generator_enabled.set(
                self._parse_bool(data["telephone_tone_generator_enabled"]),
            )

        if "telephone_tone_generator_volume" in data:
            self.config.telephone_tone_generator_volume.set(
                int(data["telephone_tone_generator_volume"]),
            )

        if "telephone_audio_profile_id" in data:
            profile_id = int(data["telephone_audio_profile_id"])
            self.config.telephone_audio_profile_id.set(profile_id)
            if self.telephone_manager and self.telephone_manager.telephone:
                await asyncio.to_thread(
                    self.telephone_manager.telephone.switch_profile,
                    profile_id,
                )

        if "telephone_web_audio_enabled" in data:
            self.config.telephone_web_audio_enabled.set(
                self._parse_bool(data["telephone_web_audio_enabled"]),
            )

        if "telephone_web_audio_allow_fallback" in data:
            self.config.telephone_web_audio_allow_fallback.set(
                self._parse_bool(data["telephone_web_audio_allow_fallback"]),
            )

        if "translator_enabled" in data:
            value = self._parse_bool(data["translator_enabled"])
            self.config.translator_enabled.set(value)
            if hasattr(self, "translator_handler"):
                self.translator_handler.enabled = value

        if "libretranslate_url" in data:
            value = data["libretranslate_url"]
            self.config.libretranslate_url.set(value)
            if hasattr(self, "translator_handler"):
                self.translator_handler.libretranslate_url = value

        # send config to websocket clients
        await self.send_config_to_websocket_clients()

    # converts nomadnetwork page variables from a string to a map
    # converts: "field1=123|field2=456"
    # to the following map:
    # - var_field1: 123
    # - var_field2: 456
    def archive_page(
        self,
        destination_hash: str,
        page_path: str,
        content: str,
        is_manual: bool = False,
        context=None,
    ):
        ctx = context or self.current_context
        if not ctx:
            return None
        return ctx.nomadnet_manager.archive_page(
            destination_hash,
            page_path,
            content,
            is_manual,
        )

    def get_archived_page_versions(self, destination_hash: str, page_path: str):
        return self.nomadnet_manager.get_archived_page_versions(
            destination_hash,
            page_path,
        )

    def flush_all_archived_pages(self):
        return self.nomadnet_manager.flush_all_archived_pages()

    # handle data received from websocket client
    async def on_websocket_data_received(self, client, data):
        # get type from client data
        if not isinstance(data, dict):
            return

        _type = data.get("type")
        if not _type:
            return

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

            try:
                await self.update_config(config)
                try:
                    AsyncUtils.run_async(self.send_config_to_websocket_clients())
                except Exception as e:
                    print(f"Failed to broadcast config update: {e}")
            except Exception:
                import traceback

                print("config.set failed:\n" + traceback.format_exc())

        # handle canceling a download
        elif _type == "nomadnet.download.cancel":
            # get data from websocket client
            download_id = data.get("download_id")
            if download_id is None:
                return

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
            destination_hash = data.get("destination_hash")
            page_path = data.get("page_path")

            if not destination_hash or not page_path:
                return

            # Try relative path first
            archives = self.get_archived_page_versions(destination_hash, page_path)

            # If nothing found and path doesn't look like it's already absolute,
            # try searching with the destination hash prefix (support for old buggy archives)
            if not archives and not page_path.startswith(destination_hash):
                buggy_path = f"{destination_hash}:{page_path}"
                archives = self.get_archived_page_versions(destination_hash, buggy_path)

            AsyncUtils.run_async(
                client.send_str(
                    json.dumps(
                        {
                            "type": "nomadnet.page.archives",
                            "destination_hash": destination_hash,
                            "page_path": page_path,
                            "archives": [
                                {
                                    "id": archive["id"],
                                    "hash": archive["hash"],
                                    "destination_hash": archive["destination_hash"],
                                    "page_path": archive["page_path"],
                                    "created_at": archive["created_at"].isoformat()
                                    if hasattr(archive["created_at"], "isoformat")
                                    else str(archive["created_at"]),
                                }
                                for archive in archives
                            ],
                        },
                    ),
                ),
            )

        # handle loading a specific archived page version
        elif _type == "nomadnet.page.archive.load":
            archive_id = data.get("archive_id")
            if archive_id is None:
                return

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
            destination_hash = data.get("destination_hash")
            page_path = data.get("page_path")
            content = data.get("content")

            if not destination_hash or not page_path or not content:
                return

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
            download_data = data.get("nomadnet_file_download")
            if not download_data:
                return

            destination_hash = download_data.get("destination_hash")
            file_path = download_data.get("file_path")

            if not destination_hash or not file_path:
                return

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
            page_download_data = data.get("nomadnet_page_download")
            if not page_download_data:
                return

            destination_hash = page_download_data.get("destination_hash")
            page_path = page_download_data.get("page_path")
            field_data = page_download_data.get("field_data")

            if not destination_hash or not page_path:
                return

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
                page_data = convert_nomadnet_string_data_to_map(page_path_parts[1])

            # Field data
            field_data = convert_nomadnet_field_data_to_map(field_data)

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
            rule_data = data.get("rule")
            if not rule_data or "forward_to_hash" not in rule_data:
                print(
                    "Missing rule data or forward_to_hash in lxmf.forwarding.rule.add",
                )
                return

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
            rule_id = data.get("id")
            if rule_id is not None:
                self.database.misc.delete_forwarding_rule(rule_id)
                # notify updated
                AsyncUtils.run_async(
                    self.on_websocket_data_received(
                        client,
                        {"type": "lxmf.forwarding.rules.get"},
                    ),
                )

        elif _type == "lxmf.forwarding.rule.toggle":
            rule_id = data.get("id")
            if rule_id is not None:
                self.database.misc.toggle_forwarding_rule(rule_id)
                # notify updated
                AsyncUtils.run_async(
                    self.on_websocket_data_received(
                        client,
                        {"type": "lxmf.forwarding.rules.get"},
                    ),
                )

        # handle ingesting an lxmf uri (paper message)
        elif _type == "lxm.ingest_uri":
            uri = data.get("uri")
            if not uri:
                return

            local_delivery_signal = "local_delivery_occurred"
            duplicate_signal = "duplicate_lxm"

            try:
                # ensure uri starts with lxmf:// or lxm://
                if not uri.lower().startswith(
                    LXMF.LXMessage.URI_SCHEMA + "://",
                ) and not uri.lower().startswith("lxm://"):
                    if ":" in uri and "//" not in uri:
                        uri = LXMF.LXMessage.URI_SCHEMA + "://" + uri
                    else:
                        uri = LXMF.LXMessage.URI_SCHEMA + "://" + uri

                ingest_result = self.message_router.ingest_lxm_uri(
                    uri,
                    signal_local_delivery=local_delivery_signal,
                    signal_duplicate=duplicate_signal,
                )

                if ingest_result is False:
                    response = "The URI contained no decodable messages"
                    status = "error"
                elif ingest_result == local_delivery_signal:
                    response = "Message was decoded, decrypted successfully, and added to your conversation list."
                    status = "success"
                elif ingest_result == duplicate_signal:
                    response = "The decoded message has already been processed by the LXMF Router, and will not be ingested again."
                    status = "info"
                else:
                    response = "The decoded message was not addressed to your LXMF address, and has been discarded."
                    status = "warning"

                AsyncUtils.run_async(
                    client.send_str(
                        json.dumps(
                            {
                                "type": "lxm.ingest_uri.result",
                                "status": status,
                                "message": response,
                            },
                        ),
                    ),
                )
            except Exception as e:
                AsyncUtils.run_async(
                    client.send_str(
                        json.dumps(
                            {
                                "type": "lxm.ingest_uri.result",
                                "status": "error",
                                "message": f"Error ingesting message from URI: {e!s}",
                            },
                        ),
                    ),
                )

        # handle generating a paper message uri
        elif _type == "lxm.generate_paper_uri":
            destination_hash = data.get("destination_hash")
            content = data.get("content")
            title = data.get("title", "")

            if not destination_hash or not content:
                return

            try:
                destination_hash_bytes = bytes.fromhex(destination_hash)
                destination_identity = RNS.Identity.recall(destination_hash_bytes)

                if destination_identity is None:
                    # try to find in database
                    announce = self.database.announces.get_announce_by_hash(
                        destination_hash,
                    )
                    if announce and announce.get("identity_public_key"):
                        destination_identity = RNS.Identity.from_bytes(
                            base64.b64decode(announce["identity_public_key"]),
                        )

                if destination_identity is None:
                    raise Exception(
                        "Recipient identity not found. Please wait for an announce or add them as a contact.",
                    )

                lxmf_destination = RNS.Destination(
                    destination_identity,
                    RNS.Destination.OUT,
                    RNS.Destination.SINGLE,
                    "lxmf",
                    "delivery",
                )

                lxm = LXMF.LXMessage(
                    lxmf_destination,
                    self.local_lxmf_destination,
                    content,
                    title=title,
                    desired_method=LXMF.LXMessage.PAPER,
                )

                # generate uri
                uri = lxm.as_uri()

                AsyncUtils.run_async(
                    client.send_str(
                        json.dumps(
                            {
                                "type": "lxm.generate_paper_uri.result",
                                "status": "success",
                                "uri": uri,
                            },
                        ),
                    ),
                )
            except Exception as e:
                AsyncUtils.run_async(
                    client.send_str(
                        json.dumps(
                            {
                                "type": "lxm.generate_paper_uri.result",
                                "status": "error",
                                "message": f"Error generating paper message: {e!s}",
                            },
                        ),
                    ),
                )

        # handle getting keyboard shortcuts
        elif _type == "keyboard_shortcuts.get":
            shortcuts = self.database.misc.get_keyboard_shortcuts(
                self.identity.hash.hex(),
            )
            AsyncUtils.run_async(
                client.send_str(
                    json.dumps(
                        {
                            "type": "keyboard_shortcuts",
                            "shortcuts": [
                                {
                                    "action": s["action"],
                                    "keys": json.loads(s["keys"]),
                                }
                                for s in shortcuts
                            ],
                        },
                    ),
                ),
            )

        # handle updating/upserting a keyboard shortcut
        elif _type == "keyboard_shortcuts.set":
            action = data["action"]
            keys = json.dumps(data["keys"])
            self.database.misc.upsert_keyboard_shortcut(
                self.identity.hash.hex(),
                action,
                keys,
            )
            # notify updated
            AsyncUtils.run_async(
                self.on_websocket_data_received(
                    client,
                    {"type": "keyboard_shortcuts.get"},
                ),
            )

        # handle deleting a keyboard shortcut
        elif _type == "keyboard_shortcuts.delete":
            action = data["action"]
            self.database.misc.delete_keyboard_shortcut(
                self.identity.hash.hex(),
                action,
            )
            # notify updated
            AsyncUtils.run_async(
                self.on_websocket_data_received(
                    client,
                    {"type": "keyboard_shortcuts.get"},
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
    async def send_config_to_websocket_clients(self, context=None):
        ctx = context or self.current_context
        if not ctx:
            return
        await self.websocket_broadcast(
            json.dumps(
                {
                    "type": "config",
                    "config": self.get_config_dict(context=ctx),
                },
            ),
        )

    # broadcasts to all websocket clients that we just announced
    async def send_announced_to_websocket_clients(self, context=None):
        ctx = context or self.current_context
        if not ctx:
            return
        await self.websocket_broadcast(
            json.dumps(
                {
                    "type": "announced",
                    "identity_hash": ctx.identity_hash,
                },
            ),
        )

    # returns a dictionary of config
    def get_config_dict(self, context=None):
        ctx = context or self.current_context
        if not ctx:
            return {}
        return {
            "display_name": ctx.config.display_name.get(),
            "identity_hash": ctx.identity.hash.hex(),
            "lxmf_address_hash": ctx.local_lxmf_destination.hexhash,
            "telephone_address_hash": ctx.telephone_manager.telephone.destination.hexhash
            if ctx.telephone_manager.telephone
            else None,
            "is_transport_enabled": (
                self.reticulum.transport_enabled()
                if hasattr(self, "reticulum") and self.reticulum
                else False
            ),
            "auto_announce_enabled": ctx.config.auto_announce_enabled.get(),
            "auto_announce_interval_seconds": ctx.config.auto_announce_interval_seconds.get(),
            "last_announced_at": ctx.config.last_announced_at.get(),
            "theme": ctx.config.theme.get(),
            "language": ctx.config.language.get(),
            "auto_resend_failed_messages_when_announce_received": ctx.config.auto_resend_failed_messages_when_announce_received.get(),
            "allow_auto_resending_failed_messages_with_attachments": ctx.config.allow_auto_resending_failed_messages_with_attachments.get(),
            "auto_send_failed_messages_to_propagation_node": ctx.config.auto_send_failed_messages_to_propagation_node.get(),
            "show_suggested_community_interfaces": ctx.config.show_suggested_community_interfaces.get(),
            "lxmf_local_propagation_node_enabled": ctx.config.lxmf_local_propagation_node_enabled.get(),
            "lxmf_local_propagation_node_address_hash": ctx.message_router.propagation_destination.hexhash,
            "lxmf_preferred_propagation_node_destination_hash": ctx.config.lxmf_preferred_propagation_node_destination_hash.get(),
            "lxmf_preferred_propagation_node_auto_select": ctx.config.lxmf_preferred_propagation_node_auto_select.get(),
            "lxmf_preferred_propagation_node_auto_sync_interval_seconds": ctx.config.lxmf_preferred_propagation_node_auto_sync_interval_seconds.get(),
            "lxmf_preferred_propagation_node_last_synced_at": ctx.config.lxmf_preferred_propagation_node_last_synced_at.get(),
            "lxmf_user_icon_name": ctx.config.lxmf_user_icon_name.get(),
            "lxmf_user_icon_foreground_colour": ctx.config.lxmf_user_icon_foreground_colour.get(),
            "lxmf_user_icon_background_colour": ctx.config.lxmf_user_icon_background_colour.get(),
            "lxmf_inbound_stamp_cost": ctx.config.lxmf_inbound_stamp_cost.get(),
            "lxmf_propagation_node_stamp_cost": ctx.config.lxmf_propagation_node_stamp_cost.get(),
            "page_archiver_enabled": ctx.config.page_archiver_enabled.get(),
            "page_archiver_max_versions": ctx.config.page_archiver_max_versions.get(),
            "archives_max_storage_gb": ctx.config.archives_max_storage_gb.get(),
            "backup_max_count": ctx.config.backup_max_count.get(),
            "crawler_enabled": ctx.config.crawler_enabled.get(),
            "crawler_max_retries": ctx.config.crawler_max_retries.get(),
            "crawler_retry_delay_seconds": ctx.config.crawler_retry_delay_seconds.get(),
            "crawler_max_concurrent": ctx.config.crawler_max_concurrent.get(),
            "auth_enabled": self.auth_enabled,
            "voicemail_enabled": ctx.config.voicemail_enabled.get(),
            "voicemail_greeting": ctx.config.voicemail_greeting.get(),
            "voicemail_auto_answer_delay_seconds": ctx.config.voicemail_auto_answer_delay_seconds.get(),
            "voicemail_max_recording_seconds": ctx.config.voicemail_max_recording_seconds.get(),
            "voicemail_tts_speed": ctx.config.voicemail_tts_speed.get(),
            "voicemail_tts_pitch": ctx.config.voicemail_tts_pitch.get(),
            "voicemail_tts_voice": ctx.config.voicemail_tts_voice.get(),
            "voicemail_tts_word_gap": ctx.config.voicemail_tts_word_gap.get(),
            "custom_ringtone_enabled": ctx.config.custom_ringtone_enabled.get(),
            "ringtone_filename": ctx.config.ringtone_filename.get(),
            "ringtone_preferred_id": ctx.config.ringtone_preferred_id.get(),
            "ringtone_volume": ctx.config.ringtone_volume.get(),
            "map_offline_enabled": ctx.config.map_offline_enabled.get(),
            "map_mbtiles_dir": ctx.config.map_mbtiles_dir.get(),
            "map_tile_cache_enabled": ctx.config.map_tile_cache_enabled.get(),
            "map_default_lat": ctx.config.map_default_lat.get(),
            "map_default_lon": ctx.config.map_default_lon.get(),
            "map_default_zoom": ctx.config.map_default_zoom.get(),
            "map_tile_server_url": ctx.config.map_tile_server_url.get(),
            "map_nominatim_api_url": ctx.config.map_nominatim_api_url.get(),
            "do_not_disturb_enabled": ctx.config.do_not_disturb_enabled.get(),
            "telephone_allow_calls_from_contacts_only": ctx.config.telephone_allow_calls_from_contacts_only.get(),
            "telephone_audio_profile_id": ctx.config.telephone_audio_profile_id.get(),
            "telephone_web_audio_enabled": ctx.config.telephone_web_audio_enabled.get(),
            "telephone_web_audio_allow_fallback": ctx.config.telephone_web_audio_allow_fallback.get(),
            "call_recording_enabled": ctx.config.call_recording_enabled.get(),
            "banished_effect_enabled": ctx.config.banished_effect_enabled.get(),
            "banished_text": ctx.config.banished_text.get(),
            "banished_color": ctx.config.banished_color.get(),
            "message_font_size": ctx.config.message_font_size.get(),
            "message_icon_size": ctx.config.message_icon_size.get(),
            "translator_enabled": ctx.config.translator_enabled.get(),
            "libretranslate_url": ctx.config.libretranslate_url.get(),
            "desktop_open_calls_in_separate_window": ctx.config.desktop_open_calls_in_separate_window.get(),
            "desktop_hardware_acceleration_enabled": ctx.config.desktop_hardware_acceleration_enabled.get(),
            "blackhole_integration_enabled": ctx.config.blackhole_integration_enabled.get(),
            "csp_extra_connect_src": ctx.config.csp_extra_connect_src.get(),
            "csp_extra_img_src": ctx.config.csp_extra_img_src.get(),
            "csp_extra_frame_src": ctx.config.csp_extra_frame_src.get(),
            "csp_extra_script_src": ctx.config.csp_extra_script_src.get(),
            "csp_extra_style_src": ctx.config.csp_extra_style_src.get(),
            "telephone_tone_generator_enabled": ctx.config.telephone_tone_generator_enabled.get(),
            "telephone_tone_generator_volume": ctx.config.telephone_tone_generator_volume.get(),
            "location_source": ctx.config.location_source.get(),
            "location_manual_lat": ctx.config.location_manual_lat.get(),
            "location_manual_lon": ctx.config.location_manual_lon.get(),
            "location_manual_alt": ctx.config.location_manual_alt.get(),
            "telemetry_enabled": ctx.config.telemetry_enabled.get(),
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
                        lxmf_name = parse_lxmf_display_name(
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

    def get_lxst_telephony_hash_for_identity_hash(self, identity_hash: str):
        # Primary: use announces table for lxst.telephony aspect
        announces = self.database.announces.get_filtered_announces(
            aspect="lxst.telephony",
            search_term=identity_hash,
        )
        if announces:
            for announce in announces:
                if announce["identity_hash"] == identity_hash:
                    return announce.get("destination_hash")

        # Fallback: derive from identity if available (same identity, different aspect)
        identity = self.recall_identity(identity_hash)
        if identity is not None:
            try:
                return RNS.Destination.hash(identity, "lxst", "telephony").hex()
            except Exception:
                return None
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

    # convert database announce to a dictionary
    def convert_db_announce_to_dict(self, announce):
        # convert to dict if it's a sqlite3.Row
        if not isinstance(announce, dict):
            announce = dict(announce)

        # parse display name from announce
        display_name = None
        if announce["aspect"] == "lxmf.delivery":
            display_name = parse_lxmf_display_name(announce["app_data"])
        elif announce["aspect"] == "nomadnetwork.node":
            display_name = parse_nomadnetwork_node_display_name(
                announce["app_data"],
            )
        elif announce["aspect"] == "lxst.telephony":
            display_name = parse_lxmf_display_name(announce["app_data"])

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
                            display_name = parse_lxmf_display_name(
                                lxmf_a["app_data"],
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
                        try:
                            lxmf_destination_hash = RNS.Destination.hash(
                                identity,
                                "lxmf",
                                "delivery",
                            ).hex()
                        except Exception:  # noqa: S110
                            pass
                except Exception:  # noqa: S110
                    pass

        # find lxmf user icon from database
        lxmf_user_icon = None
        # Try multiple potential hashes for the icon
        icon_hashes_to_check = []
        if lxmf_destination_hash:
            icon_hashes_to_check.append(lxmf_destination_hash)
        icon_hashes_to_check.append(announce["destination_hash"])

        # ensure we don't return the user's own icon for peers
        local_hash = None
        if self.current_context and self.current_context.local_lxmf_destination:
            local_hash = self.current_context.local_lxmf_destination.hexhash

        db_lxmf_user_icon = None
        for icon_hash in icon_hashes_to_check:
            # skip if this is the user's own hash - don't return user's icon for peers
            if local_hash and icon_hash == local_hash:
                continue
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

    # convert database lxmf message to a dictionary
    # updates the lxmf user icon for the provided destination hash
    def update_lxmf_user_icon(
        self,
        destination_hash: str,
        icon_name: str,
        foreground_colour: str,
        background_colour: str,
        context=None,
    ):
        ctx = context or self.current_context
        if not ctx:
            return

        # ensure we're not storing the user's own icon with a peer's hash
        # only store icons for remote peers, not for the local user
        if (
            ctx.local_lxmf_destination
            and destination_hash == ctx.local_lxmf_destination.hexhash
        ):
            print(f"skipping icon update for local user's own hash: {destination_hash}")
            return

        # log
        print(
            f"updating lxmf user icon for {destination_hash} to icon_name={icon_name}, foreground_colour={foreground_colour}, background_colour={background_colour}",
        )

        ctx.database.misc.update_lxmf_user_icon(
            destination_hash,
            icon_name,
            foreground_colour,
            background_colour,
        )

    # check if a destination is blocked
    def is_destination_blocked(self, destination_hash: str, context=None) -> bool:
        ctx = context or self.current_context
        if not ctx or not ctx.database:
            return False
        try:
            return ctx.database.misc.is_destination_blocked(destination_hash)
        except Exception:
            return False

    # check if message content matches spam keywords
    def check_spam_keywords(self, title: str, content: str, context=None) -> bool:
        ctx = context or self.current_context
        if not ctx or not ctx.database:
            return False
        try:
            return ctx.database.misc.check_spam_keywords(title, content)
        except Exception:
            return False

    # check if message has attachments and should be rejected

    # handle an lxmf delivery from reticulum
    # NOTE: cant be async, as Reticulum doesn't await it
    def on_lxmf_delivery(self, lxmf_message: LXMF.LXMessage, context=None):
        ctx = context or self.current_context
        if not ctx or not ctx.running or not ctx.database:
            return

        try:
            source_hash = lxmf_message.source_hash.hex()

            # check if source is blocked - reject immediately
            if self.is_destination_blocked(source_hash, context=ctx):
                print(f"Rejecting LXMF message from blocked source: {source_hash}")
                return

            is_sideband_telemetry_request = False
            lxmf_fields = lxmf_message.get_fields()

            # check both standard LXMF.FIELD_COMMANDS (9) and FIELD_COMMANDS (1)
            commands = []
            if LXMF.FIELD_COMMANDS in lxmf_fields:
                val = lxmf_fields[LXMF.FIELD_COMMANDS]
                if isinstance(val, list):
                    commands.extend(val)
                elif isinstance(val, dict):
                    commands.append(val)
            if 0x01 in lxmf_fields and LXMF.FIELD_COMMANDS != 0x01:
                val = lxmf_fields[0x01]
                if isinstance(val, list):
                    commands.extend(val)
                elif isinstance(val, dict):
                    commands.append(val)

            if commands:
                for command in commands:
                    if (
                        (
                            isinstance(command, dict)
                            and (
                                SidebandCommands.TELEMETRY_REQUEST in command
                                or str(SidebandCommands.TELEMETRY_REQUEST) in command
                                or f"0x{SidebandCommands.TELEMETRY_REQUEST:02x}"
                                in command
                            )
                        )
                        or (
                            isinstance(command, (list, tuple))
                            and SidebandCommands.TELEMETRY_REQUEST in command
                        )
                        or command == SidebandCommands.TELEMETRY_REQUEST
                        or str(command) == str(SidebandCommands.TELEMETRY_REQUEST)
                    ):
                        is_sideband_telemetry_request = True

            # respond to telemetry requests
            if is_sideband_telemetry_request:
                # Check if telemetry is enabled globally
                if not ctx.config.telemetry_enabled.get():
                    print(f"Telemetry is disabled, ignoring request from {source_hash}")
                else:
                    # Check if peer is trusted
                    contact = ctx.database.contacts.get_contact_by_identity_hash(
                        source_hash,
                    )
                    if not contact or not contact.get("is_telemetry_trusted"):
                        print(
                            f"Telemetry request from untrusted peer {source_hash}, ignoring",
                        )
                    else:
                        print(f"Responding to telemetry request from {source_hash}")
                        self.handle_telemetry_request(source_hash)

                self.db_upsert_lxmf_message(lxmf_message, context=ctx)

                # broadcast notification
                AsyncUtils.run_async(
                    self.websocket_broadcast(
                        json.dumps(
                            {
                                "type": "lxmf.delivery",
                                "remote_identity_name": source_hash[:8],
                                "lxmf_message": convert_db_lxmf_message_to_dict(
                                    ctx.database.messages.get_lxmf_message_by_hash(
                                        lxmf_message.hash.hex(),
                                    ),
                                    include_attachments=False,
                                ),
                            },
                        ),
                    ),
                )
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
            if has_attachments(lxmf_fields):
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
            self.db_upsert_lxmf_message(lxmf_message, is_spam=is_spam, context=ctx)

            # handle forwarding
            self.handle_forwarding(lxmf_message, context=ctx)

            # handle telemetry
            try:
                message_fields = lxmf_message.get_fields()

                # Single telemetry entry
                if LXMF.FIELD_TELEMETRY in message_fields:
                    self.process_incoming_telemetry(
                        source_hash,
                        message_fields[LXMF.FIELD_TELEMETRY],
                        lxmf_message,
                        context=ctx,
                    )

                # Telemetry stream (multiple entries)
                if (
                    hasattr(LXMF, "FIELD_TELEMETRY_STREAM")
                    and LXMF.FIELD_TELEMETRY_STREAM in message_fields
                ):
                    stream = message_fields[LXMF.FIELD_TELEMETRY_STREAM]
                    if isinstance(stream, (list, tuple)):
                        for entry in stream:
                            if isinstance(entry, (list, tuple)) and len(entry) >= 3:
                                entry_source = (
                                    entry[0].hex()
                                    if isinstance(entry[0], bytes)
                                    else entry[0]
                                )
                                entry_timestamp = entry[1]
                                entry_data = entry[2]
                                self.process_incoming_telemetry(
                                    entry_source,
                                    entry_data,
                                    lxmf_message,
                                    timestamp_override=entry_timestamp,
                                    context=ctx,
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

                    local_hash = (
                        ctx.local_lxmf_destination.hexhash
                        if ctx.local_lxmf_destination
                        else None
                    )
                    source_hash = lxmf_message.source_hash.hex()

                    # ignore our own icon and empty payloads to avoid overwriting peers with our appearance
                    if (source_hash and local_hash and source_hash == local_hash) or (
                        not icon_name or not foreground_colour or not background_colour
                    ):
                        pass
                    else:
                        local_icon_name = ctx.config.lxmf_user_icon_name.get()
                        local_icon_fg = (
                            ctx.config.lxmf_user_icon_foreground_colour.get()
                        )
                        local_icon_bg = (
                            ctx.config.lxmf_user_icon_background_colour.get()
                        )

                        # if incoming icon matches our own, skip storing and clear any mistaken stored copy
                        # for now, but this will need to be updated later if two users do have the same icon
                        # FIXME
                        if (
                            local_icon_name
                            and local_icon_fg
                            and local_icon_bg
                            and icon_name == local_icon_name
                            and foreground_colour == local_icon_fg
                            and background_colour == local_icon_bg
                        ):
                            ctx.database.misc.delete_user_icon(source_hash)
                        else:
                            self.update_lxmf_user_icon(
                                source_hash,
                                icon_name,
                                foreground_colour,
                                background_colour,
                                context=ctx,
                            )
            except Exception as e:
                print("failed to update lxmf user icon from lxmf message")
                print(e)

            # find message from database
            db_lxmf_message = ctx.database.messages.get_lxmf_message_by_hash(
                lxmf_message.hash.hex(),
            )
            if not db_lxmf_message:
                return

            # get sender name for notification
            sender_name = ctx.database.announces.get_custom_display_name(source_hash)
            if not sender_name:
                announce = ctx.database.announces.get_announce_by_hash(source_hash)
                if announce and announce["app_data"]:
                    sender_name = parse_lxmf_display_name(
                        app_data_base64=announce["app_data"],
                        default_value=None,
                    )

            if not sender_name:
                sender_name = source_hash[:8]

            # send received lxmf message data to all websocket clients
            AsyncUtils.run_async(
                self.websocket_broadcast(
                    json.dumps(
                        {
                            "type": "lxmf.delivery",
                            "remote_identity_name": sender_name,
                            "lxmf_message": convert_db_lxmf_message_to_dict(
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
    def handle_forwarding(self, lxmf_message: LXMF.LXMessage, context=None):
        try:
            ctx = context or self.current_context
            if not ctx:
                return

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
                attachments = [
                    LxmfFileAttachment(val[0], val[1])
                    for val in lxmf_fields[LXMF.FIELD_FILE_ATTACHMENTS]
                ]
                file_attachments_field = LxmfFileAttachmentsField(attachments)

            # check if this message is for an alias identity (REPLY PATH)
            mapping = ctx.database.messages.get_forwarding_mapping(
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
                        context=ctx,
                    ),
                )
                return

            # check if this message matches a forwarding rule (FORWARD PATH)
            # we check for rules that apply to the destination of this message
            rules = ctx.database.misc.get_forwarding_rules(
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
                mapping = ctx.forwarding_manager.get_or_create_mapping(
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
                        context=ctx,
                    ),
                )
        except Exception as e:
            print(f"Error in handle_forwarding: {e}")
            import traceback

            traceback.print_exc()

    # handle delivery status update for an outbound lxmf message
    def on_lxmf_sending_state_updated(self, lxmf_message, context=None):
        # upsert lxmf message to database
        self.db_upsert_lxmf_message(lxmf_message, context=context)

        # send lxmf message state to all websocket clients
        AsyncUtils.run_async(
            self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "lxmf_message_state_updated",
                        "lxmf_message": convert_lxmf_message_to_dict(
                            lxmf_message,
                            include_attachments=False,
                            reticulum=self.reticulum,
                        ),
                    },
                ),
            ),
        )

    # handle delivery failed for an outbound lxmf message
    def on_lxmf_sending_failed(self, lxmf_message, context=None):
        # check if this failed message should fall back to sending via a propagation node
        if (
            lxmf_message.state == LXMF.LXMessage.FAILED
            and hasattr(lxmf_message, "try_propagation_on_fail")
            and lxmf_message.try_propagation_on_fail
        ):
            self.send_failed_message_via_propagation_node(lxmf_message, context=context)

        # update state
        self.on_lxmf_sending_state_updated(lxmf_message)

    # sends a previously failed message via a propagation node
    def send_failed_message_via_propagation_node(
        self,
        lxmf_message: LXMF.LXMessage,
        context=None,
    ):
        ctx = context or self.current_context
        if not ctx:
            return

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
        router = ctx.message_router
        if (
            ctx.forwarding_manager
            and source_hash in ctx.forwarding_manager.forwarding_routers
        ):
            router = ctx.forwarding_manager.forwarding_routers[source_hash]
        router.handle_outbound(lxmf_message)

    # upserts the provided lxmf message to the database
    def db_upsert_lxmf_message(
        self,
        lxmf_message: LXMF.LXMessage,
        is_spam: bool = False,
        context=None,
    ):
        ctx = context or self.current_context
        if not ctx:
            return

        # convert lxmf message to dict
        lxmf_message_dict = convert_lxmf_message_to_dict(
            lxmf_message,
            reticulum=self.reticulum,
        )
        lxmf_message_dict["is_spam"] = 1 if is_spam else 0

        # calculate peer hash
        local_hash = ctx.local_lxmf_destination.hexhash
        if lxmf_message_dict["source_hash"] == local_hash:
            lxmf_message_dict["peer_hash"] = lxmf_message_dict["destination_hash"]
        else:
            lxmf_message_dict["peer_hash"] = lxmf_message_dict["source_hash"]

        ctx.database.messages.upsert_lxmf_message(lxmf_message_dict)

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
        context=None,
    ) -> LXMF.LXMessage:
        ctx = context or self.current_context
        if not ctx:
            raise RuntimeError("No identity context available for sending message")

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
                not ctx.message_router.delivery_link_available(destination_hash_bytes)
                and RNS.Identity.current_ratchet_id(destination_hash_bytes) is not None
            ):
                # since there's no link established to the destination, it's faster to send opportunistically
                # this is because it takes several packets to establish a link, and then we still have to send the message over it
                # oppotunistic mode will send the message in a single packet (if the message is small enough, otherwise it falls back to a direct link)
                # we will only do this if an encryption ratchet is available, so single packet delivery is more secure
                desired_delivery_method = LXMF.LXMessage.OPPORTUNISTIC

        # determine which identity to send from
        source_destination = ctx.local_lxmf_destination
        if sender_identity_hash is not None:
            if (
                ctx.forwarding_manager
                and sender_identity_hash
                in ctx.forwarding_manager.forwarding_destinations
            ):
                source_destination = ctx.forwarding_manager.forwarding_destinations[
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
            ctx.config.auto_send_failed_messages_to_propagation_node.get()
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

        # add icon appearance if configured and not already sent to this destination
        current_icon_hash = self.get_current_icon_hash()
        if current_icon_hash is not None:
            last_sent_icon_hash = self.database.misc.get_last_sent_icon_hash(
                destination_hash,
            )

            if last_sent_icon_hash != current_icon_hash:
                lxmf_user_icon_name = self.config.lxmf_user_icon_name.get()
                lxmf_user_icon_foreground_colour = (
                    self.config.lxmf_user_icon_foreground_colour.get()
                )
                lxmf_user_icon_background_colour = (
                    self.config.lxmf_user_icon_background_colour.get()
                )

                lxmf_message.fields[LXMF.FIELD_ICON_APPEARANCE] = [
                    lxmf_user_icon_name,
                    ColourUtils.hex_colour_to_byte_array(
                        lxmf_user_icon_foreground_colour,
                    ),
                    ColourUtils.hex_colour_to_byte_array(
                        lxmf_user_icon_background_colour,
                    ),
                ]

                # update last sent icon hash for this destination
                ctx.database.misc.update_last_sent_icon_hash(
                    destination_hash,
                    current_icon_hash,
                )

        # register delivery callbacks
        lxmf_message.register_delivery_callback(
            lambda msg: self.on_lxmf_sending_state_updated(msg, context=ctx),
        )
        lxmf_message.register_failed_callback(
            lambda msg: self.on_lxmf_sending_failed(msg, context=ctx),
        )

        # determine which router to use
        router = ctx.message_router
        if (
            sender_identity_hash is not None
            and ctx.forwarding_manager
            and sender_identity_hash in ctx.forwarding_manager.forwarding_routers
        ):
            router = ctx.forwarding_manager.forwarding_routers[sender_identity_hash]

        # send lxmf message to be routed to destination
        router.handle_outbound(lxmf_message)

        # upsert lxmf message to database
        if not no_display:
            self.db_upsert_lxmf_message(lxmf_message, context=ctx)

        # tell all websocket clients that old failed message was deleted so it can remove from ui
        if not no_display:
            await self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "lxmf_message_created",
                        "lxmf_message": convert_lxmf_message_to_dict(
                            lxmf_message,
                            include_attachments=False,
                            reticulum=self.reticulum,
                        ),
                    },
                ),
            )

        # handle lxmf message progress loop without blocking or awaiting
        # otherwise other incoming websocket packets will not be processed until sending is complete
        # which results in the next message not showing up until the first message is finished
        if not no_display:
            AsyncUtils.run_async(
                self.handle_lxmf_message_progress(lxmf_message, context=ctx),
            )

        return lxmf_message

    # get hash of current icon appearance configuration
    def get_current_icon_hash(self, context=None):
        ctx = context or self.current_context
        if not ctx:
            return None

        name = ctx.config.lxmf_user_icon_name.get()
        fg = ctx.config.lxmf_user_icon_foreground_colour.get()
        bg = ctx.config.lxmf_user_icon_background_colour.get()

        if not all([name, fg, bg]):
            return None

        data = f"{name}|{fg}|{bg}"
        return hashlib.sha256(data.encode()).hexdigest()

    def process_incoming_telemetry(
        self,
        source_hash,
        telemetry_data,
        lxmf_message,
        timestamp_override=None,
        context=None,
    ):
        ctx = context or self.current_context
        if not ctx:
            return

        try:
            unpacked = Telemeter.from_packed(telemetry_data)
            if unpacked:
                timestamp = timestamp_override or (
                    unpacked["time"]["utc"] if "time" in unpacked else int(time.time())
                )

                # physical link info
                physical_link = {
                    "rssi": self.reticulum.get_packet_rssi(lxmf_message.hash)
                    if hasattr(self, "reticulum") and self.reticulum
                    else None,
                    "snr": self.reticulum.get_packet_snr(lxmf_message.hash)
                    if hasattr(self, "reticulum") and self.reticulum
                    else None,
                    "q": self.reticulum.get_packet_q(lxmf_message.hash)
                    if hasattr(self, "reticulum") and self.reticulum
                    else None,
                }

                ctx.database.telemetry.upsert_telemetry(
                    destination_hash=source_hash,
                    timestamp=timestamp,
                    data=telemetry_data,
                    received_from=ctx.local_lxmf_destination.hexhash,
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
                                "physical_link": physical_link,
                                "is_tracking": ctx.database.telemetry.is_tracking(
                                    source_hash,
                                ),
                            },
                        ),
                    ),
                )
        except Exception as e:
            print(f"Error processing incoming telemetry: {e}")

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

            AsyncUtils.run_async(
                self.send_message(
                    destination_hash=to_addr_hash,
                    content="",
                    telemetry_data=telemetry_data,
                    delivery_method="opportunistic",
                    no_display=False,
                ),
            )
        except Exception as e:
            print(f"Failed to respond to telemetry request: {e}")

    # updates lxmf message in database and broadcasts to websocket until it's delivered, or it fails
    async def handle_lxmf_message_progress(self, lxmf_message, context=None):
        # FIXME: there's no register_progress_callback on the lxmf message, so manually send progress until delivered, propagated or failed
        # we also can't use on_lxmf_sending_state_updated method to do this, because of async/await issues...
        ctx = context or self.current_context
        if not ctx:
            return

        should_update_message = True
        while should_update_message:
            # wait 1 second between sending updates
            await asyncio.sleep(1)

            # upsert lxmf message to database (as we want to update the progress in database too)
            self.db_upsert_lxmf_message(lxmf_message, context=ctx)

            # send update to websocket clients
            await self.websocket_broadcast(
                json.dumps(
                    {
                        "type": "lxmf_message_state_updated",
                        "lxmf_message": convert_lxmf_message_to_dict(
                            lxmf_message,
                            include_attachments=False,
                            reticulum=self.reticulum,
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
        context=None,
    ):
        ctx = context or self.current_context
        if not ctx or not ctx.running or not ctx.announce_manager or not ctx.database:
            return
        # check if source is blocked - drop announce and path if blocked
        identity_hash = announced_identity.hash.hex()
        if self.is_destination_blocked(identity_hash, context=ctx):
            print(f"Dropping telephone announce from blocked source: {identity_hash}")
            if hasattr(self, "reticulum") and self.reticulum:
                self.reticulum.drop_path(destination_hash)
            return

        # log received announce
        print(
            "Received an announce from "
            + RNS.prettyhexrep(destination_hash)
            + " for [lxst.telephony]"
            + (
                f" ({display_name})"
                if (
                    display_name := parse_lxmf_display_name(
                        app_data,
                        None,
                    )
                )
                else ""
            ),
        )

        # track announce timestamp
        self.announce_timestamps.append(time.time())

        # upsert announce to database
        ctx.announce_manager.upsert_announce(
            self.reticulum,
            announced_identity,
            destination_hash,
            aspect,
            app_data,
            announce_packet_hash,
        )

        # find announce from database
        announce = ctx.database.announces.get_announce_by_hash(destination_hash.hex())
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
        context=None,
    ):
        ctx = context or self.current_context
        if not ctx or not ctx.running or not ctx.announce_manager or not ctx.database:
            return

        # check if announced identity or its hash is missing
        if not announced_identity or not announced_identity.hash:
            print(
                f"Dropping announce with missing identity or hash: {RNS.prettyhexrep(destination_hash)}",
            )
            return

        # check if source is blocked - drop announce and path if blocked
        identity_hash = announced_identity.hash.hex()
        if self.is_destination_blocked(identity_hash, context=ctx):
            print(f"Dropping announce from blocked source: {identity_hash}")
            if hasattr(self, "reticulum") and self.reticulum:
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
        ctx.announce_manager.upsert_announce(
            self.reticulum,
            announced_identity,
            destination_hash,
            aspect,
            app_data,
            announce_packet_hash,
        )

        # find announce from database
        announce = ctx.database.announces.get_announce_by_hash(destination_hash.hex())
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
        if ctx.config.auto_resend_failed_messages_when_announce_received.get():
            AsyncUtils.run_async(
                self.resend_failed_messages_for_destination(
                    destination_hash.hex(),
                    context=ctx,
                ),
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
        context=None,
    ):
        ctx = context or self.current_context
        if not ctx or not ctx.running or not ctx.announce_manager or not ctx.database:
            return

        # log received announce
        print(
            "Received an announce from "
            + RNS.prettyhexrep(destination_hash)
            + " for [lxmf.propagation]",
        )

        # track announce timestamp
        self.announce_timestamps.append(time.time())

        # upsert announce to database
        ctx.announce_manager.upsert_announce(
            self.reticulum,
            announced_identity,
            destination_hash,
            aspect,
            app_data,
            announce_packet_hash,
        )

        # find announce from database
        announce = ctx.database.announces.get_announce_by_hash(destination_hash.hex())
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
    async def resend_failed_messages_for_destination(
        self,
        destination_hash: str,
        context=None,
    ):
        ctx = context or self.current_context
        if not ctx:
            return

        # get messages that failed to send to this destination
        failed_messages = ctx.database.messages.get_failed_messages_for_destination(
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
                if not ctx.config.allow_auto_resending_failed_messages_with_attachments.get():
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
                    context=ctx,
                )

                # remove original failed message from database
                ctx.database.messages.delete_lxmf_message_by_hash(
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
        context=None,
    ):
        ctx = context or self.current_context
        if not ctx or not ctx.running or not ctx.announce_manager or not ctx.database:
            return

        # check if source is blocked - drop announce and path if blocked
        identity_hash = announced_identity.hash.hex()
        if self.is_destination_blocked(identity_hash, context=ctx):
            print(f"Dropping announce from blocked source: {identity_hash}")
            if hasattr(self, "reticulum") and self.reticulum:
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
        ctx.announce_manager.upsert_announce(
            self.reticulum,
            announced_identity,
            destination_hash,
            aspect,
            app_data,
            announce_packet_hash,
        )

        # find announce from database
        announce = ctx.database.announces.get_announce_by_hash(destination_hash.hex())
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
    def queue_crawler_task(self, destination_hash: str, page_path: str, context=None):
        ctx = context or self.current_context
        if not ctx:
            return
        ctx.database.misc.upsert_crawl_task(destination_hash, page_path)

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
        # Optimized to fetch only the needed announce
        lxmf_announce = self.database.announces.get_announce_by_hash(destination_hash)

        # if app data is available in database, it should be base64 encoded text that was announced
        # we will return the parsed lxmf display name as the conversation name
        if lxmf_announce is not None and lxmf_announce["app_data"] is not None:
            return parse_lxmf_display_name(
                app_data_base64=lxmf_announce["app_data"],
            )

        # announce did not have app data, so provide a fallback name
        return default_name

    # reads the lxmf display name from the provided base64 app data

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


def env_bool(env_name, default=False):
    val = os.environ.get(env_name)
    if val is None:
        return default
    return val.lower() in ("true", "1", "yes", "on")


# class to manage config stored in database
# FIXME: we should probably set this as an instance variable of ReticulumMeshChat so it has a proper home, and pass it in to the constructor?
def main():
    # apply asyncio 3.13 patch if needed
    AsyncUtils.apply_asyncio_313_patch()

    # Initialize crash recovery system early to catch startup errors
    recovery = CrashRecovery()
    recovery.install()

    parser = argparse.ArgumentParser(description="ReticulumMeshChat")
    parser.add_argument(
        "--host",
        nargs="?",
        default=os.environ.get("MESHCHAT_HOST", "127.0.0.1"),
        type=str,
        help="The address the web server should listen on. Can also be set via MESHCHAT_HOST environment variable.",
    )
    parser.add_argument(
        "--port",
        nargs="?",
        default=int(os.environ.get("MESHCHAT_PORT", "8000")),
        type=int,
        help="The port the web server should listen on. Can also be set via MESHCHAT_PORT environment variable.",
    )
    # If we are running from a frozen application (AppImage, EXE, etc),
    # we should default to headless mode unless explicitly requested.
    is_frozen = getattr(sys, "frozen", False)
    default_headless = env_bool("MESHCHAT_HEADLESS", is_frozen)

    parser.add_argument(
        "--headless",
        action="store_true",
        default=default_headless,
        help="Web browser will not automatically launch when this flag is passed. Can also be set via MESHCHAT_HEADLESS environment variable.",
    )
    parser.add_argument(
        "--identity-file",
        type=str,
        default=os.environ.get("MESHCHAT_IDENTITY_FILE"),
        help="Path to a Reticulum Identity file to use as your LXMF address. Can also be set via MESHCHAT_IDENTITY_FILE environment variable.",
    )
    parser.add_argument(
        "--identity-base64",
        type=str,
        default=os.environ.get("MESHCHAT_IDENTITY_BASE64"),
        help="A base64 encoded Reticulum Identity to use as your LXMF address. Can also be set via MESHCHAT_IDENTITY_BASE64 environment variable.",
    )
    parser.add_argument(
        "--identity-base32",
        type=str,
        default=os.environ.get("MESHCHAT_IDENTITY_BASE32"),
        help="A base32 encoded Reticulum Identity to use as your LXMF address. Can also be set via MESHCHAT_IDENTITY_BASE32 environment variable.",
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
        default=env_bool("MESHCHAT_AUTO_RECOVER", False),
        help="Attempt to automatically recover the SQLite database on startup before serving the app. Can also be set via MESHCHAT_AUTO_RECOVER environment variable.",
    )
    parser.add_argument(
        "--auth",
        action="store_true",
        default=env_bool("MESHCHAT_AUTH", False),
        help="Enable basic authentication for the web interface. Can also be set via MESHCHAT_AUTH environment variable.",
    )
    parser.add_argument(
        "--no-https",
        action="store_true",
        default=env_bool("MESHCHAT_NO_HTTPS", False),
        help="Disable HTTPS and use HTTP instead. Can also be set via MESHCHAT_NO_HTTPS environment variable.",
    )
    parser.add_argument(
        "--no-crash-recovery",
        action="store_true",
        default=env_bool("MESHCHAT_NO_CRASH_RECOVERY", False),
        help="Disable the crash recovery and diagnostic system. Can also be set via MESHCHAT_NO_CRASH_RECOVERY environment variable.",
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
        default=os.environ.get("MESHCHAT_RETICULUM_CONFIG_DIR"),
        help="Path to a Reticulum config directory for the RNS stack to use (e.g: ~/.reticulum). Can also be set via MESHCHAT_RETICULUM_CONFIG_DIR environment variable.",
    )
    parser.add_argument(
        "--storage-dir",
        type=str,
        default=os.environ.get("MESHCHAT_STORAGE_DIR"),
        help="Path to a directory for storing databases and config files (default: ./storage). Can also be set via MESHCHAT_STORAGE_DIR environment variable.",
    )
    parser.add_argument(
        "--public-dir",
        type=str,
        default=os.environ.get("MESHCHAT_PUBLIC_DIR"),
        help="Path to the directory containing the frontend static files (default: bundled public folder). Can also be set via MESHCHAT_PUBLIC_DIR environment variable.",
    )
    parser.add_argument(
        "--gitea-base-url",
        type=str,
        default=os.environ.get("MESHCHAT_GITEA_BASE_URL"),
        help="Base URL for Gitea instance (default: https://git.quad4.io). Can also be set via MESHCHAT_GITEA_BASE_URL environment variable.",
    )
    parser.add_argument(
        "--docs-download-urls",
        type=str,
        default=os.environ.get("MESHCHAT_DOCS_DOWNLOAD_URLS"),
        help="Comma-separated list of URLs to download documentation from. Can also be set via MESHCHAT_DOCS_DOWNLOAD_URLS environment variable.",
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
    parser.add_argument(
        "--emergency",
        action="store_true",
        help="Start in emergency mode (no database, LXMF and peer announces only). Can also be set via MESHCHAT_EMERGENCY environment variable.",
        default=env_bool("MESHCHAT_EMERGENCY", False),
    )

    parser.add_argument(
        "--restore-from-snapshot",
        type=str,
        help="Restore the database from a specific snapshot name or path on startup.",
        default=os.environ.get("MESHCHAT_RESTORE_SNAPSHOT"),
    )

    args = parser.parse_args()

    # Disable crash recovery if requested via flag
    if args.no_crash_recovery:
        recovery.disable()

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
        public_dir=args.public_dir,
        emergency=args.emergency,
        gitea_base_url=args.gitea_base_url,
        docs_download_urls=args.docs_download_urls,
    )

    # update recovery with known paths
    recovery.update_paths(
        storage_dir=reticulum_meshchat.storage_dir,
        database_path=reticulum_meshchat.database_path,
        public_dir=reticulum_meshchat.public_dir_override or get_file_path("public"),
        reticulum_config_dir=reticulum_meshchat.reticulum_config_dir,
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

    if args.restore_from_snapshot:
        snapshot_path = args.restore_from_snapshot
        if not os.path.exists(snapshot_path):
            # Try in storage_dir/snapshots
            potential_path = os.path.join(
                reticulum_meshchat.storage_dir,
                "snapshots",
                snapshot_path,
            )
            if os.path.exists(potential_path):
                snapshot_path = potential_path
            elif os.path.exists(potential_path + ".zip"):
                snapshot_path = potential_path + ".zip"

        if os.path.exists(snapshot_path):
            print(f"Restoring database from snapshot: {snapshot_path}")
            result = reticulum_meshchat.restore_database(snapshot_path)
            print(
                f"Snapshot restoration complete. Integrity check: {result['integrity_check']}",
            )
        else:
            print(f"Error: Snapshot not found at {snapshot_path}")

    enable_https = not args.no_https
    reticulum_meshchat.run(
        args.host,
        args.port,
        launch_browser=args.headless is False,
        enable_https=enable_https,
    )


if __name__ == "__main__":
    main()
