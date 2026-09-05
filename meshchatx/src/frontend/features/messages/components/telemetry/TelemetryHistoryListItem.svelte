<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../../js/i18n.js";

    type TelemetryLocation = {
        latitude: number;
        longitude: number;
        [key: string]: unknown;
    };

    type TelemetryData = {
        location?: TelemetryLocation | null;
        battery?: { charge_percent?: number | null; [key: string]: unknown } | null;
        physical_link?: { snr?: number | null; [key: string]: unknown } | null;
        [key: string]: unknown;
    };

    export type TelemetryHistoryItem = {
        is_outbound?: boolean;
        lxmf_message: {
            hash: string;
            created_at?: unknown;
            timestamp?: number;
            fields?: {
                telemetry?: TelemetryData | null;
                commands?: Array<Record<string, unknown>> | null;
                [key: string]: unknown;
            } | null;
            [key: string]: unknown;
        };
        [key: string]: unknown;
    };

    let {
        item,
        formatTimeAgo,
        onlocationclick,
    }: {
        item: TelemetryHistoryItem;
        formatTimeAgo: (value: unknown) => string;
        onlocationclick?: (location: TelemetryLocation) => void;
    } = $props();

    const telemetry = $derived(item.lxmf_message.fields?.telemetry);
    const location = $derived(telemetry?.location);
    const hasLocationRequest = $derived(
        item.lxmf_message.fields?.commands?.some((command) => Boolean(command["0x01"])) ?? false
    );
</script>

<div class="p-3 rounded-xl border border-sem-border bg-gray-50/50 dark:bg-zinc-900/30">
    <div class="flex justify-between items-start mb-2">
        <span
            class="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-sm bg-gray-200 dark:bg-zinc-800 text-sem-fg-muted"
        >
            {item.is_outbound ? t("messages.telemetry_label_sent") : t("messages.telemetry_label_received")}
        </span>
        <span class="text-[10px] text-gray-400">{formatTimeAgo(item.lxmf_message.created_at)}</span>
    </div>

    {#if location}
        <div class="flex items-center gap-2 mb-2">
            <button
                type="button"
                class="flex items-center gap-2 text-xs font-mono text-sem-accent hover:underline"
                onclick={() => onlocationclick?.(location)}
            >
                <MaterialDesignIcon iconName="map-marker" class="size-4" />
                {location.latitude.toFixed(6)}, {location.longitude.toFixed(6)}
            </button>
        </div>
    {/if}

    {#if telemetry}
        <div class="flex flex-wrap gap-3 text-[10px] text-sem-fg-muted">
            {#if telemetry.battery}
                <span class="flex items-center gap-1">
                    <MaterialDesignIcon iconName="battery" class="size-3" />
                    {t("messages.telemetry_battery_level", {
                        percent: telemetry.battery.charge_percent,
                    })}
                </span>
            {/if}
            {#if telemetry.physical_link}
                <span class="flex items-center gap-1">
                    <MaterialDesignIcon iconName="antenna" class="size-3" />
                    {t("messages.telemetry_snr_db", { snr: telemetry.physical_link.snr })}
                </span>
            {/if}
        </div>
    {/if}

    {#if hasLocationRequest}
        <div class="flex items-center gap-2 text-[10px] text-emerald-600 dark:text-emerald-400 mt-1">
            <MaterialDesignIcon iconName="crosshairs-question" class="size-3" />
            <span>{t("messages.telemetry_location_request")}</span>
        </div>
    {/if}
</div>
