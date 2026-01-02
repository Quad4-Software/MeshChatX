<template>
    <div
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-gradient-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div class="overflow-y-auto p-4 md:p-6 max-w-5xl mx-auto w-full">
            <!-- header -->
            <div class="glass-card mb-6">
                <div class="flex items-center gap-4">
                    <div class="p-3 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-2xl">
                        <MaterialDesignIcon icon-name="qrcode" class="size-8" />
                    </div>
                    <div>
                        <h2 class="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">
                            Paper Message Generator
                        </h2>
                        <p class="text-sm text-gray-600 dark:text-gray-400">
                            Generate signed LXMF messages for physical delivery or offline transfer.
                        </p>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <!-- composer -->
                <div class="space-y-6">
                    <section class="glass-card">
                        <div class="glass-card__header">
                            <h2 class="flex items-center gap-2">
                                <MaterialDesignIcon icon-name="pencil-outline" class="size-5 text-gray-400" />
                                Compose Message
                            </h2>
                        </div>
                        <div class="glass-card__body space-y-4">
                            <div>
                                <label
                                    class="block text-xs font-bold text-gray-400 dark:text-zinc-500 uppercase tracking-widest mb-2"
                                >
                                    Recipient Address
                                </label>
                                <input
                                    v-model="destinationHash"
                                    type="text"
                                    placeholder="Destination hash (e.g. a39610...)"
                                    class="input-field font-mono"
                                />
                            </div>
                            <div>
                                <label
                                    class="block text-xs font-bold text-gray-400 dark:text-zinc-500 uppercase tracking-widest mb-2"
                                >
                                    Subject (Optional)
                                </label>
                                <input v-model="title" type="text" placeholder="Message title..." class="input-field" />
                            </div>
                            <div>
                                <label
                                    class="block text-xs font-bold text-gray-400 dark:text-zinc-500 uppercase tracking-widest mb-2"
                                >
                                    Message Content
                                </label>
                                <textarea
                                    v-model="content"
                                    rows="6"
                                    placeholder="Type your message here..."
                                    class="input-field resize-none"
                                ></textarea>
                            </div>
                            <button
                                type="button"
                                class="w-full flex items-center justify-center gap-2 py-3 px-6 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl font-bold shadow-lg shadow-blue-500/20 transition-all active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none"
                                :disabled="!canGenerate || isGenerating"
                                @click="generatePaperMessage"
                            >
                                <template v-if="isGenerating">
                                    <div
                                        class="size-5 border-2 border-white/20 border-t-white rounded-full animate-spin"
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
                    <section class="glass-card">
                        <div class="glass-card__header">
                            <h2 class="flex items-center gap-2">
                                <MaterialDesignIcon icon-name="qrcode-scan" class="size-5 text-gray-400" />
                                Ingest Paper Message
                            </h2>
                        </div>
                        <div class="glass-card__body space-y-4">
                            <p class="text-sm text-gray-600 dark:text-gray-400">
                                Paste an LXMF URI to decode and add it to your conversations.
                            </p>
                            <div class="flex gap-2">
                                <input
                                    v-model="ingestUri"
                                    type="text"
                                    placeholder="lxmf://..."
                                    class="input-field flex-1 font-mono"
                                    @keydown.enter="ingestPaperMessage"
                                />
                                <button
                                    type="button"
                                    class="px-4 py-2 bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 rounded-xl hover:bg-gray-200 dark:hover:bg-zinc-700 transition-colors"
                                    @click="pasteFromClipboard"
                                >
                                    <MaterialDesignIcon icon-name="content-paste" class="size-5" />
                                </button>
                            </div>
                            <button
                                type="button"
                                class="w-full py-3 px-6 bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-200 rounded-2xl font-bold hover:bg-gray-200 dark:hover:bg-zinc-700 transition-all active:scale-[0.98]"
                                :disabled="!ingestUri"
                                @click="ingestPaperMessage"
                            >
                                Read LXM
                            </button>
                        </div>
                    </section>
                </div>

                <!-- preview / result -->
                <div class="space-y-6">
                    <section v-if="generatedUri" class="glass-card overflow-hidden">
                        <div class="glass-card__header bg-blue-50/50 dark:bg-blue-900/10">
                            <h2 class="text-blue-600 dark:text-blue-400">Generated QR Code</h2>
                        </div>
                        <div class="glass-card__body flex flex-col items-center p-8">
                            <div class="p-6 bg-white rounded-3xl shadow-inner border border-gray-100 mb-8">
                                <div
                                    ref="qrcode"
                                    class="size-64 sm:size-80 flex items-center justify-center overflow-hidden"
                                >
                                    <!-- qr code will be rendered here -->
                                </div>
                            </div>

                            <div class="w-full space-y-4">
                                <div
                                    class="bg-gray-50 dark:bg-zinc-800/50 rounded-2xl p-4 border border-gray-100 dark:border-zinc-700/50"
                                >
                                    <label
                                        class="block text-[10px] font-bold text-gray-400 dark:text-zinc-500 uppercase tracking-widest mb-2"
                                    >
                                        LXMF URI
                                    </label>
                                    <div class="flex gap-3">
                                        <div
                                            class="flex-1 font-mono text-xs break-all text-gray-600 dark:text-zinc-300 bg-white dark:bg-zinc-900 p-3 rounded-xl border border-gray-200 dark:border-zinc-700 max-h-24 overflow-y-auto"
                                        >
                                            {{ generatedUri }}
                                        </div>
                                        <button
                                            type="button"
                                            class="size-10 flex items-center justify-center bg-white dark:bg-zinc-900 text-gray-500 dark:text-zinc-400 rounded-xl border border-gray-200 dark:border-zinc-700 hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200 transition-all shadow-sm"
                                            title="Copy URI"
                                            @click="copyUri"
                                        >
                                            <MaterialDesignIcon icon-name="content-copy" class="size-5" />
                                        </button>
                                    </div>
                                </div>

                                <div class="flex gap-3 pt-2">
                                    <button
                                        type="button"
                                        class="flex-1 flex items-center justify-center gap-2 py-3.5 px-6 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl font-bold shadow-lg shadow-blue-500/20 transition-all active:scale-[0.98]"
                                        @click="printQRCode"
                                    >
                                        <MaterialDesignIcon icon-name="printer" class="size-5" />
                                        Print
                                    </button>
                                    <button
                                        type="button"
                                        class="flex-1 flex items-center justify-center gap-2 py-3.5 px-6 bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-700 text-gray-700 dark:text-zinc-200 rounded-2xl font-bold transition-all active:scale-[0.98]"
                                        @click="downloadQRCode"
                                    >
                                        <MaterialDesignIcon icon-name="download" class="size-5" />
                                        Save
                                    </button>
                                </div>
                            </div>
                        </div>
                    </section>

                    <div
                        v-else
                        class="glass-card flex flex-col items-center justify-center p-12 text-center h-[400px] border-dashed"
                    >
                        <div class="p-4 bg-gray-100 dark:bg-zinc-800 text-gray-400 rounded-full mb-4">
                            <MaterialDesignIcon icon-name="qrcode" class="size-12" />
                        </div>
                        <h3 class="text-lg font-bold text-gray-900 dark:text-white mb-2">No QR Code Generated</h3>
                        <p class="text-sm text-gray-500 dark:text-gray-400 max-w-xs">
                            Fill out the message details and click generate to create a signed paper message.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
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
            qrCodeLibrary: null,
        };
    },
    computed: {
        canGenerate() {
            return this.destinationHash.length === 32 && this.content.length > 0;
        },
    },
    mounted() {
        WebSocketConnection.on("message", this.onWebsocketMessage);
        this.loadQRCodeLibrary();
    },
    beforeUnmount() {
        WebSocketConnection.off("message", this.onWebsocketMessage);
    },
    methods: {
        async loadQRCodeLibrary() {
            if (window.QRCode) {
                this.qrCodeLibrary = window.QRCode;
                return;
            }

            return new Promise((resolve) => {
                const script = document.createElement("script");
                script.src = "https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js";
                script.onload = () => {
                    this.qrCodeLibrary = window.QRCode;
                    resolve();
                };
                document.head.appendChild(script);
            });
        },
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
                    ToastUtils.success(json.message);
                    this.ingestUri = "";
                } else if (json.status === "error") {
                    ToastUtils.error(json.message);
                } else {
                    ToastUtils.warning(json.message);
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
        renderQRCode() {
            if (!this.qrCodeLibrary || !this.$refs.qrcode) return;

            this.$refs.qrcode.innerHTML = "";

            new this.qrCodeLibrary(this.$refs.qrcode, {
                text: this.generatedUri,
                width: 320,
                height: 320,
                colorDark: "#000000",
                colorLight: "#ffffff",
                correctLevel: this.qrCodeLibrary.CorrectLevel.L,
            });

            const el = this.$refs.qrcode.querySelector("img") || this.$refs.qrcode.querySelector("canvas");
            if (el) {
                el.style.maxWidth = "100%";
                el.style.height = "auto";
                el.classList.add("rounded-lg");
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
                ToastUtils.error("Failed to read from clipboard");
            }
        },
        async copyUri() {
            try {
                await navigator.clipboard.writeText(this.generatedUri);
                ToastUtils.success("URI copied to clipboard");
            } catch {
                ToastUtils.error("Failed to copy URI");
            }
        },
        downloadQRCode() {
            const canvas = this.$refs.qrcode.querySelector("canvas");
            const img = this.$refs.qrcode.querySelector("img");

            let dataUrl = "";
            if (img && img.src) {
                dataUrl = img.src;
            } else if (canvas) {
                dataUrl = canvas.toDataURL("image/png");
            }

            if (dataUrl) {
                const link = document.createElement("a");
                link.download = `lxmf-paper-message-${Date.now()}.png`;
                link.href = dataUrl;
                link.click();
            }
        },
        printQRCode() {
            const dataUrl =
                this.$refs.qrcode.querySelector("img")?.src ||
                this.$refs.qrcode.querySelector("canvas")?.toDataURL("image/png");
            if (!dataUrl) return;

            const printWindow = window.open("", "_blank");
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
.glass-card {
    @apply bg-white/90 dark:bg-zinc-900/80 backdrop-blur border border-gray-200 dark:border-zinc-800 rounded-3xl shadow-lg flex flex-col;
}
.glass-card__header {
    @apply flex items-center justify-between gap-3 px-6 py-4 border-b border-gray-100/70 dark:border-zinc-800/80;
}
.glass-card__header h2 {
    @apply text-lg font-semibold text-gray-900 dark:text-white;
}
.glass-card__body {
    @apply px-6 py-6 text-gray-900 dark:text-gray-100;
}
.input-field {
    @apply bg-gray-50/90 dark:bg-zinc-800/80 border border-gray-200 dark:border-zinc-700 text-sm rounded-2xl focus:ring-2 focus:ring-blue-400 focus:border-blue-400 dark:focus:ring-blue-50 dark:focus:border-blue-500 block w-full p-2.5 text-gray-900 dark:text-gray-100 transition;
}
</style>
