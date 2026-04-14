<template>
    <!-- eslint-disable vue/no-v-html -->
    <div class="flex h-full overflow-hidden bg-white dark:bg-zinc-950">
        <!-- Sidebar 1: Nodes -->
        <ArchiveSidebar
            v-if="!isSidebar1Hidden"
            class="w-full sm:w-64 md:max-lg:w-56 lg:w-64 shrink-0 border-r border-gray-200 dark:border-zinc-800"
            :class="{ 'hidden sm:flex': selectedNodeHash }"
            :nodes="groupedArchives"
            :selected-node-hash="selectedNodeHash"
            :initial-search-query="searchQuery"
            @select-node="onNodeSelect"
            @update:search-query="onSearchQueryChange"
        />

        <!-- Sidebar 2: Snapshots -->
        <div
            v-if="selectedNode && !isSidebar2Hidden"
            class="flex w-full shrink-0 flex-col border-r border-gray-200 bg-white dark:border-zinc-800 dark:bg-zinc-950 sm:w-80 md:max-lg:w-64 md:max-lg:min-w-64 lg:w-80 lg:min-w-80"
            :class="{ 'hidden sm:flex': viewingArchive }"
        >
            <div
                class="flex flex-col gap-3 border-b border-gray-200 bg-white p-3 dark:border-zinc-800 dark:bg-zinc-950"
            >
                <div class="flex items-center gap-2">
                    <button class="sm:hidden p-1 -ml-1 text-gray-500" @click="selectedNodeHash = null">
                        <MaterialDesignIcon icon-name="arrow-left" class="size-6" />
                    </button>
                    <h2
                        class="font-bold text-xs uppercase tracking-wider text-gray-500 dark:text-gray-400 truncate flex-1"
                    >
                        {{ selectedNode.node_name }}
                    </h2>
                    <div
                        class="text-[10px] font-bold px-1.5 py-0.5 bg-gray-200 dark:bg-zinc-700 text-gray-600 dark:text-gray-400 rounded"
                    >
                        {{ selectedNode.archives.length }}
                    </div>
                </div>

                <!-- Multi-select controls -->
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <label class="flex items-center gap-2 cursor-pointer group">
                            <input
                                type="checkbox"
                                class="rounded border-gray-300 dark:border-zinc-700 text-blue-500 focus:ring-blue-500/20 bg-white dark:bg-zinc-800"
                                :checked="isAllSelected"
                                @change="toggleSelectAll"
                            />
                            <span
                                class="text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-zinc-500 group-hover:text-gray-600 dark:group-hover:text-zinc-400 transition-colors"
                                >Select All</span
                            >
                        </label>
                    </div>

                    <button
                        v-if="selectedArchives.length > 0"
                        class="text-[10px] font-bold uppercase tracking-wider text-blue-500 hover:text-blue-600 transition-colors flex items-center gap-1 mr-2"
                        @click="exportSelectedArchivesAsMu"
                    >
                        <MaterialDesignIcon icon-name="download" class="size-3.5" />
                        {{ $t("archives.export_selected_mu", { count: selectedArchives.length }) }}
                    </button>
                    <button
                        v-if="selectedArchives.length > 0"
                        class="text-[10px] font-bold uppercase tracking-wider text-red-500 hover:text-red-600 transition-colors flex items-center gap-1"
                        @click="deleteSelected"
                    >
                        <MaterialDesignIcon icon-name="trash-can-outline" class="size-3.5" />
                        Delete ({{ selectedArchives.length }})
                    </button>
                </div>
            </div>

            <div class="flex-1 overflow-y-auto">
                <div
                    v-for="archive in selectedNode.archives"
                    :key="archive.id"
                    class="w-full text-left border-b border-gray-100 dark:border-zinc-800/50 hover:bg-white dark:hover:bg-zinc-800 transition-colors flex items-stretch group relative"
                    :class="{
                        'bg-white dark:bg-zinc-800 ring-1 ring-inset ring-blue-500/50 z-10':
                            viewingArchive?.id === archive.id,
                        'bg-blue-50/50 dark:bg-blue-900/10': selectedArchives.includes(archive.id),
                    }"
                >
                    <!-- Checkbox Area -->
                    <div
                        class="px-3 flex items-center justify-center border-r border-transparent group-hover:border-gray-100 dark:group-hover:border-zinc-800/50"
                        @click.stop
                    >
                        <input
                            v-model="selectedArchives"
                            type="checkbox"
                            class="rounded border-gray-300 dark:border-zinc-700 text-blue-500 focus:ring-blue-500/20 bg-white dark:bg-zinc-800"
                            :value="archive.id"
                        />
                    </div>

                    <!-- Content Area -->
                    <button class="flex-1 text-left p-4 pl-1" @click="viewArchive(archive)">
                        <div class="text-sm font-bold text-gray-900 dark:text-white mb-1 truncate">
                            {{ archive.page_path || "/" }}
                        </div>
                        <div
                            class="flex items-center justify-between text-[10px] text-gray-500 dark:text-gray-400 font-medium"
                        >
                            <div class="flex items-center gap-1">
                                <MaterialDesignIcon icon-name="clock-outline" class="size-3" />
                                <span>{{ formatDate(archive.created_at) }}</span>
                            </div>
                            <div class="font-mono opacity-50">{{ archive.hash.substring(0, 8) }}</div>
                        </div>
                    </button>

                    <!-- Individual Delete (visible on hover) -->
                    <button
                        class="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all"
                        title="Delete snapshot"
                        @click.stop="deleteArchive(archive)"
                    >
                        <MaterialDesignIcon icon-name="trash-can-outline" class="size-4" />
                    </button>
                </div>
            </div>
        </div>

        <!-- Main Content: The Micron Render -->
        <div
            class="flex-1 flex flex-col min-w-0 bg-black overflow-hidden"
            :class="{ 'hidden sm:flex': !viewingArchive }"
        >
            <!-- Content Header -->
            <div
                v-if="viewingArchive"
                class="flex shrink-0 items-center gap-2 border-b border-gray-200 bg-white p-2 text-gray-900 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-100"
            >
                <button class="p-1 text-gray-500 sm:hidden dark:text-zinc-500" @click="viewingArchive = null">
                    <MaterialDesignIcon icon-name="arrow-left" class="size-6" />
                </button>

                <div class="min-w-0 flex-1 px-2">
                    <div
                        class="mb-0.5 text-[10px] font-bold uppercase tracking-widest text-gray-500 dark:text-zinc-500"
                    >
                        Viewing Archive
                    </div>
                    <div class="truncate font-mono text-sm text-gray-900 dark:text-white">
                        {{ viewingArchive.page_path || "/" }}
                    </div>
                </div>

                <div class="flex items-center gap-1">
                    <button
                        class="hidden rounded p-2 transition-colors hover:bg-gray-100 dark:hover:bg-zinc-800 sm:block"
                        :class="{
                            'text-blue-600 dark:text-blue-400': !isSidebar1Hidden,
                            'text-gray-400 dark:text-zinc-500': isSidebar1Hidden,
                        }"
                        :title="isSidebar1Hidden ? 'Show Nodes' : 'Hide Nodes'"
                        @click="isSidebar1Hidden = !isSidebar1Hidden"
                    >
                        <MaterialDesignIcon icon-name="page-layout-sidebar-left" class="size-4" />
                    </button>
                    <button
                        class="hidden rounded p-2 transition-colors hover:bg-gray-100 dark:hover:bg-zinc-800 sm:block"
                        :class="{
                            'text-blue-600 dark:text-blue-400': !isSidebar2Hidden,
                            'text-gray-400 dark:text-zinc-500': isSidebar2Hidden,
                        }"
                        :title="isSidebar2Hidden ? 'Show Snapshots' : 'Hide Snapshots'"
                        @click="isSidebar2Hidden = !isSidebar2Hidden"
                    >
                        <MaterialDesignIcon icon-name="view-list" class="size-4" />
                    </button>
                    <div class="mx-1 hidden h-6 w-px bg-gray-200 dark:bg-zinc-800 sm:block"></div>
                    <button
                        class="flex items-center gap-2 rounded p-2 text-gray-700 transition-colors hover:bg-gray-100 dark:text-zinc-300 dark:hover:bg-zinc-800"
                        :title="$t('archives.export_mu')"
                        @click="exportArchiveAsMu(viewingArchive)"
                    >
                        <MaterialDesignIcon icon-name="download" class="size-4" />
                        <span class="hidden text-xs font-bold uppercase tracking-wider xs:inline">{{
                            $t("archives.export_mu")
                        }}</span>
                    </button>
                    <div class="mx-1 hidden h-6 w-px bg-gray-200 dark:bg-zinc-800 xs:block"></div>
                    <button
                        class="flex items-center gap-2 rounded p-2 text-blue-600 transition-colors hover:bg-gray-100 dark:text-blue-400 dark:hover:bg-zinc-800"
                        @click="openInNomadnet(viewingArchive)"
                    >
                        <MaterialDesignIcon icon-name="open-in-new" class="size-4" />
                        <span class="hidden text-xs font-bold uppercase tracking-wider xs:inline">Open Live</span>
                    </button>
                    <div class="mx-1 hidden h-6 w-px bg-gray-200 dark:bg-zinc-800 xs:block"></div>
                    <button
                        class="hidden rounded p-2 transition-colors hover:bg-gray-100 dark:hover:bg-zinc-800 sm:block"
                        title="Close"
                        @click="viewingArchive = null"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-5" />
                    </button>
                </div>
            </div>

            <!-- Rendered Content -->
            <div class="flex-1 overflow-y-auto p-4 nodeContainer overscroll-contain">
                <div v-if="isLoading" class="flex items-center justify-center h-full text-zinc-500">
                    <MaterialDesignIcon icon-name="refresh" class="size-8 animate-spin-reverse" />
                </div>
                <div
                    v-else-if="!viewingArchive"
                    class="flex flex-col items-center justify-center h-full text-zinc-600 gap-4"
                >
                    <MaterialDesignIcon icon-name="archive-clock-outline" class="size-16 opacity-20" />
                    <div class="text-sm font-bold uppercase tracking-widest opacity-50">Select a snapshot to view</div>
                </div>
                <div
                    v-else
                    class="h-full selection:bg-blue-500/30"
                    :class="archiveViewerClasses"
                    @click.capture="onArchiveContentClick"
                    v-html="renderedContent"
                ></div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import Utils from "../../js/Utils";
