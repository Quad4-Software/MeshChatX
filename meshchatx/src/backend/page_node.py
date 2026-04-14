"""
PageNode: Serves Micron pages and files over RNS.

Each PageNode owns an RNS Destination (SINGLE, IN) with the aspect
nomadnetwork.node and registers per-page request handlers at
paths like /page/index.mu. This makes page nodes compatible with
the standard NomadNet page browsing protocol (which is just RNS
request/response with specific path conventions).

Clients link to the destination and call link.request("/page/name.mu")
to fetch a page, or /file/name for files.

Supported page filename extensions are ``.mu``, ``.md``, ``.txt``, and ``.html``.
"""

import json
import os

import RNS


APP_NAME = "nomadnetwork"
ASPECT = "node"
DEFAULT_INDEX = "index.mu"

ALLOWED_PAGE_EXTENSIONS = frozenset({".mu", ".md", ".txt", ".html"})


def normalize_page_filename(name: str) -> str:
    """Return a safe basename with an allowed extension. Unknown extensions raise ValueError."""
    name = os.path.basename((name or "").strip())
    if not name or name in (".", ".."):
        raise ValueError("page name is required")
    lower = name.lower()
    for ext in ALLOWED_PAGE_EXTENSIONS:
        if lower.endswith(ext):
            return name
    if "." in name:
        raise ValueError("unsupported page extension")
    return f"{name}.mu"


def is_allowed_page_filename(name: str) -> bool:
    lower = os.path.basename(name or "").lower()
    return any(lower.endswith(ext) for ext in ALLOWED_PAGE_EXTENSIONS)


