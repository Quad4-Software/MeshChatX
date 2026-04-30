<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-slate-50 dark:bg-zinc-950">
        <div
            class="flex-1 overflow-y-auto overflow-x-hidden w-full min-w-0 px-3 sm:px-5 md:px-5 lg:px-8 py-4 sm:py-6 text-gray-900 dark:text-zinc-100"
        >
            <div class="space-y-0 w-full max-w-4xl mx-auto pb-16 sm:pb-24 min-w-0">
                <div v-if="appInfo" class="about-section">
                    <div class="flex flex-col gap-8 lg:flex-row lg:items-center">
                        <!-- Logo & Title -->
                        <div class="flex items-center gap-6">
                            <img
                                src="../../public/favicons/favicon-512x512.png"
                                class="h-20 w-20 shrink-0 object-contain"
                                alt=""
                            />
                            <div class="space-y-1">
                                <div
                                    class="text-4xl font-black text-gray-900 dark:text-white leading-none tracking-tight"
                                >
                                    {{ $t("about.app_name") }}
                                </div>
                                <div
                                    class="flex flex-col gap-0.5 sm:flex-row sm:flex-wrap sm:items-baseline sm:gap-x-3 sm:gap-y-0"
                                >
                                    <div class="text-sm font-black uppercase tracking-[0.2em] text-blue-500 opacity-80">
                                        {{ $t("about.version", { version: appInfo.version }) }}
                                    </div>
                                    <div
                                        v-if="formattedUiBuildDate"
                                        class="text-xs font-medium normal-case tracking-normal text-gray-500 dark:text-zinc-500"
                                    >
                                        {{ $t("about.ui_build", { date: formattedUiBuildDate }) }}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div
                            class="grid w-full grid-cols-2 gap-2 sm:flex sm:w-auto sm:flex-1 sm:flex-wrap sm:justify-end sm:gap-3"
                        >
                            <button type="button" class="about-action-btn secondary-chip" @click="showTutorial">
                                <v-icon icon="mdi-help-circle" size="20" class="mr-2 shrink-0"></v-icon>
                                <span class="truncate">{{ $t("app.tutorial_title") }}</span>
                            </button>
                            <button type="button" class="about-action-btn secondary-chip" @click="showChangelog">
                                <v-icon icon="mdi-history" size="20" class="mr-2 shrink-0"></v-icon>
                                <span class="truncate">{{ $t("app.changelog_title") }}</span>
                            </button>
                            <router-link
                                :to="{ name: 'licenses' }"
                                class="about-action-btn secondary-chip inline-flex items-center no-underline"
                            >
                                <v-icon icon="mdi-license" size="20" class="mr-2 shrink-0"></v-icon>
                                <span class="truncate">{{ $t("about.third_party_licenses") }}</span>
                            </router-link>
                            <button
                                v-if="isElectron"
                                type="button"
                                class="about-action-btn primary-chip"
                                @click="relaunch"
                            >
                                <v-icon icon="mdi-restart" size="20" class="mr-2 shrink-0"></v-icon>
                                <span class="truncate">{{ $t("common.restart_app") }}</span>
                            </button>
                            <button
                                type="button"
                                class="about-action-btn secondary-chip"
                                :disabled="reloadingRns"
                                @click="restartRns"
                            >
                                <v-icon icon="mdi-restart-alert" size="20" class="mr-2 shrink-0"></v-icon>
                                <span class="truncate">{{
                                    reloadingRns ? $t("app.reloading_rns") : $t("app.restart_rns")
                                }}</span>
                            </button>
                            <button type="button" class="about-action-btn danger-chip" @click="shutdown">
                                <v-icon icon="mdi-power" size="20" class="mr-2 shrink-0"></v-icon>
                                <span class="truncate">{{ $t("common.shutdown") }}</span>
                            </button>
                        </div>
                    </div>

                    <div class="mt-10 pt-8 border-t border-gray-100 dark:border-zinc-800 flex flex-col gap-6">
                        <div class="text-gray-600 dark:text-zinc-400 max-w-xl text-lg leading-relaxed">
                            {{ $t("about.tagline_lead") }}
                            <a
                                href="https://reticulum.network"
                                target="_blank"
                                class="text-blue-500 font-black hover:underline decoration-2 underline-offset-4"
                                >{{ $t("about.tagline_link") }}</a
                            >{{ $t("about.tagline_after") }}
                        </div>

                        <div class="mt-6 pt-6 border-t border-gray-200/70 dark:border-zinc-800/80 space-y-3">
                            <div class="flex items-center justify-between">
                                <div
                                    class="text-xs font-black uppercase tracking-widest text-gray-500 dark:text-zinc-500"
                                >
                                    {{ $t("about.contact_developer") }}
                                </div>
                                <v-icon
                                    :icon="showContactDev ? 'mdi-chevron-up' : 'mdi-chevron-down'"
                                    size="18"
                                ></v-icon>
                            </div>
                            <button
                                class="w-full text-left flex items-center justify-between px-4 py-2 rounded-xl bg-blue-500/10 hover:bg-blue-500/20 text-blue-600 dark:text-blue-400 border border-blue-500/20 transition-all"
                                @click="showContactDev = !showContactDev"
                            >
                                <div class="flex items-center gap-2">
                                    <v-icon icon="mdi-account-card-details" size="18"></v-icon>
                                    <span class="text-xs font-black uppercase tracking-widest">{{
                                        $t("about.contact_details")
                                    }}</span>
                                </div>
                            </button>

                            <transition name="fade">
                                <div
                                    v-if="showContactDev"
                                    class="mt-4 p-5 rounded-2xl bg-white/50 dark:bg-zinc-950/50 border border-gray-100 dark:border-zinc-800 space-y-4"
                                >
                                    <div class="space-y-1">
                                        <div class="text-[9px] font-black text-gray-400 uppercase tracking-widest">
                                            {{ $t("about.contact_lxmf_address") }}
                                        </div>
                                        <div class="flex items-center gap-2">
                                            <code
                                                class="text-[11px] font-mono bg-zinc-100 dark:bg-zinc-900 px-2 py-1 rounded-lg break-all"
                                                >7cc8d66b4f6a0e0e49d34af7f6077b5a</code
                                            >
                                            <button
                                                class="p-1 hover:text-blue-500 transition"
                                                @click="
                                                    copyValue(
                                                        '7cc8d66b4f6a0e0e49d34af7f6077b5a',
                                                        'about.contact_lxmf_address'
                                                    )
                                                "
                                            >
                                                <v-icon icon="mdi-content-copy" size="14"></v-icon>
                                            </button>
                                        </div>
                                    </div>
                                    <div class="space-y-1">
                                        <div class="text-[9px] font-black text-gray-400 uppercase tracking-widest">
                                            {{ $t("about.contact_alternate") }}
                                        </div>
                                        <div class="flex items-center gap-2">
                                            <code
                                                class="text-[11px] font-mono bg-zinc-100 dark:bg-zinc-900 px-2 py-1 rounded-lg break-all"
                                                >43d3309adf27fc446556121b553b56a6</code
                                            >
                                            <button
                                                class="p-1 hover:text-blue-500 transition"
                                                @click="
                                                    copyValue(
                                                        '43d3309adf27fc446556121b553b56a6',
                                                        'about.contact_alternate'
                                                    )
                                                "
                                            >
                                                <v-icon icon="mdi-content-copy" size="14"></v-icon>
                                            </button>
                                        </div>
                                    </div>
                                    <div
                                        class="text-xs font-bold text-gray-500 dark:text-white italic bg-blue-500/5 p-3 rounded-xl border border-blue-500/10 flex items-center gap-2"
                                    >
                                        <v-icon icon="mdi-information-outline" size="14" class="text-blue-500"></v-icon>
                                        {{ $t("about.contact_propagation_hint") }}
                                    </div>
                                </div>
                            </transition>
                        </div>

                        <div class="mt-6 pt-6 border-t border-gray-200/70 dark:border-zinc-800/80 space-y-3">
                            <button
                                type="button"
                                class="w-full text-left flex items-center justify-between px-4 py-2 rounded-xl bg-violet-500/10 hover:bg-violet-500/20 text-violet-800 dark:text-violet-200 border border-violet-500/20 transition-all"
                                @click="showDonate = !showDonate"
                            >
                                <div class="flex items-center gap-2">
                                    <v-icon icon="mdi-hand-heart" size="18"></v-icon>
                                    <span class="text-xs font-black uppercase tracking-widest">{{
                                        $t("about.donate_label")
                                    }}</span>
                                </div>
                                <v-icon :icon="showDonate ? 'mdi-chevron-up' : 'mdi-chevron-down'" size="18"></v-icon>
                            </button>

                            <transition name="fade">
                                <div
                                    v-if="showDonate"
                                    class="mt-4 p-5 rounded-2xl bg-white/50 dark:bg-zinc-950/50 border border-gray-100 dark:border-zinc-800 space-y-4"
                                >
                                    <div class="space-y-1">
                                        <div class="text-[9px] font-black text-gray-400 uppercase tracking-widest">
                                            {{ $t("about.donate_monero_label") }}
                                        </div>
                                        <div class="flex items-center gap-2">
                                            <code
                                                class="text-[11px] font-mono bg-zinc-100 dark:bg-zinc-900 px-2 py-1 rounded-lg break-all select-all"
                                                >{{ moneroDonateAddress }}</code
                                            >
                                            <button
                                                type="button"
                                                class="p-1 hover:text-violet-600 dark:hover:text-violet-300 transition shrink-0"
                                                :aria-label="$t('about.donate_copy_monero')"
                                                @click="copyValue(moneroDonateAddress, 'about.donate_monero_label')"
                                            >
                                                <v-icon icon="mdi-content-copy" size="14"></v-icon>
                                            </button>
                                        </div>
                                    </div>

                                    <div class="flex flex-col gap-2 sm:flex-row sm:flex-wrap pt-1">
                                        <a
                                            href="https://ko-fi.com/quad4"
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            class="inline-flex flex-1 items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-orange-500/15 hover:bg-orange-500/25 text-orange-900 dark:text-orange-100 border border-orange-500/25 text-xs font-bold uppercase tracking-wide min-h-[44px]"
                                        >
                                            <v-icon icon="mdi-coffee" size="18"></v-icon>
                                            {{ $t("about.donate_kofi") }}
                                        </a>
                                        <a
                                            href="https://buymeacoffee.com/quad4"
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            class="inline-flex flex-1 items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 text-amber-950 dark:text-amber-50 border border-amber-500/25 text-xs font-bold uppercase tracking-wide min-h-[44px]"
                                        >
                                            <v-icon icon="mdi-cup" size="18"></v-icon>
                                            {{ $t("about.donate_buymeacoffee") }}
                                        </a>
                                    </div>
                                </div>
                            </transition>
                        </div>

                        <div class="flex items-center gap-6 shrink-0">
                            <div class="text-right">
                                <div
                                    class="text-[10px] font-black text-gray-400 dark:text-zinc-500 uppercase tracking-[0.2em] leading-none mb-1"
                                >
                                    {{ $t("about.database_size") }}
                                </div>
                                <div class="text-2xl font-black text-gray-900 dark:text-white tabular-nums">
                                    {{
                                        formatBytes(
                                            (appInfo.database_files
                                                ? appInfo.database_files.total_bytes
                                                : appInfo.database_file_size) || 0
                                        )
                                    }}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="space-y-6">
                    <!-- Security & Integrity -->
                    <div v-if="appInfo" class="about-section hidden sm:block">
                        <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between mb-6">
                            <div
                                class="text-xs font-black text-blue-500 uppercase tracking-[0.2em] flex items-center gap-2"
                            >
                                <v-icon icon="mdi-shield-lock" size="14"></v-icon>
                                {{ $t("about.security_integrity") }}
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
                                        :class="
                                            appInfo.integrity_issues.length === 0
                                                ? 'text-emerald-600 dark:text-emerald-400'
                                                : ''
                                        "
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
                                {{ $t("about.technical_issues_detected") }}
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
                            class="text-sm text-gray-700 dark:text-emerald-200 flex items-center gap-3 bg-emerald-500/10 dark:bg-emerald-900/30 p-4 rounded-xl border border-emerald-500/20 dark:border-emerald-500/30"
                        >
                            <v-icon
                                icon="mdi-check-decagram"
                                size="20"
                                class="text-emerald-600 dark:text-emerald-400 shrink-0"
                            ></v-icon>
                            <span class="font-bold tracking-tight">{{ $t("about.no_integrity_violations") }}</span>
                        </div>
                    </div>

                    <!-- Advanced Tech Info -->
                    <div v-if="appInfo" class="about-section">
                        <div
                            class="text-xs font-black text-blue-500 uppercase tracking-[0.2em] mb-6 flex items-center gap-2"
                        >
                            <v-icon icon="mdi-server" size="14"></v-icon>
                            {{ $t("about.environment_information") }}
                        </div>
                        <div class="grid gap-8 sm:grid-cols-2 lg:grid-cols-3 text-sm min-w-0">
                            <div>
                                <div class="glass-label text-[10px]! mb-2 opacity-50">
                                    {{ $t("about.reticulum_config") }}
                                </div>
                                <div
                                    class="monospace-field bg-zinc-50! dark:bg-zinc-950! break-all text-[11px] p-3! rounded-xl border border-zinc-100 dark:border-zinc-800"
                                >
                                    {{ appInfo.reticulum_config_path || $t("about.path_unknown") }}
                                </div>
                                <button
                                    v-if="isElectron"
                                    type="button"
                                    class="secondary-chip mt-3 px-3! py-1! text-[10px]!"
                                    @click="showReticulumConfigFile"
                                >
                                    <v-icon icon="mdi-folder-open" start size="14"></v-icon>
                                    {{ $t("about.reveal_config_file") }}
                                </button>
                            </div>
                            <div>
                                <div class="glass-label text-[10px]! mb-2 opacity-50">
                                    {{ $t("about.database_path") }}
                                </div>
                                <div
                                    class="monospace-field bg-zinc-50! dark:bg-zinc-950! break-all text-[11px] p-3! rounded-xl border border-zinc-100 dark:border-zinc-800"
                                >
                                    {{ appInfo.database_path || $t("about.path_unknown") }}
                                </div>
                                <button
                                    v-if="isElectron"
                                    type="button"
                                    class="secondary-chip mt-3 px-3! py-1! text-[10px]!"
                                    @click="showDatabaseFile"
                                >
                                    <v-icon icon="mdi-database-search" start size="14"></v-icon>
                                    {{ $t("about.reveal_database_file") }}
                                </button>
                            </div>
                            <div
                                class="flex flex-col justify-center space-y-3 py-2 sm:py-3 border-t sm:border border-gray-200/60 dark:border-zinc-800/80 sm:rounded-xl sm:p-4 sm:bg-black/2 dark:sm:bg-white/2"
                            >
                                <div
                                    v-if="config"
                                    class="space-y-3 mb-2 pb-3 border-b border-zinc-100 dark:border-zinc-800"
                                >
                                    <div class="flex flex-col">
                                        <span class="text-[9px] font-black text-blue-500 uppercase tracking-wider">{{
                                            $t("about.identity_hash")
                                        }}</span>
                                        <span class="font-mono text-[10px] break-all opacity-70">{{
                                            config.identity_hash
                                        }}</span>
                                    </div>
                                    <div class="flex flex-col">
                                        <span class="text-[9px] font-black text-blue-500 uppercase tracking-wider">{{
                                            $t("about.lxmf_address")
                                        }}</span>
                                        <span class="font-mono text-[10px] break-all opacity-70">{{
                                            config.lxmf_address_hash
                                        }}</span>
                                    </div>
                                </div>
                                <div class="flex items-center justify-between">
                                    <span class="text-[10px] font-black text-blue-500 uppercase tracking-wider">{{
                                        $t("about.env_python")
                                    }}</span>
                                    <span class="font-mono text-xs font-bold"
                                        >v{{ appInfo.python_version || $t("about.path_unknown") }}</span
                                    >
                                </div>
                                <div class="flex items-center justify-between">
                                    <span class="text-[10px] font-black text-purple-500 uppercase tracking-wider">{{
                                        $t("about.env_lxmf")
                                    }}</span>
                                    <span class="font-mono text-xs font-bold"
                                        >v{{ appInfo.lxmf_version || $t("about.path_unknown") }}</span
                                    >
                                </div>
                                <div class="flex items-center justify-between">
                                    <span class="text-[10px] font-black text-indigo-500 uppercase tracking-wider">{{
                                        $t("about.env_rns")
                                    }}</span>
                                    <span class="font-mono text-xs font-bold"
                                        >v{{ appInfo.rns_version || $t("about.path_unknown") }}</span
                                    >
                                </div>
                                <div class="flex items-center justify-between">
                                    <span class="text-[10px] font-black text-emerald-500 uppercase tracking-wider">{{
                                        $t("about.env_platform")
                                    }}</span>
                                    <span class="font-mono text-xs font-bold">{{ environmentInfo.platform }}</span>
                                </div>
                                <div class="flex items-center justify-between">
                                    <span class="text-[10px] font-black text-amber-500 uppercase tracking-wider">{{
                                        $t("about.env_language")
                                    }}</span>
                                    <span class="font-mono text-xs font-bold">{{ environmentInfo.language }}</span>
                                </div>
                                <div class="flex items-center justify-between">
                                    <span class="text-[10px] font-black text-fuchsia-500 uppercase tracking-wider">{{
                                        $t("about.env_backend_url")
                                    }}</span>
                                    <span class="font-mono text-xs font-bold">{{ environmentInfo.backendUrl }}</span>
                                </div>
                                <div class="flex flex-col gap-1 pt-2 border-t border-zinc-100 dark:border-zinc-800">
                                    <span class="text-[10px] font-black text-slate-500 uppercase tracking-wider">{{
                                        $t("about.env_user_agent")
                                    }}</span>
                                    <span class="font-mono text-[10px] break-all opacity-70">{{
                                        environmentInfo.userAgent
                                    }}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Dependency Chain -->
                    <div v-if="appInfo" class="about-section">
                        <div
                            class="text-xs font-black text-blue-500 uppercase tracking-[0.2em] mb-8 flex items-center gap-2"
                        >
                            <v-icon icon="mdi-link-variant" size="14"></v-icon>
                            {{ $t("about.dependency_chain") }}
                        </div>
                        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 relative min-w-0">
                            <div class="flex flex-col space-y-8 min-w-0">
                                <div class="flex items-center gap-5">
                                    <div
                                        class="w-12 h-12 rounded-2xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20 shadow-xs"
                                    >
                                        <img
                                            src="../../public/favicons/favicon-512x512.png"
                                            class="w-7 h-7 object-contain"
                                        />
                                    </div>
                                    <div>
                                        <div class="text-sm font-black text-gray-900 dark:text-white">
                                            {{ $t("about.app_name") }}
                                        </div>
                                        <div class="text-xs font-mono font-bold text-gray-400">
                                            v{{ appInfo.version }}
                                        </div>
                                    </div>
                                </div>
                                <div
                                    class="flex items-center gap-5 pl-5 border-l-2 border-zinc-100 dark:border-zinc-800 ml-6 relative"
                                >
                                    <div
                                        class="absolute left-[-2px] top-0 bottom-0 w-[2px] bg-linear-to-b from-blue-500 to-emerald-500"
                                    ></div>
                                    <div
                                        class="w-12 h-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20 text-emerald-600 font-black text-[10px] tracking-tighter shadow-xs"
                                    >
                                        LXMFy
                                    </div>
                                    <div>
                                        <div class="text-sm font-black text-gray-900 dark:text-white leading-tight">
                                            {{ $t("about.dep_lxmfy_subtitle") }}
                                        </div>
                                        <div class="text-xs font-mono font-bold text-gray-400 mt-1">
                                            v{{ (appInfo.dependencies && appInfo.dependencies.lxmfy) || "unknown" }}
                                        </div>
                                    </div>
                                </div>
                                <div
                                    class="flex items-center gap-5 pl-5 border-l-2 border-zinc-100 dark:border-zinc-800 ml-6 relative"
                                >
                                    <div
                                        class="absolute left-[-2px] top-0 bottom-0 w-[2px] bg-linear-to-b from-emerald-500 to-purple-500"
                                    ></div>
                                    <div
                                        class="w-12 h-12 rounded-2xl bg-purple-500/10 flex items-center justify-center border border-purple-500/20 text-purple-600 font-black text-[10px] tracking-tighter shadow-xs"
                                    >
                                        LXMF
                                    </div>
                                    <div>
                                        <div class="text-sm font-black text-gray-900 dark:text-white leading-tight">
                                            {{ $t("about.dep_lxmf_subtitle") }}
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
                                        class="absolute left-[-2px] top-0 bottom-0 w-[2px] bg-linear-to-b from-purple-500 to-indigo-500"
                                    ></div>
                                    <div
                                        class="w-12 h-12 rounded-2xl bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 text-indigo-600 font-black text-[10px] tracking-tighter shadow-xs"
                                    >
                                        RNS
                                    </div>
                                    <div>
                                        <div class="text-sm font-black text-gray-900 dark:text-white leading-tight">
                                            {{ $t("about.dep_rns_subtitle") }}
                                        </div>
                                        <div class="flex flex-wrap items-center gap-2 mt-1 min-w-0">
                                            <div class="text-xs font-mono font-bold text-gray-400 shrink-0">
                                                v{{ appInfo.rns_version }}
                                            </div>
                                            <div
                                                :class="[
                                                    appInfo.is_connected_to_shared_instance
                                                        ? 'bg-blue-500/10 text-blue-500 border-blue-500/20'
                                                        : 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
                                                ]"
                                                class="text-[8px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded-sm border max-w-full wrap-break-word"
                                            >
                                                {{
                                                    appInfo.is_connected_to_shared_instance
                                                        ? $t("about.shared_instance_badge", {
                                                              address:
                                                                  appInfo.shared_instance_address ||
                                                                  $t("about.path_unknown"),
                                                          })
                                                        : $t("about.main_instance_badge")
                                                }}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="space-y-8 min-w-0">
                                <div
                                    class="py-4 sm:p-5 border-t border-gray-200/60 dark:border-zinc-800/80 sm:border sm:rounded-2xl sm:bg-black/2 dark:sm:bg-white/2 min-w-0"
                                >
                                    <div
                                        class="text-[10px] font-black text-gray-400 dark:text-zinc-600 uppercase tracking-[0.2em] mb-4"
                                    >
                                        {{ $t("about.core_runtime") }}
                                    </div>
                                    <div class="grid grid-cols-2 gap-x-6 gap-y-4">
                                        <div v-if="appInfo.lxst_version" class="flex flex-col">
                                            <span
                                                class="text-[9px] font-black text-blue-500/60 uppercase leading-none"
                                                >{{ $t("about.lxst_engine") }}</span
                                            >
                                            <span
                                                class="text-[11px] font-mono font-bold mt-1.5 opacity-90 tracking-tight"
                                                >v{{ appInfo.lxst_version }}</span
                                            >
                                        </div>
                                        <div v-if="electronVersion" class="flex flex-col">
                                            <span
                                                class="text-[9px] font-black text-blue-500/60 uppercase leading-none"
                                                >{{ $t("about.electron_runtime") }}</span
                                            >
                                            <span
                                                class="text-[11px] font-mono font-bold mt-1.5 opacity-90 tracking-tight"
                                                >v{{ electronVersion }}</span
                                            >
                                        </div>
                                        <div v-if="chromeVersion" class="flex flex-col">
                                            <span
                                                class="text-[9px] font-black text-blue-500/60 uppercase leading-none"
                                                >{{ $t("about.chrome_runtime") }}</span
                                            >
                                            <span
                                                class="text-[11px] font-mono font-bold mt-1.5 opacity-90 tracking-tight"
                                                >v{{ chromeVersion }}</span
                                            >
                                        </div>
                                        <div v-if="nodeVersion" class="flex flex-col">
                                            <span
                                                class="text-[9px] font-black text-blue-500/60 uppercase leading-none"
                                                >{{ $t("about.nodejs_runtime") }}</span
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
                                        {{ $t("about.backend_stack") }}
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
                    <div class="about-section">
                        <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between mb-8">
                            <div
                                class="text-xs font-black text-blue-500 uppercase tracking-[0.2em] flex items-center gap-2"
                            >
                                <v-icon icon="mdi-database-cog" size="14"></v-icon>
                                {{ $t("about.database_health_maintenance") }}
                            </div>
                            <div class="flex flex-wrap gap-2 w-full md:w-auto">
                                <button
                                    type="button"
                                    class="secondary-chip px-4! py-1.5! text-xs! min-h-[44px] sm:min-h-0"
                                    :disabled="databaseActionInProgress || healthLoading"
                                    @click="getDatabaseHealth(true)"
                                >
                                    <v-icon icon="mdi-refresh" start size="14"></v-icon>
                                    <span v-if="healthLoading">{{ $t("common.loading") }}</span>
                                    <span v-else>{{ $t("common.refresh") }}</span>
                                </button>
                                <button
                                    type="button"
                                    class="primary-chip px-4! py-1.5! text-xs!"
                                    :disabled="databaseActionInProgress"
                                    @click="vacuumDatabase"
                                >
                                    <v-icon icon="mdi-broom" start size="14"></v-icon> {{ $t("common.vacuum") }}
                                </button>
                                <button
                                    type="button"
                                    class="danger-chip px-4! py-1.5! text-xs!"
                                    :disabled="databaseActionInProgress"
                                    @click="runRecovery"
                                >
                                    <v-icon icon="mdi-medical-bag" start size="14"></v-icon>
                                    {{ $t("about.recovery") }}
                                </button>
                            </div>
                        </div>

                        <div v-if="databaseHealth" class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-6 lg:gap-8 mb-8">
                            <div
                                class="py-3 px-2 sm:p-4 border-b border-gray-200/60 dark:border-zinc-800/60 md:border md:rounded-xl"
                            >
                                <div
                                    class="text-[9px] font-black text-gray-400 dark:text-zinc-600 uppercase tracking-[0.2em] mb-2 leading-none"
                                >
                                    {{ $t("about.integrity") }}
                                </div>
                                <div
                                    :class="[databaseHealth.quick_check === 'ok' ? 'text-emerald-500' : 'text-red-500']"
                                    class="text-lg font-black uppercase tracking-tight"
                                >
                                    {{ databaseHealth.quick_check }}
                                </div>
                            </div>
                            <div
                                class="py-3 px-2 sm:p-4 border-b border-gray-200/60 dark:border-zinc-800/60 md:border md:rounded-xl"
                            >
                                <div
                                    class="text-[9px] font-black text-gray-400 dark:text-zinc-600 uppercase tracking-[0.2em] mb-2 leading-none"
                                >
                                    {{ $t("about.journal_short") }}
                                </div>
                                <div class="text-lg font-black uppercase text-blue-500 tracking-tight">
                                    {{ databaseHealth.journal_mode }}
                                </div>
                            </div>
                            <div
                                class="py-3 px-2 sm:p-4 border-b border-gray-200/60 dark:border-zinc-800/60 md:border md:rounded-xl"
                            >
                                <div
                                    class="text-[9px] font-black text-gray-400 dark:text-zinc-600 uppercase tracking-[0.2em] mb-2 leading-none"
                                >
                                    {{ $t("about.page_count_label") }}
                                </div>
                                <div class="text-lg font-black font-mono tracking-tight tabular-nums">
                                    {{ databaseHealth.page_count }}
                                </div>
                            </div>
                            <div
                                class="py-3 px-2 sm:p-4 border-b border-gray-200/60 dark:border-zinc-800/60 md:border md:rounded-xl"
                            >
                                <div
                                    class="text-[9px] font-black text-gray-400 dark:text-zinc-600 uppercase tracking-[0.2em] mb-2 leading-none"
                                >
                                    {{ $t("about.free_space") }}
                                </div>
                                <div class="text-lg font-black text-amber-500 tracking-tight tabular-nums">
                                    {{ formatBytes(databaseHealth.estimated_free_bytes) }}
                                </div>
                            </div>
                        </div>

                        <div class="border-t border-zinc-100 dark:border-zinc-800 pt-8 space-y-8">
                            <!-- Backups -->
                            <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                                <div class="space-y-1">
                                    <div
                                        class="font-black text-gray-900 dark:text-white text-sm tracking-tight flex items-center gap-2"
                                    >
                                        <v-icon icon="mdi-content-save-all" size="16" class="text-blue-500"></v-icon>
                                        {{ $t("about.database_backups_title") }}
                                    </div>
                                    <div class="text-xs text-gray-500">
                                        {{ $t("about.database_backups_desc") }}
                                    </div>
                                </div>
                                <button
                                    type="button"
                                    class="primary-chip px-5! py-2.5!"
                                    :disabled="backupInProgress"
                                    @click="backupDatabase"
                                >
                                    <v-icon icon="mdi-download" start></v-icon>
                                    <span v-if="backupInProgress">{{ $t("about.downloading") }}</span>
                                    <span v-else>{{ $t("about.download_backup") }}</span>
                                </button>
                            </div>

                            <!-- Snapshots -->
                            <div class="space-y-6">
                                <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                                    <div class="space-y-1">
                                        <div
                                            class="font-black text-gray-900 dark:text-white text-sm tracking-tight flex items-center gap-2"
                                        >
                                            <v-icon icon="mdi-camera" size="16" class="text-purple-500"></v-icon>
                                            {{ $t("about.local_snapshots_title") }}
                                        </div>
                                        <div class="text-xs text-gray-500">
                                            {{ $t("about.local_snapshots_desc") }}
                                        </div>
                                    </div>
                                    <div class="flex gap-2 w-full md:w-auto">
                                        <input
                                            v-model="snapshotName"
                                            type="text"
                                            :placeholder="$t('about.snapshot_placeholder')"
                                            class="bg-zinc-50 dark:bg-zinc-900 px-4 py-2 rounded-xl text-sm border border-zinc-100 dark:border-zinc-800 focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 flex-1 md:min-w-[200px]"
                                        />
                                        <button
                                            type="button"
                                            class="primary-chip px-6!"
                                            :disabled="snapshotInProgress"
                                            @click="createSnapshot"
                                        >
                                            <span v-if="snapshotInProgress">{{ $t("about.creating") }}</span>
                                            <span v-else>{{ $t("about.snapshot_create") }}</span>
                                        </button>
                                    </div>
                                </div>

                                <div v-if="snapshots && snapshots.length > 0" class="space-y-4">
                                    <div class="grid gap-3 sm:grid-cols-2">
                                        <div
                                            v-for="snapshot in snapshots"
                                            :key="snapshot.path"
                                            class="flex items-center justify-between gap-2 py-3 sm:p-4 border-b border-gray-200/60 dark:border-zinc-800/80 last:border-0 sm:border sm:rounded-lg sm:bg-black/2 dark:sm:bg-white/2 transition-colors"
                                        >
                                            <div class="flex flex-col min-w-0">
                                                <span
                                                    class="font-black text-gray-900 dark:text-white text-xs truncate"
                                                    >{{ snapshot.name }}</span
                                                >
                                                <span class="text-[10px] font-bold text-gray-400 mt-1 tabular-nums"
                                                    >{{ formatBytes(snapshot.size) }} •
                                                    {{ Utils.formatTimeAgo(snapshot.created_at) }}</span
                                                >
                                            </div>
                                            <div
                                                class="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity"
                                            >
                                                <button
                                                    type="button"
                                                    class="primary-chip px-3! py-1! text-[10px]!"
                                                    @click="downloadSnapshot(snapshot.name)"
                                                >
                                                    <v-icon icon="mdi-download" size="12" start></v-icon>
                                                    {{ $t("about.snapshot_download") }}
                                                </button>
                                                <button
                                                    type="button"
                                                    class="secondary-chip px-3! py-1! text-[10px]!"
                                                    @click="restoreFromSnapshot(snapshot.path)"
                                                >
                                                    {{ $t("about.snapshot_restore") }}
                                                </button>
                                                <button
                                                    type="button"
                                                    class="danger-chip px-3! py-1! text-[10px]!"
                                                    @click="deleteSnapshot(snapshot.name)"
                                                >
                                                    <v-icon icon="mdi-delete" size="12"></v-icon>
                                                </button>
                                            </div>
                                        </div>
                                    </div>

                                    <!-- Snapshots Pagination -->
                                    <div
                                        v-if="snapshotsTotal > snapshotsLimit"
                                        class="flex items-center justify-between px-2"
                                    >
                                        <div class="text-[10px] font-black text-gray-400 uppercase tracking-widest">
                                            {{
                                                $t("about.pagination_page_of", {
                                                    current: Math.floor(snapshotsOffset / snapshotsLimit) + 1,
                                                    total: Math.ceil(snapshotsTotal / snapshotsLimit),
                                                })
                                            }}
                                        </div>
                                        <div class="flex gap-2">
                                            <button
                                                class="secondary-chip p-1! disabled:opacity-30"
                                                :disabled="snapshotsOffset === 0"
                                                @click="prevSnapshots"
                                            >
                                                <v-icon icon="mdi-chevron-left"></v-icon>
                                            </button>
                                            <button
                                                class="secondary-chip p-1! disabled:opacity-30"
                                                :disabled="snapshotsOffset + snapshotsLimit >= snapshotsTotal"
                                                @click="nextSnapshots"
                                            >
                                                <v-icon icon="mdi-chevron-right"></v-icon>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Auto Backups -->
                            <div v-if="autoBackups && autoBackups.length > 0" class="space-y-6">
                                <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                                    <div class="space-y-1">
                                        <div
                                            class="font-black text-gray-900 dark:text-white text-sm tracking-tight flex items-center gap-2"
                                        >
                                            <v-icon icon="mdi-history" size="16" class="text-blue-500"></v-icon>
                                            {{ $t("about.automatic_backups_title") }}
                                        </div>
                                        <div class="text-xs text-gray-500">
                                            {{ $t("about.automatic_backups_desc") }}
                                        </div>
                                    </div>
                                </div>

                                <div v-if="autoBackups && autoBackups.length > 0" class="space-y-4">
                                    <div class="grid gap-3 sm:grid-cols-2">
                                        <div
                                            v-for="backup in autoBackups"
                                            :key="backup.path"
                                            class="flex items-center justify-between gap-2 py-3 sm:p-4 border-b border-gray-200/60 dark:border-zinc-800/80 last:border-0 sm:border sm:rounded-lg sm:bg-black/2 dark:sm:bg-white/2 transition-colors"
                                        >
                                            <div class="flex flex-col min-w-0">
                                                <span
                                                    class="font-black text-gray-900 dark:text-white text-xs truncate"
                                                    >{{ backup.name }}</span
                                                >
                                                <span class="text-[10px] font-bold text-gray-400 mt-1 tabular-nums"
                                                    >{{ formatBytes(backup.size) }} •
                                                    {{ Utils.formatTimeAgo(backup.created_at) }}</span
                                                >
                                            </div>
                                            <div
                                                class="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity"
                                            >
                                                <button
                                                    type="button"
                                                    class="primary-chip px-3! py-1! text-[10px]!"
                                                    @click="downloadBackupFile(backup.name)"
                                                >
                                                    <v-icon icon="mdi-download" size="12" start></v-icon>
                                                    {{ $t("about.snapshot_download") }}
                                                </button>
                                                <button
                                                    type="button"
                                                    class="secondary-chip px-3! py-1! text-[10px]!"
                                                    @click="restoreFromSnapshot(backup.path)"
                                                >
                                                    {{ $t("about.snapshot_restore") }}
                                                </button>
                                                <button
                                                    type="button"
                                                    class="danger-chip px-3! py-1! text-[10px]!"
                                                    @click="deleteBackup(backup.name)"
                                                >
                                                    <v-icon icon="mdi-delete" size="12"></v-icon>
                                                </button>
                                            </div>
                                        </div>
                                    </div>

                                    <!-- Backups Pagination -->
                                    <div
                                        v-if="autoBackupsTotal > autoBackupsLimit"
                                        class="flex items-center justify-between px-2"
                                    >
                                        <div class="text-[10px] font-black text-gray-400 uppercase tracking-widest">
                                            {{
                                                $t("about.pagination_page_of", {
                                                    current: Math.floor(autoBackupsOffset / autoBackupsLimit) + 1,
                                                    total: Math.ceil(autoBackupsTotal / autoBackupsLimit),
                                                })
                                            }}
                                        </div>
                                        <div class="flex gap-2">
                                            <button
                                                class="secondary-chip p-1! disabled:opacity-30"
                                                :disabled="autoBackupsOffset === 0"
                                                @click="prevBackups"
                                            >
                                                <v-icon icon="mdi-chevron-left"></v-icon>
                                            </button>
                                            <button
                                                class="secondary-chip p-1! disabled:opacity-30"
                                                :disabled="autoBackupsOffset + autoBackupsLimit >= autoBackupsTotal"
                                                @click="nextBackups"
                                            >
                                                <v-icon icon="mdi-chevron-right"></v-icon>
                                            </button>
                                        </div>
                                    </div>
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
            Utils,
            appInfo: {
                version: "unknown",
            },
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
            reloadingRns: false,
            snapshotName: "",
            snapshots: [],
            snapshotsTotal: 0,
            snapshotsOffset: 0,
            snapshotsLimit: 3,
            snapshotInProgress: false,
            snapshotMessage: "",
            snapshotError: "",
            autoBackups: [],
            autoBackupsTotal: 0,
            autoBackupsOffset: 0,
            autoBackupsLimit: 3,
            electronVersion: null,
            chromeVersion: null,
            nodeVersion: null,
            showContactDev: false,
            showDonate: false,
            moneroDonateAddress:
                "83SUg6mmkkVGwCycckLEgRfdmXNm7H9XtVjbGXp5kko71N6pTefYURJeS7WdEGHrz2aagmt4nF3dWg6mHcYs6yu4EokwhTh",
        };
    },
    computed: {
        isElectron() {
            return ElectronUtils.isElectron();
        },
        formattedUiBuildDate() {
            try {
                const raw = typeof __APP_BUILD_TIME__ !== "undefined" ? __APP_BUILD_TIME__ : "";
                if (!raw) {
                    return "";
                }
                const d = new Date(raw);
                if (Number.isNaN(d.getTime())) {
                    return raw;
                }
                return d.toLocaleDateString(undefined, {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                });
            } catch {
                return "";
            }
        },
        environmentInfo() {
            const ua = typeof navigator !== "undefined" ? navigator.userAgent || "" : "";
            let platform = typeof navigator !== "undefined" && navigator.platform ? navigator.platform : "";
            if (
                !platform &&
                typeof navigator !== "undefined" &&
                navigator.userAgentData &&
                navigator.userAgentData.platform
            ) {
                platform = navigator.userAgentData.platform;
            }
            if (!platform && /Android/i.test(ua)) {
                platform = "Android";
            }
            if (!platform && this.appInfo && this.appInfo.host_platform) {
                platform = this.appInfo.host_platform;
            }
            if (!platform) {
                platform = "unknown";
            }
            const language =
                typeof navigator !== "undefined" && navigator.language
                    ? navigator.language
                    : typeof navigator !== "undefined" && navigator.languages && navigator.languages[0]
                      ? navigator.languages[0]
                      : "unknown";
            return {
                platform,
                language,
                userAgent: ua || "unknown",
                backendUrl: typeof window !== "undefined" && window.location ? window.location.origin : "unknown",
            };
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
                const response = await window.api.get("/api/v1/database/snapshots", {
                    params: {
                        limit: this.snapshotsLimit,
                        offset: this.snapshotsOffset,
                    },
                });
                this.snapshots = response.data.snapshots;
                this.snapshotsTotal = response.data.total;
            } catch (e) {
                console.log("Failed to list snapshots", e);
            }
        },
        async listAutoBackups() {
            try {
                const response = await window.api.get("/api/v1/database/backups", {
                    params: {
                        limit: this.autoBackupsLimit,
                        offset: this.autoBackupsOffset,
                    },
                });
                this.autoBackups = response.data.backups;
                this.autoBackupsTotal = response.data.total;
            } catch {
                console.log("Failed to list auto-backups");
            }
        },
        async downloadSnapshot(filename) {
            try {
                const response = await window.api.get(`/api/v1/database/snapshots/${filename}/download`, {
                    responseType: "blob",
                });
                const url = window.URL.createObjectURL(new Blob([response.data]));
                const link = document.createElement("a");
                link.href = url;
                link.setAttribute("download", filename);
                document.body.appendChild(link);
                link.click();
                link.remove();
                window.URL.revokeObjectURL(url);
                ToastUtils.success(this.$t("about.snapshot_downloaded"));
            } catch {
                ToastUtils.error(this.$t("about.snapshot_download_failed"));
            }
        },
        async downloadBackupFile(filename) {
            try {
                const response = await window.api.get(`/api/v1/database/backups/${filename}/download`, {
                    responseType: "blob",
                });
                const url = window.URL.createObjectURL(new Blob([response.data]));
                const link = document.createElement("a");
                link.href = url;
                link.setAttribute("download", filename);
                document.body.appendChild(link);
                link.click();
                link.remove();
                window.URL.revokeObjectURL(url);
                ToastUtils.success(this.$t("about.backup_downloaded"));
            } catch {
                ToastUtils.error(this.$t("about.backup_download_failed"));
            }
        },
        async deleteSnapshot(filename) {
            if (!(await DialogUtils.confirm(this.$t("about.delete_snapshot_confirm")))) return;
            try {
                await window.api.delete(`/api/v1/database/snapshots/${filename}`);
                ToastUtils.success(this.$t("about.snapshot_deleted"));
                await this.listSnapshots();
            } catch {
                ToastUtils.error(this.$t("about.failed_delete_snapshot"));
            }
        },
        async deleteBackup(filename) {
            if (!(await DialogUtils.confirm(this.$t("about.delete_backup_confirm")))) return;
            try {
                await window.api.delete(`/api/v1/database/backups/${filename}`);
                ToastUtils.success(this.$t("about.backup_deleted"));
                await this.listAutoBackups();
            } catch {
                ToastUtils.error(this.$t("about.failed_delete_backup"));
            }
        },
        async nextSnapshots() {
            if (this.snapshotsOffset + this.snapshotsLimit < this.snapshotsTotal) {
                this.snapshotsOffset += this.snapshotsLimit;
                await this.listSnapshots();
            }
        },
        async prevSnapshots() {
            if (this.snapshotsOffset > 0) {
                this.snapshotsOffset = Math.max(0, this.snapshotsOffset - this.snapshotsLimit);
                await this.listSnapshots();
            }
        },
        async nextBackups() {
            if (this.autoBackupsOffset + this.autoBackupsLimit < this.autoBackupsTotal) {
                this.autoBackupsOffset += this.autoBackupsLimit;
                await this.listAutoBackups();
            }
        },
        async prevBackups() {
            if (this.autoBackupsOffset > 0) {
                this.autoBackupsOffset = Math.max(0, this.autoBackupsOffset - this.autoBackupsLimit);
                await this.listAutoBackups();
            }
        },
        async createSnapshot() {
            if (this.snapshotInProgress) return;
            this.snapshotInProgress = true;
            this.snapshotMessage = "";
            this.snapshotError = "";
            try {
                await window.api.post("/api/v1/database/snapshot", {
                    name: this.snapshotName || `snapshot-${Math.floor(Date.now() / 1000)}`,
                });
                this.snapshotMessage = "Snapshot created successfully";
                this.snapshotName = "";
                await this.listSnapshots();
            } catch {
                this.snapshotError = "Failed to create snapshot";
            } finally {
                this.snapshotInProgress = false;
            }
        },
        async restoreFromSnapshot(path) {
            if (!(await DialogUtils.confirm(this.$t("about.restore_snapshot_confirm")))) {
                return;
            }
            try {
                const response = await window.api.post("/api/v1/database/restore", { path });
                if (response.data.status === "success") {
                    ToastUtils.success(this.$t("about.database_restored"));
                    if (this.isElectron) {
                        setTimeout(() => ElectronUtils.relaunch(), 2000);
                    }
                }
            } catch {
                ToastUtils.error(this.$t("about.failed_restore_snapshot"));
            }
        },
        async getAppInfo() {
            try {
                const response = await window.api.get("/api/v1/app/info");
                this.appInfo = {
                    ...(this.appInfo || {}),
                    ...(response?.data?.app_info || {}),
                };

                if (this.isElectron) {
                    this.electronMemoryUsage = await ElectronUtils.getMemoryUsage();
                    this.electronVersion = window.electron.electronVersion();
                    this.chromeVersion = window.electron.chromeVersion();
                    this.nodeVersion = window.electron.nodeVersion();
                }
            } catch (e) {
                console.log(e);
            }
        },
        async acknowledgeIntegrity() {
            if (await DialogUtils.confirm(this.$t("about.integrity_acknowledge_confirm"))) {
                try {
                    await window.api.post("/api/v1/app/integrity/acknowledge");
                    ToastUtils.success(this.$t("about.integrity_acknowledged"));
                    await this.getAppInfo();
                } catch {
                    ToastUtils.error(this.$t("about.failed_acknowledge_integrity"));
                }
            }
        },
        async getDatabaseHealth(showMessage = false) {
            this.healthLoading = true;
            try {
                const response = await window.api.get("/api/v1/database/health");
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
                const response = await window.api.post("/api/v1/database/vacuum");
                if (response.data.database?.health) {
                    this.databaseHealth = response.data.database.health;
                }
                const msg = response.data.message || this.$t("about.vacuum_complete");
                this.databaseActionMessage = msg;
                ToastUtils.success(this.$t("about.vacuum_complete"));
            } catch (e) {
                this.databaseActionError = this.$t("about.vacuum_failed");
                const detail = e?.response?.data?.message;
                ToastUtils.error(detail || this.$t("about.vacuum_failed"));
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
                const response = await window.api.get("/api/v1/database/backup/download", {
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
                const response = await window.api.post("/api/v1/database/restore", formData, {
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
            if (!(await DialogUtils.confirm(this.$t("about.recovery_confirm")))) {
                return;
            }
            this.databaseActionInProgress = true;
            this.databaseActionMessage = "";
            this.databaseActionError = "";
            try {
                const response = await window.api.post("/api/v1/database/recover");
                if (response.data.database?.health) {
                    this.databaseHealth = response.data.database.health;
                }
                this.databaseRecoveryActions = response.data.database?.actions || [];
                const msg = response.data.message || this.$t("about.recovery_complete");
                this.databaseActionMessage = msg;
                ToastUtils.success(this.$t("about.recovery_complete"));
            } catch (e) {
                this.databaseActionError = this.$t("about.recovery_failed");
                const detail = e?.response?.data?.message;
                ToastUtils.error(detail || this.$t("about.recovery_failed"));
                console.log(e);
            } finally {
                this.databaseActionInProgress = false;
            }
        },
        async getConfig() {
            try {
                const response = await window.api.get("/api/v1/config");
                this.config = response.data.config;
            } catch (e) {
                // do nothing if failed to load config
                console.log(e);
            }
        },
        async copyValue(value, labelKey) {
            if (!value) {
                return;
            }
            const label = this.$t(labelKey);
            try {
                await navigator.clipboard.writeText(value);
                ToastUtils.success(this.$t("about.copied_label_to_clipboard", { label }));
            } catch {
                ToastUtils.error(this.$t("about.failed_to_copy_label", { label }));
            }
        },
        relaunch() {
            ElectronUtils.relaunch();
        },
        async restartRns() {
            if (this.reloadingRns) return;
            try {
                this.reloadingRns = true;
                ToastUtils.loading(this.$t("app.reloading_rns"), 0, "about-rns-reload");
                const response = await window.api.post("/api/v1/reticulum/reload");
                ToastUtils.success(response?.data?.message || this.$t("app.reloaded_rns"));
                await this.getAppInfo();
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("settings.failed_reload_reticulum"));
            } finally {
                ToastUtils.dismiss("about-rns-reload");
                this.reloadingRns = false;
            }
        },
        async shutdown() {
            if (await DialogUtils.confirm(this.$t("about.shutdown_confirm"))) {
                try {
                    // try to notify backend first
                    await window.api.post("/api/v1/app/shutdown");
                } catch {
                    // ignore errors if backend is already stopping
                }

                if (this.isElectron) {
                    ElectronUtils.shutdown();
                } else if (typeof window !== "undefined" && window.MeshChatXAndroid?.exitApp) {
                    try {
                        window.MeshChatXAndroid.exitApp();
                    } catch {
                        ToastUtils.success(this.$t("about.shutdown_sent"));
                    }
                } else {
                    ToastUtils.success(this.$t("about.shutdown_sent"));
                }
            }
        },
        showChangelog() {
            GlobalEmitter.emit("show-changelog");
        },
        showTutorial() {
            GlobalEmitter.emit("show-tutorial");
        },
        async showReticulumConfigFile() {
            const reticulumConfigPath = this.appInfo.reticulum_config_path;
            if (!reticulumConfigPath) {
                return;
            }
            const ok = await ElectronUtils.revealPathInFolderOrCopy(reticulumConfigPath, () =>
                ToastUtils.success(this.$t("common.copied"))
            );
            if (!ok) {
                DialogUtils.alert(reticulumConfigPath);
            }
        },
        async showDatabaseFile() {
            const databasePath = this.appInfo.database_path;
            if (!databasePath) {
                return;
            }
            const ok = await ElectronUtils.revealPathInFolderOrCopy(databasePath, () =>
                ToastUtils.success(this.$t("common.copied"))
            );
            if (!ok) {
                DialogUtils.alert(databasePath);
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
                ? "inline-flex items-center gap-1 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300 px-3 py-1 text-xs font-semibold"
                : "inline-flex items-center gap-1 rounded-full bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300 px-3 py-1 text-xs font-semibold";
        },
    },
};
</script>

<style scoped>
@reference "../../style.css";
.about-section {
    @apply w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-6 sm:py-8 last:border-0;
}
:deep(.about-btn:focus-visible) {
    outline: 2px solid rgba(59, 130, 246, 0.35);
    outline-offset: 2px;
}
.about-action-btn {
    @apply min-w-0 min-h-[40px] justify-center whitespace-nowrap;
}
</style>
