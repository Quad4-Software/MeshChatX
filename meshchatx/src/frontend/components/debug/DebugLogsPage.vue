<template>
    <div
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-gradient-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div class="flex flex-col h-full overflow-hidden w-full px-4 md:px-8 py-6">
            <div class="flex items-center justify-between mb-4 w-full max-w-6xl mx-auto">
                <div class="space-y-1">
                    <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Diagnostics</div>
                    <div class="text-3xl font-semibold text-gray-900 dark:text-white">Debug Logs</div>
                </div>
                <div class="flex gap-2">
                    <button type="button" class="secondary-chip px-4 py-2 text-sm" @click="refreshLogs">
                        <MaterialDesignIcon icon-name="refresh" class="w-4 h-4" />
                        Refresh
                    </button>
                    <button type="button" class="primary-chip px-4 py-2 text-sm" @click="copyLogs">
                        <MaterialDesignIcon icon-name="content-copy" class="w-4 h-4" />
                        Copy All
                    </button>
                </div>
            </div>

            <div class="flex-1 overflow-hidden glass-card max-w-6xl mx-auto w-full p-0 flex flex-col">
                <div class="flex-1 overflow-auto p-4 font-mono text-[10px] sm:text-xs leading-relaxed select-text">
                    <div v-if="logs.length === 0" class="text-gray-500 italic text-center py-10">
                        No logs collected yet.
                    </div>
                    <div
                        v-for="(log, index) in logs"
                        :key="index"
                        class="border-b border-gray-100 dark:border-zinc-800 py-1 flex gap-3"
                    >
                        <span class="text-gray-400 shrink-0">{{ formatTime(log.timestamp) }}</span>
                        <span :class="levelClass(log.level)" class="w-12 shrink-0 font-bold uppercase">{{
                            log.level
                        }}</span>
                        <span class="text-blue-500 shrink-0 w-24 overflow-hidden text-ellipsis italic"
                            >[{{ log.module }}]</span
                        >
                        <span class="text-gray-800 dark:text-gray-200 break-words">{{ log.message }}</span>
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
            logs: [],
            updateInterval: null,
        };
    },
    mounted() {
        this.refreshLogs();
        this.updateInterval = setInterval(() => {
            this.refreshLogs();
        }, 5000);
    },
    beforeUnmount() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
    },
    methods: {
        async refreshLogs() {
            try {
                const response = await window.axios.get("/api/v1/debug/logs");
                this.logs = response.data;
            } catch (e) {
                console.log("Failed to fetch logs", e);
            }
        },
        formatTime(timestamp) {
            try {
                const date = new Date(timestamp);
                return date.toLocaleTimeString();
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
        async copyLogs() {
            const logText = this.logs.map((l) => `${l.timestamp} [${l.level}] [${l.module}] ${l.message}`).join("\n");
            try {
                await navigator.clipboard.writeText(logText);
                ToastUtils.success("Logs copied to clipboard");
            } catch {
                ToastUtils.error("Failed to copy logs");
            }
        },
    },
};
</script>
