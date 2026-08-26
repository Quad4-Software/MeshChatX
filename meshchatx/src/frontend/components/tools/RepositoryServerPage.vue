<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
        <ToolsPageHeader
            icon="package-variant"
            :title="$t('tools.repository_server.title')"
            :description="$t('tools.repository_server.description')"
            accent="sky"
        />
        <div class="flex-1 overflow-y-auto overflow-x-hidden w-full px-3 sm:px-5 md:px-5 lg:px-8 py-3 sm:py-4 min-w-0">
            <div class="space-y-0 w-full max-w-6xl xl:max-w-7xl mx-auto min-w-0">
                <div class="w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-4 sm:py-6 space-y-3">
                    <h2 class="text-sm font-semibold text-sem-fg">
                        {{ $t("tools.repository_server.http_heading") }}
                    </h2>
                    <div class="flex flex-wrap gap-3 items-end">
                        <label class="flex flex-col gap-1 text-xs min-w-40">
                            <span class="text-sem-fg-muted">{{ $t("tools.repository_server.host_label") }}</span>
                            <input
                                v-model="httpHost"
                                type="text"
                                autocomplete="off"
                                class="rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-sm text-sem-fg"
                                :disabled="httpBusy || loading || httpRunning"
                            />
                        </label>
                        <label class="flex flex-col gap-1 text-xs w-24">
                            <span class="text-sem-fg-muted">{{ $t("tools.repository_server.port_label") }}</span>
                            <input
                                v-model="httpPort"
                                type="text"
                                inputmode="numeric"
                                autocomplete="off"
                                class="rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-sm text-sem-fg"
                                :disabled="httpBusy || loading || httpRunning"
                            />
                        </label>
                        <div class="flex flex-wrap gap-2">
                            <button
                                type="button"
                                class="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 disabled:pointer-events-none"
                                :disabled="httpBusy || loading || httpRunning"
                                @click="startHttp"
                            >
                                <MaterialDesignIcon icon-name="play" class="size-4" />
                                {{ $t("tools.repository_server.start_http") }}
                            </button>
                            <button
                                type="button"
                                class="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-300 dark:border-zinc-600 bg-sem-surface text-sem-fg text-sm font-medium hover:bg-sem-surface-muted disabled:opacity-50 disabled:pointer-events-none"
                                :disabled="httpBusy || loading || !httpRunning"
                                @click="stopHttp"
                            >
                                <MaterialDesignIcon icon-name="stop" class="size-4" />
                                {{ $t("tools.repository_server.stop_http") }}
                            </button>
                            <button
                                type="button"
                                class="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-300 dark:border-zinc-600 bg-sem-surface text-sem-fg text-sm font-medium hover:bg-sem-surface-muted disabled:opacity-50 disabled:pointer-events-none"
                                :disabled="httpBusy || loading"
                                @click="restartHttp"
                            >
                                <MaterialDesignIcon icon-name="restart" class="size-4" />
                                {{ $t("tools.repository_server.restart_http") }}
                            </button>
                        </div>
                    </div>
                    <div v-if="httpRunning && status?.http?.url" class="text-xs space-y-1">
                        <div class="text-sem-fg-muted">
                            {{ $t("tools.repository_server.http_listen_label") }}
                            <span class="font-mono text-gray-900 text-sem-fg">{{ status.http.url }}</span>
                        </div>
                        <a
                            v-if="browserRepoUrl"
                            :href="browserRepoUrl"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="inline-flex items-center gap-1 text-sky-600 dark:text-sky-400 font-medium hover:underline"
                        >
                            <MaterialDesignIcon icon-name="open-in-new" class="size-4" />
                            {{ $t("tools.repository_server.open_http") }}
                        </a>
                    </div>
                </div>

                <div class="w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-4 sm:py-6 space-y-3">
                    <h2 class="text-sm font-semibold text-sem-fg">
                        {{ $t("tools.repository_server.upload_heading") }}
                    </h2>
                    <div class="flex flex-wrap items-center gap-3">
                        <label
                            class="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-sky-600 text-white text-sm font-medium cursor-pointer hover:bg-sky-700 transition-colors"
                        >
                            <MaterialDesignIcon icon-name="upload" class="size-4" />
                            {{ $t("tools.repository_server.choose_file") }}
                            <input type="file" class="hidden" @change="onUpload" />
                        </label>
                        <p v-if="lastUploadError" class="text-xs text-red-600 dark:text-red-400">
                            {{ lastUploadError }}
                        </p>
                    </div>
                </div>

                <div
                    v-if="status?.last_refresh_failed && Object.keys(status.last_refresh_failed).length"
                    class="w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-4 sm:py-6"
                >
                    <div
                        class="rounded-xl border border-amber-200 dark:border-amber-900/40 bg-amber-50 dark:bg-amber-950/30 p-3 text-xs text-amber-900 dark:text-amber-200"
                    >
                        <div class="font-semibold mb-1">{{ $t("tools.repository_server.refresh_partial") }}</div>
                        <ul class="list-disc pl-4 space-y-1">
                            <li v-for="(msg, pkg) in status.last_refresh_failed" :key="pkg">
                                <span class="font-mono">{{ pkg }}</span
                                >: {{ msg }}
                            </li>
                        </ul>
                    </div>
                </div>

                <div class="w-full py-4 sm:py-6 space-y-3">
                    <div class="flex items-center justify-between">
                        <h2 class="text-sm font-semibold text-sem-fg">
                            {{ $t("tools.repository_server.files_heading") }}
                        </h2>
                        <span class="text-xs text-gray-500">{{ entries.length }}</span>
                    </div>
                    <div v-if="loading" class="text-center text-sm text-gray-500 py-6">
                        {{ $t("common.loading") }}
                    </div>
                    <div v-else-if="entries.length === 0" class="text-center text-sm text-gray-500 py-6">
                        {{ $t("tools.repository_server.empty") }}
                    </div>
                    <table v-else class="w-full text-left text-xs">
                        <thead
                            class="text-gray-500 uppercase tracking-wide border-b border-gray-200/60 dark:border-zinc-800/60"
                        >
                            <tr>
                                <th class="px-4 py-2 font-semibold">{{ $t("tools.repository_server.col_name") }}</th>
                                <th class="px-4 py-2 font-semibold">{{ $t("tools.repository_server.col_source") }}</th>
                                <th class="px-4 py-2 font-semibold text-right">
                                    {{ $t("tools.repository_server.col_size") }}
                                </th>
                                <th class="px-4 py-2 font-semibold w-24"></th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-100 dark:divide-zinc-800/50 text-sem-fg">
                            <tr v-for="row in entries" :key="row.name + row.source">
                                <td class="px-4 py-2 font-mono break-all">{{ row.name }}</td>
                                <td class="px-4 py-2">{{ row.source }}</td>
                                <td class="px-4 py-2 text-right tabular-nums">{{ formatBytes(row.bytes) }}</td>
                                <td class="px-4 py-2 text-right">
                                    <button
                                        v-if="row.source === 'upload'"
                                        type="button"
                                        class="text-red-600 dark:text-red-400 hover:underline text-xs font-medium"
                                        @click="deleteUpload(row.name)"
                                    >
                                        {{ $t("tools.repository_server.delete") }}
                                    </button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";
