<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script lang="ts">
    import MaterialDesignIcon from "../../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../../js/i18n.js";
    import { batteryHistoryFromTelemetryItems } from "../../../../js/telemetryBatteryChartSpec.js";
    import TelemetryBatteryChart from "./TelemetryBatteryChart.svelte";
    import TelemetryHistoryListItem, { type TelemetryHistoryItem } from "./TelemetryHistoryListItem.svelte";

    type TelemetryLocation = {
        latitude: number;
        longitude: number;
        [key: string]: unknown;
    };

    let {
        open = false,
        telemetryItems = [],
        showTelemetryInChat = false,
        formatTimeAgo,
        gradientIdSuffix = "peer",
        onopenchange,
        onclose,
        onshowtelemetrychange,
        onlocationclick,
    }: {
        open?: boolean;
        telemetryItems?: TelemetryHistoryItem[];
        showTelemetryInChat?: boolean;
        formatTimeAgo: (value: unknown) => string;
        gradientIdSuffix?: string;
        onopenchange?: (open: boolean) => void;
        onclose?: () => void;
        onshowtelemetrychange?: (show: boolean) => void;
        onlocationclick?: (location: TelemetryLocation) => void;
    } = $props();

    const batteryHistory = $derived(batteryHistoryFromTelemetryItems(telemetryItems));
    const titleId = $derived(`telemetry-history-title-${gradientIdSuffix.replace(/[^a-zA-Z0-9_-]/g, "") || "peer"}`);

    function close() {
        onopenchange?.(false);
        onclose?.();
    }
</script>

<svelte:window
    onkeydown={(event) => {
        if (open && event.key === "Escape") close();
    }}
/>

{#if open}
    <div
        class="fixed inset-0 z-100 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs"
        onclick={(event) => {
            if (event.target === event.currentTarget) close();
        }}
        role="presentation"
    >
        <div
            class="w-full max-w-lg bg-sem-surface rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh]"
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
        >
            <div class="px-6 py-4 border-b border-sem-border flex items-center justify-between">
                <div class="flex items-center gap-2 min-w-0">
                    <MaterialDesignIcon iconName="satellite-variant" class="size-6 text-blue-500 shrink-0" />
                    <h3 id={titleId} class="text-lg font-bold text-sem-fg truncate">
                        {t("messages.telemetry_history_modal_title")}
                    </h3>
                </div>
                <button
                    type="button"
                    class="text-gray-400 hover:text-gray-500 dark:hover:text-zinc-300 transition-colors shrink-0"
                    title={t("common.close")}
                    onclick={close}
                >
                    <MaterialDesignIcon iconName="close" class="size-6" />
                </button>
            </div>
            <div class="flex-1 overflow-y-auto p-4 space-y-3">
                {#if telemetryItems.length === 0}
                    <div class="text-center py-8 text-sem-fg-muted">
                        {t("messages.telemetry_history_empty")}
                    </div>
                {:else}
                    {#each telemetryItems as item (item.lxmf_message.hash)}
                        <TelemetryHistoryListItem {item} {formatTimeAgo} {onlocationclick} />
                    {/each}
                {/if}
            </div>
            <div
                class="flex flex-col gap-3 border-t border-gray-100 bg-gray-50/40 px-6 py-4 dark:border-zinc-800 dark:bg-zinc-900/25"
            >
                {#if batteryHistory.length > 1}
                    <TelemetryBatteryChart samples={batteryHistory} idSuffix={gradientIdSuffix} />
                {/if}

                <div
                    class="flex w-full items-center justify-between gap-3 {batteryHistory.length > 1
                        ? 'border-t border-gray-200/80 pt-3 dark:border-zinc-700/80'
                        : ''}"
                >
                    <label class="flex items-center gap-2 cursor-pointer group min-w-0">
                        <input
                            checked={showTelemetryInChat}
                            type="checkbox"
                            class="rounded-sm border-gray-300 text-blue-600 focus:ring-blue-500 shrink-0"
                            onchange={(event) => onshowtelemetrychange?.(event.currentTarget.checked)}
                        />
                        <span
                            class="text-xs font-medium text-sem-fg-muted group-hover:text-gray-900 dark:group-hover:text-zinc-200"
                        >
                            {t("messages.telemetry_show_in_chat")}
                        </span>
                    </label>
                    <button
                        type="button"
                        class="px-4 py-2 bg-blue-600 text-white text-xs font-bold rounded-lg hover:bg-blue-700 transition-colors shadow-xs shrink-0"
                        onclick={close}
                    >
                        {t("messages.telemetry_history_done")}
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}
