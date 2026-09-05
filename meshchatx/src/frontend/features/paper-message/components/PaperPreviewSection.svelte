<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";

    let {
        generatedUri = null,
        isSending = false,
        qrcodeCanvas = $bindable<HTMLCanvasElement | undefined>(),
        oncopy,
        onprint,
        onsend,
    }: {
        generatedUri?: string | null;
        isSending?: boolean;
        qrcodeCanvas?: HTMLCanvasElement;
        oncopy?: () => void;
        onprint?: () => void;
        onsend?: () => void;
    } = $props();
</script>

{#if generatedUri}
    <section class="rounded-lg border border-sem-border overflow-hidden bg-sem-surface">
        <div class="px-4 py-3 border-b border-sem-border bg-blue-50/80 dark:bg-blue-900/20">
            <h2 class="text-base font-semibold text-sem-accent">Generated QR Code</h2>
        </div>
        <div class="px-4 py-4 sm:p-6 flex flex-col items-center text-gray-900 dark:text-gray-100">
            <div class="p-3 bg-white rounded-2xl shadow-inner border border-gray-100 mb-6">
                <div class="size-40 sm:size-48 flex items-center justify-center overflow-hidden">
                    <canvas bind:this={qrcodeCanvas}></canvas>
                </div>
            </div>

            <div class="w-full space-y-3">
                <div class="bg-gray-50 dark:bg-zinc-800/50 rounded-2xl p-3 border border-gray-100 dark:border-zinc-700/50">
                    <label
                        class="block text-[9px] font-bold text-sem-fg-muted uppercase tracking-widest mb-1.5"
                        for="paper-generated-uri"
                    >
                        LXMF URI
                    </label>
                    <div class="flex gap-2">
                        <div
                            id="paper-generated-uri"
                            class="flex-1 font-mono text-[10px] break-all text-sem-fg-muted bg-sem-surface p-2 rounded-lg border border-sem-border max-h-20 overflow-y-auto"
                        >
                            {generatedUri}
                        </div>
                        <button
                            type="button"
                            class="size-9 flex items-center justify-center bg-sem-surface text-sem-fg-muted rounded-lg border border-sem-border hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200 transition-all shadow-xs"
                            title="Copy URI"
                            onclick={() => oncopy?.()}
                        >
                            <MaterialDesignIcon iconName="content-copy" class="size-4" />
                        </button>
                    </div>
                </div>

                <div class="flex flex-col sm:flex-row gap-2 pt-1">
                    <button
                        type="button"
                        class="flex-1 flex items-center justify-center gap-2 py-3 sm:py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold transition-all active:scale-[0.98] text-sm min-h-[44px]"
                        onclick={() => onprint?.()}
                    >
                        <MaterialDesignIcon iconName="printer" class="size-4" />
                        Print
                    </button>
                    <button
                        type="button"
                        class="flex-1 flex items-center justify-center gap-2 py-3 sm:py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold transition-all active:scale-[0.98] text-sm min-h-[44px] disabled:opacity-50"
                        disabled={isSending}
                        onclick={() => onsend?.()}
                    >
                        {#if isSending}
                            <div class="size-4 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>
                            Sending...
                        {:else}
                            <MaterialDesignIcon iconName="send" class="size-4" />
                            Send
                        {/if}
                    </button>
                </div>
            </div>
        </div>
    </section>
{:else}
    <div
        class="rounded-lg border border-dashed border-gray-300 dark:border-zinc-700 bg-gray-50/50 dark:bg-zinc-900/30 flex flex-col items-center justify-center p-6 sm:p-8 text-center min-h-[240px] sm:min-h-[280px] sm:h-[320px]"
    >
        <div class="p-3 bg-sem-surface-muted text-gray-400 rounded-full mb-3">
            <MaterialDesignIcon iconName="qrcode" class="size-10" />
        </div>
        <h3 class="text-base font-bold text-sem-fg mb-1">No QR Code Generated</h3>
        <p class="text-xs text-sem-fg-muted max-w-[200px]">
            Fill out the message details and click generate to create a signed paper message.
        </p>
    </div>
{/if}
