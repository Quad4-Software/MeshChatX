<template>
    <div
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-gradient-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div class="flex-1 overflow-y-auto w-full px-4 md:px-8 py-6">
            <div class="space-y-4 w-full max-w-6xl mx-auto">
                <div v-if="appInfo" class="glass-card">
                    <div class="flex flex-col gap-4 md:flex-row md:items-center">
                        <div class="flex-1 space-y-2">
                            <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                                {{ $t("about.title") }}
                            </div>
                            <div class="text-3xl font-semibold text-gray-900 dark:text-white">Reticulum MeshChatX</div>
                            <div class="text-sm text-gray-600 dark:text-gray-300">
                                {{ $t("about.version", { version: appInfo.version }) }} •
                                {{ $t("about.rns_version", { version: appInfo.rns_version }) }} •
                                {{ $t("about.lxmf_version", { version: appInfo.lxmf_version }) }} •
                                {{ $t("about.python_version", { version: appInfo.python_version }) }}
                            </div>
                        </div>
                        <div v-if="isElectron" class="flex flex-col sm:flex-row gap-2">
                            <button
                                type="button"
                                class="primary-chip px-4 py-2 text-sm justify-center"
                                @click="relaunch"
                            >
                                <MaterialDesignIcon icon-name="restart" class="w-4 h-4" />
                                {{ $t("common.restart_app") }}
                            </button>
                        </div>
                    </div>
                    <div class="grid gap-3 sm:grid-cols-3 mt-4 text-sm text-gray-700 dark:text-gray-300">
                        <div>
                            <div class="glass-label">{{ $t("about.config_path") }}</div>
                            <div class="monospace-field break-all">{{ appInfo.reticulum_config_path }}</div>
                            <button
                                v-if="isElectron"
                                type="button"
                                class="secondary-chip mt-2 text-xs"
                                @click="showReticulumConfigFile"
                            >
                                <MaterialDesignIcon icon-name="folder" class="w-4 h-4" />
                                {{ $t("common.reveal") }}
                            </button>
                        </div>
                        <div>
                            <div class="glass-label">{{ $t("about.database_path") }}</div>
                            <div class="monospace-field break-all">{{ appInfo.database_path }}</div>
                            <button
                                v-if="isElectron"
                                type="button"
                                class="secondary-chip mt-2 text-xs"
                                @click="showDatabaseFile"
                            >
                                <MaterialDesignIcon icon-name="database" class="w-4 h-4" />
                                {{ $t("common.reveal") }}
                            </button>
                        </div>
                        <div>
                            <div class="glass-label">{{ $t("about.database_size") }}</div>
                            <div class="text-lg font-semibold text-gray-900 dark:text-white">
                                {{
                                    formatBytes(
                                        appInfo.database_files
                                            ? appInfo.database_files.total_bytes
                                            : appInfo.database_file_size
                                    )
                                }}
                            </div>
                            <div v-if="appInfo.database_files" class="text-xs text-gray-500 dark:text-gray-400">
                                Main {{ formatBytes(appInfo.database_files.main_bytes) }} • WAL
                                {{ formatBytes(appInfo.database_files.wal_bytes) }}
                            </div>
                        </div>
                    </div>
                </div>

                <div class="glass-card space-y-4">
                    <div class="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                        <div>
                            <div class="text-lg font-semibold text-gray-900 dark:text-white">
                                {{ $t("about.database_health") }}
                            </div>
                            <div class="text-xs text-gray-600 dark:text-gray-400">
                                {{ $t("about.database_health_description") }}
                            </div>
                        </div>
                        <div class="flex flex-wrap gap-2">
                            <button
                                type="button"
                                class="secondary-chip px-3 py-2 text-xs"
                                :disabled="databaseActionInProgress || healthLoading"
                                @click="getDatabaseHealth(true)"
                            >
                                <MaterialDesignIcon icon-name="refresh" class="w-4 h-4" />
                                {{ $t("common.refresh") }}
                            </button>
                            <button
                                type="button"
                                class="secondary-chip px-3 py-2 text-xs"
                                :disabled="databaseActionInProgress || healthLoading"
                                @click="vacuumDatabase"
                            >
                                <MaterialDesignIcon icon-name="broom" class="w-4 h-4" />
                                {{ $t("common.vacuum") }}
                            </button>
                            <button
                                type="button"
                                class="primary-chip px-3 py-2 text-xs"
                                :disabled="databaseActionInProgress || healthLoading"
                                @click="recoverDatabase"
                            >
                                <MaterialDesignIcon icon-name="shield-sync" class="w-4 h-4" />
                                {{ $t("common.auto_recover") }}
                            </button>
                        </div>
                    </div>
                    <div v-if="databaseActionMessage" class="text-xs text-emerald-600">{{ databaseActionMessage }}</div>
                    <div v-if="databaseActionError" class="text-xs text-red-600">{{ databaseActionError }}</div>
                    <div v-if="healthLoading" class="text-sm text-gray-500 dark:text-gray-400">
                        {{ $t("about.running_checks") }}
                    </div>
                    <div
                        v-if="databaseHealth"
                        class="grid gap-3 sm:grid-cols-3 text-sm text-gray-700 dark:text-gray-300"
                    >
                        <div>
                            <div class="glass-label">{{ $t("about.integrity") }}</div>
                            <div class="metric-value">{{ databaseHealth.quick_check }}</div>
                        </div>
                        <div>
                            <div class="glass-label">{{ $t("about.journal_mode") }}</div>
                            <div class="metric-value">{{ databaseHealth.journal_mode }}</div>
                        </div>
                        <div>
                            <div class="glass-label">{{ $t("about.wal_autocheckpoint") }}</div>
                            <div class="metric-value">
                                {{
                                    databaseHealth.wal_autocheckpoint !== null &&
                                    databaseHealth.wal_autocheckpoint !== undefined
                                        ? databaseHealth.wal_autocheckpoint
                                        : "—"
                                }}
                            </div>
                        </div>
                        <div>
                            <div class="glass-label">{{ $t("about.page_size") }}</div>
                            <div class="metric-value">{{ formatBytes(databaseHealth.page_size) }}</div>
                        </div>
                        <div>
                            <div class="glass-label">{{ $t("about.pages_free") }}</div>
                            <div class="metric-value">
                                {{ formatNumber(databaseHealth.page_count) }} /
                                {{ formatNumber(databaseHealth.freelist_pages) }}
                            </div>
                        </div>
                        <div>
                            <div class="glass-label">{{ $t("about.free_space_estimate") }}</div>
                            <div class="metric-value">{{ formatBytes(databaseHealth.estimated_free_bytes) }}</div>
                        </div>
                    </div>
                    <div v-else-if="!healthLoading" class="text-sm text-gray-500 dark:text-gray-400">
                        Health data will appear after the first refresh.
                    </div>
                    <div
                        v-if="databaseRecoveryActions.length"
                        class="text-xs text-gray-600 dark:text-gray-400 border-t border-gray-200 dark:border-gray-800 pt-3"
                    >
                        <div class="font-semibold text-gray-800 dark:text-gray-200 mb-1">Last recovery steps</div>
                        <ul class="list-disc list-inside space-y-1">
                            <li v-for="(action, index) in databaseRecoveryActions" :key="index">
                                <span class="font-medium text-gray-700 dark:text-gray-300">{{ action.step }}:</span>
                                <span class="ml-1">{{ formatRecoveryResult(action.result) }}</span>
                            </li>
                        </ul>
                    </div>
                    <div class="border-t border-gray-200 dark:border-gray-800 pt-3 space-y-3">
                        <div class="font-semibold text-gray-900 dark:text-white">Backups</div>
                        <button
                            type="button"
                            class="secondary-chip px-3 py-2 text-xs"
                            :disabled="backupInProgress"
                            @click="backupDatabase"
                        >
                            <MaterialDesignIcon icon-name="content-save" class="w-4 h-4" />
                            Download Backup
                        </button>
                        <div v-if="backupMessage" class="text-xs text-emerald-600">{{ backupMessage }}</div>
                        <div v-if="backupError" class="text-xs text-red-600">{{ backupError }}</div>
                        <div class="font-semibold text-gray-900 dark:text-white pt-2">Restore</div>
                        <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
                            <input type="file" accept=".zip,.db" class="file-input" @change="onRestoreFileChange" />
                            <button
                                type="button"
                                class="primary-chip px-3 py-2 text-xs"
                                :disabled="restoreInProgress"
                                @click="restoreDatabase"
                            >
                                <MaterialDesignIcon icon-name="database-sync" class="w-4 h-4" />
                                Restore
                            </button>
                        </div>
                        <div v-if="restoreFileName" class="text-xs text-gray-600 dark:text-gray-400">
                            Selected: {{ restoreFileName }}
                        </div>
                        <div v-if="restoreMessage" class="text-xs text-emerald-600">{{ restoreMessage }}</div>
                        <div v-if="restoreError" class="text-xs text-red-600">{{ restoreError }}</div>
                        <div class="border-t border-gray-200 dark:border-gray-800 pt-3 space-y-3">
                            <div class="font-semibold text-gray-900 dark:text-white">Identity Backup & Restore</div>
                            <div class="text-xs text-red-600">
                                Never share this identity. It grants full control. Clear your clipboard after copying.
                            </div>
                            <div class="flex flex-wrap gap-2">
                                <button
                                    type="button"
                                    class="secondary-chip px-3 py-2 text-xs"
                                    @click="downloadIdentityFile"
                                >
                                    <MaterialDesignIcon icon-name="content-save" class="w-4 h-4" />
                                    Download Identity File
                                </button>
                                <button
                                    type="button"
                                    class="secondary-chip px-3 py-2 text-xs"
                                    @click="copyIdentityBase32"
                                >
                                    <MaterialDesignIcon icon-name="content-copy" class="w-4 h-4" />
                                    Copy Base32 Identity
                                </button>
                            </div>
                            <div v-if="identityBackupMessage" class="text-xs text-emerald-600">
                                {{ identityBackupMessage }}
                            </div>
                            <div v-if="identityBackupError" class="text-xs text-red-600">{{ identityBackupError }}</div>
                            <div v-if="identityBase32Message" class="text-xs text-emerald-600">
                                {{ identityBase32Message }}
                            </div>
                            <div v-if="identityBase32Error" class="text-xs text-red-600">{{ identityBase32Error }}</div>
                            <div class="font-semibold text-gray-900 dark:text-white pt-2">Restore from file</div>
                            <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
                                <input
                                    type="file"
                                    accept=".identity,.bin,.key"
                                    class="file-input"
                                    @change="onIdentityRestoreFileChange"
                                />
                                <button
                                    type="button"
                                    class="primary-chip px-3 py-2 text-xs"
                                    :disabled="identityRestoreInProgress"
                                    @click="restoreIdentityFile"
                                >
                                    <MaterialDesignIcon icon-name="database-sync" class="w-4 h-4" />
                                    Restore Identity
                                </button>
                            </div>
                            <div v-if="identityRestoreFileName" class="text-xs text-gray-600 dark:text-gray-400">
                                Selected: {{ identityRestoreFileName }}
                            </div>
                            <div class="font-semibold text-gray-900 dark:text-white pt-2">Restore from base32</div>
                            <textarea v-model="identityRestoreBase32" rows="3" class="input-field"></textarea>
                            <button
                                type="button"
                                class="primary-chip px-3 py-2 text-xs"
                                :disabled="identityRestoreInProgress"
                                @click="restoreIdentityBase32"
                            >
                                <MaterialDesignIcon icon-name="database-sync" class="w-4 h-4" />
                                Restore Identity
                            </button>
                            <div v-if="identityRestoreMessage" class="text-xs text-emerald-600">
                                {{ identityRestoreMessage }}
                            </div>
                            <div v-if="identityRestoreError" class="text-xs text-red-600">
                                {{ identityRestoreError }}
                            </div>
                        </div>
                    </div>
                </div>

                <div class="grid gap-4 lg:grid-cols-2">
                    <div v-if="appInfo?.memory_usage" class="glass-card space-y-3">
                        <header class="flex items-center gap-2">
                            <MaterialDesignIcon icon-name="chip" class="w-5 h-5 text-blue-500" />
                            <div>
                                <div class="text-lg font-semibold text-gray-900 dark:text-white">
                                    {{ $t("about.system_resources") }}
                                </div>
                                <div class="text-xs text-emerald-500 flex items-center gap-1">
                                    <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                                    {{ $t("about.live") }}
                                </div>
                            </div>
                        </header>
                        <div class="metric-row">
                            <div>
                                <div class="glass-label">{{ $t("about.memory_rss") }}</div>
                                <div class="metric-value">{{ formatBytes(appInfo.memory_usage.rss) }}</div>
                            </div>
                            <div>
                                <div class="glass-label">{{ $t("about.virtual_memory") }}</div>
                                <div class="metric-value">{{ formatBytes(appInfo.memory_usage.vms) }}</div>
                            </div>
                        </div>
                    </div>

                    <div v-if="appInfo?.network_stats" class="glass-card space-y-3">
                        <header class="flex items-center gap-2">
                            <MaterialDesignIcon icon-name="access-point-network" class="w-5 h-5 text-purple-500" />
                            <div>
                                <div class="text-lg font-semibold text-gray-900 dark:text-white">
                                    {{ $t("about.network_stats") }}
                                </div>
                                <div class="text-xs text-emerald-500 flex items-center gap-1">
                                    <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                                    {{ $t("about.live") }}
                                </div>
                            </div>
                        </header>
                        <div class="metric-row">
                            <div>
                                <div class="glass-label">{{ $t("about.sent") }}</div>
                                <div class="metric-value">{{ formatBytes(appInfo.network_stats.bytes_sent) }}</div>
                            </div>
                            <div>
                                <div class="glass-label">{{ $t("about.received") }}</div>
                                <div class="metric-value">{{ formatBytes(appInfo.network_stats.bytes_recv) }}</div>
                            </div>
                        </div>
                        <div class="metric-row">
                            <div>
                                <div class="glass-label">{{ $t("about.packets_sent") }}</div>
                                <div class="metric-value">{{ formatNumber(appInfo.network_stats.packets_sent) }}</div>
                            </div>
                            <div>
                                <div class="glass-label">{{ $t("about.packets_received") }}</div>
                                <div class="metric-value">{{ formatNumber(appInfo.network_stats.packets_recv) }}</div>
                            </div>
                        </div>
                    </div>

                    <div v-if="appInfo?.reticulum_stats" class="glass-card space-y-3">
                        <header class="flex items-center gap-2">
                            <MaterialDesignIcon icon-name="diagram-projector" class="w-5 h-5 text-indigo-500" />
                            <div>
                                <div class="text-lg font-semibold text-gray-900 dark:text-white">
                                    {{ $t("about.reticulum_stats") }}
                                </div>
                                <div class="text-xs text-emerald-500 flex items-center gap-1">
                                    <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                                    {{ $t("about.live") }}
                                </div>
                            </div>
                        </header>
                        <div class="metric-grid">
                            <div>
                                <div class="glass-label">{{ $t("about.total_paths") }}</div>
                                <div class="metric-value">{{ formatNumber(appInfo.reticulum_stats.total_paths) }}</div>
                            </div>
                            <div>
                                <div class="glass-label">{{ $t("about.announces_per_second") }}</div>
                                <div class="metric-value">
                                    {{ formatNumber(appInfo.reticulum_stats.announces_per_second) }}
                                </div>
                            </div>
                            <div>
                                <div class="glass-label">{{ $t("about.announces_per_minute") }}</div>
                                <div class="metric-value">
                                    {{ formatNumber(appInfo.reticulum_stats.announces_per_minute) }}
                                </div>
                            </div>
                            <div>
                                <div class="glass-label">{{ $t("about.announces_per_hour") }}</div>
                                <div class="metric-value">
                                    {{ formatNumber(appInfo.reticulum_stats.announces_per_hour) }}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div v-if="appInfo?.download_stats" class="glass-card space-y-3">
                        <header class="flex items-center gap-2">
                            <MaterialDesignIcon icon-name="download" class="w-5 h-5 text-sky-500" />
                            <div>
                                <div class="text-lg font-semibold text-gray-900 dark:text-white">
                                    {{ $t("about.download_activity") }}
                                </div>
                                <div class="text-xs text-emerald-500 flex items-center gap-1">
                                    <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                                    {{ $t("about.live") }}
                                </div>
                            </div>
                        </header>
                        <div class="metric-value">
                            <span v-if="appInfo.download_stats.avg_download_speed_bps !== null">
                                {{ formatBytesPerSecond(appInfo.download_stats.avg_download_speed_bps) }}
                            </span>
                            <span v-else class="text-sm text-gray-500">{{ $t("about.no_downloads_yet") }}</span>
                        </div>
                    </div>
                </div>

                <div v-if="appInfo" class="glass-card space-y-3">
                    <div class="text-lg font-semibold text-gray-900 dark:text-white">
                        {{ $t("about.runtime_status") }}
                    </div>
                    <div class="flex flex-wrap gap-3">
                        <span :class="statusPillClass(!appInfo.is_connected_to_shared_instance)">
                            <MaterialDesignIcon icon-name="server" class="w-4 h-4" />
                            {{
                                appInfo.is_connected_to_shared_instance
                                    ? $t("about.shared_instance")
                                    : $t("about.standalone_instance")
                            }}
                        </span>
                        <span :class="statusPillClass(appInfo.is_transport_enabled)">
                            <MaterialDesignIcon icon-name="transit-connection" class="w-4 h-4" />
                            {{
                                appInfo.is_transport_enabled
                                    ? $t("about.transport_enabled")
                                    : $t("about.transport_disabled")
                            }}
                        </span>
                    </div>
                </div>

                <div v-if="config" class="glass-card space-y-4">
                    <div class="text-lg font-semibold text-gray-900 dark:text-white">
                        {{ $t("about.identity_addresses") }}
                    </div>
                    <div class="grid gap-3 md:grid-cols-2">
                        <div class="address-card">
                            <div class="glass-label">{{ $t("app.identity_hash") }}</div>
                            <div class="monospace-field break-all">{{ config.identity_hash }}</div>
                            <button
                                type="button"
                                class="secondary-chip mt-3 text-xs"
                                @click="copyValue(config.identity_hash, $t('app.identity_hash'))"
                            >
                                <MaterialDesignIcon icon-name="content-copy" class="w-4 h-4" />
                                {{ $t("app.copy") }}
                            </button>
                        </div>
                        <div class="address-card">
                            <div class="glass-label">{{ $t("app.lxmf_address") }}</div>
                            <div class="monospace-field break-all">{{ config.lxmf_address_hash }}</div>
                            <button
                                type="button"
                                class="secondary-chip mt-3 text-xs"
                                @click="copyValue(config.lxmf_address_hash, $t('app.lxmf_address'))"
                            >
                                <MaterialDesignIcon icon-name="account-network" class="w-4 h-4" />
                                {{ $t("app.copy") }}
                            </button>
                        </div>
                        <div class="address-card">
                            <div class="glass-label">{{ $t("app.propagation_node") }}</div>
                            <div class="monospace-field break-all">
                                {{ config.lxmf_local_propagation_node_address_hash || "—" }}
                            </div>
                        </div>
                        <div class="address-card">
                            <div class="glass-label">{{ $t("about.telephone_address") }}</div>
                            <div class="monospace-field break-all">{{ config.telephone_address_hash || "—" }}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import Utils from "../../js/Utils";
