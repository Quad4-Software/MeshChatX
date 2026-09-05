<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import {
        formatByteSize,
        formatDestinationHash,
        formatPathLabel,
        formatSeconds,
        formatStorageUsage,
    } from "../lib/propagationFormat.js";
    import type { NodePathInfo, PropagationNodeItem, PropagationNodesConfig } from "../lib/types.js";

    interface Props {
        config: PropagationNodesConfig;
        localPropagationNode: PropagationNodeItem | null;
        localNodeIsRunning: boolean;
        localNodeStatsVisible: boolean;
        localNodePath: NodePathInfo | null;
        isLocalManagerCollapsed: boolean;
        localNodeDisplayNameDraft: string;
        lxmfIncomingDeliveryPreset: string;
        lxmfIncomingDeliveryCustomAmount: number;
        lxmfIncomingDeliveryCustomUnit: string;
        propagationLimitInputMb: number;
        propagationSyncLimitInputMb: number;
        onToggleCollapse: () => void;
        onAnnounce: () => void;
        onStartNode: () => void;
        onRestartNode: () => void;
        onStopNode: () => void;
        onRequestLocalPath: () => void;
        onSaveDisplayName: () => void;
        onResetDisplayName: () => void;
        onIncomingPresetChange: (val: string) => void;
        onIncomingCustomAmountChange: (val: number) => void;
        onIncomingCustomUnitChange: (val: string) => void;
        onTransferLimitChange: (val: number) => void;
        onSyncLimitChange: (val: number) => void;
        onStampCostChange: (val: number) => void;
        onUseLocalNode: () => void;
    }

    let {
        config,
        localPropagationNode,
        localNodeIsRunning,
        localNodeStatsVisible,
        localNodePath,
        isLocalManagerCollapsed,
        localNodeDisplayNameDraft = $bindable(),
        lxmfIncomingDeliveryPreset = $bindable(),
        lxmfIncomingDeliveryCustomAmount = $bindable(),
        lxmfIncomingDeliveryCustomUnit = $bindable(),
        propagationLimitInputMb = $bindable(),
        propagationSyncLimitInputMb = $bindable(),
        onToggleCollapse,
        onAnnounce,
        onStartNode,
        onRestartNode,
        onStopNode,
        onRequestLocalPath,
        onSaveDisplayName,
        onResetDisplayName,
        onIncomingPresetChange,
        onIncomingCustomAmountChange,
        onIncomingCustomUnitChange,
        onTransferLimitChange,
        onSyncLimitChange,
        onStampCostChange,
        onUseLocalNode,
    }: Props = $props();
</script>

