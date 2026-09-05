<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import fatalErrorState, { type FatalErrorRecord } from "../../js/fatalErrorState.js";
    import ToastUtils from "../../js/ToastUtils.js";
    import { t } from "../../js/i18n.js";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import { FATAL_ERROR_COPY_RESET_MS } from "./lib/constants.js";
    import {
        copyFatalErrorReport,
        reportFatalErrorLocally,
        resolveFatalErrorSummary,
    } from "./lib/fatalErrorActions.js";

    interface Props {
        error?: FatalErrorRecord | null;
        embedded?: boolean;
        router?: { push?: (target: { name: string }) => void };
    }

    let { error = null, embedded = false, router = undefined }: Props = $props();

    let copyLabel = $state(t("app.error_copy_details"));
    let reportLabel = $state(t("app.error_report_locally"));
    const headingId = `fatal-error-title-${Math.random().toString(36).slice(2, 9)}`;
    const messageId = `fatal-error-message-${Math.random().toString(36).slice(2, 9)}`;

    const effectiveError = $derived(error || fatalErrorState.active);
    const summary = $derived(
        resolveFatalErrorSummary(effectiveError, t("app.error_backend_title"), t("app.error_frontend_title"))
    );

    function onReload(): void {
        window.location.reload();
    }

    async function onReportLocal(): Promise<void> {
        const ok = await reportFatalErrorLocally(effectiveError, router);
        if (ok) {
            ToastUtils.success(t("app.error_report_saved"));
            reportLabel = t("app.error_report_saved");
        } else {
            ToastUtils.error(t("app.error_report_failed"));
        }
    }

    async function onCopy(): Promise<void> {
        const ok = await copyFatalErrorReport(effectiveError);
        if (ok) {
            ToastUtils.success(t("common.copied"));
            copyLabel = t("common.copied");
            window.setTimeout(() => {
                copyLabel = t("app.error_copy_details");
            }, FATAL_ERROR_COPY_RESET_MS);
        } else {
            ToastUtils.error(t("common.failed_to_copy"));
        }
    }
</script>

<div
    class="fatal-error-page flex min-h-dvh w-full flex-col items-center justify-center px-4 py-8 {embedded
        ? 'relative min-h-0 bg-transparent'
        : 'fixed inset-0 z-[500] bg-sem-canvas'}"
    role="alertdialog"
    aria-modal="true"
    aria-labelledby={headingId}
    aria-describedby={messageId}
    data-testid="fatal-error-page"
>
    <div class="modal-panel w-full max-w-lg p-6 sm:p-8">
        <div class="flex items-start gap-4">
            <div
                class="flex size-12 shrink-0 items-center justify-center rounded-2xl {summary.kind === 'backend'
                    ? 'bg-sem-warning/15 text-sem-warning'
                    : 'bg-sem-danger/15 text-sem-danger'}"
            >
                <MaterialDesignIcon
                    iconName={summary.kind === "backend" ? "server-off" : "alert-circle-outline"}
                    class="size-7"
                />
            </div>
            <div class="min-w-0 flex-1 space-y-2">
                <h1 id={headingId} class="text-xl font-bold text-sem-fg">
                    {summary.title}
                </h1>
                <p id={messageId} class="text-sm leading-relaxed text-sem-fg-muted">
                    {summary.message}
                </p>
            </div>
        </div>

        {#if summary.hasDetails}
            <details class="mt-5 rounded-xl border border-sem-border bg-sem-surface-muted">
                <summary class="cursor-pointer px-4 py-3 text-sm font-semibold text-sem-fg">
                    {t("app.error_details_heading")}
                </summary>
                <pre
                    class="max-h-48 overflow-auto border-t border-sem-border px-4 py-3 text-xs leading-relaxed text-sem-fg-secondary whitespace-pre-wrap wrap-break-word">{summary.detailBody}</pre>
            </details>
        {/if}

        <div class="mt-6 flex flex-wrap items-center gap-2">
            <button type="button" class="primary-chip" onclick={onReload}>
                <MaterialDesignIcon iconName="refresh" class="size-4" />
                {t("app.error_reload_page")}
            </button>
            <button type="button" class="secondary-chip" onclick={onReportLocal}>
                <MaterialDesignIcon iconName="bug-outline" class="size-4" />
                {reportLabel}
            </button>
            <button type="button" class="secondary-chip" onclick={onCopy}>
                <MaterialDesignIcon iconName="content-copy" class="size-4" />
                {copyLabel}
            </button>
        </div>
    </div>
</div>
