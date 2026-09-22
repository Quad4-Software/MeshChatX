<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onDestroy } from "svelte";
    import Modal from "../../../ui/svelte/Modal.svelte";
    import {
        attachStreamToVideo,
        decodeQrFromVideo,
        describeCameraError as describeQrCameraError,
        isCameraSupported,
        startCameraStream,
    } from "../../../js/qrScannerUtils.js";
    import ToastUtils from "../../../js/ToastUtils.js";
    import { t } from "../../../js/i18n.js";

    let {
        open = $bindable(false),
        onClose,
        onScanned,
    }: {
        open?: boolean;
        onClose?: () => void;
        onScanned?: (value: string) => void;
    } = $props();

    let scannerVideo: HTMLVideoElement | undefined = $state();
    let scannerError: string | null = $state(null);
    let scannerStream: MediaStream | null = null;
    let scannerAnimationFrame: number | null = null;

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

    function handleClose() {
        open = false;
        stopScanner();
        onClose?.();
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
                    handleClose();
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

<Modal bind:open title={t("contacts.scan_qr")} maxWidth={576} onClose={handleClose}>
    <div class="p-5 space-y-3">
        <video bind:this={scannerVideo} class="w-full rounded-xl bg-black max-h-[60vh]" autoplay playsinline muted
        ></video>
        <div class="text-sm text-sem-fg-muted">{scannerError || t("contacts.scanner_hint")}</div>
    </div>
</Modal>
