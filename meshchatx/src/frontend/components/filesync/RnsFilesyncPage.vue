<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
        <ToolsPageHeader
            icon="folder-sync"
            :title="$t('rns_filesync.title')"
            :description="$t('rns_filesync.description')"
            :eyebrow="$t('rns_filesync.eyebrow')"
            accent="green"
        />
        <div
            class="flex-1 overflow-y-auto w-full px-4 md:px-5 lg:px-8 py-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]"
        >
            <div class="space-y-4 w-full max-w-4xl mx-auto">
                <div class="glass-card space-y-5">
                    <div
                        class="p-4 rounded-lg bg-emerald-50/50 dark:bg-emerald-900/10 border border-emerald-100 dark:border-emerald-900/20"
                    >
                        <div
                            class="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-2"
                        >
                            {{ $t("rns_filesync.usage_steps") }}
                        </div>
                        <div class="space-y-1.5 text-xs text-emerald-800/80 dark:text-emerald-300/80 leading-relaxed">
                            <p>{{ $t("rns_filesync.step_1") }}</p>
                            <p>{{ $t("rns_filesync.step_2") }}</p>
                            <p>{{ $t("rns_filesync.step_3") }}</p>
                        </div>
                    </div>

                    <div
                        class="border-b border-sem-border overflow-x-auto overscroll-x-contain -mx-4 px-4 sm:mx-0 sm:px-0"
                    >
                        <div class="flex w-max min-w-full sm:w-auto gap-1 sm:gap-2">
                            <button
                                v-for="tab in tabs"
                                :key="tab.id"
                                type="button"
                                :class="[
                                    activeTab === tab.id
                                        ? 'border-b-2 border-emerald-500 text-emerald-600 dark:text-emerald-400'
                                        : 'text-sem-fg-muted',
                                    'shrink-0 px-3 sm:px-4 py-2 text-sm font-semibold transition',
                                ]"
                                @click="activeTab = tab.id"
                            >
                                {{ $t(tab.labelKey) }}
                            </button>
                        </div>
                    </div>

                    <div v-if="activeTab === 'folder'" class="space-y-4">
                        <div class="rounded-xl border border-sem-border bg-sem-surface-muted/40 p-4 space-y-4">
                            <div class="flex flex-wrap items-center gap-2">
                                <span
                                    class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold"
                                    :class="
                                        status.running
                                            ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
                                            : 'bg-sem-surface-muted text-sem-fg-muted'
                                    "
                                >
                                    <span
                                        class="size-1.5 rounded-full"
                                        :class="status.running ? 'bg-emerald-500' : 'bg-sem-fg-muted'"
                                    ></span>
                                    {{
                                        status.running
                                            ? $t("rns_filesync.status_syncing")
                                            : $t("rns_filesync.status_stopped")
                                    }}
                                </span>
                                <span class="text-xs text-sem-fg-muted">
                                    {{ $t("rns_filesync.peers_count") }}:
                                    <strong class="text-sem-fg">{{ status.peers || 0 }}</strong>
                                </span>
                                <span class="text-xs text-sem-fg-muted">
                                    {{ $t("rns_filesync.files_count") }}:
                                    <strong class="text-sem-fg">{{ status.files || 0 }}</strong>
                                </span>
                            </div>

                            <div>
                                <label class="glass-label">{{ $t("rns_filesync.sync_directory") }}</label>
                                <div class="flex gap-2">
                                    <input
                                        v-model="syncDirectory"
                                        type="text"
                                        class="input-field flex-1 min-w-0 font-mono text-sm"
                                        :disabled="status.running"
                                        :placeholder="$t('rns_filesync.sync_directory_placeholder')"
                                    />
                                    <button
                                        type="button"
                                        class="secondary-chip px-3 py-2 text-xs shrink-0"
                                        :disabled="busy || status.running"
                                        :title="$t('rns_filesync.browse_folder')"
                                        @click="openDirectoryBrowser"
                                    >
                                        <MaterialDesignIcon icon-name="folder-open-outline" class="w-4 h-4" />
                                        <span class="hidden sm:inline">{{ $t("rns_filesync.browse_folder") }}</span>
                                    </button>
                                    <button
                                        type="button"
                                        class="secondary-chip px-3 py-2 text-xs shrink-0"
                                        :disabled="busy || status.running"
                                        :title="$t('rns_filesync.use_shared_folder')"
                                        @click="useSharedFolder"
                                    >
                                        <MaterialDesignIcon icon-name="folder-account-outline" class="w-4 h-4" />
                                        <span class="hidden sm:inline">{{ $t("rns_filesync.use_shared_folder") }}</span>
                                    </button>
                                    <button
                                        type="button"
                                        class="secondary-chip px-3 py-2 text-xs shrink-0"
                                        :disabled="busy || !syncDirectory"
                                        :title="$t('rns_filesync.open_folder')"
                                        @click="openSyncFolder"
                                    >
                                        <MaterialDesignIcon icon-name="folder" class="w-4 h-4" />
                                        <span class="hidden sm:inline">{{ $t("rns_filesync.open_folder") }}</span>
                                    </button>
                                </div>
                                <p class="mt-1.5 text-xs text-sem-fg-muted">
                                    {{ $t("rns_filesync.sync_directory_help") }}
                                </p>
                            </div>

                            <div class="grid gap-3 sm:grid-cols-2">
                                <div>
                                    <label class="glass-label">{{ $t("rns_filesync.announce_interval") }}</label>
                                    <input
                                        v-model.number="announceInterval"
                                        type="number"
                                        min="10"
                                        class="input-field w-full"
                                    />
                                    <p class="mt-1 text-xs text-sem-fg-muted">
                                        {{ $t("rns_filesync.announce_interval_help") }}
                                    </p>
                                </div>
                                <div class="flex items-end">
                                    <label class="flex items-center gap-2 text-sm text-sem-fg pb-2">
                                        <input v-model="monitor" type="checkbox" class="rounded" />
                                        {{ $t("rns_filesync.monitor") }}
                                    </label>
                                </div>
                            </div>

                            <div class="flex flex-wrap gap-2">
                                <button
                                    v-if="!status.running"
                                    type="button"
                                    class="primary-chip px-4 py-2 text-sm"
                                    :disabled="busy"
                                    @click="startService"
                                >
                                    <MaterialDesignIcon icon-name="play" class="w-4 h-4" />
                                    {{ $t("rns_filesync.start") }}
                                </button>
                                <button
                                    v-else
                                    type="button"
                                    class="secondary-chip px-4 py-2 text-sm text-red-600 dark:text-red-300 border-red-200 dark:border-red-500/50"
                                    :disabled="busy"
                                    @click="stopService"
                                >
                                    <MaterialDesignIcon icon-name="stop" class="w-4 h-4" />
                                    {{ $t("rns_filesync.stop") }}
                                </button>
                                <button
                                    type="button"
                                    class="secondary-chip px-4 py-2 text-sm"
                                    :disabled="busy || !status.running"
                                    @click="announceNow"
                                >
                                    <MaterialDesignIcon icon-name="bullhorn" class="w-4 h-4" />
                                    {{ $t("rns_filesync.announce") }}
                                </button>
                                <button
                                    type="button"
                                    class="secondary-chip px-4 py-2 text-sm"
                                    :disabled="busy"
                                    @click="refreshStatus"
                                >
                                    <MaterialDesignIcon icon-name="refresh" class="w-4 h-4" />
                                    {{ $t("rns_filesync.refresh") }}
                                </button>
                            </div>
                        </div>

                        <div v-if="status.destination_hash" class="rounded-xl border border-sem-border p-4 space-y-2">
                            <div class="text-sm font-semibold text-sem-fg">
                                {{ $t("rns_filesync.share_id") }}
                            </div>
                            <p class="text-xs text-sem-fg-muted">{{ $t("rns_filesync.share_id_help") }}</p>
                            <button
                                type="button"
                                class="w-full text-left font-mono text-xs break-all rounded-lg border border-sem-border bg-sem-surface-muted/50 px-3 py-2 hover:border-emerald-500"
                                @click="copyHash(status.destination_hash)"
                            >
                                {{ status.destination_hash }}
                            </button>
                        </div>

                        <div
                            v-if="lastProgressLabel"
                            class="rounded-lg border border-sem-border px-3 py-2 text-xs text-sem-fg-muted"
                        >
                            {{ $t("rns_filesync.last_progress") }}: {{ lastProgressLabel }}
                        </div>
                    </div>

                    <div v-else-if="activeTab === 'devices'" class="space-y-4">
                        <p class="text-sm text-sem-fg-muted">{{ $t("rns_filesync.devices_help") }}</p>
                        <div class="flex flex-col sm:flex-row gap-2">
                            <input
                                v-model="connectHash"
                                type="text"
                                class="input-field flex-1 font-mono text-sm"
                                :placeholder="$t('rns_filesync.peer_hash_placeholder')"
                            />
                            <button
                                type="button"
                                class="primary-chip px-4 py-2 text-sm"
                                :disabled="busy || !status.running"
                                @click="connectPeer"
                            >
                                <MaterialDesignIcon icon-name="link-variant" class="w-4 h-4" />
                                {{ $t("rns_filesync.connect") }}
                            </button>
                        </div>
                        <button
                            type="button"
                            class="secondary-chip px-3 py-1.5 text-sm"
                            :disabled="busy"
                            @click="refreshPeers"
                        >
                            {{ $t("rns_filesync.refresh") }}
                        </button>
                        <div v-if="peers.length === 0" class="text-sm text-sem-fg-muted">
                            {{ $t("rns_filesync.no_peers") }}
                        </div>
                        <ul v-else class="space-y-2">
                            <li
                                v-for="peer in peers"
                                :key="peer.peer_id"
                                class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-lg border border-sem-border"
                            >
                                <div class="min-w-0">
                                    <div class="font-mono text-xs break-all text-sem-fg">{{ peer.peer_id }}</div>
                                    <div class="text-xs text-sem-fg-muted mt-1">
                                        {{ peerStatusLabel(peer) }}
                                        <span v-if="peer.destination_hash" class="font-mono">
                                            · {{ peer.destination_hash }}
                                        </span>
                                    </div>
                                </div>
                                <button
                                    type="button"
                                    class="secondary-chip px-3 py-1.5 text-sm text-red-600 dark:text-red-300"
                                    :disabled="busy"
                                    @click="disconnectPeer(peer.peer_id)"
                                >
                                    {{ $t("rns_filesync.disconnect") }}
                                </button>
                            </li>
                        </ul>
                    </div>

                    <div v-else-if="activeTab === 'files'" class="space-y-4">
                        <FilesyncFileManager
                            ref="fileManager"
                            :sync-directory="syncDirectory"
                            @open-folder="openSyncFolder"
                        />
                    </div>

                    <div v-else-if="activeTab === 'remote'" class="space-y-4">
                        <p class="text-sm text-sem-fg-muted">{{ $t("rns_filesync.remote_help") }}</p>
                        <div class="flex flex-col sm:flex-row gap-2">
                            <select v-model="browsePeerId" class="input-field flex-1 font-mono text-sm">
                                <option value="">{{ $t("rns_filesync.select_peer") }}</option>
                                <option v-for="peer in peers" :key="peer.peer_id" :value="peer.peer_id">
                                    {{ peer.peer_id }}
                                </option>
                            </select>
                            <button
                                type="button"
                                class="primary-chip px-4 py-2 text-sm"
                                :disabled="busy || !status.running || !browsePeerId"
                                @click="browsePeer"
                            >
                                <MaterialDesignIcon icon-name="folder-open-outline" class="w-4 h-4" />
                                {{ $t("rns_filesync.browse") }}
                            </button>
                        </div>
                        <div v-if="remoteFiles.length === 0" class="text-sm text-sem-fg-muted">
                            {{ $t("rns_filesync.no_remote_files") }}
                        </div>
                        <ul v-else class="space-y-2">
                            <li
                                v-for="file in remoteFiles"
                                :key="file.path || file"
                                class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-lg border border-sem-border"
                            >
                                <div class="min-w-0 text-sm break-all text-sem-fg">
                                    {{ file.path || file }}
                                    <span v-if="file.size != null" class="text-xs text-sem-fg-muted">
                                        · {{ formatFileSize(file.size) }}
                                    </span>
                                </div>
                                <button
                                    type="button"
                                    class="secondary-chip px-3 py-1.5 text-sm"
                                    :disabled="busy || !browsePeerId"
                                    @click="downloadFile(file.path || file)"
                                >
                                    {{ $t("rns_filesync.download") }}
                                </button>
                            </li>
                        </ul>
                    </div>

                    <div v-else-if="activeTab === 'sharing'" class="space-y-4">
                        <p class="text-sm text-sem-fg-muted">{{ $t("rns_filesync.sharing_help") }}</p>
                        <label class="flex items-center gap-2 text-sm text-sem-fg">
                            <input v-model="aclEnforce" type="checkbox" class="rounded" @change="saveEnforce" />
                            {{ $t("rns_filesync.acl_enforce") }}
                        </label>
                        <div class="flex flex-col gap-3">
                            <input
                                v-model="aclHash"
                                type="text"
                                class="input-field w-full font-mono text-sm"
                                :placeholder="$t('rns_filesync.peer_hash_placeholder')"
                            />
                            <div class="flex flex-wrap items-center gap-4 text-sm text-sem-fg">
                                <label class="flex items-center gap-1.5">
                                    <input v-model="aclRead" type="checkbox" class="rounded" />
                                    {{ $t("rns_filesync.perm_read") }}
                                </label>
                                <label class="flex items-center gap-1.5">
                                    <input v-model="aclWrite" type="checkbox" class="rounded" />
                                    {{ $t("rns_filesync.perm_write") }}
                                </label>
                                <label class="flex items-center gap-1.5">
                                    <input v-model="aclDelete" type="checkbox" class="rounded" />
                                    {{ $t("rns_filesync.perm_delete") }}
                                </label>
                            </div>
                            <button
                                type="button"
                                class="primary-chip px-4 py-2 text-sm self-start"
                                :disabled="busy"
                                @click="grantAcl"
                            >
                                {{ $t("rns_filesync.acl_grant") }}
                            </button>
                        </div>
                        <div v-if="aclRows.length === 0" class="text-sm text-sem-fg-muted">
                            {{ $t("rns_filesync.no_acl_rules") }}
                        </div>
                        <ul v-else class="space-y-2">
                            <li
                                v-for="row in aclRows"
                                :key="row.hash"
                                class="p-3 rounded-lg border border-sem-border text-sm"
                            >
                                <div class="font-mono text-xs break-all text-sem-fg">{{ row.hash }}</div>
                                <div class="text-xs text-sem-fg-muted mt-1">{{ row.permsLabel }}</div>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>

        <FilesyncDirectoryBrowserModal
            :open="directoryBrowserOpen"
            :initial-path="syncDirectory"
            @close="directoryBrowserOpen = false"
            @select="onDirectorySelected"
        />
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";
import ToolsPageHeader from "../tools/ToolsPageHeader.vue";
import FilesyncDirectoryBrowserModal from "./FilesyncDirectoryBrowserModal.vue";
import FilesyncFileManager from "./FilesyncFileManager.vue";
import ElectronUtils from "../../js/ElectronUtils";
import Utils from "../../js/Utils";
import { onWsEvent, offWsEvent } from "../../js/registries/wsEventRegistry.js";

