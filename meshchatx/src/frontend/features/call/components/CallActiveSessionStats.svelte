<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import type { ActiveCall } from "../lib/types.js";

    interface Props {
        activeCall?: Partial<ActiveCall> | null;
        formatNumber: (n?: number | null) => string;
        formatBytes: (bytes?: number | null) => string;
        formatBitrate: (bps?: number | null) => string;
    }

    let { activeCall = null, formatNumber, formatBytes, formatBitrate }: Props = $props();
</script>

<div class="mt-3 grid grid-cols-2 gap-2 text-xs w-full max-w-xs">
    <div class="rounded-xl bg-sem-surface-muted/50 border border-sem-border px-2 py-1.5 text-left">
        <div class="text-[10px] text-sem-fg-muted">{t("call.tx_packets")}</div>
        <div class="font-semibold text-sem-fg">{formatNumber(activeCall?.tx_packets)}</div>
    </div>
    <div class="rounded-xl bg-sem-surface-muted/50 border border-sem-border px-2 py-1.5 text-left">
        <div class="text-[10px] text-sem-fg-muted">{t("call.rx_packets")}</div>
        <div class="font-semibold text-sem-fg">{formatNumber(activeCall?.rx_packets)}</div>
    </div>
    <div class="rounded-xl bg-sem-surface-muted/50 border border-sem-border px-2 py-1.5 text-left">
        <div class="text-[10px] text-sem-fg-muted">{t("call.tx_data")}</div>
        <div class="font-semibold text-sem-fg">{formatBytes(activeCall?.tx_bytes)}</div>
    </div>
    <div class="rounded-xl bg-sem-surface-muted/50 border border-sem-border px-2 py-1.5 text-left">
        <div class="text-[10px] text-sem-fg-muted">{t("call.rx_data")}</div>
        <div class="font-semibold text-sem-fg">{formatBytes(activeCall?.rx_bytes)}</div>
    </div>
    <div class="rounded-xl bg-sem-surface-muted/50 border border-sem-border px-2 py-1.5 text-left">
        <div class="text-[10px] text-sem-fg-muted">{t("call.tx_rate")}</div>
        <div class="font-semibold text-sem-fg">{formatBitrate(activeCall?.tx_bps)}</div>
    </div>
    <div class="rounded-xl bg-sem-surface-muted/50 border border-sem-border px-2 py-1.5 text-left">
        <div class="text-[10px] text-sem-fg-muted">{t("call.rx_rate")}</div>
        <div class="font-semibold text-sem-fg">{formatBitrate(activeCall?.rx_bps)}</div>
    </div>
</div>
