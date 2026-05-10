# SPDX-License-Identifier: 0BSD

import html
import io
import logging
import os
import re
import shutil
import zipfile

from meshchatx.src.backend.markdown_renderer import MarkdownRenderer

BUNDLED_DOCS_SUBDIR = os.path.join("reticulum-docs-bundled", "current")


class DocsManager:
    """Manages the bundled Reticulum manual and any user-uploaded overrides.

    The Reticulum manual is shipped with the application under
    ``<public_dir>/reticulum-docs-bundled/current``. Users may upload a
    replacement archive which is extracted into ``<storage_dir>/reticulum-docs``
    and takes precedence at request time. Removing the user upload restores the
    bundled copy. There is no runtime download path; the manual must be staged
    at build time (see ``scripts/build/fetch_reticulum_manual.py``).
    """

    def __init__(self, config, public_dir, project_root=None, storage_dir=None):
        self.config = config
        self.public_dir = public_dir
        self.project_root = project_root
        self.storage_dir = storage_dir

        if self.storage_dir:
            self.docs_base_dir = os.path.join(self.storage_dir, "reticulum-docs")
            self.meshchatx_docs_dir = os.path.join(self.storage_dir, "meshchatx-docs")
        else:
            self.docs_base_dir = os.path.join(self.public_dir, "reticulum-docs")
            self.meshchatx_docs_dir = os.path.join(self.public_dir, "meshchatx-docs")

        self.docs_dir = os.path.join(self.docs_base_dir, "current")
        self.versions_dir = os.path.join(self.docs_base_dir, "versions")
        self.bundled_docs_dir = os.path.join(self.public_dir, BUNDLED_DOCS_SUBDIR)

        self.upload_status = "idle"
        self.upload_progress = 0
        self.last_error = None

        try:
            for d in [
                self.docs_base_dir,
                self.versions_dir,
                self.docs_dir,
                self.meshchatx_docs_dir,
            ]:
                if not os.path.exists(d):
                    os.makedirs(d)

            if not os.path.exists(self.docs_dir) or not os.listdir(self.docs_dir):
                self._update_current_link()

        except OSError as e:
            logging.exception(f"Failed to create documentation directories: {e}")
            self.last_error = str(e)

        if os.path.exists(self.meshchatx_docs_dir) and os.access(
            self.meshchatx_docs_dir,
            os.W_OK,
        ):
            self.populate_meshchatx_docs()

    def _update_current_link(self, version=None):
        """Update the 'current' directory to point at the chosen or latest version."""
        if not os.path.exists(self.versions_dir):
            return

        versions = self.get_available_versions()
        if not versions:
            return

        target_version = version or versions[-1]

        version_path = os.path.join(self.versions_dir, target_version)
        if not os.path.exists(version_path):
            return

        if os.path.exists(self.docs_dir):
            if os.path.islink(self.docs_dir):
                os.unlink(self.docs_dir)
            else:
                self._remove_tree_force_writable(self.docs_dir)

        try:
            rel_target = os.path.relpath(version_path, os.path.dirname(self.docs_dir))
            os.symlink(rel_target, self.docs_dir)
        except (OSError, AttributeError):
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

        version_file = os.path.join(self.docs_dir, ".version")
        if os.path.exists(version_file):
            try:
                with open(version_file) as f:
                    return f.read().strip()
            except OSError:
                pass

        if self.has_user_docs():
            return "unknown"
        if self.has_bundled_docs():
            return "bundled"
        return None

    def switch_version(self, version):
        if version in self.get_available_versions():
            self._update_current_link(version)
            return True
        return False

    def delete_version(self, version):
        """Delete a specific user-uploaded version of the documentation."""
        if version not in self.get_available_versions():
            return False

        version_path = os.path.join(self.versions_dir, version)
        if not os.path.exists(version_path):
            return False

        try:
            current_version = self.get_current_version()
            if current_version == version:
                if os.path.exists(self.docs_dir):
                    if os.path.islink(self.docs_dir):
                        os.unlink(self.docs_dir)
                    else:
                        self._remove_tree_force_writable(self.docs_dir)

            self._remove_tree_force_writable(version_path)

            if current_version == version:
                self._update_current_link()

            return True
        except Exception as e:
            logging.exception(f"Failed to delete docs version {version}: {e}")
            return False

    def clear_reticulum_docs(self):
        """Remove every user-uploaded Reticulum doc; bundled copy is untouched."""
        try:
            if os.path.exists(self.docs_base_dir):
                for item in os.listdir(self.docs_base_dir):
                    item_path = os.path.join(self.docs_base_dir, item)
                    if os.path.islink(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        self._remove_tree_force_writable(item_path)
                    else:
                        os.remove(item_path)

                for d in [self.versions_dir, self.docs_dir]:
                    if not os.path.exists(d):
                        os.makedirs(d)
                return True
        except Exception as e:
            logging.exception(f"Failed to clear Reticulum docs: {e}")
            return False

    def populate_meshchatx_docs(self):
        """Copy the project's bundled MeshChatX markdown docs into storage."""
        search_paths = []
        if self.project_root:
            search_paths.append(os.path.join(self.project_root, "docs"))

        search_paths.append(os.path.join(self.public_dir, "meshchatx-docs"))

        this_dir = os.path.dirname(os.path.abspath(__file__))
        search_paths.append(
            os.path.abspath(os.path.join(this_dir, "..", "..", "..", "docs")),
        )

        candidate_dirs = [p for p in search_paths if os.path.isdir(p)]
        if not candidate_dirs:
            logging.warning("MeshChatX docs source directory not found.")
            return

        seen_basenames: set[str] = set()
        sourced: list[tuple[str, str]] = []
        for base in candidate_dirs:
            try:
                names = sorted(os.listdir(base))
            except OSError:
                continue
            for file in names:
                if not file.endswith((".md", ".txt")):
                    continue
                if file in seen_basenames:
                    continue
                seen_basenames.add(file)
                sourced.append((file, base))

        if not sourced:
            logging.warning(
                "No MeshChatX .md or .txt files found in docs search paths."
            )
            return

        try:
            index_links: list[str] = []
            for file, src_docs in sourced:
                src_path = os.path.join(src_docs, file)
                dest_path = os.path.join(self.meshchatx_docs_dir, file)

                if os.path.abspath(src_path) != os.path.abspath(
                    dest_path,
                ) and os.access(self.meshchatx_docs_dir, os.W_OK):
                    shutil.copy2(src_path, dest_path)

                try:
                    with open(src_path, encoding="utf-8") as f:
                        content = f.read()

                    html_content = MarkdownRenderer.render(content)
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
                    index_links.append(
                        f'<li class="mb-2"><a href="{html_file}" class="text-blue-400 hover:text-blue-300">{html_file}</a></li>'
                    )
                except Exception as e:
                    logging.exception(f"Failed to render {file} to HTML: {e}")

            # Generate an index.html so /meshchatx-docs/index.html resolves
            if index_links and os.access(self.meshchatx_docs_dir, os.W_OK):
                index_html = f"""<!DOCTYPE html>
<html class="dark">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>MeshChatX Documentation</title>
    <script src="../assets/js/tailwindcss/tailwind-v3.4.3-forms-v0.5.7.js"></script>
    <style>
        body {{ background-color: #111827; color: #f3f4f6; }}
    </style>
</head>
<body class="p-4 md:p-8 max-w-4xl mx-auto">
    <h1 class="text-2xl font-bold mb-4">MeshChatX Documentation</h1>
    <ul class="list-disc pl-5">
        {''.join(index_links)}
    </ul>
</body>
</html>"""
                with open(
                    os.path.join(self.meshchatx_docs_dir, "index.html"),
                    "w",
                    encoding="utf-8",
                ) as f:
                    f.write(index_html)
        except Exception as e:
            logging.exception(f"Failed to populate MeshChatX docs: {e}")

    def get_status(self):
        return {
            "status": self.upload_status,
            "progress": self.upload_progress,
            "last_error": self.last_error,
            "has_docs": self.has_docs(),
            "has_bundled_docs": self.has_bundled_docs(),
            "has_user_docs": self.has_user_docs(),
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
        """Build a ZIP archive containing the active Reticulum docs and MeshChatX docs."""
        buffer = io.BytesIO()
        active_docs_dir = self._active_reticulum_docs_dir()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            if active_docs_dir and os.path.isdir(active_docs_dir):
                for root, _, files in os.walk(active_docs_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.join(
                            "reticulum-docs",
                            os.path.relpath(file_path, active_docs_dir),
                        )
                        zip_file.write(file_path, rel_path)

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

    def export_reticulum_docs(self, root_folder="reticulum_manual"):
        """Build a ZIP of the active Reticulum manual in upload-compatible form.

        The archive lays out files under ``<root_folder>/docs/`` so that another
        MeshChatX instance can re-import it via the ``/api/v1/docs/upload``
        endpoint without modification. Returns ``None`` when no Reticulum docs
        are currently available (neither user-uploaded nor bundled).
        """
        active_docs_dir = self._active_reticulum_docs_dir()
        if not active_docs_dir or not os.path.isdir(active_docs_dir):
            return None

        safe_root = os.path.basename(root_folder.strip()) or "reticulum_manual"
        if safe_root in (".", ".."):
            safe_root = "reticulum_manual"

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for root, _, files in os.walk(active_docs_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join(
                        safe_root,
                        "docs",
                        os.path.relpath(file_path, active_docs_dir),
                    )
                    zip_file.write(file_path, arcname)
        buffer.seek(0)
        return buffer.getvalue()

    def search(self, query, lang="en"):
        if not query:
            return []

        results = []
        query = query.lower()

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

        active_docs_dir = self._active_reticulum_docs_dir()
        if active_docs_dir and os.path.isdir(active_docs_dir):
            known_langs = ["de", "es", "jp", "nl", "pl", "pt-br", "tr", "uk", "zh-cn"]

            target_files = []
            try:
                for root, _, files in os.walk(active_docs_dir):
                    for file in files:
                        if file.endswith(".html"):
                            if lang != "en":
                                if f"_{lang}.html" in file:
                                    target_files.append(os.path.join(root, file))
                            else:
                                has_lang_suffix = False
                                for lang_code in known_langs:
                                    if f"_{lang_code}.html" in file:
                                        has_lang_suffix = True
                                        break
                                if not has_lang_suffix:
                                    target_files.append(os.path.join(root, file))

                if not target_files and lang != "en":
                    for root, _, files in os.walk(active_docs_dir):
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

                            text_content = re.sub(r"<[^>]+>", " ", content)
                            text_content = " ".join(text_content.split())

                            if query in text_content.lower():
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
                                title = re.sub(r"\s+[\u2014-].*$", "", title)

                                idx = text_content.lower().find(query)
                                start = max(0, idx - 80)
                                end = min(len(text_content), idx + len(query) + 120)
                                snippet = text_content[start:end]
                                if start > 0:
                                    snippet = "..." + snippet
                                if end < len(text_content):
                                    snippet = snippet + "..."

                                rel_path = os.path.relpath(file_path, active_docs_dir)
                                results.append(
                                    {
                                        "title": title,
                                        "path": f"/reticulum-docs/{rel_path}",
                                        "snippet": snippet,
                                        "source": "Reticulum",
                                    },
                                )

                                if len(results) >= 25:
                                    break
                    except Exception as e:
                        logging.exception(f"Error searching file {file_path}: {e}")
            except Exception as e:
                logging.exception(f"Search failed: {e}")

        return results

    def has_docs(self):
        """True if either user-uploaded or bundled Reticulum docs are available."""
        return self.has_user_docs() or self.has_bundled_docs()

    def has_user_docs(self):
        if os.path.exists(os.path.join(self.docs_dir, "index.html")):
            return True
        return len(self.get_available_versions()) > 0

    def has_bundled_docs(self):
        return os.path.exists(os.path.join(self.bundled_docs_dir, "index.html"))

    def find_docs_file(self, rel_path):
        """Resolve ``rel_path`` against user docs first, then bundled docs.

        Returns the absolute on-disk path of the matching file, or ``None`` when
        the path either escapes the docs roots or no file exists in either
        location. Path traversal attempts are rejected.
        """
        if rel_path is None:
            rel_path = ""
        for base in (self.docs_dir, self.bundled_docs_dir):
            if not base or not os.path.isdir(base):
                continue
            try:
                candidate = os.path.realpath(os.path.join(base, rel_path))
                base_real = os.path.realpath(base)
            except (ValueError, OSError):
                continue
            if candidate != base_real and not candidate.startswith(base_real + os.sep):
                continue
            if os.path.isfile(candidate):
                return candidate
        return None

    def _active_reticulum_docs_dir(self):
        if os.path.exists(os.path.join(self.docs_dir, "index.html")):
            return self.docs_dir
        if self.has_bundled_docs():
            return self.bundled_docs_dir
        return None

    def upload_zip(self, zip_bytes, version):
        """Extract a user-uploaded docs ZIP into a new version and switch to it."""
        self.upload_status = "extracting"
        self.upload_progress = 0
        self.last_error = None

        try:
            zip_path = os.path.join(self.docs_base_dir, "uploaded.zip")
            with open(zip_path, "wb") as f:
                f.write(zip_bytes)

            self._extract_docs(zip_path, version)

            if os.path.exists(zip_path):
                os.remove(zip_path)

            self.upload_status = "completed"
            self.upload_progress = 100
            self.switch_version(version)
            return True
        except Exception as e:
            self.last_error = str(e)
            self.upload_status = "error"
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
            self._remove_tree_force_writable(version_dir)
        os.makedirs(version_dir, exist_ok=True)
        self._ensure_dir_writable(version_dir)

        temp_extract = os.path.join(self.docs_base_dir, "temp_extract")
        if os.path.exists(temp_extract):
            self._remove_tree_force_writable(temp_extract)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            namelist = zip_ref.namelist()
            if not namelist:
                raise Exception("Zip file is empty")

            root_folder = namelist[0].split("/")[0]

            docs_prefix = f"{root_folder}/docs/"
            has_docs_subfolder = any(m.startswith(docs_prefix) for m in namelist)

            if has_docs_subfolder:
                members_to_extract = [m for m in namelist if m.startswith(docs_prefix)]
                for member in members_to_extract:
                    if ".." in member.split("/"):
                        continue
                    zip_ref.extract(member, temp_extract)

                src_path = os.path.join(temp_extract, root_folder, "docs")
                for item in os.listdir(src_path):
                    s = os.path.join(src_path, item)
                    d = os.path.join(version_dir, item)
                    if os.path.isdir(s):
                        self._copy_tree_no_metadata(s, d)
                    else:
                        self._copy_file_no_metadata(s, d)
            else:
                safe_members = [m for m in namelist if ".." not in m.split("/")]
                zip_ref.extractall(temp_extract, members=safe_members)
                src_path = os.path.join(temp_extract, root_folder)
                if os.path.exists(src_path) and os.path.isdir(src_path):
                    for item in os.listdir(src_path):
                        s = os.path.join(src_path, item)
                        d = os.path.join(version_dir, item)
                        if os.path.isdir(s):
                            self._copy_tree_no_metadata(s, d)
                        else:
                            self._copy_file_no_metadata(s, d)
                else:
                    for item in os.listdir(temp_extract):
                        s = os.path.join(temp_extract, item)
                        d = os.path.join(version_dir, item)
                        if os.path.isdir(s):
                            self._copy_tree_no_metadata(s, d)
                        else:
                            self._copy_file_no_metadata(s, d)

        with open(os.path.join(version_dir, ".version"), "w") as f:
            f.write(version)

        if os.path.exists(temp_extract):
            self._remove_tree_force_writable(temp_extract)

    def _ensure_dir_writable(self, path):
        if not os.path.isdir(path):
            return
        try:
            os.chmod(path, 0o755)  # noqa: S103
        except OSError:
            pass

    def _remove_tree_force_writable(self, path):
        if not os.path.exists(path):
            return
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                file_path = os.path.join(root, name)
                try:
                    os.chmod(file_path, 0o644)
                except OSError:
                    pass
            for name in dirs:
                dir_path = os.path.join(root, name)
                self._ensure_dir_writable(dir_path)
        self._ensure_dir_writable(path)
        shutil.rmtree(path)

    def _copy_file_no_metadata(self, src, dst):
        parent = os.path.dirname(dst)
        if parent:
            os.makedirs(parent, exist_ok=True)
            self._ensure_dir_writable(parent)
        shutil.copyfile(src, dst)
        try:
            os.chmod(dst, 0o644)
        except OSError:
            pass

    def _copy_tree_no_metadata(self, src, dst):
        os.makedirs(dst, exist_ok=True)
        self._ensure_dir_writable(dst)
        for root, dirs, files in os.walk(src):
            rel_root = os.path.relpath(root, src)
            target_root = dst if rel_root == "." else os.path.join(dst, rel_root)
            os.makedirs(target_root, exist_ok=True)
            self._ensure_dir_writable(target_root)
            for dirname in dirs:
                target_dir = os.path.join(target_root, dirname)
                os.makedirs(target_dir, exist_ok=True)
                self._ensure_dir_writable(target_dir)
            for filename in files:
                self._copy_file_no_metadata(
                    os.path.join(root, filename),
                    os.path.join(target_root, filename),
                )