export default {
    name: "RnsFilesyncPage",
    components: {
        MaterialDesignIcon,
        ToolsPageHeader,
        FilesyncDirectoryBrowserModal,
        FilesyncFileManager,
    },
    data() {
        return {
            activeTab: "folder",
            tabs: [
                { id: "folder", labelKey: "rns_filesync.tab_folder" },
                { id: "devices", labelKey: "rns_filesync.tab_devices" },
                { id: "files", labelKey: "rns_filesync.tab_files" },
                { id: "remote", labelKey: "rns_filesync.tab_remote" },
                { id: "sharing", labelKey: "rns_filesync.tab_sharing" },
            ],
            busy: false,
            status: {
                running: false,
                peers: 0,
                files: 0,
                destination_hash: null,
                sync_directory: "",
                storage_directory: "",
            },
            syncDirectory: "",
            announceInterval: 300,
            monitor: true,
            connectHash: "",
            peers: [],
            browsePeerId: "",
            remoteFiles: [],
            aclEnforce: false,
            aclHash: "",
            aclRead: true,
            aclWrite: false,
            aclDelete: false,
            aclRules: {},
            lastProgress: null,
            directoryBrowserOpen: false,
            wsHandlers: [],
        };
    },
    computed: {
        lastProgressLabel() {
            const payload = this.lastProgress;
            if (!payload) {
                return "";
            }
            if (typeof payload === "string") {
                return payload;
            }
            const path = payload.path || payload.file || payload.name || "";
            const status = payload.status || payload.state || payload.phase || "";
            const bytes = payload.bytes ?? payload.transferred ?? payload.done;
            const total = payload.total ?? payload.size;
            const parts = [];
            if (path) {
                parts.push(String(path));
            }
            if (status) {
                parts.push(String(status));
            }
            if (bytes != null && total != null) {
                parts.push(`${this.formatFileSize(bytes)} / ${this.formatFileSize(total)}`);
            } else if (bytes != null) {
                parts.push(this.formatFileSize(bytes));
            }
            if (parts.length === 0) {
                try {
                    return JSON.stringify(payload);
                } catch {
                    return String(payload);
                }
            }
            return parts.join(" · ");
        },
        aclRows() {
            const rules = this.aclRules || {};
            const byHash = {};
            for (const perm of ["read", "write", "delete"]) {
                const targets = Array.isArray(rules[perm]) ? rules[perm] : [];
                for (const hash of targets) {
                    if (!byHash[hash]) {
                        byHash[hash] = new Set();
                    }
                    byHash[hash].add(perm);
                }
            }
            const labelMap = {
                read: this.$t("rns_filesync.perm_read"),
                write: this.$t("rns_filesync.perm_write"),
                delete: this.$t("rns_filesync.perm_delete"),
            };
            return Object.keys(byHash)
                .sort()
                .map((hash) => ({
                    hash,
                    permsLabel: ["read", "write", "delete"]
                        .filter((p) => byHash[hash].has(p))
                        .map((p) => labelMap[p])
                        .join(", "),
                }));
        },
    },
    async mounted() {
        this.bindWs();
        await this.refreshAll();
    },
    beforeUnmount() {
        for (const [type, handler] of this.wsHandlers) {
            offWsEvent(type, handler);
        }
        this.wsHandlers = [];
    },
    methods: {
        bindWs() {
            const bind = (type, handler) => {
                onWsEvent(type, handler);
                this.wsHandlers.push([type, handler]);
            };
            bind("filesync.sync.progress", (payload) => {
                this.lastProgress = payload && typeof payload === "object" ? payload : { status: String(payload) };
            });
            bind("filesync.peer.connected", async () => {
                await this.refreshPeers();
                await this.refreshStatus();
            });
            bind("filesync.peer.disconnected", async () => {
                await this.refreshPeers();
                await this.refreshStatus();
            });
            bind("filesync.file.updated", async () => {
                await this.refreshFileManager();
                ToastUtils.info(this.$t("rns_filesync.file_updated"));
            });
            bind("filesync.file.deleted", async () => {
                await this.refreshFileManager();
                ToastUtils.info(this.$t("rns_filesync.file_deleted"));
            });
            bind("filesync.error", (payload) => {
                const detail = payload?.error || payload?.message || "";
                ToastUtils.error(`${this.$t("rns_filesync.error")}${detail ? ": " + detail : ""}`);
            });
        },
        formatFileSize(bytes) {
            return Utils.formatBytes(bytes || 0);
        },
        peerStatusLabel(peer) {
            const raw = peer?.status;
            if (raw === 1 || raw === "connected" || raw === true) {
                return this.$t("rns_filesync.peer_connected");
            }
            if (raw === 0 || raw === "disconnected" || raw === false) {
                return this.$t("rns_filesync.peer_disconnected");
            }
            return raw != null ? String(raw) : this.$t("rns_filesync.peer_unknown");
        },
        openDirectoryBrowser() {
            if (this.status.running) {
                ToastUtils.warning(this.$t("rns_filesync.stop_before_change_folder"));
                return;
            }
            this.directoryBrowserOpen = true;
        },
        async useSharedFolder() {
            if (this.status.running) {
                ToastUtils.warning(this.$t("rns_filesync.stop_before_change_folder"));
                return;
            }
            const bridge = typeof window !== "undefined" ? window.MeshChatXAndroid : null;
            if (bridge && typeof bridge.hasAllFilesAccess === "function") {
                let hasAccess = false;
                try {
                    hasAccess = Boolean(bridge.hasAllFilesAccess());
                } catch (_err) {
                    hasAccess = false;
                }
                if (!hasAccess && typeof bridge.requestAllFilesAccess === "function") {
                    bridge.requestAllFilesAccess();
                    ToastUtils.info(this.$t("rns_filesync.shared_folder_permission_needed"));
                    return;
                }
            }
            this.busy = true;
            try {
                const response = await window.api.get("/api/v1/filesync/shared-directory-suggestion");
                const path = String(response?.data?.path || "").trim();
                if (!path) {
                    ToastUtils.error(this.$t("rns_filesync.error"));
                    return;
                }
                this.syncDirectory = path;
                ToastUtils.success(this.$t("rns_filesync.shared_folder_selected"));
            } catch (err) {
                ToastUtils.error(err?.message || this.$t("rns_filesync.error"));
            } finally {
                this.busy = false;
            }
        },
        onDirectorySelected(path) {
            const cleaned = String(path || "").trim();
            if (!cleaned) {
                return;
            }
            this.syncDirectory = cleaned;
            ToastUtils.success(this.$t("rns_filesync.folder_selected"));
        },
        async openSyncFolder() {
            const path = String(this.syncDirectory || "").trim();
            if (!path) {
                return;
            }
            const ok = await ElectronUtils.openDirectoryOrCopy(path, () =>
                ToastUtils.success(this.$t("rns_filesync.path_copied"))
            );
            if (!ok) {
                ToastUtils.info(path);
            }
        },
        async refreshAll() {
            await Promise.all([this.refreshStatus(), this.refreshPeers(), this.refreshAcl()]);
            await this.refreshFileManager();
        },
        async refreshFileManager() {
            const manager = this.$refs.fileManager;
            if (manager && typeof manager.refresh === "function") {
                await manager.refresh();
            }
        },
        async refreshStatus() {
            try {
                const response = await window.api.get("/api/v1/filesync/status");
                const status = response?.data || {};
                this.status = status;
                if (status.sync_directory) {
                    this.syncDirectory = status.sync_directory;
                }
                if (typeof status.announce_interval === "number") {
                    this.announceInterval = status.announce_interval;
                }
                if (typeof status.monitor === "boolean") {
                    this.monitor = status.monitor;
                }
            } catch (err) {
                ToastUtils.error(err?.message || this.$t("rns_filesync.error"));
            }
        },
        async refreshPeers() {
            try {
                const response = await window.api.get("/api/v1/filesync/peers");
                const data = response?.data || {};
                this.peers = Array.isArray(data.peers) ? data.peers : [];
            } catch (err) {
                ToastUtils.error(err?.message || this.$t("rns_filesync.error"));
            }
        },
        async refreshAcl() {
            try {
                const response = await window.api.get("/api/v1/filesync/acl");
                const data = response?.data || {};
                this.aclEnforce = Boolean(data.enforce);
                this.aclRules = data.rules || {};
            } catch (err) {
                ToastUtils.error(err?.message || this.$t("rns_filesync.error"));
            }
        },
        async startService() {
            this.busy = true;
            try {
                if (!this.status.running && this.syncDirectory) {
                    await window.api.patch("/api/v1/filesync/settings", {
                        sync_directory: this.syncDirectory,
                        monitor: this.monitor,
                        announce_interval: this.announceInterval,
                    });
                }
                await window.api.post("/api/v1/filesync/start", {
                    sync_directory: this.syncDirectory || undefined,
                    monitor: this.monitor,
                    announce_interval: this.announceInterval,
                });
                ToastUtils.success(this.$t("rns_filesync.started"));
                await this.refreshAll();
            } catch (err) {
                ToastUtils.error(err?.message || this.$t("rns_filesync.error"));
            } finally {
                this.busy = false;
            }
        },
        async stopService() {
            this.busy = true;
            try {
                await window.api.post("/api/v1/filesync/stop", {});
                ToastUtils.success(this.$t("rns_filesync.stopped"));
                await this.refreshAll();
            } catch (err) {
                ToastUtils.error(err?.message || this.$t("rns_filesync.error"));
            } finally {
                this.busy = false;
            }
        },
        async announceNow() {
            this.busy = true;
            try {
                await window.api.post("/api/v1/filesync/announce", {});
                ToastUtils.success(this.$t("rns_filesync.announced"));
            } catch (err) {
                ToastUtils.error(err?.message || this.$t("rns_filesync.error"));
            } finally {
                this.busy = false;
            }
        },
        async connectPeer() {
            this.busy = true;
            try {
                await window.api.post("/api/v1/filesync/connect", {
                    identity_hash: this.connectHash,
                });
                ToastUtils.success(this.$t("rns_filesync.connected"));
                this.connectHash = "";
                await this.refreshPeers();
                await this.refreshStatus();
            } catch (err) {
                ToastUtils.error(err?.message || this.$t("rns_filesync.error"));
            } finally {
                this.busy = false;
            }
        },
        async disconnectPeer(peerId) {
            this.busy = true;
            try {
                await window.api.post("/api/v1/filesync/disconnect", {
                    peer_id: peerId,
                });
                ToastUtils.success(this.$t("rns_filesync.disconnected"));
                await this.refreshPeers();
                await this.refreshStatus();
            } catch (err) {
                ToastUtils.error(err?.message || this.$t("rns_filesync.error"));
            } finally {
                this.busy = false;
            }
        },
        async browsePeer() {
            this.busy = true;
            try {
                const response = await window.api.post("/api/v1/filesync/browse", {
                    peer_id: this.browsePeerId,
                });
                const data = response?.data || {};
                this.remoteFiles = Array.isArray(data.files) ? data.files : [];
                ToastUtils.success(this.$t("rns_filesync.browse_done"));
            } catch (err) {
                this.remoteFiles = [];
                ToastUtils.error(err?.message || this.$t("rns_filesync.error"));
            } finally {
                this.busy = false;
            }
        },
        async downloadFile(path) {
            this.busy = true;
            try {
                await window.api.post("/api/v1/filesync/download", {
                    peer_id: this.browsePeerId,
                    path,
                });
                ToastUtils.info(this.$t("rns_filesync.download_started"));
            } catch (err) {
                ToastUtils.error(err?.message || this.$t("rns_filesync.error"));
            } finally {
                this.busy = false;
            }
        },
        async grantAcl() {
            const perms = [];
            if (this.aclRead) perms.push("read");
            if (this.aclWrite) perms.push("write");
            if (this.aclDelete) perms.push("delete");
            this.busy = true;
            try {
                await window.api.post("/api/v1/filesync/acl", {
                    identity_hash: this.aclHash,
                    perms,
                    enforce: this.aclEnforce,
                });
                ToastUtils.success(this.$t("rns_filesync.acl_updated"));
                this.aclHash = "";
                await this.refreshAcl();
            } catch (err) {
                ToastUtils.error(err?.message || this.$t("rns_filesync.error"));
            } finally {
                this.busy = false;
            }
        },
        async saveEnforce() {
            this.busy = true;
            try {
                await window.api.post("/api/v1/filesync/acl", {
                    enforce: this.aclEnforce,
                });
                ToastUtils.success(this.$t("rns_filesync.acl_updated"));
                await this.refreshAcl();
            } catch (err) {
                ToastUtils.error(err?.message || this.$t("rns_filesync.error"));
            } finally {
                this.busy = false;
            }
        },
        async copyHash(hash) {
            try {
                await navigator.clipboard.writeText(hash);
                ToastUtils.success(this.$t("rns_filesync.copied"));
            } catch {
                ToastUtils.error(this.$t("rns_filesync.error"));
            }
        },
    },
};
</script>
