<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <!-- eslint-disable vue/no-v-html -->
    <div class="flex h-full overflow-hidden bg-sem-canvas text-sem-fg">
        <ArchiveSidebar
            v-if="!isSidebar1Hidden"
            class="w-full shrink-0 sm:w-60 lg:w-64"
            :class="{ 'hidden sm:flex': selectedNodeHash }"
            :nodes="groupedArchives"
            :selected-node-hash="selectedNodeHash"
            :initial-search-query="searchQuery"
            @select-node="onNodeSelect"
            @update:search-query="onSearchQueryChange"
        />

        <div
            v-if="selectedNode && !isSidebar2Hidden"
            class="flex w-full shrink-0 flex-col border-r border-sem-border bg-sem-canvas sm:w-72 lg:w-80"
            :class="{ 'hidden sm:flex': viewingArchive }"
        >
            <div class="flex flex-col gap-2 border-b border-sem-border px-3 py-2.5">
                <div class="flex items-center gap-2">
                    <button
                        type="button"
                        class="rounded-lg p-1 text-sem-fg-muted hover:bg-sem-surface/60 sm:hidden"
                        @click="selectedNodeHash = null"
                    >
                        <MaterialDesignIcon icon-name="arrow-left" class="size-5" />
                    </button>
                    <h2 class="min-w-0 flex-1 truncate text-sm font-semibold">{{ selectedNode.node_name }}</h2>
                    <span class="rounded-full bg-sem-surface-muted px-2 py-0.5 text-xs text-sem-fg-muted">
                        {{ selectedNode.archives.length }}
                    </span>
                </div>

                <div class="flex items-center justify-between gap-2">
                    <button
                        v-if="!selectMode"
                        type="button"
                        class="rounded-lg px-2 py-1 text-xs font-medium text-sem-fg-muted transition-colors hover:bg-sem-surface/60 hover:text-sem-fg"
                        @click="selectMode = true"
                    >
                        {{ $t("common.select") }}
                    </button>
                    <label v-else class="flex cursor-pointer items-center gap-2">
                        <input
                            type="checkbox"
                            class="rounded border-sem-border text-sem-accent focus:ring-sem-accent/30"
                            :checked="isAllSelected"
                            @change="toggleSelectAll"
                        />
                        <span class="text-xs text-sem-fg-muted">{{ $t("archives.select_all") }}</span>
                    </label>

                    <div class="flex items-center gap-1">
                        <template v-if="selectMode && selectedArchives.length > 0">
                            <button
                                type="button"
                                class="rounded-lg p-1.5 text-sem-accent hover:bg-sem-surface/60"
                                :title="$t('archives.export_selected_mu', { count: selectedArchives.length })"
                                @click="exportSelectedArchivesAsMu"
                            >
                                <MaterialDesignIcon icon-name="download" class="size-4" />
                            </button>
                            <button
                                type="button"
                                class="rounded-lg p-1.5 text-red-500 hover:bg-sem-surface/60"
                                :title="$t('archives.delete_selected', { count: selectedArchives.length })"
                                @click="deleteSelected"
                            >
                                <MaterialDesignIcon icon-name="trash-can-outline" class="size-4" />
                            </button>
                        </template>
                        <button
                            v-if="selectMode"
                            type="button"
                            class="rounded-lg px-2 py-1 text-xs font-medium text-sem-fg-muted transition-colors hover:bg-sem-surface/60 hover:text-sem-fg"
                            @click="exitSelectMode"
                        >
                            {{ $t("common.cancel") }}
                        </button>
                    </div>
                </div>
            </div>

            <div class="flex-1 overflow-y-auto">
                <div
                    v-for="archive in selectedNode.archives"
                    :key="archive.id"
                    class="group relative flex items-stretch border-b border-sem-border/50 transition-colors hover:bg-sem-surface/40"
                    :class="{
                        'bg-sem-surface/60 ring-1 ring-inset ring-sem-accent/30': viewingArchive?.id === archive.id,
                        'bg-sem-accent/5': selectedArchives.includes(archive.id),
                    }"
                >
                    <div v-if="selectMode" class="flex items-center px-2" @click.stop>
                        <input
                            v-model="selectedArchives"
                            type="checkbox"
                            class="rounded border-sem-border text-sem-accent focus:ring-sem-accent/30"
                            :value="archive.id"
                        />
                    </div>

                    <button
                        type="button"
                        class="min-w-0 flex-1 px-2 py-2.5 text-left"
                        :class="selectMode ? '' : 'pl-3'"
                        @click="viewArchive(archive)"
                    >
                        <div class="truncate text-sm font-medium">{{ archive.page_path || "/" }}</div>
                        <div class="mt-1 flex items-center justify-between gap-2 text-xs text-sem-fg-muted">
                            <span class="inline-flex items-center gap-1">
                                <MaterialDesignIcon icon-name="clock-outline" class="size-3" />
                                {{ formatDate(archive.created_at) }}
                            </span>
                            <span class="font-mono opacity-60">{{ archive.hash.substring(0, 8) }}</span>
                        </div>
                    </button>

                    <button
                        type="button"
                        class="self-center rounded-lg p-2 text-sem-fg-muted opacity-0 transition-opacity hover:text-red-500 group-hover:opacity-100"
                        :title="$t('archives.delete_snapshot')"
                        @click.stop="deleteArchive(archive)"
                    >
                        <MaterialDesignIcon icon-name="trash-can-outline" class="size-4" />
                    </button>
                </div>
            </div>
        </div>

        <div
            class="flex min-w-0 flex-1 flex-col overflow-hidden bg-sem-canvas"
            :class="{ 'hidden sm:flex': !viewingArchive }"
        >
            <div v-if="viewingArchive" class="flex shrink-0 items-center gap-1 border-b border-sem-border px-2 py-2">
                <button
                    type="button"
                    class="rounded-lg p-1 text-sem-fg-muted hover:bg-sem-surface/60 sm:hidden"
                    @click="viewingArchive = null"
                >
                    <MaterialDesignIcon icon-name="arrow-left" class="size-5" />
                </button>

                <div class="min-w-0 flex-1 px-1">
                    <div class="text-xs text-sem-fg-muted">{{ $t("archives.viewing_archive") }}</div>
                    <div class="truncate font-mono text-sm">{{ viewingArchive.page_path || "/" }}</div>
                </div>

                <div class="flex items-center gap-0.5">
                    <button
                        type="button"
                        class="hidden rounded-lg p-2 hover:bg-sem-surface/60 sm:block"
                        :class="isSidebar1Hidden ? 'text-sem-fg-muted' : 'text-sem-accent'"
                        :title="isSidebar1Hidden ? $t('archives.show_nodes') : $t('archives.hide_nodes')"
                        @click="isSidebar1Hidden = !isSidebar1Hidden"
                    >
                        <MaterialDesignIcon icon-name="page-layout-sidebar-left" class="size-4" />
                    </button>
                    <button
                        type="button"
                        class="hidden rounded-lg p-2 hover:bg-sem-surface/60 sm:block"
                        :class="isSidebar2Hidden ? 'text-sem-fg-muted' : 'text-sem-accent'"
                        :title="isSidebar2Hidden ? $t('archives.show_snapshots') : $t('archives.hide_snapshots')"
                        @click="isSidebar2Hidden = !isSidebar2Hidden"
                    >
                        <MaterialDesignIcon icon-name="view-list" class="size-4" />
                    </button>
                    <button
                        type="button"
                        class="rounded-lg p-2 text-sem-fg hover:bg-sem-surface/60"
                        :title="$t('archives.export_mu')"
                        @click="exportArchiveAsMu(viewingArchive)"
                    >
                        <MaterialDesignIcon icon-name="download" class="size-4" />
                    </button>
                    <button
                        type="button"
                        class="rounded-lg p-2 text-sem-accent hover:bg-sem-surface/60"
                        :title="$t('archives.open_live')"
                        @click="openInNomadnet(viewingArchive)"
                    >
                        <MaterialDesignIcon icon-name="open-in-new" class="size-4" />
                    </button>
                    <button
                        type="button"
                        class="hidden rounded-lg p-2 text-sem-fg-muted hover:bg-sem-surface/60 sm:block"
                        :title="$t('common.cancel')"
                        @click="viewingArchive = null"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-5" />
                    </button>
                </div>
            </div>

            <div class="nodeContainer flex-1 overflow-y-auto overscroll-contain p-4">
                <div v-if="isLoading" class="flex h-full items-center justify-center text-sem-fg-muted">
                    <MaterialDesignIcon icon-name="refresh" class="size-8 animate-spin-reverse" />
                </div>
                <div
                    v-else-if="!viewingArchive"
                    class="flex h-full flex-col items-center justify-center gap-3 text-sem-fg-muted"
                >
                    <MaterialDesignIcon icon-name="archive-clock-outline" class="size-14 opacity-30" />
                    <div class="text-sm">{{ $t("archives.select_snapshot") }}</div>
                </div>
                <div
                    v-else
                    class="h-full selection:bg-sem-accent/30"
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
import DownloadUtils from "../../js/DownloadUtils";
import MicronParser from "../../js/MicronParser.js";
import GlobalState from "../../js/GlobalState.js";
import {
    preloadNomadMicronWasm,
    invalidateNomadMicronWasmPreload,
    isMicronWasmBundled,
} from "../../js/MicronWasmLoader.js";
import { renderNomadPageByPath } from "../../js/NomadPageRenderer.js";
import { handleRichHtmlLinkClick } from "../../js/NomadRichHtmlLinks.js";
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
            selectMode: false,
            pagination: {
                page: 1,
                limit: 500, // Reduced from 1000 to improve initial load
            },
            nomadMicronWasmReady: false,
        };
    },
    computed: {
        nomadMicronWasmFeatureEffective() {
            return isMicronWasmBundled() && (GlobalState.config || {}).nomad_micron_wasm_enabled === true;
        },
        nomadMicronWasmActive() {
            const engineWasm = (GlobalState.config?.nomad_micron_default_engine || "js") === "wasm";
            return (
                this.nomadMicronWasmFeatureEffective &&
                this.nomadMicronWasmReady === true &&
                typeof globalThis.micronConvert === "function" &&
                engineWasm
            );
        },
        nomadRenderOptions() {
            const c = GlobalState.config || {};
            const hash = this.viewingArchive?.destination_hash || null;
            const engineWasm = (c.nomad_micron_default_engine || "js") === "wasm";
            return {
                renderMarkdown: c.nomad_render_markdown_enabled !== false,
                renderHtml: c.nomad_render_html_enabled !== false,
                renderPlaintext: c.nomad_render_plaintext_enabled !== false,
                nomadDestinationHash: hash,
                nomad_micron_wasm_use:
                    this.nomadMicronWasmFeatureEffective && this.nomadMicronWasmReady === true && engineWasm,
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
                return ["wrap-break-word", "whitespace-pre-wrap", "text-gray-100"];
            }
            const pl = (a.page_path || "").split("`")[0].toLowerCase();
            const isRich = pl.endsWith(".mu") || pl.endsWith(".md") || pl.endsWith(".html");
            const isHtml = pl.endsWith(".html");
            const isMd = pl.endsWith(".md");
            const classes = ["wrap-break-word"];
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

        this.$watch(
            () => GlobalState.config?.nomad_micron_wasm_enabled,
            async (enabled) => {
                if (!isMicronWasmBundled()) {
                    this.nomadMicronWasmReady = false;
                    return;
                }
                if (!enabled) {
                    this.nomadMicronWasmReady = false;
                    return;
                }
                invalidateNomadMicronWasmPreload();
                this.nomadMicronWasmReady = await preloadNomadMicronWasm();
                const a = this.viewingArchive;
                if (a) {
                    this.renderedContent = this.renderFullContent(a);
                }
            }
        );

        this.$watch(
            () => GlobalState.config?.nomad_micron_default_engine,
            () => {
                const a = this.viewingArchive;
                if (a) {
                    this.renderedContent = this.renderFullContent(a);
                }
            }
        );

        if (isMicronWasmBundled() && GlobalState.config?.nomad_micron_wasm_enabled === true) {
            preloadNomadMicronWasm().then((ok) => {
                this.nomadMicronWasmReady = ok === true;
                const a = this.viewingArchive;
                if (a && ok) {
                    this.renderedContent = this.renderFullContent(a);
                }
            });
        }
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
            this.selectMode = false;
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
        exitSelectMode() {
            this.selectMode = false;
            this.selectedArchives = [];
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
            handleRichHtmlLinkClick(event, {
                onNomadUrl: (url) => {
                    const [hash, ...pathParts] = url.split(":");
                    const path = pathParts.join(":");
                    this.$router.push({
                        name: "nomadnetwork",
                        params: { destinationHash: hash },
                        query: { path: path },
                    });
                },
                onOpenNode: (destination) => {
                    const [hash, ...pathParts] = destination.split(":");
                    const path = pathParts.join(":") || "/page/index.mu";
                    this.$router.push({
                        name: "nomadnetwork",
                        params: { destinationHash: hash },
                        query: { path: path },
                    });
                },
            });
        },
        async downloadTextAsFile(content, filename) {
            const blob = new Blob([content ?? ""], { type: "text/plain;charset=utf-8" });
            await DownloadUtils.downloadFile(filename, blob);
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
            const micronOpts = {
                useWasm: this.nomadMicronWasmActive,
            };
            try {
                if (!hasKnownExt && archive.content.includes("`")) {
                    return new MicronParser().convertMicronToHtml(archive.content, {}, micronOpts);
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
