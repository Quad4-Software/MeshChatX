import logging
import os
import re
import shutil
import threading
import zipfile
import io
import html

import requests
from meshchatx.src.backend.markdown_renderer import MarkdownRenderer


class DocsManager:
    def __init__(self, config, public_dir, project_root=None, storage_dir=None):
        self.config = config
        self.public_dir = public_dir
        self.project_root = project_root
        self.storage_dir = storage_dir

        # Determine docs directories
        # If storage_dir is provided, we prefer using it for documentation storage
        # to avoid Read-only file system errors in environments like AppImages.
        if self.storage_dir:
            self.docs_dir = os.path.join(self.storage_dir, "reticulum-docs")
            self.meshchatx_docs_dir = os.path.join(self.storage_dir, "meshchatx-docs")
        else:
            self.docs_dir = os.path.join(self.public_dir, "reticulum-docs")
            self.meshchatx_docs_dir = os.path.join(self.public_dir, "meshchatx-docs")

        self.download_status = "idle"
        self.download_progress = 0
        self.last_error = None

        # Ensure docs directories exist
        try:
            if not os.path.exists(self.docs_dir):
                os.makedirs(self.docs_dir)

            if not os.path.exists(self.meshchatx_docs_dir):
                os.makedirs(self.meshchatx_docs_dir)
        except OSError as e:
            # If we still fail (e.g. storage_dir was not provided and public_dir is read-only)
            # we log it but don't crash the whole app. Emergency mode can still run.
            logging.error(f"Failed to create documentation directories: {e}")
            self.last_error = str(e)

        # Initial population of MeshChatX docs
        if os.path.exists(self.meshchatx_docs_dir) and os.access(
            self.meshchatx_docs_dir, os.W_OK
        ):
            self.populate_meshchatx_docs()

    def populate_meshchatx_docs(self):
        """Populates meshchatx-docs from the project's docs folder."""
        # Try to find docs folder in several places
        search_paths = []
        if self.project_root:
            search_paths.append(os.path.join(self.project_root, "docs"))

        # Also try in the public directory
        search_paths.append(os.path.join(self.public_dir, "meshchatx-docs"))

        # Also try relative to this file
        # This file is in meshchatx/src/backend/docs_manager.py
        # Project root is 3 levels up
        this_dir = os.path.dirname(os.path.abspath(__file__))
        search_paths.append(
            os.path.abspath(os.path.join(this_dir, "..", "..", "..", "docs"))
        )

        src_docs = None
        for path in search_paths:
            if os.path.exists(path) and os.path.isdir(path):
                src_docs = path
                break

        if not src_docs:
            logging.warning("MeshChatX docs source directory not found.")
            return

        try:
            for file in os.listdir(src_docs):
                if file.endswith(".md") or file.endswith(".txt"):
                    src_path = os.path.join(src_docs, file)
                    dest_path = os.path.join(self.meshchatx_docs_dir, file)

                    # Only copy if source and destination are different
                    if os.path.abspath(src_path) != os.path.abspath(
                        dest_path
                    ) and os.access(self.meshchatx_docs_dir, os.W_OK):
                        shutil.copy2(src_path, dest_path)

                    # Also pre-render to HTML for easy sharing/viewing
                    try:
                        with open(src_path, "r", encoding="utf-8") as f:
                            content = f.read()

                        html_content = MarkdownRenderer.render(content)
                        # Basic HTML wrapper for standalone viewing
                        full_html = f"""<!DOCTYPE html>
<html class="dark">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{file}</title>
    <script src="../assets/js/tailwindcss/tailwind-v3.4.3-forms-v0.5.7.js"></script>
    <style>
        body {{ background-color: #111827; color: #f3f4f6; }}
    </style>
</head>
<body class="p-4 md:p-8 max-w-4xl mx-auto">
    <div class="max-w-none break-words">
        {html_content}
    </div>
</body>
</html>"""
                        html_file = os.path.splitext(file)[0] + ".html"
                        with open(
                            os.path.join(self.meshchatx_docs_dir, html_file),
                            "w",
                            encoding="utf-8",
                        ) as f:
                            f.write(full_html)
                    except Exception as e:
                        logging.error(f"Failed to render {file} to HTML: {e}")
        except Exception as e:
            logging.error(f"Failed to populate MeshChatX docs: {e}")

    def get_status(self):
        return {
            "status": self.download_status,
            "progress": self.download_progress,
            "last_error": self.last_error,
            "has_docs": self.has_docs(),
            "has_meshchatx_docs": self.has_meshchatx_docs(),
        }

    def has_meshchatx_docs(self):
        return (
            any(
                f.endswith((".md", ".txt")) for f in os.listdir(self.meshchatx_docs_dir)
            )
            if os.path.exists(self.meshchatx_docs_dir)
            else False
        )

    def get_meshchatx_docs_list(self):
        docs = []
        if not os.path.exists(self.meshchatx_docs_dir):
            return docs

        for file in os.listdir(self.meshchatx_docs_dir):
            if file.endswith((".md", ".txt")):
                docs.append(
                    {
                        "name": file,
                        "path": file,
                        "type": "markdown" if file.endswith(".md") else "text",
                    }
                )
        return sorted(docs, key=lambda x: x["name"])

    def get_doc_content(self, path):
        full_path = os.path.join(self.meshchatx_docs_dir, path)
        if not os.path.exists(full_path):
            return None

        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if path.endswith(".md"):
            return {
                "content": content,
                "html": MarkdownRenderer.render(content),
                "type": "markdown",
            }
        else:
            return {
                "content": content,
                "html": f"<pre class='whitespace-pre-wrap font-mono'>{html.escape(content)}</pre>",
                "type": "text",
            }

    def export_docs(self):
        """Creates a zip of all docs and returns the bytes."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Add reticulum docs
            for root, _, files in os.walk(self.docs_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.join(
                        "reticulum-docs", os.path.relpath(file_path, self.docs_dir)
                    )
                    zip_file.write(file_path, rel_path)

            # Add meshchatx docs
            for root, _, files in os.walk(self.meshchatx_docs_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.join(
                        "meshchatx-docs",
                        os.path.relpath(file_path, self.meshchatx_docs_dir),
                    )
                    zip_file.write(file_path, rel_path)

        buffer.seek(0)
        return buffer.getvalue()

    def search(self, query, lang="en"):
        if not query:
            return []

        results = []
        query = query.lower()

        # 1. Search MeshChatX Docs first
        if os.path.exists(self.meshchatx_docs_dir):
            for file in os.listdir(self.meshchatx_docs_dir):
                if file.endswith((".md", ".txt")):
                    file_path = os.path.join(self.meshchatx_docs_dir, file)
                    try:
                        with open(
                            file_path, "r", encoding="utf-8", errors="ignore"
                        ) as f:
                            content = f.read()
                            if query in content.lower():
                                # Simple snippet
                                idx = content.lower().find(query)
                                start = max(0, idx - 80)
                                end = min(len(content), idx + len(query) + 120)
                                snippet = content[start:end]
                                if start > 0:
                                    snippet = "..." + snippet
                                if end < len(content):
                                    snippet = snippet + "..."

                                results.append(
                                    {
                                        "title": file,
                                        "path": f"/meshchatx-docs/{file}",
                                        "snippet": snippet,
                                        "source": "MeshChatX",
                                    }
                                )
                    except Exception as e:
                        logging.error(f"Error searching MeshChatX doc {file}: {e}")

        # 2. Search Reticulum Docs
        if self.has_docs():
            # Known language suffixes in Reticulum docs
            known_langs = ["de", "es", "jp", "nl", "pl", "pt-br", "tr", "uk", "zh-cn"]

        # Determine files to search
        target_files = []
        try:
            for root, _, files in os.walk(self.docs_dir):
                for file in files:
                    if file.endswith(".html"):
                        # Basic filtering for language if possible
                        if lang != "en":
                            if f"_{lang}.html" in file:
                                target_files.append(os.path.join(root, file))
                        else:
                            # For English, we want files that DON'T have a language suffix
                            # This is a bit heuristic
                            has_lang_suffix = False
                            for lang_code in known_langs:
                                if f"_{lang_code}.html" in file:
                                    has_lang_suffix = True
                                    break
                            if not has_lang_suffix:
                                target_files.append(os.path.join(root, file))

            # If we found nothing for a specific language, fall back to English ONLY
            if not target_files and lang != "en":
                for root, _, files in os.walk(self.docs_dir):
                    for file in files:
                        if file.endswith(".html"):
                            has_lang_suffix = False
                            for lang_code in known_langs:
                                if f"_{lang_code}.html" in file:
                                    has_lang_suffix = True
                                    break
                            if not has_lang_suffix:
                                target_files.append(os.path.join(root, file))

            for file_path in target_files:
                try:
                    with open(file_path, encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                        # Very basic HTML tag removal for searching
                        text_content = re.sub(r"<[^>]+>", " ", content)
                        text_content = " ".join(text_content.split())

                        if query in text_content.lower():
                            # Find title
                            title_match = re.search(
                                r"<title>(.*?)</title>",
                                content,
                                re.IGNORECASE | re.DOTALL,
                            )
                            title = (
                                title_match.group(1).strip()
                                if title_match
                                else os.path.basename(file_path)
                            )
                            # Remove " — Reticulum Network Stack ..." suffix often found in Sphinx docs
                            title = re.sub(r"\s+[\u2014-].*$", "", title)

                            # Find snippet
                            idx = text_content.lower().find(query)
                            start = max(0, idx - 80)
                            end = min(len(text_content), idx + len(query) + 120)
                            snippet = text_content[start:end]
                            if start > 0:
                                snippet = "..." + snippet
                            if end < len(text_content):
                                snippet = snippet + "..."

                            rel_path = os.path.relpath(file_path, self.docs_dir)
                            results.append(
                                {
                                    "title": title,
                                    "path": f"/reticulum-docs/{rel_path}",
                                    "snippet": snippet,
                                    "source": "Reticulum",
                                }
                            )

                            if len(results) >= 25:  # Limit results
                                break
                except Exception as e:
                    logging.exception(f"Error searching file {file_path}: {e}")
        except Exception as e:
            logging.exception(f"Search failed: {e}")

        return results

    def has_docs(self):
        # Check if index.html exists in the docs folder or if config says so
        if self.config.docs_downloaded.get():
            return True
        return os.path.exists(os.path.join(self.docs_dir, "index.html"))

    def update_docs(self):
        if (
            self.download_status == "downloading"
            or self.download_status == "extracting"
        ):
            return False

        thread = threading.Thread(target=self._download_task)
        thread.daemon = True
        thread.start()
        return True

    def _download_task(self):
        self.download_status = "downloading"
        self.download_progress = 0
        self.last_error = None

        try:
            # We use the reticulum_website repository which contains the built HTML docs
            url = "https://github.com/markqvist/reticulum_website/archive/refs/heads/main.zip"
            zip_path = os.path.join(self.docs_dir, "website.zip")

            # Download ZIP
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded_size = 0

            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0:
                            self.download_progress = int(
                                (downloaded_size / total_size) * 90
                            )

            # Extract
            self.download_status = "extracting"
            self._extract_docs(zip_path)

            # Cleanup
            if os.path.exists(zip_path):
                os.remove(zip_path)

            self.config.docs_downloaded.set(True)
            self.download_progress = 100
            self.download_status = "completed"
        except Exception as e:
            self.last_error = str(e)
            self.download_status = "error"
            logging.exception(f"Failed to update docs: {e}")

    def _extract_docs(self, zip_path):
        # Temp dir for extraction
        temp_extract = os.path.join(self.docs_dir, "temp_extract")
        if os.path.exists(temp_extract):
            shutil.rmtree(temp_extract)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            # GitHub zips have a root folder like reticulum_website-main/
            # We want the contents of reticulum_website-main/docs/
            root_folder = zip_ref.namelist()[0].split("/")[0]
            docs_prefix = f"{root_folder}/docs/"

            members_to_extract = [
                m for m in zip_ref.namelist() if m.startswith(docs_prefix)
            ]

            for member in members_to_extract:
                zip_ref.extract(member, temp_extract)

            src_path = os.path.join(temp_extract, root_folder, "docs")

            # Clear existing docs except for the temp folder
            for item in os.listdir(self.docs_dir):
                item_path = os.path.join(self.docs_dir, item)
                if item != "temp_extract" and item != "website.zip":
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)

            # Move files from extracted docs to docs_dir
            if os.path.exists(src_path):
                for item in os.listdir(src_path):
                    s = os.path.join(src_path, item)
                    d = os.path.join(self.docs_dir, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)

        # Cleanup temp
        shutil.rmtree(temp_extract)
