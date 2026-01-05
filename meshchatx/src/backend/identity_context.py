import os
import asyncio
import threading
import RNS
from meshchatx.src.backend.database import Database
from meshchatx.src.backend.integrity_manager import IntegrityManager
from meshchatx.src.backend.config_manager import ConfigManager
from meshchatx.src.backend.message_handler import MessageHandler
from meshchatx.src.backend.announce_manager import AnnounceManager
from meshchatx.src.backend.archiver_manager import ArchiverManager
from meshchatx.src.backend.map_manager import MapManager
from meshchatx.src.backend.docs_manager import DocsManager
from meshchatx.src.backend.nomadnet_utils import NomadNetworkManager
from meshchatx.src.backend.telephone_manager import TelephoneManager
from meshchatx.src.backend.voicemail_manager import VoicemailManager
from meshchatx.src.backend.ringtone_manager import RingtoneManager
from meshchatx.src.backend.rncp_handler import RNCPHandler
from meshchatx.src.backend.rnstatus_handler import RNStatusHandler
from meshchatx.src.backend.rnpath_handler import RNPathHandler
from meshchatx.src.backend.rnprobe_handler import RNProbeHandler
from meshchatx.src.backend.translator_handler import TranslatorHandler
from meshchatx.src.backend.forwarding_manager import ForwardingManager
from meshchatx.src.backend.meshchat_utils import create_lxmf_router
from meshchatx.src.backend.announce_handler import AnnounceHandler
from meshchatx.src.backend.community_interfaces import CommunityInterfacesManager


