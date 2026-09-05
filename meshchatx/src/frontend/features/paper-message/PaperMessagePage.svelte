<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, tick } from "svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import WebSocketConnection from "../../js/WebSocketConnection.js";
    import ToastUtils from "../../js/ToastUtils.js";
    import { t } from "../../js/i18n.js";
    import { onWsEvent, offWsEvent } from "../../js/registries/wsEventRegistry.js";
    import {
        attachStreamToVideo,
        decodeQrFromVideo,
        describeCameraError as describeQrCameraError,
        isCameraSupported,
        startCameraStream,
    } from "../../js/qrScannerUtils.js";
    import { canGeneratePaperMessage, isValidLxmUri, renderQrCodeToCanvas } from "./lib/paperQr.js";
    import { downloadPaperQr, printPaperQr } from "./lib/paperPrint.js";
    import { sendPaperMessageApi } from "./lib/paperSend.js";
    import type { LxmGeneratePaperUriWsResult, LxmIngestUriWsResult } from "./lib/types.js";
    import PaperComposer from "./components/PaperComposer.svelte";
    import PaperIngestSection from "./components/PaperIngestSection.svelte";
    import PaperPreviewSection from "./components/PaperPreviewSection.svelte";
    import PaperScannerModal from "./components/PaperScannerModal.svelte";

    let destinationHash = $state("");
    let title = $state("");
    let content = $state("");
    let isGenerating = $state(false);
    let generatedUri = $state<string | null>(null);
    let ingestUri = $state("");
    let isSending = $state(false);
    let isIngestScannerModalOpen = $state(false);
    let ingestScannerError = $state<string | null>(null);
    let qrcodeCanvas = $state<HTMLCanvasElement | undefined>();
    let scannerVideo = $state<HTMLVideoElement | undefined>();

    let scannerStream: MediaStream | null = null;
    let scannerAnimationFrame: number | null = null;

    const canGenerate = $derived(canGeneratePaperMessage(destinationHash, content));
    const cameraSupported = isCameraSupported();

    async function onGeneratePaperUriResult(json: LxmGeneratePaperUriWsResult): Promise<void> {
        isGenerating = false;
        if (json.status === "success") {
            generatedUri = json.uri || null;
            await tick();
            if (qrcodeCanvas && generatedUri) {
                await renderQrCodeToCanvas(qrcodeCanvas, generatedUri);
            }
        } else {
            ToastUtils.error(json.message || "Failed to generate paper message");
        }
    }

    function onIngestUriResult(json: LxmIngestUriWsResult): void {
        if (json.status === "success") {
            ingestUri = "";
        }
    }

    function generatePaperMessage(): void {
        if (!canGenerate) {
            return;
        }
        isGenerating = true;
        generatedUri = null;
        WebSocketConnection.send(
            JSON.stringify({
                type: "lxm.generate_paper_uri",
                destination_hash: destinationHash,
                content,
                title,
            })
        );
    }

    function ingestPaperMessage(): void {
        if (!ingestUri) {
            return;
        }
        WebSocketConnection.send(
            JSON.stringify({
                type: "lxm.ingest_uri",
                uri: ingestUri,
            })
        );
    }

    async function pasteFromClipboard(): Promise<void> {
        try {
            ingestUri = await navigator.clipboard.readText();
        } catch {
            ToastUtils.error(t("messages.failed_read_clipboard"));
        }
    }

    async function copyUri(): Promise<void> {
        if (!generatedUri) {
            return;
        }
        try {
            await navigator.clipboard.writeText(generatedUri);
            ToastUtils.success(t("messages.uri_copied"));
        } catch {
            ToastUtils.error(t("messages.failed_copy_uri"));
        }
    }

    function printQRCode(): void {
        if (!qrcodeCanvas) {
            return;
        }
        printPaperQr({ canvas: qrcodeCanvas, destinationHash });
    }

    export function downloadQRCode(): void {
        if (!qrcodeCanvas) {
            return;
        }
        downloadPaperQr(qrcodeCanvas);
    }

    async function sendPaperMessage(): Promise<void> {
        if (!destinationHash || !generatedUri) {
            return;
        }
        isSending = true;
        try {
            const res = await sendPaperMessageApi({
                destinationHash,
                generatedUri,
                canvas: qrcodeCanvas,
            });
            if (res.success) {
                generatedUri = null;
                destinationHash = "";
                content = "";
                title = "";
            }
        } finally {
            isSending = false;
        }
    }

    function describeCameraError(error: unknown): string {
        return describeQrCameraError(error, {
            permissionDenied: t("messages.camera_permission_denied"),
            notFound: t("messages.camera_not_found"),
            failed: t("messages.camera_failed"),
        });
    }

    function stopIngestScanner(): void {
        if (scannerAnimationFrame != null) {
            cancelAnimationFrame(scannerAnimationFrame);
            scannerAnimationFrame = null;
        }
        if (scannerStream) {
            scannerStream.getTracks().forEach((track) => track.stop());
            scannerStream = null;
        }
    }

    function closeIngestScannerModal(): void {
        isIngestScannerModalOpen = false;
        stopIngestScanner();
    }

    function detectIngestQrLoop(): void {
        if (!isIngestScannerModalOpen) {
            return;
        }
        decodeQrFromVideo(scannerVideo)
            .then((qr) => {
                if (!isIngestScannerModalOpen) {
                    return;
                }
                if (!qr) {
                    scannerAnimationFrame = requestAnimationFrame(() => detectIngestQrLoop());
                    return;
                }
                if (!isValidLxmUri(qr)) {
                    ToastUtils.error(t("messages.invalid_qr_uri"));
                    scannerAnimationFrame = requestAnimationFrame(() => detectIngestQrLoop());
                    return;
                }
                ingestUri = qr;
                closeIngestScannerModal();
                ingestPaperMessage();
            })
            .catch(() => {
                if (isIngestScannerModalOpen) {
                    scannerAnimationFrame = requestAnimationFrame(() => detectIngestQrLoop());
                }
            });
    }

    async function startIngestScanner(): Promise<void> {
        if (!cameraSupported) {
            ingestScannerError = t("messages.camera_not_supported");
            return;
        }
        try {
            const stream = await startCameraStream();
            scannerStream = stream;
            if (!(await attachStreamToVideo(stream, scannerVideo))) {
                ingestScannerError = t("messages.camera_failed");
                stopIngestScanner();
                return;
            }
            detectIngestQrLoop();
        } catch (e) {
            ingestScannerError = describeCameraError(e);
        }
    }

    async function openIngestScannerModal(): Promise<void> {
        ingestScannerError = null;
        isIngestScannerModalOpen = true;
        await tick();
        await startIngestScanner();
    }

    $effect(() => {
        if (generatedUri && qrcodeCanvas) {
            void renderQrCodeToCanvas(qrcodeCanvas, generatedUri);
        }
    });

    onMount(() => {
        onWsEvent("lxm.generate_paper_uri.result", onGeneratePaperUriResult);
        onWsEvent("lxm.ingest_uri.result", onIngestUriResult);
        return () => {
            offWsEvent("lxm.generate_paper_uri.result", onGeneratePaperUriResult);
            offWsEvent("lxm.ingest_uri.result", onIngestUriResult);
            stopIngestScanner();
        };
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas" data-testid="paper-message-page">
    <ToolsPageHeader
        icon="qrcode"
        title={t("tools.paper_message.title")}
        description={t("tools.paper_message.description")}
        accent="blue"
    />
    <div class="flex-1 overflow-y-auto w-full pb-[max(1rem,env(safe-area-inset-bottom))]">
        <div class="p-3 sm:p-4 md:p-6 max-w-5xl mx-auto w-full space-y-4 min-w-0">
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div class="space-y-4 min-w-0">
                    <PaperComposer
                        bind:destinationHash
                        bind:title
                        bind:content
                        {isGenerating}
                        {canGenerate}
                        ongenerate={generatePaperMessage}
                    />

                    <PaperIngestSection
                        bind:ingestUri
                        {cameraSupported}
                        onpaste={pasteFromClipboard}
                        onscan={openIngestScannerModal}
                        oningest={ingestPaperMessage}
                    />
                </div>

                <div class="space-y-4 min-w-0">
                    <PaperPreviewSection
                        {generatedUri}
                        {isSending}
                        bind:qrcodeCanvas
                        oncopy={copyUri}
                        onprint={printQRCode}
                        onsend={sendPaperMessage}
                    />
                </div>
            </div>
        </div>
    </div>

    <PaperScannerModal
        open={isIngestScannerModalOpen}
        scannerError={ingestScannerError}
        bind:videoElement={scannerVideo}
        onclose={closeIngestScannerModal}
    />
</div>
