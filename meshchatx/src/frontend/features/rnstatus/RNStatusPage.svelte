<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import GlobalEmitter from "../../js/GlobalEmitter.js";
    import ToastUtils from "../../js/ToastUtils.js";
    import { onWsEvent, offWsEvent } from "../../js/registries/wsEventRegistry.js";
    import { t } from "../../js/i18n.js";
    import RNStatusFilters from "./components/RNStatusFilters.svelte";
    import RNStatusRemoteQuery from "./components/RNStatusRemoteQuery.svelte";
    import RNStatusSummary from "./components/RNStatusSummary.svelte";
    import RNStatusTable from "./components/RNStatusTable.svelte";
    import { DEFAULT_REMOTE_TIMEOUT } from "./lib/constants.js";
    import { fetchRNStatus } from "./lib/statusPoller.js";
    import type { RNStatusResponse } from "./lib/types.js";

    let isLoading = $state(false);
    let reloadingRns = $state(false);
    let includeLinkStats = $state(false);
    let showAll = $state(false);
    let sorting = $state("");
    let remoteHash = $state("");
    let identityPath = $state("");
    let remoteTimeout = $state(DEFAULT_REMOTE_TIMEOUT);
    let statusData = $state<RNStatusResponse>({});

    export function onReloadStatus(json: { in_progress?: boolean; level?: string }): void {
        reloadingRns = json?.in_progress !== false;
        if (json?.in_progress === false && json?.level !== "error") {
            void refreshStatus();
        }
    }

    export function onWebsocketMessage(message: unknown): void {
        let json: { type?: string; in_progress?: boolean; level?: string } | undefined;
        try {
            if (
                message &&
                typeof message === "object" &&
                "type" in message &&
                typeof (message as { type: unknown }).type === "string" &&
                (message as { data?: unknown }).data === undefined
            ) {
                json = message as { type?: string; in_progress?: boolean; level?: string };
            } else {
                const raw = typeof message === "string" ? message : (message as { data?: unknown })?.data;
                json = typeof raw === "string" ? JSON.parse(raw) : message;
            }
        } catch {
            return;
        }
        if (!json || typeof json !== "object" || typeof json.type !== "string") {
            return;
        }
        if (json.type === "reticulum_reload_status") {
            onReloadStatus(json);
        }
    }

    function onWebsocketReconnected(): void {
        void refreshStatus();
    }

    export function clearRemote(): void {
        remoteHash = "";
        statusData = { ...statusData, remote: "" };
        void refreshStatus();
    }

    export async function refreshStatus(): Promise<void> {
        if (reloadingRns) {
            return;
        }
        isLoading = true;
        try {
            const data = await fetchRNStatus({
                include_link_stats: includeLinkStats,
                show_all: showAll,
                sorting,
                remote: remoteHash,
                identity_path: identityPath,
                timeout: remoteTimeout,
            });
            statusData = data;
        } catch (e: unknown) {
            const err = e as { response?: { data?: { message?: string } }; message?: string };
            console.error(err);
            const detail = err?.response?.data?.message || err?.message || "";
            ToastUtils.error(detail ? `${t("rnstatus.failed_refresh")}: ${detail}` : t("rnstatus.failed_refresh"));
        } finally {
            isLoading = false;
        }
    }

    function handleFilterChange(): void {
        if (!reloadingRns) {
            void refreshStatus();
        }
    }

    onMount(() => {
        onWsEvent("reticulum_reload_status", onReloadStatus);
        GlobalEmitter.on("websocket-reconnected", onWebsocketReconnected);
        void refreshStatus();
        return () => {
            offWsEvent("reticulum_reload_status", onReloadStatus);
            GlobalEmitter.off("websocket-reconnected", onWebsocketReconnected);
        };
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas" data-testid="rnstatus-page">
    <ToolsPageHeader
        icon="chart-line"
        title={t("tools.rnstatus.title")}
        description={t("tools.rnstatus.description")}
        eyebrow={t("rnprobe.network_diagnostics")}
        accent="orange"
    >
        <button
            type="button"
            class="primary-chip disabled:opacity-50 disabled:pointer-events-none focus-ring-sem"
            disabled={isLoading || reloadingRns}
            onclick={() => void refreshStatus()}
        >
            <MaterialDesignIcon
                iconName="refresh"
                class="h-4 w-4 shrink-0 {isLoading || reloadingRns ? 'animate-spin-reverse' : ''}"
            />
            <span class="hidden sm:inline">
                {reloadingRns ? t("rnstatus.reloading") : t("rnstatus.refresh")}
            </span>
        </button>
    </ToolsPageHeader>

    <div class="flex-1 overflow-y-auto overflow-x-hidden w-full px-3 sm:px-5 md:px-5 lg:px-8 py-3 sm:py-4 min-w-0">
        <div class="space-y-4 w-full max-w-6xl xl:max-w-7xl mx-auto min-w-0">
            <RNStatusFilters
                bind:includeLinkStats
                bind:showAll
                bind:sorting
                disabled={reloadingRns}
                onChange={handleFilterChange}
            />

            <RNStatusRemoteQuery
                bind:remoteHash
                bind:identityPath
                bind:remoteTimeout
                activeRemoteHash={statusData.remote || ""}
                disabled={reloadingRns}
                onClearRemote={clearRemote}
            />

            <RNStatusSummary {statusData} />

            <RNStatusTable interfaces={statusData.interfaces || []} {isLoading} {reloadingRns} />
        </div>
    </div>
</div>