class IdentityContext:
    def __init__(self, identity: RNS.Identity, app):
        self.identity = identity
        self.app = app
        self.identity_hash = identity.hash.hex()

        # Storage paths
        self.storage_path = os.path.join(
            app.storage_dir,
            "identities",
            self.identity_hash,
        )
        os.makedirs(self.storage_path, exist_ok=True)

        self.database_path = os.path.join(self.storage_path, "database.db")
        self.lxmf_router_path = os.path.join(self.storage_path, "lxmf_router")

        # Identity backup
        identity_backup_file = os.path.join(self.storage_path, "identity")
        if not os.path.exists(identity_backup_file):
            with open(identity_backup_file, "wb") as f:
                f.write(identity.get_private_key())

        # Session ID for this specific context instance
        if not hasattr(app, "_identity_session_id_counter"):
            app._identity_session_id_counter = 0
        app._identity_session_id_counter += 1
        self.session_id = app._identity_session_id_counter

        # Initialized state
        self.database = None
        self.config = None
        self.message_handler = None
        self.announce_manager = None
        self.archiver_manager = None
        self.map_manager = None
        self.docs_manager = None
        self.nomadnet_manager = None
        self.message_router = None
        self.telephone_manager = None
        self.voicemail_manager = None
        self.ringtone_manager = None
        self.rncp_handler = None
        self.rnstatus_handler = None
        self.rnprobe_handler = None
        self.translator_handler = None
        self.forwarding_manager = None
        self.community_interfaces_manager = None
        self.local_lxmf_destination = None
        self.announce_handlers = []
        self.integrity_manager = IntegrityManager(
            self.storage_path, self.database_path, self.identity_hash
        )

        self.running = False

    def setup(self):
        print(f"Setting up Identity Context for {self.identity_hash}...")

        # 0. Clear any previous integrity issues on the app
        self.app.integrity_issues = []

        # 1. Cleanup RNS state for this identity if any lingers
        self.app.cleanup_rns_state_for_identity(self.identity.hash)

        # 2. Initialize Database
        if getattr(self.app, "emergency", False):
            print("EMERGENCY MODE ENABLED: Using in-memory database.")
            self.database = Database(":memory:")
        else:
            self.database = Database(self.database_path)

        # Check Integrity (skip in emergency mode)
        if not getattr(self.app, "emergency", False):
            is_ok, issues = self.integrity_manager.check_integrity()
            if not is_ok:
                print(
                    f"INTEGRITY WARNING for {self.identity_hash}: {', '.join(issues)}"
                )
                if not hasattr(self.app, "integrity_issues"):
                    self.app.integrity_issues = []
                self.app.integrity_issues.extend(issues)

        try:
            self.database.initialize()
            if not getattr(self.app, "emergency", False):
                self.database.migrate_from_legacy(
                    self.app.reticulum_config_dir,
                    self.identity_hash,
                )
            self.database._tune_sqlite_pragmas()
        except Exception as exc:
            if not self.app.auto_recover and not getattr(self.app, "emergency", False):
                raise
            print(
                f"Database initialization failed for {self.identity_hash}, attempting recovery: {exc}"
            )
            if not getattr(self.app, "emergency", False):
                self.app._run_startup_auto_recovery()
                self.database.initialize()
                self.database._tune_sqlite_pragmas()

        # 3. Initialize Config and Managers
        self.config = ConfigManager(self.database)

        # Apply overrides from CLI/ENV if provided
        if (
            hasattr(self.app, "gitea_base_url_override")
            and self.app.gitea_base_url_override
        ):
            self.config.gitea_base_url.set(self.app.gitea_base_url_override)
        if (
            hasattr(self.app, "docs_download_urls_override")
            and self.app.docs_download_urls_override
        ):
            self.config.docs_download_urls.set(self.app.docs_download_urls_override)

        self.message_handler = MessageHandler(self.database)
        self.announce_manager = AnnounceManager(self.database)
        self.archiver_manager = ArchiverManager(self.database)
        self.map_manager = MapManager(self.config, self.app.storage_dir)
        self.docs_manager = DocsManager(
            self.config,
            self.app.get_public_path(),
            project_root=os.path.dirname(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
            ),
            storage_dir=self.storage_path,
        )
        self.nomadnet_manager = NomadNetworkManager(
            self.config,
            self.archiver_manager,
            self.database,
        )

        # Vacuum and mark stuck messages
        self.database.provider.vacuum()
        self.database.messages.mark_stuck_messages_as_failed()

        # 4. Initialize LXMF Router
        propagation_stamp_cost = self.config.lxmf_propagation_node_stamp_cost.get()
        self.message_router = create_lxmf_router(
            identity=self.identity,
            storagepath=self.lxmf_router_path,
            propagation_cost=propagation_stamp_cost,
        )
        self.message_router.PROCESSING_INTERVAL = 1
        self.message_router.delivery_per_transfer_limit = (
            self.config.lxmf_delivery_transfer_limit_in_bytes.get() / 1000
        )

        # Register LXMF delivery identity
        inbound_stamp_cost = self.config.lxmf_inbound_stamp_cost.get()
        self.local_lxmf_destination = self.message_router.register_delivery_identity(
            identity=self.identity,
            display_name=self.config.display_name.get(),
            stamp_cost=inbound_stamp_cost,
        )

        # Forwarding Manager
        self.forwarding_manager = ForwardingManager(
            self.database,
            self.lxmf_router_path,
            lambda msg: self.app.on_lxmf_delivery(msg, context=self),
            config=self.config,
        )
        self.forwarding_manager.load_aliases()

        # Register delivery callback
        self.message_router.register_delivery_callback(
            lambda msg: self.app.on_lxmf_delivery(msg, context=self)
        )

        # 5. Initialize Handlers and Managers
        self.rncp_handler = RNCPHandler(
            reticulum_instance=getattr(self.app, "reticulum", None),
            identity=self.identity,
            storage_dir=self.app.storage_dir,
        )
        self.rnstatus_handler = RNStatusHandler(
            reticulum_instance=getattr(self.app, "reticulum", None),
        )
        self.rnpath_handler = RNPathHandler(
            reticulum_instance=getattr(self.app, "reticulum", None),
        )
        self.rnprobe_handler = RNProbeHandler(
            reticulum_instance=getattr(self.app, "reticulum", None),
            identity=self.identity,
        )

        libretranslate_url = self.config.libretranslate_url.get()
        translator_enabled = self.config.translator_enabled.get()
        self.translator_handler = TranslatorHandler(
            libretranslate_url=libretranslate_url,
            enabled=translator_enabled,
        )

        # Initialize managers
        self.telephone_manager = TelephoneManager(
            self.identity,
            config_manager=self.config,
            storage_dir=self.storage_path,
            db=self.database,
        )
        self.telephone_manager.get_name_for_identity_hash = (
            self.app.get_name_for_identity_hash
        )
        self.telephone_manager.on_initiation_status_callback = (
            lambda status, target: self.app.on_telephone_initiation_status(
                status, target, context=self
            )
        )
        self.telephone_manager.register_ringing_callback(
            lambda call: self.app.on_incoming_telephone_call(call, context=self)
        )
        self.telephone_manager.register_established_callback(
            lambda call: self.app.on_telephone_call_established(call, context=self)
        )
        self.telephone_manager.register_ended_callback(
            lambda call: self.app.on_telephone_call_ended(call, context=self)
        )

        # Only initialize telephone hardware/profile if not in emergency mode
        if not getattr(self.app, "emergency", False):
            self.telephone_manager.init_telephone()

        self.voicemail_manager = VoicemailManager(
            db=self.database,
            config=self.config,
            telephone_manager=self.telephone_manager,
            storage_dir=self.storage_path,
        )
        self.voicemail_manager.get_name_for_identity_hash = (
            self.app.get_name_for_identity_hash
        )
        self.voicemail_manager.on_new_voicemail_callback = (
            lambda vm: self.app.on_new_voicemail_received(vm, context=self)
        )

        self.ringtone_manager = RingtoneManager(
            config=self.config,
            storage_dir=self.storage_path,
        )

        self.community_interfaces_manager = CommunityInterfacesManager()

        # 6. Register Announce Handlers
        self.register_announce_handlers()

        # 7. Start background threads
        self.running = True
        self.start_background_threads()

        # 8. Handle initial documentation download
        if (
            not getattr(self.app, "emergency", False)
            and not self.config.initial_docs_download_attempted.get()
        ):
            if not self.docs_manager.has_docs():
                print(
                    f"Triggering initial documentation download for {self.identity_hash}..."
                )
                self.docs_manager.update_docs()
            self.config.initial_docs_download_attempted.set(True)

        # Baseline integrity manifest after successful setup
        if not getattr(self.app, "emergency", False):
            self.integrity_manager.save_manifest()

        print(f"Identity Context for {self.identity_hash} is now running.")

    def start_background_threads(self):
        # start background thread for auto announce loop
        thread = threading.Thread(
            target=asyncio.run,
            args=(self.app.announce_loop(self.session_id, context=self),),
        )
        thread.daemon = True
        thread.start()

        # start background thread for auto syncing propagation nodes
        thread = threading.Thread(
            target=asyncio.run,
            args=(
                self.app.announce_sync_propagation_nodes(self.session_id, context=self),
            ),
        )
        thread.daemon = True
        thread.start()

        # start background thread for crawler loop
        thread = threading.Thread(
            target=asyncio.run,
            args=(self.app.crawler_loop(self.session_id, context=self),),
        )
        thread.daemon = True
        thread.start()

        # start background thread for auto backup loop
        thread = threading.Thread(
            target=asyncio.run,
            args=(self.app.auto_backup_loop(self.session_id, context=self),),
        )
        thread.daemon = True
        thread.start()

    def register_announce_handlers(self):
        handlers = [
            AnnounceHandler(
                "lxst.telephony",
                lambda aspect, dh, ai, ad, aph: self.app.on_telephone_announce_received(
                    aspect, dh, ai, ad, aph, context=self
                ),
            ),
            AnnounceHandler(
                "lxmf.delivery",
                lambda aspect, dh, ai, ad, aph: self.app.on_lxmf_announce_received(
                    aspect, dh, ai, ad, aph, context=self
                ),
            ),
            AnnounceHandler(
                "lxmf.propagation",
                lambda aspect,
                dh,
                ai,
                ad,
                aph: self.app.on_lxmf_propagation_announce_received(
                    aspect, dh, ai, ad, aph, context=self
                ),
            ),
            AnnounceHandler(
                "nomadnetwork.node",
                lambda aspect,
                dh,
                ai,
                ad,
                aph: self.app.on_nomadnet_node_announce_received(
                    aspect, dh, ai, ad, aph, context=self
                ),
            ),
        ]
        for handler in handlers:
            RNS.Transport.register_announce_handler(handler)
            self.announce_handlers.append(handler)

    def teardown(self):
        print(f"Tearing down Identity Context for {self.identity_hash}...")
        self.running = False

        # 1. Deregister announce handlers
        for handler in self.announce_handlers:
            try:
                RNS.Transport.deregister_announce_handler(handler)
            except Exception:
                pass
        self.announce_handlers = []

        # 2. Cleanup RNS destinations and links
        try:
            if self.message_router:
                if hasattr(self.message_router, "delivery_destinations"):
                    for dest_hash in list(
                        self.message_router.delivery_destinations.keys()
                    ):
                        dest = self.message_router.delivery_destinations[dest_hash]
                        RNS.Transport.deregister_destination(dest)

                if (
                    hasattr(self.message_router, "propagation_destination")
                    and self.message_router.propagation_destination
                ):
                    RNS.Transport.deregister_destination(
                        self.message_router.propagation_destination
                    )

            if self.telephone_manager and self.telephone_manager.telephone:
                if (
                    hasattr(self.telephone_manager.telephone, "destination")
                    and self.telephone_manager.telephone.destination
                ):
                    RNS.Transport.deregister_destination(
                        self.telephone_manager.telephone.destination
                    )

            self.app.cleanup_rns_state_for_identity(self.identity.hash)
        except Exception as e:
            print(f"Error during RNS cleanup for {self.identity_hash}: {e}")

        # 3. Stop LXMF Router jobs
        if self.message_router:
            try:
                self.message_router.jobs = lambda: None
                if hasattr(self.message_router, "exit_handler"):
                    self.message_router.exit_handler()
            except Exception as e:
                print(
                    f"Error while tearing down LXMRouter for {self.identity_hash}: {e}"
                )

        # 4. Stop telephone and voicemail
        if self.telephone_manager:
            try:
                self.telephone_manager.teardown()
            except Exception as e:
                print(
                    f"Error while tearing down telephone for {self.identity_hash}: {e}"
                )

        if self.database:
            try:
                # 1. Checkpoint WAL and close database cleanly to ensure file is stable for hashing
                self.database._checkpoint_and_close()
            except Exception as e:
                print(
                    f"Error closing database during teardown for {self.identity_hash}: {e}"
                )

            # 2. Save integrity manifest AFTER closing to capture final stable state
            self.integrity_manager.save_manifest()

        print(f"Identity Context for {self.identity_hash} torn down.")
