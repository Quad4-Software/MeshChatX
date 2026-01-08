<template>
    <div
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-gradient-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div class="flex-1 overflow-y-auto w-full px-4 md:px-8 py-6">
            <div class="space-y-4 w-full max-w-4xl mx-auto">
                <div class="glass-card space-y-5">
                    <div class="space-y-2">
                        <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            {{ $t("rncp.file_transfer") }}
                        </div>
                        <div class="text-2xl font-semibold text-gray-900 dark:text-white">
                            {{ $t("rncp.title") }}
                        </div>
                        <div class="text-sm text-gray-600 dark:text-gray-300">
                            {{ $t("rncp.description") }}
                        </div>

                        <div
                            class="mt-4 p-4 rounded-lg bg-blue-50/50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-900/20"
                        >
                            <div
                                class="text-xs font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400 mb-2"
                            >
                                {{ $t("rncp.usage_steps") }}
                            </div>
                            <div class="space-y-1.5">
                                <!-- eslint-disable vue/no-v-html -->
                                <p
                                    class="text-xs text-blue-800/80 dark:text-blue-300/80 leading-relaxed"
                                    @click="handleMessageClick"
                                    v-html="renderMarkdown($t('rncp.step_1'))"
                                ></p>
                                <p
                                    class="text-xs text-blue-800/80 dark:text-blue-300/80 leading-relaxed"
                                    @click="handleMessageClick"
                                    v-html="renderMarkdown($t('rncp.step_2'))"
                                ></p>
                                <p
                                    class="text-xs text-blue-800/80 dark:text-blue-300/80 leading-relaxed"
                                    @click="handleMessageClick"
                                    v-html="renderMarkdown($t('rncp.step_3'))"
                                ></p>
                                <!-- eslint-enable vue/no-v-html -->
                            </div>
                        </div>
                    </div>

                    <div class="flex gap-2 border-b border-gray-200 dark:border-zinc-700">
                        <button
                            :class="[
                                activeTab === 'send'
                                    ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                                    : 'text-gray-600 dark:text-gray-400',
                                'px-4 py-2 font-semibold transition',
                            ]"
                            @click="activeTab = 'send'"
                        >
                            {{ $t("rncp.send_file") }}
                        </button>
                        <button
                            :class="[
                                activeTab === 'fetch'
                                    ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                                    : 'text-gray-600 dark:text-gray-400',
                                'px-4 py-2 font-semibold transition',
                            ]"
                            @click="activeTab = 'fetch'"
                        >
                            {{ $t("rncp.fetch_file") }}
                        </button>
                        <button
                            :class="[
                                activeTab === 'listen'
                                    ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                                    : 'text-gray-600 dark:text-gray-400',
                                'px-4 py-2 font-semibold transition',
                            ]"
                            @click="activeTab = 'listen'"
                        >
                            {{ $t("rncp.listen") }}
                        </button>
                    </div>

                    <div v-if="activeTab === 'send'" class="space-y-4">
                        <div class="grid md:grid-cols-2 gap-4">
                            <div>
                                <label class="glass-label">{{ $t("rncp.destination_hash") }}</label>
                                <input
                                    v-model="sendDestinationHash"
                                    type="text"
                                    placeholder="e.g. 7b746057a7294469799cd8d7d429676a"
                                    class="input-field font-mono"
                                />
                            </div>
                            <div>
                                <label class="glass-label">{{ $t("rncp.file_path") }}</label>
                                <input
                                    v-model="sendFilePath"
                                    type="text"
                                    placeholder="/path/to/file"
                                    class="input-field"
                                />
                            </div>
                        </div>
                        <div class="grid md:grid-cols-2 gap-4">
                            <div>
                                <label class="glass-label">{{ $t("rncp.timeout_seconds") }}</label>
                                <input v-model="sendTimeout" type="number" min="1" class="input-field" />
                            </div>
                            <div class="flex items-end">
                                <label class="flex items-center gap-2 cursor-pointer">
                                    <input v-model="sendNoCompress" type="checkbox" class="rounded" />
                                    <span class="text-sm text-gray-700 dark:text-gray-300">{{
                                        $t("rncp.disable_compression")
                                    }}</span>
                                </label>
                            </div>
                        </div>
                        <div class="flex gap-2">
                            <button
                                v-if="!sendInProgress"
                                type="button"
                                class="primary-chip px-4 py-2 text-sm"
                                @click="sendFile"
                            >
                                <MaterialDesignIcon icon-name="upload" class="w-4 h-4" />
                                {{ $t("rncp.send_file") }}
                            </button>
                            <button
                                v-else
                                type="button"
                                class="secondary-chip px-4 py-2 text-sm text-red-600 dark:text-red-300 border-red-200 dark:border-red-500/50"
                                @click="cancelSend"
                            >
                                <MaterialDesignIcon icon-name="close" class="w-4 h-4" />
                                {{ $t("rncp.cancel") }}
                            </button>
                        </div>
                        <div v-if="sendProgress > 0" class="space-y-2">
                            <div class="flex justify-between text-sm">
                                <span class="text-gray-700 dark:text-gray-300">{{ $t("rncp.progress") }}</span>
                                <span class="text-gray-700 dark:text-gray-300"
                                    >{{ Math.round(sendProgress * 100) }}%</span
                                >
                            </div>
                            <div class="w-full bg-gray-200 dark:bg-zinc-700 rounded-full h-2">
                                <div
                                    class="bg-blue-600 h-2 rounded-full transition-all"
                                    :style="{ width: sendProgress * 100 + '%' }"
                                ></div>
                            </div>
                        </div>
                        <div
                            v-if="sendResult"
                            class="p-3 rounded-lg"
                            :class="
                                sendResult.success
                                    ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                                    : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'
                            "
                        >
                            {{ sendResult.message }}
                        </div>
                    </div>

                    <div v-if="activeTab === 'fetch'" class="space-y-4">
                        <div class="grid md:grid-cols-2 gap-4">
                            <div>
                                <label class="glass-label">{{ $t("rncp.destination_hash") }}</label>
                                <input
                                    v-model="fetchDestinationHash"
                                    type="text"
                                    placeholder="e.g. 7b746057a7294469799cd8d7d429676a"
                                    class="input-field font-mono"
                                />
                            </div>
                            <div>
                                <label class="glass-label">{{ $t("rncp.remote_file_path") }}</label>
                                <input
                                    v-model="fetchFilePath"
                                    type="text"
                                    placeholder="/path/to/remote/file"
                                    class="input-field"
                                />
                            </div>
                        </div>
                        <div class="grid md:grid-cols-2 gap-4">
                            <div>
                                <label class="glass-label">{{ $t("rncp.save_path_optional") }}</label>
                                <input
                                    v-model="fetchSavePath"
                                    type="text"
                                    :placeholder="$t('rncp.save_path_placeholder')"
                                    class="input-field"
                                />
                            </div>
                            <div>
                                <label class="glass-label">{{ $t("rncp.timeout_seconds") }}</label>
                                <input v-model="fetchTimeout" type="number" min="1" class="input-field" />
                            </div>
                        </div>
                        <div class="flex items-center gap-2">
                            <label class="flex items-center gap-2 cursor-pointer">
                                <input v-model="fetchAllowOverwrite" type="checkbox" class="rounded" />
                                <span class="text-sm text-gray-700 dark:text-gray-300">{{
                                    $t("rncp.allow_overwrite")
                                }}</span>
                            </label>
                        </div>
                        <div class="flex gap-2">
                            <button
                                v-if="!fetchInProgress"
                                type="button"
                                class="primary-chip px-4 py-2 text-sm"
                                @click="fetchFile"
                            >
                                <MaterialDesignIcon icon-name="download" class="w-4 h-4" />
                                {{ $t("rncp.fetch_file") }}
                            </button>
                            <button
                                v-else
                                type="button"
                                class="secondary-chip px-4 py-2 text-sm text-red-600 dark:text-red-300 border-red-200 dark:border-red-500/50"
                                @click="cancelFetch"
                            >
                                <MaterialDesignIcon icon-name="close" class="w-4 h-4" />
                                {{ $t("rncp.cancel") }}
                            </button>
                        </div>
                        <div v-if="fetchProgress > 0" class="space-y-2">
                            <div class="flex justify-between text-sm">
                                <span class="text-gray-700 dark:text-gray-300">{{ $t("rncp.progress") }}</span>
                                <span class="text-gray-700 dark:text-gray-300"
                                    >{{ Math.round(fetchProgress * 100) }}%</span
                                >
                            </div>
                            <div class="w-full bg-gray-200 dark:bg-zinc-700 rounded-full h-2">
                                <div
                                    class="bg-blue-600 h-2 rounded-full transition-all"
                                    :style="{ width: fetchProgress * 100 + '%' }"
                                ></div>
                            </div>
                        </div>
                        <div
                            v-if="fetchResult"
                            class="p-3 rounded-lg"
                            :class="
                                fetchResult.success
                                    ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                                    : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'
                            "
                        >
                            {{ fetchResult.message }}
                        </div>
                    </div>

                    <div v-if="activeTab === 'listen'" class="space-y-4">
                        <div>
                            <label class="glass-label">{{ $t("rncp.allowed_hashes") }}</label>
                            <textarea
                                v-model="listenAllowedHashes"
                                rows="4"
                                placeholder="7b746057a7294469799cd8d7d429676a&#10;8c857168b830557080ad9e8e8e539787b"
                                class="input-field font-mono text-sm"
                            ></textarea>
                        </div>
                        <div class="grid md:grid-cols-2 gap-4">
                            <div>
                                <label class="glass-label">{{ $t("rncp.fetch_jail_path") }}</label>
                                <input
                                    v-model="listenFetchJail"
                                    type="text"
                                    placeholder="/path/to/jail"
                                    class="input-field"
                                />
                            </div>
                            <div class="flex items-end gap-4">
                                <label class="flex items-center gap-2 cursor-pointer">
                                    <input v-model="listenFetchAllowed" type="checkbox" class="rounded" />
                                    <span class="text-sm text-gray-700 dark:text-gray-300">{{
                                        $t("rncp.allow_fetch")
                                    }}</span>
                                </label>
                                <label class="flex items-center gap-2 cursor-pointer">
                                    <input v-model="listenAllowOverwrite" type="checkbox" class="rounded" />
                                    <span class="text-sm text-gray-700 dark:text-gray-300">{{
                                        $t("rncp.allow_overwrite")
                                    }}</span>
                                </label>
                            </div>
                        </div>
                        <div class="flex gap-2">
                            <button
                                v-if="!listenActive"
                                type="button"
                                class="primary-chip px-4 py-2 text-sm"
                                @click="startListen"
                            >
                                <MaterialDesignIcon icon-name="play" class="w-4 h-4" />
                                {{ $t("rncp.start_listening") }}
                            </button>
                            <button
                                v-else
                                type="button"
                                class="secondary-chip px-4 py-2 text-sm text-red-600 dark:text-red-300 border-red-200 dark:border-red-500/50"
                                @click="stopListen"
                            >
                                <MaterialDesignIcon icon-name="stop" class="w-4 h-4" />
                                {{ $t("rncp.stop_listening") }}
                            </button>
                        </div>
                        <div
                            v-if="listenDestinationHash"
                            class="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                        >
                            <div class="font-semibold mb-1">{{ $t("rncp.listening_on") }}</div>
                            <div class="font-mono text-sm">{{ listenDestinationHash }}</div>
                        </div>
                        <div
                            v-if="listenResult"
                            class="p-3 rounded-lg"
                            :class="
                                listenResult.success
                                    ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                                    : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'
                            "
                        >
                            {{ listenResult.message }}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import DialogUtils from "../../js/DialogUtils";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import WebSocketConnection from "../../js/WebSocketConnection";