<div class="shrink-0 border-b border-sem-border">
    <div class="flex items-center gap-2 px-3 py-1.5 min-h-10">
        <button
            type="button"
            class="flex min-w-0 flex-1 items-center gap-2 text-left"
            data-testid="prop-nodes-hosted-toggle"
            onclick={onToggleCollapse}
        >
            <MaterialDesignIcon
                iconName={isLocalManagerCollapsed ? "chevron-right" : "chevron-down"}
                class="size-4 text-sem-fg-muted shrink-0"
            />
            <span class="text-sm font-medium truncate">{t("tools.propagation_nodes.hosted_heading")}</span>
            {#if localPropagationNode}
                <span
                    class="inline-flex items-center rounded-full px-1.5 py-0 text-[10px] font-semibold shrink-0 {localNodeIsRunning
                        ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                        : 'bg-sem-surface-muted text-sem-fg-muted'}"
                >
                    {localNodeIsRunning ? t("tools.propagation_nodes.running") : t("tools.propagation_nodes.stopped")}
                </span>
            {/if}
            {#if localPropagationNode && config.lxmf_preferred_propagation_node_destination_hash === localPropagationNode.destination_hash}
                <span
                    class="inline-flex items-center rounded-full bg-blue-100 dark:bg-blue-900/30 px-1.5 py-0 text-[10px] font-semibold text-blue-700 dark:text-blue-300 shrink-0"
                >
                    {t("tools.propagation_nodes.preferred_badge")}
                </span>
            {/if}
        </button>
        <div class="flex items-center gap-0.5 shrink-0">
            <button
                type="button"
                class="inline-flex size-8 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-sem-accent disabled:opacity-40"
                title={t("app.announce_now")}
                disabled={!localPropagationNode}
                onclick={onAnnounce}
            >
                <MaterialDesignIcon iconName="bullhorn" class="size-4" />
            </button>
            {#if !localNodeIsRunning}
                <button
                    type="button"
                    class="inline-flex size-8 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-emerald-600 disabled:opacity-40"
                    title={t("tools.propagation_nodes.start_node")}
                    disabled={!localPropagationNode}
                    onclick={onStartNode}
                >
                    <MaterialDesignIcon iconName="play" class="size-4" />
                </button>
            {/if}
            {#if localNodeIsRunning}
                <button
                    type="button"
                    class="inline-flex size-8 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-amber-600"
                    title={t("tools.propagation_nodes.restart_node")}
                    onclick={onRestartNode}
                >
                    <MaterialDesignIcon iconName="refresh" class="size-4" />
                </button>
                <button
                    type="button"
                    class="inline-flex size-8 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-red-600"
                    title={t("tools.propagation_nodes.stop_node")}
                    onclick={onStopNode}
                >
                    <MaterialDesignIcon iconName="stop" class="size-4" />
                </button>
            {/if}
        </div>
    </div>

    {#if !isLocalManagerCollapsed}
        <div data-testid="prop-nodes-hosted-expanded" class="px-3 pb-3 space-y-2 border-t border-sem-border">
            {#if config.lxmf_local_propagation_node_address_hash}
                <div class="pt-2 text-[11px] font-mono text-sem-fg-muted break-all">
                    {formatDestinationHash(config.lxmf_local_propagation_node_address_hash)}
                </div>
            {/if}
            <div class="text-[11px] text-sem-fg-muted flex items-center gap-2">
                <span>{formatPathLabel(localNodePath)}</span>
                <button
                    type="button"
                    class="inline-flex size-7 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-sem-accent disabled:opacity-40"
                    title={t("tools.propagation_nodes.find_path")}
                    disabled={!config.lxmf_local_propagation_node_address_hash}
                    onclick={onRequestLocalPath}
                >
                    <MaterialDesignIcon iconName="map-marker-path" class="size-4" />
                </button>
            </div>
            <label class="block text-[11px] text-sem-fg-muted">
                {t("tools.propagation_nodes.display_name")}
                <div class="mt-1 flex items-center gap-2">
                    <input
                        bind:value={localNodeDisplayNameDraft}
                        type="text"
                        maxlength={64}
                        class="input-field py-1.5 text-sm"
                        placeholder={t("tools.propagation_nodes.display_name")}
                        onkeydown={(e) => {
                            if (e.key === "Enter") {
                                e.preventDefault();
                                onSaveDisplayName();
                            }
                        }}
                    />
                    <button
                        type="button"
                        class="inline-flex size-8 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-emerald-600"
                        title={t("tools.propagation_nodes.save_name")}
                        onclick={onSaveDisplayName}
                    >
                        <MaterialDesignIcon iconName="check" class="size-4" />
                    </button>
                    <button
                        type="button"
                        class="inline-flex size-8 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted"
                        title={t("tools.propagation_nodes.reset_name")}
                        onclick={onResetDisplayName}
                    >
                        <MaterialDesignIcon iconName="restore" class="size-4" />
                    </button>
                </div>
            </label>

            {#if localNodeStatsVisible && localPropagationNode?.local_node_stats}
                <div class="text-[11px] text-sem-fg-muted flex flex-wrap gap-x-3 gap-y-0.5">
                    <span>
                        {t("tools.propagation_nodes.stats_uptime", {
                            time: formatSeconds(localPropagationNode.local_node_stats.uptime_seconds),
                        })}
                    </span>
                    <span>
                        {t("tools.propagation_nodes.stats_peers", {
                            count: localPropagationNode.local_node_stats.total_peers,
                        })}
                    </span>
                    <span>
                        {t("tools.propagation_nodes.stats_messages", {
                            count: localPropagationNode.local_node_stats.messagestore_count,
                        })}
                    </span>
                    <span>
                        {t("tools.propagation_nodes.stats_received", {
                            count: localPropagationNode.local_node_stats.client_messages_received,
                        })}
                    </span>
                    <span>
                        {t("tools.propagation_nodes.stats_served", {
                            count: localPropagationNode.local_node_stats.client_messages_served,
                        })}
                    </span>
                    <span>
                        {t("tools.propagation_nodes.stats_storage", {
                            size: formatStorageUsage(localPropagationNode.local_node_stats),
                        })}
                    </span>
                    <span>RX {formatByteSize(localPropagationNode.local_node_stats.rx_bytes)}</span>
                    <span>TX {formatByteSize(localPropagationNode.local_node_stats.tx_bytes)}</span>
                </div>
            {:else}
                <div class="text-[11px] text-sem-fg-muted">
                    {t("tools.propagation_nodes.stats_when_running")}
                </div>
            {/if}

            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <label class="text-[11px] text-sem-fg-muted block">
                    {t("app.incoming_message_size")}
                    <select
                        bind:value={lxmfIncomingDeliveryPreset}
                        class="input-field mt-1 py-1.5 text-sm"
                        onchange={(e) => onIncomingPresetChange((e.target as HTMLSelectElement).value)}
                    >
                        <option value="1mb">{t("app.incoming_message_size_1mb")}</option>
                        <option value="10mb">{t("app.incoming_message_size_10mb")}</option>
                        <option value="25mb">{t("app.incoming_message_size_25mb")}</option>
                        <option value="50mb">{t("app.incoming_message_size_50mb")}</option>
                        <option value="1gb">{t("app.incoming_message_size_1gb")}</option>
                        <option value="custom">{t("app.incoming_message_size_custom")}</option>
                    </select>
                    {#if lxmfIncomingDeliveryPreset === "custom"}
                        <div class="mt-1 flex flex-wrap items-center gap-2">
                            <input
                                bind:value={lxmfIncomingDeliveryCustomAmount}
                                type="number"
                                min="0.001"
                                step="any"
                                class="input-field min-w-0 flex-1 py-1.5 text-sm"
                                oninput={(e) =>
                                    onIncomingCustomAmountChange(Number((e.target as HTMLInputElement).value))}
                            />
                            <select
                                bind:value={lxmfIncomingDeliveryCustomUnit}
                                class="input-field py-1.5 text-sm w-auto"
                                onchange={(e) => onIncomingCustomUnitChange((e.target as HTMLSelectElement).value)}
                            >
                                <option value="mb">{t("app.incoming_message_size_unit_mb")}</option>
                                <option value="gb">{t("app.incoming_message_size_unit_gb")}</option>
                            </select>
                        </div>
                    {/if}
                </label>
                <label class="text-[11px] text-sem-fg-muted">
                    {t("tools.propagation_nodes.transfer_limit_mb")}
                    <input
                        bind:value={propagationLimitInputMb}
                        type="number"
                        min="0.001"
                        step="0.01"
                        class="input-field mt-1 py-1.5 text-sm"
                        oninput={(e) => onTransferLimitChange(Number((e.target as HTMLInputElement).value))}
                    />
                </label>
                <label class="text-[11px] text-sem-fg-muted">
                    {t("tools.propagation_nodes.sync_limit_mb")}
                    <input
                        bind:value={propagationSyncLimitInputMb}
                        type="number"
                        min="0.001"
                        step="0.01"
                        class="input-field mt-1 py-1.5 text-sm"
                        oninput={(e) => onSyncLimitChange(Number((e.target as HTMLInputElement).value))}
                    />
                </label>
            </div>

            <label class="block text-[11px] text-sem-fg-muted">
                {t("tools.propagation_nodes.stamp_cost")}
                <input
                    value={config.lxmf_propagation_node_stamp_cost ?? 16}
                    type="number"
                    min="13"
                    max="254"
                    class="input-field mt-1 py-1.5 text-sm"
                    oninput={(e) => onStampCostChange(Number((e.target as HTMLInputElement).value))}
                />
            </label>
            <button
                type="button"
                class="primary-chip text-xs"
                disabled={!localPropagationNode}
                onclick={onUseLocalNode}
            >
                {t("tools.propagation_nodes.use_our_node")}
            </button>
        </div>
    {/if}
</div>
