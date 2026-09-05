<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import logoUrl from "../../../assets/images/logo.png";
    import GlobalEmitter from "../../../js/GlobalEmitter.js";
    import ToastUtils from "../../../js/ToastUtils.js";
    import Utils from "../../../js/Utils.js";
    import { t } from "../../../js/i18n.js";
    import {
        channelBadgeClass,
        channelBugReportTarget,
        channelLabelKey,
        normalizeReleaseChannel,
    } from "../../../js/releaseChannel.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { formatDisplayVersion, formatUiBuildDate } from "../lib/aboutFormat.js";
    import type { AppInfo } from "../lib/types.js";

    interface Props {
        appInfo?: AppInfo | null;
        isElectron?: boolean;
        reloadingRns?: boolean;
        onreloadrns?: () => void;
        onrelaunch?: () => void;
        onshutdown?: () => void;
    }

    let {
        appInfo = null,
        isElectron = false,
        reloadingRns = false,
        onreloadrns,
        onrelaunch,
        onshutdown,
    }: Props = $props();

    const aboutDisplayVersion = $derived(formatDisplayVersion(appInfo));
    const formattedUiBuildDate = $derived(formatUiBuildDate());
    const aboutChannel = $derived(normalizeReleaseChannel(appInfo?.build_channel));
    const aboutChannelLabel = $derived(appInfo ? t(channelLabelKey(aboutChannel)) : "");
    const aboutChannelBadgeClass = $derived(channelBadgeClass(aboutChannel));
    const aboutShowChannelPromptDetails = $derived(aboutChannel === "testing" || aboutChannel === "beta");
    const aboutChannelPrompt = $derived(
        appInfo?.channel_prompt && typeof appInfo.channel_prompt === "object" ? appInfo.channel_prompt : {}
    );
    const aboutFocusAreas = $derived(
        Array.isArray(aboutChannelPrompt.focus_areas)
            ? aboutChannelPrompt.focus_areas.map((s) => String(s)).filter(Boolean)
            : []
    );
    const aboutBugReportSteps = $derived(
        Array.isArray(aboutChannelPrompt.bug_report_steps)
            ? aboutChannelPrompt.bug_report_steps.map((s) => String(s)).filter(Boolean)
            : []
    );
    const aboutBugReportTarget = $derived(channelBugReportTarget(aboutChannelPrompt));
    const aboutChannelNotes = $derived(
        typeof aboutChannelPrompt.notes === "string" ? aboutChannelPrompt.notes.trim() : ""
    );

    const totalDatabaseBytes = $derived(
        (appInfo?.database_files ? appInfo.database_files.total_bytes : appInfo?.database_file_size) || 0
    );

    function showTutorial(): void {
        GlobalEmitter.emit("show-tutorial");
    }

    function showChangelog(): void {
        GlobalEmitter.emit("show-changelog");
    }

    async function onAboutBugReportAction(): Promise<void> {
        if (!aboutBugReportTarget.value) return;
        try {
            await navigator.clipboard.writeText(aboutBugReportTarget.value);
            ToastUtils.success(
                aboutBugReportTarget.kind === "lxmf" ? t("channel_prompt.lxmf_copied") : t("channel_prompt.url_copied")
            );
        } catch {
            ToastUtils.error(
                aboutBugReportTarget.kind === "lxmf"
                    ? t("channel_prompt.lxmf_copy_failed")
                    : t("channel_prompt.url_copy_failed")
            );
        }
    }
</script>

