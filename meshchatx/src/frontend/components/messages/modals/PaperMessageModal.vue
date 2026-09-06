<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="fixed inset-0 z-150 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs transition-opacity"
        @click.self="close"
    >
        <div
            class="w-full max-w-lg bg-sem-surface rounded-3xl shadow-2xl overflow-hidden transform transition-all scale-100"
        >
            <!-- header -->
            <div
                class="px-6 py-5 border-b border-sem-border flex items-center justify-between bg-sem-surface-muted/50 dark:bg-zinc-900/50"
            >
                <div class="flex items-center gap-3">
                    <div class="p-2 bg-blue-100 dark:bg-blue-900/30 text-sem-accent rounded-xl">
                        <MaterialDesignIcon icon-name="qrcode" class="size-6" />
                    </div>
                    <h3 class="text-xl font-bold text-sem-fg tracking-tight">Paper Message</h3>
                </div>
                <button
                    type="button"
                    class="p-2 text-sem-fg-muted hover:text-sem-fg-muted hover:text-sem-fg hover:bg-sem-surface-muted rounded-full transition-all"
                    @click="close"
                >
                    <MaterialDesignIcon icon-name="close" class="size-6" />
                </button>
            </div>

            <div class="p-4 sm:p-6 flex flex-col items-center">
                <div v-if="isLoading" class="flex flex-col items-center py-8">
                    <div
                        class="size-12 border-4 border-sem-accent/20 border-t-blue-500 rounded-full animate-spin"
                    ></div>
                    <p class="mt-4 text-xs text-sem-fg-muted font-medium">Generating Paper Message...</p>
                </div>
                <template v-else-if="uri">
                    <!-- QR code container -->
                    <div class="p-3 bg-white rounded-2xl shadow-inner border border-sem-border mb-6 relative group">
                        <div class="size-40 sm:size-48 flex items-center justify-center overflow-hidden">
                            <canvas ref="qrcode"></canvas>
                        </div>
                        <div
                            class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-white/10 backdrop-blur-[2px] rounded-2xl pointer-events-none"
                        >
                            <div
                                class="p-2 bg-white/90 dark:bg-zinc-900/90 rounded-xl shadow-xl border border-sem-border"
                            >
                                <MaterialDesignIcon icon-name="magnify-plus-outline" class="size-6 text-sem-accent" />
                            </div>
                        </div>
                    </div>

                    <div v-if="recipientHash" class="w-full space-y-3">
                        <div class="bg-sem-surface-muted/50 rounded-2xl p-3 border border-sem-border /50">
                            <label
                                class="block text-[9px] font-bold text-sem-fg-muted uppercase tracking-widest mb-1.5"
                            >
                                LXMF URI
                            </label>
                            <div class="flex gap-2">
                                <div
                                    class="flex-1 font-mono text-[10px] break-all text-sem-fg-muted bg-sem-surface p-2 rounded-lg border border-sem-border max-h-20 overflow-y-auto"
                                >
                                    {{ uri }}
                                </div>
                                <button
                                    type="button"
                                    class="size-9 flex items-center justify-center bg-sem-surface text-sem-fg-muted rounded-lg border border-sem-border hover:bg-blue-50 hover:text-sem-accent hover:border-blue-200 transition-all shadow-xs"
                                    title="Copy URI"
                                    @click="copyUri"
                                >
                                    <MaterialDesignIcon icon-name="content-copy" class="size-4" />
                                </button>
                            </div>
                        </div>

                        <div class="flex gap-2 pt-1">
                            <button
                                type="button"
                                class="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 bg-sem-action-primary hover:bg-sem-action-primary-hover text-white rounded-xl font-bold shadow-lg shadow-blue-500/20 transition-all active:scale-[0.98] text-sm"
                                @click="printQRCode"
                            >
                                <MaterialDesignIcon icon-name="printer" class="size-4" />
                                Print
                            </button>
                            <button
                                type="button"
                                class="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold shadow-lg shadow-emerald-500/20 transition-all active:scale-[0.98] text-sm"
                                :disabled="isSending"
                                @click="sendPaperMessage"
                            >
                                <template v-if="isSending">
                                    <div
                                        class="size-4 border-2 border-white/20 border-t-white rounded-full animate-spin"
                                    ></div>
                                    Sending...
                                </template>
                                <template v-else>
                                    <MaterialDesignIcon icon-name="send" class="size-4" />
                                    Send
                                </template>
                            </button>
                        </div>
                    </div>
                    <div v-else class="w-full space-y-3">
                        <div class="bg-sem-surface-muted/50 rounded-2xl p-3 border border-sem-border /50">
                            <label
                                class="block text-[9px] font-bold text-sem-fg-muted uppercase tracking-widest mb-1.5"
                            >
                                LXMF URI
                            </label>
                            <div class="flex gap-2">
                                <div
                                    class="flex-1 font-mono text-[10px] break-all text-sem-fg-muted bg-sem-surface p-2 rounded-lg border border-sem-border max-h-20 overflow-y-auto"
                                >
                                    {{ uri }}
                                </div>
                                <button
                                    type="button"
                                    class="size-9 flex items-center justify-center bg-sem-surface text-sem-fg-muted rounded-lg border border-sem-border hover:bg-blue-50 hover:text-sem-accent hover:border-blue-200 transition-all shadow-xs"
                                    title="Copy URI"
                                    @click="copyUri"
                                >
                                    <MaterialDesignIcon icon-name="content-copy" class="size-4" />
                                </button>
                            </div>
                        </div>

                        <div class="flex gap-2 pt-1">
                            <button
                                type="button"
                                class="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 bg-sem-action-primary hover:bg-sem-action-primary-hover text-white rounded-xl font-bold shadow-lg shadow-blue-500/20 transition-all active:scale-[0.98] text-sm"
                                @click="printQRCode"
                            >
                                <MaterialDesignIcon icon-name="printer" class="size-4" />
                                Print
                            </button>
                            <button
                                type="button"
                                class="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 bg-sem-surface-muted hover:bg-sem-surface-muted hover:bg-sem-surface-muted text-sem-fg-secondary rounded-xl font-bold transition-all active:scale-[0.98] text-sm"
                                @click="downloadQRCode"
                            >
                                <MaterialDesignIcon icon-name="download" class="size-4" />
                                Save
                            </button>
                        </div>
                    </div>
                </template>
                <div v-else class="flex flex-col items-center py-12 text-center">
                    <div class="p-4 bg-red-50 dark:bg-red-900/20 text-red-500 rounded-full mb-4">
                        <MaterialDesignIcon icon-name="alert-circle-outline" class="size-12" />
                    </div>
                    <h4 class="text-lg font-bold text-sem-fg mb-2">Message Not Available</h4>
                    <p class="text-sm text-sem-fg-muted max-w-xs">
                        The original message bytes are no longer available in the router queue to generate a signed
                        paper message.
                    </p>
                    <button
                        type="button"
                        class="mt-6 py-2.5 px-6 bg-sem-surface-muted text-sem-fg-secondary rounded-xl font-bold hover:bg-sem-surface-muted hover:bg-sem-surface-muted transition-all"
                        @click="close"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import QRCode from "qrcode";
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";
import ToastUtils from "../../../js/ToastUtils";
import Utils from "../../../js/Utils";

