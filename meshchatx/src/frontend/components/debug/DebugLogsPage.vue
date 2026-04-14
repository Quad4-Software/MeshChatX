<template>
    <div
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-gradient-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div class="flex flex-col h-full overflow-hidden w-full px-4 md:px-5 lg:px-8 py-6">
            <div class="flex flex-col mb-4 w-full max-w-6xl mx-auto space-y-4">
                <div class="flex items-center justify-between">
                    <div class="space-y-1">
                        <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Diagnostics</div>
                        <div class="text-3xl font-semibold text-gray-900 dark:text-white">Debug Logs</div>
                    </div>
                    <div class="flex gap-2">
                        <button type="button" class="secondary-chip px-4 py-2 text-sm" @click="refreshActive">
                            <MaterialDesignIcon icon-name="refresh" class="w-4 h-4" />
                            Refresh
                        </button>
                        <button type="button" class="primary-chip px-4 py-2 text-sm" @click="copyActive">
                            <MaterialDesignIcon icon-name="content-copy" class="w-4 h-4" />
                            Copy All
                        </button>
                    </div>
                </div>

                <div class="flex flex-wrap gap-2 border-b border-gray-200 dark:border-zinc-700 pb-2">
                    <button
                        type="button"
                        class="px-4 py-2 text-sm rounded-md transition-colors"
                        :class="
                            activeTab === 'logs'
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-zinc-700'
                        "
                        @click="switchTab('logs')"
                    >
                        {{ $t("debug.tab_logs") }}
                    </button>
                    <button
                        type="button"
                        class="px-4 py-2 text-sm rounded-md transition-colors"
                        :class="
                            activeTab === 'access'
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-zinc-700'
                        "
                        @click="switchTab('access')"
                    >
                        {{ $t("debug.tab_access_attempts") }}
                    </button>
                </div>

                <div
                    v-if="activeTab === 'logs'"
                    class="flex flex-wrap gap-3 items-center bg-white/50 dark:bg-zinc-800/50 p-3 rounded-lg border border-gray-200 dark:border-zinc-700"
                >
                    <div class="relative flex-1 min-w-[200px]">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <MaterialDesignIcon icon-name="magnify" class="w-4 h-4 text-gray-400" />
                        </div>
                        <input
                            v-model="search"
                            type="text"
                            class="block w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-zinc-600 rounded-md leading-5 bg-white dark:bg-zinc-900 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                            :placeholder="$t('debug.search_logs_placeholder')"
                            @input="debouncedSearch"
                        />
                    </div>

                    <select
                        v-model="level"
                        class="block pl-3 pr-10 py-2 text-base border-gray-300 dark:border-zinc-600 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md bg-white dark:bg-zinc-900 text-gray-900 dark:text-white"
                        @change="refreshLogs"
                    >
                        <option value="">{{ $t("debug.level_all") }}</option>
                        <option value="DEBUG">Debug</option>
                        <option value="INFO">Info</option>
                        <option value="WARNING">Warning</option>
                        <option value="ERROR">Error</option>
                        <option value="CRITICAL">Critical</option>
                    </select>

                    <label class="inline-flex items-center cursor-pointer">
                        <input
                            v-model="is_anomaly"
                            type="checkbox"
                            class="form-checkbox h-4 w-4 text-blue-600 transition duration-150 ease-in-out"
                            @change="refreshLogs"
                        />
                        <span class="ml-2 text-sm text-gray-700 dark:text-gray-300">{{
                            $t("debug.anomalies_only")
                        }}</span>
                    </label>
                </div>

                <div
                    v-else
                    class="flex flex-wrap gap-3 items-center bg-white/50 dark:bg-zinc-800/50 p-3 rounded-lg border border-gray-200 dark:border-zinc-700"
                >
                    <div class="relative flex-1 min-w-[200px]">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <MaterialDesignIcon icon-name="magnify" class="w-4 h-4 text-gray-400" />
                        </div>
                        <input
                            v-model="accessSearch"
                            type="text"
                            class="block w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-zinc-600 rounded-md leading-5 bg-white dark:bg-zinc-900 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                            :placeholder="$t('debug.search_access_placeholder')"
                            @input="debouncedAccessSearch"
                        />
                    </div>
                    <select
                        v-model="accessOutcome"
                        class="block pl-3 pr-10 py-2 text-base border-gray-300 dark:border-zinc-600 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md bg-white dark:bg-zinc-900 text-gray-900 dark:text-white"
                        @change="refreshAccessAttempts"
                    >
                        <option value="">{{ $t("debug.outcome_all") }}</option>
                        <option value="success">success</option>
                        <option value="failed_password">failed_password</option>
                        <option value="rate_limited">rate_limited</option>
                        <option value="lockout">lockout</option>
                        <option value="invalid_json">invalid_json</option>
                        <option value="auth_not_setup">auth_not_setup</option>
                        <option value="password_required">password_required</option>
                        <option value="weak_password">weak_password</option>
                        <option value="setup_already_done">setup_already_done</option>
                    </select>
                </div>
            </div>

            <div class="flex-1 overflow-hidden glass-card max-w-6xl mx-auto w-full p-0 flex flex-col rounded-sm">
                <div
                    v-if="activeTab === 'logs'"
                    class="flex-1 overflow-auto p-4 font-mono text-[10px] sm:text-xs leading-relaxed select-text bg-white dark:bg-zinc-950"
                >
                    <div v-if="logs.length === 0" class="text-gray-500 italic text-center py-10">
                        {{ loading ? $t("debug.loading_logs") : $t("debug.no_logs") }}
                    </div>
                    <div
                        v-for="(log, index) in logs"
                        :key="index"
                        class="border-b border-gray-100 dark:border-zinc-900 py-1 flex gap-3 hover:bg-gray-50 dark:hover:bg-zinc-900/50"
                        :class="{ 'bg-red-50/30 dark:bg-red-900/10': log.is_anomaly }"
                    >
                        <span class="text-gray-400 shrink-0">{{ formatTime(log.timestamp) }}</span>
                        <span :class="levelClass(log.level)" class="w-12 shrink-0 font-bold uppercase">{{
                            log.level
                        }}</span>
                        <span class="text-blue-500 shrink-0 w-24 overflow-hidden text-ellipsis italic"
                            >[{{ log.module }}]</span
                        >
                        <span class="text-gray-800 dark:text-gray-200 break-words flex-1">
                            {{ log.message }}
                            <span
                                v-if="log.is_anomaly"
                                class="ml-2 inline-flex items-center px-1.5 py-0.5 rounded-full text-[8px] font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200 uppercase"
                            >
                                <MaterialDesignIcon icon-name="alert-circle" class="w-2.5 h-2.5 mr-1" />
                                {{ log.anomaly_type || "anomaly" }}
                            </span>
                        </span>
                    </div>
                </div>

                <div
                    v-else
                    class="flex-1 overflow-auto p-4 font-mono text-[10px] sm:text-xs leading-relaxed select-text bg-white dark:bg-zinc-950"
                >
                    <div v-if="accessAttempts.length === 0" class="text-gray-500 italic text-center py-10">
                        {{ accessLoading ? $t("debug.loading_access") : $t("debug.no_access") }}
                    </div>
                    <div
                        v-for="row in accessAttempts"
                        :key="row.id"
                        class="border-b border-gray-100 dark:border-zinc-900 py-2 flex flex-col gap-1 hover:bg-gray-50 dark:hover:bg-zinc-900/50"
                    >
                        <div class="flex flex-wrap gap-x-3 gap-y-1">
                            <span class="text-gray-400 shrink-0">{{ formatTime(row.created_at) }}</span>
                            <span class="text-amber-600 dark:text-amber-400 font-semibold">{{ row.outcome }}</span>
                            <span class="text-cyan-600 dark:text-cyan-400">{{ row.method }} {{ row.path }}</span>
                        </div>
                        <div class="text-gray-600 dark:text-gray-400 break-all pl-0">
                            <span class="text-gray-500">IP</span> {{ row.client_ip }}
                        </div>
                        <div class="text-gray-600 dark:text-gray-400 break-all">
                            <span class="text-gray-500">UA</span> {{ row.user_agent || "—" }}
                        </div>
                        <div v-if="row.detail" class="text-gray-500 text-[10px]">{{ row.detail }}</div>
                    </div>
                </div>

                <div
                    class="px-4 py-3 flex items-center justify-between border-t border-gray-200 dark:border-zinc-800 bg-gray-50 dark:bg-zinc-900/50"
                >
                    <div class="flex-1 flex justify-between sm:hidden">
                        <button
                            class="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                            :disabled="listOffset === 0"
                            @click="prevPage"
                        >
                            Previous
                        </button>
                        <button
                            class="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                            :disabled="listOffset + limit >= listTotal"
                            @click="nextPage"
                        >
                            Next
                        </button>
                    </div>
                    <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                        <div>
                            <p class="text-sm text-gray-700 dark:text-gray-400 font-mono">
                                Showing
                                <span class="font-bold">{{ listTotal === 0 ? 0 : listOffset + 1 }}</span>
                                to
                                <span class="font-bold">{{ Math.min(listOffset + limit, listTotal) }}</span>
                                of
                                <span class="font-bold">{{ listTotal }}</span>
                                results
                            </p>
                        </div>
                        <div class="flex gap-2">
                            <button
                                class="secondary-chip px-3 py-1 text-xs disabled:opacity-50"
                                :disabled="listOffset === 0"
                                @click="prevPage"
                            >
                                <MaterialDesignIcon icon-name="chevron-left" class="w-4 h-4" />
                                Previous
                            </button>
                            <button
                                class="secondary-chip px-3 py-1 text-xs disabled:opacity-50"
                                :disabled="listOffset + limit >= listTotal"
                                @click="nextPage"
                            >
                                Next
                                <MaterialDesignIcon icon-name="chevron-right" class="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";

