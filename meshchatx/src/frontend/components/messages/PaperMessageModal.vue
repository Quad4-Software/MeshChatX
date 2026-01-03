<template>
    <div
        class="fixed inset-0 z-[150] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm transition-opacity"
        @click.self="close"
    >
        <div
            class="w-full max-w-lg bg-white dark:bg-zinc-900 rounded-3xl shadow-2xl overflow-hidden transform transition-all scale-100"
        >
            <!-- header -->
            <div
                class="px-6 py-5 border-b border-gray-100 dark:border-zinc-800 flex items-center justify-between bg-gray-50/50 dark:bg-zinc-900/50"
            >
                <div class="flex items-center gap-3">
                    <div class="p-2 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-xl">
                        <MaterialDesignIcon icon-name="qrcode" class="size-6" />
                    </div>
                    <h3 class="text-xl font-bold text-gray-900 dark:text-white tracking-tight">Paper Message</h3>
                </div>
                <button
                    type="button"
                    class="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-zinc-200 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-full transition-all"
                    @click="close"
                >
                    <MaterialDesignIcon icon-name="close" class="size-6" />
                </button>
            </div>

            <div class="p-4 sm:p-6 flex flex-col items-center">
                <div v-if="isLoading" class="flex flex-col items-center py-8">
                    <div class="size-12 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin"></div>
                    <p class="mt-4 text-xs text-gray-500 dark:text-gray-400 font-medium">Generating Paper Message...</p>
                </div>
                <template v-else-if="uri">
                    <!-- QR code container -->
                    <div class="p-4 bg-white rounded-2xl shadow-inner border border-gray-100 mb-6 relative group">
                        <div class="size-48 sm:size-64 flex items-center justify-center overflow-hidden">
                            <canvas ref="qrcode"></canvas>
                        </div>
                        <div
                            class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-white/10 backdrop-blur-[2px] rounded-2xl pointer-events-none"
                        >
                            <div
                                class="p-2 bg-white/90 dark:bg-zinc-900/90 rounded-xl shadow-xl border border-gray-200 dark:border-zinc-700"
                            >
                                <MaterialDesignIcon icon-name="magnify-plus-outline" class="size-6 text-blue-500" />
                            </div>
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
                                    {{ uri }}
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

                        <div class="flex gap-2 pt-1">
                            <button
                                type="button"
                                class="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold shadow-lg shadow-blue-500/20 transition-all active:scale-[0.98] text-sm"
                                @click="printQRCode"
                            >
                                <MaterialDesignIcon icon-name="printer" class="size-4" />
                                Print
                            </button>
                            <button
                                type="button"
                                class="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-700 text-gray-700 dark:text-zinc-200 rounded-xl font-bold transition-all active:scale-[0.98] text-sm"
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
                    <h4 class="text-lg font-bold text-gray-900 dark:text-white mb-2">Message Not Available</h4>
                    <p class="text-sm text-gray-500 dark:text-gray-400 max-w-xs">
                        The original message bytes are no longer available in the router queue to generate a signed
                        paper message.
                    </p>
                    <button
                        type="button"
                        class="mt-6 py-2.5 px-6 bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-200 rounded-xl font-bold hover:bg-gray-200 dark:hover:bg-zinc-700 transition-all"
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
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";

export default {
    name: "PaperMessageModal",
    components: { MaterialDesignIcon },
    props: {
        messageHash: {
            type: String,
            required: true,
        },
    },
    emits: ["close"],
    data() {
        return {
            uri: null,
            isLoading: true,
        };
    },
    async mounted() {
        await this.fetchUri();
    },
    methods: {
        async fetchUri() {
            try {
                this.isLoading = true;
                const response = await window.axios.get(`/api/v1/lxmf-messages/${this.messageHash}/uri`);
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
                    width: 320,
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
                ToastUtils.error("Failed to render QR code");
            }
        },
        close() {
            this.$emit("close");
        },
        async copyUri() {
            try {
                await navigator.clipboard.writeText(this.uri);
                ToastUtils.success("URI copied to clipboard");
            } catch {
                ToastUtils.error("Failed to copy URI");
            }
        },
        downloadQRCode() {
            const canvas = this.$refs.qrcode;
            if (!canvas) return;

            const dataUrl = canvas.toDataURL("image/png");
            if (dataUrl) {
                const link = document.createElement("a");
                link.download = `lxmf-paper-message-${this.messageHash.substring(0, 8)}.png`;
                link.href = dataUrl;
                link.click();
            }
        },
        printQRCode() {
            const canvas = this.$refs.qrcode;
            if (!canvas) return;

            const dataUrl = canvas.toDataURL("image/png");
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
                        <div class="hash">Message Hash: ${this.messageHash}</div>
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
