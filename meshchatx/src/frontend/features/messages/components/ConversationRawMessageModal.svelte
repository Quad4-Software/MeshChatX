<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    type RawMessageData = {
        id?: string | number;
        state?: string;
        is_incoming?: boolean;
        hash?: string;
        source_hash?: string;
        destination_hash?: string;
        path_interface_at_send?: string | null;
        path_hops_at_send?: number | null;
        path_finding_measure?: string | null;
        path_row_hash_hex?: string | null;
        method?: string;
        rssi?: string | number | null;
        snr?: string | number | null;
        delivery_attempts?: number;
        content?: string;
        raw_uri?: string | null;
        [key: string]: unknown;
    };

    let {
        open = false,
        rawMessageData = {} as RawMessageData,
        rawMessageJsonPreview = "",
        isBodyOversized = false,
        bodyCharCount = 0,
        hasStoredPath = false,
        onclose,
        oncopyhash,
        oncopycontent,
    }: {
        open?: boolean;
        rawMessageData?: RawMessageData;
        rawMessageJsonPreview?: string;
        isBodyOversized?: boolean;
        bodyCharCount?: number;
        hasStoredPath?: boolean;
        onclose?: () => void;
        oncopyhash?: (hash: string) => void;
        oncopycontent?: () => void;
    } = $props();

    const stateClass = $derived(
        rawMessageData.state === "delivered"
            ? "bg-green-50 text-green-700 ring-green-600/20 dark:bg-green-900/30 dark:text-green-400"
            : "bg-blue-50 text-blue-700 ring-blue-700/10 dark:bg-blue-900/30 dark:text-blue-400"
    );
</script>

