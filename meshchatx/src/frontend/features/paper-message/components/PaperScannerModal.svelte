<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    let {
        open = false,
        scannerError = null,
        videoElement = $bindable<HTMLVideoElement | undefined>(),
        onclose,
    }: {
        open?: boolean;
        scannerError?: string | null;
        videoElement?: HTMLVideoElement;
        onclose?: () => void;
    } = $props();
</script>

{#if open}
    <div
        class="fixed inset-0 z-210 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs"
        onclick={(e) => {
            if (e.target === e.currentTarget) onclose?.();
        }}
        onkeydown={(e) => {
            if (e.key === "Escape") onclose?.();
        }}
        role="presentation"
    >
        <div class="w-full max-w-xl rounded-2xl bg-sem-surface shadow-2xl overflow-hidden" role="dialog" aria-modal="true">
            <div class="px-5 py-4 border-b border-sem-border flex items-center justify-between">
                <h3 class="text-lg font-bold text-sem-fg">{t("messages.scan_qr")}</h3>
                <button type="button" class="text-sem-fg-muted hover:text-sem-fg" onclick={() => onclose?.()}>
                    <MaterialDesignIcon iconName="close" class="size-5" />
                </button>
            </div>
            <div class="p-5 space-y-3">
                <video
                    bind:this={videoElement}
                    class="w-full rounded-xl bg-black max-h-[60vh]"
                    autoplay
                    playsinline
                    muted
                ></video>
                <div class="text-sm text-sem-fg-muted">
                    {scannerError || t("messages.scanner_hint")}
                </div>
            </div>
        </div>
    </div>
{/if}