import DialogUtils from "../../js/DialogUtils";
import ToolsPageHeader from "./ToolsPageHeader.vue";

export default {
    name: "RepositoryServerPage",
    components: { MaterialDesignIcon, ToolsPageHeader },
    data() {
        return {
            loading: true,
            httpBusy: false,
            httpHost: "127.0.0.1",
            httpPort: "8787",
            status: null,
            entries: [],
            lastUploadError: null,
        };
    },
    computed: {
        httpRunning() {
            return Boolean(this.status?.http?.running);
        },
        browserRepoUrl() {
            const raw = this.status?.http?.url;
            if (!raw) {
                return null;
            }
            try {
                const parsed = new URL(raw);
                if (parsed.hostname === "0.0.0.0" && typeof window !== "undefined" && window.location?.hostname) {
                    parsed.hostname = window.location.hostname;
                }
                return parsed.toString();
            } catch {
                return raw;
            }
        },
    },
    async mounted() {
        await this.loadAll();
    },
    methods: {
        syncHttpFormFromStatus() {
            const h = this.status?.http;
            if (!h) {
                return;
            }
            if (h.running) {
                if (h.host) {
                    this.httpHost = h.host;
                }
                if (h.port != null) {
                    this.httpPort = String(h.port);
                }
            } else if (h.last_host) {
                this.httpHost = h.last_host;
                this.httpPort = h.last_port != null ? String(h.last_port) : "8787";
            }
        },
        formatBytes(n) {
            if (n < 1024) return `${n} B`;
            if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
            return `${(n / (1024 * 1024)).toFixed(1)} MB`;
        },
        httpErrorToast(errKey, detail) {
            const map = {
                invalid_host: this.$t("tools.repository_server.http_err_invalid_host"),
                invalid_port: this.$t("tools.repository_server.http_err_invalid_port"),
                already_running: this.$t("tools.repository_server.http_err_already_running"),
                bind_failed: this.$t("tools.repository_server.http_err_bind_failed"),
            };
            let msg = map[errKey] || this.$t("tools.repository_server.http_err_generic");
            if (errKey === "bind_failed" && detail) {
                msg = `${msg}: ${detail}`;
            } else if (!map[errKey] && detail) {
                msg = `${msg}: ${detail}`;
            }
            ToastUtils.error(msg);
        },
        async loadAll() {
            this.loading = true;
            this.lastUploadError = null;
            try {
                const [s, list] = await Promise.all([
                    window.api.get("/api/v1/repository-server/status"),
                    window.api.get("/api/v1/repository-server/list"),
                ]);
                this.status = s.data;
                this.entries = Array.isArray(list.data) ? list.data : [];
                this.syncHttpFormFromStatus();
            } catch (e) {
                ToastUtils.error(this.$t("tools.repository_server.load_failed"));
                console.error(e);
            } finally {
                this.loading = false;
            }
        },
        buildHttpBody() {
            const body = {};
            const host = (this.httpHost || "").trim();
            if (host) {
                body.host = host;
            }
            const portRaw = (this.httpPort || "").trim();
            if (portRaw !== "") {
                const p = parseInt(portRaw, 10);
                if (!Number.isFinite(p)) {
                    return { error: "invalid_port" };
                }
                body.port = p;
            }
            return { body };
        },
        async startHttp() {
            const built = this.buildHttpBody();
            if (built.error === "invalid_port") {
                this.httpErrorToast("invalid_port");
                return;
            }
            this.httpBusy = true;
            try {
                const { data } = await window.api.post("/api/v1/repository-server/http/start", built.body || {});
                if (!data.ok) {
                    this.httpErrorToast(data.error, data.message);
                } else {
                    ToastUtils.success(this.$t("tools.repository_server.http_started"));
                }
                await this.loadAll();
            } catch (e) {
                ToastUtils.error(this.$t("tools.repository_server.http_err_generic"));
                console.error(e);
            } finally {
                this.httpBusy = false;
            }
        },
        async stopHttp() {
            this.httpBusy = true;
            try {
                await window.api.post("/api/v1/repository-server/http/stop");
                ToastUtils.success(this.$t("tools.repository_server.http_stopped"));
                await this.loadAll();
            } catch (e) {
                ToastUtils.error(this.$t("tools.repository_server.http_err_generic"));
                console.error(e);
            } finally {
                this.httpBusy = false;
            }
        },
        async restartHttp() {
            const built = this.buildHttpBody();
            if (built.error === "invalid_port") {
                this.httpErrorToast("invalid_port");
                return;
            }
            this.httpBusy = true;
            try {
                const { data } = await window.api.post("/api/v1/repository-server/http/restart", built.body || {});
                if (!data.ok) {
                    this.httpErrorToast(data.error, data.message);
                } else {
                    ToastUtils.success(this.$t("tools.repository_server.http_restarted"));
                }
                await this.loadAll();
            } catch (e) {
                ToastUtils.error(this.$t("tools.repository_server.http_err_generic"));
                console.error(e);
            } finally {
                this.httpBusy = false;
            }
        },
        async onUpload(ev) {
            const input = ev.target;
            const file = input.files && input.files[0];
            input.value = "";
            if (!file) return;
            this.lastUploadError = null;
            const form = new FormData();
            form.append("file", file, file.name);
            try {
                await window.api.post("/api/v1/repository-server/upload", form);
                ToastUtils.success(this.$t("tools.repository_server.upload_ok"));
                await this.loadAll();
            } catch (e) {
                this.lastUploadError =
                    e.response?.data?.error || e.message || this.$t("tools.repository_server.upload_failed");
                ToastUtils.error(this.$t("tools.repository_server.upload_failed"));
            }
        },
        async deleteUpload(name) {
            if (!(await DialogUtils.confirm(this.$t("tools.repository_server.delete_confirm", { name })))) {
                return;
            }
            try {
                const enc = encodeURIComponent(name);
                await window.api.delete(`/api/v1/repository-server/upload/${enc}`);
                ToastUtils.success(this.$t("tools.repository_server.delete_ok"));
                await this.loadAll();
            } catch (e) {
                ToastUtils.error(this.$t("tools.repository_server.delete_failed"));
                console.error(e);
            }
        },
    },
};
</script>
