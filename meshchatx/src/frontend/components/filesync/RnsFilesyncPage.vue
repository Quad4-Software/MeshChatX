<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-slate-50 dark:bg-zinc-950">
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
                        class="border-b border-gray-200 dark:border-zinc-700 overflow-x-auto overscroll-x-contain -mx-4 px-4 sm:mx-0 sm:px-0"
                    >
                        <div class="flex w-max min-w-full sm:w-auto gap-1 sm:gap-2">
                            <button
                                v-for="tab in tabs"
                                :key="tab.id"
                                type="button"
                                :class="[
                                    activeTab === tab.id
                                        ? 'border-b-2 border-emerald-500 text-emerald-600 dark:text-emerald-400'
                                        : 'text-gray-600 dark:text-gray-400',
                                    'shrink-0 px-3 sm:px-4 py-2 text-sm font-semibold transition',
                                ]"
                                @click="activeTab = tab.id"
                            >
                                {{ $t(tab.labelKey) }}
                            </button>
                        </div>
                    </div>

                    <div v-if="activeTab === 'status'" class="space-y-4">
                        <div class="grid gap-3 sm:grid-cols-2">
                            <div>
                                <label class="glass-label">{{ $t("rns_filesync.sync_directory") }}</label>
                                <input
                                    v-model="syncDirectory"
                                    type="text"
                                    class="glass-input w-full font-mono text-sm"
                                    :disabled="status.running"
                                    :placeholder="$t('rns_filesync.sync_directory_placeholder')"
                                />
                            </div>
                            <div>
                                <label class="glass-label">{{ $t("rns_filesync.announce_interval") }}</label>
                                <input
                                    v-model.number="announceInterval"
                                    type="number"
                                    min="10"
                                    class="glass-input w-full"
                                />
                            </div>
                        </div>
                        <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                            <input v-model="monitor" type="checkbox" class="rounded" />
                            {{ $t("rns_filesync.monitor") }}
                        </label>
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
                        <div class="space-y-2 text-sm">
                            <div class="flex flex-wrap gap-x-4 gap-y-1">
                                <span>
                                    {{ $t("rns_filesync.running") }}:
                                    <strong>{{
                                        status.running ? $t("rns_filesync.yes") : $t("rns_filesync.no")
                                    }}</strong>
                                </span>
                                <span>
                                    {{ $t("rns_filesync.peers_count") }}:
                                    <strong>{{ status.peers || 0 }}</strong>
                                </span>
                                <span>
                                    {{ $t("rns_filesync.files_count") }}:
                                    <strong>{{ status.files || 0 }}</strong>
                                </span>
                            </div>
                            <div v-if="status.destination_hash" class="font-mono text-xs break-all">
                                <div class="font-semibold mb-1">{{ $t("rns_filesync.destination_hash") }}</div>
                                <button
                                    type="button"
                                    class="text-left hover:underline"
                                    @click="copyHash(status.destination_hash)"
                                >
                                    {{ status.destination_hash }}
                                </button>
                            </div>
                            <div v-if="lastProgress" class="text-xs text-gray-600 dark:text-gray-400">
                                {{ $t("rns_filesync.last_progress") }}: {{ lastProgress }}
                            </div>
                        </div>
                    </div>

                    <div v-else-if="activeTab === 'peers'" class="space-y-4">
                        <div class="flex flex-col sm:flex-row gap-2">
                            <input
                                v-model="connectHash"
                                type="text"
                                class="glass-input flex-1 font-mono text-sm"
                                :placeholder="$t('rns_filesync.peer_hash_placeholder')"
                            />
                            <button
                                type="button"
                                class="primary-chip px-4 py-2 text-sm"
                                :disabled="busy || !status.running"
                                @click="connectPeer"
                            >
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
                        <div v-if="peers.length === 0" class="text-sm text-gray-500 dark:text-gray-400">
                            {{ $t("rns_filesync.no_peers") }}
                        </div>
                        <ul v-else class="space-y-2">
                            <li
                                v-for="peer in peers"
                                :key="peer.peer_id"
                                class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-lg border border-gray-200 dark:border-zinc-700"
                            >
                                <div class="min-w-0 font-mono text-xs break-all">
                                    <div>{{ peer.peer_id }}</div>
                                    <div class="text-gray-500 dark:text-gray-400">
                                        {{ peer.destination_hash }} · {{ peer.status }}
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
                        <button
                            type="button"
                            class="secondary-chip px-3 py-1.5 text-sm"
                            :disabled="busy"
                            @click="refreshFiles"
                        >
                            {{ $t("rns_filesync.refresh") }}
                        </button>
                        <div v-if="files.length === 0" class="text-sm text-gray-500 dark:text-gray-400">
                            {{ $t("rns_filesync.no_files") }}
                        </div>
                        <ul v-else class="space-y-2">
                            <li
                                v-for="file in files"
                                :key="file.path"
                                class="p-3 rounded-lg border border-gray-200 dark:border-zinc-700 font-mono text-xs"
                            >
                                <div class="break-all">{{ file.path }}</div>
                                <div class="text-gray-500 dark:text-gray-400 mt-1">
                                    {{ file.size }} B · {{ file.hash }}
                                </div>
                            </li>
                        </ul>
                    </div>

                    <div v-else-if="activeTab === 'browse'" class="space-y-4">
                        <div class="flex flex-col sm:flex-row gap-2">
                            <select v-model="browsePeerId" class="glass-input flex-1 font-mono text-sm">
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
                                {{ $t("rns_filesync.browse") }}
                            </button>
                        </div>
                        <div v-if="remoteFiles.length === 0" class="text-sm text-gray-500 dark:text-gray-400">
                            {{ $t("rns_filesync.no_remote_files") }}
                        </div>
                        <ul v-else class="space-y-2">
                            <li
                                v-for="file in remoteFiles"
                                :key="file.path || file"
                                class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-lg border border-gray-200 dark:border-zinc-700"
                            >
                                <div class="min-w-0 font-mono text-xs break-all">
                                    {{ file.path || file }}
                                    <span v-if="file.size != null" class="text-gray-500"> · {{ file.size }} B</span>
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

                    <div v-else-if="activeTab === 'acl'" class="space-y-4">
                        <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                            <input v-model="aclEnforce" type="checkbox" class="rounded" @change="saveEnforce" />
                            {{ $t("rns_filesync.acl_enforce") }}
                        </label>
                        <div class="flex flex-col sm:flex-row gap-2">
                            <input
                                v-model="aclHash"
                                type="text"
                                class="glass-input flex-1 font-mono text-sm"
                                :placeholder="$t('rns_filesync.peer_hash_placeholder')"
                            />
                            <div class="flex items-center gap-3 text-sm">
                                <label class="flex items-center gap-1">
                                    <input v-model="aclRead" type="checkbox" />
                                    r
                                </label>
                                <label class="flex items-center gap-1">
                                    <input v-model="aclWrite" type="checkbox" />
                                    w
                                </label>
                                <label class="flex items-center gap-1">
                                    <input v-model="aclDelete" type="checkbox" />
                                    d
                                </label>
                            </div>
                            <button
                                type="button"
                                class="primary-chip px-4 py-2 text-sm"
                                :disabled="busy"
                                @click="grantAcl"
                            >
                                {{ $t("rns_filesync.acl_grant") }}
                            </button>
                        </div>
                        <pre class="p-3 rounded-lg bg-zinc-100 dark:bg-zinc-900 text-xs overflow-x-auto">{{
                            aclRulesText
                        }}</pre>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";
