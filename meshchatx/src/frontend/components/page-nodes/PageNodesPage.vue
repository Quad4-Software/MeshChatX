<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
        <ToolsPageHeader
            icon="server-network"
            :title="$t('tools.mesh_server.title')"
            :description="$t('tools.mesh_server.description')"
            accent="amber"
        >
            <template #actions>
                <button type="button" class="primary-chip px-4 py-2 text-sm shrink-0" @click="showCreateDialog = true">
                    <MaterialDesignIcon icon-name="plus" class="w-4 h-4" />
                    {{ $t("tools.mesh_server.create_node") }}
                </button>
            </template>
        </ToolsPageHeader>
        <div class="flex-1 overflow-y-auto overflow-x-hidden w-full px-3 sm:px-5 md:px-5 lg:px-8 py-3 sm:py-4 min-w-0">
            <div class="space-y-0 w-full max-w-6xl xl:max-w-7xl mx-auto min-w-0">
                <div
                    v-if="loading"
                    class="w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-8 sm:py-12 text-center"
                >
                    <div class="text-sem-fg-muted">{{ $t("tools.mesh_server.loading") }}</div>
                </div>

                <div
                    v-else-if="nodes.length === 0"
                    class="w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-8 sm:py-12 text-center"
                >
                    <MaterialDesignIcon icon-name="server-network" class="w-12 h-12 mx-auto mb-4 text-gray-400" />
                    <div class="text-gray-600 dark:text-gray-400 mb-2">{{ $t("tools.mesh_server.empty_title") }}</div>
                    <div class="text-sm text-gray-500 dark:text-gray-500">
                        {{ $t("tools.mesh_server.empty_description") }}
                    </div>
                </div>

                <div v-else class="w-full divide-y divide-gray-200/60 dark:divide-zinc-800/60">
                    <div
                        v-for="node in nodes"
                        :key="node.node_id"
                        class="py-3 sm:py-4 space-y-2 cursor-pointer hover:bg-black/5 dark:hover:bg-white/5 transition-colors rounded-lg -mx-3 sm:-mx-4 px-3 sm:px-4"
                        @click="selectNode(node)"
                    >
                        <div class="flex items-center justify-between gap-3">
                            <div class="flex items-center gap-3 min-w-0">
                                <div
                                    class="w-3 h-3 rounded-full shrink-0"
                                    :class="node.running ? 'bg-green-500' : 'bg-gray-400'"
                                ></div>
                                <div class="min-w-0">
                                    <div class="flex items-center gap-2">
                                        <div class="font-semibold text-sem-fg truncate">
                                            {{ node.name }}
                                        </div>
                                        <span
                                            v-if="!node.announce_enabled"
                                            class="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 shrink-0"
                                        >
                                            {{ $t("tools.mesh_server.announce_off_badge") }}
                                        </span>
                                    </div>
                                    <div
                                        v-if="node.destination_hash"
                                        class="text-xs font-mono text-sem-fg-muted truncate"
                                    >
                                        {{ node.destination_hash }}
                                    </div>
                                </div>
                            </div>
                            <div class="flex items-center gap-1.5 shrink-0 flex-wrap justify-end">
                                <span class="text-xs text-sem-fg-muted mr-1">
                                    {{
                                        $t("tools.mesh_server.stats_pages_files", {
                                            pages: node.pages.length,
                                            files: node.files.length,
                                        })
                                    }}
                                </span>
                                <button
                                    v-if="!node.running"
                                    class="primary-chip py-1! px-2.5! text-xs!"
                                    @click.stop="startNode(node.node_id)"
                                >
                                    {{ $t("tools.mesh_server.start") }}
                                </button>
                                <button
                                    v-else
                                    class="secondary-chip py-1! px-2.5! text-xs! text-red-500! hover:bg-red-50! dark:hover:bg-red-900/20!"
                                    @click.stop="stopNode(node.node_id)"
                                >
                                    {{ $t("tools.mesh_server.stop") }}
                                </button>
                                <button
                                    v-if="node.running"
                                    class="secondary-chip py-1! px-2.5! text-xs!"
                                    @click.stop="announceNode(node.node_id)"
                                >
                                    {{ $t("tools.mesh_server.announce") }}
                                </button>
                                <button
                                    v-if="node.running && node.destination_hash"
                                    class="secondary-chip py-1! px-2.5! text-xs!"
                                    @click.stop="viewNode(node)"
                                >
                                    <MaterialDesignIcon icon-name="eye" class="w-3.5 h-3.5" />
                                    {{ $t("tools.mesh_server.view") }}
                                </button>
                                <button
                                    class="secondary-chip py-1! px-2.5! text-xs! text-red-500! hover:bg-red-50! dark:hover:bg-red-900/20!"
                                    @click.stop="deleteNode(node.node_id)"
                                >
                                    <MaterialDesignIcon icon-name="delete" class="w-3.5 h-3.5" />
                                </button>
                            </div>
                        </div>

                        <div
                            v-if="node.stats || node.running"
                            class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-sem-fg-muted pl-6"
                        >
                            <span v-if="node.running">
                                {{
                                    $t("tools.mesh_server.uptime", {
                                        time: formatMeshUptime(node.uptime_seconds),
                                    })
                                }}
                            </span>
                            <span>
                                {{
                                    $t("tools.mesh_server.connections", {
                                        count: node.unique_connections ?? 0,
                                    })
                                }}
                            </span>
                            <span v-if="node.stats">
                                {{
                                    $t("tools.mesh_server.pages_served", {
                                        count: node.stats.pages_served,
                                    })
                                }}
                            </span>
                            <span v-if="node.stats">
                                {{
                                    $t("tools.mesh_server.files_served", {
                                        count: node.stats.files_served,
                                    })
                                }}
                            </span>
                            <span v-if="node.stats">
                                {{
                                    $t("tools.mesh_server.links", {
                                        count: node.stats.links_established,
                                    })
                                }}
                            </span>
                            <span>{{ formatLastAnnounced(node.last_announced_at) }}</span>
                        </div>
                    </div>
                </div>

                <!-- Selected Node Detail -->
                <div
                    v-if="selectedNode"
                    class="w-full py-4 sm:py-6 space-y-4 border-t border-gray-200/60 dark:border-zinc-800/60"
                >
                    <div class="flex items-center justify-between">
                        <div class="text-lg font-semibold text-sem-fg">
                            {{ selectedNode.name }}
                        </div>
                        <div class="flex items-center gap-2">
                            <button class="secondary-chip py-1! px-3! text-xs!" @click="showRenameDialog = true">
                                {{ $t("tools.mesh_server.rename") }}
                            </button>
                            <button class="secondary-chip py-1! px-3! text-xs!" @click="selectedNode = null">
                                <MaterialDesignIcon icon-name="close" class="w-3.5 h-3.5" />
                            </button>
                        </div>
                    </div>

                    <div
                        v-if="selectedNode.destination_hash"
                        class="p-3 rounded-lg bg-sem-surface-muted text-blue-700 dark:text-blue-300"
                    >
                        <div class="flex items-center justify-between mb-1">
                            <div class="text-xs font-bold uppercase tracking-wider">
                                {{ $t("tools.mesh_server.destination_hash") }}
                            </div>
                            <button
                                v-if="selectedNode.running"
                                class="primary-chip py-0.5! px-2! text-xs!"
                                @click="viewNode(selectedNode)"
                            >
                                <MaterialDesignIcon icon-name="eye" class="w-3 h-3" />
                                {{ $t("tools.mesh_server.view_in_browser") }}
                            </button>
                        </div>
                        <div class="font-mono text-sm select-all">{{ selectedNode.destination_hash }}</div>
                    </div>

                    <!-- Announce settings -->
                    <div class="p-3 rounded-lg bg-slate-50 dark:bg-zinc-800/50 border border-sem-border space-y-3">
                        <div class="text-xs font-bold uppercase tracking-wider text-sem-fg-muted">
                            {{ $t("tools.mesh_server.announce_settings") }}
                        </div>
                        <div class="flex items-center justify-between gap-3">
                            <Toggle
                                id="mesh-server-executable-pages-enabled"
                                v-model="announceSettingsForm.executable_pages_enabled"
                                :label="$t('tools.mesh_server.executable_pages_enabled_label')"
                            />
                        </div>
                        <div class="text-xs text-sem-fg-muted">
                            {{ $t("tools.mesh_server.executable_pages_warning") }}
                        </div>
                        <div class="flex items-center justify-between gap-3">
                            <Toggle
                                id="mesh-server-announce-enabled"
                                v-model="announceSettingsForm.announce_enabled"
                                :label="$t('tools.mesh_server.announce_enabled_label')"
                            />
                        </div>
                        <div v-if="announceSettingsForm.announce_enabled" class="space-y-1">
                            <div class="flex items-center gap-3">
                                <label for="mesh-server-announce-interval" class="glass-label mb-0 shrink-0">
                                    {{ $t("tools.mesh_server.announce_interval_label") }}
                                </label>
                                <input
                                    id="mesh-server-announce-interval"
                                    v-model.number="announceIntervalMinutes"
                                    type="number"
                                    min="0"
                                    max="1440"
                                    class="input-field w-24"
                                />
                            </div>
                            <div class="text-xs text-sem-fg-muted">
                                {{ $t("tools.mesh_server.announce_interval_manual_hint") }}
                            </div>
                        </div>
                        <div class="flex items-center justify-between gap-3">
                            <span class="text-xs text-sem-fg-muted">
                                {{ formatLastAnnounced(selectedNode.last_announced_at) }}
                            </span>
                            <button class="primary-chip py-1! px-3! text-xs!" @click="saveAnnounceSettings">
                                {{ $t("common.save") }}
                            </button>
                        </div>
                    </div>

                    <!-- Tabs: Pages / Files -->
                    <div class="flex gap-2 border-b border-gray-200/60 dark:border-zinc-800/60">
                        <button
                            :class="[
                                detailTab === 'pages'
                                    ? 'border-b-2 border-blue-500 text-sem-accent'
                                    : 'text-gray-600 dark:text-gray-400',
                                'px-4 py-2 font-semibold transition text-sm -mb-px',
                            ]"
                            @click="detailTab = 'pages'"
                        >
                            {{
                                $t("tools.mesh_server.tabs_pages", {
                                    count: selectedNode.pages.length,
                                })
                            }}
                        </button>
                        <button
                            :class="[
                                detailTab === 'files'
                                    ? 'border-b-2 border-blue-500 text-sem-accent'
                                    : 'text-gray-600 dark:text-gray-400',
                                'px-4 py-2 font-semibold transition text-sm -mb-px',
                            ]"
                            @click="detailTab = 'files'"
                        >
                            {{
                                $t("tools.mesh_server.tabs_files", {
                                    count: selectedNode.files.length,
                                })
                            }}
                        </button>
                    </div>

                    <!-- Pages Tab -->
                    <div v-if="detailTab === 'pages'" class="space-y-3">
                        <div class="flex gap-2">
                            <input
                                v-model="newPageName"
                                type="text"
                                :placeholder="$t('tools.mesh_server.page_name_placeholder')"
                                class="input-field flex-1"
                                @keyup.enter="addPage"
                            />
                            <button class="primary-chip py-1! px-3! text-xs!" @click="addPage">
                                <MaterialDesignIcon icon-name="plus" class="w-3.5 h-3.5" />
                                {{ $t("tools.mesh_server.add_page") }}
                            </button>
                        </div>

                        <div v-if="selectedNode.pages.length === 0" class="text-sm text-sem-fg-muted py-4 text-center">
                            {{ $t("tools.mesh_server.no_pages") }}
                        </div>

                        <div
                            v-for="page in selectedNode.pages"
                            :key="page.name"
                            class="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-zinc-800/50 border border-sem-border"
                        >
                            <div class="flex items-center gap-2">
                                <MaterialDesignIcon icon-name="file-document-outline" class="w-4 h-4 text-teal-500" />
                                <span class="text-sm font-mono text-sem-fg">{{ page.name }}</span>
                                <span
                                    v-if="page.executable"
                                    class="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-300"
                                >
                                    {{ $t("tools.mesh_server.executable_badge") }}
                                </span>
                            </div>
                            <div class="flex items-center gap-2">
                                <button class="secondary-chip py-0.5! px-2! text-xs!" @click="editPage(page.name)">
                                    {{ $t("common.edit") }}
                                </button>
                                <button
                                    class="secondary-chip py-0.5! px-2! text-xs! text-red-500!"
                                    @click="deletePage(page.name)"
                                >
                                    <MaterialDesignIcon icon-name="delete" class="w-3 h-3" />
                                </button>
                            </div>
                        </div>

                        <!-- Page editor -->
                        <div v-if="editingPage" class="space-y-2">
                            <div class="flex items-center justify-between">
                                <div class="text-sm font-semibold text-sem-fg">
                                    {{
                                        $t("tools.mesh_server.editing_page", {
                                            name: editingPage,
                                        })
                                    }}
                                </div>
                                <div class="flex gap-2">
                                    <button class="primary-chip py-1! px-3! text-xs!" @click="savePage">
                                        {{ $t("common.save") }}
                                    </button>
                                    <button class="secondary-chip py-1! px-3! text-xs!" @click="editingPage = null">
                                        {{ $t("common.cancel") }}
                                    </button>
                                </div>
                            </div>
                            <div class="flex items-center gap-2">
                                <Toggle
                                    id="mesh-server-page-executable"
                                    v-model="editingPageExecutable"
                                    :label="$t('tools.mesh_server.page_executable_label')"
                                />
                            </div>
                            <textarea
                                v-model="editingPageContent"
                                class="w-full h-64 bg-sem-surface text-sem-fg p-3 font-mono text-sm rounded-lg border border-sem-border resize-y focus:outline-hidden focus:ring-2 focus:ring-blue-500/50"
                            ></textarea>
                        </div>
                    </div>

                    <!-- Files Tab -->
                    <div v-if="detailTab === 'files'" class="space-y-3">
                        <div class="flex gap-2">
                            <input ref="fileInput" type="file" class="hidden" @change="uploadFile" />
                            <button class="primary-chip py-1! px-3! text-xs!" @click="$refs.fileInput.click()">
                                <MaterialDesignIcon icon-name="upload" class="w-3.5 h-3.5" />
                                {{ $t("tools.mesh_server.upload_file") }}
                            </button>
                        </div>

                        <div v-if="selectedNode.files.length === 0" class="text-sm text-sem-fg-muted py-4 text-center">
                            {{ $t("tools.mesh_server.no_files") }}
                        </div>

                        <div
                            v-for="file in selectedNode.files"
                            :key="file.name"
                            class="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-zinc-800/50 border border-sem-border"
                        >
                            <div class="flex items-center gap-2">
                                <MaterialDesignIcon icon-name="file-outline" class="w-4 h-4 text-blue-500" />
                                <span class="text-sm font-mono text-sem-fg">{{ file.name }}</span>
                                <span class="text-xs text-sem-fg-muted">{{ formatFileSize(file.size) }}</span>
                            </div>
                            <button
                                class="secondary-chip py-0.5! px-2! text-xs! text-red-500!"
                                @click="deleteFile(file.name)"
                            >
                                <MaterialDesignIcon icon-name="delete" class="w-3 h-3" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Create Node Dialog -->
        <div
            v-if="showCreateDialog"
            class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            @click.self="showCreateDialog = false"
        >
            <div class="bg-sem-surface rounded-2xl p-6 w-full max-w-md mx-4 shadow-xl space-y-4">
                <div class="text-lg font-semibold text-sem-fg">
                    {{ $t("tools.mesh_server.create_dialog_title") }}
                </div>
                <div>
                    <label class="glass-label">{{ $t("tools.mesh_server.server_name_label") }}</label>
                    <input
                        v-model="createNodeName"
                        type="text"
                        :placeholder="$t('tools.mesh_server.server_name_placeholder')"
                        class="input-field"
                        @keyup.enter="createNode"
                    />
                </div>
                <div class="flex justify-end gap-2">
                    <button class="secondary-chip py-1.5! px-4! text-sm!" @click="showCreateDialog = false">
                        {{ $t("common.cancel") }}
                    </button>
                    <button class="primary-chip py-1.5! px-4! text-sm!" @click="createNode">
                        {{ $t("tools.mesh_server.create") }}
                    </button>
                </div>
            </div>
        </div>

        <!-- Rename Dialog -->
        <div
            v-if="showRenameDialog"
            class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            @click.self="showRenameDialog = false"
        >
            <div class="bg-sem-surface rounded-2xl p-6 w-full max-w-md mx-4 shadow-xl space-y-4">
                <div class="text-lg font-semibold text-sem-fg">
                    {{ $t("tools.mesh_server.rename_dialog_title") }}
                </div>
                <div>
                    <label class="glass-label">{{ $t("tools.mesh_server.new_name_label") }}</label>
                    <input
                        v-model="renameNodeName"
                        type="text"
                        :placeholder="selectedNode ? selectedNode.name : ''"
                        class="input-field"
                        @keyup.enter="renameNode"
                    />
                </div>
                <div class="flex justify-end gap-2">
                    <button class="secondary-chip py-1.5! px-4! text-sm!" @click="showRenameDialog = false">
                        {{ $t("common.cancel") }}
                    </button>
                    <button class="primary-chip py-1.5! px-4! text-sm!" @click="renameNode">
                        {{ $t("tools.mesh_server.rename") }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import DialogUtils from "../../js/DialogUtils";
import ToolsPageHeader from "../tools/ToolsPageHeader.vue";
import Toggle from "../forms/Toggle.vue";
import ToastUtils from "../../js/ToastUtils";
import Utils from "../../js/Utils";
import GlobalEmitter from "../../js/GlobalEmitter";

const DEFAULT_ANNOUNCE_INTERVAL_SECONDS = 900;
const ANNOUNCE_INTERVAL_MIN_MINUTES = 1;
const ANNOUNCE_INTERVAL_MAX_MINUTES = 1440;

function resolveAnnounceIntervalSeconds(seconds, defaultSeconds = DEFAULT_ANNOUNCE_INTERVAL_SECONDS) {
    if (seconds == null) {
        return defaultSeconds;
    }
    const n = Number(seconds);
    if (!Number.isFinite(n)) {
        return defaultSeconds;
    }
    return n;
}

export default {
    name: "PageNodesPage",
    components: {
        MaterialDesignIcon,
        ToolsPageHeader,
        Toggle,
    },
    data() {
        return {
            nodes: [],
            loading: true,
            selectedNode: null,
            detailTab: "pages",
            showCreateDialog: false,
            showRenameDialog: false,
            createNodeName: "",
            renameNodeName: "",
            newPageName: "",
            editingPage: null,
            editingPageContent: "",
            editingPageExecutable: false,
            announceSettingsForm: {
                announce_enabled: true,
                announce_interval_seconds: DEFAULT_ANNOUNCE_INTERVAL_SECONDS,
                executable_pages_enabled: false,
            },
        };
    },
    computed: {
        announceIntervalMinutes: {
            get() {
                const seconds = resolveAnnounceIntervalSeconds(
                    this.announceSettingsForm.announce_interval_seconds,
                    DEFAULT_ANNOUNCE_INTERVAL_SECONDS
                );
                if (seconds === 0) {
                    return 0;
                }
                return Math.round(seconds / 60);
            },
            set(minutes) {
                const n = Number(minutes);
                if (Number.isFinite(n) && n === 0) {
                    this.announceSettingsForm.announce_interval_seconds = 0;
                    return;
                }
                const clamped = Math.max(
                    ANNOUNCE_INTERVAL_MIN_MINUTES,
                    Math.min(ANNOUNCE_INTERVAL_MAX_MINUTES, Number.isFinite(n) ? n : ANNOUNCE_INTERVAL_MIN_MINUTES)
                );
                this.announceSettingsForm.announce_interval_seconds = clamped * 60;
            },
        },
    },
    async mounted() {
        GlobalEmitter.on("websocket-reconnected", this.onWebsocketReconnected);
        await this.loadNodes();
    },
    beforeUnmount() {
        GlobalEmitter.off("websocket-reconnected", this.onWebsocketReconnected);
    },
    methods: {
        onWebsocketReconnected() {
            void this.loadNodes();
        },
        async loadNodes() {
            this.loading = true;
            try {
                const response = await window.api.get("/api/v1/page-nodes");
                this.nodes = response.data;
                if (this.selectedNode) {
                    const updated = this.nodes.find((n) => n.node_id === this.selectedNode.node_id);
                    if (updated) {
                        this.selectedNode = updated;
                    } else {
                        this.selectedNode = null;
                    }
                }
            } catch {
                ToastUtils.error(this.$t("tools.mesh_server.failed_load"));
            } finally {
                this.loading = false;
            }
        },
        selectNode(node) {
            this.selectedNode = node;
            this.detailTab = "pages";
            this.editingPage = null;
            this.announceSettingsForm = {
                announce_enabled: node.announce_enabled !== false,
                announce_interval_seconds: resolveAnnounceIntervalSeconds(node.announce_interval_seconds),
                executable_pages_enabled: node.executable_pages_enabled === true,
            };
        },
        async createNode() {
            if (!this.createNodeName.trim()) return;
            try {
                await window.api.post("/api/v1/page-nodes", { name: this.createNodeName.trim() });
                this.createNodeName = "";
                this.showCreateDialog = false;
                ToastUtils.success(this.$t("tools.mesh_server.created"));
                await this.loadNodes();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("tools.mesh_server.failed_create"));
            }
        },
        async deleteNode(nodeId) {
            if (!(await DialogUtils.confirm(this.$t("tools.mesh_server.delete_confirm")))) return;
            try {
                await window.api.delete(`/api/v1/page-nodes/${nodeId}`);
                if (this.selectedNode && this.selectedNode.node_id === nodeId) {
                    this.selectedNode = null;
                }
                ToastUtils.success(this.$t("tools.mesh_server.deleted"));
                await this.loadNodes();
            } catch {
                ToastUtils.error(this.$t("tools.mesh_server.failed_delete"));
            }
        },
        async startNode(nodeId) {
            try {
                const response = await window.api.post(`/api/v1/page-nodes/${nodeId}/start`);
                ToastUtils.success(
                    this.$t("tools.mesh_server.started", {
                        hash: response.data.destination_hash,
                    })
                );
                await this.loadNodes();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("tools.mesh_server.failed_start"));
            }
        },
        async stopNode(nodeId) {
            try {
                await window.api.post(`/api/v1/page-nodes/${nodeId}/stop`);
                ToastUtils.success(this.$t("tools.mesh_server.stopped"));
                await this.loadNodes();
            } catch {
                ToastUtils.error(this.$t("tools.mesh_server.failed_stop"));
            }
        },
        async announceNode(nodeId) {
            try {
                await window.api.post(`/api/v1/page-nodes/${nodeId}/announce`);
                ToastUtils.success(this.$t("tools.mesh_server.announced"));
                await this.loadNodes();
            } catch {
                ToastUtils.error(this.$t("tools.mesh_server.failed_announce"));
            }
        },
        async saveAnnounceSettings() {
            if (!this.selectedNode) return;
            try {
                const response = await window.api.patch(
                    `/api/v1/page-nodes/${this.selectedNode.node_id}/announce-settings`,
                    {
                        announce_enabled: this.announceSettingsForm.announce_enabled,
                        announce_interval_seconds: this.announceSettingsForm.announce_interval_seconds,
                        executable_pages_enabled: this.announceSettingsForm.executable_pages_enabled,
                    }
                );
                this.selectedNode = response.data;
                ToastUtils.success(this.$t("tools.mesh_server.announce_settings_saved"));
                await this.loadNodes();
            } catch {
                ToastUtils.error(this.$t("tools.mesh_server.announce_settings_failed"));
            }
        },
        formatLastAnnounced(lastAnnouncedAt) {
            if (!lastAnnouncedAt) {
                return this.$t("tools.mesh_server.never_announced");
            }
            return this.$t("tools.mesh_server.last_announced_ago", {
                time: Utils.formatSecondsAgoForI18n(lastAnnouncedAt),
            });
        },
        async renameNode() {
            if (!this.renameNodeName.trim() || !this.selectedNode) return;
            try {
                await window.api.put(`/api/v1/page-nodes/${this.selectedNode.node_id}/rename`, {
                    name: this.renameNodeName.trim(),
                });
                this.renameNodeName = "";
                this.showRenameDialog = false;
                ToastUtils.success(this.$t("tools.mesh_server.renamed"));
                await this.loadNodes();
            } catch {
                ToastUtils.error(this.$t("tools.mesh_server.failed_rename"));
            }
        },
        async addPage() {
            if (!this.newPageName.trim() || !this.selectedNode) return;
            try {
                await window.api.post(`/api/v1/page-nodes/${this.selectedNode.node_id}/pages`, {
                    name: this.newPageName.trim(),
                    content: "",
                });
                this.newPageName = "";
                ToastUtils.success(this.$t("tools.mesh_server.page_created"));
                await this.loadNodes();
            } catch {
                ToastUtils.error(this.$t("tools.mesh_server.failed_page_create"));
            }
        },
        async editPage(pageName) {
            try {
                const response = await window.api.get(
                    `/api/v1/page-nodes/${this.selectedNode.node_id}/pages/${encodeURIComponent(pageName)}`
                );
                let body = response.data;
                if (typeof body === "string") {
                    try {
                        body = JSON.parse(body);
                    } catch {
                        body = {};
                    }
                }
                this.editingPage = pageName;
                this.editingPageContent = body?.content ?? "";
                this.editingPageExecutable = body?.executable === true;
            } catch {
                ToastUtils.error(this.$t("tools.mesh_server.failed_page_load"));
            }
        },
        async savePage() {
            if (!this.editingPage || !this.selectedNode) return;
            try {
                await window.api.post(`/api/v1/page-nodes/${this.selectedNode.node_id}/pages`, {
                    name: this.editingPage,
                    content: this.editingPageContent,
                    executable: this.editingPageExecutable,
                });
                this.editingPage = null;
                this.editingPageContent = "";
                this.editingPageExecutable = false;
                ToastUtils.success(this.$t("tools.mesh_server.page_saved"));
                await this.loadNodes();
            } catch {
                ToastUtils.error(this.$t("tools.mesh_server.failed_page_save"));
            }
        },
        async deletePage(pageName) {
            if (
                !(await DialogUtils.confirm(
                    this.$t("tools.mesh_server.delete_page_confirm", {
                        name: pageName,
                    })
                ))
            ) {
                return;
            }
            try {
                await window.api.delete(
                    `/api/v1/page-nodes/${this.selectedNode.node_id}/pages/${encodeURIComponent(pageName)}`
                );
                if (this.editingPage === pageName) {
                    this.editingPage = null;
                }
                ToastUtils.success(this.$t("tools.mesh_server.page_deleted"));
                await this.loadNodes();
            } catch {
                ToastUtils.error(this.$t("tools.mesh_server.failed_page_delete"));
            }
        },
        async uploadFile(event) {
            const file = event.target.files[0];
            if (!file || !this.selectedNode) return;
            const formData = new FormData();
            formData.append("file", file);
            try {
                await window.api.post(`/api/v1/page-nodes/${this.selectedNode.node_id}/files`, formData, {
                    headers: { "Content-Type": "multipart/form-data" },
                });
                ToastUtils.success(this.$t("tools.mesh_server.file_uploaded"));
                await this.loadNodes();
            } catch {
                ToastUtils.error(this.$t("tools.mesh_server.failed_file_upload"));
            }
            event.target.value = "";
        },
        async deleteFile(fileName) {
            if (
                !(await DialogUtils.confirm(
                    this.$t("tools.mesh_server.delete_file_confirm", {
                        name: fileName,
                    })
                ))
            ) {
                return;
            }
            try {
                await window.api.delete(
                    `/api/v1/page-nodes/${this.selectedNode.node_id}/files/${encodeURIComponent(fileName)}`
                );
                ToastUtils.success(this.$t("tools.mesh_server.file_deleted"));
                await this.loadNodes();
            } catch {
                ToastUtils.error(this.$t("tools.mesh_server.failed_file_delete"));
            }
        },
        viewNode(node) {
            if (node.destination_hash) {
                this.$router.push({
                    name: "nomadnetwork",
                    params: { destinationHash: node.destination_hash },
                });
            }
        },
        formatFileSize(bytes) {
            if (bytes < 1024) return bytes + " B";
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
            return (bytes / (1024 * 1024)).toFixed(1) + " MB";
        },
        formatMeshUptime(seconds) {
            if (seconds == null || seconds < 0) return "-";
            let s = Math.floor(seconds);
            if (s < 60) return `${s}s`;
            if (s < 3600) return `${Math.floor(s / 60)}m`;
            if (s < 86400) return `${Math.floor(s / 3600)}h`;
            if (s < 30 * 86400) return `${Math.floor(s / 86400)}d`;
            const yearSec = 365 * 86400;
            const monthSec = 30 * 86400;
            const years = Math.floor(s / yearSec);
            s -= years * yearSec;
            const months = Math.floor(s / monthSec);
            s -= months * monthSec;
            const days = Math.floor(s / 86400);
            const parts = [];
            if (years) parts.push(`${years} year${years === 1 ? "" : "s"}`);
            if (months) parts.push(`${months} month${months === 1 ? "" : "s"}`);
            if (days) parts.push(`${days} day${days === 1 ? "" : "s"}`);
            return parts.length ? parts.join(" ") : "0d";
        },
    },
};
</script>
