<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { formatInt, copyText, extractQueueRows, filterI2pInterfaces, hasStatusSummary } from "../lib/statusFormat.js";
    import type { RNStatusResponse } from "../lib/types.js";

    interface Props {
        statusData: RNStatusResponse;
    }

    let { statusData }: Props = $props();

    const linkCount = $derived(statusData.link_count ?? null);
    const activeLinkCount = $derived(statusData.active_link_count ?? null);
    const rnsVersion = $derived(statusData.rns_version || "");
    const transportUptimeStr = $derived(statusData.transport_uptime_str || "");
    const totals = $derived(statusData.totals || null);
    const totalsAnnounces = $derived(statusData.totals?.announces || null);
    const totalsPathRequests = $derived(statusData.totals?.path_requests || null);
    const blackholeEnabled = $derived(statusData.blackhole_enabled ?? null);
    const blackholeCount = $derived(statusData.blackhole_count || 0);
    const blackholeSources = $derived(statusData.blackhole_sources || []);
    const rssStr = $derived(statusData.rss_str || "");
    const transportId = $derived(statusData.transport_id || "");
    const networkId = $derived(statusData.network_id || "");
    const probeResponder = $derived(statusData.probe_responder || "");

    const showSummary = $derived(hasStatusSummary(statusData));
    const queueRows = $derived(extractQueueRows(statusData.queues));
    const i2pInterfaces = $derived(filterI2pInterfaces(statusData.interfaces || []));
</script>

