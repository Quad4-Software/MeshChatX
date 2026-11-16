"""Shared constants for RNS FileSync."""

APP_NAME = "rns_filesync"
ASPECT = "filesync"
BLOCK_SIZE = 4096
HASH_CHUNK_SIZE = 65536
SCAN_INTERVAL = 5.0
ANNOUNCE_INTERVAL_DEFAULT = 21600
# Announces rebroadcast across the whole mesh, so sub-15-minute cadences are
# treated as spam. Matches the MeshChatX shared announce floor.
ANNOUNCE_INTERVAL_MIN = 900
PATH_TIMEOUT_DEFAULT = 30.0
LINK_TIMEOUT_DEFAULT = 15.0
RECONNECT_BASE_INTERVAL = 5.0
RECONNECT_MAX_INTERVAL = 60.0
HASH_DB_NAME = ".rns-filesync.db"
VALID_PERMISSIONS = frozenset({"read", "write", "delete"})
EMPTY_FILE_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
