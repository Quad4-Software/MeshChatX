<!-- SPDX-License-Identifier: 0BSD -->

<script>
    import { onDestroy } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import {
        attachStreamToVideo,
        decodeQrFromVideo,
        describeCameraError as describeQrCameraError,
        isCameraSupported,
        startCameraStream,
    } from "../../../js/qrScannerUtils.js";
    import ToastUtils from "../../../js/ToastUtils.js";
    import { t } from "../../../js/i18n.js";

    /**
     * @type {{
     *   open?: boolean,
     *   onClose?: () => void,
     *   onScanned?: (value: string) => void,
     * }}
     */
    let { open = false, onClose, onScanned } = $props();

    /** @type {HTMLVideoElement | undefined} */
    let scannerVideo = $state();
    let scannerError = $state(/** @type {string | null} */ (null));
    /** @type {MediaStream | null} */
    let scannerStream = null;
    /** @type {number | null} */
    let scannerAnimationFrame = null;

    const cameraSupported = isCameraSupported();

    function stopScanner() {
        if (scannerAnimationFrame != null) {
            cancelAnimationFrame(scannerAnimationFrame);
            scannerAnimationFrame = null;
        }
        if (scannerStream) {
            scannerStream.getTracks().forEach((track) => track.stop());
            scannerStream = null;
        }
    }

    function detectQrLoop() {
        if (!open) {
            return;
        }
        decodeQrFromVideo(scannerVideo)
            .then((qr) => {
                if (!open) {
                    return;
                }
                if (qr) {
                    onScanned?.(qr);
                    ToastUtils.success(t("contacts.qr_scanned"));
                    onClose?.();
                    return;
                }
                scannerAnimationFrame = requestAnimationFrame(() => detectQrLoop());
            })
            .catch(() => {
                if (open) {
                    scannerAnimationFrame = requestAnimationFrame(() => detectQrLoop());
                }
            });
    }

    async function startScanner() {
        if (!cameraSupported) {
            scannerError = t("contacts.camera_not_supported");
            return;
        }
        try {
            const stream = await startCameraStream();
            if (!stream.getVideoTracks().length) {
                scannerError = t("contacts.camera_not_found");
                stream.getTracks().forEach((track) => track.stop());
                return;
            }
            scannerStream = stream;
            if (!(await attachStreamToVideo(stream, scannerVideo))) {
                return;
            }
            detectQrLoop();
        } catch (e) {
            scannerError = describeQrCameraError(e, {
                permissionDenied: t("contacts.camera_permission_denied"),
                notFound: t("contacts.camera_not_found"),
                failed: t("contacts.camera_failed"),
            });
        }
    }

    $effect(() => {
        if (!open) {
            return;
        }
        scannerError = null;
        let cancelled = false;
        queueMicrotask(() => {
            if (!cancelled) {
                void startScanner();
            }
        });
        return () => {
            cancelled = true;
            stopScanner();
        };
    });

    onDestroy(() => {
        stopScanner();
    });
</script>

{#if open}
    <div
        class="fixed inset-0 z-220 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs"
        onclick={(e) => {
            if (e.target === e.currentTarget) onClose?.();
        }}
        onkeydown={(e) => {
            if (e.key === "Escape") onClose?.();
        }}
        role="presentation"
    >
        <div
            class="w-full max-w-xl rounded-2xl bg-sem-surface shadow-2xl overflow-hidden"
            role="dialog"
            aria-modal="true"
        >
            <div class="px-5 py-4 border-b border-sem-border flex items-center justify-between">
                <h3 class="text-lg font-bold text-sem-fg">{t("contacts.scan_qr")}</h3>
                <button type="button" class="text-sem-fg-muted hover:text-sem-fg" onclick={() => onClose?.()}>
                    <MaterialDesignIcon iconName="close" class="size-5" />
                </button>
            </div>
            <div class="p-5 space-y-3">
                <video
                    bind:this={scannerVideo}
                    class="w-full rounded-xl bg-black max-h-[60vh]"
                    autoplay
                    playsinline
                    muted
                ></video>
                <div class="text-sm text-sem-fg-muted">{scannerError || t("contacts.scanner_hint")}</div>
            </div>
        </div>
    </div>
{/if}
