<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex h-full min-h-0 flex-col overflow-hidden bg-sem-canvas text-sem-fg">
        <div class="shrink-0 border-b border-sem-border px-3 py-3 sm:px-4">
            <div class="mx-auto flex w-full max-w-6xl flex-col gap-3">
                <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0">
                        <h1 class="text-lg font-semibold sm:text-xl">{{ $t("archives.title") }}</h1>
                        <p class="mt-0.5 text-xs text-sem-fg-muted sm:text-sm">{{ $t("archives.description") }}</p>
                    </div>
                    <button
                        v-if="viewingArchive && !isWideSplit"
                        type="button"
                        class="rounded-lg p-2 text-sem-fg-muted hover:bg-sem-surface/60"
                        :title="$t('archives.close_viewer')"
                        @click="closeViewer"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-5" />
                    </button>
                </div>

                <div v-show="!viewingArchive || isWideSplit" class="relative">
                    <MaterialDesignIcon
                        icon-name="magnify"
                        class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-sem-fg-muted"
                    />
                    <input
                        v-model="searchQuery"
                        type="search"
                        :placeholder="$t('archives.search_placeholder')"
                        class="w-full rounded-xl border border-sem-border bg-sem-surface py-2.5 pl-10 pr-10 text-sm text-sem-fg placeholder:text-sem-fg-muted focus:border-sem-accent focus:outline-hidden focus:ring-2 focus:ring-sem-accent/20"
                        @input="onSearchInput"
                    />
                    <div v-if="isSearching" class="absolute inset-y-0 right-3 flex items-center">
                        <MaterialDesignIcon icon-name="loading" class="size-4 animate-spin text-sem-fg-muted" />
                    </div>
                    <button
                        v-else-if="searchQuery"
                        type="button"
                        class="absolute inset-y-0 right-2 flex items-center rounded p-1 text-sem-fg-muted hover:text-sem-fg"
                        :title="$t('archives.clear_search')"
                        @click="clearSearch"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-4" />
                    </button>
                </div>

                <div
                    v-show="!viewingArchive || isWideSplit"
                    class="flex flex-wrap items-center gap-2 text-xs text-sem-fg-muted"
                >
                    <span
                        v-if="pagination.total_count > 0"
                        class="rounded-full bg-sem-surface-muted px-2 py-0.5 font-medium"
                    >
                        {{
                            searchQuery
                                ? $t("archives.matches_count", { count: pagination.total_count })
                                : $t("archives.showing_range", {
                                      start: rangeStart,
                                      end: rangeEnd,
                                      total: pagination.total_count,
                                  })
                        }}
                    </span>
                    <label class="ml-auto flex items-center gap-1.5">
                        <span>{{ $t("archives.filter_node") }}</span>
                        <select
                            v-model="nodeFilter"
                            class="rounded-lg border border-sem-border bg-sem-canvas px-2 py-1 text-xs text-sem-fg"
                            @change="onFilterChange"
                        >
                            <option value="">{{ $t("archives.all_nodes") }}</option>
                            <option v-for="node in nodeOptions" :key="node.hash" :value="node.hash">
                                {{ node.label }}
                            </option>
                        </select>
                    </label>
                </div>
            </div>
        </div>

        <div
            class="mx-auto flex min-h-0 w-full max-w-6xl flex-1 overflow-hidden"
            :class="isWideSplit ? 'flex-row' : 'flex-col'"
        >
            <div
                v-show="!viewingArchive || isWideSplit"
                class="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden"
                :class="{ 'lg:max-w-md lg:border-r lg:border-sem-border xl:max-w-lg': isWideSplit && viewingArchive }"
            >
                <div v-if="loadError" class="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center">
                    <MaterialDesignIcon icon-name="alert-circle-outline" class="size-10 text-red-400" />
                    <p class="text-sm">{{ $t("archives.search_failed") }}</p>
                    <button type="button" class="text-xs font-medium text-sem-accent" @click="getArchives">
                        {{ $t("archives.retry") }}
                    </button>
                </div>

                <div
                    v-else-if="!isLoading && archives.length === 0"
                    class="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center"
                >
                    <MaterialDesignIcon icon-name="text-search" class="size-12 text-sem-fg-muted opacity-40" />
                    <p class="text-sm font-medium">
                        {{ searchQuery ? $t("archives.no_results") : $t("archives.no_archives") }}
                    </p>
                    <p class="max-w-sm text-xs text-sem-fg-muted">
                        {{ searchQuery ? $t("archives.adjust_filters") : $t("archives.browse_to_archive") }}
                    </p>
                    <button
                        v-if="searchQuery"
                        type="button"
                        class="mt-2 text-xs font-medium text-sem-accent"
                        @click="clearSearch"
                    >
                        {{ $t("archives.clear_search") }}
                    </button>
                </div>

                <div v-else class="flex-1 overflow-y-auto">
                    <div class="grid grid-cols-1 gap-3 p-3 sm:p-4" :class="{ 'sm:grid-cols-2': !viewingArchive }">
                        <article
                            v-for="archive in archives"
                            :key="archive.id"
                            class="group flex cursor-pointer flex-col overflow-hidden rounded-2xl border border-sem-border/70 bg-sem-surface/40 shadow-sm transition-colors hover:border-sem-accent/40 hover:bg-sem-surface/70"
                            :class="{
                                'ring-2 ring-sem-accent/40 border-sem-accent/40': viewingArchive?.id === archive.id,
                            }"
                            @click="openArchive(archive)"
                        >
                            <div
                                class="flex items-start justify-between gap-2 border-b border-sem-border/50 px-3 py-2.5"
                            >
                                <div class="min-w-0">
                                    <h2 class="truncate text-sm font-semibold group-hover:text-sem-accent">
                                        {{ archive.node_name }}
                                    </h2>
                                    <p class="mt-0.5 truncate font-mono text-[11px] text-sem-fg-muted">
                                        {{ archive.page_path || "/" }}
                                    </p>
                                </div>
                                <div class="shrink-0 text-right text-[10px] text-sem-fg-muted">
                                    <div>{{ formatDate(archive.created_at) }}</div>
                                    <div class="mt-0.5 font-mono opacity-70">
                                        {{ (archive.hash || "").substring(0, 8) }}
                                    </div>
                                </div>
                            </div>

                            <div class="archive-card-preview min-h-[5.5rem] flex-1 overflow-hidden px-3 py-2">
                                <!-- eslint-disable vue/no-v-html -- sanitized via renderPreviewHtml -->
                                <div
                                    class="pointer-events-none max-h-36 overflow-hidden text-xs leading-relaxed text-sem-fg-muted"
                                    :class="previewClasses(archive)"
                                    v-html="cardPreviewHtml(archive)"
                                ></div>
                                <!-- eslint-enable vue/no-v-html -->
                            </div>

                            <div
                                class="flex items-center justify-between gap-2 border-t border-sem-border/50 px-3 py-2"
                            >
                                <span
                                    class="rounded bg-sem-surface-muted px-1.5 py-0.5 font-mono text-[10px] text-sem-fg-muted"
                                >
                                    {{ shortHash(archive.destination_hash) }}
                                </span>
                                <span
                                    class="text-[10px] font-medium text-sem-accent opacity-0 transition-opacity group-hover:opacity-100"
                                >
                                    {{ $t("archives.view") }}
                                </span>
                            </div>
                        </article>
                    </div>

                    <div
                        v-if="pagination.total_pages > 1"
                        class="flex items-center justify-center gap-3 border-t border-sem-border px-3 py-3"
                    >
                        <button
                            type="button"
                            class="rounded-lg px-3 py-1.5 text-xs font-medium disabled:opacity-40"
                            :disabled="pagination.page <= 1 || isLoading"
                            @click="goPage(pagination.page - 1)"
                        >
                            {{ $t("archives.prev_page") }}
                        </button>
                        <span class="text-xs text-sem-fg-muted">
                            {{
                                $t("archives.page_of", {
                                    page: pagination.page,
                                    total_pages: pagination.total_pages,
                                })
                            }}
                        </span>
                        <button
                            type="button"
                            class="rounded-lg px-3 py-1.5 text-xs font-medium disabled:opacity-40"
                            :disabled="pagination.page >= pagination.total_pages || isLoading"
                            @click="goPage(pagination.page + 1)"
                        >
                            {{ $t("archives.next_page") }}
                        </button>
                    </div>
                </div>
            </div>

            <div
                v-if="viewingArchive"
                class="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-sem-canvas"
                :class="{ 'border-t border-sem-border lg:border-t-0': !isWideSplit }"
            >
                <div class="flex shrink-0 items-center gap-1 border-b border-sem-border px-2 py-2">
                    <button
                        type="button"
                        class="rounded-lg p-1 text-sem-fg-muted hover:bg-sem-surface/60 lg:hidden"
                        :title="$t('archives.back_to_list')"
                        @click="closeViewer"
                    >
                        <MaterialDesignIcon icon-name="arrow-left" class="size-5" />
                    </button>
                    <div class="min-w-0 flex-1 px-1">
                        <div class="truncate text-xs text-sem-fg-muted">{{ viewingArchive.node_name }}</div>
                        <div class="truncate font-mono text-sm">{{ viewingArchive.page_path || "/" }}</div>
                    </div>
                    <button
                        type="button"
                        class="rounded-lg p-2 text-sem-fg hover:bg-sem-surface/60 disabled:opacity-40"
                        :disabled="isRecrawling"
                        :title="$t('archives.recrawl')"
                        @click="recrawlArchive(viewingArchive)"
                    >
                        <MaterialDesignIcon
                            :icon-name="isRecrawling ? 'loading' : 'refresh'"
                            class="size-4"
                            :class="{ 'animate-spin': isRecrawling }"
                        />
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
                        class="rounded-lg p-2 text-sem-fg-muted hover:bg-sem-surface/60"
                        :title="$t('archives.never_crawl')"
                        @click="optOutNode(viewingArchive)"
                    >
                        <MaterialDesignIcon icon-name="cancel" class="size-4" />
                    </button>
                    <button
                        type="button"
                        class="rounded-lg p-2 text-red-500 hover:bg-sem-surface/60"
                        :title="$t('archives.delete_snapshot')"
                        @click="deleteArchive(viewingArchive)"
                    >
                        <MaterialDesignIcon icon-name="trash-can-outline" class="size-4" />
                    </button>
                    <button
                        type="button"
                        class="hidden rounded-lg p-2 text-sem-fg-muted hover:bg-sem-surface/60 lg:inline-flex"
                        :title="$t('archives.close_viewer')"
                        @click="closeViewer"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-5" />
                    </button>
                </div>

                <div class="nodeContainer flex-1 overflow-y-auto overscroll-contain p-4">
                    <div v-if="isLoadingViewer" class="flex h-full items-center justify-center text-sem-fg-muted">
                        <MaterialDesignIcon icon-name="refresh" class="size-8 animate-spin-reverse" />
                    </div>
                    <!-- eslint-disable vue/no-v-html -- sanitized via renderNomadPageByPath -->
                    <div
                        v-else
                        class="h-full selection:bg-sem-accent/30"
                        :class="archiveViewerClasses"
                        @click.capture="onArchiveContentClick"
                        v-html="renderedContent"
                    ></div>
                    <!-- eslint-enable vue/no-v-html -->
                </div>
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
import { renderNomadPageByPath, isolateNomadLinksInHtml } from "../../js/NomadPageRenderer.js";
import { handleRichHtmlLinkClick } from "../../js/NomadRichHtmlLinks.js";
import DialogUtils from "../../js/DialogUtils";
import ToastUtils from "../../js/ToastUtils";

