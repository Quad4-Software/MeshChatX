<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import DialogUtils from "../../js/DialogUtils.js";
    import { t } from "../../js/i18n.js";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import {
        DEFAULT_PROBE_COUNT,
        DEFAULT_PROBE_FULL_NAME,
        DEFAULT_PROBE_SIZE,
        DEFAULT_PROBE_WAIT,
        MAX_PROBE_SIZE,
        MAX_PROBES,
        MIN_PROBE_SIZE,
        MIN_PROBES,
        RNPROBE_API_ENDPOINT,
    } from "./lib/constants.js";
    import {
        isProbeDelivered,
        isProbeTimeout,
        isValidProbeDestinationHash,
        isValidProbeFullName,
        parseProbeSummary,
    } from "./lib/probeFormat.js";
    import type { ProbeApiResponse, ProbeResultItem, ProbeSummary } from "./lib/types.js";

    interface Props {
        routeQuery?: Record<string, string>;
    }

    let { routeQuery = {} }: Props = $props();

    let isRunning = $state(false);
    let destinationHash = $state("");
    let fullName = $state(DEFAULT_PROBE_FULL_NAME);
    let probeSize = $state(DEFAULT_PROBE_SIZE);
    let probes = $state(DEFAULT_PROBE_COUNT);
    let wait = $state(DEFAULT_PROBE_WAIT);
    let results = $state<ProbeResultItem[]>([]);
    let summary = $state<ProbeSummary | null>(null);
    let abortController = $state<AbortController | null>(null);

    async function startProbe(): Promise<void> {
        if (isRunning) {
            return;
        }

        if (!isValidProbeDestinationHash(destinationHash)) {
            DialogUtils.alert(t("rnprobe.invalid_hash"));
            return;
        }

        if (!isValidProbeFullName(fullName)) {
            DialogUtils.alert(t("rnprobe.provide_full_name"));
            return;
        }

        isRunning = true;
        abortController = new AbortController();
        results = [];
        summary = null;

        try {
            const response = await window.api.post(
                RNPROBE_API_ENDPOINT,
                {
                    destination_hash: destinationHash,
                    full_name: fullName,
                    size: probeSize,
                    probes: probes,
                    wait: wait,
                },
                {
                    signal: abortController.signal,
                }
            );

            const data = (response as { data?: ProbeApiResponse })?.data;
            results = data?.results || [];
            summary = parseProbeSummary(data || {});
        } catch (e: any) {
            if (!window.api.isCancel?.(e)) {
                console.error(e);
                DialogUtils.alert(e.response?.data?.message || t("rnprobe.failed_to_probe"));
            }
        } finally {
            isRunning = false;
        }
    }

    function stopProbe(): void {
        isRunning = false;
        if (abortController) {
            abortController.abort();
            abortController = null;
        }
    }

    function clearResults(): void {
        results = [];
        summary = null;
    }

    onMount(() => {
        if (routeQuery.hash) {
            destinationHash = routeQuery.hash;
        }
        return () => {
            stopProbe();
        };
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas" data-testid="rnprobe-page">
    <ToolsPageHeader
        icon="radar"
        title={t("rnprobe.title")}
        description={t("tools.rnprobe.description")}
        eyebrow={t("rnprobe.network_diagnostics")}
        accent="purple"
    />
    <div
        class="flex-1 overflow-y-auto w-full px-4 md:px-5 lg:px-8 py-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]"
    >
        <div class="space-y-4 w-full max-w-4xl mx-auto">
            <div class="glass-card space-y-5">
                <div class="grid lg:grid-cols-2 gap-4">
                    <div>
                        <label class="glass-label" for="rnprobe-hash">{t("rnprobe.destination_hash")}</label>
                        <input
                            id="rnprobe-hash"
                            bind:value={destinationHash}
                            type="text"
                            placeholder="e.g. 7b746057a7294469799cd8d7d429676a"
                            class="input-field font-mono"
                        />
                    </div>
                    <div>
                        <label class="glass-label" for="rnprobe-fullname">{t("rnprobe.full_destination_name")}</label>
                        <input
                            id="rnprobe-fullname"
                            bind:value={fullName}
                            type="text"
                            placeholder="e.g. lxmf.delivery"
                            class="input-field"
                        />
                    </div>
                </div>

                <div class="grid lg:grid-cols-3 gap-4">
                    <div>
                        <label class="glass-label" for="rnprobe-size">{t("rnprobe.probe_size_bytes")}</label>
                        <input
                            id="rnprobe-size"
                            bind:value={probeSize}
                            type="number"
                            min={MIN_PROBE_SIZE}
                            max={MAX_PROBE_SIZE}
                            class="input-field"
                        />
                    </div>
                    <div>
                        <label class="glass-label" for="rnprobe-count">{t("rnprobe.number_of_probes")}</label>
                        <input
                            id="rnprobe-count"
                            bind:value={probes}
                            type="number"
                            min={MIN_PROBES}
                            max={MAX_PROBES}
                            class="input-field"
                        />
                    </div>
                    <div>
                        <label class="glass-label" for="rnprobe-wait">{t("rnprobe.wait_between_probes")}</label>
                        <input
                            id="rnprobe-wait"
                            bind:value={wait}
                            type="number"
                            min="0"
                            step="0.1"
                            class="input-field"
                        />
                    </div>
                </div>

                <div class="flex gap-2">
                    {#if !isRunning}
                        <button
                            type="button"
                            class="primary-chip px-4 py-2 text-sm"
                            onclick={startProbe}
                        >
                            <MaterialDesignIcon iconName="radar" class="w-4 h-4" />
                            {t("rnprobe.start_probe")}
                        </button>
                    {:else}
                        <button
                            type="button"
                            class="secondary-chip px-4 py-2 text-sm text-red-600 dark:text-red-300 border-red-200 dark:border-red-500/50"
                            onclick={stopProbe}
                        >
                            <MaterialDesignIcon iconName="stop" class="w-4 h-4" />
                            {t("rnprobe.stop")}
                        </button>
                    {/if}
                    <button type="button" class="secondary-chip px-4 py-2 text-sm" onclick={clearResults}>
                        <MaterialDesignIcon iconName="broom" class="w-4 h-4" />
                        {t("rnprobe.clear_results")}
                    </button>
                </div>

                {#if summary}
                    <div class="p-3 rounded-lg bg-sem-surface-muted text-blue-700 dark:text-blue-300">
                        <div class="font-semibold">{t("rnprobe.summary")}:</div>
                        <div class="text-sm mt-1">
                            {t("rnprobe.sent")}: {summary.sent}, {t("rnprobe.delivered")}: {summary.delivered}, {t("rnprobe.timeouts")}: {summary.timeouts}, {t("rnprobe.failed")}: {summary.failed}
                        </div>
                    </div>
                {/if}
            </div>

            <div class="glass-card flex flex-col min-h-[320px] space-y-3">
                <div class="flex items-center justify-between gap-4">
                    <div>
                        <div class="text-sm font-semibold text-sem-fg">
                            {t("rnprobe.probe_results")}
                        </div>
                        <div class="text-xs text-sem-fg-muted">
                            {t("rnprobe.probe_responses_realtime")}
                        </div>
                    </div>
                </div>

                <div
                    class="flex-1 overflow-y-auto rounded-2xl bg-black/80 text-emerald-300 font-mono text-xs p-3 space-y-2 shadow-inner border border-zinc-900"
                >
                    {#if results.length === 0}
                        <div class="text-emerald-500/80">
                            {t("rnprobe.no_probes_yet")}
                        </div>
                    {:else}
                        {#each results as result, index (`${index}-${result.probe_number}`)}
                            <div class="space-y-1">
                                <div class="flex items-center gap-2">
                                    <span class="text-emerald-400">
                                        {t("rnprobe.probe_number", { number: result.probe_number })}
                                    </span>
                                    <span class="text-gray-400">({result.size} {t("rnprobe.bytes")})</span>
                                    <span class="text-gray-400">-&gt;</span>
                                    <span class="text-emerald-300">{result.destination}</span>
                                </div>
                                {#if result.via || result.interface}
                                    <div class="text-gray-500 ml-4">
                                        {result.via || ""}{result.interface || ""}
                                    </div>
                                {/if}
                                {#if isProbeDelivered(result)}
                                    <div class="text-green-400 ml-4 space-y-1">
                                        <div>{t("rnprobe.summary")}: {t("rnprobe.delivered")}</div>
                                        <div>{t("rnprobe.hops")}: {result.hops}</div>
                                        <div>{t("rnprobe.rtt")}: {result.rtt_string}</div>
                                        {#if result.reception_stats}
                                            <div class="space-x-2">
                                                {#if result.reception_stats.rssi != null}
                                                    <span>{t("rnprobe.rssi")}: {result.reception_stats.rssi} dBm</span>
                                                {/if}
                                                {#if result.reception_stats.snr != null}
                                                    <span>{t("rnprobe.snr")}: {result.reception_stats.snr} dB</span>
                                                {/if}
                                                {#if result.reception_stats.quality != null}
                                                    <span>{t("rnprobe.quality")}: {result.reception_stats.quality}%</span>
                                                {/if}
                                            </div>
                                        {/if}
                                    </div>
                                {:else if isProbeTimeout(result)}
                                    <div class="text-yellow-400 ml-4">
                                        {t("rnprobe.summary")}: {t("rnprobe.timeout")}
                                    </div>
                                {:else}
                                    <div class="text-red-400 ml-4">
                                        {t("rnprobe.summary")}: {t("rnprobe.failed")}
                                    </div>
                                {/if}
                            </div>
                        {/each}
                    {/if}
                </div>
            </div>
        </div>
    </div>
</div>
