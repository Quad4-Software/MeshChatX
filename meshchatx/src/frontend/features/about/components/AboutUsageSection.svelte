<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Utils from "../../../js/Utils.js";
    import {
        appBatteryUsageToneClass,
        batteryStatusIconName,
        formatAppBatteryShareLabel,
        formatAppBatteryUsageLabel,
        formatProcessUptime,
        isNativeBatteryStatus,
    } from "../../../js/deviceBattery.js";
    import { t } from "../../../js/i18n.js";
    import { mergeResourceBreakdown, topResourceByCpu, topResourceByRss } from "../../../js/resourceBreakdown.js";
    import { activeBatterySaverMeasures } from "../../../js/settings/batterySaverPrefs.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import {
        batteryStatusLabel as formatBatteryStatusLabel,
        batteryStatusToneClass as formatBatteryStatusToneClass,
        formatCpuPercent,
        formatMemoryPressure,
        formatPathTableSize,
        memoryPressureToneClass,
    } from "../lib/aboutFormat.js";
    import type { AppInfo } from "../lib/types.js";
    import type { DeviceBatteryStatus } from "../../../js/deviceBattery.js";
    import type { BatterySaverPrefs } from "../../../js/settings/batterySaverPrefs.js";

    interface Props {
        appInfo?: AppInfo | null;
        batterySaverPrefs?: BatterySaverPrefs | null;
        batteryStatus?: DeviceBatteryStatus | null;
        electronMemoryUsage?: unknown;
    }

    let {
        appInfo = null,
        batterySaverPrefs = null,
        batteryStatus = null,
        electronMemoryUsage = null,
    }: Props = $props();

    const batterySaverActive = $derived(Boolean(batterySaverPrefs?.enabled));
    const batterySaverMeasures = $derived(activeBatterySaverMeasures(batterySaverPrefs));

    const resourceBreakdownRows = $derived(mergeResourceBreakdown(appInfo?.resource_breakdown, electronMemoryUsage));

    const topMemoryConsumerLabel = $derived.by(() => {
        const top = topResourceByRss(resourceBreakdownRows);
        if (!top) return "";
        return `${top.name} (${Utils.formatBytes(top.rss || 0)})`;
    });

    const topCpuConsumerLabel = $derived.by(() => {
        const top = topResourceByCpu(resourceBreakdownRows);
        if (!top) return "";
        return `${top.name} (${formatCpuPercent(top.cpu_percent)})`;
    });

    const batteryUsageLabel = $derived(
        formatAppBatteryUsageLabel(appInfo?.battery_usage, (key, values) => t(key, values))
    );
    const batteryUsageShareLabel = $derived(
        formatAppBatteryShareLabel(appInfo?.battery_usage, (key, values) => t(key, values))
    );
    const batteryUsageTone = $derived(appBatteryUsageToneClass(appInfo?.battery_usage));

    const processUptimeLabel = $derived(formatProcessUptime(appInfo?.memory_usage?.create_time));
    const pathTableSizeLabel = $derived(formatPathTableSize(appInfo?.reticulum_stats));
    const memoryPressureText = $derived(formatMemoryPressure(appInfo?.reticulum_stats));
    const memoryPressureTone = $derived(memoryPressureToneClass(appInfo?.reticulum_stats));

    const showHostBattery = $derived(isNativeBatteryStatus(batteryStatus));
    const hostBatteryLabel = $derived(formatBatteryStatusLabel(batteryStatus));
    const hostBatteryToneClass = $derived(formatBatteryStatusToneClass(batteryStatus));
    const hostBatteryIcon = $derived(batteryStatusIconName(batteryStatus));

    const shouldShow = $derived(
        Boolean(appInfo && (appInfo.memory_usage || appInfo.battery_usage || showHostBattery || batterySaverPrefs))
    );
</script>