import MarkdownRenderer from "../../js/MarkdownRenderer";

export default {
    name: "RNCPPage",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            activeTab: "send",
            sendDestinationHash: null,
            sendFilePath: null,
            sendTimeout: 30,
            sendNoCompress: false,
            sendInProgress: false,
            sendProgress: 0,
            sendResult: null,
            sendTransferId: null,
            fetchDestinationHash: null,
            fetchFilePath: null,
            fetchSavePath: null,
            fetchTimeout: 30,
            fetchAllowOverwrite: false,
            fetchInProgress: false,
            fetchProgress: 0,
            fetchResult: null,
            listenAllowedHashes: "",
            listenFetchJail: null,
            listenFetchAllowed: false,
            listenAllowOverwrite: false,
            listenActive: false,
            listenDestinationHash: null,
            listenResult: null,
        };
    },
    mounted() {
        WebSocketConnection.on("message", this.handleWebSocketMessage);
    },
    beforeUnmount() {
        WebSocketConnection.off("message", this.handleWebSocketMessage);
        this.cancelSend();
        this.cancelFetch();
    },
    methods: {
        handleWebSocketMessage(message) {
            try {
                const data = JSON.parse(message.data);
                if (data.type === "rncp.transfer.progress") {
                    if (data.transfer_id === this.sendTransferId) {
                        this.sendProgress = data.progress;
                    } else {
                        this.fetchProgress = data.progress;
                    }
                }
            } catch {
                // ignore parse errors
            }
        },
        async sendFile() {
            if (!this.sendDestinationHash || this.sendDestinationHash.length !== 32) {
                DialogUtils.alert(this.$t("rncp.invalid_hash"));
                return;
            }
            if (!this.sendFilePath) {
                DialogUtils.alert(this.$t("rncp.provide_file_path"));
                return;
            }

            this.sendInProgress = true;
            this.sendProgress = 0;
            this.sendResult = null;

            try {
                const response = await window.axios.post("/api/v1/rncp/send", {
                    destination_hash: this.sendDestinationHash,
                    file_path: this.sendFilePath,
                    timeout: this.sendTimeout,
                    no_compress: this.sendNoCompress,
                });

                this.sendTransferId = response.data.transfer_id;
                this.sendProgress = 1;
                this.sendResult = {
                    success: true,
                    message: this.$t("rncp.file_sent_successfully", { id: response.data.transfer_id }),
                };
            } catch (e) {
                console.error(e);
                this.sendResult = {
                    success: false,
                    message: e.response?.data?.message || this.$t("rncp.failed_to_send"),
                };
            } finally {
                this.sendInProgress = false;
            }
        },
        cancelSend() {
            this.sendInProgress = false;
            this.sendProgress = 0;
        },
        async fetchFile() {
            if (!this.fetchDestinationHash || this.fetchDestinationHash.length !== 32) {
                DialogUtils.alert(this.$t("rncp.invalid_hash"));
                return;
            }
            if (!this.fetchFilePath) {
                DialogUtils.alert(this.$t("rncp.provide_remote_file_path"));
                return;
            }

            this.fetchInProgress = true;
            this.fetchProgress = 0;
            this.fetchResult = null;

            try {
                const response = await window.axios.post("/api/v1/rncp/fetch", {
                    destination_hash: this.fetchDestinationHash,
                    file_path: this.fetchFilePath,
                    timeout: this.fetchTimeout,
                    save_path: this.fetchSavePath || null,
                    allow_overwrite: this.fetchAllowOverwrite,
                });

                this.fetchProgress = 1;
                this.fetchResult = {
                    success: true,
                    message: this.$t("rncp.file_fetched_successfully", {
                        path: response.data.file_path || "current directory",
                    }),
                };
            } catch (e) {
                console.error(e);
                this.fetchResult = {
                    success: false,
                    message: e.response?.data?.message || this.$t("rncp.failed_to_fetch"),
                };
            } finally {
                this.fetchInProgress = false;
            }
        },
        cancelFetch() {
            this.fetchInProgress = false;
            this.fetchProgress = 0;
        },
        async startListen() {
            const allowedHashes = this.listenAllowedHashes
                .split("\n")
                .map((h) => h.trim())
                .filter((h) => h.length === 32);

            if (allowedHashes.length === 0) {
                DialogUtils.alert(this.$t("rncp.provide_allowed_hash"));
                return;
            }

            this.listenResult = null;

            try {
                const response = await window.axios.post("/api/v1/rncp/listen", {
                    allowed_hashes: allowedHashes,
                    fetch_allowed: this.listenFetchAllowed,
                    fetch_jail: this.listenFetchJail || null,
                    allow_overwrite: this.listenAllowOverwrite,
                });

                this.listenActive = true;
                this.listenDestinationHash = response.data.destination_hash;
                this.listenResult = {
                    success: true,
                    message: response.data.message,
                };
            } catch (e) {
                console.error(e);
                this.listenResult = {
                    success: false,
                    message: e.response?.data?.message || this.$t("rncp.failed_to_start_listener"),
                };
            }
        },
        stopListen() {
            this.listenActive = false;
            this.listenDestinationHash = null;
            this.listenResult = null;
        },
        renderMarkdown(text) {
            return MarkdownRenderer.render(text);
        },
        handleMessageClick(event) {
            const nomadnetLink = event.target.closest(".nomadnet-link");
            if (nomadnetLink) {
                event.preventDefault();
                const url = nomadnetLink.getAttribute("data-nomadnet-url");
                if (url) {
                    const [hash, ...pathParts] = url.split(":");
                    const path = pathParts.join(":");
                    this.$router.push({
                        name: "nomadnetwork",
                        params: { destinationHash: hash },
                        query: { path: path },
                    });
                }
            }
        },
    },
};
</script>
