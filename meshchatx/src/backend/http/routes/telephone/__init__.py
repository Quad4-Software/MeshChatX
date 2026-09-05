# SPDX-License-Identifier: 0BSD
"""HTTP routes: telephone (package)."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend.http.routes.telephone._names import (
    first_multipart_file_field,
)
from meshchatx.src.backend.http.routes.telephone.session import (
    register_telephone_session_routes,
)
from meshchatx.src.backend.http.routes.telephone.history import (
    register_telephone_history_routes,
)
from meshchatx.src.backend.http.routes.telephone.voicemail import (
    register_telephone_voicemail_routes,
)
from meshchatx.src.backend.http.routes.telephone.recordings import (
    register_telephone_recordings_routes,
)
from meshchatx.src.backend.http.routes.telephone.ringtones import (
    register_telephone_ringtones_routes,
)
from meshchatx.src.backend.http.routes.telephone.notification_sounds import (
    register_telephone_notification_sounds_routes,
)


def register_telephone_routes(routes: Any, app: Any) -> None:
    register_telephone_session_routes(routes, app)
    register_telephone_history_routes(routes, app)
    register_telephone_voicemail_routes(routes, app)
    register_telephone_recordings_routes(routes, app)
    register_telephone_ringtones_routes(routes, app)
    register_telephone_notification_sounds_routes(routes, app)


__all__ = [
    "first_multipart_file_field",
    "register_telephone_routes",
]
