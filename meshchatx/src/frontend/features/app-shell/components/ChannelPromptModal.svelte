<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import AppUpdatePrompt from "./AppUpdatePrompt.svelte";
    import ToastUtils from "../../../js/ToastUtils.js";
    import {
        channelBugReportTarget,
        channelLabelKey,
        channelPromptSeenKey,
        normalizeReleaseChannel,
        shouldShowChannelPrompt,
    } from "../../../js/releaseChannel.js";

    interface AppInfo {
        build_channel?: string;
        channel_prompt?: {
            notes?: string;
            focus_areas?: string[];
            bug_report_steps?: string[];
            bug_report_target?: unknown;
        };
        channel_prompt_seen?: string;
    }

    interface Props {
        open?: boolean;
    }

    let { open = $bindable(false) }: Props = $props();

    let appInfo = $state<AppInfo | null>(null);
    let sourceInfo: AppInfo | null = null;

    const channel = $derived(normalizeReleaseChannel(appInfo?.build_channel));

    const titleText = $derived.by(() => {
        const label = t(channelLabelKey(channel));
        return t("channel_prompt.title", { channel: label });
    });

    const introText = $derived.by(() => {
        const label = t(channelLabelKey(channel));
        return t("channel_prompt.intro", { channel: label });
    });

    const prompt = $derived.by(() => {
        const p = appInfo?.channel_prompt;
        return p && typeof p === "object" ? p : {};
    });

    const notes = $derived.by(() => {
        return typeof prompt.notes === "string" ? prompt.notes.trim() : "";
    });

    const focusAreas = $derived.by(() => {
        return Array.isArray(prompt.focus_areas) ? prompt.focus_areas.map((s) => String(s)).filter(Boolean) : [];
    });

    const bugReportSteps = $derived.by(() => {
        return Array.isArray(prompt.bug_report_steps)
            ? prompt.bug_report_steps.map((s) => String(s)).filter(Boolean)
            : [];
    });

    const reportTarget = $derived(channelBugReportTarget(prompt));

    const secondaryLabel = $derived.by(() => {
        if (!reportTarget.value) {
            return "";
        }
        if (reportTarget.kind === "lxmf") {
            return t("channel_prompt.copy_lxmf");
        }
        return t("channel_prompt.copy_url");
    });

    export function show(info: AppInfo): boolean {
        if (!shouldShowChannelPrompt(info)) {
            return false;
        }
        sourceInfo = info;
        appInfo = info;
        open = true;
        return true;
    }

    export async function onDismiss(): Promise<void> {
        await markSeen();
        open = false;
    }

    export async function onSecondary(): Promise<void> {
        if (!reportTarget.value) {
            return;
        }
        try {
            await navigator.clipboard.writeText(reportTarget.value);
            ToastUtils.success(
                reportTarget.kind === "lxmf" ? t("channel_prompt.lxmf_copied") : t("channel_prompt.url_copied")
            );
        } catch {
            ToastUtils.error(
                reportTarget.kind === "lxmf"
                    ? t("channel_prompt.lxmf_copy_failed")
                    : t("channel_prompt.url_copy_failed")
            );
        }
    }

    async function markSeen(): Promise<void> {
        if (!appInfo) {
            return;
        }
        const key = channelPromptSeenKey(appInfo);
        try {
            const api = (window as unknown as { api?: { post: (url: string, data?: unknown) => Promise<unknown> } })
                .api;
            if (api) {
                await api.post("/api/v1/app/channel-prompt/seen", { key });
            }
            if (sourceInfo) {
                sourceInfo.channel_prompt_seen = key;
            }
            if (appInfo) {
                appInfo.channel_prompt_seen = key;
            }
        } catch (e) {
            console.log(e);
        }
    }
</script>

<AppUpdatePrompt
    bind:open
    title={titleText}
    description={introText}
    primaryLabel={t("channel_prompt.dismiss")}
    {secondaryLabel}
    onprimary={onDismiss}
    onsecondary={onSecondary}
>
    {#if notes}
        <div class="rounded-md border border-sem-border bg-sem-canvas px-3 py-2 text-sem-fg">
            {notes}
        </div>
    {/if}

    {#if focusAreas.length > 0}
        <div class="space-y-2">
            <div class="text-xs font-semibold uppercase tracking-wide text-sem-fg">
                {t("channel_prompt.focus_title")}
            </div>
            <ul class="list-disc space-y-1 pl-5 text-sem-fg-muted">
                {#each focusAreas as area, idx (`focus-${idx}`)}
                    <li>{area}</li>
                {/each}
            </ul>
        </div>
    {/if}

    <div class="space-y-2">
        <div class="text-xs font-semibold uppercase tracking-wide text-sem-fg">
            {t("channel_prompt.bug_report_title")}
        </div>
        <ol class="list-decimal space-y-1 pl-5 text-sem-fg-muted">
            {#each bugReportSteps as step, idx (`step-${idx}`)}
                <li>{step}</li>
            {/each}
        </ol>
        {#if reportTarget.value}
            <p class="break-all font-mono text-xs text-sem-fg-secondary" data-testid="channel-prompt-bug-url">
                {#if reportTarget.kind === "lxmf"}
                    <span>{t("channel_prompt.lxmf_label")} </span>
                {/if}
                {reportTarget.value}
            </p>
        {/if}
    </div>
</AppUpdatePrompt>
