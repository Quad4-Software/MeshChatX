<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
        <ToolsPageHeader
            icon="email-send-outline"
            :title="$t('tools.forwarder.title')"
            :description="$t('tools.forwarder.description')"
            accent="rose"
        />
        <div class="flex-1 overflow-y-auto w-full pb-[max(1.5rem,env(safe-area-inset-bottom))]">
            <div class="space-y-4 p-4 md:p-6 max-w-5xl mx-auto w-full">
                <!-- Add New Rule -->
                <div class="glass-card space-y-4">
                    <div class="text-lg font-semibold text-sem-fg">
                        {{ $t("forwarder.add_rule") }}
                    </div>
                    <div class="grid gap-4 md:grid-cols-3">
                        <div class="space-y-1">
                            <label class="text-xs font-medium text-sem-fg-muted uppercase tracking-wider">{{
                                $t("forwarder.name")
                            }}</label>
                            <input
                                v-model="newRule.name"
                                type="text"
                                :placeholder="$t('forwarder.name_placeholder')"
                                class="w-full px-4 py-2 rounded-xl border border-sem-border bg-sem-surface text-sem-fg focus:ring-2 focus:ring-blue-500 transition-all outline-hidden"
                            />
                        </div>
                        <div class="space-y-1">
                            <label class="text-xs font-medium text-sem-fg-muted uppercase tracking-wider">{{
                                $t("forwarder.forward_to_hash")
                            }}</label>
                            <input
                                v-model="newRule.forward_to_hash"
                                type="text"
                                :placeholder="$t('forwarder.destination_placeholder')"
                                class="w-full px-4 py-2 rounded-xl border border-sem-border bg-sem-surface text-sem-fg focus:ring-2 focus:ring-blue-500 transition-all outline-hidden"
                            />
                        </div>
                        <div class="space-y-1">
                            <label class="text-xs font-medium text-sem-fg-muted uppercase tracking-wider">{{
                                $t("forwarder.source_filter")
                            }}</label>
                            <input
                                v-model="newRule.source_filter_hash"
                                type="text"
                                :placeholder="$t('forwarder.source_filter_placeholder')"
                                class="w-full px-4 py-2 rounded-xl border border-sem-border bg-sem-surface text-sem-fg focus:ring-2 focus:ring-blue-500 transition-all outline-hidden"
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
                    <div class="text-lg font-semibold text-sem-fg">
                        {{ $t("forwarder.active_rules") }}
                    </div>
                    <div v-if="rules.length === 0" class="glass-card text-center py-12 text-sem-fg-muted">
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
                                    class="px-2 py-0.5 rounded-sm text-[10px] font-bold uppercase tracking-wider"
                                    :class="
                                        rule.is_active
                                            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                            : 'bg-gray-100 text-gray-700 dark:bg-zinc-800 text-sem-fg-muted'
                                    "
                                >
                                    {{ rule.is_active ? $t("forwarder.active") : $t("forwarder.disabled") }}
                                </div>
                                <span class="text-xs text-sem-fg-muted">ID: {{ rule.id }}</span>
                            </div>
                            <div v-if="rule.name" class="text-base font-semibold text-sem-fg mb-1">
                                {{ rule.name }}
                            </div>
                            <div class="space-y-1">
                                <div class="flex items-center gap-2">
                                    <MaterialDesignIcon
                                        icon-name="arrow-right"
                                        class="w-4 h-4 text-blue-500 shrink-0"
                                    />
                                    <span class="text-sm font-medium text-sem-fg truncate">
                                        {{ $t("forwarder.forwarding_to", { hash: rule.forward_to_hash }) }}
                                    </span>
                                </div>
                                <div v-if="rule.source_filter_hash" class="flex items-center gap-2">
                                    <MaterialDesignIcon
                                        icon-name="filter-variant"
                                        class="w-4 h-4 text-purple-500 shrink-0"
                                    />
                                    <span class="text-sm text-sem-fg-muted truncate">
                                        {{ $t("forwarder.source_filter_display", { hash: rule.source_filter_hash }) }}
                                    </span>
                                </div>
                            </div>
                        </div>
                        <div class="flex items-center gap-2">
                            <button
                                class="p-2 hover:bg-sem-surface-muted rounded-lg transition-colors"
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
import DialogUtils from "../../js/DialogUtils";
import ToastUtils from "../../js/ToastUtils";
import ToolsPageHeader from "../tools/ToolsPageHeader.vue";

export default {
    name: "ForwarderPage",
    components: {
        MaterialDesignIcon,
        ToolsPageHeader,
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
            const hash = String(this.newRule.forward_to_hash || "").trim();
            if (hash.length !== 32 || !/^[0-9a-fA-F]+$/.test(hash)) {
                ToastUtils.warning(this.$t("forwarder.invalid_hash"));
                return;
            }
            const sent = WebSocketConnection.send(
                JSON.stringify({
                    type: "lxmf.forwarding.rule.add",
                    rule: { ...this.newRule, forward_to_hash: hash },
                })
            );
            if (sent === false) {
                ToastUtils.error(this.$t("forwarder.send_failed"));
                return;
            }
            this.newRule.name = "";
            this.newRule.forward_to_hash = "";
            this.newRule.source_filter_hash = "";
            ToastUtils.success(this.$t("forwarder.rule_added"));
        },
        async deleteRule(id) {
            if (await DialogUtils.confirm(this.$t("forwarder.delete_confirm"))) {
                const sent = WebSocketConnection.send(
                    JSON.stringify({
                        type: "lxmf.forwarding.rule.delete",
                        id: id,
                    })
                );
                if (sent === false) {
                    ToastUtils.error(this.$t("forwarder.send_failed"));
                    return;
                }
                ToastUtils.success(this.$t("forwarder.rule_deleted"));
            }
        },
        toggleRule(id) {
            const sent = WebSocketConnection.send(
                JSON.stringify({
                    type: "lxmf.forwarding.rule.toggle",
                    id: id,
                })
            );
            if (sent === false) {
                ToastUtils.error(this.$t("forwarder.send_failed"));
            }
        },
    },
};
</script>