class PageNode:
    """A single page-serving node on the Reticulum mesh."""

    def __init__(self, node_id, name, base_dir, identity=None, identity_path=None):
        self.node_id = node_id
        self.name = name
        self.base_dir = base_dir
        self.pages_dir = os.path.join(base_dir, "pages")
        self.files_dir = os.path.join(base_dir, "files")

        self.identity = identity
        self.identity_path = identity_path or os.path.join(base_dir, "identity")
        self.destination = None
        self.active_links = []
        self.running = False
        self._registered_page_paths = set()
        self._registered_file_paths = set()
        self._stats = {"pages_served": 0, "files_served": 0, "links_established": 0}

    def setup(self):
        """Create directories, load or create identity, set up RNS destination."""
        os.makedirs(self.pages_dir, exist_ok=True)
        os.makedirs(self.files_dir, exist_ok=True)

        if self.identity is None:
            if os.path.isfile(self.identity_path):
                self.identity = RNS.Identity.from_file(self.identity_path)
            else:
                self.identity = RNS.Identity()
                self.identity.to_file(self.identity_path)

        self.destination = RNS.Destination(
            self.identity,
            RNS.Destination.IN,
            RNS.Destination.SINGLE,
            APP_NAME,
            ASPECT,
        )

        self.destination.set_link_established_callback(self._link_established)

        self._register_existing_pages()
        self._register_existing_files()
        self._ensure_local_path()

        self.running = True
        return self.destination.hash.hex()

    def announce(self):
        """Broadcast this node's presence on the mesh."""
        if self.destination and self.running:
            app_data = self.name.encode("utf-8")
            self.destination.announce(app_data=app_data)
            self._ensure_local_path()

    def teardown(self):
        """Deregister handlers and clean up."""
        self.running = False
        if self.destination:
            for rpath in list(self._registered_page_paths):
                self.destination.deregister_request_handler(rpath)
            for rpath in list(self._registered_file_paths):
                self.destination.deregister_request_handler(rpath)
            self._registered_page_paths.clear()
            self._registered_file_paths.clear()

            RNS.Transport.deregister_destination(self.destination)
            self.destination = None

        for link in list(self.active_links):
            try:
                link.teardown()
            except Exception:
                pass
        self.active_links.clear()

    def _link_established(self, link):
        self.active_links.append(link)
        self._stats["links_established"] += 1
        link.set_link_closed_callback(self._link_closed)

    def _link_closed(self, link):
        if link in self.active_links:
            self.active_links.remove(link)

    def _ensure_local_path(self):
        """
        Register the destination's identity in RNS.Identity.known_destinations
        so that Identity.recall() can resolve it for local link establishment.
        """
        if not self.destination:
            return
        RNS.Identity.remember(
            packet_hash=None,
            destination_hash=self.destination.hash,
            public_key=self.identity.get_public_key(),
            app_data=self.name.encode("utf-8"),
        )

    def _page_request_path(self, page_name):
        """Build the NomadNet-style request path for a page."""
        return f"/page/{page_name}"

    def _file_request_path(self, file_name):
        """Build the NomadNet-style request path for a file."""
        return f"/file/{file_name}"

    def _register_existing_pages(self):
        """Scan pages directory and register a handler for each page."""
        if not os.path.isdir(self.pages_dir):
            return
        for fname in os.listdir(self.pages_dir):
            if not os.path.isfile(os.path.join(self.pages_dir, fname)):
                continue
            if not is_allowed_page_filename(fname):
                continue
            self._register_page_handler(fname)

    def _register_existing_files(self):
        """Scan files directory and register a handler for each file."""
        if not os.path.isdir(self.files_dir):
            return
        for fname in os.listdir(self.files_dir):
            if os.path.isfile(os.path.join(self.files_dir, fname)):
                self._register_file_handler(fname)

    def _register_page_handler(self, page_name):
        """Register a request handler for a specific page."""
        if not self.destination:
            return
        rpath = self._page_request_path(page_name)
        if rpath in self._registered_page_paths:
            return
        self.destination.register_request_handler(
            rpath,
            response_generator=self._make_page_responder(page_name),
            allow=RNS.Destination.ALLOW_ALL,
        )
        self._registered_page_paths.add(rpath)

    def _deregister_page_handler(self, page_name):
        """Deregister the request handler for a specific page."""
        if not self.destination:
            return
        rpath = self._page_request_path(page_name)
        if rpath not in self._registered_page_paths:
            return
        self.destination.deregister_request_handler(rpath)
        self._registered_page_paths.discard(rpath)

    def _register_file_handler(self, file_name):
        """Register a request handler for a specific file."""
        if not self.destination:
            return
        rpath = self._file_request_path(file_name)
        if rpath in self._registered_file_paths:
            return
        self.destination.register_request_handler(
            rpath,
            response_generator=self._make_file_responder(file_name),
            allow=RNS.Destination.ALLOW_ALL,
        )
        self._registered_file_paths.add(rpath)

    def _deregister_file_handler(self, file_name):
        """Deregister the request handler for a specific file."""
        if not self.destination:
            return
        rpath = self._file_request_path(file_name)
        if rpath not in self._registered_file_paths:
            return
        self.destination.deregister_request_handler(rpath)
        self._registered_file_paths.discard(rpath)

    def _make_page_responder(self, page_name):
        """Return a closure that serves a specific page."""

        def responder(path, data, request_id, link_id, remote_identity, requested_at):
            safe_name = os.path.basename(page_name)
            page_path = os.path.join(self.pages_dir, safe_name)
            if not os.path.isfile(page_path):
                return None
            try:
                with open(page_path, "rb") as f:
                    content = f.read()
                self._stats["pages_served"] += 1
                return content
            except Exception:
                return None

        return responder

    def _make_file_responder(self, file_name):
        """Return a closure that serves a specific file."""

        def responder(path, data, request_id, link_id, remote_identity, requested_at):
            safe_name = os.path.basename(file_name)
            file_path = os.path.join(self.files_dir, safe_name)
            if not os.path.isfile(file_path):
                return None
            try:
                fh = open(file_path, "rb")
                metadata = {"name": safe_name.encode("utf-8")}
                self._stats["files_served"] += 1
                return [fh, metadata]
            except Exception:
                return None

        return responder

    def add_page(self, name, content):
        """Write a page file and register its request handler."""
        name = normalize_page_filename(name)
        page_path = os.path.join(self.pages_dir, name)
        if isinstance(content, str):
            content = content.encode("utf-8")
        with open(page_path, "wb") as f:
            f.write(content)
        if self.running:
            self._register_page_handler(name)
        return name

    def remove_page(self, name):
        """Remove a page and deregister its request handler."""
        try:
            name = normalize_page_filename(name)
        except ValueError:
            return False
        page_path = os.path.join(self.pages_dir, name)
        if os.path.isfile(page_path):
            os.remove(page_path)
            self._deregister_page_handler(name)
            return True
        return False

    def list_pages(self):
        """Return a list of page names."""
        if not os.path.isdir(self.pages_dir):
            return []
        return sorted(
            f
            for f in os.listdir(self.pages_dir)
            if os.path.isfile(os.path.join(self.pages_dir, f))
            and is_allowed_page_filename(f)
        )

    def get_page_content(self, name):
        """Read and return a page's content."""
        try:
            name = normalize_page_filename(name)
        except ValueError:
            return None
        page_path = os.path.join(self.pages_dir, name)
        if not os.path.isfile(page_path):
            return None
        with open(page_path, "r", encoding="utf-8") as f:
            return f.read()

    def add_file(self, name, data):
        """Write a file and register its request handler."""
        name = os.path.basename(name)
        file_path = os.path.join(self.files_dir, name)
        mode = "wb" if isinstance(data, bytes) else "w"
        with open(file_path, mode) as f:
            f.write(data)
        if self.running:
            self._register_file_handler(name)
        return name

    def remove_file(self, name):
        """Remove a file and deregister its request handler."""
        name = os.path.basename(name)
        file_path = os.path.join(self.files_dir, name)
        if os.path.isfile(file_path):
            os.remove(file_path)
            self._deregister_file_handler(name)
            return True
        return False

    def list_files(self):
        """Return a list of file dicts with name and size."""
        if not os.path.isdir(self.files_dir):
            return []
        result = []
        for fname in sorted(os.listdir(self.files_dir)):
            fpath = os.path.join(self.files_dir, fname)
            if os.path.isfile(fpath):
                result.append({"name": fname, "size": os.path.getsize(fpath)})
        return result

    def get_destination_hash(self):
        """Return the hex destination hash if running."""
        if self.destination:
            return self.destination.hash.hex()
        return None

    def get_status(self):
        """Return current node status dict."""
        return {
            "node_id": self.node_id,
            "name": self.name,
            "running": self.running,
            "destination_hash": self.get_destination_hash(),
            "identity_hash": self.identity.hash.hex() if self.identity else None,
            "active_links": len(self.active_links),
            "pages": self.list_pages(),
            "files": self.list_files(),
            "stats": dict(self._stats),
        }

    def save_config(self):
        """Persist node configuration to disk."""
        config = {
            "node_id": self.node_id,
            "name": self.name,
        }
        config_path = os.path.join(self.base_dir, "config.json")
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

    @staticmethod
    def load_config(base_dir):
        """Load node configuration from disk. Returns dict or None."""
        config_path = os.path.join(base_dir, "config.json")
        if not os.path.isfile(config_path):
            return None
        with open(config_path, "r") as f:
            return json.load(f)