const SPLIT_MIN_WIDTH = 1024;

export default {
    name: "ArchivesPage",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            archives: [],
            isLoading: false,
            isSearching: false,
            isLoadingViewer: false,
            isRecrawling: false,
            loadError: false,
            viewingArchive: null,
            renderedContent: "",
            searchQuery: "",
            nodeFilter: "",
            nodeOptions: [],
            searchTimeout: null,
            isWideSplit: false,
            cardPreviewCache: {},
            pagination: {
                page: 1,
                limit: 25,
                total_count: 0,
                total_pages: 0,
            },
            nomadMicronWasmReady: false,
        };
    },
    computed: {
        rangeStart() {
            if (!this.pagination.total_count) return 0;
            return (this.pagination.page - 1) * this.pagination.limit + 1;
        },
        rangeEnd() {
            return Math.min(this.pagination.page * this.pagination.limit, this.pagination.total_count);
        },
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
        archiveViewerClasses() {
            return this.pathViewerClasses(this.viewingArchive?.page_path);
        },
    },
    watch: {
        viewingArchive(newVal) {
            if (newVal && newVal.content != null) {
                this.renderedContent = this.$t("archives.rendering");
                this.$nextTick(() => {
                    this.renderedContent = this.renderFullContent(newVal);
                });
            } else if (!newVal) {
                this.renderedContent = "";
            }
        },
        archives() {
            this.cardPreviewCache = {};
        },
    },
    mounted() {
        this.updateWideSplit();
        window.addEventListener("resize", this.updateWideSplit);
        const q = this.$route?.query?.q;
        if (typeof q === "string" && q) {
            this.searchQuery = q;
        }
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
                this.cardPreviewCache = {};
                const a = this.viewingArchive;
                if (a) {
                    this.renderedContent = this.renderFullContent(a);
                }
            }
        );
        this.$watch(
            () => GlobalState.config?.nomad_micron_default_engine,
            () => {
                this.cardPreviewCache = {};
                const a = this.viewingArchive;
                if (a) {
                    this.renderedContent = this.renderFullContent(a);
                }
            }
        );
        if (isMicronWasmBundled() && GlobalState.config?.nomad_micron_wasm_enabled === true) {
            preloadNomadMicronWasm().then((ok) => {
                this.nomadMicronWasmReady = ok === true;
                this.cardPreviewCache = {};
                const a = this.viewingArchive;
                if (a && ok) {
                    this.renderedContent = this.renderFullContent(a);
                }
            });
        }
    },
    beforeUnmount() {
        window.removeEventListener("resize", this.updateWideSplit);
    },
    methods: {
        updateWideSplit() {
            this.isWideSplit = typeof window !== "undefined" && window.innerWidth >= SPLIT_MIN_WIDTH;
        },
        shortHash(hash) {
            return (hash || "").substring(0, 12);
        },
        escapeHtml(value) {
            return String(value ?? "")
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        },
        highlightMatch(snippet) {
            const safe = this.escapeHtml(snippet);
            const q = (this.searchQuery || "").trim();
            if (!q || q.length < 2) {
                return safe;
            }
            const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
            try {
                // eslint-disable-next-line security/detect-non-literal-regexp -- query is escaped above
                const re = new RegExp(`(${escaped})`, "ig");
                return safe.replace(re, '<mark class="bg-sem-accent/30 text-inherit rounded-sm px-0.5">$1</mark>');
            } catch {
                return safe;
            }
        },
        pathViewerClasses(pagePath) {
            if (!pagePath) {
                return ["wrap-break-word", "whitespace-pre-wrap", "text-gray-100"];
            }
            const pl = (pagePath || "").split("`")[0].toLowerCase();
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
        previewClasses(archive) {
            return this.pathViewerClasses(archive?.page_path);
        },
        cardPreviewHtml(archive) {
            const cacheKey = `${archive.id}:${archive.hash || ""}:${this.nomadMicronWasmActive ? "w" : "j"}`;
            if (this.cardPreviewCache[cacheKey]) {
                return this.cardPreviewCache[cacheKey];
            }
            const source = archive.preview || archive.snippet || "";
            if (!source) {
                return "";
            }
            let html = this.renderPreviewHtml(archive.page_path, source, archive.destination_hash);
            if (this.searchQuery && archive.snippet && !archive.preview) {
                html = this.highlightMatch(archive.snippet);
            }
            this.cardPreviewCache[cacheKey] = html;
            return html;
        },
        renderPreviewHtml(pagePath, content, destinationHash) {
            if (!content) {
                return "";
            }
            try {
                return this.renderContentByPath(pagePath, content, destinationHash);
            } catch {
                return this.escapeHtml(content).replace(/\n/g, "<br>");
            }
        },
        async getArchives() {
            this.isLoading = true;
            this.isSearching = Boolean(this.searchQuery);
            this.loadError = false;
            try {
                const params = {
                    page: this.pagination.page,
                    limit: this.pagination.limit,
                    include_content: false,
                };
                if (this.searchQuery) {
                    params.q = this.searchQuery;
                }
                if (this.nodeFilter) {
                    params.destination_hash = this.nodeFilter;
                }
                const response = await window.api.get("/api/v1/nomadnet/archives", { params });
                this.archives = response.data.archives || [];
                const pag = response.data.pagination || {};
                this.pagination = {
                    page: pag.page || this.pagination.page,
                    limit: pag.limit || this.pagination.limit,
                    total_count: pag.total_count || 0,
                    total_pages: pag.total_pages || 0,
                };
                this.refreshNodeOptions();
            } catch (e) {
                console.error("Failed to load archives:", e);
                this.loadError = true;
                ToastUtils.error(this.$t("archives.search_failed"));
            } finally {
                this.isLoading = false;
                this.isSearching = false;
            }
        },
        refreshNodeOptions() {
            const map = new Map();
            for (const a of this.archives) {
                if (!map.has(a.destination_hash)) {
                    map.set(a.destination_hash, {
                        hash: a.destination_hash,
                        label: `${a.node_name} (${this.shortHash(a.destination_hash)})`,
                    });
                }
            }
            if (this.nodeFilter && !map.has(this.nodeFilter)) {
                map.set(this.nodeFilter, {
                    hash: this.nodeFilter,
                    label: this.shortHash(this.nodeFilter),
                });
            }
            this.nodeOptions = Array.from(map.values()).sort((a, b) => a.label.localeCompare(b.label));
        },
        onSearchInput() {
            clearTimeout(this.searchTimeout);
            this.isSearching = true;
            this.searchTimeout = setTimeout(() => {
                this.pagination.page = 1;
                this.getArchives();
            }, 300);
        },
        clearSearch() {
            this.searchQuery = "";
            this.pagination.page = 1;
            this.getArchives();
        },
        onFilterChange() {
            this.pagination.page = 1;
            this.getArchives();
        },
        goPage(page) {
            this.pagination.page = page;
            this.getArchives();
        },
        async openArchive(archive) {
            this.isLoadingViewer = true;
            this.viewingArchive = { ...archive, content: archive.content || null };
            try {
                const response = await window.api.get(`/api/v1/nomadnet/archives/${archive.id}`);
                const full = response.data.archive;
                this.viewingArchive = full;
                this.renderedContent = this.renderFullContent(full);
            } catch (e) {
                console.error("Failed to load archive:", e);
                ToastUtils.error(this.$t("archives.failed_load"));
                this.viewingArchive = null;
            } finally {
                this.isLoadingViewer = false;
            }
        },
        closeViewer() {
            this.viewingArchive = null;
            this.renderedContent = "";
        },
        async recrawlArchive(archive) {
            if (!archive || this.isRecrawling) {
                return;
            }
            this.isRecrawling = true;
            const toastKey = `archives-recrawl-${archive.id || archive.destination_hash}`;
            ToastUtils.loading(this.$t("archives.recrawl_pending"), 0, toastKey);
            try {
                const response = await window.api.post("/api/v1/nomadnet/archives/recrawl", {
                    destination_hash: archive.destination_hash,
                    page_path: archive.page_path,
                });
                ToastUtils.dismiss(toastKey);
                const next = response.data.archive;
                ToastUtils.success(this.$t("archives.recrawl_done"));
                if (next) {
                    this.viewingArchive = next;
                    this.renderedContent = this.renderFullContent(next);
                    const idx = this.archives.findIndex(
                        (a) => a.destination_hash === next.destination_hash && a.page_path === next.page_path
                    );
                    if (idx >= 0) {
                        this.archives.splice(idx, 1, {
                            ...this.archives[idx],
                            ...next,
                            content: undefined,
                        });
                    } else {
                        this.archives.unshift({
                            ...next,
                            content: undefined,
                        });
                    }
                    this.cardPreviewCache = {};
                } else {
                    await this.getArchives();
                }
            } catch (e) {
                ToastUtils.dismiss(toastKey);
                console.error("Recrawl failed:", e);
                const msg = e?.response?.data?.message || this.$t("archives.recrawl_failed");
                ToastUtils.error(msg);
            } finally {
                this.isRecrawling = false;
            }
        },
        async deleteArchive(archive) {
            if (!(await DialogUtils.confirm(this.$t("archives.delete_snapshot_confirm")))) {
                return;
            }
            try {
                await window.api.delete("/api/v1/nomadnet/archives", {
                    data: { ids: [archive.id] },
                });
                this.archives = this.archives.filter((a) => a.id !== archive.id);
                if (this.viewingArchive?.id === archive.id) {
                    this.closeViewer();
                }
                this.pagination.total_count = Math.max(0, this.pagination.total_count - 1);
                ToastUtils.success(this.$t("archives.deleted"));
            } catch (e) {
                console.error("Failed to delete archive:", e);
                ToastUtils.error(this.$t("archives.failed_delete"));
            }
        },
        async optOutNode(archive) {
            if (!(await DialogUtils.confirm(this.$t("archives.never_crawl_confirm")))) {
                return;
            }
            try {
                await window.api.post("/api/v1/nomadnet/crawl/opt-outs", {
                    destination_hash: archive.destination_hash,
                    reason: "user",
                });
                ToastUtils.success(this.$t("archives.never_crawl_saved"));
            } catch (e) {
                console.error("Failed to opt out node:", e);
                ToastUtils.error(this.$t("archives.never_crawl_failed"));
            }
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
        renderContentByPath(pagePath, content, destinationHash) {
            const pathPart = (pagePath || "").split("`")[0];
            const pl = pathPart.toLowerCase();
            const hasKnownExt = /\.(mu|md|txt|html)$/.test(pl);
            const micronOpts = {
                useWasm: this.nomadMicronWasmActive,
            };
            const dest = destinationHash || null;
            if (!hasKnownExt && String(content).includes("`")) {
                let out = new MicronParser().convertMicronToHtml(content, {}, micronOpts);
                if (dest) {
                    out = isolateNomadLinksInHtml(out, dest);
                }
                return out;
            }
            if (!hasKnownExt) {
                // Treat extensionless Nomad pages as Micron (common for index paths).
                let out = new MicronParser().convertMicronToHtml(content, {}, micronOpts);
                if (dest) {
                    out = isolateNomadLinksInHtml(out, dest);
                }
                return out;
            }
            return renderNomadPageByPath(pathPart, content, {}, MicronParser, {
                ...this.nomadRenderOptions,
                nomadDestinationHash: dest || this.nomadRenderOptions.nomadDestinationHash,
            });
        },
        renderFullContent(archive) {
            if (!archive?.content) {
                return "";
            }
            try {
                return this.renderContentByPath(
                    archive.page_path,
                    archive.content,
                    archive.destination_hash || this.viewingArchive?.destination_hash
                );
            } catch (e) {
                console.error("Archive render failed", e);
                return this.escapeHtml(archive.content);
            }
        },
    },
};
</script>

<style scoped>
.nodeContainer {
    contain: content;
}

.archive-card-preview {
    mask-image: linear-gradient(to bottom, #000 70%, transparent 100%);
}

:deep(.nodeContainer) a,
:deep(.archive-card-preview) a {
    color: #3b82f6;
    text-decoration: underline;
}

:deep(.nodeContainer) p,
:deep(.archive-card-preview) p {
    margin: 0.5rem 0;
}

:deep(.nodeContainer) h1,
:deep(.nodeContainer) h2,
:deep(.nodeContainer) h3,
:deep(.archive-card-preview) h1,
:deep(.archive-card-preview) h2,
:deep(.archive-card-preview) h3 {
    margin: 1.25rem 0 0.75rem 0;
    font-weight: bold;
    line-height: 1.2;
}

:deep(.nodeContainer) h1,
:deep(.archive-card-preview) h1 {
    font-size: 1.5rem;
}
:deep(.nodeContainer) h2,
:deep(.archive-card-preview) h2 {
    font-size: 1.25rem;
}
:deep(.nodeContainer) h3,
:deep(.archive-card-preview) h3 {
    font-size: 1.1rem;
}

:deep(.nodeContainer) hr {
    margin: 1.5rem 0;
    border: 0;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
}
</style>

<style>
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