import MicronParser from "../../js/MicronParser.js";
import GlobalState from "../../js/GlobalState.js";
import { renderNomadPageByPath } from "../../js/NomadPageRenderer.js";
import ArchiveSidebar from "./ArchiveSidebar.vue";

export default {
    name: "ArchivesPage",
    components: {
        MaterialDesignIcon,
        ArchiveSidebar,
    },
    data() {
        return {
            archives: [],
            isLoading: false,
            selectedNodeHash: null,
            viewingArchive: null,
            isSidebar1Hidden: false,
            isSidebar2Hidden: false,
            renderedContent: "",
            searchQuery: "",
            selectedArchives: [],
            pagination: {
                page: 1,
                limit: 500, // Reduced from 1000 to improve initial load
            },
        };
    },
    computed: {
        nomadRenderOptions() {
            const c = GlobalState.config || {};
            const hash = this.viewingArchive?.destination_hash || null;
            return {
                renderMarkdown: c.nomad_render_markdown_enabled !== false,
                renderHtml: c.nomad_render_html_enabled !== false,
                renderPlaintext: c.nomad_render_plaintext_enabled !== false,
                nomadDestinationHash: hash,
            };
        },
        selectedNode() {
            if (!this.selectedNodeHash) return null;
            return this.groupedArchives.find((g) => g.destination_hash === this.selectedNodeHash);
        },
        isAllSelected() {
            if (!this.selectedNode || this.selectedNode.archives.length === 0) return false;
            return this.selectedNode.archives.every((a) => this.selectedArchives.includes(a.id));
        },
        archiveViewerClasses() {
            const a = this.viewingArchive;
            if (!a?.page_path) {
                return ["break-words", "whitespace-pre-wrap", "text-gray-100"];
            }
            const pl = (a.page_path || "").split("`")[0].toLowerCase();
            const isRich = pl.endsWith(".mu") || pl.endsWith(".md") || pl.endsWith(".html");
            const isHtml = pl.endsWith(".html");
            const isMd = pl.endsWith(".md");
            const classes = ["break-words"];
            if (isRich) {
                classes.push("nomad-page-rich");
            } else {
                classes.push("whitespace-pre-wrap");
            }
            if (isHtml) {
                classes.push("nomad-page-html-host");
            } else {
                classes.push("text-gray-100");
            }
            if (isMd) {
                classes.push("nomad-markdown-host");
            }
            return classes;
        },
        groupedArchives() {
            // Optimization: Use a simple object for grouping
            const groups = {};
            const list = this.archives || [];
            for (let i = 0; i < list.length; i++) {
                const archive = list[i];
                const hash = archive.destination_hash;
                if (!groups[hash]) {
                    groups[hash] = {
                        destination_hash: hash,
                        node_name: archive.node_name,
                        archives: [],
                    };
                }
                groups[hash].archives.push(archive);
            }

            return Object.values(groups).sort((a, b) => {
                // Sort by latest archive date
                const dateA = new Date(a.archives[0].created_at);
                const dateB = new Date(b.archives[0].created_at);
                return dateB - dateA;
            });
        },
    },
    watch: {
        groupedArchives(newVal) {
            if (!this.selectedNodeHash && newVal.length > 0 && window.innerWidth >= 640) {
                this.selectedNodeHash = newVal[0].destination_hash;
            }
        },
        viewingArchive(newVal) {
            if (newVal) {
                // Defer heavy rendering to next tick or use a small delay to prevent UI freezing
                this.renderedContent = "Rendering...";
                setTimeout(() => {
                    this.renderedContent = this.renderFullContent(newVal);
                }, 10);
            } else {
                this.renderedContent = "";
                this.isSidebar1Hidden = false;
                this.isSidebar2Hidden = false;
            }
        },
    },
    mounted() {
        this.getArchives();
    },
    methods: {
        async getArchives() {
            this.isLoading = true;
            try {
                const response = await window.api.get("/api/v1/nomadnet/archives", {
                    params: {
                        page: 1,
                        limit: 500,
                        q: this.searchQuery,
                    },
                });
                this.archives = response.data.archives;
            } catch (e) {
                console.error("Failed to load archives:", e);
            } finally {
                this.isLoading = false;
            }
        },
        onSearchQueryChange(query) {
            this.searchQuery = query;
            // Debounce search
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.getArchives();
            }, 300);
        },
        onNodeSelect(node) {
            this.selectedNodeHash = node.destination_hash;
            this.selectedArchives = [];
            // On desktop, auto-select latest archive. On mobile, just show the list.
            if (window.innerWidth >= 640 && node.archives && node.archives.length > 0) {
                this.viewingArchive = node.archives[0];
            } else {
                this.viewingArchive = null;
            }
        },
        toggleSelectAll() {
            if (this.isAllSelected) {
                this.selectedArchives = [];
            } else if (this.selectedNode) {
                this.selectedArchives = this.selectedNode.archives.map((a) => a.id);
            }
        },
        async deleteSelected() {
            if (this.selectedArchives.length === 0) return;

            if (!confirm(`Are you sure you want to delete ${this.selectedArchives.length} selected snapshots?`)) {
                return;
            }

            try {
                await window.api.delete("/api/v1/nomadnet/archives", {
                    data: { ids: this.selectedArchives },
                });

                // Remove from local list
                this.archives = this.archives.filter((a) => !this.selectedArchives.includes(a.id));
                this.selectedArchives = [];

                if (this.viewingArchive && !this.archives.find((a) => a.id === this.viewingArchive.id)) {
                    this.viewingArchive = null;
                }

                // If current node has no more archives, deselect it
                if (this.selectedNode && this.selectedNode.archives.length === 0) {
                    this.selectedNodeHash = null;
                }
            } catch (e) {
                console.error("Failed to delete archives:", e);
                alert("Failed to delete snapshots. Please try again.");
            }
        },
        async deleteArchive(archive) {
            if (!confirm("Are you sure you want to delete this snapshot?")) {
                return;
            }

            try {
                await window.api.delete("/api/v1/nomadnet/archives", {
                    data: { ids: [archive.id] },
                });

                // Remove from local list
                this.archives = this.archives.filter((a) => a.id !== archive.id);
                this.selectedArchives = this.selectedArchives.filter((id) => id !== archive.id);

                if (this.viewingArchive?.id === archive.id) {
                    this.viewingArchive = null;
                }

                // If current node has no more archives, deselect it
                if (this.selectedNode && this.selectedNode.archives.length === 0) {
                    this.selectedNodeHash = null;
                }
            } catch (e) {
                console.error("Failed to delete archive:", e);
                alert("Failed to delete snapshot. Please try again.");
            }
        },
        viewArchive(archive) {
            this.viewingArchive = archive;
        },
        openInNomadnet(archive) {
            this.$router.push({
                name: "nomadnetwork",
                params: { destinationHash: archive.destination_hash },
                query: {
                    path: archive.page_path,
                    archive_id: archive.id,
                },
            });
        },
        formatDate(dateStr) {
            return Utils.formatTimeAgo(dateStr);
        },
        onArchiveContentClick(event) {
            const nomadLink = event.target.closest("a.nomadnet-link[data-nomadnet-url]");
            if (nomadLink) {
                event.preventDefault();
                event.stopPropagation();
                const url = nomadLink.getAttribute("data-nomadnet-url");
                if (!url) {
                    return;
                }
                const [hash, ...pathParts] = url.split(":");
                const path = pathParts.join(":");
                this.$router.push({
                    name: "nomadnetwork",
                    params: { destinationHash: hash },
                    query: { path: path },
                });
                return;
            }
            const fragAnchor = event.target.closest("a[href]");
            if (
                fragAnchor &&
                fragAnchor.getAttribute("href") &&
                fragAnchor.getAttribute("href") !== "#" &&
                fragAnchor.getAttribute("href").startsWith("#") &&
                !fragAnchor.getAttribute("data-nomadnet-url")
            ) {
                event.preventDefault();
                event.stopPropagation();
                const raw = fragAnchor.getAttribute("href").slice(1);
                const id = decodeURIComponent(raw);
                const el = document.getElementById(id);
                if (el) {
                    el.scrollIntoView({ behavior: "smooth", block: "nearest" });
                }
            }
        },
        downloadTextAsFile(content, filename) {
            const blob = new Blob([content ?? ""], { type: "text/plain;charset=utf-8" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = filename;
            a.rel = "noopener";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        },
        muExportBasename(archive) {
            let base = (archive.page_path || "page").split("/").pop() || "page";
            base = base.replace(/[\\/:*?"<>|]+/g, "_").trim() || "page";
            return base;
        },
        muExportFilename(archive) {
            let base = this.muExportBasename(archive);
            const lower = base.toLowerCase();
            const allowed = [".mu", ".md", ".txt", ".html"];
            if (allowed.some((ext) => lower.endsWith(ext))) {
                return base;
            }
            const without = base.includes(".") ? base.replace(/\.[^.]+$/, "") : base;
            return `${without || "page"}.mu`;
        },
        muExportFilenameDisambiguated(archive) {
            const name = this.muExportFilename(archive);
            const m = name.match(/^(.+)(\.[^.]+)$/);
            const stem = m ? m[1] : name.replace(/\.[^.]+$/, "");
            const ext = m ? m[2] : ".mu";
            const short = (archive.hash || "snap").substring(0, 8);
            return `${stem}_${short}${ext}`;
        },
        exportArchiveAsMu(archive) {
            if (!archive) {
                return;
            }
            this.downloadTextAsFile(archive.content, this.muExportFilename(archive));
        },
        exportSelectedArchivesAsMu() {
            const list = this.archives.filter((a) => this.selectedArchives.includes(a.id));
            list.forEach((archive, i) => {
                window.setTimeout(() => {
                    this.downloadTextAsFile(archive.content, this.muExportFilenameDisambiguated(archive));
                }, i * 120);
            });
        },
        renderFullContent(archive) {
            if (!archive.content) {
                return "";
            }
            const pathPart = (archive.page_path || "").split("`")[0];
            const pl = pathPart.toLowerCase();
            const hasKnownExt = /\.(mu|md|txt|html)$/.test(pl);
            try {
                if (!hasKnownExt && archive.content.includes("`")) {
                    return new MicronParser().convertMicronToHtml(archive.content, {});
                }
                return renderNomadPageByPath(pathPart, archive.content, {}, MicronParser, this.nomadRenderOptions);
            } catch (e) {
                console.error("Archive render failed", e);
                return String(archive.content)
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;")
                    .replace(/"/g, "&quot;")
                    .replace(/'/g, "&#039;");
            }
        },
    },
};
</script>

<style scoped>
pre {
    font-family: "Roboto Mono Nerd Font", ui-monospace, monospace;
    font-size: 13px;
    line-height: 1.5;
    letter-spacing: normal;
    font-variant-ligatures: none;
    font-feature-settings: normal;
}

/* Ensure long pages don't lag the layout */
.nodeContainer {
    contain: content;
}

:deep(.nodeContainer) a {
    color: #3b82f6;
    text-decoration: underline;
}

:deep(.nodeContainer) p {
    margin: 0.5rem 0;
}

:deep(.nodeContainer) h1,
:deep(.nodeContainer) h2,
:deep(.nodeContainer) h3 {
    margin: 1.25rem 0 0.75rem 0;
    font-weight: bold;
    line-height: 1.2;
}

:deep(.nodeContainer) h1 {
    font-size: 1.5rem;
}
:deep(.nodeContainer) h2 {
    font-size: 1.25rem;
}
:deep(.nodeContainer) h3 {
    font-size: 1.1rem;
}

:deep(.nodeContainer) hr {
    margin: 1.5rem 0;
    border: 0;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
}
</style>

<style>
/* Match NomadNetworkPage so archives render Markdown/HTML before that route is loaded */
.nomad-markdown-host {
    font-family: ui-sans-serif, system-ui, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
}

.nomad-markdown-host .nomad-markdown {
    white-space: pre-wrap;
    word-wrap: break-word;
}

.nomad-markdown-host .nomad-markdown table {
    white-space: normal;
}

.nomad-markdown-host .nomad-markdown h1 {
    font-size: 1.875rem;
    line-height: 2.25rem;
    font-weight: 700;
    margin: 0.75rem 0 0.5rem;
}

.nomad-markdown-host .nomad-markdown h2 {
    font-size: 1.5rem;
    line-height: 2rem;
    font-weight: 700;
    margin: 0.65rem 0 0.45rem;
}

.nomad-markdown-host .nomad-markdown h3 {
    font-size: 1.25rem;
    line-height: 1.75rem;
    font-weight: 600;
    margin: 0.55rem 0 0.4rem;
}

.nomad-markdown-host .nomad-markdown h4 {
    font-size: 1.125rem;
    line-height: 1.75rem;
    font-weight: 600;
    margin: 0.5rem 0 0.35rem;
}

.nomad-markdown-host .nomad-markdown h5,
.nomad-markdown-host .nomad-markdown h6 {
    font-size: 1rem;
    line-height: 1.5rem;
    font-weight: 600;
    margin: 0.45rem 0 0.3rem;
}

.nomad-markdown-host .nomad-markdown p {
    margin: 0.4rem 0;
}

.nomad-markdown-host .nomad-markdown ul,
.nomad-markdown-host .nomad-markdown ol {
    margin: 0.4rem 0;
    padding-left: 1.5rem;
}

.nomad-markdown-host .nomad-markdown blockquote {
    margin: 0.5rem 0;
    padding-left: 0.75rem;
    border-left: 3px solid rgb(107 114 128);
}

.nomad-markdown-host .nomad-markdown pre {
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-x: auto;
}

.nomad-page-html-host {
    font-family: ui-sans-serif, system-ui, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
}

.nomad-page-html-host .nomad-html-root {
    color: rgb(229 231 235);
}
</style>