{#if appInfo}
    <div class="w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-6 sm:py-8 last:border-0">
        <div class="flex flex-col gap-8 lg:flex-row lg:items-center">
            <!-- Logo & Title -->
            <div class="flex items-center gap-6">
                <img src={logoUrl} class="h-20 w-20 shrink-0 object-contain" alt="" />
                <div class="space-y-1">
                    <div class="text-4xl font-black text-sem-fg leading-none tracking-tight">
                        {t("about.app_name")}
                    </div>
                    <div class="flex flex-col gap-0.5 sm:flex-row sm:flex-wrap sm:items-baseline sm:gap-x-3 sm:gap-y-0">
                        <div class="flex flex-wrap items-center gap-2">
                            <div class="text-sm font-black uppercase tracking-[0.2em] text-blue-500 opacity-80">
                                {t("about.version", { version: aboutDisplayVersion })}
                            </div>
                            {#if aboutChannelLabel}
                                <span
                                    class="inline-flex h-5 items-center rounded-xs px-2 text-[10px] font-black uppercase tracking-tighter {aboutChannelBadgeClass}"
                                    data-testid="about-channel-badge"
                                >
                                    {aboutChannelLabel}
                                </span>
                            {/if}
                        </div>
                        {#if appInfo.git_commit_short || appInfo.git_commit}
                            <div
                                class="text-xs font-medium normal-case tracking-normal font-mono text-sem-fg-muted"
                                title={appInfo.git_commit || appInfo.git_commit_short}
                            >
                                {t("about.git_commit", {
                                    commit: appInfo.git_commit_short || appInfo.git_commit,
                                })}
                            </div>
                        {/if}
                        {#if formattedUiBuildDate}
                            <div class="text-xs font-medium normal-case tracking-normal text-sem-fg-muted">
                                {t("about.ui_build", { date: formattedUiBuildDate })}
                            </div>
                        {/if}
                    </div>
                </div>
            </div>

            <!-- Action buttons -->
            <div class="grid w-full grid-cols-2 gap-2 sm:flex sm:w-auto sm:flex-1 sm:flex-wrap sm:justify-end sm:gap-3">
                <button
                    type="button"
                    class="min-w-0 min-h-[40px] justify-center whitespace-nowrap secondary-chip"
                    onclick={showTutorial}
                >
                    <MaterialDesignIcon iconName="help-circle" class="size-5 mr-2 shrink-0" />
                    <span class="truncate">{t("app.tutorial_title")}</span>
                </button>
                <button
                    type="button"
                    class="min-w-0 min-h-[40px] justify-center whitespace-nowrap secondary-chip"
                    onclick={showChangelog}
                >
                    <MaterialDesignIcon iconName="history" class="size-5 mr-2 shrink-0" />
                    <span class="truncate">{t("app.changelog_title")}</span>
                </button>
                <a
                    href="#/licenses"
                    class="min-w-0 min-h-[40px] justify-center whitespace-nowrap secondary-chip inline-flex items-center no-underline"
                >
                    <MaterialDesignIcon iconName="license" class="size-5 mr-2 shrink-0" />
                    <span class="truncate">{t("about.third_party_licenses")}</span>
                </a>
                {#if isElectron}
                    <button
                        type="button"
                        class="min-w-0 min-h-[40px] justify-center whitespace-nowrap primary-chip"
                        onclick={onrelaunch}
                    >
                        <MaterialDesignIcon iconName="restart" class="size-5 mr-2 shrink-0" />
                        <span class="truncate">{t("common.restart_app")}</span>
                    </button>
                {/if}
                <button
                    type="button"
                    class="min-w-0 min-h-[40px] justify-center whitespace-nowrap secondary-chip"
                    disabled={reloadingRns}
                    onclick={onreloadrns}
                >
                    <MaterialDesignIcon iconName="restart-alert" class="size-5 mr-2 shrink-0" />
                    <span class="truncate">
                        {reloadingRns ? t("app.reloading_rns") : t("app.restart_rns")}
                    </span>
                </button>
                <button
                    type="button"
                    class="min-w-0 min-h-[40px] justify-center whitespace-nowrap danger-chip"
                    onclick={onshutdown}
                >
                    <MaterialDesignIcon iconName="power" class="size-5 mr-2 shrink-0" />
                    <span class="truncate">{t("common.shutdown")}</span>
                </button>
            </div>
        </div>

        <!-- Channel prompt box -->
        {#if aboutShowChannelPromptDetails}
            <div
                class="mt-8 rounded-xl border border-sem-border bg-sem-surface px-4 py-4 space-y-4"
                data-testid="about-channel-prompt"
            >
                {#if aboutChannelNotes}
                    <p class="text-sm text-sem-fg">{aboutChannelNotes}</p>
                {/if}
                {#if aboutFocusAreas.length}
                    <div class="space-y-2">
                        <div class="text-xs font-semibold uppercase tracking-wide text-sem-fg">
                            {t("about.channel_focus_title")}
                        </div>
                        <ul class="list-disc space-y-1 pl-5 text-sm text-sem-fg-muted">
                            {#each aboutFocusAreas as area, idx (`about-focus-${idx}`)}
                                <li>{area}</li>
                            {/each}
                        </ul>
                    </div>
                {/if}
                <div class="space-y-2">
                    <div class="text-xs font-semibold uppercase tracking-wide text-sem-fg">
                        {t("about.channel_bug_report_title")}
                    </div>
                    <ol class="list-decimal space-y-1 pl-5 text-sm text-sem-fg-muted">
                        {#each aboutBugReportSteps as step, idx (`about-step-${idx}`)}
                            <li>{step}</li>
                        {/each}
                    </ol>
                    {#if aboutBugReportTarget.value}
                        <p class="break-all font-mono text-xs text-sem-fg-secondary">
                            {#if aboutBugReportTarget.kind === "lxmf"}
                                {t("channel_prompt.lxmf_label")}
                            {/if}
                            {aboutBugReportTarget.value}
                        </p>
                        <button
                            type="button"
                            class="min-w-0 min-h-[40px] justify-center whitespace-nowrap secondary-chip"
                            onclick={onAboutBugReportAction}
                        >
                            {aboutBugReportTarget.kind === "lxmf"
                                ? t("channel_prompt.copy_lxmf")
                                : t("channel_prompt.copy_url")}
                        </button>
                    {/if}
                </div>
            </div>
        {/if}

        <div class="mt-10 pt-8 border-t border-sem-border flex flex-col gap-6">
            <div class="text-sem-fg-muted max-w-xl text-lg leading-relaxed">
                {t("about.tagline_lead")}
                <a
                    href="https://reticulum.network"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="text-blue-500 font-black hover:underline decoration-2 underline-offset-4"
                >
                    {t("about.tagline_link")}
                </a>
                {t("about.tagline_after")}
            </div>

            <!-- Database size summary -->
            <div class="flex items-center gap-6 shrink-0">
                <div class="text-right">
                    <div class="text-[10px] font-black text-sem-fg-muted uppercase tracking-[0.2em] leading-none mb-1">
                        {t("about.database_size")}
                    </div>
                    <div class="text-2xl font-black text-sem-fg tabular-nums">
                        {Utils.formatBytes(totalDatabaseBytes)}
                    </div>
                </div>
            </div>
        </div>
    </div>
{/if}
