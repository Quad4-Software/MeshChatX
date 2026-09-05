<!-- SPDX-License-Identifier: 0BSD -->

<script>
    import { onMount } from "svelte";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import WebSocketConnection from "../../js/WebSocketConnection.js";
    import GlobalEmitter from "../../js/GlobalEmitter.js";
    import DialogUtils from "../../js/DialogUtils.js";
    import ToastUtils from "../../js/ToastUtils.js";
    import { onWsEvent, offWsEvent } from "../../js/registries/wsEventRegistry.js";
    import { t } from "../../js/i18n.js";
    import { isValidForwarderDestinationHash } from "./lib/forwarderHash.js";

    /** @type {Array<{ id: string, name?: string, forward_to_hash: string, source_filter_hash?: string, is_active?: boolean }>} */
    let rules = $state([]);
    let newRule = $state({
        name: "",
        forward_to_hash: "",
        source_filter_hash: "",
        is_active: true,
    });

    function onWebsocketReconnected() {
        fetchRules();
    }

    function fetchRules() {
        WebSocketConnection.send(
            JSON.stringify({
                type: "lxmf.forwarding.rules.get",
            })
        );
    }

    /**
     * @param {{ rules?: typeof rules }} data
     */
    function onForwardingRules(data) {
        rules = Array.isArray(data?.rules) ? data.rules : [];
    }

    function addRule() {
        if (!newRule.forward_to_hash) {
            return;
        }
        const hash = String(newRule.forward_to_hash || "").trim();
        if (!isValidForwarderDestinationHash(hash)) {
            ToastUtils.warning(t("forwarder.invalid_hash"));
            return;
        }
        const sent = WebSocketConnection.send(
            JSON.stringify({
                type: "lxmf.forwarding.rule.add",
                rule: { ...newRule, forward_to_hash: hash },
            })
        );
        if (sent === false) {
            ToastUtils.error(t("forwarder.send_failed"));
            return;
        }
        newRule = {
            name: "",
            forward_to_hash: "",
            source_filter_hash: "",
            is_active: true,
        };
        ToastUtils.success(t("forwarder.rule_added"));
    }

    /**
     * @param {string} id
     */
    async function deleteRule(id) {
        if (!(await DialogUtils.confirm(t("forwarder.delete_confirm")))) {
            return;
        }
        const sent = WebSocketConnection.send(
            JSON.stringify({
                type: "lxmf.forwarding.rule.delete",
                id,
            })
        );
        if (sent === false) {
            ToastUtils.error(t("forwarder.send_failed"));
            return;
        }
        ToastUtils.success(t("forwarder.rule_deleted"));
    }

    /**
     * @param {string} id
     */
    function toggleRule(id) {
        const sent = WebSocketConnection.send(
            JSON.stringify({
                type: "lxmf.forwarding.rule.toggle",
                id,
            })
        );
        if (sent === false) {
            ToastUtils.error(t("forwarder.send_failed"));
        }
    }

    onMount(() => {
        onWsEvent("lxmf.forwarding.rules", onForwardingRules);
        GlobalEmitter.on("websocket-reconnected", onWebsocketReconnected);
        fetchRules();
        return () => {
            offWsEvent("lxmf.forwarding.rules", onForwardingRules);
            GlobalEmitter.off("websocket-reconnected", onWebsocketReconnected);
        };
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas" data-testid="forwarder-page">
    <ToolsPageHeader
        icon="email-send-outline"
        title={t("tools.forwarder.title")}
        description={t("tools.forwarder.description")}
        accent="rose"
    />
    <div class="flex-1 overflow-y-auto w-full pb-[max(1.5rem,env(safe-area-inset-bottom))]">
        <div class="space-y-4 p-4 md:p-6 max-w-5xl mx-auto w-full">
            <div class="glass-card space-y-4">
                <div class="text-lg font-semibold text-sem-fg">
                    {t("forwarder.add_rule")}
                </div>
                <div class="grid gap-4 md:grid-cols-3">
                    <div class="space-y-1">
                        <label class="text-xs font-medium text-sem-fg-muted uppercase tracking-wider" for="fwd-name">
                            {t("forwarder.name")}
                        </label>
                        <input
                            id="fwd-name"
                            bind:value={newRule.name}
                            type="text"
                            placeholder={t("forwarder.name_placeholder")}
                            class="w-full px-4 py-2 rounded-xl border border-sem-border bg-sem-surface text-sem-fg focus:ring-2 focus:ring-blue-500 transition-all outline-hidden"
                        />
                    </div>
                    <div class="space-y-1">
                        <label class="text-xs font-medium text-sem-fg-muted uppercase tracking-wider" for="fwd-hash">
                            {t("forwarder.forward_to_hash")}
                        </label>
                        <input
                            id="fwd-hash"
                            bind:value={newRule.forward_to_hash}
                            type="text"
                            placeholder={t("forwarder.destination_placeholder")}
                            class="w-full px-4 py-2 rounded-xl border border-sem-border bg-sem-surface text-sem-fg focus:ring-2 focus:ring-blue-500 transition-all outline-hidden"
                        />
                    </div>
                    <div class="space-y-1">
                        <label class="text-xs font-medium text-sem-fg-muted uppercase tracking-wider" for="fwd-source">
                            {t("forwarder.source_filter")}
                        </label>
                        <input
                            id="fwd-source"
                            bind:value={newRule.source_filter_hash}
                            type="text"
                            placeholder={t("forwarder.source_filter_placeholder")}
                            class="w-full px-4 py-2 rounded-xl border border-sem-border bg-sem-surface text-sem-fg focus:ring-2 focus:ring-blue-500 transition-all outline-hidden"
                        />
                    </div>
                </div>
                <div class="flex justify-end">
                    <button
                        type="button"
                        class="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-medium transition-colors flex items-center gap-2"
                        onclick={addRule}
                    >
                        <MaterialDesignIcon iconName="plus" />
                        {t("forwarder.add_button")}
                    </button>
                </div>
            </div>

            <div class="space-y-4">
                <div class="text-lg font-semibold text-sem-fg">
                    {t("forwarder.active_rules")}
                </div>
                {#if rules.length === 0}
                    <div class="glass-card text-center py-12 text-sem-fg-muted">
                        {t("forwarder.no_rules")}
                    </div>
                {:else}
                    {#each rules as rule (rule.id)}
                        <div class="glass-card flex items-center justify-between gap-4">
                            <div class="flex-1 min-w-0">
                                <div class="flex items-center gap-2 mb-1">
                                    <div
                                        class="px-2 py-0.5 rounded-sm text-[10px] font-bold uppercase tracking-wider {rule.is_active
                                            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                            : 'bg-gray-100 text-gray-700 dark:bg-zinc-800 text-sem-fg-muted'}"
                                    >
                                        {rule.is_active ? t("forwarder.active") : t("forwarder.disabled")}
                                    </div>
                                    <span class="text-xs text-sem-fg-muted">ID: {rule.id}</span>
                                </div>
                                {#if rule.name}
                                    <div class="text-base font-semibold text-sem-fg mb-1">
                                        {rule.name}
                                    </div>
                                {/if}
                                <div class="space-y-1">
                                    <div class="flex items-center gap-2">
                                        <span class="text-blue-500 shrink-0">
                                            <MaterialDesignIcon iconName="arrow-right" />
                                        </span>
                                        <span class="text-sm font-medium text-sem-fg truncate">
                                            {t("forwarder.forwarding_to", { hash: rule.forward_to_hash })}
                                        </span>
                                    </div>
                                    {#if rule.source_filter_hash}
                                        <div class="flex items-center gap-2">
                                            <span class="text-purple-500 shrink-0">
                                                <MaterialDesignIcon iconName="filter-variant" />
                                            </span>
                                            <span class="text-sm text-sem-fg-muted truncate">
                                                {t("forwarder.source_filter_display", {
                                                    hash: rule.source_filter_hash,
                                                })}
                                            </span>
                                        </div>
                                    {/if}
                                </div>
                            </div>
                            <div class="flex items-center gap-2">
                                <button
                                    type="button"
                                    class="p-2 hover:bg-sem-surface-muted rounded-lg transition-colors {rule.is_active
                                        ? 'text-blue-500'
                                        : 'text-gray-400'}"
                                    title={rule.is_active ? t("forwarder.disabled") : t("forwarder.active")}
                                    onclick={() => toggleRule(rule.id)}
                                >
                                    <MaterialDesignIcon
                                        iconName={rule.is_active ? "toggle-switch" : "toggle-switch-off"}
                                    />
                                </button>
                                <button
                                    type="button"
                                    class="p-2 hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500 rounded-lg transition-colors"
                                    title={t("common.delete")}
                                    onclick={() => deleteRule(rule.id)}
                                >
                                    <MaterialDesignIcon iconName="delete" />
                                </button>
                            </div>
                        </div>
                    {/each}
                {/if}
            </div>
        </div>
    </div>
</div>
