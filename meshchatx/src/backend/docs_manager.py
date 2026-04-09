import asyncio
import html
import io
import logging
import os
import re
import shutil
import threading
import zipfile

import aiohttp

from meshchatx.src.backend.markdown_renderer import MarkdownRenderer


class DocsManager:
    def __init__(self, config, public_dir, project_root=None, storage_dir=None):
        self.config = config
        self.public_dir = public_dir
        self.project_root = project_root
        self.storage_dir = storage_dir

        # Determine docs directories
        if self.storage_dir:
            self.docs_base_dir = os.path.join(self.storage_dir, "reticulum-docs")
            self.meshchatx_docs_dir = os.path.join(self.storage_dir, "meshchatx-docs")
        else:
            self.docs_base_dir = os.path.join(self.public_dir, "reticulum-docs")
            self.meshchatx_docs_dir = os.path.join(self.public_dir, "meshchatx-docs")

        # The actual docs are served from this directory
        # We will use a 'current' subdirectory for the active version
        self.docs_dir = os.path.join(self.docs_base_dir, "current")
        self.versions_dir = os.path.join(self.docs_base_dir, "versions")

        self.download_status = "idle"
        self.download_progress = 0
        self.last_error = None

        # Ensure docs directories exist
        try:
            for d in [
                self.docs_base_dir,
                self.versions_dir,
                self.docs_dir,
                self.meshchatx_docs_dir,
            ]:
                if not os.path.exists(d):
                    os.makedirs(d)

            # If 'current' doesn't exist but we have versions, pick the latest one
            if not os.path.exists(self.docs_dir) or not os.listdir(self.docs_dir):
                self._update_current_link()

        except OSError as e:
            logging.exception(f"Failed to create documentation directories: {e}")
            self.last_error = str(e)

        # Initial population of MeshChatX docs
        if os.path.exists(self.meshchatx_docs_dir) and os.access(
            self.meshchatx_docs_dir,
            os.W_OK,
        ):
            self.populate_meshchatx_docs()

    def _update_current_link(self, version=None):
        """Updates the 'current' directory to point to the specified version or the latest one."""
        if not os.path.exists(self.versions_dir):
            return

        versions = self.get_available_versions()
        if not versions:
            return

        target_version = version
        if not target_version:
            # Pick latest version (alphabetically)
            target_version = versions[-1]

        version_path = os.path.join(self.versions_dir, target_version)
        if not os.path.exists(version_path):
            return

        # On some systems symlinks might fail or be restricted, so we use a directory copy or move
        # but for now let's try to just use the path directly if possible.
        # However, meshchat.py uses self.docs_dir for the static route.

        # To make it simple and robust across platforms, we'll clear 'current' and copy the version
        if os.path.exists(self.docs_dir):
            if os.path.islink(self.docs_dir):
                os.unlink(self.docs_dir)
            else:
                shutil.rmtree(self.docs_dir)

        try:
            # Try symlink first as it's efficient
            # We use a relative path for the symlink target to make the storage directory portable
            # version_path is relative to CWD, so we need it relative to the parent of self.docs_dir
            rel_target = os.path.relpath(version_path, os.path.dirname(self.docs_dir))
            os.symlink(rel_target, self.docs_dir)
        except (OSError, AttributeError):
            # Fallback to copy
            shutil.copytree(version_path, self.docs_dir)

    def get_available_versions(self):
        if not os.path.exists(self.versions_dir):
            return []
        versions = [
            d
            for d in os.listdir(self.versions_dir)
            if os.path.isdir(os.path.join(self.versions_dir, d))
        ]
        return sorted(versions)

    def get_current_version(self):
        if not os.path.exists(self.docs_dir):
            return None

        if os.path.islink(self.docs_dir):
            return os.path.basename(os.readlink(self.docs_dir))

        # If it's a copy, we might need a metadata file to know which version it is
        version_file = os.path.join(self.docs_dir, ".version")
        if os.path.exists(version_file):
            try:
                with open(version_file) as f:
                    return f.read().strip()
            except OSError:
                pass
        return "unknown"

    def switch_version(self, version):
        if version in self.get_available_versions():
            self._update_current_link(version)
            return True
        return False

    def delete_version(self, version):
        """Deletes a specific version of documentation."""
        if version not in self.get_available_versions():
            return False

        version_path = os.path.join(self.versions_dir, version)
        if not os.path.exists(version_path):
            return False

        try:
            # If the deleted version is the current one, unlink 'current' first
            current_version = self.get_current_version()
            if current_version == version:
                if os.path.exists(self.docs_dir):
                    if os.path.islink(self.docs_dir):
                        os.unlink(self.docs_dir)
                    else:
                        shutil.rmtree(self.docs_dir)

            shutil.rmtree(version_path)

            # If we just deleted the current version, try to pick another one as current
            if current_version == version:
                self._update_current_link()

            return True
        except Exception as e:
            logging.exception(f"Failed to delete docs version {version}: {e}")
            return False

    def clear_reticulum_docs(self):
        """Clears all Reticulum documentation and versions."""
        try:
            if os.path.exists(self.docs_base_dir):
                # We don't want to delete the base dir itself, just its contents
                # except possibly some metadata if we added any.
                # Actually, deleting everything inside reticulum-docs is fine.
                for item in os.listdir(self.docs_base_dir):
                    item_path = os.path.join(self.docs_base_dir, item)
                    if os.path.islink(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)

                # Re-create required subdirectories
                for d in [self.versions_dir, self.docs_dir]:
                    if not os.path.exists(d):
                        os.makedirs(d)

                self.config.docs_downloaded.set(False)
                return True
        except Exception as e:
            logging.exception(f"Failed to clear Reticulum docs: {e}")
            return False

    def populate_meshchatx_docs(self):
        """Populates meshchatx-docs from the project's docs folder."""
        # Try to find docs folder in several places
        search_paths = []
        if self.project_root:
            search_paths.append(os.path.join(self.project_root, "docs"))

        # Also try in the public directory
        search_paths.append(os.path.join(self.public_dir, "meshchatx-docs"))

        # Also try relative to this file (project root 3 levels up)
        this_dir = os.path.dirname(os.path.abspath(__file__))
        search_paths.append(
            os.path.abspath(os.path.join(this_dir, "..", "..", "..", "docs")),
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
                        dest_path,
                    ) and os.access(self.meshchatx_docs_dir, os.W_OK):
                        shutil.copy2(src_path, dest_path)

                    # Also pre-render to HTML for easy sharing/viewing
                    try:
                        with open(src_path, encoding="utf-8") as f:
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
                        logging.exception(f"Failed to render {file} to HTML: {e}")
        except Exception as e:
            logging.exception(f"Failed to populate MeshChatX docs: {e}")

    def get_status(self):
        return {
            "status": self.download_status,
            "progress": self.download_progress,
            "last_error": self.last_error,
            "has_docs": self.has_docs(),
            "has_meshchatx_docs": self.has_meshchatx_docs(),
            "versions": self.get_available_versions(),
            "current_version": self.get_current_version(),
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

        docs.extend(
            {
                "name": file,
                "path": file,
                "type": "markdown" if file.endswith(".md") else "text",
            }
            for file in os.listdir(self.meshchatx_docs_dir)
            if file.endswith((".md", ".txt"))
        )
        return sorted(docs, key=lambda x: x["name"])

    def get_doc_content(self, path):
        try:
            full_path = os.path.realpath(os.path.join(self.meshchatx_docs_dir, path))
            base = os.path.realpath(self.meshchatx_docs_dir)
        except (ValueError, OSError):
            return None
        if not full_path.startswith(base + os.sep) and full_path != base:
            return None
        if not os.path.exists(full_path):
            return None

        with open(full_path, encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if path.endswith(".md"):
            return {
                "content": content,
                "html": MarkdownRenderer.render(content),
                "type": "markdown",
            }
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
                        "reticulum-docs",
                        os.path.relpath(file_path, self.docs_dir),
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
                            file_path,
                            encoding="utf-8",
                            errors="ignore",
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
                                    },
                                )
                    except Exception as e:
                        logging.exception(f"Error searching MeshChatX doc {file}: {e}")

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
                            # English: no language suffix; other langs use _<lang>.html
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
                                },
                            )

                            if len(results) >= 25:  # Limit results
                                break
                except Exception as e:
                    logging.exception(f"Error searching file {file_path}: {e}")
        except Exception as e:
            logging.exception(f"Search failed: {e}")

        return results

    def has_docs(self):
        # Check if index.html exists in the docs folder or if we have any versions
        return (
            os.path.exists(os.path.join(self.docs_dir, "index.html"))
            or len(self.get_available_versions()) > 0
        )

    def update_docs(self, version="latest"):
        if (
            self.download_status == "downloading"
            or self.download_status == "extracting"
        ):
            return False

        thread = threading.Thread(target=self._download_task, args=(version,))
        thread.daemon = True
        thread.start()
        return True

    def _download_task(self, version="latest"):
        try:
            asyncio.run(self._download_docs_async(version))
        except Exception as e:
            logging.exception(f"Docs download task failed: {e}")
            self.last_error = str(e)
            self.download_status = "error"

    async def _download_docs_async(self, version="latest"):
        self.download_status = "downloading"
        self.download_progress = 0
        self.last_error = None

        urls_str = self.config.docs_download_urls.get()
        urls = [u.strip() for u in urls_str.replace("\n", ",").split(",") if u.strip()]
        if not urls:
            urls = ["https://git.quad4.io/Reticulum/reticulum_website/archive/main.zip"]

        timeout = aiohttp.ClientTimeout(total=60)
        last_exception = None
        for url in urls:
            try:
                logging.info(f"Attempting to download docs from {url}")
                zip_path = os.path.join(self.docs_base_dir, "website.zip")

                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as response:
                        response.raise_for_status()
                        total_size = int(response.headers.get("Content-Length", 0) or 0)
                        downloaded_size = 0

                        with open(zip_path, "wb") as f:
                            async for chunk in response.content.iter_chunked(8192):
                                if chunk:
                                    f.write(chunk)
                                    downloaded_size += len(chunk)
                                    if total_size > 0:
                                        self.download_progress = int(
                                            (downloaded_size / total_size) * 90,
                                        )

                self.download_status = "extracting"
                if version == "latest":
                    import time

                    version = f"git-{int(time.time())}"

                self._extract_docs(zip_path, version)

                if os.path.exists(zip_path):
                    os.remove(zip_path)

                self.config.docs_downloaded.set(True)
                self.download_progress = 100
                self.download_status = "completed"

                self.switch_version(version)
                return

            except Exception as e:
                logging.warning(f"Failed to download docs from {url}: {e}")
                last_exception = e
                zip_gone = os.path.join(self.docs_base_dir, "website.zip")
                if os.path.exists(zip_gone):
                    os.remove(zip_gone)
                continue

        self.last_error = str(last_exception)
        self.download_status = "error"
        logging.error(f"All docs download sources failed. Last error: {last_exception}")

    def upload_zip(self, zip_bytes, version):
        self.download_status = "extracting"
        self.download_progress = 0
        self.last_error = None

        try:
            zip_path = os.path.join(self.docs_base_dir, "uploaded.zip")
            with open(zip_path, "wb") as f:
                f.write(zip_bytes)

            self._extract_docs(zip_path, version)

            if os.path.exists(zip_path):
                os.remove(zip_path)

            self.download_status = "completed"
            self.download_progress = 100
            self.switch_version(version)
            return True
        except Exception as e:
            self.last_error = str(e)
            self.download_status = "error"
            logging.exception(f"Failed to upload docs: {e}")
            return False

    def _extract_docs(self, zip_path, version):
        safe_version = os.path.basename(version)
        if not safe_version or safe_version in (".", ".."):
            raise ValueError(f"Invalid version name: {version}")

        version_dir = os.path.join(self.versions_dir, safe_version)
        resolved = os.path.realpath(version_dir)
        base = os.path.realpath(self.versions_dir)
        if not resolved.startswith(base + os.sep):
            raise ValueError(f"Invalid version name: {version}")

        if os.path.exists(version_dir):
            shutil.rmtree(version_dir)
        os.makedirs(version_dir)

        # Temp dir for extraction
        temp_extract = os.path.join(self.docs_base_dir, "temp_extract")
        if os.path.exists(temp_extract):
            shutil.rmtree(temp_extract)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            # Gitea/GitHub zips have a root folder
            namelist = zip_ref.namelist()
            if not namelist:
                raise Exception("Zip file is empty")

            root_folder = namelist[0].split("/")[0]

            # Check if it's the reticulum_website repo (has docs/ folder)
            docs_prefix = f"{root_folder}/docs/"
            has_docs_subfolder = any(m.startswith(docs_prefix) for m in namelist)

            if has_docs_subfolder:
                members_to_extract = [m for m in namelist if m.startswith(docs_prefix)]
                for member in members_to_extract:
                    if ".." in member.split("/"):
                        continue
                    zip_ref.extract(member, temp_extract)

                src_path = os.path.join(temp_extract, root_folder, "docs")
                # Move files from extracted docs to version_dir
                for item in os.listdir(src_path):
                    s = os.path.join(src_path, item)
                    d = os.path.join(version_dir, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
            else:
                safe_members = [
                    m for m in namelist if ".." not in m.split("/")
                ]
                zip_ref.extractall(temp_extract, members=safe_members)
                src_path = os.path.join(temp_extract, root_folder)
                if os.path.exists(src_path) and os.path.isdir(src_path):
                    for item in os.listdir(src_path):
                        s = os.path.join(src_path, item)
                        d = os.path.join(version_dir, item)
                        if os.path.isdir(s):
                            shutil.copytree(s, d)
                        else:
                            shutil.copy2(s, d)
                else:
                    # Fallback if no root folder
                    for item in os.listdir(temp_extract):
                        s = os.path.join(temp_extract, item)
                        d = os.path.join(version_dir, item)
                        if os.path.isdir(s):
                            shutil.copytree(s, d)
                        else:
                            shutil.copy2(s, d)

        # Create a metadata file with the version name
        with open(os.path.join(version_dir, ".version"), "w") as f:
            f.write(version)

        # Cleanup temp
        if os.path.exists(temp_extract):
            shutil.rmtree(temp_extract)