{#if open}
    <div
        class="fixed inset-0 z-150 flex items-center justify-center p-4 pt-[max(0.75rem,env(safe-area-inset-top))] pb-[max(0.75rem,env(safe-area-inset-bottom))] bg-black/60 backdrop-blur-xs"
        onclick={(e) => {
            if (e.target === e.currentTarget) onclose?.();
        }}
        onkeydown={(e) => {
            if (e.key === "Escape") onclose?.();
        }}
        role="presentation"
    >
        <div
            class="w-full max-w-2xl bg-sem-surface rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[min(90dvh,48rem)]"
            role="dialog"
            aria-modal="true"
        >
            <div class="px-6 py-4 border-b border-sem-border flex items-center justify-between shrink-0">
                <h3 class="text-lg font-bold text-sem-fg">Raw LXMF Message</h3>
                <button
                    type="button"
                    class="text-gray-400 hover:text-gray-500 dark:hover:text-zinc-300 transition-colors"
                    onclick={() => onclose?.()}
                >
                    <MaterialDesignIcon iconName="close" class="size-6" />
                </button>
            </div>
            <div class="p-0 overflow-y-auto bg-gray-50 dark:bg-zinc-950 grow">
                <div class="p-6 space-y-6">
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <div class="space-y-1">
                            <div class="text-[10px] font-bold uppercase tracking-wider text-sem-fg-muted">
                                Message ID
                            </div>
                            <div class="text-sm font-mono text-sem-fg">{rawMessageData.id}</div>
                        </div>
                        <div class="space-y-1">
                            <div class="text-[10px] font-bold uppercase tracking-wider text-sem-fg-muted">State</div>
                            <div class="flex items-center gap-2">
                                <span
                                    class="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset {stateClass}"
                                >
                                    {rawMessageData.state}
                                </span>
                                <span class="text-[10px] text-gray-400">
                                    {rawMessageData.is_incoming ? "Incoming" : "Outbound"}
                                </span>
                            </div>
                        </div>
                    </div>

                    <div class="space-y-1">
                        <div class="text-[10px] font-bold uppercase tracking-wider text-sem-fg-muted">Message Hash</div>
                        <div
                            class="text-sm font-mono break-all text-sem-fg bg-sem-surface p-2 rounded-sm border border-sem-border"
                        >
                            {rawMessageData.hash}
                        </div>
                    </div>

                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <div class="space-y-1">
                            <div class="text-[10px] font-bold uppercase tracking-wider text-sem-fg-muted">
                                Source Hash
                            </div>
                            <div class="text-xs font-mono break-all text-sem-fg">{rawMessageData.source_hash}</div>
                        </div>
                        <div class="space-y-1">
                            <div class="text-[10px] font-bold uppercase tracking-wider text-sem-fg-muted">
                                Destination Hash
                            </div>
                            <div class="text-xs font-mono break-all text-sem-fg">{rawMessageData.destination_hash}</div>
                        </div>
                    </div>

                    {#if hasStoredPath}
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div class="space-y-1">
                                <div class="text-[10px] font-bold uppercase tracking-wider text-sem-fg-muted">
                                    {t("messages.raw_path_interface_at_send")}
                                </div>
                                <div class="text-sm text-sem-fg wrap-break-word">
                                    {rawMessageData.path_interface_at_send != null &&
                                    rawMessageData.path_interface_at_send !== ""
                                        ? rawMessageData.path_interface_at_send
                                        : t("messages.raw_path_value_unknown")}
                                </div>
                            </div>
                            <div class="space-y-1">
                                <div class="text-[10px] font-bold uppercase tracking-wider text-sem-fg-muted">
                                    {t("messages.raw_path_hops_at_send")}
                                </div>
                                <div class="text-sm text-sem-fg">
                                    {rawMessageData.path_hops_at_send != null
                                        ? rawMessageData.path_hops_at_send
                                        : t("messages.raw_path_value_unknown")}
                                </div>
                            </div>
                        </div>
                    {/if}

                    {#if rawMessageData.path_finding_measure || rawMessageData.path_row_hash_hex}
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div class="space-y-1">
                                <div class="text-[10px] font-bold uppercase tracking-wider text-sem-fg-muted">
                                    {t("messages.raw_path_finding_measure")}
                                </div>
                                <div class="text-sm font-mono text-sem-fg wrap-break-word">
                                    {rawMessageData.path_finding_measure || t("messages.raw_path_value_unknown")}
                                </div>
                            </div>
                            <div class="space-y-1">
                                <div class="text-[10px] font-bold uppercase tracking-wider text-sem-fg-muted">
                                    {t("messages.raw_path_row_hash_rnpath")}
                                </div>
                                <div class="flex flex-wrap items-center gap-2">
                                    <div class="text-xs font-mono break-all text-sem-fg">
                                        {rawMessageData.path_row_hash_hex || t("messages.raw_path_value_unknown")}
                                    </div>
                                    {#if rawMessageData.path_row_hash_hex}
                                        <button
                                            type="button"
                                            class="text-xs text-sem-accent hover:underline shrink-0"
                                            onclick={() => oncopyhash?.(String(rawMessageData.path_row_hash_hex))}
                                        >
                                            {t("messages.copy_hash")}
                                        </button>
                                    {/if}
                                </div>
                                <div class="text-[10px] text-sem-fg-muted">
                                    {t("messages.raw_path_row_hash_rnpath_hint")}
                                </div>
                            </div>
                        </div>
                    {/if}

                    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        <div class="space-y-1">
                            <div class="text-[10px] font-bold uppercase tracking-wider text-sem-fg-muted">Method</div>
                            <div class="text-sm text-sem-fg capitalize">{rawMessageData.method}</div>
                        </div>
                        <div class="space-y-1">
                            <div class="text-[10px] font-bold uppercase tracking-wider text-sem-fg-muted">RSSI</div>
                            <div class="text-sm text-sem-fg">{rawMessageData.rssi || "N/A"}</div>
                        </div>
                        <div class="space-y-1">
                            <div class="text-[10px] font-bold uppercase tracking-wider text-sem-fg-muted">SNR</div>
                            <div class="text-sm text-sem-fg">{rawMessageData.snr || "N/A"}</div>
                        </div>
                        <div class="space-y-1">
                            <div class="text-[10px] font-bold uppercase tracking-wider text-sem-fg-muted">Attempts</div>
                            <div class="text-sm text-sem-fg">{rawMessageData.delivery_attempts}</div>
                        </div>
                    </div>

                    <div class="space-y-1">
                        <div class="text-[10px] font-bold uppercase tracking-wider text-sem-fg-muted">
                            Content / App Data
                        </div>
                        {#if !isBodyOversized}
                            <div
                                class="text-xs font-mono bg-sem-surface p-3 rounded-sm border border-sem-border whitespace-pre-wrap break-all text-sem-fg-muted"
                            >
                                {rawMessageData.content}
                            </div>
                        {:else}
                            <div
                                class="rounded-lg border border-amber-200/90 dark:border-amber-800/50 bg-amber-50/90 dark:bg-amber-950/25 p-3 space-y-2"
                            >
                                <p class="text-xs text-amber-950 dark:text-amber-100/90 leading-relaxed">
                                    {t("messages.oversized_body_notice", { count: bodyCharCount })}
                                </p>
                                <button
                                    type="button"
                                    class="inline-flex items-center gap-2 rounded-lg bg-amber-700 hover:bg-amber-800 dark:bg-amber-700 dark:hover:bg-amber-600 px-3 py-2 text-xs font-semibold text-white transition-colors"
                                    onclick={() => oncopycontent?.()}
                                >
                                    <MaterialDesignIcon iconName="content-copy" class="size-4 shrink-0" />
                                    {t("messages.oversized_body_copy")}
                                </button>
                            </div>
                        {/if}
                    </div>

                    {#if rawMessageData.raw_uri}
                        <div class="space-y-1">
                            <div class="text-[10px] font-bold uppercase tracking-wider text-sem-fg-muted">
                                Raw LXMF URI
                            </div>
                            <div
                                class="text-[10px] font-mono bg-sem-surface p-2 rounded-sm border border-sem-border break-all text-sem-fg-muted"
                            >
                                {rawMessageData.raw_uri}
                            </div>
                        </div>
                    {/if}

                    <details class="group">
                        <summary
                            class="flex items-center gap-2 cursor-pointer text-[10px] font-bold uppercase tracking-wider text-sem-fg-muted hover:text-sem-fg transition-colors"
                        >
                            <MaterialDesignIcon
                                iconName="chevron-right"
                                class="size-4 group-open:rotate-90 transition-transform"
                            />
                            View Full JSON Object
                        </summary>
                        <div class="mt-2 p-4 bg-black/5 dark:bg-black/20 rounded-lg overflow-x-auto">
                            <pre class="text-[10px] font-mono text-sem-fg-muted">{rawMessageJsonPreview}</pre>
                        </div>
                    </details>
                </div>
            </div>
            <div class="px-6 py-4 border-t border-sem-border flex justify-end shrink-0">
                <button
                    type="button"
                    class="px-4 py-2 bg-sem-action-primary hover:bg-sem-action-primary-hover text-white rounded-lg text-sm font-bold transition-colors"
                    onclick={() => onclose?.()}
                >
                    Close
                </button>
            </div>
        </div>
    </div>
{/if}