export default {
    name: "DebugLogsPage",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            activeTab: "logs",
            logs: [],
            total: 0,
            limit: 100,
            offset: 0,
            search: "",
            level: "",
            is_anomaly: false,
            loading: false,
            updateInterval: null,
            searchTimeout: null,
            accessAttempts: [],
            accessTotal: 0,
            accessOffset: 0,
            accessSearch: "",
            accessOutcome: "",
            accessLoading: false,
            accessSearchTimeout: null,
        };
    },
    computed: {
        listOffset() {
            return this.activeTab === "logs" ? this.offset : this.accessOffset;
        },
        listTotal() {
            return this.activeTab === "logs" ? this.total : this.accessTotal;
        },
    },
    mounted() {
        this.refreshLogs();
        this.updateInterval = setInterval(() => {
            if (this.activeTab !== "logs") return;
            if (this.offset === 0 && !this.search && !this.is_anomaly && !this.level) {
                this.refreshLogs(true);
            }
        }, 5000);
    },
    beforeUnmount() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }
        if (this.accessSearchTimeout) {
            clearTimeout(this.accessSearchTimeout);
        }
    },
    methods: {
        switchTab(tab) {
            this.activeTab = tab;
            if (tab === "access" && this.accessAttempts.length === 0 && !this.accessLoading) {
                this.refreshAccessAttempts();
            }
        },
        refreshActive() {
            if (this.activeTab === "logs") this.refreshLogs();
            else this.refreshAccessAttempts();
        },
        async refreshLogs(silent = false) {
            if (!silent) this.loading = true;
            try {
                const params = {
                    limit: this.limit,
                    offset: this.offset,
                    search: this.search || undefined,
                    level: this.level || undefined,
                    is_anomaly: this.is_anomaly ? true : undefined,
                };
                const response = await window.api.get("/api/v1/debug/logs", { params });
                this.logs = response.data.logs;
                this.total = response.data.total;
            } catch (e) {
                console.log("Failed to fetch logs", e);
                if (!silent) ToastUtils.error(this.$t("debug.failed_fetch_logs"));
            } finally {
                if (!silent) this.loading = false;
            }
        },
        async refreshAccessAttempts(silent = false) {
            if (!silent) this.accessLoading = true;
            try {
                const params = {
                    limit: this.limit,
                    offset: this.accessOffset,
                    search: this.accessSearch || undefined,
                    outcome: this.accessOutcome || undefined,
                };
                const response = await window.api.get("/api/v1/debug/access-attempts", { params });
                this.accessAttempts = response.data.attempts;
                this.accessTotal = response.data.total;
            } catch (e) {
                console.log("Failed to fetch access attempts", e);
                if (!silent) ToastUtils.error(this.$t("debug.failed_fetch_access"));
            } finally {
                if (!silent) this.accessLoading = false;
            }
        },
        debouncedSearch() {
            if (this.searchTimeout) clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.offset = 0;
                this.refreshLogs();
            }, 500);
        },
        debouncedAccessSearch() {
            if (this.accessSearchTimeout) clearTimeout(this.accessSearchTimeout);
            this.accessSearchTimeout = setTimeout(() => {
                this.accessOffset = 0;
                this.refreshAccessAttempts();
            }, 500);
        },
        prevPage() {
            if (this.activeTab === "logs") {
                if (this.offset >= this.limit) {
                    this.offset -= this.limit;
                    this.refreshLogs();
                }
            } else if (this.accessOffset >= this.limit) {
                this.accessOffset -= this.limit;
                this.refreshAccessAttempts();
            }
        },
        nextPage() {
            if (this.activeTab === "logs") {
                if (this.offset + this.limit < this.total) {
                    this.offset += this.limit;
                    this.refreshLogs();
                }
            } else if (this.accessOffset + this.limit < this.accessTotal) {
                this.accessOffset += this.limit;
                this.refreshAccessAttempts();
            }
        },
        formatTime(timestamp) {
            try {
                const ts = typeof timestamp === "number" ? timestamp * 1000 : timestamp;
                const date = new Date(ts);
                return date.toLocaleString();
            } catch {
                return timestamp;
            }
        },
        levelClass(level) {
            const l = level.toUpperCase();
            if (l === "ERROR" || l === "CRITICAL") return "text-red-500";
            if (l === "WARNING") return "text-orange-500";
            if (l === "INFO") return "text-blue-500";
            if (l === "DEBUG") return "text-gray-500";
            return "text-gray-400";
        },
        async copyActive() {
            if (this.activeTab === "logs") {
                const logText = this.logs
                    .map(
                        (l) =>
                            `${this.formatTime(l.timestamp)} [${l.level}] [${l.module}] ${l.message}${l.is_anomaly ? " [ANOMALY:" + l.anomaly_type + "]" : ""}`
                    )
                    .join("\n");
                try {
                    await navigator.clipboard.writeText(logText);
                    ToastUtils.success(this.$t("debug.logs_copied"));
                } catch {
                    ToastUtils.error(this.$t("debug.failed_copy_logs"));
                }
            } else {
                const lines = this.accessAttempts.map((r) =>
                    [
                        this.formatTime(r.created_at),
                        r.outcome,
                        r.method,
                        r.path,
                        r.client_ip,
                        r.user_agent || "",
                        r.detail || "",
                    ].join(" | ")
                );
                try {
                    await navigator.clipboard.writeText(lines.join("\n"));
                    ToastUtils.success(this.$t("debug.access_copied"));
                } catch {
                    ToastUtils.error(this.$t("debug.failed_copy_access"));
                }
            }
        },
    },
};
</script>

<style scoped>
.glass-card {
    border-radius: 2px !important;
}
</style>
