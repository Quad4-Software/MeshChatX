<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Modal from "../../../ui/svelte/Modal.svelte";
    import { t } from "../../../js/i18n.js";

    let {
        open = $bindable(false),
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

<Modal bind:open title={t("messages.scan_qr")} onClose={onclose} maxWidth={576}>
    <div class="space-y-3">
        <video bind:this={videoElement} class="w-full rounded-xl bg-black max-h-[60vh]" autoplay playsinline muted
        ></video>
        <div class="text-sm text-sem-fg-muted">
            {scannerError || t("messages.scanner_hint")}
        </div>
    </div>
</Modal>
