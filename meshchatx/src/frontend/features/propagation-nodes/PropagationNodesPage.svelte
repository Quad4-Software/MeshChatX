<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import Utils from "../../js/Utils.js";
    import ToastUtils from "../../js/ToastUtils.js";
    import GlobalEmitter from "../../js/GlobalEmitter.js";
    import { copyTextToClipboard, readTextFromClipboard } from "../../js/clipboardUtils.js";
    import { onWsEvent, offWsEvent } from "../../js/registries/wsEventRegistry.js";
    import { t } from "../../js/i18n.js";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import {
        incomingDeliveryBytesFromCustom,
        incomingDeliveryBytesFromPresetKey,
        syncIncomingDeliveryFieldsFromBytes,
    } from "../../js/settings/incomingDeliveryLimit.js";
    import { DEFAULT_ITEMS_PER_PAGE, SAVE_DEBOUNCE_MS } from "./lib/constants.js";
    import {
        fetchPropagationConfig,
        fetchPropagationNodes,
        requestNodePath,
        restartLocalNode,
        stopLocalNode,
        triggerAnnounce,
        updatePropagationConfig,
    } from "./lib/propagationApi.js";
    import { bytesToMb, mbToBytes } from "./lib/propagationFormat.js";
    import { filterAndSortNodes } from "./lib/propagationSort.js";
    import type { NodePathInfo, PropagationNodeItem, PropagationNodesConfig, PropagationSortBy } from "./lib/types.js";
    import PropagationHostedSection from "./components/PropagationHostedSection.svelte";
    import PropagationPreferredSection from "./components/PropagationPreferredSection.svelte";
    import PropagationNodeList from "./components/PropagationNodeList.svelte";

    let searchTerm = $state("");
    let sortBy = $state<PropagationSortBy>("preferred");
    let propagationNodes = $state<PropagationNodeItem[]>([]);
    let config = $state<PropagationNodesConfig>({
        lxmf_preferred_propagation_node_destination_hash: null,
        lxmf_preferred_propagation_node_auto_select: false,
        lxmf_local_propagation_node_address_hash: null,
        lxmf_delivery_transfer_limit_in_bytes: 1000 * 1000 * 10,
        lxmf_propagation_transfer_limit_in_bytes: 1000 * 256,
        lxmf_propagation_sync_limit_in_bytes: 1000 * 10240,
        lxmf_propagation_node_stamp_cost: 16,
    });

    let manualHashDraft = $state("");
    let isSavingPreferred = $state(false);
    let currentPage = $state(1);
    let itemsPerPage = $state(DEFAULT_ITEMS_PER_PAGE);

    let isLocalManagerCollapsed = $state(true);
    let localNodeDisplayNameDraft = $state("");
    let lxmfIncomingDeliveryPreset = $state("10mb");
    let lxmfIncomingDeliveryCustomAmount = $state(10);
    let lxmfIncomingDeliveryCustomUnit = $state("mb");
    let propagationLimitInputMb = $state(0);
    let propagationSyncLimitInputMb = $state(0);
    let nodePathsByHash = $state<Record<string, NodePathInfo | null>>({});

    let saveTimeouts = {
        deliveryLimit: null as ReturnType<typeof setTimeout> | null,
        propagationLimit: null as ReturnType<typeof setTimeout> | null,
        propagationSyncLimit: null as ReturnType<typeof setTimeout> | null,
        propagationStampCost: null as ReturnType<typeof setTimeout> | null,
    };

    const localPropagationNode = $derived(propagationNodes.find((node) => node.is_local_node) ?? null);

    const localNodeIsRunning = $derived(
        (() => {
            const running = localPropagationNode?.local_node_stats?.is_running;
            if (typeof running === "boolean") {
                return running;
            }
            return Boolean(localPropagationNode?.is_propagation_enabled);
        })()
    );

    const localNodeStatsVisible = $derived(Boolean(localPropagationNode?.local_node_stats && localNodeIsRunning));

    const sortedAndSearchedPropagationNodes = $derived(
        filterAndSortNodes(
            propagationNodes,
            searchTerm,
            sortBy,
            config.lxmf_preferred_propagation_node_destination_hash
        )
    );

    const totalPages = $derived(Math.ceil(sortedAndSearchedPropagationNodes.length / itemsPerPage));

    const startIndex = $derived((currentPage - 1) * itemsPerPage);
    const endIndex = $derived(Math.min(startIndex + itemsPerPage, sortedAndSearchedPropagationNodes.length));

    const paginatedNodes = $derived(sortedAndSearchedPropagationNodes.slice(startIndex, endIndex));

    const localNodePath = $derived(nodePathsByHash[config.lxmf_local_propagation_node_address_hash || ""] || null);

    const preferredPath = $derived(
        nodePathsByHash[config.lxmf_preferred_propagation_node_destination_hash || ""] || null
    );

    export function isPreferredNode(destinationHash: string | undefined | null): boolean {
        return config.lxmf_preferred_propagation_node_destination_hash === destinationHash;
    }

    export function syncManagerInputsFromConfig(): void {
        const displayName = (config.display_name || "").trim();
        localNodeDisplayNameDraft = displayName || "Anonymous Peer";
        const incoming = syncIncomingDeliveryFieldsFromBytes(config.lxmf_delivery_transfer_limit_in_bytes);
        lxmfIncomingDeliveryPreset = incoming.preset;
        lxmfIncomingDeliveryCustomAmount = incoming.customAmount;
        lxmfIncomingDeliveryCustomUnit = incoming.customUnit;
        propagationLimitInputMb = bytesToMb(config.lxmf_propagation_transfer_limit_in_bytes);
        propagationSyncLimitInputMb = bytesToMb(config.lxmf_propagation_sync_limit_in_bytes);
    }

    export function syncManualHashDraftFromConfig(): void {
        const preferred = config.lxmf_preferred_propagation_node_destination_hash || "";
        manualHashDraft = preferred;
    }

    export async function getConfig(): Promise<void> {
        try {
            const cfg = await fetchPropagationConfig();
            config = cfg;
            syncManagerInputsFromConfig();
            syncManualHashDraftFromConfig();
        } catch (e) {
            console.error(e);
            ToastUtils.error(t("common.save_failed"));
        }
    }

    export async function updateConfig(patch: Partial<PropagationNodesConfig>): Promise<boolean> {
        try {
            const nextCfg = await updatePropagationConfig(patch);
            config = nextCfg;
            syncManagerInputsFromConfig();
            return true;
        } catch (e) {
            ToastUtils.error(t("common.save_failed"));
            console.error(e);
            return false;
        }
    }

    export async function loadPropagationNodes(): Promise<void> {
        try {
            const nodes = await fetchPropagationNodes(500);
            propagationNodes = nodes;
            await refreshPriorityNodePaths();
        } catch {
            ToastUtils.error(t("tools.propagation_nodes.load_failed"));
        }
    }

    export async function requestPathForNode(destinationHash: string | undefined | null): Promise<void> {
        const hash = (destinationHash || "").trim();
        if (!hash) return;
        const path = await requestNodePath(hash);
        nodePathsByHash = {
            ...nodePathsByHash,
            [hash]: path,
        };
    }

    export async function refreshPriorityNodePaths(): Promise<void> {
        const hashes = new Set<string>();
        const localHash = config.lxmf_local_propagation_node_address_hash;
        if (localHash) hashes.add(localHash);
        const preferredHash = config.lxmf_preferred_propagation_node_destination_hash;
        if (preferredHash) hashes.add(preferredHash);
        for (const hash of hashes) {
            await requestPathForNode(hash);
        }
    }

    export async function usePropagationNode(destination_hash: string): Promise<boolean> {
        const parsed = Utils.parseDestinationHash(destination_hash);
        if (!parsed) {
            ToastUtils.error(t("tools.propagation_nodes.invalid_hash"));
            return false;
        }
        const patch: Partial<PropagationNodesConfig> = {
            lxmf_preferred_propagation_node_destination_hash: parsed,
        };
        if (config.lxmf_preferred_propagation_node_auto_select) {
            patch.lxmf_preferred_propagation_node_auto_select = false;
        }
        const didUpdate = await updateConfig(patch);
        if (!didUpdate) {
            return false;
        }
        manualHashDraft = parsed;
        ToastUtils.success(t("tools.propagation_nodes.preferred_set"));
        await requestPathForNode(parsed);
        return true;
    }

    export async function selectPreferredNode(destinationHash: string): Promise<void> {
        if (isPreferredNode(destinationHash)) {
            return;
        }
        await usePropagationNode(destinationHash);
    }

    export async function stopUsingPropagationNode(): Promise<void> {
        const didUpdate = await updateConfig({
            lxmf_preferred_propagation_node_destination_hash: null,
        });
        if (!didUpdate) return;
        manualHashDraft = "";
        ToastUtils.success(t("tools.propagation_nodes.preferred_cleared"));
    }

    export function onManualHashPaste(event: ClipboardEvent): void {
        const text = event.clipboardData?.getData("text") || "";
        const parsed = Utils.parseDestinationHash(text);
        if (!parsed) return;
        event.preventDefault();
        manualHashDraft = parsed;
    }

    export async function pastePreferredHash(): Promise<void> {
        const result = await readTextFromClipboard();
        if (!result.ok) {
            ToastUtils.error(t("messages.failed_read_clipboard"));
            return;
        }
        const parsed = Utils.parseDestinationHash(result.text);
        if (!parsed) {
            ToastUtils.error(t("tools.propagation_nodes.invalid_hash"));
            return;
        }
        manualHashDraft = parsed;
        await usePropagationNode(parsed);
    }

    export async function copyPreferredHash(): Promise<void> {
        const hash = config.lxmf_preferred_propagation_node_destination_hash;
        if (!hash) return;
        const ok = await copyTextToClipboard(hash);
        if (ok) {
            ToastUtils.success(t("common.copied"));
        } else {
            ToastUtils.error(t("common.failed_to_copy"));
        }
    }

    export async function setPreferredFromDraft(): Promise<void> {
        if (isSavingPreferred) return;
        isSavingPreferred = true;
        try {
            await usePropagationNode(manualHashDraft);
        } finally {
            isSavingPreferred = false;
        }
    }

    export async function useLocalPropagationNode(): Promise<void> {
        if (!localPropagationNode) return;
        await usePropagationNode(localPropagationNode.destination_hash);
        await requestPathForNode(localPropagationNode.destination_hash);
    }

    export async function restartLocalPropagationNode(): Promise<void> {
        try {
            await restartLocalNode();
            ToastUtils.success(t("tools.propagation_nodes.local_restarted"));
            await Promise.all([getConfig(), loadPropagationNodes()]);
            await refreshPriorityNodePaths();
        } catch {
            ToastUtils.error(t("common.save_failed"));
        }
    }

    export async function stopLocalPropagationNode(): Promise<void> {
        try {
            await stopLocalNode();
            ToastUtils.success(t("tools.propagation_nodes.local_stopped"));
            await Promise.all([getConfig(), loadPropagationNodes()]);
            await refreshPriorityNodePaths();
        } catch {
            ToastUtils.error(t("common.save_failed"));
        }
    }

    export async function startLocalPropagationNode(): Promise<void> {
        try {
            const didUpdate = await updateConfig({ lxmf_local_propagation_node_enabled: true });
            if (!didUpdate) return;
            ToastUtils.success(t("tools.propagation_nodes.local_started"));
            await Promise.all([getConfig(), loadPropagationNodes()]);
            await refreshPriorityNodePaths();
        } catch {
            ToastUtils.error(t("common.save_failed"));
        }
    }

    export async function announceNow(showSuccessToast = true): Promise<void> {
        try {
            await triggerAnnounce();
            if (showSuccessToast) {
                ToastUtils.success(t("tools.propagation_nodes.announce_triggered"));
            }
            await loadPropagationNodes();
            await refreshPriorityNodePaths();
        } catch {
            ToastUtils.error(t("common.save_failed"));
        }
    }

    export async function saveLocalNodeDisplayName(): Promise<void> {
        const nextName = (localNodeDisplayNameDraft || "").trim() || "Anonymous Peer";
        try {
            const didUpdate = await updateConfig({ display_name: nextName });
            if (!didUpdate) return;
            localNodeDisplayNameDraft = nextName;
            await announceNow(false);
            ToastUtils.success(t("tools.propagation_nodes.name_saved"));
            await loadPropagationNodes();
            await refreshPriorityNodePaths();
        } catch {
            ToastUtils.error(t("common.save_failed"));
        }
    }

    export async function resetLocalNodeDisplayName(): Promise<void> {
        localNodeDisplayNameDraft = "Anonymous Peer";
        await saveLocalNodeDisplayName();
    }

    export async function onLxmfIncomingDeliveryPresetChange(preset: string): Promise<void> {
        lxmfIncomingDeliveryPreset = preset;
        if (preset === "custom") {
            const incoming = syncIncomingDeliveryFieldsFromBytes(config.lxmf_delivery_transfer_limit_in_bytes);
            lxmfIncomingDeliveryCustomAmount = incoming.customAmount;
            lxmfIncomingDeliveryCustomUnit = incoming.customUnit;
            return;
        }
        const bytes = incomingDeliveryBytesFromPresetKey(preset);
        if (bytes == null) return;
        await updateConfig({
            lxmf_delivery_transfer_limit_in_bytes: bytes,
        });
    }

    export function onLxmfIncomingDeliveryCustomChange(): void {
        if (lxmfIncomingDeliveryPreset !== "custom") return;
        if (saveTimeouts.deliveryLimit) clearTimeout(saveTimeouts.deliveryLimit);
        saveTimeouts.deliveryLimit = setTimeout(async () => {
            await updateConfig({
                lxmf_delivery_transfer_limit_in_bytes: incomingDeliveryBytesFromCustom(
                    lxmfIncomingDeliveryCustomAmount,
                    lxmfIncomingDeliveryCustomUnit
                ),
            });
        }, SAVE_DEBOUNCE_MS);
    }

    export function onPropagationTransferLimitChange(valueMb: number): void {
        propagationLimitInputMb = valueMb;
        if (saveTimeouts.propagationLimit) clearTimeout(saveTimeouts.propagationLimit);
        saveTimeouts.propagationLimit = setTimeout(async () => {
            await updateConfig({
                lxmf_propagation_transfer_limit_in_bytes: mbToBytes(propagationLimitInputMb),
            });
        }, SAVE_DEBOUNCE_MS);
    }

    export function onPropagationSyncLimitChange(valueMb: number): void {
        propagationSyncLimitInputMb = valueMb;
        if (saveTimeouts.propagationSyncLimit) clearTimeout(saveTimeouts.propagationSyncLimit);
        saveTimeouts.propagationSyncLimit = setTimeout(async () => {
            await updateConfig({
                lxmf_propagation_sync_limit_in_bytes: mbToBytes(propagationSyncLimitInputMb),
            });
        }, SAVE_DEBOUNCE_MS);
    }

    export function onPropagationStampCostChange(costInput: number): void {
        if (saveTimeouts.propagationStampCost) clearTimeout(saveTimeouts.propagationStampCost);
        saveTimeouts.propagationStampCost = setTimeout(async () => {
            let cost = Number(costInput);
            if (!Number.isFinite(cost) || cost < 13) {
                cost = 13;
            } else if (cost > 254) {
                cost = 254;
            }
            config = { ...config, lxmf_propagation_node_stamp_cost: cost };
            await updateConfig({
                lxmf_propagation_node_stamp_cost: cost,
            });
        }, SAVE_DEBOUNCE_MS);
    }

    function onConfigEvent(json: { config?: PropagationNodesConfig }): void {
        if (json?.config) {
            config = json.config;
            syncManagerInputsFromConfig();
            syncManualHashDraftFromConfig();
        }
    }

    function onWebsocketReconnected(): void {
        void Promise.all([getConfig(), loadPropagationNodes()]);
    }

    onMount(() => {
        onWsEvent("config", onConfigEvent);
        GlobalEmitter.on("websocket-reconnected", onWebsocketReconnected);

        if (typeof window !== "undefined" && window.matchMedia && window.matchMedia("(max-width: 640px)").matches) {
            isLocalManagerCollapsed = true;
        }

        void getConfig();
        void loadPropagationNodes();

        return () => {
            offWsEvent("config", onConfigEvent);
            GlobalEmitter.off("websocket-reconnected", onWebsocketReconnected);
            if (saveTimeouts.deliveryLimit) clearTimeout(saveTimeouts.deliveryLimit);
            if (saveTimeouts.propagationLimit) clearTimeout(saveTimeouts.propagationLimit);
            if (saveTimeouts.propagationSyncLimit) clearTimeout(saveTimeouts.propagationSyncLimit);
            if (saveTimeouts.propagationStampCost) clearTimeout(saveTimeouts.propagationStampCost);
        };
    });
