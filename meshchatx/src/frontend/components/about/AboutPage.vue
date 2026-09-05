<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
        <div
            class="flex-1 overflow-y-auto overflow-x-hidden w-full min-w-0 px-3 sm:px-5 md:px-5 lg:px-8 py-4 sm:py-6 text-sem-fg"
        >
            <div class="space-y-0 w-full max-w-4xl mx-auto pb-16 sm:pb-24 min-w-0">
                <div v-if="appInfo" class="about-section">
                    <div class="flex flex-col gap-8 lg:flex-row lg:items-center">
                        <!-- Logo & Title -->
                        <div class="flex items-center gap-6">
                            <img :src="logoUrl" class="h-20 w-20 shrink-0 object-contain" alt="" />
                            <div class="space-y-1">
                                <div class="text-4xl font-black text-sem-fg leading-none tracking-tight">
                                    {{ $t("about.app_name") }}
                                </div>
                                <div
                                    class="flex flex-col gap-0.5 sm:flex-row sm:flex-wrap sm:items-baseline sm:gap-x-3 sm:gap-y-0"
                                >
                                    <div class="flex flex-wrap items-center gap-2">
                                        <div
                                            class="text-sm font-black uppercase tracking-[0.2em] text-blue-500 opacity-80"
                                        >
                                            {{ $t("about.version", { version: aboutDisplayVersion }) }}
                                        </div>
                                        <span
                                            v-if="aboutChannelLabel"
                                            class="inline-flex h-5 items-center rounded-xs px-2 text-[10px] font-black uppercase tracking-tighter"
                                            :class="aboutChannelBadgeClass"
                                            data-testid="about-channel-badge"
                                        >
                                            {{ aboutChannelLabel }}
                                        </span>
                                    </div>
                                    <div
                                        v-if="appInfo.git_commit_short || appInfo.git_commit"
                                        class="text-xs font-medium normal-case tracking-normal font-mono text-sem-fg-muted"
                                        :title="appInfo.git_commit || appInfo.git_commit_short"
                                    >
                                        {{
                                            $t("about.git_commit", {
                                                commit: appInfo.git_commit_short || appInfo.git_commit,
                                            })
                                        }}
                                    </div>
                                    <div
                                        v-if="formattedUiBuildDate"
                                        class="text-xs font-medium normal-case tracking-normal text-sem-fg-muted"
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
                                <MaterialDesignIcon icon-name="help-circle" class="size-5 mr-2 shrink-0" />
                                <span class="truncate">{{ $t("app.tutorial_title") }}</span>
                            </button>
                            <button type="button" class="about-action-btn secondary-chip" @click="showChangelog">
                                <MaterialDesignIcon icon-name="history" class="size-5 mr-2 shrink-0" />
                                <span class="truncate">{{ $t("app.changelog_title") }}</span>
                            </button>
                            <router-link
                                :to="{ name: 'licenses' }"
                                class="about-action-btn secondary-chip inline-flex items-center no-underline"
                            >
                                <MaterialDesignIcon icon-name="license" class="size-5 mr-2 shrink-0" />
                                <span class="truncate">{{ $t("about.third_party_licenses") }}</span>
                            </router-link>
                            <button
                                v-if="isElectron"
                                type="button"
                                class="about-action-btn primary-chip"
                                @click="relaunch"
                            >
                                <MaterialDesignIcon icon-name="restart" class="size-5 mr-2 shrink-0" />
                                <span class="truncate">{{ $t("common.restart_app") }}</span>
                            </button>
                            <button
                                type="button"
                                class="about-action-btn secondary-chip"
                                :disabled="reloadingRns"
                                @click="restartRns"
                            >
                                <MaterialDesignIcon icon-name="restart-alert" class="size-5 mr-2 shrink-0" />
                                <span class="truncate">{{
                                    reloadingRns ? $t("app.reloading_rns") : $t("app.restart_rns")
                                }}</span>
                            </button>
                            <button type="button" class="about-action-btn danger-chip" @click="shutdown">
                                <MaterialDesignIcon icon-name="power" class="size-5 mr-2 shrink-0" />
                                <span class="truncate">{{ $t("common.shutdown") }}</span>
                            </button>
                        </div>
                    </div>

                    <div
                        v-if="aboutShowChannelPromptDetails"
                        class="mt-8 rounded-xl border border-sem-border bg-sem-surface px-4 py-4 space-y-4"
                        data-testid="about-channel-prompt"
                    >
                        <p v-if="aboutChannelNotes" class="text-sm text-sem-fg">{{ aboutChannelNotes }}</p>
                        <div v-if="aboutFocusAreas.length" class="space-y-2">
                            <div class="text-xs font-semibold uppercase tracking-wide text-sem-fg">
                                {{ $t("about.channel_focus_title") }}
                            </div>
                            <ul class="list-disc space-y-1 pl-5 text-sm text-sem-fg-muted">
                                <li v-for="(area, idx) in aboutFocusAreas" :key="`about-focus-${idx}`">
                                    {{ area }}
                                </li>
                            </ul>
                        </div>
                        <div class="space-y-2">
                            <div class="text-xs font-semibold uppercase tracking-wide text-sem-fg">
                                {{ $t("about.channel_bug_report_title") }}
                            </div>
                            <ol class="list-decimal space-y-1 pl-5 text-sm text-sem-fg-muted">
                                <li v-for="(step, idx) in aboutBugReportSteps" :key="`about-step-${idx}`">
                                    {{ step }}
                                </li>
                            </ol>
                            <p
                                v-if="aboutBugReportTarget.value"
                                class="break-all font-mono text-xs text-sem-fg-secondary"
                            >
                                <span v-if="aboutBugReportTarget.kind === 'lxmf'">
                                    {{ $t("channel_prompt.lxmf_label") }}
                                </span>
                                {{ aboutBugReportTarget.value }}
                            </p>
                            <button
                                v-if="aboutBugReportTarget.value"
                                type="button"
                                class="about-action-btn secondary-chip"
                                @click="onAboutBugReportAction"
                            >
                                {{
                                    aboutBugReportTarget.kind === "lxmf"
                                        ? $t("channel_prompt.copy_lxmf")
                                        : $t("channel_prompt.copy_url")
                                }}
                            </button>
                        </div>
                    </div>

                    <div class="mt-10 pt-8 border-t border-sem-border flex flex-col gap-6">
                        <div class="text-sem-fg-muted max-w-xl text-lg leading-relaxed">
                            {{ $t("about.tagline_lead") }}
                            <a
                                href="https://reticulum.network"
                                target="_blank"
                                class="text-blue-500 font-black hover:underline decoration-2 underline-offset-4"
                                >{{ $t("about.tagline_link") }}</a
                            >{{ $t("about.tagline_after") }}
                        </div>

                        <div class="mt-6 pt-6 border-t border-gray-200/70 dark:border-zinc-800/80">
                            <button
                                type="button"
                                class="about-action-btn secondary-chip w-full justify-between text-left"
                                :aria-expanded="showContactSupport"
                                @click="showContactSupport = !showContactSupport"
                            >
                                <div class="flex items-center gap-3 min-w-0">
                                    <span
                                        class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-sem-surface-muted text-sem-fg-muted"
                                    >
                                        <MaterialDesignIcon
                                            icon-name="card-account-details-outline"
                                            class="size-[22px]"
                                        />
                                    </span>
                                    <span class="text-xs font-semibold uppercase tracking-wide text-sem-fg truncate">
                                        {{ $t("about.contact_support_title") }}
                                    </span>
                                </div>
                                <MaterialDesignIcon
                                    :icon-name="showContactSupport ? 'chevron-up' : 'chevron-down'"
                                    class="size-[22px] shrink-0 text-sem-fg-muted group-hover:text-gray-700 dark:group-hover:text-zinc-200 transition-colors"
                                />
                            </button>

                            <transition name="fade">
                                <div v-if="showContactSupport" class="mt-6 flex flex-col gap-6">
                                    <div class="flex flex-col gap-3">
                                        <div
                                            class="text-xs font-semibold text-sem-fg-muted uppercase tracking-wide flex items-center gap-2"
                                        >
                                            <MaterialDesignIcon icon-name="account-circle-outline" class="size-4" />
                                            {{ $t("about.contact_developer") }}
                                        </div>
                                        <div class="flex flex-col gap-2">
                                            <div
                                                class="flex items-center justify-between gap-2 px-3 py-2 rounded-xl bg-sem-surface-muted/40 border border-sem-border"
                                            >
                                                <router-link
                                                    :to="{
                                                        name: 'messages',
                                                        params: { destinationHash: developerLxmfPrimary },
                                                    }"
                                                    class="flex-1 min-w-0 text-sm font-mono text-sem-fg-muted hover:text-blue-600 dark:hover:text-blue-400 break-all leading-snug text-left"
                                                    :title="$t('about.contact_open_messages')"
                                                >
                                                    {{ developerLxmfPrimary }}
                                                </router-link>
                                                <button
                                                    type="button"
                                                    class="shrink-0 rounded-lg p-1.5 text-gray-500 hover:text-blue-600 text-sem-fg-muted dark:hover:text-blue-400 hover:bg-sem-surface-muted transition-colors"
                                                    :aria-label="$t('about.contact_copy_address')"
                                                    @click="
                                                        copyValue(developerLxmfPrimary, 'about.contact_lxmf_address')
                                                    "
                                                >
                                                    <MaterialDesignIcon icon-name="content-copy" class="size-4" />
                                                </button>
                                            </div>
                                            <div
                                                class="flex items-center justify-between gap-2 px-3 py-2 rounded-xl bg-sem-surface-muted/40 border border-sem-border"
                                            >
                                                <router-link
                                                    :to="{
                                                        name: 'messages',
                                                        params: { destinationHash: developerLxmfAlternate },
                                                    }"
                                                    class="flex-1 min-w-0 text-sm font-mono text-sem-fg-muted hover:text-blue-600 dark:hover:text-blue-400 break-all leading-snug text-left"
                                                    :title="$t('about.contact_open_messages')"
                                                >
                                                    {{ developerLxmfAlternate }}
                                                </router-link>
                                                <button
                                                    type="button"
                                                    class="shrink-0 rounded-lg p-1.5 text-gray-500 hover:text-blue-600 text-sem-fg-muted dark:hover:text-blue-400 hover:bg-sem-surface-muted transition-colors"
                                                    :aria-label="$t('about.contact_copy_address')"
                                                    @click="
                                                        copyValue(developerLxmfAlternate, 'about.contact_alternate')
                                                    "
                                                >
                                                    <MaterialDesignIcon icon-name="content-copy" class="size-4" />
                                                </button>
                                            </div>
                                        </div>
                                        <div
                                            class="text-xs text-sem-fg-muted bg-sem-surface-muted/40 p-3 rounded-xl border border-sem-border flex items-start gap-2"
                                        >
                                            <MaterialDesignIcon
                                                icon-name="information-outline"
                                                class="size-4 shrink-0 mt-0.5"
                                            />
                                            <span>{{ $t("about.contact_propagation_hint") }}</span>
                                        </div>
                                    </div>

                                    <div class="border-t border-sem-border/90"></div>

                                    <div class="flex flex-col gap-3">
                                        <div
                                            class="text-xs font-semibold text-sem-fg-muted uppercase tracking-wide flex items-center gap-2"
                                        >
                                            <MaterialDesignIcon icon-name="hand-heart" class="size-4" />
                                            {{ $t("about.donate_label") }}
                                        </div>
                                        <div>
                                            <div
                                                class="text-xs font-semibold text-sem-fg-muted uppercase tracking-wide mb-1.5"
                                            >
                                                {{ $t("about.donate_monero_label") }}
                                            </div>
                                            <div
                                                class="flex items-center justify-between gap-2 px-3 py-2 rounded-xl bg-sem-surface-muted/40 border border-sem-border"
                                            >
                                                <span
                                                    class="flex-1 min-w-0 text-sm font-mono text-sem-fg-muted break-all leading-snug select-all"
                                                    >{{ moneroDonateAddress }}</span
                                                >
                                                <button
                                                    type="button"
                                                    class="shrink-0 rounded-lg p-1.5 text-gray-500 hover:text-blue-600 text-sem-fg-muted dark:hover:text-blue-400 hover:bg-sem-surface-muted transition-colors"
                                                    :aria-label="$t('about.donate_copy_monero')"
                                                    @click="copyValue(moneroDonateAddress, 'about.donate_monero_label')"
                                                >
                                                    <MaterialDesignIcon icon-name="content-copy" class="size-4" />
                                                </button>
                                            </div>
                                        </div>

                                        <div class="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                                            <a
                                                href="https://ko-fi.com/quad4"
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                class="inline-flex flex-1 items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-sem-border bg-sem-surface-muted/40 hover:bg-sem-surface-muted text-sem-fg text-xs font-semibold transition-colors"
                                            >
                                                <MaterialDesignIcon
                                                    icon-name="coffee"
                                                    class="size-[18px] text-sem-fg-muted"
                                                />
                                                {{ $t("about.donate_kofi") }}
                                            </a>
                                            <a
                                                href="https://buymeacoffee.com/quad4"
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                class="inline-flex flex-1 items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-sem-border bg-sem-surface-muted/40 hover:bg-sem-surface-muted text-sem-fg text-xs font-semibold transition-colors"
                                            >
                                                <MaterialDesignIcon
                                                    icon-name="cup"
                                                    class="size-[18px] text-sem-fg-muted"
                                                />
                                                {{ $t("about.donate_buymeacoffee") }}
                                            </a>
                                        </div>
                                    </div>
                                </div>
                            </transition>
                        </div>

                        <div class="flex items-center gap-6 shrink-0">
                            <div class="text-right">
                                <div
                                    class="text-[10px] font-black text-sem-fg-muted uppercase tracking-[0.2em] leading-none mb-1"
                                >
                                    {{ $t("about.database_size") }}
                                </div>
                                <div class="text-2xl font-black text-sem-fg tabular-nums">
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
                        <div
                            class="text-xs font-black text-blue-500 uppercase tracking-[0.2em] flex items-center gap-2 mb-6"
                        >
                            <MaterialDesignIcon icon-name="shield-search" class="size-3.5" />
                            {{ $t("about.security_integrity") }}
                        </div>

                        <div class="mb-6 pb-6 border-b border-gray-200/60 dark:border-zinc-800/80 space-y-4">
                            <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                                <div>
                                    <div class="text-[10px] font-black text-sem-fg uppercase tracking-[0.2em] mb-2">
                                        {{ $t("about.integrity_monitoring_title") }}
                                    </div>
                                    <p class="text-[11px] leading-relaxed text-sem-fg-muted">
                                        {{ $t("about.security_integrity_description") }}
                                    </p>
                                </div>
                                <div
                                    v-if="Array.isArray(appInfo.integrity_issues)"
                                    class="flex flex-wrap gap-2 shrink-0"
                                >
                                    <span
                                        :class="statusPillClass(appInfo.integrity_issues.length === 0)"
                                        class="font-black px-3 py-1 text-[11px]"
                                    >
                                        <MaterialDesignIcon
                                            :icon-name="
                                                appInfo.integrity_issues.length === 0 ? 'shield-check' : 'shield-alert'
                                            "
                                            class="size-3.5 shrink-0"
                                            :class="
                                                appInfo.integrity_issues.length === 0
                                                    ? 'text-emerald-600 dark:text-emerald-400'
                                                    : ''
                                            "
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
                                        class="secondary-chip px-3 py-1 text-[11px] font-black"
                                        @click="acknowledgeIntegrity"
                                    >
                                        <MaterialDesignIcon icon-name="check-circle" class="size-3.5 shrink-0" />
                                        {{ $t("common.acknowledge_reset") }}
                                    </button>
                                </div>
                            </div>

                            <div
                                v-if="Array.isArray(appInfo.integrity_issues) && appInfo.integrity_issues.length > 0"
                                class="p-4 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900 rounded-xl"
                            >
                                <div
                                    class="text-xs font-black text-amber-700 dark:text-amber-400 mb-3 uppercase tracking-wider flex items-center gap-2"
                                >
                                    <MaterialDesignIcon icon-name="alert" class="size-4" />
                                    {{ $t("about.technical_issues_detected") }}
                                </div>
                                <ul
                                    class="text-[11px] text-amber-700 dark:text-amber-300 space-y-2 list-none font-mono"
                                >
                                    <li
                                        v-for="(issue, index) in appInfo.integrity_issues"
                                        :key="index"
                                        class="flex gap-2"
                                    >
                                        <span class="opacity-50">•</span>
                                        <span>{{ issue }}</span>
                                    </li>
                                </ul>
                            </div>
                            <div
                                v-else
                                class="text-sm text-gray-700 dark:text-emerald-200 flex items-center gap-3 bg-emerald-500/10 dark:bg-emerald-900/30 p-4 rounded-xl border border-emerald-500/20 dark:border-emerald-500/30"
                            >
                                <MaterialDesignIcon
                                    icon-name="check-decagram"
                                    class="size-5 text-emerald-600 dark:text-emerald-400 shrink-0"
                                />
                                <span class="font-bold tracking-tight">{{ $t("about.no_integrity_violations") }}</span>
                            </div>
                        </div>

                        <div class="space-y-4">
                            <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                                <div>
                                    <div class="text-[10px] font-black text-sem-fg uppercase tracking-[0.2em] mb-2">
                                        {{ $t("about.sandbox_title") }}
                                    </div>
                                    <p class="text-[11px] leading-relaxed text-sem-fg-muted">
                                        {{ $t("about.sandbox_description") }}
                                    </p>
                                </div>
                                <span
                                    :class="statusPillClass(sandboxSummaryActive)"
                                    class="font-black px-3 py-1 text-[11px] shrink-0"
                                >
                                    <MaterialDesignIcon
                                        :icon-name="sandboxSummaryActive ? 'shield-check' : 'shield-off'"
                                        class="size-3.5 shrink-0"
                                        :class="sandboxSummaryActive ? 'text-emerald-600 dark:text-emerald-400' : ''"
                                    />
                                    {{ $t(sandboxSummaryTypeKey) }}
                                </span>
                            </div>

                            <div class="grid grid-cols-1 gap-3 min-w-0">
                                <div
                                    v-for="card in sandboxFeatureCards"
                                    :key="card.id"
                                    class="rounded-xl border p-3 min-w-0"
                                    :class="sandboxCardClass(card)"
                                >
                                    <div class="flex items-center gap-3 flex-wrap min-w-0">
                                        <span
                                            class="inline-flex items-center justify-center size-9 rounded-full border shrink-0"
                                            :class="sandboxIconClass(card)"
                                        >
                                            <MaterialDesignIcon
                                                :icon-name="card.active ? 'shield-check' : 'shield-off'"
                                                class="size-4"
                                            />
                                        </span>
                                        <div class="flex-1 min-w-0">
                                            <div class="text-sm font-bold text-sem-fg">
                                                {{ $t(card.titleKey) }}
                                            </div>
                                        </div>
                                        <span
                                            class="inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wider shrink-0"
                                            :class="sandboxBadgeClass(card)"
                                        >
                                            {{ $t(card.badgeKey) }}
                                        </span>
                                    </div>
                                    <p
                                        class="text-[11px] leading-relaxed text-sem-fg-muted mt-2"
                                        :class="card.active ? 'text-emerald-700 dark:text-emerald-300' : ''"
                                    >
                                        {{ $t(card.noteKey) }}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Active sessions -->
                    <div class="about-section">
                        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-4">
                            <div
                                class="text-xs font-black text-blue-500 uppercase tracking-[0.2em] flex items-center gap-2"
                            >
                                <MaterialDesignIcon icon-name="monitor-multiple" class="size-3.5" />
                                {{ $t("about.active_sessions") }}
                            </div>
                            <span class="text-[11px] font-black uppercase tracking-wider text-sem-fg-muted">
                                {{ $t("about.active_sessions_count", { count: activeSessionCount }) }}
                            </span>
                        </div>
                        <p class="text-[11px] leading-relaxed text-sem-fg-muted mb-4">
                            {{ $t("about.active_sessions_description") }}
                        </p>
                        <div v-if="!activeSessions.length" class="text-sm text-sem-fg-muted">
                            {{ $t("about.active_sessions_empty") }}
                        </div>
                        <ul v-else class="space-y-3 list-none">
                            <li
                                v-for="session in activeSessions"
                                :key="session.id"
                                class="rounded-xl border border-sem-border bg-gray-50/70 dark:bg-zinc-900/40 p-3 min-w-0"
                            >
                                <div class="grid gap-2 text-[11px] sm:grid-cols-2">
                                    <div class="min-w-0">
                                        <div
                                            class="text-[10px] font-black uppercase tracking-wider text-sem-fg-muted mb-1"
                                        >
                                            {{ $t("about.active_session_ip") }}
                                        </div>
                                        <div class="font-mono text-sem-fg break-all">
                                            {{ session.ip || "unknown" }}
                                        </div>
                                    </div>
                                    <div class="min-w-0">
                                        <div
                                            class="text-[10px] font-black uppercase tracking-wider text-sem-fg-muted mb-1"
                                        >
                                            {{ $t("about.active_session_connected") }}
                                        </div>
                                        <div class="text-sem-fg">
                                            {{ formatSessionConnectedAt(session.connected_at) }}
                                        </div>
                                    </div>
                                    <div class="min-w-0 sm:col-span-2">
                                        <div
                                            class="text-[10px] font-black uppercase tracking-wider text-sem-fg-muted mb-1"
                                        >
                                            {{ $t("about.active_session_user_agent") }}
                                        </div>
                                        <div class="font-mono text-sem-fg-secondary break-all">
                                            {{ session.user_agent || "unknown" }}
                                        </div>
                                    </div>
                                </div>
                            </li>
                        </ul>
                    </div>

                    <!-- Advanced Tech Info -->
                    <div v-if="appInfo" class="about-section">
                        <div
                            class="text-xs font-black text-blue-500 uppercase tracking-[0.2em] mb-6 flex items-center gap-2"
                        >
                            <MaterialDesignIcon icon-name="server" class="size-3.5" />
                            {{ $t("about.environment_information") }}
                        </div>
                        <div class="grid gap-8 sm:grid-cols-2 text-sm min-w-0">
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
                                    <MaterialDesignIcon icon-name="folder-open" class="size-3.5 shrink-0" />
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
                                    <MaterialDesignIcon icon-name="database-search" class="size-3.5 shrink-0" />
                                    {{ $t("about.reveal_database_file") }}
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Usage and battery -->
                    <div
                        v-if="
                            appInfo &&
                            (appInfo.memory_usage || appInfo.battery_usage || showHostBattery || batterySaverPrefs)
                        "
                        class="about-section"
                    >
                        <div
                            class="text-xs font-black text-cyan-600 uppercase tracking-[0.2em] mb-6 flex items-center gap-2"
                        >
                            <MaterialDesignIcon icon-name="gauge" class="size-3.5" />
                            {{ $t("about.usage_insights") }}
                        </div>
                        <div
                            class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 text-sm min-w-0 rounded-xl border border-gray-200/60 dark:border-zinc-800/80 p-4 sm:bg-black/2 dark:sm:bg-white/2"
                        >
                            <div class="flex items-center justify-between gap-3 sm:col-span-2 lg:col-span-3">
                                <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">{{
                                    $t("about.battery_saver")
                                }}</span>
                                <span
                                    class="font-mono text-xs font-bold tabular-nums shrink-0"
                                    :class="
                                        batterySaverPrefs.enabled
                                            ? 'text-emerald-600 dark:text-emerald-400'
                                            : 'opacity-70'
                                    "
                                >
                                    {{
                                        batterySaverPrefs.enabled
                                            ? $t("about.battery_saver_on")
                                            : $t("about.battery_saver_off")
                                    }}
                                </span>
                            </div>
                            <div
                                v-if="batterySaverActiveMeasures.length"
                                class="sm:col-span-2 lg:col-span-3 space-y-1.5"
                            >
                                <div class="text-[10px] font-semibold uppercase tracking-wider opacity-70">
                                    {{ $t("about.battery_saver_measures") }}
                                </div>
                                <ul
                                    class="text-xs grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 list-disc list-inside opacity-90"
                                >
                                    <li v-for="measure in batterySaverActiveMeasures" :key="measure">
                                        {{ $t(`about.battery_saver_measure.${measure}`) }}
                                    </li>
                                </ul>
                            </div>
                            <div v-if="topMemoryConsumerLabel" class="flex items-center justify-between gap-3">
                                <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">{{
                                    $t("about.top_memory_consumer")
                                }}</span>
                                <span
                                    class="font-mono text-xs font-bold tabular-nums text-right shrink-0 max-w-[70%]"
                                    :title="topMemoryConsumerLabel"
                                >
                                    {{ topMemoryConsumerLabel }}
                                </span>
                            </div>
                            <div v-if="topCpuConsumerLabel" class="flex items-center justify-between gap-3">
                                <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">{{
                                    $t("about.top_cpu_consumer")
                                }}</span>
                                <span
                                    class="font-mono text-xs font-bold tabular-nums text-right shrink-0 max-w-[70%]"
                                    :title="topCpuConsumerLabel"
                                >
                                    {{ topCpuConsumerLabel }}
                                </span>
                            </div>
                            <div v-if="batteryUsageLabel" class="flex items-center justify-between gap-3">
                                <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">{{
                                    $t("about.app_battery_use")
                                }}</span>
                                <span
                                    class="font-mono text-xs font-bold tabular-nums shrink-0"
                                    :class="batteryUsageToneClass"
                                    :title="$t('about.app_battery_use_hint')"
                                >
                                    {{ batteryUsageLabel }}
                                </span>
                            </div>
                            <div v-if="batteryUsageShareLabel" class="flex items-center justify-between gap-3">
                                <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">{{
                                    $t("about.app_battery_share")
                                }}</span>
                                <span class="font-mono text-xs font-bold tabular-nums">{{
                                    batteryUsageShareLabel
                                }}</span>
                            </div>
                            <div v-if="appInfo.memory_usage" class="flex items-center justify-between gap-3">
                                <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">{{
                                    $t("about.memory_rss")
                                }}</span>
                                <span class="font-mono text-xs font-bold tabular-nums">{{
                                    formatBytes(appInfo.memory_usage.rss || 0)
                                }}</span>
                            </div>
                            <div v-if="appInfo.memory_usage" class="flex items-center justify-between gap-3">
                                <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">{{
                                    $t("about.virtual_memory")
                                }}</span>
                                <span class="font-mono text-xs font-bold tabular-nums">{{
                                    formatBytes(appInfo.memory_usage.vms || 0)
                                }}</span>
                            </div>
                            <div
                                v-if="appInfo.memory_usage && appInfo.memory_usage.cpu_percent != null"
                                class="flex items-center justify-between gap-3"
                            >
                                <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">{{
                                    $t("about.process_cpu")
                                }}</span>
                                <span class="font-mono text-xs font-bold tabular-nums">{{
                                    formatCpuPercent(appInfo.memory_usage.cpu_percent)
                                }}</span>
                            </div>
                            <div
                                v-if="appInfo.memory_usage && appInfo.memory_usage.num_threads != null"
                                class="flex items-center justify-between gap-3"
                            >
                                <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">{{
                                    $t("about.process_threads")
                                }}</span>
                                <span class="font-mono text-xs font-bold tabular-nums">{{
                                    appInfo.memory_usage.num_threads
                                }}</span>
                            </div>
                            <div v-if="processUptimeLabel" class="flex items-center justify-between gap-3">
                                <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">{{
                                    $t("about.process_uptime")
                                }}</span>
                                <span class="font-mono text-xs font-bold tabular-nums">{{ processUptimeLabel }}</span>
                            </div>
                            <div v-if="pathTableSizeLabel" class="flex items-center justify-between gap-3">
                                <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">{{
                                    $t("about.path_table")
                                }}</span>
                                <span class="font-mono text-xs font-bold tabular-nums">{{ pathTableSizeLabel }}</span>
                            </div>
                            <div v-if="memoryPressureLabel" class="flex items-center justify-between gap-3">
                                <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">{{
                                    $t("about.memory_pressure")
                                }}</span>
                                <span
                                    class="font-mono text-xs font-bold tabular-nums"
                                    :class="memoryPressureToneClass"
                                    >{{ memoryPressureLabel }}</span
                                >
                            </div>
                            <div v-if="showHostBattery" class="flex items-center justify-between gap-3">
                                <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">{{
                                    $t("about.env_host_battery")
                                }}</span>
                                <span
                                    class="font-mono text-xs font-bold shrink-0 inline-flex items-center gap-1"
                                    :class="batteryStatusToneClass"
                                >
                                    <MaterialDesignIcon :icon-name="batteryStatusIcon" class="size-3.5" />
                                    {{ batteryStatusLabel }}
                                </span>
                            </div>
                        </div>
                    </div>

                    <!-- Dependency Chain -->
                    <div v-if="appInfo" class="about-section">
                        <div
                            class="text-xs font-black text-blue-500 uppercase tracking-[0.2em] mb-8 flex items-center gap-2"
                        >
                            <MaterialDesignIcon icon-name="link-variant" class="size-3.5" />
                            {{ $t("about.dependency_chain") }}
                        </div>
                        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 relative min-w-0">
                            <div class="flex flex-col space-y-8 min-w-0">
                                <div class="flex items-center gap-5">
                                    <div
                                        class="w-12 h-12 rounded-2xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20 shadow-xs"
                                    >
                                        <img :src="logoUrl" class="w-7 h-7 object-contain" />
                                    </div>
                                    <div>
                                        <div class="text-sm font-black text-sem-fg">
                                            {{ $t("about.app_name") }}
                                        </div>
                                        <div class="text-xs font-mono font-bold text-gray-400">
                                            v{{ aboutDisplayVersion }}
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
                                        class="w-12 h-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20 text-emerald-600 shadow-xs"
                                    >
                                        <MaterialDesignIcon icon-name="robot" class="size-6" />
                                    </div>
                                    <div>
                                        <div class="text-sm font-black text-sem-fg leading-tight">LXMFy</div>
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
                                        class="w-12 h-12 rounded-2xl bg-purple-500/10 flex items-center justify-center border border-purple-500/20 text-purple-600 shadow-xs"
                                    >
                                        <MaterialDesignIcon icon-name="message-text" class="size-6" />
                                    </div>
                                    <div>
                                        <div class="text-sm font-black text-sem-fg leading-tight">LXMF</div>
                                        <div class="text-xs font-mono font-bold text-gray-400 mt-1">
                                            v{{ appInfo.lxmf_version }}
                                        </div>
                                    </div>
                                </div>
                                <div
                                    v-if="appInfo.lxst_version"
                                    class="flex items-center gap-5 pl-5 border-l-2 border-zinc-100 dark:border-zinc-800 ml-6 relative"
                                >
                                    <div
                                        class="absolute left-[-2px] top-0 bottom-0 w-[2px] bg-linear-to-b from-purple-500 to-rose-500"
                                    ></div>
                                    <div
                                        class="w-12 h-12 rounded-2xl bg-rose-500/10 flex items-center justify-center border border-rose-500/20 text-rose-600 shadow-xs"
                                    >
                                        <MaterialDesignIcon icon-name="phone" class="size-6" />
                                    </div>
                                    <div>
                                        <div class="text-sm font-black text-sem-fg leading-tight">LXST</div>
                                        <div class="text-xs font-mono font-bold text-gray-400 mt-1">
                                            v{{ appInfo.lxst_version }}
                                        </div>
                                    </div>
                                </div>
                                <div
                                    class="flex items-center gap-5 pl-5 border-l-2 border-zinc-100 dark:border-zinc-800 ml-6 relative"
                                >
                                    <div
                                        class="absolute left-[-2px] top-0 bottom-0 w-[2px] bg-linear-to-b from-rose-500 to-indigo-500"
                                    ></div>
                                    <div
                                        class="w-12 h-12 rounded-2xl bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 text-indigo-600 shadow-xs"
                                    >
                                        <MaterialDesignIcon icon-name="lan" class="size-6" />
                                    </div>
                                    <div>
                                        <div class="text-sm font-black text-sem-fg leading-tight">RNS</div>
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
                                    v-if="electronVersion || chromeVersion || nodeVersion"
                                    class="py-4 sm:p-5 border-t border-gray-200/60 dark:border-zinc-800/80 sm:border sm:rounded-2xl sm:bg-black/2 dark:sm:bg-white/2 min-w-0"
                                >
                                    <div
                                        class="text-[10px] font-black text-black dark:text-white uppercase tracking-[0.2em] mb-4"
                                    >
                                        {{ $t("about.core_runtime") }}
                                    </div>
                                    <div class="grid grid-cols-2 gap-x-6 gap-y-4">
                                        <div v-if="electronVersion" class="flex flex-col">
                                            <span
                                                class="text-[9px] font-black text-black dark:text-white uppercase leading-none"
                                                >{{ $t("about.electron_runtime") }}</span
                                            >
                                            <span
                                                class="text-[11px] font-mono font-bold mt-1.5 text-black dark:text-white tracking-tight"
                                                >v{{ electronVersion }}</span
                                            >
                                        </div>
                                        <div v-if="chromeVersion" class="flex flex-col">
                                            <span
                                                class="text-[9px] font-black text-black dark:text-white uppercase leading-none"
                                                >{{ $t("about.chrome_runtime") }}</span
                                            >
                                            <span
                                                class="text-[11px] font-mono font-bold mt-1.5 text-black dark:text-white tracking-tight"
                                                >v{{ chromeVersion }}</span
                                            >
                                        </div>
                                        <div v-if="nodeVersion" class="flex flex-col">
                                            <span
                                                class="text-[9px] font-black text-black dark:text-white uppercase leading-none"
                                                >{{ $t("about.nodejs_runtime") }}</span
                                            >
                                            <span
                                                class="text-[11px] font-mono font-bold mt-1.5 text-black dark:text-white tracking-tight"
                                                >v{{ nodeVersion }}</span
                                            >
                                        </div>
                                    </div>
                                </div>

                                <div v-if="appInfo.dependencies" class="pt-2">
                                    <div
                                        class="text-[10px] font-black text-black dark:text-white uppercase tracking-[0.2em] mb-4"
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
                                                class="text-[9px] font-black text-black dark:text-white uppercase truncate leading-none"
                                                >{{ name.replace("_", " ") }}</span
                                            >
                                            <span
                                                class="text-[10px] font-mono font-bold mt-1.5 text-black dark:text-white tracking-tight"
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
                                <MaterialDesignIcon icon-name="database-cog" class="size-3.5" />
                                {{ $t("about.database_health_maintenance") }}
                            </div>
                            <div class="flex flex-wrap gap-2 w-full md:w-auto">
                                <button
                                    type="button"
                                    class="secondary-chip px-4! py-1.5! text-xs! min-h-[44px] sm:min-h-0"
                                    :disabled="databaseActionInProgress || healthLoading"
                                    @click="getDatabaseHealth(true)"
                                >
                                    <MaterialDesignIcon icon-name="refresh" class="size-3.5 shrink-0" />
                                    <span v-if="healthLoading">{{ $t("common.loading") }}</span>
                                    <span v-else>{{ $t("common.refresh") }}</span>
                                </button>
                                <button
                                    type="button"
                                    class="primary-chip px-4! py-1.5! text-xs!"
                                    :disabled="databaseActionInProgress"
                                    @click="vacuumDatabase"
                                >
                                    <MaterialDesignIcon icon-name="broom" class="size-3.5 shrink-0" />
                                    {{ $t("common.vacuum") }}
                                </button>
                                <button
                                    type="button"
                                    class="primary-chip px-4! py-1.5! text-xs!"
                                    :disabled="databaseActionInProgress"
                                    @click="runAutoRecover"
                                >
                                    <MaterialDesignIcon icon-name="auto-fix" class="size-3.5 shrink-0" />
                                    {{ $t("common.auto_recover") }}
                                </button>
                                <button
                                    type="button"
                                    class="danger-chip px-4! py-1.5! text-xs!"
                                    :disabled="databaseActionInProgress"
                                    @click="runRecovery"
                                >
                                    <MaterialDesignIcon icon-name="medical-bag" class="size-3.5 shrink-0" />
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

                        <div
                            id="about-database-backups"
                            class="border-t border-zinc-100 dark:border-zinc-800 pt-8 space-y-8"
                        >
                            <!-- Backups -->
                            <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                                <div class="space-y-1">
                                    <div class="font-black text-sem-fg text-sm tracking-tight flex items-center gap-2">
                                        <MaterialDesignIcon icon-name="content-save-all" class="size-4 text-blue-500" />
                                        {{ $t("about.database_backups_title") }}
                                    </div>
                                    <div class="text-xs text-gray-500">
                                        {{ $t("about.database_backups_desc") }}
                                    </div>
                                </div>
                                <div class="flex flex-col sm:flex-row gap-2 shrink-0">
                                    <button
                                        type="button"
                                        class="primary-chip px-5! py-2.5! text-sm"
                                        :disabled="backupInProgress"
                                        @click="backupDatabase"
                                    >
                                        <MaterialDesignIcon icon-name="download" class="size-4 shrink-0" />
                                        <span v-if="backupInProgress">{{ $t("about.downloading") }}</span>
                                        <span v-else>{{ $t("about.download_backup") }}</span>
                                    </button>
                                    <button
                                        type="button"
                                        class="secondary-chip px-5! py-2.5! text-sm"
                                        :disabled="restoreInProgress"
                                        @click="$refs.restoreFileInput?.click()"
                                    >
                                        <MaterialDesignIcon icon-name="upload" class="size-4 shrink-0" />
                                        <span v-if="restoreInProgress">{{ $t("about.restoring") }}</span>
                                        <span v-else>{{ $t("about.restore_from_file") }}</span>
                                    </button>
                                    <input
                                        ref="restoreFileInput"
                                        type="file"
                                        accept=".zip,application/zip"
                                        class="hidden"
                                        @change="onRestoreFileChange"
                                    />
                                </div>
                            </div>

                            <!-- Snapshots -->
                            <div class="space-y-6">
                                <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                                    <div class="space-y-1">
                                        <div
                                            class="font-black text-sem-fg text-sm tracking-tight flex items-center gap-2"
                                        >
                                            <MaterialDesignIcon icon-name="camera" class="size-4 text-purple-500" />
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
                                                <span class="font-black text-sem-fg text-xs truncate">{{
                                                    snapshot.name
                                                }}</span>
                                                <span class="text-[10px] font-bold text-gray-400 mt-1 tabular-nums"
                                                    >{{ formatBytes(snapshot.size) }} •
                                                    {{ Utils.formatTimeAgo(snapshot.created_at) }}</span
                                                >
                                            </div>
                                            <div class="flex gap-2 shrink-0">
                                                <button
                                                    type="button"
                                                    class="primary-chip px-3! py-1! text-[10px]!"
                                                    @click="downloadSnapshot(snapshot.name)"
                                                >
                                                    <MaterialDesignIcon icon-name="download" class="size-3 shrink-0" />
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
                                                    <MaterialDesignIcon icon-name="delete" class="size-3" />
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
                                                class="secondary-chip p-1.5! disabled:opacity-30"
                                                :disabled="snapshotsOffset === 0"
                                                @click="prevSnapshots"
                                            >
                                                <MaterialDesignIcon icon-name="chevron-left" class="size-4" />
                                            </button>
                                            <button
                                                class="secondary-chip p-1.5! disabled:opacity-30"
                                                :disabled="snapshotsOffset + snapshotsLimit >= snapshotsTotal"
                                                @click="nextSnapshots"
                                            >
                                                <MaterialDesignIcon icon-name="chevron-right" class="size-4" />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Auto Backups -->
                            <div class="space-y-6">
                                <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                                    <div class="space-y-1">
                                        <div
                                            class="font-black text-sem-fg text-sm tracking-tight flex items-center gap-2"
                                        >
                                            <MaterialDesignIcon icon-name="history" class="size-4 text-blue-500" />
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
                                                <span class="font-black text-sem-fg text-xs truncate">{{
                                                    backup.name
                                                }}</span>
                                                <span class="text-[10px] font-bold text-gray-400 mt-1 tabular-nums"
                                                    >{{ formatBytes(backup.size) }} •
                                                    {{ Utils.formatTimeAgo(backup.created_at) }}</span
                                                >
                                            </div>
                                            <div class="flex gap-2 shrink-0">
                                                <button
                                                    type="button"
                                                    class="primary-chip p-1.5!"
                                                    :aria-label="$t('about.snapshot_download')"
                                                    :title="$t('about.snapshot_download')"
                                                    @click="downloadBackupFile(backup.name)"
                                                >
                                                    <MaterialDesignIcon icon-name="download" class="size-4" />
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
                                                    <MaterialDesignIcon icon-name="delete" class="size-3" />
                                                </button>
                                            </div>
                                        </div>
                                    </div>

                                    <div
                                        v-if="autoBackups.some((b) => b.name.includes('SUSPICIOUS'))"
                                        class="mt-4 p-3 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900 text-xs text-amber-700 dark:text-amber-300 flex items-start gap-2"
                                    >
                                        <MaterialDesignIcon icon-name="alert" class="size-4 shrink-0 mt-0.5" />
                                        <span
                                            >Suspicious backups are created when the database size or message count
                                            drops unexpectedly compared to the last known baseline, usually after a
                                            crash, corruption, or deletion. They are kept automatically so you can
                                            inspect or restore from them.</span
                                        >
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
                                                class="secondary-chip p-1.5! disabled:opacity-30"
                                                :disabled="autoBackupsOffset === 0"
                                                @click="prevBackups"
                                            >
                                                <MaterialDesignIcon icon-name="chevron-left" class="size-4" />
                                            </button>
                                            <button
                                                class="secondary-chip p-1.5! disabled:opacity-30"
                                                :disabled="autoBackupsOffset + autoBackupsLimit >= autoBackupsTotal"
                                                @click="nextBackups"
                                            >
                                                <MaterialDesignIcon icon-name="chevron-right" class="size-4" />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                                <div
                                    v-else
                                    class="rounded-xl border border-dashed border-zinc-200 dark:border-zinc-700 px-4 py-6 text-center text-xs text-gray-500"
                                >
                                    {{ $t("about.automatic_backups_empty") }}
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
import DownloadUtils from "../../js/DownloadUtils";
import GlobalEmitter from "../../js/GlobalEmitter";
import { onWsEvent, offWsEvent } from "../../js/registries/wsEventRegistry.js";
import {
    appBatteryUsageToneClass,
    batteryStatusIconName,
    formatAppBatteryShareLabel,
    formatAppBatteryUsageLabel,
    formatProcessUptime,
    getDeviceBatteryStatus,
    isNativeBatteryStatus,
} from "../../js/deviceBattery.js";
import {
    activeBatterySaverMeasures,
    applyBackgroundPollInterval,
    BATTERY_SAVER_CHANGED_EVENT,
    loadBatterySaverPrefs,
} from "../../js/settings/batterySaverPrefs.js";
import { mergeResourceBreakdown, topResourceByCpu, topResourceByRss } from "../../js/resourceBreakdown.js";
import {
    listSandboxFeatures,
    sandboxSummaryActive as computeSandboxSummaryActive,
    sandboxSummaryType,
} from "../../js/sandboxStatus.js";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import logoUrl from "../../assets/images/logo.png";
import {
    channelBadgeClass,
    channelBugReportTarget,
    channelLabelKey,
    normalizeReleaseChannel,
} from "../../js/releaseChannel.js";

