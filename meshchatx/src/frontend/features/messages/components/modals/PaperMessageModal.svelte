<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { tick } from "svelte";
    import QRCode from "qrcode";
    import MaterialDesignIcon from "../../../../ui/svelte/MaterialDesignIcon.svelte";
    import ToastUtils from "../../../../js/ToastUtils.js";
    import Utils from "../../../../js/Utils.js";
    import { t } from "../../../../js/i18n.js";

    let {
        messageHash = null as string | null,
        initialUri = null as string | null,
        recipientHash = null as string | null,
        onclose,
    }: {
        messageHash?: string | null;
        initialUri?: string | null;
        recipientHash?: string | null;
        onclose?: () => void;
    } = $props();

    let uri = $state<string | null>(null);
    let isLoading = $state(true);
    let isSending = $state(false);
    let qrcode: HTMLCanvasElement | undefined = $state();
    let didInit = $state(false);

    async function renderQRCode() {
        if (!uri || !qrcode) return;
        try {
            await QRCode.toCanvas(qrcode, uri, {
                width: 256,
                margin: 2,
                color: { dark: "#000000", light: "#ffffff" },
                errorCorrectionLevel: "L",
            });
            qrcode.style.maxWidth = "100%";
            qrcode.style.height = "auto";
            qrcode.classList.add("rounded-lg");
        } catch (err) {
            console.error("Failed to render QR code:", err);
            ToastUtils.error(t("messages.failed_render_qr"));
        }
    }

    async function fetchUri() {
        if (!messageHash) {
            isLoading = false;
            return;
        }
        try {
            isLoading = true;
            const response = await window.api.get(`/api/v1/lxmf-messages/${messageHash}/uri`);
            uri = response.data.uri;
            if (uri) {
                await tick();
                await renderQRCode();
            }
        } catch (e) {
            console.error("Failed to fetch message URI:", e);
        } finally {
            isLoading = false;
        }
    }

    $effect(() => {
        if (didInit) return;
        didInit = true;
        let cancelled = false;
        (async () => {
            if (initialUri) {
                uri = initialUri;
                isLoading = false;
                await tick();
                if (!cancelled) await renderQRCode();
            } else if (messageHash) {
                await fetchUri();
            } else {
                isLoading = false;
            }
        })();
        return () => {
            cancelled = true;
        };
    });

    $effect(() => {
        if (!uri || !qrcode || isLoading) return;
        void renderQRCode();
    });
    function close() {
        onclose?.();
    }

    async function copyUri() {
        if (!uri) return;
        try {
            await navigator.clipboard.writeText(uri);
            ToastUtils.success(t("messages.uri_copied"));
        } catch {
            ToastUtils.error(t("messages.failed_copy_uri"));
        }
    }

    function downloadQRCode() {
        if (!qrcode) return;
        const dataUrl = qrcode.toDataURL("image/png");
        if (!dataUrl) return;
        const link = document.createElement("a");
        const hashPrefix = messageHash ? messageHash.substring(0, 8) : String(Date.now());
        link.download = `lxmf-paper-message-${hashPrefix}.png`;
        link.href = dataUrl;
        link.click();
    }

    async function sendPaperMessage() {
        if (!recipientHash || !uri) return;
        try {
            isSending = true;
            const lxmf_message: Record<string, unknown> = {
                destination_hash: recipientHash,
                content: `Please scan the attached Paper Message or manually ingest this URI: ${uri}`,
                fields: {},
            };
            if (qrcode) {
                const dataUrl = qrcode.toDataURL("image/png");
                const imageBytes = dataUrl.split(",")[1];
                (lxmf_message.fields as Record<string, unknown>).image = {
                    image_type: "png",
                    image_bytes: imageBytes,
                    name: "paper_message_qr.png",
                };
            }
            const response = await window.api.post(`/api/v1/lxmf-messages/send`, {
                delivery_method: "opportunistic",
                lxmf_message,
            });
            if (response.data.lxmf_message) {
                ToastUtils.success(t("messages.paper_message_sent"));
                close();
            } else {
                ToastUtils.error(response.data.message || "Failed to send paper message");
            }
        } catch (err) {
            console.error("Failed to send paper message:", err);
            ToastUtils.error(t("messages.failed_send_paper"));
        } finally {
            isSending = false;
        }
    }

    function printQRCode() {
        if (!qrcode) return;
        const dataUrl = qrcode.toDataURL("image/png");
        if (!dataUrl) return;
        const printWindow = window.open("", "_blank");
        if (!printWindow) {
            ToastUtils.error("Pop-up blocked. Please allow pop-ups to print.");
            return;
        }
        printWindow.document.write(`
            <html>
                <head>
                    <title>LXMF Paper Message</title>
                    <style>
                        body { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; font-family: sans-serif; }
                        img { width: 400px; height: 400px; margin-bottom: 20px; }
                        .hash { font-family: monospace; font-size: 12px; color: #666; }
                        @media print { body { height: auto; padding: 20px; } }
                    </style>
                </head>
                <body>
                    <h1>LXMF Paper Message</h1>
                    <img src="${Utils.escapeHtml(dataUrl)}" />
                    <div class="hash">Message Hash: ${Utils.escapeHtml(messageHash || "")}</div>
                    <p>Scan this code with an LXMF-compatible app to read the message.</p>
                    <script>window.onload = () => { window.print(); window.close(); }</${"script"}>
                </body>
            </html>
        `);
        printWindow.document.close();
    }
