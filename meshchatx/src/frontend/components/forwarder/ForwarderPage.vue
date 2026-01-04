<template>
    <div
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-gradient-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div class="flex-1 overflow-y-auto w-full">
            <div class="space-y-4 p-4 md:p-6 max-w-5xl mx-auto w-full">
                <div class="glass-card space-y-3">
                    <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                        {{ $t("tools.utilities") }}
                    </div>
                    <div class="text-2xl font-semibold text-gray-900 dark:text-white">{{ $t("forwarder.title") }}</div>
                    <div class="text-sm text-gray-600 dark:text-gray-300">
                        {{ $t("forwarder.description") }}
                    </div>
                </div>

                <!-- Add New Rule -->
                <div class="glass-card space-y-4">
                    <div class="text-lg font-semibold text-gray-900 dark:text-white">
                        {{ $t("forwarder.add_rule") }}
                    </div>
                    <div class="grid gap-4 md:grid-cols-3">
                        <div class="space-y-1">
                            <label
                                class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                                >{{ $t("forwarder.name") }}</label
                            >
                            <input
                                v-model="newRule.name"
                                type="text"
                                :placeholder="$t('forwarder.name_placeholder')"
                                class="w-full px-4 py-2 rounded-xl border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 transition-all outline-none"
                            />
                        </div>
                        <div class="space-y-1">
                            <label
                                class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                                >{{ $t("forwarder.forward_to_hash") }}</label
                            >
                            <input
                                v-model="newRule.forward_to_hash"
                                type="text"
                                :placeholder="$t('forwarder.destination_placeholder')"
                                class="w-full px-4 py-2 rounded-xl border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 transition-all outline-none"
                            />
                        </div>
                        <div class="space-y-1">
                            <label
                                class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                                >{{ $t("forwarder.source_filter") }}</label
                            >
                            <input
                                v-model="newRule.source_filter_hash"
                                type="text"
                                :placeholder="$t('forwarder.source_filter_placeholder')"
                                class="w-full px-4 py-2 rounded-xl border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 transition-all outline-none"
                            />
                        </div>
                    </div>
                    <div class="flex justify-end">
                        <button
                            class="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-medium transition-colors flex items-center gap-2"
                            @click="addRule"
                        >
                            <MaterialDesignIcon icon-name="plus" class="w-5 h-5" />
                            {{ $t("forwarder.add_button") }}
                        </button>
                    </div>
                </div>

                <!-- Rules List -->
                <div class="space-y-4">
                    <div class="text-lg font-semibold text-gray-900 dark:text-white">
                        {{ $t("forwarder.active_rules") }}
                    </div>
                    <div
                        v-if="rules.length === 0"
                        class="glass-card text-center py-12 text-gray-500 dark:text-zinc-400"
                    >
                        {{ $t("forwarder.no_rules") }}
                    </div>
                    <div
                        v-for="rule in rules"
                        :key="rule.id"
                        class="glass-card flex items-center justify-between gap-4"
                    >
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center gap-2 mb-1">
                                <div
                                    class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider"
                                    :class="
                                        rule.is_active
                                            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                            : 'bg-gray-100 text-gray-700 dark:bg-zinc-800 dark:text-zinc-400'
                                    "
                                >
                                    {{ rule.is_active ? $t("forwarder.active") : $t("forwarder.disabled") }}
                                </div>
                                <span class="text-xs text-gray-500 dark:text-zinc-400">ID: {{ rule.id }}</span>
                            </div>
                            <div v-if="rule.name" class="text-base font-semibold text-gray-900 dark:text-white mb-1">
                                {{ rule.name }}
                            </div>
                            <div class="space-y-1">
                                <div class="flex items-center gap-2">
                                    <MaterialDesignIcon
                                        icon-name="arrow-right"
                                        class="w-4 h-4 text-blue-500 shrink-0"
                                    />
                                    <span class="text-sm font-medium text-gray-900 dark:text-white truncate">
                                        {{ $t("forwarder.forwarding_to", { hash: rule.forward_to_hash }) }}
                                    </span>
                                </div>
                                <div v-if="rule.source_filter_hash" class="flex items-center gap-2">
                                    <MaterialDesignIcon
                                        icon-name="filter-variant"
                                        class="w-4 h-4 text-purple-500 shrink-0"
                                    />
                                    <span class="text-sm text-gray-600 dark:text-zinc-300 truncate">
                                        {{ $t("forwarder.source_filter_display", { hash: rule.source_filter_hash }) }}
                                    </span>
                                </div>
                            </div>
                        </div>
                        <div class="flex items-center gap-2">
                            <button
                                class="p-2 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-lg transition-colors"
                                :title="rule.is_active ? $t('forwarder.disabled') : $t('forwarder.active')"
                                @click="toggleRule(rule.id)"
                            >
                                <MaterialDesignIcon
                                    :icon-name="rule.is_active ? 'toggle-switch' : 'toggle-switch-off'"
                                    class="w-6 h-6"
                                    :class="rule.is_active ? 'text-blue-500' : 'text-gray-400'"
                                />
                            </button>
                            <button
                                class="p-2 hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500 rounded-lg transition-colors"
                                :title="$t('common.delete')"
                                @click="deleteRule(rule.id)"
                            >
                                <MaterialDesignIcon icon-name="delete" class="w-6 h-6" />
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
import WebSocketConnection from "../../js/WebSocketConnection";

export default {
    name: "ForwarderPage",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            rules: [],
            newRule: {
                name: "",
                forward_to_hash: "",
                source_filter_hash: "",
                is_active: true,
            },
        };
    },
    mounted() {
        WebSocketConnection.on("message", this.onWebsocketMessage);
        this.fetchRules();
    },
    beforeUnmount() {
        WebSocketConnection.off("message", this.onWebsocketMessage);
    },
    methods: {
        fetchRules() {
            WebSocketConnection.send(
                JSON.stringify({
                    type: "lxmf.forwarding.rules.get",
                })
            );
        },
        onWebsocketMessage(message) {
            try {
                const data = JSON.parse(message.data);
                if (data.type === "lxmf.forwarding.rules") {
                    this.rules = data.rules;
                }
            } catch (e) {
                console.error("Failed to parse websocket message", e);
            }
        },
        addRule() {
            if (!this.newRule.forward_to_hash) return;
            WebSocketConnection.send(
                JSON.stringify({
                    type: "lxmf.forwarding.rule.add",
                    rule: { ...this.newRule },
                })
            );
            this.newRule.name = "";
            this.newRule.forward_to_hash = "";
            this.newRule.source_filter_hash = "";
        },
        deleteRule(id) {
            if (confirm(this.$t("forwarder.delete_confirm"))) {
                WebSocketConnection.send(
                    JSON.stringify({
                        type: "lxmf.forwarding.rule.delete",
                        id: id,
                    })
                );
            }
        },
        toggleRule(id) {
            WebSocketConnection.send(
                JSON.stringify({
                    type: "lxmf.forwarding.rule.toggle",
                    id: id,
                })
            );
        },
    },
};
</script>

<style scoped>
.glass-card {
    @apply bg-white/80 dark:bg-zinc-900/80 backdrop-blur-md border border-gray-200 dark:border-zinc-800 p-6 rounded-3xl shadow-sm;
}
</style>
