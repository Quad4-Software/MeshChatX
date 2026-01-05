<template>
    <div
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-gradient-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div class="flex-1 overflow-y-auto w-full px-4 md:px-8 py-6 text-gray-900 dark:text-zinc-100">
            <div class="space-y-6 w-full max-w-4xl mx-auto pb-20">
                <!-- Basic Info Card -->
                <div v-if="appInfo" class="glass-card !p-8">
                    <div class="flex flex-col gap-8 md:flex-row md:items-center">
                        <!-- Logo & Title -->
                        <div class="flex items-center gap-6">
                            <div
                                class="w-20 h-20 rounded-3xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20 shadow-xl"
                            >
                                <img src="../../public/favicons/favicon-512x512.png" class="w-12 h-12 object-contain" />
                            </div>
                            <div class="space-y-1">
                                <div
                                    class="text-4xl font-black text-gray-900 dark:text-white leading-none tracking-tight"
                                >
                                    MeshChatX
                                </div>
                                <div class="text-sm font-black text-blue-500 uppercase tracking-[0.2em] opacity-80">
                                    {{ $t("about.version", { version: appInfo.version }) }}
                                </div>
                            </div>
                        </div>

                        <div class="flex-1 md:text-right flex flex-wrap justify-start md:justify-end gap-3">
                            <button type="button" class="secondary-chip" @click="showTutorial">
                                <v-icon icon="mdi-help-circle" size="20" class="mr-2"></v-icon>
                                {{ $t("app.tutorial_title") }}
                            </button>
                            <button type="button" class="secondary-chip" @click="showChangelog">
                                <v-icon icon="mdi-history" size="20" class="mr-2"></v-icon>
                                {{ $t("app.changelog_title") }}
                            </button>
                            <button v-if="isElectron" type="button" class="primary-chip" @click="relaunch">
                                <v-icon icon="mdi-restart" size="20" class="mr-2"></v-icon>
                                {{ $t("common.restart_app") }}
                            </button>
                            <button type="button" class="danger-chip" @click="shutdown">
                                <v-icon icon="mdi-power" size="20" class="mr-2"></v-icon>
                                {{ $t("common.shutdown", "Shutdown") }}
                            </button>
                        </div>
                    </div>

                    <div
                        class="mt-10 pt-8 border-t border-gray-100 dark:border-zinc-800 flex flex-col md:flex-row md:items-center justify-between gap-6"
                    >
                        <div class="text-gray-600 dark:text-zinc-400 max-w-xl text-lg leading-relaxed">
                            A secure, resilient, and beautiful communications platform powered by the
                            <a
                                href="https://reticulum.network"
                                target="_blank"
                                class="text-blue-500 font-black hover:underline decoration-2 underline-offset-4"
                                >Reticulum Network Stack</a
                            >.
                        </div>
                        <div class="flex items-center gap-6 shrink-0">
                            <div class="text-right">
                                <div
                                    class="text-[10px] font-black text-gray-400 dark:text-zinc-500 uppercase tracking-[0.2em] leading-none mb-1"
                                >
                                    Database Size
                                </div>
                                <div class="text-2xl font-black text-gray-900 dark:text-white tabular-nums">
                                    {{
                                        formatBytes(
                                            appInfo.database_files
                                                ? appInfo.database_files.total_bytes
                                                : appInfo.database_file_size
                                        )
                                    }}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="space-y-6">
                    <!-- Security & Integrity -->
                    <div v-if="appInfo" class="glass-card !p-6">
                        <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-6">
                            <div
                                class="text-xs font-black text-blue-500 uppercase tracking-[0.2em] flex items-center gap-2"
                            >
                                <v-icon icon="mdi-shield-lock" size="14"></v-icon>
                                Security & Integrity
                            </div>
                            <div v-if="appInfo.integrity_issues" class="flex flex-wrap gap-2">
                                <span
                                    :class="statusPillClass(appInfo.integrity_issues.length === 0)"
                                    class="font-black px-3 py-1 text-[11px]"
                                >
                                    <v-icon
                                        :icon="
                                            appInfo.integrity_issues.length === 0
                                                ? 'mdi-shield-check'
                                                : 'mdi-shield-alert'
                                        "
                                        size="14"
                                        start
                                    ></v-icon>
                                    {{
                                        appInfo.integrity_issues.length === 0
                                            ? $t("about.secured")
                                            : $t("about.tampering_detected")
                                    }}
                                </span>
                                <button
                                    v-if="appInfo.integrity_issues.length > 0"
                                    type="button"
                                    class="secondary-chip px-3 py-1 text-[11px] font-black"
                                    @click="acknowledgeIntegrity"
                                >
                                    <v-icon icon="mdi-check-circle" size="14" start></v-icon>
                                    {{ $t("common.acknowledge_reset") }}
                                </button>
                            </div>
                        </div>

                        <div
                            v-if="appInfo.integrity_issues && appInfo.integrity_issues.length > 0"
                            class="p-4 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 rounded-xl"
                        >
                            <div
                                class="text-xs font-black text-red-700 dark:text-red-400 mb-3 uppercase tracking-wider flex items-center gap-2"
                            >
                                <v-icon icon="mdi-alert-octagon" size="16"></v-icon>
                                Technical Issues Detected
                            </div>
                            <ul class="text-[11px] text-red-600 dark:text-red-300 space-y-2 list-none font-mono">
                                <li v-for="(issue, index) in appInfo.integrity_issues" :key="index" class="flex gap-2">
                                    <span class="opacity-50">•</span>
                                    <span>{{ issue }}</span>
                                </li>
                            </ul>
                        </div>
                        <div
                            v-else
                            class="text-sm text-gray-500 dark:text-zinc-500 flex items-center gap-3 bg-emerald-500/5 p-4 rounded-xl border border-emerald-500/10"
                        >
                            <v-icon icon="mdi-check-decagram" color="green" size="20"></v-icon>
                            <span class="font-bold tracking-tight">{{ $t("about.no_integrity_violations") }}</span>
                        </div>
                    </div>

                    <!-- Advanced Tech Info -->
                    <div v-if="appInfo" class="glass-card !p-6">
                        <div
                            class="text-xs font-black text-blue-500 uppercase tracking-[0.2em] mb-6 flex items-center gap-2"
                        >
                            <v-icon icon="mdi-server" size="14"></v-icon>
                            Environment Information
                        </div>
                        <div class="grid gap-8 sm:grid-cols-2 lg:grid-cols-3 text-sm">
                            <div>
                                <div class="glass-label !text-[10px] mb-2 opacity-50">Reticulum Config</div>
                                <div
                                    class="monospace-field !bg-zinc-50 dark:!bg-zinc-950 break-all text-[11px] !p-3 rounded-xl border border-zinc-100 dark:border-zinc-800"
                                >
                                    {{ appInfo.reticulum_config_path }}
                                </div>
                                <button
                                    v-if="isElectron"
                                    type="button"
                                    class="secondary-chip mt-3 !px-3 !py-1 !text-[10px]"
                                    @click="showReticulumConfigFile"
                                >
                                    <v-icon icon="mdi-folder-open" start size="14"></v-icon> Reveal File
                                </button>
                            </div>
                            <div>
                                <div class="glass-label !text-[10px] mb-2 opacity-50">Database Path</div>
                                <div
                                    class="monospace-field !bg-zinc-50 dark:!bg-zinc-950 break-all text-[11px] !p-3 rounded-xl border border-zinc-100 dark:border-zinc-800"
                                >
                                    {{ appInfo.database_path }}
                                </div>
                                <button
                                    v-if="isElectron"
                                    type="button"
                                    class="secondary-chip mt-3 !px-3 !py-1 !text-[10px]"
                                    @click="showDatabaseFile"
                                >
                                    <v-icon icon="mdi-database-search" start size="14"></v-icon> Reveal DB
                                </button>
                            </div>
                            <div
                                class="flex flex-col justify-center space-y-3 bg-zinc-50 dark:bg-zinc-950 p-4 rounded-xl border border-zinc-100 dark:border-zinc-800"
                            >
                                <div
                                    v-if="config"
                                    class="space-y-3 mb-2 pb-3 border-b border-zinc-100 dark:border-zinc-800"
                                >
                                    <div class="flex flex-col">
                                        <span class="text-[9px] font-black text-blue-500 uppercase tracking-wider"
                                            >Identity Hash</span
                                        >
                                        <span class="font-mono text-[10px] break-all opacity-70">{{
                                            config.identity_hash
                                        }}</span>
                                    </div>
                                    <div class="flex flex-col">
                                        <span class="text-[9px] font-black text-blue-500 uppercase tracking-wider"
                                            >LXMF Address</span
                                        >
                                        <span class="font-mono text-[10px] break-all opacity-70">{{
                                            config.lxmf_address_hash
                                        }}</span>
                                    </div>
                                </div>
                                <div class="flex items-center justify-between">
                                    <span class="text-[10px] font-black text-blue-500 uppercase tracking-wider"
                                        >Python</span
                                    >
                                    <span class="font-mono text-xs font-bold">v{{ appInfo.python_version }}</span>
                                </div>
                                <div class="flex items-center justify-between">
                                    <span class="text-[10px] font-black text-purple-500 uppercase tracking-wider"
                                        >LXMF</span
                                    >
                                    <span class="font-mono text-xs font-bold">v{{ appInfo.lxmf_version }}</span>
                                </div>
                                <div class="flex items-center justify-between">
                                    <span class="text-[10px] font-black text-indigo-500 uppercase tracking-wider"
                                        >RNS</span
                                    >
                                    <span class="font-mono text-xs font-bold">v{{ appInfo.rns_version }}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Dependency Chain -->
                    <div v-if="appInfo" class="glass-card !p-6">
                        <div
                            class="text-xs font-black text-blue-500 uppercase tracking-[0.2em] mb-8 flex items-center gap-2"
                        >
                            <v-icon icon="mdi-link-variant" size="14"></v-icon>
                            Dependency Chain
                        </div>
                        <div class="grid grid-cols-1 lg:grid-cols-2 gap-12 relative">
                            <div class="flex flex-col space-y-8">
                                <div class="flex items-center gap-5">
                                    <div
                                        class="w-12 h-12 rounded-2xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20 shadow-sm"
                                    >
                                        <img
                                            src="../../public/favicons/favicon-512x512.png"
                                            class="w-7 h-7 object-contain"
                                        />
                                    </div>
                                    <div>
                                        <div class="text-sm font-black text-gray-900 dark:text-white">MeshChatX</div>
                                        <div class="text-xs font-mono font-bold text-gray-400">
                                            v{{ appInfo.version }}
                                        </div>
                                    </div>
                                </div>
                                <div
                                    class="flex items-center gap-5 pl-5 border-l-2 border-zinc-100 dark:border-zinc-800 ml-6 relative"
                                >
                                    <div
                                        class="absolute -left-[2px] top-0 bottom-0 w-[2px] bg-gradient-to-b from-blue-500 to-purple-500"
                                    ></div>
                                    <div
                                        class="w-12 h-12 rounded-2xl bg-purple-500/10 flex items-center justify-center border border-purple-500/20 text-purple-600 font-black text-[10px] tracking-tighter shadow-sm"
                                    >
                                        LXMF
                                    </div>
                                    <div>
                                        <div class="text-sm font-black text-gray-900 dark:text-white leading-tight">
                                            Lightweight Extensible Message Format
                                        </div>
                                        <div class="text-xs font-mono font-bold text-gray-400 mt-1">
                                            v{{ appInfo.lxmf_version }}
                                        </div>
                                    </div>
                                </div>
                                <div
                                    class="flex items-center gap-5 pl-5 border-l-2 border-zinc-100 dark:border-zinc-800 ml-6 relative"
                                >
                                    <div
                                        class="absolute -left-[2px] top-0 bottom-0 w-[2px] bg-gradient-to-b from-purple-500 to-indigo-500"
                                    ></div>
                                    <div
                                        class="w-12 h-12 rounded-2xl bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 text-indigo-600 font-black text-[10px] tracking-tighter shadow-sm"
                                    >
                                        RNS
                                    </div>
                                    <div>
                                        <div class="text-sm font-black text-gray-900 dark:text-white leading-tight">
                                            Reticulum Network Stack
                                        </div>
                                        <div class="text-xs font-mono font-bold text-gray-400 mt-1">
                                            v{{ appInfo.rns_version }}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="space-y-8">
                                <div
                                    class="bg-zinc-50 dark:bg-zinc-950 p-5 rounded-2xl border border-zinc-100 dark:border-zinc-800"
                                >
                                    <div
                                        class="text-[10px] font-black text-gray-400 dark:text-zinc-600 uppercase tracking-[0.2em] mb-4"
                                    >
                                        Core Runtime
                                    </div>
                                    <div class="grid grid-cols-2 gap-x-6 gap-y-4">
                                        <div v-if="appInfo.lxst_version" class="flex flex-col">
                                            <span class="text-[9px] font-black text-blue-500/60 uppercase leading-none"
                                                >LXST Engine</span
                                            >
                                            <span
                                                class="text-[11px] font-mono font-bold mt-1.5 opacity-90 tracking-tight"
                                                >v{{ appInfo.lxst_version }}</span
                                            >
                                        </div>
                                        <div v-if="electronVersion" class="flex flex-col">
                                            <span class="text-[9px] font-black text-blue-500/60 uppercase leading-none"
                                                >Electron</span
                                            >
                                            <span
                                                class="text-[11px] font-mono font-bold mt-1.5 opacity-90 tracking-tight"
                                                >v{{ electronVersion }}</span
                                            >
                                        </div>
                                        <div v-if="chromeVersion" class="flex flex-col">
                                            <span class="text-[9px] font-black text-blue-500/60 uppercase leading-none"
                                                >Chrome</span
                                            >
                                            <span
                                                class="text-[11px] font-mono font-bold mt-1.5 opacity-90 tracking-tight"
                                                >v{{ chromeVersion }}</span
                                            >
                                        </div>
                                        <div v-if="nodeVersion" class="flex flex-col">
                                            <span class="text-[9px] font-black text-blue-500/60 uppercase leading-none"
                                                >Node.js</span
                                            >
                                            <span
                                                class="text-[11px] font-mono font-bold mt-1.5 opacity-90 tracking-tight"
                                                >v{{ nodeVersion }}</span
                                            >
                                        </div>
                                    </div>
                                </div>

                                <div v-if="appInfo.dependencies" class="pt-2">
                                    <div
                                        class="text-[10px] font-black text-gray-400 dark:text-zinc-600 uppercase tracking-[0.2em] mb-4"
                                    >
                                        Backend Stack
                                    </div>
                                    <div class="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-4">
                                        <div
                                            v-for="(version, name) in appInfo.dependencies"
                                            :key="name"
                                            class="flex flex-col"
                                        >
                                            <span
                                                class="text-[9px] font-black text-gray-400 dark:text-zinc-600 uppercase truncate leading-none"
                                                >{{ name.replace("_", " ") }}</span
                                            >
                                            <span
                                                class="text-[10px] font-mono font-bold mt-1.5 opacity-50 tracking-tight"
                                                >v{{ version }}</span
                                            >
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Database Health -->
                    <div class="glass-card !p-6">
                        <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-8">
                            <div
                                class="text-xs font-black text-blue-500 uppercase tracking-[0.2em] flex items-center gap-2"
                            >
                                <v-icon icon="mdi-database-cog" size="14"></v-icon>
                                Database Health & Maintenance
                            </div>
                            <div class="flex flex-wrap gap-2">
                                <button
                                    type="button"
                                    class="secondary-chip !px-4 !py-1.5 !text-xs"
                                    :disabled="databaseActionInProgress || healthLoading"
                                    @click="getDatabaseHealth(true)"
                                >
                                    <v-icon icon="mdi-refresh" start size="14"></v-icon>
                                    <span v-if="healthLoading">Loading...</span>
                                    <span v-else>Refresh</span>
                                </button>
                                <button
                                    type="button"
                                    class="primary-chip !px-4 !py-1.5 !text-xs"
                                    :disabled="databaseActionInProgress"
                                    @click="vacuumDatabase"
                                >
                                    <v-icon icon="mdi-broom" start size="14"></v-icon> Vacuum
                                </button>
                                <button
                                    type="button"
                                    class="danger-chip !px-4 !py-1.5 !text-xs"
                                    :disabled="databaseActionInProgress"
                                    @click="runRecovery"
                                >
                                    <v-icon icon="mdi-medical-bag" start size="14"></v-icon> Recovery
                                </button>
                            </div>
                        </div>

                        <div v-if="databaseHealth" class="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
                            <div
                                class="bg-zinc-50 dark:bg-zinc-950 p-4 rounded-2xl border border-zinc-100 dark:border-zinc-800 shadow-inner"
                            >
                                <div
                                    class="text-[9px] font-black text-gray-400 dark:text-zinc-600 uppercase tracking-[0.2em] mb-2 leading-none"
                                >
                                    Integrity
                                </div>
                                <div
                                    :class="[databaseHealth.quick_check === 'ok' ? 'text-emerald-500' : 'text-red-500']"
                                    class="text-lg font-black uppercase tracking-tight"
                                >
                                    {{ databaseHealth.quick_check }}
                                </div>
                            </div>
                            <div
                                class="bg-zinc-50 dark:bg-zinc-950 p-4 rounded-2xl border border-zinc-100 dark:border-zinc-800 shadow-inner"
                            >
                                <div
                                    class="text-[9px] font-black text-gray-400 dark:text-zinc-600 uppercase tracking-[0.2em] mb-2 leading-none"
                                >
                                    Journal
                                </div>
                                <div class="text-lg font-black uppercase text-blue-500 tracking-tight">
                                    {{ databaseHealth.journal_mode }}
                                </div>
                            </div>
                            <div
                                class="bg-zinc-50 dark:bg-zinc-950 p-4 rounded-2xl border border-zinc-100 dark:border-zinc-800 shadow-inner"
                            >
                                <div
                                    class="text-[9px] font-black text-gray-400 dark:text-zinc-600 uppercase tracking-[0.2em] mb-2 leading-none"
                                >
                                    Page Count
                                </div>
                                <div class="text-lg font-black font-mono tracking-tight tabular-nums">
                                    {{ databaseHealth.page_count }}
                                </div>
                            </div>
                            <div
                                class="bg-zinc-50 dark:bg-zinc-950 p-4 rounded-2xl border border-zinc-100 dark:border-zinc-800 shadow-inner"
                            >
                                <div
                                    class="text-[9px] font-black text-gray-400 dark:text-zinc-600 uppercase tracking-[0.2em] mb-2 leading-none"
                                >
                                    Free Space
                                </div>
                                <div class="text-lg font-black text-amber-500 tracking-tight tabular-nums">
                                    {{ formatBytes(databaseHealth.estimated_free_bytes) }}
                                </div>
                            </div>
                        </div>

                        <div class="border-t border-zinc-100 dark:border-zinc-800 pt-8 space-y-8">
                            <!-- Backups -->
                            <div class="flex flex-col md:flex-row md:items-center justify-between gap-6">
                                <div class="space-y-1">
                                    <div
                                        class="font-black text-gray-900 dark:text-white text-sm tracking-tight flex items-center gap-2"
                                    >
                                        <v-icon icon="mdi-content-save-all" size="16" class="text-blue-500"></v-icon>
                                        Database Backups
                                    </div>
                                    <div class="text-xs text-gray-500">
                                        Full snapshots of your communications database.
                                    </div>
                                </div>
                                <button
                                    type="button"
                                    class="primary-chip !px-5 !py-2.5"
                                    :disabled="backupInProgress"
                                    @click="backupDatabase"
                                >
                                    <v-icon icon="mdi-download" start></v-icon>
                                    <span v-if="backupInProgress">Downloading...</span>
                                    <span v-else>Download Backup</span>
                                </button>
                            </div>

                            <!-- Snapshots -->
                            <div class="space-y-6">
                                <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                    <div class="space-y-1">
                                        <div
                                            class="font-black text-gray-900 dark:text-white text-sm tracking-tight flex items-center gap-2"
                                        >
                                            <v-icon icon="mdi-camera" size="16" class="text-purple-500"></v-icon>
                                            Local Snapshots
                                        </div>
                                        <div class="text-xs text-gray-500">
                                            Create point-in-time restore points on disk.
                                        </div>
                                    </div>
                                    <div class="flex gap-2 w-full md:w-auto">
                                        <input
                                            v-model="snapshotName"
                                            type="text"
                                            placeholder="Snapshot label..."
                                            class="bg-zinc-50 dark:bg-zinc-900 px-4 py-2 rounded-xl text-sm border border-zinc-100 dark:border-zinc-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 flex-1 md:min-w-[200px]"
                                        />
                                        <button
                                            type="button"
                                            class="primary-chip !px-6"
                                            :disabled="snapshotInProgress"
                                            @click="createSnapshot"
                                        >
                                            <span v-if="snapshotInProgress">Creating...</span>
                                            <span v-else>Create</span>
                                        </button>
                                    </div>
                                </div>

                                <div v-if="snapshots.length > 0" class="grid gap-3 sm:grid-cols-2">
                                    <div
                                        v-for="snapshot in snapshots"
                                        :key="snapshot.path"
                                        class="flex items-center justify-between p-4 rounded-2xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-100 dark:border-zinc-800 hover:border-purple-500/20 transition-all group"
                                    >
                                        <div class="flex flex-col">
                                            <span
                                                class="font-black text-gray-900 dark:text-white text-xs truncate max-w-[150px]"
                                                >{{ snapshot.name }}</span
                                            >
                                            <span class="text-[10px] font-bold text-gray-400 mt-1 tabular-nums"
                                                >{{ formatBytes(snapshot.size) }} • {{ snapshot.created_at }}</span
                                            >
                                        </div>
                                        <button
                                            type="button"
                                            class="secondary-chip !px-3 !py-1 !text-[10px] opacity-0 group-hover:opacity-100"
                                            @click="restoreFromSnapshot(snapshot.path)"
                                        >
                                            Restore
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <!-- Auto Backups -->
                            <div v-if="autoBackups.length > 0" class="space-y-6">
                                <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                    <div class="space-y-1">
                                        <div
                                            class="font-black text-gray-900 dark:text-white text-sm tracking-tight flex items-center gap-2"
                                        >
                                            <v-icon icon="mdi-history" size="16" class="text-blue-500"></v-icon>
                                            Automatic Backups
                                        </div>
                                        <div class="text-xs text-gray-500">
                                            Automated daily snapshots of your database.
                                        </div>
                                    </div>
                                </div>

                                <div class="grid gap-3 sm:grid-cols-2">
                                    <div
                                        v-for="backup in autoBackups"
                                        :key="backup.path"
                                        class="flex items-center justify-between p-4 rounded-2xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-100 dark:border-zinc-800 hover:border-blue-500/20 transition-all group"
                                    >
                                        <div class="flex flex-col">
                                            <span
                                                class="font-black text-gray-900 dark:text-white text-xs truncate max-w-[150px]"
                                                >{{ backup.name }}</span
                                            >
                                            <span class="text-[10px] font-bold text-gray-400 mt-1 tabular-nums"
                                                >{{ formatBytes(backup.size) }} • {{ backup.created_at }}</span
                                            >
                                        </div>
                                        <button
                                            type="button"
                                            class="secondary-chip !px-3 !py-1 !text-[10px] opacity-0 group-hover:opacity-100"
                                            @click="restoreFromSnapshot(backup.path)"
                                        >
                                            Restore
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <!-- Identity Section -->
                            <div class="bg-red-500/5 p-6 rounded-2xl border border-red-500/10 space-y-6">
                                <div class="flex items-center gap-4 text-red-500">
                                    <v-icon icon="mdi-key-alert" size="24"></v-icon>
                                    <div class="space-y-0.5">
                                        <div class="font-black text-sm tracking-tight">Identity Key Control</div>
                                        <div class="text-[10px] font-bold uppercase tracking-widest opacity-70 italic">
                                            Critical Security Warning
                                        </div>
                                    </div>
                                </div>

                                <div class="flex flex-wrap gap-3">
                                    <button
                                        type="button"
                                        class="danger-chip !px-5 !py-2.5"
                                        @click="downloadIdentityFile"
                                    >
                                        <v-icon icon="mdi-file-export" start></v-icon>
                                        Export Key File
                                    </button>
                                    <button
                                        type="button"
                                        class="secondary-chip !border-red-200 dark:!border-red-900/50 !text-red-600 dark:!text-red-400 !px-5 !py-2.5"
                                        @click="copyIdentityBase32"
                                    >
                                        <v-icon icon="mdi-content-copy" start></v-icon>
                                        Copy Base32 Key
                                    </button>
                                </div>

                                <div class="space-y-4 pt-4 border-t border-red-500/10">
                                    <div class="text-[10px] font-black text-red-500/60 uppercase tracking-widest">
                                        Restore Identity
                                    </div>
                                    <div class="flex flex-col sm:flex-row gap-3">
                                        <button
                                            type="button"
                                            class="secondary-chip flex-1 !border-dashed !border-2 !rounded-2xl !py-4"
                                            @click="$refs.identityFileInput.click()"
                                        >
                                            <v-icon icon="mdi-upload" start></v-icon>
                                            Upload Key File
                                        </button>
                                        <input
                                            ref="identityFileInput"
                                            type="file"
                                            accept=".identity,.bin,.key"
                                            class="hidden"
                                            @change="onIdentityRestoreFileChange"
                                        />
                                        <div
                                            class="text-center sm:py-2 text-[10px] font-black text-zinc-400 uppercase italic px-2 shrink-0 self-center"
                                        >
                                            — or —
                                        </div>
                                        <button
                                            type="button"
                                            class="secondary-chip flex-1 !border-dashed !border-2 !rounded-2xl !py-4"
                                            @click="showIdentityPaste = !showIdentityPaste"
                                        >
                                            <v-icon icon="mdi-clipboard-text" start></v-icon>
                                            Paste Base32
                                        </button>
                                    </div>

                                    <transition name="fade-blur">
                                        <div v-if="showIdentityPaste" class="space-y-3">
                                            <textarea
                                                v-model="identityRestoreBase32"
                                                rows="4"
                                                placeholder="Paste your base32 identity key here..."
                                                class="w-full bg-white dark:bg-zinc-950 p-4 rounded-xl font-mono text-xs border border-zinc-100 dark:border-zinc-800 focus:outline-none focus:ring-2 focus:ring-red-500/20"
                                            ></textarea>
                                            <button
                                                type="button"
                                                class="danger-chip w-full !py-3 !rounded-xl"
                                                :disabled="identityRestoreInProgress"
                                                @click="restoreIdentityBase32"
                                            >
                                                <span v-if="identityRestoreInProgress">Restoring...</span>
                                                <span v-else>Confirm Key Restore</span>
                                            </button>
                                        </div>
                                    </transition>
                                </div>
                            </div>
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
import ToastUtils from "../../js/ToastUtils";
import GlobalEmitter from "../../js/GlobalEmitter";
export default {
    name: "AboutPage",
    components: {},
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
            autoBackups: [],
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
            showIdentityPaste: false,
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
        this.listAutoBackups();
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
        async listAutoBackups() {
            try {
                const response = await window.axios.get("/api/v1/database/backups");
                this.autoBackups = response.data;
            } catch (e) {
                console.log("Failed to list auto-backups", e);
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
        async runRecovery() {
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
            GlobalEmitter.emit("show-changelog");
        },
        showTutorial() {
            GlobalEmitter.emit("show-tutorial");
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
                this.identityRestoreMessage = response.data.message || "Identity imported.";
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
                this.identityRestoreMessage = response.data.message || "Identity imported.";
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

<style scoped>
:deep(.about-btn:focus-visible) {
    outline: 2px solid rgba(59, 130, 246, 0.35);
    outline-offset: 2px;
}
</style>