import ElectronUtils from "../../js/ElectronUtils";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";
export default {
    name: "AboutPage",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            appInfo: null,
            config: null,
            updateInterval: null,
            healthInterval: null,
            databaseHealth: null,
            databaseRecoveryActions: [],
            databaseActionMessage: "",
            databaseActionError: "",
            databaseActionInProgress: false,
            healthLoading: false,
            backupInProgress: false,
            backupMessage: "",
            backupError: "",
            restoreInProgress: false,
            restoreMessage: "",
            restoreError: "",
            restoreFileName: "",
            restoreFile: null,
            identityBackupMessage: "",
            identityBackupError: "",
            identityBase32: "",
            identityBase32Message: "",
            identityBase32Error: "",
            identityRestoreInProgress: false,
            identityRestoreMessage: "",
            identityRestoreError: "",
            identityRestoreFileName: "",
            identityRestoreFile: null,
            identityRestoreBase32: "",
        };
    },
    computed: {
        isElectron() {
            return ElectronUtils.isElectron();
        },
    },
    mounted() {
        this.getAppInfo();
        this.getConfig();
        this.getDatabaseHealth();
        // Update stats every 5 seconds
        this.updateInterval = setInterval(() => {
            this.getAppInfo();
        }, 5000);
        this.healthInterval = setInterval(() => {
            this.getDatabaseHealth();
        }, 30000);
    },
    beforeUnmount() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        if (this.healthInterval) {
            clearInterval(this.healthInterval);
        }
    },
    methods: {
        async getAppInfo() {
            try {
                const response = await window.axios.get("/api/v1/app/info");
                this.appInfo = response.data.app_info;
            } catch (e) {
                // do nothing if failed to load app info
                console.log(e);
            }
        },
        async getDatabaseHealth(showMessage = false) {
            this.healthLoading = true;
            try {
                const response = await window.axios.get("/api/v1/database/health");
                this.databaseHealth = response.data.database;
                if (showMessage) {
                    this.databaseActionMessage = "Database health refreshed";
                }
                this.databaseActionError = "";
            } catch {
                this.databaseActionError = "Failed to load database health";
            } finally {
                this.healthLoading = false;
            }
        },
        async vacuumDatabase() {
            if (this.databaseActionInProgress) {
                return;
            }
            this.databaseActionInProgress = true;
            this.databaseActionMessage = "";
            this.databaseActionError = "";
            this.databaseRecoveryActions = [];
            try {
                const response = await window.axios.post("/api/v1/database/vacuum");
                if (response.data.database?.health) {
                    this.databaseHealth = response.data.database.health;
                }
                this.databaseActionMessage = response.data.message || "Database vacuum completed";
            } catch (e) {
                this.databaseActionError = "Vacuum failed";
                console.log(e);
            } finally {
                this.databaseActionInProgress = false;
            }
        },
        async backupDatabase() {
            if (this.backupInProgress) {
                return;
            }
            this.backupInProgress = true;
            this.backupMessage = "";
            this.backupError = "";
            try {
                const response = await window.axios.get("/api/v1/database/backup/download", {
                    responseType: "blob",
                });
                const blob = new Blob([response.data], { type: "application/zip" });
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement("a");
                link.href = url;
                const filename =
                    response.headers["content-disposition"]?.split("filename=")?.[1]?.replace(/"/g, "") ||
                    "meshchatx-backup.zip";
                link.setAttribute("download", filename);
                document.body.appendChild(link);
                link.click();
                link.remove();
                window.URL.revokeObjectURL(url);
                this.backupMessage = "Backup downloaded";
                await this.getDatabaseHealth();
            } catch (e) {
                this.backupError = "Backup failed";
                console.log(e);
            } finally {
                this.backupInProgress = false;
            }
        },
        async restoreDatabase() {
            if (this.restoreInProgress) {
                return;
            }
            if (!this.restoreFile) {
                this.restoreError = "Select a backup file to restore.";
                return;
            }
            this.restoreInProgress = true;
            this.restoreMessage = "";
            this.restoreError = "";
            try {
                const formData = new FormData();
                formData.append("file", this.restoreFile);
                const response = await window.axios.post("/api/v1/database/restore", formData, {
                    headers: { "Content-Type": "multipart/form-data" },
                });
                this.restoreMessage = response.data.message || "Database restored";
                this.databaseHealth = response.data.database?.health || this.databaseHealth;
                this.databaseRecoveryActions = response.data.database?.actions || this.databaseRecoveryActions;
                await this.getDatabaseHealth();
            } catch (e) {
                this.restoreError = "Restore failed";
                console.log(e);
            } finally {
                this.restoreInProgress = false;
            }
        },
        async recoverDatabase() {
            if (this.databaseActionInProgress) {
                return;
            }
            this.databaseActionInProgress = true;
            this.databaseActionMessage = "";
            this.databaseActionError = "";
            try {
                const response = await window.axios.post("/api/v1/database/recover");
                if (response.data.database?.health) {
                    this.databaseHealth = response.data.database.health;
                }
                this.databaseRecoveryActions = response.data.database?.actions || [];
                this.databaseActionMessage = response.data.message || "Database recovery completed";
            } catch (e) {
                this.databaseActionError = "Recovery failed";
                console.log(e);
            } finally {
                this.databaseActionInProgress = false;
            }
        },
        async getConfig() {
            try {
                const response = await window.axios.get("/api/v1/config");
                this.config = response.data.config;
            } catch (e) {
                // do nothing if failed to load config
                console.log(e);
            }
        },
        async copyValue(value, label) {
            if (!value) {
                return;
            }
            try {
                await navigator.clipboard.writeText(value);
                ToastUtils.success(`${label} copied to clipboard`);
            } catch {
                ToastUtils.error(`Failed to copy ${label}`);
            }
        },
        relaunch() {
            ElectronUtils.relaunch();
        },
        showReticulumConfigFile() {
            const reticulumConfigPath = this.appInfo.reticulum_config_path;
            if (reticulumConfigPath) {
                ElectronUtils.showPathInFolder(reticulumConfigPath);
            }
        },
        showDatabaseFile() {
            const databasePath = this.appInfo.database_path;
            if (databasePath) {
                ElectronUtils.showPathInFolder(databasePath);
            }
        },
        formatBytes: function (bytes) {
            return Utils.formatBytes(bytes);
        },
        formatNumber: function (num) {
            return Utils.formatNumber(num);
        },
        formatBytesPerSecond: function (bytesPerSecond) {
            return Utils.formatBytesPerSecond(bytesPerSecond);
        },
        onRestoreFileChange(event) {
            const files = event.target.files;
            if (files && files[0]) {
                this.restoreFile = files[0];
                this.restoreFileName = files[0].name;
                this.restoreError = "";
                this.restoreMessage = "";
            }
        },
        async downloadIdentityFile() {
            this.identityBackupMessage = "";
            this.identityBackupError = "";
            try {
                const response = await window.axios.get("/api/v1/identity/backup/download", {
                    responseType: "blob",
                });
                const blob = new Blob([response.data], { type: "application/octet-stream" });
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement("a");
                link.href = url;
                link.setAttribute("download", "identity");
                document.body.appendChild(link);
                link.click();
                link.remove();
                window.URL.revokeObjectURL(url);
                this.identityBackupMessage = "Identity downloaded. Keep it secret.";
            } catch (e) {
                this.identityBackupError = "Failed to download identity";
                console.log(e);
            }
        },
        async copyIdentityBase32() {
            this.identityBase32Message = "";
            this.identityBase32Error = "";
            try {
                const response = await window.axios.get("/api/v1/identity/backup/base32");
                this.identityBase32 = response.data.identity_base32 || "";
                if (!this.identityBase32) {
                    this.identityBase32Error = "No identity available";
                    return;
                }
                await navigator.clipboard.writeText(this.identityBase32);
                this.identityBase32Message = "Identity copied. Clear your clipboard after use.";
            } catch (e) {
                this.identityBase32Error = "Failed to copy identity";
                console.log(e);
            }
        },
        onIdentityRestoreFileChange(event) {
            const files = event.target.files;
            if (files && files[0]) {
                this.identityRestoreFile = files[0];
                this.identityRestoreFileName = files[0].name;
                this.identityRestoreError = "";
                this.identityRestoreMessage = "";
            }
        },
        async restoreIdentityFile() {
            if (this.identityRestoreInProgress) {
                return;
            }
            if (!this.identityRestoreFile) {
                this.identityRestoreError = "Select an identity file to restore.";
                return;
            }
            this.identityRestoreInProgress = true;
            this.identityRestoreMessage = "";
            this.identityRestoreError = "";
            try {
                const formData = new FormData();
                formData.append("file", this.identityRestoreFile);
                const response = await window.axios.post("/api/v1/identity/restore", formData, {
                    headers: { "Content-Type": "multipart/form-data" },
                });
                this.identityRestoreMessage = response.data.message || "Identity restored. Restart app.";
            } catch (e) {
                this.identityRestoreError = "Identity restore failed";
                console.log(e);
            } finally {
                this.identityRestoreInProgress = false;
            }
        },
        async restoreIdentityBase32() {
            if (this.identityRestoreInProgress) {
                return;
            }
            if (!this.identityRestoreBase32) {
                this.identityRestoreError = "Provide a base32 key to restore.";
                return;
            }
            this.identityRestoreInProgress = true;
            this.identityRestoreMessage = "";
            this.identityRestoreError = "";
            try {
                const response = await window.axios.post("/api/v1/identity/restore", {
                    base32: this.identityRestoreBase32.trim(),
                });
                this.identityRestoreMessage = response.data.message || "Identity restored. Restart app.";
            } catch (e) {
                this.identityRestoreError = "Identity restore failed";
                console.log(e);
            } finally {
                this.identityRestoreInProgress = false;
            }
        },
        formatRecoveryResult(value) {
            if (value === null || value === undefined) {
                return "—";
            }
            if (Array.isArray(value)) {
                return value.join(", ");
            }
            return value;
        },
        statusPillClass(isGood) {
            return isGood
                ? "inline-flex items-center gap-1 rounded-full bg-emerald-100 text-emerald-700 px-3 py-1 text-xs font-semibold"
                : "inline-flex items-center gap-1 rounded-full bg-orange-100 text-orange-700 px-3 py-1 text-xs font-semibold";
        },
    },
};
</script>
