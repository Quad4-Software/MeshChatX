# SPDX-License-Identifier: 0BSD
"""HTTP routes: archives export."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.archives._helpers import resolve_node_name
from meshchatx.src.backend.http.routes.archives._names import *  # noqa: F403


def register_archives_export_routes(routes: Any, app: Any) -> None:
    @routes.get("/api/v1/nomadnet/archives/export")
    async def export_archived_pages(request):
        """Download the filtered archive set as a single zip bundle."""
        query = request.query.get("q", "").strip()
        destination_hash = request.query.get("destination_hash", "").strip() or None
        rows = app.database.misc.get_archived_pages_paginated(
            destination_hash=destination_hash,
            query=query or None,
            limit=None,
            include_content=True,
        )

        def _safe_segment(value: str) -> str:
            cleaned = re.sub(r"[\\/:*?\"<>|\x00-\x1f]+", "_", value or "").strip()
            cleaned = cleaned.strip(". ")
            return cleaned[:80] or "_"

        def _arcname(row) -> str:
            dest_dir = (row["destination_hash"] or "unknown")[:8]
            raw_path = (row["page_path"] or "/").split("`", 1)[0].strip("/")
            parts = [_safe_segment(p) for p in raw_path.split("/") if p.strip()]
            rel = "/".join(parts) if parts else "index"
            return f"{dest_dir}/{rel}"

        buf = io.BytesIO()
        used_names = set()
        manifest = []
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for row in rows:
                name = _arcname(row)
                stem, dot, ext = name.rpartition(".")
                if not dot or "/" in ext:
                    stem, ext = name, ""
                if name in used_names:
                    short = (row.get("hash") or "snap")[:8]
                    name = f"{stem}__{short}{'.' + ext if ext else ''}"
                while name in used_names:
                    name = f"{stem}__{secrets.token_hex(4)}{'.' + ext if ext else ''}"
                used_names.add(name)
                zf.writestr(name, row.get("content") or "")
                manifest.append(
                    {
                        "id": row["id"],
                        "file": name,
                        "destination_hash": row["destination_hash"],
                        "node_name": resolve_node_name(app, row["destination_hash"]),
                        "page_path": row["page_path"],
                        "hash": row["hash"],
                        "created_at": row["created_at"],
                    }
                )
            zf.writestr(
                "manifest.json",
                json.dumps(
                    {
                        "format": "meshchatx-archives",
                        "version": 1,
                        "exported_at": datetime.now(UTC).isoformat(),
                        "archives": manifest,
                    },
                    indent=2,
                ),
            )

        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        return web.Response(
            body=buf.getvalue(),
            content_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="meshchatx-archives-{stamp}.zip"',
            },
        )
