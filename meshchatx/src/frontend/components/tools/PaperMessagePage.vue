<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-slate-50 dark:bg-zinc-950">
        <div class="flex-1 overflow-y-auto w-full pb-[max(1rem,env(safe-area-inset-bottom))]">
            <div class="p-3 sm:p-4 md:p-6 max-w-5xl mx-auto w-full space-y-4 min-w-0">
                <!-- header -->
                <div class="border-b border-gray-200 dark:border-zinc-800 pb-4">
                    <div class="flex items-start gap-3 min-w-0">
                        <div
                            class="p-2 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-lg shrink-0"
                        >
                            <MaterialDesignIcon icon-name="qrcode" class="size-6" />
                        </div>
                        <div class="min-w-0">
                            <h2 class="text-lg sm:text-xl font-bold text-gray-900 dark:text-white tracking-tight">
                                Paper Message Generator
                            </h2>
                            <p class="text-xs sm:text-sm text-gray-600 dark:text-gray-400 mt-1">
                                Generate signed LXMF messages for physical delivery or offline transfer.
                            </p>
                        </div>
                    </div>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <!-- composer -->
                    <div class="space-y-4 min-w-0">
                        <section
                            class="rounded-lg border border-gray-200 dark:border-zinc-800 overflow-hidden bg-white dark:bg-zinc-950"
                        >
                            <div
                                class="px-4 py-3 border-b border-gray-200 dark:border-zinc-800 bg-gray-50/80 dark:bg-zinc-900/50"
                            >
                                <h2
                                    class="flex items-center gap-2 text-base font-semibold text-gray-900 dark:text-white"
                                >
                                    <MaterialDesignIcon
                                        icon-name="pencil-outline"
                                        class="size-5 text-gray-400 shrink-0"
                                    />
                                    Compose Message
                                </h2>
                            </div>
                            <div class="px-4 py-4 space-y-3 text-gray-900 dark:text-gray-100">
                                <div>
                                    <label
                                        class="block text-[10px] font-bold text-gray-400 dark:text-zinc-500 uppercase tracking-widest mb-1.5"
                                    >
                                        Recipient Address
                                    </label>
                                    <input
                                        v-model="destinationHash"
                                        type="text"
                                        placeholder="Destination hash (e.g. a39610...)"
                                        class="input-field font-mono text-sm"
                                        maxlength="32"
                                    />
                                </div>
                                <div>
                                    <label
                                        class="block text-[10px] font-bold text-gray-400 dark:text-zinc-500 uppercase tracking-widest mb-1.5"
                                    >
                                        Subject (Optional)
                                    </label>
                                    <input
                                        v-model="title"
                                        type="text"
                                        placeholder="Message title..."
                                        class="input-field text-sm"
                                    />
                                </div>
                                <div>
                                    <label
                                        class="block text-[10px] font-bold text-gray-400 dark:text-zinc-500 uppercase tracking-widest mb-1.5"
                                    >
                                        Message Content
                                    </label>
                                    <textarea
                                        v-model="content"
                                        rows="4"
                                        placeholder="Type your message here..."
                                        class="input-field resize-none text-sm"
                                    ></textarea>
                                </div>
                                <button
                                    type="button"
                                    class="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold shadow-lg shadow-blue-500/20 transition-all active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none text-sm"
                                    :disabled="!canGenerate || isGenerating"
                                    @click="generatePaperMessage"
                                >
                                    <template v-if="isGenerating">
                                        <div
                                            class="size-4 border-2 border-white/20 border-t-white rounded-full animate-spin"
                                        ></div>
                                        Generating...
                                    </template>
                                    <template v-else>
                                        <MaterialDesignIcon icon-name="qrcode-plus" class="size-5" />
                                        Generate Paper Message
                                    </template>
                                </button>
                            </div>
                        </section>

                        <!-- read / ingest section -->
                        <section
                            class="rounded-lg border border-gray-200 dark:border-zinc-800 overflow-hidden bg-white dark:bg-zinc-950"
                        >
                            <div
                                class="px-4 py-3 border-b border-gray-200 dark:border-zinc-800 bg-gray-50/80 dark:bg-zinc-900/50"
                            >
                                <h2
                                    class="flex items-center gap-2 text-base font-semibold text-gray-900 dark:text-white"
                                >
                                    <MaterialDesignIcon icon-name="qrcode-scan" class="size-5 text-gray-400 shrink-0" />
                                    Ingest Paper Message
                                </h2>
                            </div>
                            <div class="px-4 py-4 space-y-3 text-gray-900 dark:text-gray-100">
                                <p class="text-xs text-gray-600 dark:text-gray-400">
                                    Paste an LXMF URI to decode and add it to your conversations.
                                </p>
                                <div class="flex flex-col sm:flex-row gap-2">
                                    <input
                                        v-model="ingestUri"
                                        type="text"
                                        placeholder="lxmf://..."
                                        class="input-field flex-1 min-w-0 font-mono text-sm"
                                        @keydown.enter="ingestPaperMessage"
                                    />
                                    <button
                                        type="button"
                                        class="inline-flex items-center justify-center gap-2 px-3 py-2.5 sm:py-2 bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 rounded-lg hover:bg-gray-200 dark:hover:bg-zinc-700 transition-colors shrink-0"
                                        @click="pasteFromClipboard"
                                    >
                                        <MaterialDesignIcon icon-name="content-paste" class="size-5" />
                                        <span class="sm:hidden text-sm font-medium">Paste</span>
                                    </button>
                                </div>
                                <button
                                    type="button"
                                    class="w-full py-2.5 px-4 bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-200 rounded-xl font-bold hover:bg-gray-200 dark:hover:bg-zinc-700 transition-all active:scale-[0.98] text-sm"
                                    :disabled="!ingestUri"
                                    @click="ingestPaperMessage"
                                >
                                    Read LXM
                                </button>
                            </div>
                        </section>
                    </div>

                    <!-- preview / result -->
                    <div class="space-y-4 min-w-0">
                        <section
                            v-if="generatedUri"
                            class="rounded-lg border border-gray-200 dark:border-zinc-800 overflow-hidden bg-white dark:bg-zinc-950"
                        >
                            <div
                                class="px-4 py-3 border-b border-gray-200 dark:border-zinc-800 bg-blue-50/80 dark:bg-blue-900/20"
                            >
                                <h2 class="text-base font-semibold text-blue-600 dark:text-blue-400">
                                    Generated QR Code
                                </h2>
                            </div>
                            <div class="px-4 py-4 sm:p-6 flex flex-col items-center text-gray-900 dark:text-gray-100">
                                <div class="p-3 bg-white rounded-2xl shadow-inner border border-gray-100 mb-6">
                                    <div class="size-40 sm:size-48 flex items-center justify-center overflow-hidden">
                                        <canvas ref="qrcode"></canvas>
                                    </div>
                                </div>

                                <div class="w-full space-y-3">
                                    <div
                                        class="bg-gray-50 dark:bg-zinc-800/50 rounded-2xl p-3 border border-gray-100 dark:border-zinc-700/50"
                                    >
                                        <label
                                            class="block text-[9px] font-bold text-gray-400 dark:text-zinc-500 uppercase tracking-widest mb-1.5"
                                        >
                                            LXMF URI
                                        </label>
                                        <div class="flex gap-2">
                                            <div
                                                class="flex-1 font-mono text-[10px] break-all text-gray-600 dark:text-zinc-300 bg-white dark:bg-zinc-900 p-2 rounded-lg border border-gray-200 dark:border-zinc-700 max-h-20 overflow-y-auto"
                                            >
                                                {{ generatedUri }}
                                            </div>
                                            <button
                                                type="button"
                                                class="size-9 flex items-center justify-center bg-white dark:bg-zinc-900 text-gray-500 dark:text-zinc-400 rounded-lg border border-gray-200 dark:border-zinc-700 hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200 transition-all shadow-sm"
                                                title="Copy URI"
                                                @click="copyUri"
                                            >
                                                <MaterialDesignIcon icon-name="content-copy" class="size-4" />
                                            </button>
                                        </div>
                                    </div>

                                    <div class="flex flex-col sm:flex-row gap-2 pt-1">
                                        <button
                                            type="button"
                                            class="flex-1 flex items-center justify-center gap-2 py-3 sm:py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold transition-all active:scale-[0.98] text-sm min-h-[44px]"
                                            @click="printQRCode"
                                        >
                                            <MaterialDesignIcon icon-name="printer" class="size-4" />
                                            Print
                                        </button>
                                        <button
                                            type="button"
                                            class="flex-1 flex items-center justify-center gap-2 py-3 sm:py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold transition-all active:scale-[0.98] text-sm min-h-[44px]"
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
                            </div>
                        </section>

                        <div
                            v-else
                            class="rounded-lg border border-dashed border-gray-300 dark:border-zinc-700 bg-gray-50/50 dark:bg-zinc-900/30 flex flex-col items-center justify-center p-6 sm:p-8 text-center min-h-[240px] sm:min-h-[280px] sm:h-[320px]"
                        >
                            <div class="p-3 bg-gray-100 dark:bg-zinc-800 text-gray-400 rounded-full mb-3">
                                <MaterialDesignIcon icon-name="qrcode" class="size-10" />
                            </div>
                            <h3 class="text-base font-bold text-gray-900 dark:text-white mb-1">No QR Code Generated</h3>
                            <p class="text-xs text-gray-500 dark:text-gray-400 max-w-[200px]">
                                Fill out the message details and click generate to create a signed paper message.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import QRCode from "qrcode";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import WebSocketConnection from "../../js/WebSocketConnection";
