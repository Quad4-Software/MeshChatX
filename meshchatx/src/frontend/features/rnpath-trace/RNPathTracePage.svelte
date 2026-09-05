<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import ToastUtils from "../../js/ToastUtils.js";
    import { t } from "../../js/i18n.js";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import { RNPATH_TRACE_API_BASE } from "./lib/constants.js";
    import {
        formatTraceHash,
        getNodeClass,
        getNodeIcon,
        isUnknownTraceNode,
        isValidTraceHash,
    } from "./lib/traceFormat.js";
    import type { PathTraceResult } from "./lib/types.js";

    interface Props {
        routeQuery?: Record<string, string>;
    }

    let { routeQuery = {} }: Props = $props();

    let destinationHash = $state("");
    let isLoading = $state(false);
    let traceResult = $state<PathTraceResult | null>(null);
    let error = $state<string | null>(null);

    let isValidHash = $derived(isValidTraceHash(destinationHash));

    async function runTrace(): Promise<void> {
        if (!isValidHash) return;

        isLoading = true;
        error = null;
        traceResult = null;

        try {
            const res = await window.api.get(`${RNPATH_TRACE_API_BASE}/${destinationHash}`);
            const data = res.data as ({ error?: string } & PathTraceResult) | undefined;
            if (data?.error) {
                error = data.error;
            } else if (data) {
                traceResult = data;
            }
        } catch (e: any) {
            console.error(e);
            error =
                e.response?.data?.error ||
                e.response?.data?.message ||
                "Failed to communicate with the backend handler.";
        } finally {
            isLoading = false;
        }
    }

    function pingDestination(): void {
        location.hash = `#/ping?hash=${encodeURIComponent(destinationHash)}&autostart=1`;
    }

    function copyDestinationHash(): void {
        if (destinationHash) {
            navigator.clipboard.writeText(destinationHash);
            ToastUtils.success(t("common.copied"));
        }
    }

    onMount(() => {
        if (routeQuery.hash) {
            destinationHash = routeQuery.hash;
            if (isValidTraceHash(destinationHash)) {
                runTrace();
            }
        }
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas" data-testid="rnpath-trace-page">
    <ToolsPageHeader
        icon="map-marker-path"
        title={t("tools.rnpath_trace.title")}
        description={t("tools.rnpath_trace.description")}
        accent="blue"
    >
        {#if traceResult}
            <button
                type="button"
                class="p-2 text-gray-400 hover:text-indigo-500 dark:hover:text-indigo-400 transition-colors shrink-0"
                title="Refresh Trace"
                onclick={runTrace}
            >
                <MaterialDesignIcon iconName="refresh" class="size-5 {isLoading ? 'animate-spin' : ''}" />
            </button>
        {/if}
    </ToolsPageHeader>

    <div class="flex-1 overflow-y-auto min-w-0">
        <div
            class="p-3 sm:p-4 md:p-6 max-w-5xl mx-auto space-y-4 sm:space-y-6 pb-[max(1rem,env(safe-area-inset-bottom))]"
        >
            <div class="rounded-lg border border-sem-border bg-sem-surface p-3 sm:p-4 md:p-6">
                <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                    <div class="relative flex-1 min-w-0">
                        <input
                            bind:value={destinationHash}
                            type="text"
                            placeholder="input destination hash"
                            class="w-full pl-4 pr-12 py-3 bg-gray-50 dark:bg-zinc-800 border border-sem-border rounded-lg text-sm md:text-base font-mono focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-hidden transition-all dark:text-white"
                            onkeydown={(e) => {
                                if (e.key === "Enter") runTrace();
                            }}
                        />
                        <div
                            class="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none text-sem-fg-muted"
                        >
                            <MaterialDesignIcon iconName="identifier" class="size-5" />
                        </div>
                    </div>
                    <button
                        type="button"
                        class="w-full sm:w-auto sm:min-w-12 h-12 sm:h-14 px-4 sm:px-0 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg flex items-center justify-center gap-2 transition active:scale-95 disabled:opacity-50 shrink-0"
                        disabled={!isValidHash || isLoading}
                        title="Trace Path"
                        onclick={runTrace}
                    >
                        {#if !isLoading}
                            <MaterialDesignIcon
                                iconName="keyboard-return"
                                class="size-6 sm:size-7"
                            />
                        {:else}
                            <MaterialDesignIcon iconName="loading" class="size-6 animate-spin" />
                        {/if}
                        <span class="sm:hidden font-semibold">{t("tools.rnpath_trace.trace")}</span>
                    </button>
                </div>
            </div>

            {#if traceResult || isLoading || error}
                <div class="space-y-6">
                    {#if isLoading}
                        <div
                            class="rounded-lg border border-sem-border bg-sem-surface p-8 sm:p-12 flex flex-col items-center justify-center gap-4"
                        >
                            <div class="relative">
                                <div
                                    class="w-12 h-12 border-4 border-indigo-200 dark:border-indigo-900/30 border-t-indigo-600 rounded-full animate-spin"
                                ></div>
                            </div>
                            <div class="text-sm font-medium text-gray-600 dark:text-gray-400">
                                {t("tools.rnpath_trace.tracing")}
                            </div>
                        </div>
                    {:else if error}
                        <div
                            class="rounded-lg border border-sem-border border-l-4 border-l-red-500 p-4 sm:p-6 bg-red-50/50 dark:bg-red-900/10"
                        >
                            <div class="flex items-start gap-3 text-red-600 dark:text-red-400">
                                <MaterialDesignIcon iconName="alert-circle" class="size-5 md:size-6 shrink-0 mt-0.5" />
                                <div class="space-y-1">
                                    <div class="font-bold text-sm md:text-base">Trace Error</div>
                                    <div class="text-xs md:text-sm opacity-90 break-all whitespace-pre-wrap font-mono">
                                        {error}
                                    </div>
                                </div>
                            </div>
                        </div>
                    {:else if traceResult}
                        <div
                            class="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500"
                        >
                            <div class="rounded-lg border border-sem-border bg-sem-surface p-1 overflow-hidden">
                                <div class="flex flex-wrap items-center divide-x divide-gray-100 dark:divide-zinc-800">
                                    <div class="flex-1 min-w-[120px] p-3 md:p-4 flex flex-col items-center text-center">
                                        <div class="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">
                                            {t("tools.rnpath_trace.total_hops")}
                                        </div>
                                        <div class="text-xl md:text-2xl font-black text-indigo-600 dark:text-indigo-400">
                                            {traceResult.hops}
                                        </div>
                                    </div>
                                    <div class="flex-1 min-w-[120px] p-3 md:p-4 flex flex-col items-center text-center">
                                        <div class="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">
                                            {t("tools.rnpath_trace.interface")}
                                        </div>
                                        <div class="text-xs md:text-sm font-bold text-sem-fg-secondary truncate max-w-full">
                                            {traceResult.interface || "None"}
                                        </div>
                                    </div>
                                    <div
                                        class="flex-1 min-w-[120px] p-3 md:p-4 flex flex-col items-center text-center hidden sm:flex"
                                    >
                                        <div class="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">
                                            {t("tools.rnpath_trace.next_hop")}
                                        </div>
                                        <div
                                            class="text-[10px] md:text-xs font-mono font-bold text-sem-fg-muted truncate max-w-full"
                                        >
                                            {traceResult.next_hop || "N/A"}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-6 md:p-10 lg:p-16">
                                <div class="hidden md:flex items-start justify-center min-w-fit py-4">
                                    {#each traceResult.path as node, idx (`desktop-${idx}-${node.hash || node.type}`)}
                                        <div class="flex flex-col items-center group relative w-32 shrink-0">
                                            <div
                                                class="w-14 h-14 rounded-2xl flex items-center justify-center transition-all duration-300 shadow-md group-hover:shadow-indigo-500/20 group-hover:scale-110 z-10 {getNodeClass(node)}"
                                            >
                                                <MaterialDesignIcon iconName={getNodeIcon(node)} class="size-7" />
                                            </div>
                                            <div class="mt-4 text-center px-2 w-full">
                                                <div class="text-[11px] font-bold text-sem-fg truncate">
                                                    {node.name ||
                                                        formatTraceHash(node.hash) ||
                                                        (node.type === "unknown"
                                                            ? t("tools.rnpath_trace.unknown_hops", { count: node.count })
                                                            : "")}
                                                </div>
                                                {#if node.interface}
                                                    <div
                                                        class="text-[9px] text-indigo-500 font-mono font-bold mt-0.5 truncate"
                                                    >
                                                        {node.interface}
                                                    </div>
                                                {/if}
                                            </div>

                                            {#if node.hash}
                                                <div
                                                    class="absolute -top-10 left-1/2 -translate-x-1/2 bg-zinc-900 dark:bg-zinc-800 text-white text-[10px] px-2 py-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-all shadow-xl border border-zinc-700 pointer-events-none font-mono whitespace-nowrap z-20"
                                                >
                                                    {node.hash}
                                                </div>
                                            {/if}
                                        </div>

                                        {#if idx < traceResult.path.length - 1}
                                            <div
                                                class="flex-1 min-w-[40px] max-w-[100px] mt-7 h-0.5 relative"
                                            >
                                                <div
                                                    class="absolute inset-0 {isUnknownTraceNode(traceResult.path[idx + 1]) || isUnknownTraceNode(node)
                                                        ? 'border-t-2 border-dashed border-indigo-300 dark:border-indigo-800 bg-transparent h-0'
                                                        : 'bg-indigo-500/30'}"
                                                ></div>
                                                {#if !isUnknownTraceNode(traceResult.path[idx + 1]) && !isUnknownTraceNode(node)}
                                                    <div
                                                        class="absolute right-0 -top-1 w-2 h-2 rounded-full bg-indigo-500 shadow-xs shadow-indigo-500/50"
                                                    ></div>
                                                {/if}
                                            </div>
                                        {/if}
                                    {/each}
                                </div>

                                <div class="md:hidden space-y-0">
                                    {#each traceResult.path as node, idx (`mobile-${idx}-${node.hash || node.type}`)}
                                        <div class="flex gap-4">
                                            <div class="flex flex-col items-center w-10 shrink-0">
                                                <div
                                                    class="w-10 h-10 rounded-xl flex items-center justify-center shadow-md z-10 {getNodeClass(node)}"
                                                >
                                                    <MaterialDesignIcon iconName={getNodeIcon(node)} class="size-5" />
                                                </div>
                                                {#if idx < traceResult.path.length - 1}
                                                    <div
                                                        class="w-0.5 flex-1 min-h-[40px] my-1 {isUnknownTraceNode(traceResult.path[idx + 1]) || isUnknownTraceNode(node)
                                                            ? 'border-l-2 border-dashed border-indigo-300 dark:border-indigo-800'
                                                            : 'bg-indigo-500/30'}"
                                                    ></div>
                                                {/if}
                                            </div>

                                            <div class="flex-1 pb-6 pt-1 min-w-0">
                                                <div class="font-bold text-sm text-sem-fg truncate">
                                                    {node.name ||
                                                        (node.type === "unknown"
                                                            ? t("tools.rnpath_trace.unknown_hops", { count: node.count })
                                                            : formatTraceHash(node.hash))}
                                                </div>
                                                {#if node.hash}
                                                    <div
                                                        class="text-[10px] font-mono text-sem-fg-muted mt-0.5 truncate"
                                                    >
                                                        {node.hash}
                                                    </div>
                                                {/if}
                                                {#if node.interface}
                                                    <div
                                                        class="inline-flex items-center gap-1 mt-1.5 px-2 py-0.5 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 rounded-sm text-[9px] font-bold uppercase tracking-wider"
                                                    >
                                                        <MaterialDesignIcon iconName="router-wireless" class="size-3" />
                                                        {node.interface}
                                                    </div>
                                                {/if}
                                            </div>
                                        </div>
                                    {/each}
                                </div>
                            </div>

                            <div class="flex flex-col sm:flex-row items-center justify-center gap-3">
                                <button
                                    type="button"
                                    class="w-full sm:w-auto px-6 py-3 bg-indigo-100 hover:bg-indigo-200 dark:bg-indigo-900/30 dark:hover:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 rounded-2xl font-bold transition flex items-center justify-center gap-2 text-sm"
                                    onclick={pingDestination}
                                >
                                    <MaterialDesignIcon iconName="radar" class="size-5" />
                                    {t("tools.rnpath_trace.ping_test")}
                                </button>
                                <button
                                    type="button"
                                    class="w-full sm:w-auto px-6 py-3 bg-sem-surface border border-sem-border hover:bg-sem-surface-muted text-sem-fg-muted rounded-2xl font-bold transition flex items-center justify-center gap-2 text-sm"
                                    onclick={copyDestinationHash}
                                >
                                    <MaterialDesignIcon iconName="content-copy" class="size-5" />
                                    {t("common.copy_to_clipboard")}
                                </button>
                            </div>
                        </div>
                    {/if}
                </div>
            {/if}
        </div>
    </div>
</div>
