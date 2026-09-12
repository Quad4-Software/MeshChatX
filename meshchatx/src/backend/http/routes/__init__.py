# SPDX-License-Identifier: 0BSD

"""HTTP route module exports and fixed registration order."""

from __future__ import annotations

from meshchatx.src.backend.http.routes.app_info import register_app_info_routes
from meshchatx.src.backend.http.routes.archives import register_archives_routes
from meshchatx.src.backend.http.routes.auth import register_auth_routes
from meshchatx.src.backend.http.routes.blocklist import register_blocklist_routes
from meshchatx.src.backend.http.routes.bots import register_bots_routes
from meshchatx.src.backend.http.routes.community import register_community_routes
from meshchatx.src.backend.http.routes.config import register_config_routes
from meshchatx.src.backend.http.routes.contacts import register_contacts_routes
from meshchatx.src.backend.http.routes.database import register_database_routes
from meshchatx.src.backend.http.routes.debug import register_debug_routes
from meshchatx.src.backend.http.routes.docs import register_docs_routes
from meshchatx.src.backend.http.routes.favourites import register_favourites_routes
from meshchatx.src.backend.http.routes.filesync import register_filesync_routes
from meshchatx.src.backend.http.routes.gifs import register_gifs_routes
from meshchatx.src.backend.http.routes.identities import register_identities_routes
from meshchatx.src.backend.http.routes.interfaces import register_interfaces_routes
from meshchatx.src.backend.http.routes.lxmf import register_lxmf_routes
from meshchatx.src.backend.http.routes.maintenance import register_maintenance_routes
from meshchatx.src.backend.http.routes.map import register_map_routes
from meshchatx.src.backend.http.routes.messages import register_messages_routes
from meshchatx.src.backend.http.routes.nomad import register_nomad_routes
from meshchatx.src.backend.http.routes.page_nodes import register_page_nodes_routes
from meshchatx.src.backend.http.routes.path_probe import register_path_probe_routes
from meshchatx.src.backend.http.routes.plugins import register_plugins_routes
from meshchatx.src.backend.http.routes.repository_server import (
    register_repository_server_routes,
)
from meshchatx.src.backend.http.routes.reticulum_instance import (
    register_reticulum_instance_routes,
)
from meshchatx.src.backend.http.routes.rn_tools import register_rn_tools_routes
from meshchatx.src.backend.http.routes.rrc import register_rrc_routes
from meshchatx.src.backend.http.routes.shell import register_shell_routes
from meshchatx.src.backend.http.routes.sideband import register_sideband_routes
from meshchatx.src.backend.http.routes.spam import register_spam_routes
from meshchatx.src.backend.http.routes.status import register_status_routes
from meshchatx.src.backend.http.routes.stickers import register_stickers_routes
from meshchatx.src.backend.http.routes.telemetry import register_telemetry_routes
from meshchatx.src.backend.http.routes.telephone import register_telephone_routes
from meshchatx.src.backend.http.routes.translation import register_translation_routes
from meshchatx.src.backend.http.routes.websocket_upgrade import (
    register_websocket_upgrade_routes,
)

_REGISTER_ORDER = (
    register_shell_routes,
    register_debug_routes,
    register_database_routes,
    register_status_routes,
    register_auth_routes,
    register_interfaces_routes,
    register_community_routes,
    register_websocket_upgrade_routes,
    register_app_info_routes,
    register_docs_routes,
    register_repository_server_routes,
    register_identities_routes,
    register_maintenance_routes,
    register_config_routes,
    register_reticulum_instance_routes,
    register_rrc_routes,
    register_telephone_routes,
    register_contacts_routes,
    register_favourites_routes,
    register_archives_routes,
    register_lxmf_routes,
    register_path_probe_routes,
    register_rn_tools_routes,
    register_filesync_routes,
    register_plugins_routes,
    register_sideband_routes,
    register_page_nodes_routes,
    register_bots_routes,
    register_messages_routes,
    register_nomad_routes,
    register_blocklist_routes,
    register_spam_routes,
    register_map_routes,
    register_stickers_routes,
    register_gifs_routes,
    register_translation_routes,
    register_telemetry_routes,
)


def register_extracted_routes(routes, app) -> None:
    """Call each extracted register_*_routes in fixed order."""
    for register in _REGISTER_ORDER:
        register(routes, app)