import ToastUtils from "../../js/ToastUtils";

export default {
    name: "PaperMessagePage",
    components: { MaterialDesignIcon },
    data() {
        return {
            destinationHash: "",
            title: "",
            content: "",
            isGenerating: false,
            generatedUri: null,
            ingestUri: "",
            isSending: false,
        };
    },
    computed: {
        canGenerate() {
            return this.destinationHash.length === 32 && this.content.length > 0;
        },
    },
    mounted() {
        WebSocketConnection.on("message", this.onWebsocketMessage);
    },
    beforeUnmount() {
        WebSocketConnection.off("message", this.onWebsocketMessage);
    },
    methods: {
        async onWebsocketMessage(message) {
            const json = JSON.parse(message.data);
            if (json.type === "lxm.generate_paper_uri.result") {
                this.isGenerating = false;
                if (json.status === "success") {
                    this.generatedUri = json.uri;
                    this.$nextTick(() => {
                        this.renderQRCode();
                    });
                } else {
                    ToastUtils.error(json.message);
                }
            } else if (json.type === "lxm.ingest_uri.result") {
                if (json.status === "success") {
                    this.ingestUri = "";
                }
            }
        },
        async generatePaperMessage() {
            if (!this.canGenerate) return;

            this.isGenerating = true;
            this.generatedUri = null;

            WebSocketConnection.send(
                JSON.stringify({
                    type: "lxm.generate_paper_uri",
                    destination_hash: this.destinationHash,
                    content: this.content,
                    title: this.title,
                })
            );
        },
        async renderQRCode() {
            if (!this.generatedUri || !this.$refs.qrcode) return;

            try {
                await QRCode.toCanvas(this.$refs.qrcode, this.generatedUri, {
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
        async ingestPaperMessage() {
            if (!this.ingestUri) return;

            WebSocketConnection.send(
                JSON.stringify({
                    type: "lxm.ingest_uri",
                    uri: this.ingestUri,
                })
            );
        },
        async pasteFromClipboard() {
            try {
                this.ingestUri = await navigator.clipboard.readText();
            } catch {
                ToastUtils.error(this.$t("messages.failed_read_clipboard"));
            }
        },
        async copyUri() {
            try {
                await navigator.clipboard.writeText(this.generatedUri);
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
                link.download = `lxmf-paper-message-${Date.now()}.png`;
                link.href = dataUrl;
                link.click();
            }
        },
        async sendPaperMessage() {
            if (!this.destinationHash || !this.generatedUri) return;

            try {
                this.isSending = true;

                // build lxmf message
                const lxmf_message = {
                    destination_hash: this.destinationHash,
                    content: `Please scan the attached Paper Message or manually ingest this URI: ${this.generatedUri}`,
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
                    this.generatedUri = null;
                    this.destinationHash = "";
                    this.content = "";
                    this.title = "";
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
                        <img src="${dataUrl}" />
                        <div class="hash">Recipient: ${this.destinationHash}</div>
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
.input-field {
    @apply bg-gray-50/90 dark:bg-zinc-800/80 border border-gray-200 dark:border-zinc-700 text-sm rounded-2xl focus:ring-2 focus:ring-blue-400 focus:border-blue-400 dark:focus:ring-blue-50 dark:focus:border-blue-500 block w-full p-2.5 text-gray-900 dark:text-gray-100 transition;
}
</style>
