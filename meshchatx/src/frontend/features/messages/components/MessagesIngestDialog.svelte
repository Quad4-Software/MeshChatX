<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Modal from "../../../ui/svelte/Modal.svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import {
        attachStreamToVideo,
        decodeQrFromVideo,
        describeCameraError as describeQrCameraError,
        isCameraSupported,
        startCameraStream,
    } from "../../../js/qrScannerUtils.js";
    import ToastUtils from "../../../js/ToastUtils.js";

    type Props = {
        open?: boolean;
        ingestUri?: string;
        onclose?: () => void;
        oningest?: () => void;
        onupdateIngestUri?: (uri: string) => void;
    };

    let { open = false, ingestUri = "", onclose, oningest, onupdateIngestUri }: Props = $props();

    let isScannerOpen = $state(false);
    let scannerError = $state<string | null>(null);
    let scannerVideo: HTMLVideoElement | null = $state(null);
    let scannerStream: MediaStream | null = null;
    let scannerRaf: number | null = null;

    const cameraSupported = isCameraSupported();

    function stopScanner() {
        if (scannerRaf != null) {
            cancelAnimationFrame(scannerRaf);
            scannerRaf = null;
        }
        if (scannerStream) {
            scannerStream.getTracks().forEach((track) => track.stop());
            scannerStream = null;
        }
    }

    function closeScanner() {
        isScannerOpen = false;
        stopScanner();
    }

    function describeCameraError(error: unknown): string {
        return describeQrCameraError(error, {
            permissionDenied: t("messages.camera_permission_denied"),
            notFound: t("messages.camera_not_found"),
            failed: t("messages.camera_failed"),
        });
    }

    async function openScanner() {
        scannerError = null;
        isScannerOpen = true;
        await Promise.resolve();
        if (!cameraSupported) {
            scannerError = t("messages.camera_not_supported");
            return;
        }
        try {
            const stream = await startCameraStream();
            scannerStream = stream;
            if (!(await attachStreamToVideo(stream, scannerVideo))) {
                scannerError = t("messages.camera_failed");
                stopScanner();
                return;
            }
            detectLoop();
        } catch (e) {
            scannerError = describeCameraError(e);
        }
    }

    function detectLoop() {
        if (!isScannerOpen) {
            return;
        }
        decodeQrFromVideo(scannerVideo)
            .then((qr) => {
                if (!isScannerOpen) {
                    return;
                }
                if (!qr) {
                    scannerRaf = requestAnimationFrame(() => detectLoop());
                    return;
                }
                if (!/^lxm(a|f)?:\/\//i.test(qr)) {
                    ToastUtils.error(t("messages.invalid_qr_uri"));
                    scannerRaf = requestAnimationFrame(() => detectLoop());
                    return;
                }
                onupdateIngestUri?.(qr);
                closeScanner();
                oningest?.();
            })
            .catch(() => {
                if (isScannerOpen) {
                    scannerRaf = requestAnimationFrame(() => detectLoop());
                }
            });
    }

    async function pasteFromClipboard() {
        try {
            const text = await navigator.clipboard.readText();
            onupdateIngestUri?.(text);
        } catch {
            ToastUtils.error(t("messages.failed_read_clipboard"));
        }
    }

    $effect(() => {
        if (!open) {
            closeScanner();
        }
    });
</script>

<Modal {open} title="Ingest Paper Message" maxWidth={448} onClose={() => onclose?.()}>
    <div class="space-y-4">
        <p class="text-sm text-sem-fg-muted">
            You can read LXMF paper messages by scanning a QR code or pasting an <strong>lxmf://</strong> or
            <strong>lxm://</strong> link. Contact-sharing links using <strong>lxma://</strong> are also supported.
        </p>
        <div>
            <label class="block text-xs font-medium text-sem-fg-muted uppercase tracking-wider mb-1" for="ingest-uri">
                LXMF URI
            </label>
            <div class="flex gap-2">
                <input
                    id="ingest-uri"
                    type="text"
                    value={ingestUri}
                    placeholder="lxmf://... or lxma://..."
                    class="input-field flex-1 min-w-0"
                    oninput={(e) => onupdateIngestUri?.((e.currentTarget as HTMLInputElement).value)}
                    onkeydown={(e) => {
                        if (e.key === "Enter") oningest?.();
                    }}
                />
                <button
                    type="button"
                    class="px-3 py-2 bg-sem-surface-muted text-sem-fg-muted rounded-lg hover:bg-sem-surface-muted focus-ring-sem transition-colors"
                    title="Paste from Clipboard"
                    onclick={() => void pasteFromClipboard()}
                >
                    <MaterialDesignIcon iconName="clipboard-text-outline" class="size-5" />
                </button>
                {#if cameraSupported}
                    <button
                        type="button"
                        class="px-3 py-2 bg-sem-surface-muted text-sem-fg-muted rounded-lg hover:bg-sem-surface-muted focus-ring-sem transition-colors"
                        title={t("messages.scan_qr")}
                        onclick={() => void openScanner()}
                    >
                        <MaterialDesignIcon iconName="qrcode-scan" class="size-5" />
                    </button>
                {/if}
            </div>
        </div>
        <button
            type="button"
            class="primary-chip w-full! rounded-xl! py-2.5! text-sm! focus-ring-sem"
            disabled={!ingestUri}
            onclick={() => oningest?.()}
        >
            Read LXM
        </button>
        {#if !cameraSupported}
            <p class="text-xs text-sem-fg-muted">{t("messages.camera_not_supported")}</p>
        {/if}
    </div>
</Modal>

<Modal open={isScannerOpen} title={t("messages.scan_qr")} maxWidth={576} onClose={closeScanner}>
    <div class="space-y-3">
        <video bind:this={scannerVideo} class="w-full rounded-xl bg-black max-h-[60vh]" autoplay playsinline muted
        ></video>
        <div class="text-sm text-sem-fg-muted">{scannerError || t("messages.scanner_hint")}</div>
    </div>
</Modal>
