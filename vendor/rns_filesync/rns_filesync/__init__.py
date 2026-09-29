"""RNS FileSync: peer-to-peer directory sync over Reticulum."""

from rns_filesync._meta import (
    BUILD_DATE,
    GIT_COMMIT,
    __version__,
    version_info,
    version_string,
)
from rns_filesync.service import FileSyncService

__all__ = [
    "FileSyncService",
    "__version__",
    "BUILD_DATE",
    "GIT_COMMIT",
    "version_info",
    "version_string",
]
