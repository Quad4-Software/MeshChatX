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
                        <div class="flex flex-col sm:flex-row gap-2">
                            <button
                                type="button"
                                class="danger-chip px-4 py-2 text-sm justify-center"
                                @click="shutdown"
                            >
                                <MaterialDesignIcon icon-name="power" class="w-4 h-4" />
                                {{ $t("common.shutdown", "Shutdown") }}
                            </button>
                            <button
                                type="button"
                                class="secondary-chip px-4 py-2 text-sm justify-center"
                                @click="showChangelog"
                            >
                                <MaterialDesignIcon icon-name="history" class="w-4 h-4" />
                                {{ $t("app.changelog_title") }}
                            </button>
                            <button
                                type="button"
                                class="secondary-chip px-4 py-2 text-sm justify-center"
                                @click="showTutorial"
                            >
                                <MaterialDesignIcon icon-name="help-circle" class="w-4 h-4" />
                                {{ $t("app.tutorial_title") }}
                            </button>
                            <button
                                v-if="isElectron"
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

                <div v-if="appInfo" class="glass-card">
                    <div class="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                        <div>
                            <div class="text-lg font-semibold text-gray-900 dark:text-white">
                                {{ $t("about.security_integrity") }}
                            </div>
                            <div class="text-xs text-gray-600 dark:text-gray-400">
                                {{ $t("about.security_integrity_description") }}
                            </div>
                        </div>
                        <div v-if="appInfo.integrity_issues" class="flex flex-wrap gap-2">
                            <span :class="statusPillClass(appInfo.integrity_issues.length === 0)">
                                <MaterialDesignIcon
                                    :icon-name="appInfo.integrity_issues.length === 0 ? 'shield-check' : 'shield-alert'"
                                    class="w-4 h-4"
                                />
                                {{
                                    appInfo.integrity_issues.length === 0
                                        ? $t("about.secured")
                                        : $t("about.tampering_detected")
                                }}
                            </span>
                            <button
                                v-if="appInfo.integrity_issues.length > 0"
                                type="button"
                                class="secondary-chip px-3 py-1 text-xs"
                                @click="acknowledgeIntegrity"
                            >
                                <MaterialDesignIcon icon-name="check-circle-outline" class="w-4 h-4" />
                                {{ $t("common.acknowledge_reset") }}
                            </button>
                        </div>
                    </div>
                    <div
                        v-if="appInfo.integrity_issues && appInfo.integrity_issues.length > 0"
                        class="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
                    >
                        <div class="text-sm font-semibold text-red-700 dark:text-red-400 mb-2">
                            {{ $t("about.technical_issues") }}
                        </div>
                        <ul class="text-xs text-red-600 dark:text-red-300 space-y-1 list-disc list-inside">
                            <li v-for="(issue, index) in appInfo.integrity_issues" :key="index">{{ issue }}</li>
                        </ul>
                    </div>
                    <div v-else class="mt-4 text-sm text-gray-500 dark:text-gray-400 flex items-center gap-2">
                        <MaterialDesignIcon icon-name="check-circle" class="w-4 h-4 text-emerald-500" />
                        {{ $t("about.no_integrity_violations") }}
                    </div>
                </div>

                <div v-if="appInfo" class="glass-card">
                    <div class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                        {{ $t("about.dependency_chain") }}
                    </div>
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 relative">
                        <!-- Main Dependencies -->
                        <div class="flex flex-col space-y-4">
                            <!-- MeshChatX -->
                            <div class="flex items-center gap-4">
                                <div
                                    class="w-10 h-10 rounded-full bg-blue-500/10 flex items-center justify-center border border-blue-500/20"
                                >
                                    <img
                                        src="../../public/favicons/favicon-512x512.png"
                                        class="w-6 h-6 object-contain"
                                    />
                                </div>
                                <div class="flex-1">
                                    <div class="text-sm font-bold text-gray-900 dark:text-white">MeshChatX</div>
                                    <div class="text-xs text-gray-500 dark:text-gray-400">v{{ appInfo.version }}</div>
                                </div>
                            </div>

                            <!-- Connector -->
                            <div class="ml-5 border-l-2 border-gray-200 dark:border-zinc-800 h-4"></div>

                            <!-- LXMF -->
                            <div class="flex items-center gap-4">
                                <div
                                    class="w-10 h-10 rounded-full bg-purple-500/10 flex items-center justify-center border border-purple-500/20 text-purple-600 font-black text-xs"
                                >
                                    LXMF
                                </div>
                                <div class="flex-1">
                                    <div class="text-sm font-bold text-gray-900 dark:text-white">
                                        Lightweight Extensible Message Format
                                    </div>
                                    <div class="text-xs text-gray-500 dark:text-gray-400">
                                        v{{ appInfo.lxmf_version }}
                                    </div>
                                </div>
                            </div>

                            <!-- Connector -->
                            <div class="ml-5 border-l-2 border-gray-200 dark:border-zinc-800 h-4"></div>

                            <!-- RNS -->
                            <div class="flex items-center gap-4">
                                <div
                                    class="w-10 h-10 rounded-full bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 text-indigo-600 font-black text-xs"
                                >
                                    RNS
                                </div>
                                <div class="flex-1">
                                    <div class="text-sm font-bold text-gray-900 dark:text-white">
                                        Reticulum Network Stack
                                    </div>
                                    <div class="text-xs text-gray-500 dark:text-gray-400">
                                        v{{ appInfo.rns_version }}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Side & Python Dependencies -->
                        <div class="space-y-8">
                            <!-- Side Dependencies -->
                            <div>
                                <div
                                    class="text-xs font-bold text-gray-400 dark:text-zinc-500 uppercase tracking-wider mb-3"
                                >
                                    {{ $t("about.other_core_components", "Other Core Components") }}
                                </div>
                                <div class="grid grid-cols-2 sm:grid-cols-3 gap-4">
                                    <div v-if="appInfo.lxst_version" class="flex flex-col">
                                        <span class="text-[10px] font-black text-blue-500 uppercase">LXST</span>
                                        <span class="text-sm font-medium text-gray-700 dark:text-zinc-300"
                                            >v{{ appInfo.lxst_version }}</span
                                        >
                                    </div>
                                    <div class="flex flex-col">
                                        <span class="text-[10px] font-black text-blue-500 uppercase">Python</span>
                                        <span class="text-sm font-medium text-gray-700 dark:text-zinc-300"
                                            >v{{ appInfo.python_version }}</span
                                        >
                                    </div>
                                    <div v-if="electronVersion" class="flex flex-col">
                                        <span class="text-[10px] font-black text-blue-500 uppercase">Electron</span>
                                        <span class="text-sm font-medium text-gray-700 dark:text-zinc-300"
                                            >v{{ electronVersion }}</span
                                        >
                                    </div>
                                    <div v-if="chromeVersion" class="flex flex-col">
                                        <span class="text-[10px] font-black text-blue-500 uppercase">Chrome</span>
                                        <span class="text-sm font-medium text-gray-700 dark:text-zinc-300"
                                            >v{{ chromeVersion }}</span
                                        >
                                    </div>
                                    <div v-if="nodeVersion" class="flex flex-col">
                                        <span class="text-[10px] font-black text-blue-500 uppercase">Node</span>
                                        <span class="text-sm font-medium text-gray-700 dark:text-zinc-300"
                                            >v{{ nodeVersion }}</span
                                        >
                                    </div>
                                </div>
                            </div>

                            <!-- Python Dependencies -->
                            <div v-if="appInfo.dependencies" class="pt-6 border-t border-gray-100 dark:border-zinc-800">
                                <div
                                    class="text-xs font-bold text-gray-400 dark:text-zinc-500 uppercase tracking-wider mb-3"
                                >
                                    {{ $t("about.backend_dependencies") }}
                                </div>
                                <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                                    <div v-for="(version, name) in appInfo.dependencies" :key="name" class="flex flex-col">
                                        <span class="text-[10px] font-black text-blue-500/70 uppercase">{{
                                            name.replace("_", " ")
                                        }}</span>
                                        <span class="text-xs font-medium text-gray-600 dark:text-zinc-400"
                                            >v{{ version }}</span
                                        >
                                    </div>
                                </div>
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
                        <div class="font-semibold text-gray-900 dark:text-white pt-2">Snapshots</div>
                        <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
                            <input
                                v-model="snapshotName"
                                type="text"
                                placeholder="Snapshot name"
                                class="input-field max-w-xs"
                            />
                            <button
                                type="button"
                                class="primary-chip px-3 py-2 text-xs"
                                :disabled="snapshotInProgress"
                                @click="createSnapshot"
                            >
                                <MaterialDesignIcon icon-name="camera" class="w-4 h-4" />
                                Create Snapshot
                            </button>
                        </div>
                        <div v-if="snapshots.length > 0" class="mt-3 space-y-2">
                            <div
                                v-for="snapshot in snapshots"
                                :key="snapshot.path"
                                class="flex items-center justify-between p-2 rounded-lg bg-gray-50 dark:bg-zinc-800 border border-gray-100 dark:border-zinc-700 text-xs"
                            >
                                <div class="flex flex-col">
                                    <span class="font-bold text-gray-900 dark:text-white">{{ snapshot.name }}</span>
                                    <span class="text-gray-500"
                                        >{{ formatBytes(snapshot.size) }} • {{ snapshot.created_at }}</span
                                    >
                                </div>
                                <button
                                    type="button"
                                    class="secondary-chip px-2 py-1"
                                    @click="restoreFromSnapshot(snapshot.path)"
                                >
                                    Restore
                                </button>
                            </div>
                        </div>
                        <div v-if="snapshotMessage" class="text-xs text-emerald-600">{{ snapshotMessage }}</div>
                        <div v-if="snapshotError" class="text-xs text-red-600">{{ snapshotError }}</div>

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

                    <div v-if="electronMemoryUsage" class="glass-card space-y-3">
                        <header class="flex items-center gap-2">
                            <MaterialDesignIcon icon-name="electron-framework" class="w-5 h-5 text-blue-400" />
                            <div>
                                <div class="text-lg font-semibold text-gray-900 dark:text-white">
                                    Electron Resources
                                </div>
                                <div class="text-xs text-emerald-500 flex items-center gap-1">
                                    <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                                    {{ $t("about.live") }}
                                </div>
                            </div>
                        </header>
                        <div class="metric-row">
                            <div>
                                <div class="glass-label">Private Memory</div>
                                <div class="metric-value">{{ formatBytes(electronMemoryUsage.private * 1024) }}</div>
                            </div>
                            <div>
                                <div class="glass-label">Resident Set</div>
                                <div class="metric-value">
                                    {{ formatBytes(electronMemoryUsage.residentSet * 1024) }}
                                </div>
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
import DialogUtils from "../../js/DialogUtils";
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
            electronMemoryUsage: null,
            backupInProgress: false,
            backupMessage: "",
            backupError: "",
            restoreInProgress: false,
            restoreMessage: "",
            restoreError: "",
            restoreFileName: "",
            restoreFile: null,
            snapshotName: "",
            snapshots: [],
            snapshotInProgress: false,
            snapshotMessage: "",
            snapshotError: "",
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
            electronVersion: null,
            chromeVersion: null,
            nodeVersion: null,
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
        this.listSnapshots();
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
        async listSnapshots() {
            try {
                const response = await window.axios.get("/api/v1/database/snapshots");
                this.snapshots = response.data;
            } catch (e) {
                console.log("Failed to list snapshots", e);
            }
        },
        async createSnapshot() {
            if (this.snapshotInProgress) return;
            this.snapshotInProgress = true;
            this.snapshotMessage = "";
            this.snapshotError = "";
            try {
                await window.axios.post("/api/v1/database/snapshot", {
                    name: this.snapshotName || `snapshot-${Math.floor(Date.now() / 1000)}`,
                });
                this.snapshotMessage = "Snapshot created successfully";
                this.snapshotName = "";
                await this.listSnapshots();
            } catch (e) {
                this.snapshotError = "Failed to create snapshot";
                console.log(e);
            } finally {
                this.snapshotInProgress = false;
            }
        },
        async restoreFromSnapshot(path) {
            if (
                !(await DialogUtils.confirm(
                    "Are you sure you want to restore this snapshot? This will overwrite the current database and require an app relaunch."
                ))
            ) {
                return;
            }
            try {
                const response = await window.axios.post("/api/v1/database/restore", { path });
                if (response.data.status === "success") {
                    ToastUtils.success("Database restored. Relaunching...");
                    if (this.isElectron) {
                        setTimeout(() => ElectronUtils.relaunch(), 2000);
                    }
                }
            } catch (e) {
                ToastUtils.error("Failed to restore snapshot");
                console.log(e);
            }
        },
        async getAppInfo() {
            try {
                const response = await window.axios.get("/api/v1/app/info");
                this.appInfo = response.data.app_info;

                if (this.isElectron) {
                    this.electronMemoryUsage = await ElectronUtils.getMemoryUsage();
                    this.electronVersion = window.electron.electronVersion();
                    this.chromeVersion = window.electron.chromeVersion();
                    this.nodeVersion = window.electron.nodeVersion();
                }
            } catch (e) {
                // do nothing if failed to load app info
                console.log(e);
            }
        },
        async acknowledgeIntegrity() {
            if (
                await DialogUtils.confirm(
                    "Are you sure you want to acknowledge these integrity issues? This will update the security manifest to match the current state of your files."
                )
            ) {
                try {
                    await window.axios.post("/api/v1/app/integrity/acknowledge");
                    ToastUtils.success("Integrity issues acknowledged");
                    await this.getAppInfo();
                } catch (e) {
                    ToastUtils.error("Failed to acknowledge integrity issues");
                    console.log(e);
                }
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
        async shutdown() {
            if (
                await DialogUtils.confirm(
                    "Are you sure you want to shutdown the app? This will stop the server and close the application."
                )
            ) {
                try {
                    // try to notify backend first
                    await window.axios.post("/api/v1/app/shutdown");
                } catch {
                    // ignore errors if backend is already stopping
                }

                if (this.isElectron) {
                    ElectronUtils.shutdown();
                } else {
                    ToastUtils.success("Shutdown command sent to server.");
                }
            }
        },
        showChangelog() {
            this.$router.push({ name: "changelog" });
        },
        showTutorial() {
            this.$router.push({ name: "tutorial" });
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