export default {
    name: "PaperMessageModal",
    components: { MaterialDesignIcon },
    props: {
        messageHash: {
            type: String,
            required: false,
            default: null,
        },
        initialUri: {
            type: String,
            required: false,
            default: null,
        },
        recipientHash: {
            type: String,
            required: false,
            default: null,
        },
    },
    emits: ["close"],
    data() {
        return {
            uri: this.initialUri,
            isLoading: !this.initialUri,
            isSending: false,
        };
    },
    async mounted() {
        if (!this.uri && this.messageHash) {
            await this.fetchUri();
        } else if (this.uri) {
            this.$nextTick(() => {
                this.renderQRCode();
            });
        }
    },
    methods: {
        async fetchUri() {
            try {
                this.isLoading = true;
                const response = await window.api.get(`/api/v1/lxmf-messages/${this.messageHash}/uri`);
                this.uri = response.data.uri;
                if (this.uri) {
                    this.$nextTick(() => {
                        this.renderQRCode();
                    });
                }
            } catch (e) {
                console.error("Failed to fetch message URI:", e);
            } finally {
                this.isLoading = false;
            }
        },
        async renderQRCode() {
            if (!this.uri || !this.$refs.qrcode) return;

            try {
                await QRCode.toCanvas(this.$refs.qrcode, this.uri, {
                    width: 256,
                    margin: 2,
                    color: {
                        dark: "#000000",
                        light: "#ffffff",
                    },
                    errorCorrectionLevel: "L",
                });

                const el = this.$refs.qrcode;
                if (el) {
                    el.style.maxWidth = "100%";
                    el.style.height = "auto";
                    el.classList.add("rounded-lg");
                }
            } catch (err) {
                console.error("Failed to render QR code:", err);
                ToastUtils.error(this.$t("messages.failed_render_qr"));
            }
        },
        close() {
            this.$emit("close");
        },
        async copyUri() {
            try {
                await navigator.clipboard.writeText(this.uri);
                ToastUtils.success(this.$t("messages.uri_copied"));
            } catch {
                ToastUtils.error(this.$t("messages.failed_copy_uri"));
            }
        },
        downloadQRCode() {
            const canvas = this.$refs.qrcode;
            if (!canvas) return;

            const dataUrl = canvas.toDataURL("image/png");
            if (dataUrl) {
                const link = document.createElement("a");
                link.download = `lxmf-paper-message-${this.messageHash ? this.messageHash.substring(0, 8) : Date.now()}.png`;
                link.href = dataUrl;
                link.click();
            }
        },
        async sendPaperMessage() {
            if (!this.recipientHash || !this.uri) return;

            try {
                this.isSending = true;

                // build lxmf message
                const lxmf_message = {
                    destination_hash: this.recipientHash,
                    content: `Please scan the attached Paper Message or manually ingest this URI: ${this.uri}`,
                    fields: {},
                };

                // get data url from canvas if available
                const canvas = this.$refs.qrcode;
                if (canvas) {
                    const dataUrl = canvas.toDataURL("image/png");
                    const imageBytes = dataUrl.split(",")[1];
                    lxmf_message.fields.image = {
                        image_type: "png",
                        image_bytes: imageBytes,
                        name: "paper_message_qr.png",
                    };
                }

                // send message
                const response = await window.api.post(`/api/v1/lxmf-messages/send`, {
                    delivery_method: "opportunistic",
                    lxmf_message: lxmf_message,
                });

                if (response.data.lxmf_message) {
                    ToastUtils.success(this.$t("messages.paper_message_sent"));
                    this.close();
                } else {
                    ToastUtils.error(response.data.message || "Failed to send paper message");
                }
            } catch (err) {
                console.error("Failed to send paper message:", err);
                ToastUtils.error(this.$t("messages.failed_send_paper"));
            } finally {
                this.isSending = false;
            }
        },
        printQRCode() {
            const canvas = this.$refs.qrcode;
            if (!canvas) return;

            const dataUrl = canvas.toDataURL("image/png");
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
                        <div class="hash">Message Hash: ${Utils.escapeHtml(this.messageHash || "")}</div>
                        <p>Scan this code with an LXMF-compatible app to read the message.</p>
                        <script>window.onload = () => { window.print(); window.close(); }</scr' + 'ipt>
                    </body>
                </html>
            `);
            printWindow.document.close();
        },
    },
};
</script>

<style scoped>
.audio-controls-light::-webkit-media-controls-panel {
    background-color: rgba(255, 255, 255, 0.2);
}
.audio-controls-dark::-webkit-media-controls-panel {
    background-color: rgba(0, 0, 0, 0.2);
}
</style>