import ToolsPageHeader from "../tools/ToolsPageHeader.vue";
import { onWsEvent, offWsEvent } from "../../js/registries/wsEventRegistry.js";

export default {
    name: "RnsFilesyncPage",
    components: {
        MaterialDesignIcon,
        ToolsPageHeader,
    },
    data() {
        return {
            activeTab: "status",
            tabs: [
                { id: "status", labelKey: "rns_filesync.tab_status" },
                { id: "peers", labelKey: "rns_filesync.tab_peers" },
                { id: "files", labelKey: "rns_filesync.tab_files" },
                { id: "browse", labelKey: "rns_filesync.tab_browse" },
                { id: "acl", labelKey: "rns_filesync.tab_acl" },
            ],
            busy: false,
            status: {
                running: false,
                peers: 0,
                files: 0,
                destination_hash: null,
                sync_directory: "",
            },
            syncDirectory: "",
            announceInterval: 300,
            monitor: true,
            connectHash: "",
            peers: [],
            files: [],
            browsePeerId: "",
            remoteFiles: [],
            aclEnforce: false,
            aclHash: "",
            aclRead: true,
            aclWrite: false,
            aclDelete: false,
            aclRules: {},
            lastProgress: "",
            wsHandlers: [],
        };
    },
    computed: {
        aclRulesText() {
            try {
                return JSON.stringify(this.aclRules || {}, null, 2);
            } catch {
                return "{}";
            }
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
                this.lastProgress = JSON.stringify(payload);
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
                await this.refreshFiles();
                ToastUtils.info(this.$t("rns_filesync.file_updated"));
            });
            bind("filesync.file.deleted", async () => {
                await this.refreshFiles();
                ToastUtils.info(this.$t("rns_filesync.file_deleted"));
            });
            bind("filesync.error", (payload) => {
                const detail = payload?.error || payload?.message || "";
                ToastUtils.error(`${this.$t("rns_filesync.error")}${detail ? ": " + detail : ""}`);
            });
        },
        async refreshAll() {
            await Promise.all([this.refreshStatus(), this.refreshPeers(), this.refreshFiles(), this.refreshAcl()]);
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
        async refreshFiles() {
            try {
                const response = await window.api.get("/api/v1/filesync/files");
                const data = response?.data || {};
                this.files = Array.isArray(data.files) ? data.files : [];
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