{#if shouldShow}
    <div class="w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-6 sm:py-8 last:border-0">
        <div class="text-xs font-black text-cyan-600 uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
            <MaterialDesignIcon iconName="gauge" class="size-3.5" />
            {t("about.usage_insights")}
        </div>
        <div
            class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 text-sm min-w-0 rounded-xl border border-gray-200/60 dark:border-zinc-800/80 p-4 sm:bg-black/2 dark:sm:bg-white/2"
        >
            {#if batterySaverPrefs}
                <div class="flex items-center justify-between gap-3 sm:col-span-2 lg:col-span-3">
                    <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">
                        {t("about.battery_saver")}
                    </span>
                    <span
                        class="font-mono text-xs font-bold tabular-nums shrink-0 {batterySaverActive
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'opacity-70'}"
                    >
                        {batterySaverActive ? t("about.battery_saver_on") : t("about.battery_saver_off")}
                    </span>
                </div>
            {/if}

            {#if batterySaverMeasures.length}
                <div class="sm:col-span-2 lg:col-span-3 space-y-1.5">
                    <div class="text-[10px] font-semibold uppercase tracking-wider opacity-70">
                        {t("about.battery_saver_measures")}
                    </div>
                    <ul
                        class="text-xs grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 list-disc list-inside opacity-90 p-0 m-0"
                    >
                        {#each batterySaverMeasures as measure (measure)}
                            <li>{t(`about.battery_saver_measure.${measure}`)}</li>
                        {/each}
                    </ul>
                </div>
            {/if}

            {#if topMemoryConsumerLabel}
                <div class="flex items-center justify-between gap-3">
                    <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">
                        {t("about.top_memory_consumer")}
                    </span>
                    <span
                        class="font-mono text-xs font-bold tabular-nums text-right shrink-0 max-w-[70%]"
                        title={topMemoryConsumerLabel}
                    >
                        {topMemoryConsumerLabel}
                    </span>
                </div>
            {/if}

            {#if topCpuConsumerLabel}
                <div class="flex items-center justify-between gap-3">
                    <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">
                        {t("about.top_cpu_consumer")}
                    </span>
                    <span
                        class="font-mono text-xs font-bold tabular-nums text-right shrink-0 max-w-[70%]"
                        title={topCpuConsumerLabel}
                    >
                        {topCpuConsumerLabel}
                    </span>
                </div>
            {/if}

            {#if batteryUsageLabel}
                <div class="flex items-center justify-between gap-3">
                    <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">
                        {t("about.app_battery_use")}
                    </span>
                    <span
                        class="font-mono text-xs font-bold tabular-nums shrink-0 {batteryUsageTone}"
                        title={t("about.app_battery_use_hint")}
                    >
                        {batteryUsageLabel}
                    </span>
                </div>
            {/if}

            {#if batteryUsageShareLabel}
                <div class="flex items-center justify-between gap-3">
                    <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">
                        {t("about.app_battery_share")}
                    </span>
                    <span class="font-mono text-xs font-bold tabular-nums">
                        {batteryUsageShareLabel}
                    </span>
                </div>
            {/if}

            {#if appInfo?.memory_usage}
                <div class="flex items-center justify-between gap-3">
                    <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">
                        {t("about.memory_rss")}
                    </span>
                    <span class="font-mono text-xs font-bold tabular-nums">
                        {Utils.formatBytes(appInfo.memory_usage.rss || 0)}
                    </span>
                </div>
                <div class="flex items-center justify-between gap-3">
                    <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">
                        {t("about.virtual_memory")}
                    </span>
                    <span class="font-mono text-xs font-bold tabular-nums">
                        {Utils.formatBytes(appInfo.memory_usage.vms || 0)}
                    </span>
                </div>
                {#if appInfo.memory_usage.cpu_percent != null}
                    <div class="flex items-center justify-between gap-3">
                        <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">
                            {t("about.process_cpu")}
                        </span>
                        <span class="font-mono text-xs font-bold tabular-nums">
                            {formatCpuPercent(appInfo.memory_usage.cpu_percent)}
                        </span>
                    </div>
                {/if}
                {#if appInfo.memory_usage.num_threads != null}
                    <div class="flex items-center justify-between gap-3">
                        <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">
                            {t("about.process_threads")}
                        </span>
                        <span class="font-mono text-xs font-bold tabular-nums">
                            {appInfo.memory_usage.num_threads}
                        </span>
                    </div>
                {/if}
            {/if}

            {#if processUptimeLabel}
                <div class="flex items-center justify-between gap-3">
                    <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">
                        {t("about.process_uptime")}
                    </span>
                    <span class="font-mono text-xs font-bold tabular-nums">{processUptimeLabel}</span>
                </div>
            {/if}

            {#if pathTableSizeLabel}
                <div class="flex items-center justify-between gap-3">
                    <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">
                        {t("about.path_table")}
                    </span>
                    <span class="font-mono text-xs font-bold tabular-nums">{pathTableSizeLabel}</span>
                </div>
            {/if}

            {#if memoryPressureText}
                <div class="flex items-center justify-between gap-3">
                    <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">
                        {t("about.memory_pressure")}
                    </span>
                    <span class="font-mono text-xs font-bold tabular-nums {memoryPressureTone}">
                        {memoryPressureText}
                    </span>
                </div>
            {/if}

            {#if showHostBattery}
                <div class="flex items-center justify-between gap-3">
                    <span class="text-[10px] font-semibold uppercase tracking-wider opacity-70">
                        {t("about.env_host_battery")}
                    </span>
                    <span
                        class="font-mono text-xs font-bold shrink-0 inline-flex items-center gap-1 {hostBatteryToneClass}"
                    >
                        <MaterialDesignIcon iconName={hostBatteryIcon} class="size-3.5" />
                        {hostBatteryLabel}
                    </span>
                </div>
            {/if}
        </div>
    </div>
{/if}