</script>

<div
    class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas text-sem-fg"
    data-testid="propagation-nodes-page"
>
    <ToolsPageHeader icon="mailbox" title={t("tools.propagation_nodes.title")} accent="cyan">
        <button
            type="button"
            class="inline-flex size-9 items-center justify-center rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-sem-accent"
            title={t("tools.propagation_nodes.reload")}
            onclick={loadPropagationNodes}
        >
            <MaterialDesignIcon iconName="refresh" class="size-5" />
        </button>
    </ToolsPageHeader>

    <PropagationHostedSection
        {config}
        {localPropagationNode}
        {localNodeIsRunning}
        {localNodeStatsVisible}
        {localNodePath}
        {isLocalManagerCollapsed}
        bind:localNodeDisplayNameDraft
        bind:lxmfIncomingDeliveryPreset
        bind:lxmfIncomingDeliveryCustomAmount
        bind:lxmfIncomingDeliveryCustomUnit
        bind:propagationLimitInputMb
        bind:propagationSyncLimitInputMb
        onToggleCollapse={() => (isLocalManagerCollapsed = !isLocalManagerCollapsed)}
        onAnnounce={() => announceNow(true)}
        onStartNode={startLocalPropagationNode}
        onRestartNode={restartLocalPropagationNode}
        onStopNode={stopLocalPropagationNode}
        onRequestLocalPath={() => requestPathForNode(config.lxmf_local_propagation_node_address_hash)}
        onSaveDisplayName={saveLocalNodeDisplayName}
        onResetDisplayName={resetLocalNodeDisplayName}
        onIncomingPresetChange={onLxmfIncomingDeliveryPresetChange}
        onIncomingCustomAmountChange={(val) => {
            lxmfIncomingDeliveryCustomAmount = val;
            onLxmfIncomingDeliveryCustomChange();
        }}
        onIncomingCustomUnitChange={(val) => {
            lxmfIncomingDeliveryCustomUnit = val;
            onLxmfIncomingDeliveryCustomChange();
        }}
        onTransferLimitChange={onPropagationTransferLimitChange}
        onSyncLimitChange={onPropagationSyncLimitChange}
        onStampCostChange={onPropagationStampCostChange}
        onUseLocalNode={useLocalPropagationNode}
    />

    <PropagationPreferredSection
        {config}
        {preferredPath}
        bind:manualHashDraft
        {isSavingPreferred}
        onCopyPreferredHash={copyPreferredHash}
        onRequestPreferredPath={() => requestPathForNode(config.lxmf_preferred_propagation_node_destination_hash)}
        onClearPreferred={stopUsingPropagationNode}
        {onManualHashPaste}
        onPastePreferredHash={pastePreferredHash}
        onSetPreferredFromDraft={setPreferredFromDraft}
    />

    <PropagationNodeList
        totalNodesCount={propagationNodes.length}
        filteredNodesCount={sortedAndSearchedPropagationNodes.length}
        {paginatedNodes}
        preferredHash={config.lxmf_preferred_propagation_node_destination_hash}
        bind:searchTerm
        bind:sortBy
        {currentPage}
        {totalPages}
        {startIndex}
        {endIndex}
        {nodePathsByHash}
        onSelectPreferredNode={selectPreferredNode}
        onRequestPath={requestPathForNode}
        onPageChange={(page) => (currentPage = page)}
        onReloadNodes={loadPropagationNodes}
    />
</div>
