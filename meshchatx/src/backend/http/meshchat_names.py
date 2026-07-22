# SPDX-License-Identifier: 0BSD

"""Ruff-visible live meshchat name bindings for extracted HTTP and WS modules."""

from __future__ import annotations

from meshchatx.src.backend.http.live_names import LiveMeshchatName
from meshchatx.src.backend.map_geo_validator import GeoValidationError  # noqa: F401
from meshchatx.src.backend.privacy_mode import OutboundHttpBlockedError  # noqa: F401
from meshchatx.src.backend.map_overlay_export import OverlayExportError  # noqa: F401
from meshchatx.src.backend.map_overlay_sources import OverlaySourceParseError  # noqa: F401
from meshchatx.src.backend.plugin_guard import PluginSecurityError  # noqa: F401

AsyncUtils = LiveMeshchatName("AsyncUtils")
InterfaceConfigParser = LiveMeshchatName("InterfaceConfigParser")
InterfaceDiscovery = LiveMeshchatName("InterfaceDiscovery")
InterfaceEditor = LiveMeshchatName("InterfaceEditor")
LOGIN_PATH = LiveMeshchatName("LOGIN_PATH")
LXMF = LiveMeshchatName("LXMF")
LxmfAudioField = LiveMeshchatName("LxmfAudioField")
LxmfFileAttachment = LiveMeshchatName("LxmfFileAttachment")
LxmfFileAttachmentsField = LiveMeshchatName("LxmfFileAttachmentsField")
LxmfImageField = LiveMeshchatName("LxmfImageField")
MAX_EXPORT_TILES = LiveMeshchatName("MAX_EXPORT_TILES")
MarkdownRenderer = LiveMeshchatName("MarkdownRenderer")
NomadnetFileDownloader = LiveMeshchatName("NomadnetFileDownloader")
NomadnetPageDownloader = LiveMeshchatName("NomadnetPageDownloader")
RNProbeHandler = LiveMeshchatName("RNProbeHandler")
RNS = LiveMeshchatName("RNS")
ReticulumMeshChat = LiveMeshchatName("ReticulumMeshChat")
SETUP_PATH = LiveMeshchatName("SETUP_PATH")
TRANSPARENT_TILE = LiveMeshchatName("TRANSPARENT_TILE")
Telemeter = LiveMeshchatName("Telemeter")
UTC = LiveMeshchatName("UTC")
WSMsgType = LiveMeshchatName("WSMsgType")
_is_chaquopy_android = LiveMeshchatName("_is_chaquopy_android")
_is_loopback_bind_host = LiveMeshchatName("_is_loopback_bind_host")
_request_client_ip = LiveMeshchatName("_request_client_ip")
aiohttp = LiveMeshchatName("aiohttp")
app_version = LiveMeshchatName("app_version")
assert_migration_context_paths = LiveMeshchatName("assert_migration_context_paths")
asyncio = LiveMeshchatName("asyncio")
base64 = LiveMeshchatName("base64")
bcrypt = LiveMeshchatName("bcrypt")
binascii = LiveMeshchatName("binascii")
build_blocklist_export_document = LiveMeshchatName("build_blocklist_export_document")
build_export_document = LiveMeshchatName("build_export_document")
build_messages_export_bundle = LiveMeshchatName("build_messages_export_bundle")
cache_stats = LiveMeshchatName("cache_stats")
cancel_inbound_deliveries = LiveMeshchatName("cancel_inbound_deliveries")
cast = LiveMeshchatName("cast")
compute_lxmf_conversation_unread_from_latest_row = LiveMeshchatName(
    "compute_lxmf_conversation_unread_from_latest_row"
)
configparser = LiveMeshchatName("configparser")
contextlib = LiveMeshchatName("contextlib")
convert_db_favourite_to_dict = LiveMeshchatName("convert_db_favourite_to_dict")
convert_db_lxmf_message_to_dict = LiveMeshchatName("convert_db_lxmf_message_to_dict")
convert_lxmf_message_to_dict = LiveMeshchatName("convert_lxmf_message_to_dict")
convert_nomadnet_field_data_to_map = LiveMeshchatName(
    "convert_nomadnet_field_data_to_map"
)
convert_nomadnet_string_data_to_map = LiveMeshchatName(
    "convert_nomadnet_string_data_to_map"
)
convert_propagation_node_state_to_string = LiveMeshchatName(
    "convert_propagation_node_state_to_string"
)
copy = LiveMeshchatName("copy")
datetime = LiveMeshchatName("datetime")
describe_port_conflict = LiveMeshchatName("describe_port_conflict")
detect_image_format_from_magic = LiveMeshchatName("detect_image_format_from_magic")
ensure_outbound_http_allowed = LiveMeshchatName("ensure_outbound_http_allowed")
ensure_session_csrf_token = LiveMeshchatName("ensure_session_csrf_token")
filter_announced_dicts_by_search_query = LiveMeshchatName(
    "filter_announced_dicts_by_search_query"
)
fresh_storage_at_target = LiveMeshchatName("fresh_storage_at_target")
get_cached_active_link = LiveMeshchatName("get_cached_active_link")
get_file_path = LiveMeshchatName("get_file_path")
get_session = LiveMeshchatName("get_session")
get_trusted_proxy_cidrs = LiveMeshchatName("get_trusted_proxy_cidrs")
gif_utils = LiveMeshchatName("gif_utils")
i2p_support = LiveMeshchatName("i2p_support")
import_messages_export_bundle = LiveMeshchatName("import_messages_export_bundle")
io = LiveMeshchatName("io")
is_mbtiles_filename = LiveMeshchatName("is_mbtiles_filename")
is_path_within_dir = LiveMeshchatName("is_path_within_dir")
is_port_in_use = LiveMeshchatName("is_port_in_use")
is_user_facing_lxmf_payload = LiveMeshchatName("is_user_facing_lxmf_payload")
json = LiveMeshchatName("json")
list_host_network_interfaces = LiveMeshchatName("list_host_network_interfaces")
list_inbound_deliveries = LiveMeshchatName("list_inbound_deliveries")
list_ports = LiveMeshchatName("list_ports")
load_app_security_settings = LiveMeshchatName("load_app_security_settings")
logger = LiveMeshchatName("logger")
logging = LiveMeshchatName("logging")
lxmf_sidebar_preview_for_conversation_latest_row = LiveMeshchatName(
    "lxmf_sidebar_preview_for_conversation_latest_row"
)
memory_log_handler = LiveMeshchatName("memory_log_handler")
message_fields_have_attachments = LiveMeshchatName("message_fields_have_attachments")
migrate_legacy_to_target = LiveMeshchatName("migrate_legacy_to_target")
mime_for_image_type = LiveMeshchatName("mime_for_image_type")
normalize_identity_storage_hash = LiveMeshchatName("normalize_identity_storage_hash")
normalize_lxmf_sieve_filters = LiveMeshchatName("normalize_lxmf_sieve_filters")
normalize_message_blocklist = LiveMeshchatName("normalize_message_blocklist")
os = LiveMeshchatName("os")
parse_bool_query_param = LiveMeshchatName("parse_bool_query_param")
parse_import_document = LiveMeshchatName("parse_import_document")
parse_lxmf_display_name = LiveMeshchatName("parse_lxmf_display_name")
parse_lxmf_propagation_node_app_data = LiveMeshchatName(
    "parse_lxmf_propagation_node_app_data"
)
parse_lxmf_sieve_filters_json = LiveMeshchatName("parse_lxmf_sieve_filters_json")
parse_lxmf_stamp_cost = LiveMeshchatName("parse_lxmf_stamp_cost")
parse_message_blocklist_json = LiveMeshchatName("parse_message_blocklist_json")
parse_nomadnetwork_node_display_name = LiveMeshchatName(
    "parse_nomadnetwork_node_display_name"
)
platform = LiveMeshchatName("platform")
privacy_mode_enabled = LiveMeshchatName("privacy_mode_enabled")
psutil = LiveMeshchatName("psutil")
purge_messages_before_cutoff = LiveMeshchatName("purge_messages_before_cutoff")
re = LiveMeshchatName("re")
resolve_message_age_cutoff = LiveMeshchatName("resolve_message_age_cutoff")
reticulum_pathfinding = LiveMeshchatName("reticulum_pathfinding")
rotate_session_csrf_token = LiveMeshchatName("rotate_session_csrf_token")
rrc_protocol = LiveMeshchatName("rrc_protocol")
safe_path_under_dir = LiveMeshchatName("safe_path_under_dir")
sanitize_sticker_emoji = LiveMeshchatName("sanitize_sticker_emoji")
sanitize_sticker_name = LiveMeshchatName("sanitize_sticker_name")
sanitize_websocket_config_update = LiveMeshchatName("sanitize_websocket_config_update")
save_app_security_settings = LiveMeshchatName("save_app_security_settings")
secrets = LiveMeshchatName("secrets")
shutil = LiveMeshchatName("shutil")
sqlite3 = LiveMeshchatName("sqlite3")
sticker_pack_utils = LiveMeshchatName("sticker_pack_utils")
sys = LiveMeshchatName("sys")
tempfile = LiveMeshchatName("tempfile")
threading = LiveMeshchatName("threading")
time = LiveMeshchatName("time")
traceback = LiveMeshchatName("traceback")
user_agent_hash = LiveMeshchatName("user_agent_hash")
validate_export_document = LiveMeshchatName("validate_export_document")
web = LiveMeshchatName("web")
websocket_type_requires_auth = LiveMeshchatName("websocket_type_requires_auth")
zipfile = LiveMeshchatName("zipfile")
