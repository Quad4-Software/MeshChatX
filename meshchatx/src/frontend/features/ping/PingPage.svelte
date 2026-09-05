<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import ToastUtils from "../../js/ToastUtils.js";
    import { t } from "../../js/i18n.js";
    import { formatPingSuccess, isValidPingDestinationHash, isValidPingTimeout } from "./lib/pingFormat.js";
    import type { PingSuccessSummary } from "./lib/pingFormat.js";

    interface Props {
        routeQuery?: Record<string, string>;
    }

    interface PingSummaryState extends Partial<PingSuccessSummary> {
        error?: string;
    }

    let { routeQuery = {} }: Props = $props();

    let isRunning = $state(false);
    let destinationHash = $state<string | null>(null);
    let timeout = $state(10);
    let seq = $state(0);
    let pingResults = $state<string[]>([]);
    let abortController = $state<AbortController | null>(null);
    let lastPingSummary = $state<PingSummaryState | null>(null);
    let currentSessionId = $state(0);
    let resultsEl = $state<HTMLElement | undefined>();

    function sleep(millis: number): Promise<void> {
        return new Promise((resolve) => setTimeout(resolve, millis));
    }

    function scrollPingResultsToBottom(): void {
        queueMicrotask(() => {
            setTimeout(() => {
                if (resultsEl) {
                    resultsEl.scrollTop = resultsEl.scrollHeight;
                }
            }, 0);
        });
    }

    function addPingResult(result: string): void {
        pingResults = [...pingResults, result];
        scrollPingResultsToBottom();
    }

    async function ping(): Promise<void> {
        try {
            seq += 1;
            const response = await window.api.post(
                `/api/v1/ping/${destinationHash}/lxmf.delivery`,
                {},
                {
                    signal: abortController?.signal,
                    params: { timeout },
                }
            );
            const pingResult = response.data.ping_result;
            const formatted = formatPingSuccess(pingResult, seq);
            addPingResult(formatted.line);
            lastPingSummary = formatted.summary;
        } catch (e: any) {
            if (window.api.isCancel?.(e)) {
                return;
            }
            const message = e.response?.data?.message ?? e.message ?? String(e);
            console.warn("Ping failed:", message);
            addPingResult(`seq=${seq} error=${message}`);
            lastPingSummary = {
                error: typeof message === "string" ? message : JSON.stringify(message),
            };
        }
    }

    async function start(): Promise<void> {
        if (isRunning) {
            return;
        }
        if (!isValidPingDestinationHash(destinationHash)) {
            ToastUtils.error(t("ping.invalid_hash"));
            return;
        }
        if (!isValidPingTimeout(timeout)) {
            ToastUtils.error(t("ping.timeout_must_be_number"));
            return;
        }
        seq = 0;
        isRunning = true;
        currentSessionId += 1;
        const sessionId = currentSessionId;
        abortController = new AbortController();
        while (isRunning && currentSessionId === sessionId) {
            await ping();
            if (isRunning && currentSessionId === sessionId) {
                await sleep(1000);
            }
        }
    }

    function stop(): void {
        isRunning = false;
        if (abortController) {
            abortController.abort();
        }
    }

    function clear(): void {
        pingResults = [];
        lastPingSummary = null;
    }

    async function dropPath(): Promise<void> {
        if (!isValidPingDestinationHash(destinationHash)) {
            ToastUtils.error(t("ping.invalid_hash"));
            return;
        }
        try {
            const response = await window.api.post(`/api/v1/destination/${destinationHash}/drop-path`);
            ToastUtils.success(response.data.message);
        } catch (e: any) {
            console.log(e);
            const message = e.response?.data?.message ?? `Failed to drop path: ${e}`;
            ToastUtils.error(message);
        }
    }

    onMount(() => {
        if (routeQuery.hash) {
            destinationHash = routeQuery.hash;
            if (routeQuery.autostart === "1" || routeQuery.autostart === "true") {
                start();
            }
        }
        return () => stop();
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas" data-testid="ping-page">
    <ToolsPageHeader icon="radar" title={t("ping.title")} description={t("tools.ping.description")} accent="blue" />
    <div class="flex-1 overflow-y-auto w-full px-4 md:px-5 lg:px-8 py-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]">
        <div class="space-y-4 w-full max-w-4xl mx-auto">
            <div class="glass-card space-y-5">
                <div class="text-sm text-sem-fg-muted">
                    {t("ping.description")}
                </div>

                <div class="grid md:grid-cols-2 gap-4">
                    <div>
                        <label class="glass-label" for="ping-hash">{t("ping.destination_hash")}</label>
                        <input
                            id="ping-hash"
                            bind:value={destinationHash}
                            type="text"
                            placeholder="e.g. 7b746057a7294469799cd8d7d429676a"
                            class="input-field font-mono"
                        />
                    </div>
                    <div>
                        <label class="glass-label" for="ping-timeout">{t("ping.timeout_seconds")}</label>
                        <input
                            id="ping-timeout"
                            bind:value={timeout}
                            type="number"
                            min="1"
                            max="600"
                            class="input-field"
                        />
                    </div>
                </div>

                <div class="flex flex-wrap gap-2">
                    {#if !isRunning}
                        <button type="button" class="primary-chip focus-ring-sem" onclick={start}>
                            <MaterialDesignIcon iconName="play" />
                            {t("ping.start_ping")}
                        </button>
                    {:else}
                        <button
                            type="button"
                            class="secondary-chip focus-ring-sem text-red-600! dark:text-red-300! border-red-200! dark:border-red-500/50!"
                            onclick={stop}
                        >
                            <MaterialDesignIcon iconName="pause" />
                            {t("ping.stop")}
                        </button>
                    {/if}
                    <button type="button" class="secondary-chip focus-ring-sem" onclick={clear}>
                        <MaterialDesignIcon iconName="broom" />
                        {t("ping.clear_results")}
                    </button>
                    <button type="button" class="danger-chip focus-ring-sem" onclick={dropPath}>
                        <MaterialDesignIcon iconName="link-variant-remove" />
                        {t("ping.drop_path")}
                    </button>
                </div>

                <div class="flex flex-wrap gap-2 text-xs font-semibold">
                    <span
                        class="rounded-full px-3 py-1 {isRunning
                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-200'
                            : 'bg-gray-200 text-gray-700 dark:bg-zinc-800 dark:text-gray-200'}"
                    >
                        {t("ping.status")}: {isRunning ? t("ping.running") : t("ping.idle")}
                    </span>
                    {#if lastPingSummary?.duration}
                        <span
                            class="rounded-full px-3 py-1 bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-200"
                        >
                            {t("ping.last_rtt")}: {lastPingSummary.duration}
                        </span>
                    {/if}
                    {#if lastPingSummary?.error}
                        <span
                            class="rounded-full px-3 py-1 bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-200"
                        >
                            {t("ping.last_error")}: {lastPingSummary.error}
                        </span>
                    {/if}
                </div>
            </div>

            <div class="glass-card flex flex-col min-h-[320px] space-y-3">
                <div class="flex items-center justify-between gap-4">
                    <div>
                        <div class="text-sm font-semibold text-sem-fg">{t("ping.console_output")}</div>
                        <div class="text-xs text-sem-fg-muted">{t("ping.streaming_responses")}</div>
                    </div>
                    <div class="text-xs text-sem-fg-muted">seq #{seq}</div>
                </div>

                {#if lastPingSummary && !lastPingSummary.error}
                    <div class="flex flex-wrap gap-2 text-xs text-gray-700 dark:text-gray-200">
                        {#if lastPingSummary.hopsThere != null}
                            <span class="stat-chip">{t("rnprobe.hops")} there: {lastPingSummary.hopsThere}</span>
                        {/if}
                        {#if lastPingSummary.hopsBack != null}
                            <span class="stat-chip">{t("rnprobe.hops")} back: {lastPingSummary.hopsBack}</span>
                        {/if}
                        {#if lastPingSummary.rssi != null}
                            <span class="stat-chip">{t("rnprobe.rssi")} {lastPingSummary.rssi} dBm</span>
                        {/if}
                        {#if lastPingSummary.snr != null}
                            <span class="stat-chip">{t("rnprobe.snr")} {lastPingSummary.snr} dB</span>
                        {/if}
                        {#if lastPingSummary.quality != null}
                            <span class="stat-chip">{t("rnprobe.quality")} {lastPingSummary.quality}%</span>
                        {/if}
                        {#if lastPingSummary.via}
                            <span class="stat-chip">{t("app.interfaces")} {lastPingSummary.via}</span>
                        {/if}
                    </div>
                {/if}

                <div
                    bind:this={resultsEl}
                    id="results"
                    class="flex-1 overflow-y-auto rounded-2xl bg-black/80 text-emerald-300 font-mono text-xs p-3 space-y-1 shadow-inner border border-zinc-900"
                >
                    {#if pingResults.length === 0}
                        <div class="text-emerald-500/80">{t("ping.no_pings_yet")}</div>
                    {:else}
                        {#each pingResults as pingResult, index (`${index}-${pingResult}`)}
                            <div class="whitespace-pre-wrap">{pingResult}</div>
                        {/each}
                    {/if}
                </div>
            </div>
        </div>
    </div>
</div>