{#if showSummary}
    <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {#if linkCount !== null}
            <div class="rounded-xl border border-sem-border bg-sem-surface p-4">
                <div class="text-xs uppercase tracking-wide text-sem-fg-muted">
                    {t("rnstatus.active_links_label")}
                </div>
                <div class="mt-1 text-2xl font-semibold tabular-nums text-sem-fg">
                    {formatInt(linkCount)}
                </div>
                {#if activeLinkCount !== null}
                    <div class="text-xs text-sem-fg-muted tabular-nums">
                        {t("rnstatus.active_links_detail", {
                            active: formatInt(activeLinkCount),
                            total: formatInt(linkCount),
                        })}
                    </div>
                {/if}
            </div>
        {/if}

        {#if rnsVersion}
            <div class="rounded-xl border border-sem-border bg-sem-surface p-4">
                <div class="text-xs uppercase tracking-wide text-sem-fg-muted">
                    {t("rnstatus.rns_version")}
                </div>
                <div class="mt-1 text-lg font-semibold text-sem-fg">
                    {rnsVersion}
                </div>
            </div>
        {/if}

        {#if transportUptimeStr}
            <div class="rounded-xl border border-sem-border bg-sem-surface p-4">
                <div class="text-xs uppercase tracking-wide text-sem-fg-muted">
                    {t("rnstatus.uptime")}
                </div>
                <div class="mt-1 text-lg font-semibold text-sem-fg">
                    {transportUptimeStr}
                </div>
            </div>
        {/if}

        {#if totals}
            <div class="rounded-xl border border-sem-border bg-sem-surface p-4">
                <div class="text-xs uppercase tracking-wide text-sem-fg-muted">
                    {t("rnstatus.totals")}
                </div>
                <div class="mt-1 text-sm font-semibold tabular-nums text-sem-fg">
                    <div>TX: {totals.tx_bytes_str} {totals.tx_speed_str}</div>
                    <div>RX: {totals.rx_bytes_str} {totals.rx_speed_str}</div>
                </div>
            </div>
        {/if}

        {#if blackholeEnabled !== null}
            <div class="rounded-xl border border-sem-border bg-sem-surface p-4">
                <div class="text-xs uppercase tracking-wide text-sem-fg-muted">
                    {t("rnstatus.blackhole_heading")}
                </div>
                <div class="mt-1 text-lg font-semibold text-sem-fg">
                    {blackholeEnabled ? t("rnstatus.blackhole_publishing") : t("rnstatus.blackhole_inactive")}
                </div>
                <div class="text-xs text-sem-fg-muted tabular-nums">
                    {t("rnstatus.blackhole_identities", { count: formatInt(blackholeCount) })}
                </div>
            </div>
        {/if}

        {#if rssStr}
            <div class="rounded-xl border border-sem-border bg-sem-surface p-4">
                <div class="text-xs uppercase tracking-wide text-sem-fg-muted">
                    {t("rnstatus.memory_rss")}
                </div>
                <div class="mt-1 text-lg font-semibold text-sem-fg">
                    {rssStr}
                </div>
            </div>
        {/if}
    </div>
{/if}

{#if totalsAnnounces || totalsPathRequests}
    <div class="grid gap-3 lg:grid-cols-2">
        {#if totalsAnnounces}
            <div class="rounded-xl border border-sem-border bg-sem-surface p-4 space-y-2">
                <h2 class="text-sm font-semibold text-sem-fg">
                    {t("rnstatus.transport_announces")}
                </h2>
                <div class="text-sm tabular-nums text-sem-fg">
                    <div>TX: {totalsAnnounces.tx_bytes_str} {totalsAnnounces.tx_speed_str}</div>
                    <div>RX: {totalsAnnounces.rx_bytes_str} {totalsAnnounces.rx_speed_str}</div>
                </div>
            </div>
        {/if}
        {#if totalsPathRequests}
            <div class="rounded-xl border border-sem-border bg-sem-surface p-4 space-y-2">
                <h2 class="text-sm font-semibold text-sem-fg">
                    {t("rnstatus.transport_path_requests")}
                </h2>
                <div class="text-sm tabular-nums text-sem-fg">
                    <div>TX: {totalsPathRequests.tx_bytes_str} {totalsPathRequests.tx_speed_str}</div>
                    <div>RX: {totalsPathRequests.rx_bytes_str} {totalsPathRequests.rx_speed_str}</div>
                </div>
            </div>
        {/if}
    </div>
{/if}

{#if queueRows.length > 0}
    <div class="rounded-xl border border-sem-border bg-sem-surface p-4 space-y-3">
        <h2 class="text-sm font-semibold text-sem-fg">
            {t("rnstatus.queue_pressure")}
        </h2>
        <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {#each queueRows as queue (queue.key)}
                <div class="rounded-lg border border-sem-border bg-sem-canvas p-3">
                    <div class="text-xs font-semibold uppercase tracking-wide text-sem-fg-muted">
                        {queue.label}
                    </div>
                    <div class="mt-1 text-sm font-semibold text-sem-fg">
                        {queue.pressure || "-"}
                    </div>
                    <div class="text-xs text-sem-fg-muted">
                        {#if queue.packets}
                            <span>{t("rnstatus.queue_packets", { count: queue.packets })}</span>
                        {/if}
                        {#if queue.dropped}
                            <span class="ml-2">{t("rnstatus.queue_dropped", { count: queue.dropped })}</span>
                        {/if}
                    </div>
                </div>
            {/each}
        </div>
    </div>
{/if}

{#if transportId || networkId || probeResponder}
    <div class="rounded-xl border border-sem-border bg-sem-surface p-4 space-y-3">
        <h2 class="text-sm font-semibold text-sem-fg">
            {t("rnstatus.transport_instance")}
        </h2>
        <div class="grid gap-3 md:grid-cols-2">
            {#if transportId}
                <div class="address-card">
                    <div class="address-card__label">{t("rnstatus.transport_id")}</div>
                    <div class="address-card__value monospace-field">{transportId}</div>
                    <button type="button" class="address-card__action" onclick={() => copyText(transportId)}>
                        <MaterialDesignIcon iconName="content-copy" class="w-3.5 h-3.5" />
                        {t("common.copy")}
                    </button>
                </div>
            {/if}
            {#if networkId}
                <div class="address-card">
                    <div class="address-card__label">{t("rnstatus.network_id")}</div>
                    <div class="address-card__value monospace-field">{networkId}</div>
                    <button type="button" class="address-card__action" onclick={() => copyText(networkId)}>
                        <MaterialDesignIcon iconName="content-copy" class="w-3.5 h-3.5" />
                        {t("common.copy")}
                    </button>
                </div>
            {/if}
            {#if probeResponder}
                <div class="address-card">
                    <div class="address-card__label">{t("rnstatus.probe_responder")}</div>
                    <div class="address-card__value monospace-field">{probeResponder}</div>
                    <button type="button" class="address-card__action" onclick={() => copyText(probeResponder)}>
                        <MaterialDesignIcon iconName="content-copy" class="w-3.5 h-3.5" />
                        {t("common.copy")}
                    </button>
                </div>
            {/if}
        </div>
    </div>
{/if}

{#if i2pInterfaces.length > 0}
    <div class="rounded-xl border border-violet-200 dark:border-violet-900/60 bg-violet-50 dark:bg-violet-950/30 p-4 space-y-3">
        <h2 class="text-sm font-semibold text-violet-950 dark:text-violet-100">
            {t("rnstatus.i2p_address")}
        </h2>
        {#each i2pInterfaces as iface (`i2p-${iface.name}`)}
            <div class="space-y-2">
                <div class="text-xs text-violet-800 dark:text-violet-200">{iface.name}</div>
                {#if iface.i2p_b32}
                    <div class="address-card">
                        <div class="address-card__label">{t("rnstatus.i2p_address")}</div>
                        <div class="address-card__value monospace-field">{iface.i2p_b32}</div>
                        <button type="button" class="address-card__action" onclick={() => copyText(iface.i2p_b32)}>
                            <MaterialDesignIcon iconName="content-copy" class="w-3.5 h-3.5" />
                            {t("common.copy")}
                        </button>
                    </div>
                {:else if iface.i2p_connectable}
                    <p class="text-sm text-violet-900 dark:text-violet-100">
                        {t("rnstatus.i2p_waiting")}
                    </p>
                {:else}
                    <p class="text-sm text-violet-900 dark:text-violet-100">
                        {t("rnstatus.i2p_not_published")}
                    </p>
                {/if}
                <div class="flex flex-wrap gap-2 text-xs">
                    <span
                        class="rounded-full px-2 py-0.5 font-medium {iface.i2p_connectable
                            ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-100'
                            : 'bg-gray-200 text-gray-700 dark:bg-zinc-800 text-sem-fg'}"
                    >
                        {iface.i2p_connectable ? t("rnstatus.i2p_connectable_yes") : t("rnstatus.i2p_connectable_no")}
                    </span>
                    {#if iface.i2p_tunnel_state}
                        <span class="rounded-full bg-white/70 dark:bg-zinc-900/70 px-2 py-0.5 font-medium text-violet-900 dark:text-violet-100">
                            {iface.i2p_tunnel_state}
                        </span>
                    {/if}
                </div>
            </div>
        {/each}
    </div>
{/if}

{#if blackholeSources.length > 0}
    <div class="rounded-xl border border-sem-border bg-sem-surface p-4 space-y-3">
        <h2 class="text-sm font-semibold text-sem-fg">
            {t("rnstatus.blackhole_sources")}
        </h2>
        <div class="divide-y divide-gray-100 dark:divide-zinc-800/50">
            {#each blackholeSources as source (source)}
                <div class="py-2 text-sm font-mono text-sem-fg truncate">
                    {source}
                </div>
            {/each}
        </div>
    </div>
{/if}