export default {
    name: "AboutPage",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            Utils,
            logoUrl,
            appInfo: {
                version: "unknown",
            },
            updateInterval: null,
            healthInterval: null,
            databaseHealth: null,
            databaseRecoveryActions: [],
            databaseActionMessage: "",
            databaseActionError: "",
            databaseActionInProgress: false,
            healthLoading: false,
            electronMemoryUsage: null,
            batteryStatus: null,
            batterySaverPrefs: loadBatterySaverPrefs(),
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
            autoBackupsLimit: 4,
            electronVersion: null,
            chromeVersion: null,
            nodeVersion: null,
            showContactSupport: false,
            developerLxmfPrimary: "f489752fbef161c64d65e385a4e9fc74",
            developerLxmfAlternate: "43d3309adf27fc446556121b553b56a6",
            moneroDonateAddress:
                "83SUg6mmkkVGwCycckLEgRfdmXNm7H9XtVjbGXp5kko71N6pTefYURJeS7WdEGHrz2aagmt4nF3dWg6mHcYs6yu4EokwhTh",
            activeSessions: [],
            activeSessionCount: 0,
            sessionsWsHandler: null,
        };
    },
    computed: {
        isElectron() {
            return ElectronUtils.isElectron();
        },
        aboutDisplayVersion() {
            const info = this.appInfo || {};
            if (info.display_version) {
                return info.display_version;
            }
            const base = info.version || "unknown";
            if (info.is_dev_build && !String(base).endsWith("-dev")) {
                return `${base}-dev`;
            }
            return base;
        },
        aboutChannel() {
            return normalizeReleaseChannel(this.appInfo?.build_channel);
        },
        aboutChannelLabel() {
            if (!this.appInfo) {
                return "";
            }
            return this.$t(channelLabelKey(this.aboutChannel));
        },
        aboutChannelBadgeClass() {
            return channelBadgeClass(this.aboutChannel);
        },
        aboutShowChannelPromptDetails() {
            return this.aboutChannel === "testing" || this.aboutChannel === "beta";
        },
        aboutChannelPrompt() {
            const p = this.appInfo?.channel_prompt;
            return p && typeof p === "object" ? p : {};
        },
        aboutFocusAreas() {
            return Array.isArray(this.aboutChannelPrompt.focus_areas)
                ? this.aboutChannelPrompt.focus_areas.map((s) => String(s)).filter(Boolean)
                : [];
        },
        aboutBugReportSteps() {
            return Array.isArray(this.aboutChannelPrompt.bug_report_steps)
                ? this.aboutChannelPrompt.bug_report_steps.map((s) => String(s)).filter(Boolean)
                : [];
        },
        aboutBugReportTarget() {
            return channelBugReportTarget(this.aboutChannelPrompt);
        },
        aboutChannelNotes() {
            return typeof this.aboutChannelPrompt.notes === "string" ? this.aboutChannelPrompt.notes.trim() : "";
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
        batteryStatusIcon() {
            return batteryStatusIconName(this.batteryStatus);
        },
        showHostBattery() {
            return isNativeBatteryStatus(this.batteryStatus);
        },
        batteryUsageLabel() {
            return formatAppBatteryUsageLabel(this.appInfo?.battery_usage, (key, values) => this.$t(key, values));
        },
        batteryUsageShareLabel() {
            return formatAppBatteryShareLabel(this.appInfo?.battery_usage, (key, values) => this.$t(key, values));
        },
        batteryUsageToneClass() {
            return appBatteryUsageToneClass(this.appInfo?.battery_usage);
        },
        batterySaverActiveMeasures() {
            return activeBatterySaverMeasures(this.batterySaverPrefs);
        },
        resourceBreakdownRows() {
            return mergeResourceBreakdown(this.appInfo?.resource_breakdown, this.electronMemoryUsage);
        },
        topMemoryConsumerLabel() {
            const top = topResourceByRss(this.resourceBreakdownRows);
            if (!top) return "";
            return `${top.name} (${this.formatBytes(top.rss || 0)})`;
        },
        topCpuConsumerLabel() {
            const top = topResourceByCpu(this.resourceBreakdownRows);
            if (!top) return "";
            return `${top.name} (${this.formatCpuPercent(top.cpu_percent)})`;
        },
        processUptimeLabel() {
            return formatProcessUptime(this.appInfo?.memory_usage?.create_time);
        },
        pathTableSizeLabel() {
            const cleanup = this.appInfo?.reticulum_stats?.memory_cleanup;
            const total = this.appInfo?.reticulum_stats?.total_paths;
            const pathSize =
                cleanup && typeof cleanup === "object" && cleanup.path_table_size != null
                    ? cleanup.path_table_size
                    : total;
            if (pathSize == null) {
                return null;
            }
            return this.$t("about.path_table_count", { count: pathSize });
        },
        memoryPressureLabel() {
            const cleanup = this.appInfo?.reticulum_stats?.memory_cleanup;
            if (!cleanup || typeof cleanup !== "object") {
                return this.$t("about.memory_pressure_normal");
            }
            if (cleanup.sqlite_relaxed) {
                return this.$t("about.memory_pressure_relaxed");
            }
            return this.$t("about.memory_pressure_normal");
        },
        memoryPressureToneClass() {
            const cleanup = this.appInfo?.reticulum_stats?.memory_cleanup;
            if (cleanup && typeof cleanup === "object" && cleanup.sqlite_relaxed) {
                return "text-amber-600 dark:text-amber-400";
            }
            return "opacity-70";
        },
        batteryStatusLabel() {
            if (!this.batteryStatus || !this.batteryStatus.supported) {
                return this.$t("about.env_battery_unavailable");
            }
            const level =
                this.batteryStatus.level != null ? `${this.batteryStatus.level}%` : this.$t("about.path_unknown");
            if (this.batteryStatus.charging === true) {
                return this.$t("about.env_battery_charging", { percent: level });
            }
            if (this.batteryStatus.charging === false) {
                return this.$t("about.env_battery_on_battery", { percent: level });
            }
            return level;
        },
        sandboxFeatureCards() {
            return listSandboxFeatures(this.appInfo);
        },
        sandboxSummaryActive() {
            return computeSandboxSummaryActive(this.appInfo);
        },
        sandboxSummaryTypeKey() {
            return sandboxSummaryType(this.appInfo);
        },
        batteryStatusToneClass() {
            if (!this.batteryStatus || !this.batteryStatus.supported) {
                return "opacity-70";
            }
            if (this.batteryStatus.charging) {
                return "text-emerald-600 dark:text-emerald-400";
            }
            const level = this.batteryStatus.level;
            if (level != null && level <= 15) {
                return "text-red-600 dark:text-red-400";
            }
            if (level != null && level <= 30) {
                return "text-amber-600 dark:text-amber-400";
            }
            return "";
        },
    },
    watch: {
        "$route.hash"() {
            this.$nextTick(() => {
                this.scrollToDatabaseBackupsIfNeeded();
            });
        },
    },
    mounted() {
        this.getAppInfo();
        this.getActiveSessions();
        this.getDatabaseHealth();
        this.listSnapshots();
        this.listAutoBackups();
        this._batterySaverPrefsHandler = (prefs) => {
            this.batterySaverPrefs = prefs || loadBatterySaverPrefs();
            this.restartAboutPollIntervals();
        };
        GlobalEmitter.on(BATTERY_SAVER_CHANGED_EVENT, this._batterySaverPrefsHandler);
        GlobalEmitter.on("identity-switched", this.onIdentitySwitched);
        this.sessionsWsHandler = (payload) => {
            this.applyActiveSessionsPayload(payload);
        };
        onWsEvent("app.sessions.updated", this.sessionsWsHandler);
        this.restartAboutPollIntervals();
        this.$nextTick(() => {
            this.scrollToDatabaseBackupsIfNeeded();
        });
    },
    beforeUnmount() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        if (this.healthInterval) {
            clearInterval(this.healthInterval);
        }
        if (this._batterySaverPrefsHandler) {
            GlobalEmitter.off(BATTERY_SAVER_CHANGED_EVENT, this._batterySaverPrefsHandler);
        }
        GlobalEmitter.off("identity-switched", this.onIdentitySwitched);
        if (this.sessionsWsHandler) {
            offWsEvent("app.sessions.updated", this.sessionsWsHandler);
            this.sessionsWsHandler = null;
        }
    },
    methods: {
        onIdentitySwitched() {
            this.getAppInfo();
            this.getActiveSessions();
            this.getDatabaseHealth();
            this.snapshotsOffset = 0;
            this.autoBackupsOffset = 0;
            this.listSnapshots();
            this.listAutoBackups();
        },
        scrollToDatabaseBackupsIfNeeded() {
            const hash = typeof this.$route?.hash === "string" ? this.$route.hash : "";
            if (!hash.includes("about-database-backups")) {
                return;
            }
            const el = document.getElementById("about-database-backups");
            if (el) {
                el.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        },
        restartAboutPollIntervals() {
            if (this.updateInterval) {
                clearInterval(this.updateInterval);
            }
            if (this.healthInterval) {
                clearInterval(this.healthInterval);
            }
            const prefs = this.batterySaverPrefs || loadBatterySaverPrefs();
            this.updateInterval = setInterval(
                () => {
                    this.getAppInfo();
                    this.getActiveSessions();
                },
                applyBackgroundPollInterval(5000, prefs)
            );
            this.healthInterval = setInterval(
                () => {
                    this.getDatabaseHealth();
                },
                applyBackgroundPollInterval(30000, prefs)
            );
        },
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
                const downloadName = filename.endsWith(".zip") ? filename : `${filename}.zip`;
                const response = await window.api.post(`/api/v1/database/snapshots/${filename}/download`, null, {
                    responseType: "arraybuffer",
                });
                await DownloadUtils.downloadFromApiResponse(response, downloadName);
                ToastUtils.success(this.$t("about.snapshot_downloaded"));
            } catch {
                ToastUtils.error(this.$t("about.snapshot_download_failed"));
            }
        },
        async downloadBackupFile(filename) {
            try {
                const response = await window.api.post(`/api/v1/database/backups/${filename}/download`, null, {
                    responseType: "arraybuffer",
                });
                await DownloadUtils.downloadFromApiResponse(response, filename);
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
            if (this.restoreInProgress) {
                return;
            }
            this.restoreInProgress = true;
            try {
                if (!(await DialogUtils.confirm(this.$t("about.restore_snapshot_confirm")))) {
                    return;
                }
                const response = await window.api.post("/api/v1/database/restore", { path });
                if (response.data.status === "success") {
                    ToastUtils.success(this.$t("about.database_restored"));
                    this.scheduleRestoreRelaunch();
                }
            } catch {
                ToastUtils.error(this.$t("about.failed_restore_snapshot"));
            } finally {
                this.restoreInProgress = false;
            }
        },
        scheduleRestoreRelaunch() {
            if (this.isElectron) {
                setTimeout(() => ElectronUtils.relaunch(), 2000);
                return;
            }
            setTimeout(() => {
                window.location.reload();
            }, 2000);
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
                await this.refreshBatteryStatus();
            } catch (e) {
                console.log(e);
            }
        },
        applyActiveSessionsPayload(payload) {
            const sessions = Array.isArray(payload?.sessions) ? payload.sessions : [];
            this.activeSessions = sessions;
            const count = Number(payload?.count);
            this.activeSessionCount = Number.isFinite(count) ? count : sessions.length;
        },
        async getActiveSessions() {
            try {
                const response = await window.api.get("/api/v1/app/sessions");
                this.applyActiveSessionsPayload(response?.data || {});
            } catch (e) {
                console.log(e);
            }
        },
        formatSessionConnectedAt(value) {
            const ts = Number(value);
            if (!Number.isFinite(ts) || ts <= 0) {
                return "unknown";
            }
            try {
                return new Date(ts * 1000).toLocaleString();
            } catch {
                return "unknown";
            }
        },
        async refreshBatteryStatus() {
            try {
                this.batteryStatus = await getDeviceBatteryStatus();
            } catch {
                this.batteryStatus = null;
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
                const response = await window.api.post("/api/v1/database/backup/download", null, {
                    responseType: "arraybuffer",
                });
                const filename =
                    response.headers["content-disposition"]?.split("filename=")?.[1]?.replace(/"/g, "") ||
                    "meshchatx-backup.zip";
                await DownloadUtils.downloadFromApiResponse(response, filename);
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
                this.restoreError = this.$t("about.restore_select_file");
                return;
            }
            if (!(await DialogUtils.confirm(this.$t("about.restore_file_confirm")))) {
                this.restoreFile = null;
                this.restoreFileName = "";
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
                this.restoreMessage = response.data.message || this.$t("about.database_restored");
                this.databaseHealth = response.data.database?.health || this.databaseHealth;
                this.databaseRecoveryActions = response.data.database?.actions || this.databaseRecoveryActions;
                ToastUtils.success(this.$t("about.database_restored"));
                this.scheduleRestoreRelaunch();
                await this.getDatabaseHealth();
            } catch (e) {
                this.restoreError = this.$t("about.failed_restore_file");
                ToastUtils.error(this.$t("about.failed_restore_file"));
                console.log(e);
            } finally {
                this.restoreInProgress = false;
                this.restoreFile = null;
                this.restoreFileName = "";
            }
        },
        async runAutoRecover() {
            if (this.databaseActionInProgress) {
                return;
            }
            if (!(await DialogUtils.confirm(this.$t("about.auto_recover_confirm")))) {
                return;
            }
            this.databaseActionInProgress = true;
            this.databaseActionMessage = "";
            this.databaseActionError = "";
            try {
                const response = await window.api.post("/api/v1/database/auto-recover", { relaunch: true });
                const strategy = response.data?.strategy;
                const msg = response.data?.message;
                if (strategy === "restore_backup") {
                    ToastUtils.success(msg || this.$t("about.auto_recover_backup"));
                    if (response.data?.requires_relaunch) {
                        this.scheduleRestoreRelaunch();
                    }
                } else if (strategy === "sqlite_recovery") {
                    if (response.data.database?.health) {
                        this.databaseHealth = response.data.database.health;
                    }
                    this.databaseRecoveryActions = response.data.database?.actions || [];
                    ToastUtils.success(msg || this.$t("about.recovery_complete"));
                } else {
                    this.databaseActionError = msg || this.$t("about.auto_recover_failed");
                    ToastUtils.error(this.databaseActionError);
                }
            } catch (e) {
                this.databaseActionError = this.$t("about.auto_recover_failed");
                const detail = e?.response?.data?.message || e?.response?.data?.error;
                ToastUtils.error(detail || this.databaseActionError);
                console.log(e);
            } finally {
                this.databaseActionInProgress = false;
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
        async onAboutBugReportAction() {
            if (!this.aboutBugReportTarget.value) {
                return;
            }
            try {
                await navigator.clipboard.writeText(this.aboutBugReportTarget.value);
                ToastUtils.success(
                    this.aboutBugReportTarget.kind === "lxmf"
                        ? this.$t("channel_prompt.lxmf_copied")
                        : this.$t("channel_prompt.url_copied")
                );
            } catch {
                ToastUtils.error(
                    this.aboutBugReportTarget.kind === "lxmf"
                        ? this.$t("channel_prompt.lxmf_copy_failed")
                        : this.$t("channel_prompt.url_copy_failed")
                );
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
        formatCpuPercent(value) {
            const n = typeof value === "number" ? value : Number(value);
            if (!Number.isFinite(n)) {
                return this.$t("about.path_unknown");
            }
            return `${n.toFixed(n >= 10 ? 0 : 1)}%`;
        },
        formatNumber: function (num) {
            return Utils.formatNumber(num);
        },
        formatBytesPerSecond: function (bytesPerSecond) {
            return Utils.formatBytesPerSecond(bytesPerSecond);
        },
        async onRestoreFileChange(event) {
            const input = event.target;
            const files = input.files;
            if (files && files[0]) {
                this.restoreFile = files[0];
                this.restoreFileName = files[0].name;
                this.restoreError = "";
                this.restoreMessage = "";
                await this.restoreDatabase();
            }
            // allow re-selecting the same file later
            input.value = "";
        },
        formatRecoveryResult(value) {
            if (value === null || value === undefined) {
                return "-";
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
        sandboxCardClass(card) {
            if (card.active) {
                return "border-emerald-500/35 bg-emerald-500/5 dark:bg-emerald-900/20";
            }
            if (card.warn) {
                return "border-amber-500/35 bg-amber-500/5 dark:bg-amber-950/20";
            }
            return "border-gray-200/60 dark:border-zinc-800/80";
        },
        sandboxIconClass(card) {
            if (card.active) {
                return "text-emerald-600 dark:text-emerald-400 border-emerald-500/35 bg-emerald-500/10";
            }
            if (card.unavailable) {
                return "text-sem-fg-muted border-gray-200/60 dark:border-zinc-800/80 bg-gray-50/70 dark:bg-zinc-900/40";
            }
            return "text-sem-fg-muted border-gray-200/60 dark:border-zinc-800/80";
        },
        sandboxBadgeClass(card) {
            if (card.active) {
                return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300";
            }
            if (card.unavailable) {
                return "bg-gray-100 text-gray-600 dark:bg-zinc-800 dark:text-gray-300";
            }
            if (card.warn) {
                return "bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300";
            }
            return "bg-gray-100 text-gray-600 dark:bg-zinc-800 dark:text-gray-300";
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