</script>

<div
    class="fixed inset-0 z-150 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs transition-opacity"
    onclick={(e) => {
        if (e.target === e.currentTarget) close();
    }}
    onkeydown={(e) => {
        if (e.key === "Escape") close();
    }}
    role="presentation"
>
    <div
        class="w-full max-w-lg bg-sem-surface rounded-3xl shadow-2xl overflow-hidden transform transition-all scale-100"
        role="dialog"
        aria-modal="true"
    >
        <div
            class="px-6 py-5 border-b border-sem-border flex items-center justify-between bg-gray-50/50 dark:bg-zinc-900/50"
        >
            <div class="flex items-center gap-3">
                <div class="p-2 bg-blue-100 dark:bg-blue-900/30 text-sem-accent rounded-xl">
                    <MaterialDesignIcon iconName="qrcode" class="size-6" />
                </div>
                <h3 class="text-xl font-bold text-sem-fg tracking-tight">Paper Message</h3>
            </div>
            <button
                type="button"
                class="p-2 text-gray-400 hover:text-gray-600 hover:text-sem-fg hover:bg-sem-surface-muted rounded-full transition-all"
                onclick={close}
            >
                <MaterialDesignIcon iconName="close" class="size-6" />
            </button>
        </div>

        <div class="p-4 sm:p-6 flex flex-col items-center">
            {#if isLoading}
                <div class="flex flex-col items-center py-8">
                    <div class="size-12 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin"></div>
                    <p class="mt-4 text-xs text-sem-fg-muted font-medium">Generating Paper Message...</p>
                </div>
            {:else if uri}
                <div class="p-3 bg-white rounded-2xl shadow-inner border border-gray-100 mb-6 relative group">
                    <div class="size-40 sm:size-48 flex items-center justify-center overflow-hidden">
                        <canvas bind:this={qrcode}></canvas>
                    </div>
                </div>

                <div class="w-full space-y-3">
                    <div
                        class="bg-gray-50 dark:bg-zinc-800/50 rounded-2xl p-3 border border-gray-100 dark:border-zinc-700/50"
                    >
                        <div class="block text-[9px] font-bold text-sem-fg-muted uppercase tracking-widest mb-1.5">
                            LXMF URI
                        </div>
                        <div class="flex gap-2">
                            <div
                                class="flex-1 font-mono text-[10px] break-all text-sem-fg-muted bg-sem-surface p-2 rounded-lg border border-sem-border max-h-20 overflow-y-auto"
                            >
                                {uri}
                            </div>
                            <button
                                type="button"
                                class="size-9 flex items-center justify-center bg-sem-surface text-sem-fg-muted rounded-lg border border-sem-border hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200 transition-all shadow-xs"
                                title="Copy URI"
                                onclick={copyUri}
                            >
                                <MaterialDesignIcon iconName="content-copy" class="size-4" />
                            </button>
                        </div>
                    </div>

                    <div class="flex gap-2 pt-1">
                        <button
                            type="button"
                            class="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 bg-sem-action-primary hover:bg-sem-action-primary-hover text-white rounded-xl font-bold shadow-lg transition-all active:scale-[0.98] text-sm"
                            onclick={printQRCode}
                        >
                            <MaterialDesignIcon iconName="printer" class="size-4" />
                            Print
                        </button>
                        {#if recipientHash}
                            <button
                                type="button"
                                class="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold shadow-lg shadow-emerald-500/20 transition-all active:scale-[0.98] text-sm"
                                disabled={isSending}
                                onclick={sendPaperMessage}
                            >
                                {#if isSending}
                                    <div
                                        class="size-4 border-2 border-white/20 border-t-white rounded-full animate-spin"
                                    ></div>
                                    Sending...
                                {:else}
                                    <MaterialDesignIcon iconName="send" class="size-4" />
                                    Send
                                {/if}
                            </button>
                        {:else}
                            <button
                                type="button"
                                class="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 bg-sem-surface-muted hover:bg-sem-surface-muted text-sem-fg-secondary rounded-xl font-bold transition-all active:scale-[0.98] text-sm"
                                onclick={downloadQRCode}
                            >
                                <MaterialDesignIcon iconName="download" class="size-4" />
                                Save
                            </button>
                        {/if}
                    </div>
                </div>
            {:else}
                <div class="flex flex-col items-center py-12 text-center">
                    <div class="p-4 bg-red-50 dark:bg-red-900/20 text-red-500 rounded-full mb-4">
                        <MaterialDesignIcon iconName="alert-circle-outline" class="size-12" />
                    </div>
                    <h4 class="text-lg font-bold text-sem-fg mb-2">Message Not Available</h4>
                    <p class="text-sm text-sem-fg-muted max-w-xs">
                        The original message bytes are no longer available in the router queue to generate a signed
                        paper message.
                    </p>
                    <button
                        type="button"
                        class="mt-6 py-2.5 px-6 bg-sem-surface-muted text-sem-fg-secondary rounded-xl font-bold hover:bg-sem-surface-muted transition-all"
                        onclick={close}
                    >
                        Close
                    </button>
                </div>
            {/if}
        </div>
    </div>
</div>
