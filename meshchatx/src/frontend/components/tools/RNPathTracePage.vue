<template>
    <div class="flex flex-col flex-1 h-full overflow-hidden bg-slate-50 dark:bg-zinc-950">
        <!-- header -->
        <div class="bg-white dark:bg-zinc-900 border-b border-gray-200 dark:border-zinc-800 shadow-sm z-10">
            <div class="px-4 py-3 md:px-6 md:py-4 flex items-center justify-between gap-4">
                <div class="flex items-center gap-3">
                    <div class="p-2 bg-indigo-100 dark:bg-indigo-900/30 rounded-xl shrink-0">
                        <MaterialDesignIcon
                            icon-name="map-marker-path"
                            class="size-5 md:size-6 text-indigo-600 dark:text-indigo-400"
                        />
                    </div>
                    <div class="min-w-0">
                        <h1 class="text-lg md:text-xl font-bold text-gray-900 dark:text-white truncate">
                            {{ $t("tools.rnpath_trace.title") }}
                        </h1>
                        <p class="text-[10px] md:text-xs text-gray-500 dark:text-gray-400 truncate">
                            {{ $t("tools.rnpath_trace.description") }}
                        </p>
                    </div>
                </div>

                <div class="flex items-center gap-2">
                    <button
                        v-if="traceResult"
                        class="p-2 text-gray-400 hover:text-indigo-500 dark:hover:text-indigo-400 transition-colors shrink-0"
                        title="Refresh Trace"
                        @click="runTrace"
                    >
                        <MaterialDesignIcon icon-name="refresh" class="size-5" :class="{ 'animate-spin': isLoading }" />
                    </button>
                </div>
            </div>
        </div>

        <div class="flex-1 overflow-y-auto">
            <div class="p-4 md:p-6 lg:p-8 max-w-5xl mx-auto space-y-6">
                <!-- main input card -->
                <div class="glass-card p-4 md:p-6">
                    <div class="flex items-center gap-3">
                        <div class="relative flex-1">
                            <input
                                v-model="destinationHash"
                                type="text"
                                placeholder="input destination hash"
                                class="w-full pl-4 pr-12 py-3 bg-gray-50 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-2xl text-sm md:text-base font-mono focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all dark:text-white shadow-inner"
                                @keyup.enter="runTrace"
                            />
                            <div
                                class="absolute inset-y-0 right-0 flex items-center pr-4 pointer-events-none text-gray-400 dark:text-zinc-500"
                            >
                                <MaterialDesignIcon icon-name="identifier" class="size-5" />
                            </div>
                        </div>
                        <button
                            class="size-12 md:size-14 bg-indigo-600 hover:bg-indigo-500 text-white rounded-2xl flex items-center justify-center transition shadow-lg shadow-indigo-500/20 active:scale-95 disabled:opacity-50 shrink-0"
                            :disabled="!isValidHash || isLoading"
                            title="Trace Path"
                            @click="runTrace"
                        >
                            <MaterialDesignIcon
                                v-if="!isLoading"
                                icon-name="keyboard-return"
                                class="size-6 md:size-7"
                            />
                            <MaterialDesignIcon v-else icon-name="loading" class="size-6 animate-spin" />
                        </button>
                    </div>
                </div>

                <!-- results area -->
                <div v-if="traceResult || isLoading || error" class="space-y-6">
                    <!-- loading state -->
                    <div v-if="isLoading" class="glass-card p-12 flex flex-col items-center justify-center gap-4">
                        <div class="relative">
                            <div
                                class="w-12 h-12 border-4 border-indigo-200 dark:border-indigo-900/30 border-t-indigo-600 rounded-full animate-spin"
                            ></div>
                        </div>
                        <div class="text-sm font-medium text-gray-600 dark:text-gray-400">
                            {{ $t("tools.rnpath_trace.tracing") }}
                        </div>
                    </div>

                    <!-- error state -->
                    <div
                        v-else-if="error"
                        class="glass-card p-6 border-l-4 border-l-red-500 bg-red-50/50 dark:bg-red-900/10"
                    >
                        <div class="flex items-start gap-3 text-red-600 dark:text-red-400">
                            <MaterialDesignIcon icon-name="alert-circle" class="size-5 md:size-6 shrink-0 mt-0.5" />
                            <div class="space-y-1">
                                <div class="font-bold text-sm md:text-base">Trace Error</div>
                                <div class="text-xs md:text-sm opacity-90 break-all whitespace-pre-wrap font-mono">
                                    {{ error }}
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- success state -->
                    <div
                        v-else-if="traceResult"
                        class="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500"
                    >
                        <!-- compact summary bar -->
                        <div class="glass-card p-1 overflow-hidden">
                            <div class="flex flex-wrap items-center divide-x divide-gray-100 dark:divide-zinc-800">
                                <div class="flex-1 min-w-[120px] p-3 md:p-4 flex flex-col items-center text-center">
                                    <div class="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">
                                        {{ $t("tools.rnpath_trace.total_hops") }}
                                    </div>
                                    <div class="text-xl md:text-2xl font-black text-indigo-600 dark:text-indigo-400">
                                        {{ traceResult.hops }}
                                    </div>
                                </div>
                                <div class="flex-1 min-w-[120px] p-3 md:p-4 flex flex-col items-center text-center">
                                    <div class="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">
                                        {{ $t("tools.rnpath_trace.interface") }}
                                    </div>
                                    <div
                                        class="text-xs md:text-sm font-bold text-gray-700 dark:text-zinc-200 truncate max-w-full"
                                    >
                                        {{ traceResult.interface || "None" }}
                                    </div>
                                </div>
                                <div
                                    class="flex-1 min-w-[120px] p-3 md:p-4 flex flex-col items-center text-center hidden sm:flex"
                                >
                                    <div class="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">
                                        {{ $t("tools.rnpath_trace.next_hop") }}
                                    </div>
                                    <div
                                        class="text-[10px] md:text-xs font-mono font-bold text-gray-700 dark:text-zinc-300 truncate max-w-full"
                                    >
                                        {{ traceResult.next_hop || "N/A" }}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- path visualization -->
                        <div class="glass-card p-6 md:p-10 lg:p-16">
                            <!-- Desktop View (Horizontal) -->
                            <div class="hidden md:flex items-start justify-center min-w-fit py-4">
                                <template v-for="(node, idx) in traceResult.path" :key="'d-' + idx">
                                    <!-- node item -->
                                    <div class="flex flex-col items-center group relative w-32 shrink-0">
                                        <div
                                            class="w-14 h-14 rounded-2xl flex items-center justify-center transition-all duration-300 shadow-md group-hover:shadow-indigo-500/20 group-hover:scale-110 z-10"
                                            :class="getNodeClass(node)"
                                        >
                                            <MaterialDesignIcon :icon-name="getNodeIcon(node)" class="size-7" />
                                        </div>
                                        <div class="mt-4 text-center px-2 w-full">
                                            <div class="text-[11px] font-bold text-gray-900 dark:text-white truncate">
                                                {{
                                                    node.name ||
                                                    formatHash(node.hash) ||
                                                    (node.type === "unknown"
                                                        ? $t("tools.rnpath_trace.unknown_hops", { count: node.count })
                                                        : "")
                                                }}
                                            </div>
                                            <div
                                                v-if="node.interface"
                                                class="text-[9px] text-indigo-500 font-mono font-bold mt-0.5 truncate"
                                            >
                                                {{ node.interface }}
                                            </div>
                                        </div>

                                        <!-- tooltip -->
                                        <div
                                            v-if="node.hash"
                                            class="absolute -top-10 left-1/2 -translate-x-1/2 bg-zinc-900 dark:bg-zinc-800 text-white text-[10px] px-2 py-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-all shadow-xl border border-zinc-700 pointer-events-none font-mono whitespace-nowrap z-20"
                                        >
                                            {{ node.hash }}
                                        </div>
                                    </div>

                                    <!-- connector -->
                                    <div
                                        v-if="idx < traceResult.path.length - 1"
                                        class="flex-1 min-w-[40px] max-w-[100px] mt-7 h-0.5 relative"
                                    >
                                        <div
                                            class="absolute inset-0 bg-indigo-500/30"
                                            :class="{
                                                'border-t-2 border-dashed border-indigo-300 dark:border-indigo-800 bg-transparent h-0':
                                                    traceResult.path[idx + 1].type === 'unknown' ||
                                                    node.type === 'unknown',
                                            }"
                                        ></div>
                                        <div
                                            v-if="
                                                traceResult.path[idx + 1].type !== 'unknown' && node.type !== 'unknown'
                                            "
                                            class="absolute right-0 -top-1 w-2 h-2 rounded-full bg-indigo-500 shadow-sm shadow-indigo-500/50"
                                        ></div>
                                    </div>
                                </template>
                            </div>

                            <!-- Mobile View (Vertical) -->
                            <div class="md:hidden space-y-0">
                                <template v-for="(node, idx) in traceResult.path" :key="'m-' + idx">
                                    <div class="flex gap-4">
                                        <!-- timeline axis -->
                                        <div class="flex flex-col items-center w-10 shrink-0">
                                            <div
                                                class="w-10 h-10 rounded-xl flex items-center justify-center shadow-md z-10"
                                                :class="getNodeClass(node)"
                                            >
                                                <MaterialDesignIcon :icon-name="getNodeIcon(node)" class="size-5" />
                                            </div>
                                            <div
                                                v-if="idx < traceResult.path.length - 1"
                                                class="w-0.5 flex-1 min-h-[40px] my-1"
                                                :class="
                                                    traceResult.path[idx + 1].type === 'unknown' ||
                                                    node.type === 'unknown'
                                                        ? 'border-l-2 border-dashed border-indigo-300 dark:border-indigo-800'
                                                        : 'bg-indigo-500/30'
                                                "
                                            ></div>
                                        </div>

                                        <!-- content -->
                                        <div class="flex-1 pb-6 pt-1 min-w-0">
                                            <div class="font-bold text-sm text-gray-900 dark:text-white truncate">
                                                {{
                                                    node.name ||
                                                    (node.type === "unknown"
                                                        ? $t("tools.rnpath_trace.unknown_hops", { count: node.count })
                                                        : formatHash(node.hash))
                                                }}
                                            </div>
                                            <div
                                                v-if="node.hash"
                                                class="text-[10px] font-mono text-gray-500 dark:text-gray-400 mt-0.5 truncate"
                                            >
                                                {{ node.hash }}
                                            </div>
                                            <div
                                                v-if="node.interface"
                                                class="inline-flex items-center gap-1 mt-1.5 px-2 py-0.5 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 rounded text-[9px] font-bold uppercase tracking-wider"
                                            >
                                                <MaterialDesignIcon icon-name="router-wireless" class="size-3" />
                                                {{ node.interface }}
                                            </div>
                                        </div>
                                    </div>
                                </template>
                            </div>
                        </div>

                        <!-- action buttons -->
                        <div class="flex flex-col sm:flex-row items-center justify-center gap-3">
                            <button
                                class="w-full sm:w-auto px-6 py-3 bg-indigo-100 hover:bg-indigo-200 dark:bg-indigo-900/30 dark:hover:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 rounded-2xl font-bold transition flex items-center justify-center gap-2 text-sm"
                                @click="pingDestination"
                            >
                                <MaterialDesignIcon icon-name="radar" class="size-5" />
                                {{ $t("tools.rnpath_trace.ping_test") }}
                            </button>
                            <button
                                class="w-full sm:w-auto px-6 py-3 bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 hover:bg-gray-50 dark:hover:bg-zinc-800 text-gray-600 dark:text-gray-300 rounded-2xl font-bold transition flex items-center justify-center gap-2 text-sm"
                                @click="copyDestinationHash"
                            >
                                <MaterialDesignIcon icon-name="content-copy" class="size-5" />
                                {{ $t("common.copy_to_clipboard") }}
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
    name: "RNPathTracePage",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            destinationHash: "",
            isLoading: false,
            traceResult: null,
            error: null,
        };
    },
    computed: {
        isValidHash() {
            return /^[0-9a-f]{32}$/i.test(this.destinationHash);
        },
    },
    mounted() {
        if (this.$route.query.hash) {
            this.destinationHash = this.$route.query.hash;
            if (this.isValidHash) {
                this.runTrace();
            }
        }
    },
    methods: {
        async runTrace() {
            if (!this.isValidHash) return;

            this.isLoading = true;
            this.error = null;
            this.traceResult = null;

            try {
                const res = await window.axios.get(`/api/v1/rnpath/trace/${this.destinationHash}`);
                if (res.data.error) {
                    this.error = res.data.error;
                } else {
                    this.traceResult = res.data;
                }
            } catch (e) {
                console.error(e);
                this.error =
                    e.response?.data?.error ||
                    e.response?.data?.message ||
                    "Failed to communicate with the backend handler.";
            } finally {
                this.isLoading = false;
            }
        },
        getNodeClass(node) {
            if (node.type === "local") return "bg-blue-600 text-white";
            if (node.type === "destination") return "bg-emerald-600 text-white";
            if (node.type === "unknown")
                return "bg-gray-100 dark:bg-zinc-800 text-gray-400 dark:text-gray-600 border-2 border-dashed border-gray-200 dark:border-zinc-700 shadow-none";
            return "bg-indigo-600 text-white";
        },
        getNodeIcon(node) {
            if (node.type === "local") return "home";
            if (node.type === "destination") return "flag-variant";
            if (node.type === "unknown") return "dots-horizontal";
            return "router-wireless";
        },
        formatHash(hash) {
            if (!hash) return "";
            return hash.substring(0, 8) + "...";
        },
        pingDestination() {
            this.$router.push({
                name: "ping",
                query: {
                    hash: this.destinationHash,
                    autostart: "1",
                },
            });
        },
        copyDestinationHash() {
            if (this.destinationHash) {
                navigator.clipboard.writeText(this.destinationHash);
                ToastUtils.success(this.$t("common.copied"));
            }
        },
    },
};
</script>

<style scoped>
.glass-card {
    @apply bg-white/90 dark:bg-zinc-900/80 backdrop-blur border border-gray-200 dark:border-zinc-800 rounded-3xl shadow-xl shadow-slate-200/20 dark:shadow-none;
}
</style>
