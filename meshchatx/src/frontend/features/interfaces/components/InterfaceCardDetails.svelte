<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import { formatFrequency } from "../lib/interfacesFormat.js";
    import type { ConfiguredInterface } from "../lib/types.js";

    interface Props {
        iface: ConfiguredInterface;
    }

    let { iface }: Props = $props();
</script>

{#if ["UDPInterface", "RNodeInterface"].includes(iface.type)}
    <div class="mt-4 grid gap-2 text-sm text-gray-700 dark:text-gray-300">
        {#if iface.type === "UDPInterface"}
            <div class="detail-grid">
                <div>
                    <div class="detail-label">{t("interface.listen")}</div>
                    <div class="detail-value min-w-0 break-all">{iface.listen_ip}:{iface.listen_port}</div>
                </div>
                <div>
                    <div class="detail-label">{t("interface.forward")}</div>
                    <div class="detail-value min-w-0 break-all">{iface.forward_ip}:{iface.forward_port}</div>
                </div>
            </div>
        {:else if iface.type === "RNodeInterface"}
            <div class="detail-grid">
                <div>
                    <div class="detail-label">{t("interface.port")}</div>
                    <div class="detail-value min-w-0 break-all">{iface.port}</div>
                </div>
                <div>
                    <div class="detail-label">{t("interface.frequency")}</div>
                    <div class="detail-value min-w-0 break-all">{formatFrequency(iface.frequency)}</div>
                </div>
                <div>
                    <div class="detail-label">{t("interface.bandwidth")}</div>
                    <div class="detail-value min-w-0 break-all">{formatFrequency(iface.bandwidth)}</div>
                </div>
                <div>
                    <div class="detail-label">{t("interface.spreading_factor")}</div>
                    <div class="detail-value min-w-0 break-all">{iface.spreadingfactor}</div>
                </div>
                <div>
                    <div class="detail-label">{t("interface.coding_rate")}</div>
                    <div class="detail-value min-w-0 break-all">{iface.codingrate}</div>
                </div>
                <div>
                    <div class="detail-label">{t("interface.txpower")}</div>
                    <div class="detail-value min-w-0 break-all">{iface.txpower} dBm</div>
                </div>
            </div>
        {/if}
    </div>
{/if}

<style>
    .detail-grid {
        display: grid;
        gap: 0.75rem;
    }
    @media (min-width: 640px) {
        .detail-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }
    .detail-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--sem-fg-muted, #6b7280);
    }
    .detail-value {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--sem-fg, #111827);
        min-width: 0;
        word-break: break-all;
    }
</style>
