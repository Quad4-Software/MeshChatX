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
                                <div class="flex gap-2">
                                    <input
                                        v-model="sendFilePath"
                                        type="text"
                                        placeholder="/path/to/file"
                                        class="input-field flex-1 min-w-0"
                                    />
                                    <input
                                        ref="sendFileInput"
                                        type="file"
                                        class="hidden"
                                        @change="onWebSendFilePicked"
                                    />
                                    <button
                                        type="button"
                                        class="secondary-chip px-3 py-2 text-xs shrink-0"
                                        :title="$t('rncp.browse_file')"
                                        @click="pickSendFile"
                                    >
                                        <MaterialDesignIcon icon-name="folder-open-outline" class="w-4 h-4" />
                                        {{ $t("rncp.browse_file") }}
                                    </button>
                                </div>
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
                            class="p-3 rounded-lg space-y-2"
                            :class="
                                sendResult.success
                                    ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                                    : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'
                            "
                        >
                            <div>{{ sendResult.message }}</div>
                            <div v-if="sendResult.success && sendResult.filePath" class="font-mono text-xs break-all">
                                {{ sendResult.filePath }}
                            </div>
                            <div v-if="sendResult.success && sendResult.filePath" class="flex gap-2">
                                <button
                                    type="button"
                                    class="secondary-chip text-xs py-1 px-2"
                                    @click="openPathInOs(sendResult.filePath)"
                                >
                                    {{ $t("rncp.show_in_folder") }}
                                </button>
                            </div>
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
                                <div class="flex gap-2">
                                    <input
                                        v-model="fetchSavePath"
                                        type="text"
                                        :placeholder="$t('rncp.save_path_placeholder')"
                                        class="input-field flex-1 min-w-0"
                                    />
                                    <button
                                        type="button"
                                        class="secondary-chip px-3 py-2 text-xs shrink-0"
                                        :title="$t('rncp.browse_folder')"
                                        @click="pickFetchSaveDirectory"
                                    >
                                        <MaterialDesignIcon icon-name="folder-open-outline" class="w-4 h-4" />
                                        {{ $t("rncp.browse_folder") }}
                                    </button>
                                </div>
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
                            class="p-3 rounded-lg space-y-2"
                            :class="
                                fetchResult.success
                                    ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                                    : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'
                            "
                        >
                            <div>{{ fetchResult.message }}</div>
                            <div
                                v-if="fetchResult.success && fetchResult.savedPath"
                                class="font-mono text-xs break-all"
                            >
                                {{ fetchResult.savedPath }}
                            </div>
                            <div v-if="fetchResult.success && fetchResult.savedPath" class="flex gap-2">
                                <button
                                    type="button"
                                    class="secondary-chip text-xs py-1 px-2"
                                    @click="openPathInOs(fetchResult.savedPath)"
                                >
                                    {{ $t("rncp.show_in_folder") }}
                                </button>
                            </div>
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
                        <p class="text-xs text-gray-500 dark:text-zinc-400">
                            {{ $t("rncp.listening_active_background") }}
                        </p>
                        <div
                            v-if="receiveDirectory"
                            class="p-3 rounded-lg bg-slate-50 dark:bg-zinc-800/80 border border-gray-200 dark:border-zinc-700 space-y-2"
                        >
                            <div class="text-xs font-semibold text-gray-600 dark:text-zinc-300">
                                {{ $t("rncp.receive_folder") }}
                            </div>
                            <div class="font-mono text-xs break-all text-gray-800 dark:text-zinc-200">
                                {{ receiveDirectory }}
                            </div>
                            <button
                                type="button"
                                class="secondary-chip text-xs py-1.5 px-2"
                                @click="openReceiveDirectory"
                            >
                                <MaterialDesignIcon icon-name="folder-open-outline" class="w-4 h-4" />
                                {{ $t("rncp.open_folder") }}
                            </button>
                        </div>
                        <div
                            v-if="lastReceiveEvent"
                            class="p-3 rounded-lg border space-y-2"
                            :class="
                                lastReceiveEvent.status === 'completed'
                                    ? 'bg-green-50/80 dark:bg-green-900/15 border-green-200 dark:border-green-800'
                                    : 'bg-amber-50/80 dark:bg-amber-900/15 border-amber-200 dark:border-amber-800'
                            "
                        >
                            <div class="text-sm font-semibold text-gray-800 dark:text-zinc-100">
                                {{
                                    lastReceiveEvent.status === "completed"
                                        ? $t("rncp.received_file")
                                        : $t("rncp.receive_failed")
                                }}
                            </div>
                            <div v-if="lastReceiveEvent.saved_path" class="font-mono text-xs break-all">
                                {{ lastReceiveEvent.saved_path }}
                            </div>
                            <div v-if="lastReceiveEvent.error" class="text-xs text-red-600 dark:text-red-400">
                                {{ lastReceiveEvent.error }}
                            </div>
                            <button
                                v-if="lastReceiveEvent.saved_path"
                                type="button"
                                class="secondary-chip text-xs py-1 px-2"
                                @click="openPathInOs(lastReceiveEvent.saved_path)"
                            >
                                {{ $t("rncp.show_in_folder") }}
                            </button>
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
import ElectronUtils from "../../js/ElectronUtils";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import WebSocketConnection from "../../js/WebSocketConnection";
import MarkdownRenderer from "../../js/MarkdownRenderer";
import ToastUtils from "../../js/ToastUtils";

