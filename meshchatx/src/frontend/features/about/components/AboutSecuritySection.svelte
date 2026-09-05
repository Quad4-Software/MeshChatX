<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import {
        listSandboxFeatures,
        sandboxSummaryActive as computeSandboxSummaryActive,
        sandboxSummaryType,
    } from "../../../js/sandboxStatus.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { sandboxBadgeClass, sandboxCardClass, sandboxIconClass, statusPillClass } from "../lib/aboutFormat.js";
    import type { AppInfo } from "../lib/types.js";

    interface Props {
        appInfo?: AppInfo | null;
        onacknowledge?: () => void;
    }

    let { appInfo = null, onacknowledge }: Props = $props();

    const sandboxFeatureCards = $derived(listSandboxFeatures(appInfo));
    const sandboxSummaryActive = $derived(computeSandboxSummaryActive(appInfo));
    const sandboxSummaryTypeKey = $derived(sandboxSummaryType(appInfo));
    const integrityIssues = $derived(Array.isArray(appInfo?.integrity_issues) ? appInfo.integrity_issues : []);
</script>

{#if appInfo}
    <div class="w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-6 sm:py-8 last:border-0 hidden sm:block">
        <div class="text-xs font-black text-blue-500 uppercase tracking-[0.2em] flex items-center gap-2 mb-6">
            <MaterialDesignIcon iconName="shield-search" class="size-3.5" />
            {t("about.security_integrity")}
        </div>

        <div class="mb-6 pb-6 border-b border-gray-200/60 dark:border-zinc-800/80 space-y-4">
            <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <div class="text-[10px] font-black text-sem-fg uppercase tracking-[0.2em] mb-2">
                        {t("about.integrity_monitoring_title")}
                    </div>
                    <p class="text-[11px] leading-relaxed text-sem-fg-muted">
                        {t("about.security_integrity_description")}
                    </p>
                </div>
                {#if Array.isArray(appInfo.integrity_issues)}
                    <div class="flex flex-wrap gap-2 shrink-0">
                        <span class="{statusPillClass(integrityIssues.length === 0)} font-black px-3 py-1 text-[11px]">
                            <MaterialDesignIcon
                                iconName={integrityIssues.length === 0 ? "shield-check" : "shield-alert"}
                                class="size-3.5 shrink-0 {integrityIssues.length === 0
                                    ? 'text-emerald-600 dark:text-emerald-400'
                                    : ''}"
                            />
                            {integrityIssues.length === 0 ? t("about.secured") : t("about.tampering_detected")}
                        </span>
                        {#if integrityIssues.length > 0}
                            <button
                                type="button"
                                class="secondary-chip px-3 py-1 text-[11px] font-black"
                                onclick={onacknowledge}
                            >
                                <MaterialDesignIcon iconName="check-circle" class="size-3.5 shrink-0" />
                                {t("common.acknowledge_reset")}
                            </button>
                        {/if}
                    </div>
                {/if}
            </div>

            {#if integrityIssues.length > 0}
                <div
                    class="p-4 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900 rounded-xl"
                >
                    <div
                        class="text-xs font-black text-amber-700 dark:text-amber-400 mb-3 uppercase tracking-wider flex items-center gap-2"
                    >
                        <MaterialDesignIcon iconName="alert" class="size-4" />
                        {t("about.technical_issues_detected")}
                    </div>
                    <ul class="text-[11px] text-amber-700 dark:text-amber-300 space-y-2 list-none font-mono">
                        {#each integrityIssues as issue, index (`issue-${index}`)}
                            <li class="flex gap-2">
                                <span class="opacity-50">•</span>
                                <span>{issue}</span>
                            </li>
                        {/each}
                    </ul>
                </div>
            {:else}
                <div
                    class="text-sm text-gray-700 dark:text-emerald-200 flex items-center gap-3 bg-emerald-500/10 dark:bg-emerald-900/30 p-4 rounded-xl border border-emerald-500/20 dark:border-emerald-500/30"
                >
                    <MaterialDesignIcon
                        iconName="check-decagram"
                        class="size-5 text-emerald-600 dark:text-emerald-400 shrink-0"
                    />
                    <span class="font-bold tracking-tight">{t("about.no_integrity_violations")}</span>
                </div>
            {/if}
        </div>

        <div class="space-y-4">
            <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <div class="text-[10px] font-black text-sem-fg uppercase tracking-[0.2em] mb-2">
                        {t("about.sandbox_title")}
                    </div>
                    <p class="text-[11px] leading-relaxed text-sem-fg-muted">
                        {t("about.sandbox_description")}
                    </p>
                </div>
                <span class="{statusPillClass(sandboxSummaryActive)} font-black px-3 py-1 text-[11px] shrink-0">
                    <MaterialDesignIcon
                        iconName={sandboxSummaryActive ? "shield-check" : "shield-off"}
                        class="size-3.5 shrink-0 {sandboxSummaryActive ? 'text-emerald-600 dark:text-emerald-400' : ''}"
                    />
                    {t(sandboxSummaryTypeKey)}
                </span>
            </div>

            <div class="grid grid-cols-1 gap-3 min-w-0">
                {#each sandboxFeatureCards as card (card.id)}
                    <div class="rounded-xl border p-3 min-w-0 {sandboxCardClass(card)}">
                        <div class="flex items-center gap-3 flex-wrap min-w-0">
                            <span
                                class="inline-flex items-center justify-center size-9 rounded-full border shrink-0 {sandboxIconClass(
                                    card
                                )}"
                            >
                                <MaterialDesignIcon
                                    iconName={card.active ? "shield-check" : "shield-off"}
                                    class="size-4"
                                />
                            </span>
                            <div class="flex-1 min-w-0">
                                <div class="text-sm font-bold text-sem-fg">
                                    {t(card.titleKey)}
                                </div>
                            </div>
                            <span
                                class="inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wider shrink-0 {sandboxBadgeClass(
                                    card
                                )}"
                            >
                                {t(card.badgeKey)}
                            </span>
                        </div>
                        <p
                            class="text-[11px] leading-relaxed text-sem-fg-muted mt-2 {card.active
                                ? 'text-emerald-700 dark:text-emerald-300'
                                : ''}"
                        >
                            {t(card.noteKey)}
                        </p>
                    </div>
                {/each}
            </div>
        </div>
    </div>
{/if}