const RNCP_LISTEN_PREFS_KEY = "meshchatx.rncp.listenForm.v1";

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
            receiveDirectory: null,
            lastReceiveEvent: null,
            fetchTransferId: null,
        };
    },
    watch: {
        listenAllowedHashes() {
            this.saveRncpListenPrefs();
        },
        listenFetchJail() {
            this.saveRncpListenPrefs();
        },
        listenFetchAllowed() {
            this.saveRncpListenPrefs();
        },
        listenAllowOverwrite() {
            this.saveRncpListenPrefs();
        },
    },
    mounted() {
        WebSocketConnection.on("message", this.handleWebSocketMessage);
        this.loadRncpListenPrefs();
        this.syncListenerStatusFromServer();
    },
    beforeUnmount() {
        WebSocketConnection.off("message", this.handleWebSocketMessage);
        this.cancelSend();
        this.cancelFetch();
    },
    methods: {
        loadRncpListenPrefs() {
            try {
                const raw = localStorage.getItem(RNCP_LISTEN_PREFS_KEY);
                if (!raw) {
                    return;
                }
                const o = JSON.parse(raw);
                if (typeof o.listenAllowedHashes === "string") {
                    this.listenAllowedHashes = o.listenAllowedHashes;
                }
                if (o.listenFetchJail != null) {
                    this.listenFetchJail = o.listenFetchJail;
                }
                if (typeof o.listenFetchAllowed === "boolean") {
                    this.listenFetchAllowed = o.listenFetchAllowed;
                }
                if (typeof o.listenAllowOverwrite === "boolean") {
                    this.listenAllowOverwrite = o.listenAllowOverwrite;
                }
            } catch {
                // ignore invalid storage
            }
        },
        saveRncpListenPrefs() {
            try {
                localStorage.setItem(
                    RNCP_LISTEN_PREFS_KEY,
                    JSON.stringify({
                        listenAllowedHashes: this.listenAllowedHashes,
                        listenFetchJail: this.listenFetchJail,
                        listenFetchAllowed: this.listenFetchAllowed,
                        listenAllowOverwrite: this.listenAllowOverwrite,
                    })
                );
            } catch {
                // ignore quota / private mode
            }
        },
        async syncListenerStatusFromServer() {
            try {
                const response = await window.api.get("/api/v1/rncp/status");
                const s = response.data;
                this.receiveDirectory = s.receive_directory || null;
                if (!s?.listening) {
                    return;
                }
                this.listenActive = true;
                this.listenDestinationHash = s.destination_hash || null;
                if (Array.isArray(s.allowed_hashes) && s.allowed_hashes.length) {
                    this.listenAllowedHashes = s.allowed_hashes.join("\n");
                }
                this.listenFetchAllowed = Boolean(s.fetch_allowed);
                this.listenFetchJail = s.fetch_jail || null;
                this.listenAllowOverwrite = Boolean(s.allow_overwrite);
            } catch (e) {
                console.error(e);
            }
        },
        notifyRncp(title, body) {
            const text = body || title;
            ToastUtils.success(text);
            if (ElectronUtils.isElectron()) {
                ElectronUtils.showNotification(title, body || "");
            }
        },
        notifyRncpError(title, body) {
            ToastUtils.error(body || title);
            if (ElectronUtils.isElectron()) {
                ElectronUtils.showNotification(title, body || "", true);
            }
        },
        async openPathInOs(filePath) {
            if (!filePath) {
                return;
            }
            const ok = await ElectronUtils.revealPathInFolderOrCopy(filePath, () =>
                ToastUtils.success(this.$t("common.copied"))
            );
            if (!ok) {
                DialogUtils.alert(filePath);
            }
        },
        async openReceiveDirectory() {
            if (!this.receiveDirectory) {
                await this.syncListenerStatusFromServer();
            }
            if (!this.receiveDirectory) {
                return;
            }
            const ok = await ElectronUtils.openDirectoryOrCopy(this.receiveDirectory, () =>
                ToastUtils.success(this.$t("common.copied"))
            );
            if (!ok) {
                DialogUtils.alert(this.receiveDirectory);
            }
        },
        async pickSendFile() {
            const p = await ElectronUtils.pickFile();
            if (p) {
                this.sendFilePath = p;
                return;
            }
            this.$refs.sendFileInput?.click();
        },
        onWebSendFilePicked(event) {
            const f = event.target.files?.[0];
            event.target.value = "";
            if (!f) return;
            this.sendFilePath = f.name;
            DialogUtils.alert(this.$t("rncp.web_path_hint"));
        },
        async pickFetchSaveDirectory() {
            const p = await ElectronUtils.pickDirectory();
            if (p) {
                this.fetchSavePath = p;
                return;
            }
            if (ElectronUtils.isElectron()) {
                return;
            }
            const entered = await DialogUtils.prompt(this.$t("rncp.web_save_path_prompt"));
            if (entered != null && String(entered).trim()) {
                this.fetchSavePath = String(entered).trim();
            }
        },
        handleWebSocketMessage(message) {
            try {
                const data = JSON.parse(message.data);
                if (data.type === "rncp.transfer.progress") {
                    const tid = data.transfer_id;
                    const p = typeof data.progress === "number" ? data.progress : 0;
                    if (this.sendInProgress) {
                        if (!this.sendTransferId && tid) {
                            this.sendTransferId = tid;
                        }
                        if (tid && this.sendTransferId === tid) {
                            this.sendProgress = p;
                        }
                    } else if (this.fetchInProgress) {
                        if (!this.fetchTransferId && tid) {
                            this.fetchTransferId = tid;
                        }
                        if (tid && this.fetchTransferId === tid) {
                            this.fetchProgress = p;
                        }
                    }
                    return;
                }
                if (data.type === "rncp.receive.completed") {
                    this.lastReceiveEvent = {
                        status: data.status,
                        saved_path: data.saved_path,
                        error: data.error,
                    };
                    if (data.status === "completed" && data.saved_path) {
                        this.notifyRncp(this.$t("rncp.received_file"), data.saved_path);
                    } else if (data.status !== "completed") {
                        this.notifyRncpError(this.$t("rncp.receive_failed"), data.error || data.status);
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
            this.sendTransferId = null;

            try {
                const response = await window.api.post("/api/v1/rncp/send", {
                    destination_hash: this.sendDestinationHash,
                    file_path: this.sendFilePath,
                    timeout: this.sendTimeout,
                    no_compress: this.sendNoCompress,
                });

                this.sendTransferId = response.data.transfer_id;
                this.sendProgress = 1;
                const fp = response.data.file_path;
                this.sendResult = {
                    success: true,
                    message: this.$t("rncp.file_sent_successfully", { id: response.data.transfer_id }),
                    filePath: fp,
                };
                this.notifyRncp(this.$t("rncp.send_complete"), fp || "");
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
            this.fetchTransferId = null;

            try {
                const response = await window.api.post("/api/v1/rncp/fetch", {
                    destination_hash: this.fetchDestinationHash,
                    file_path: this.fetchFilePath,
                    timeout: this.fetchTimeout,
                    save_path: this.fetchSavePath || null,
                    allow_overwrite: this.fetchAllowOverwrite,
                });

                this.fetchProgress = 1;
                const saved = response.data.file_path;
                this.fetchResult = {
                    success: true,
                    message: this.$t("rncp.file_fetched_successfully", {
                        path: saved || "current directory",
                    }),
                    savedPath: saved,
                };
                this.notifyRncp(this.$t("rncp.fetch_complete"), saved || "");
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
                const response = await window.api.post("/api/v1/rncp/listen", {
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
                this.saveRncpListenPrefs();
            } catch (e) {
                console.error(e);
                this.listenResult = {
                    success: false,
                    message: e.response?.data?.message || this.$t("rncp.failed_to_start_listener"),
                };
            }
        },
        async stopListen() {
            try {
                await window.api.post("/api/v1/rncp/stop");
            } catch (e) {
                console.error(e);
                this.listenResult = {
                    success: false,
                    message: e.response?.data?.message || this.$t("rncp.failed_to_stop_listener"),
                };
                return;
            }
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

            const lxmfLink = event.target.closest(".lxmf-link");
            if (lxmfLink) {
                event.preventDefault();
                const address = lxmfLink.getAttribute("data-lxmf-address");
                if (address) {
                    this.$router.push({
                        name: "messages",
                        params: { destinationHash: address },
                    });
                }
            }
        },
    },
};
</script>
