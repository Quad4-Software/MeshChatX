<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script lang="ts">
    import { onMount } from "svelte";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import ToastUtils from "../../js/ToastUtils.js";
    import { t } from "../../js/i18n.js";
    import SieveFlowNetwork from "./components/SieveFlowNetwork.svelte";
    import SieveRuleCard from "./components/SieveRuleCard.svelte";
    import {
        createDefaultRule,
        ensureValidAction,
        ensureValidMatchTargets,
        mapRuleFromApi,
        normalizeFiltersForSave,
        reorderRules,
    } from "./lib/sieveRules";
    import type { SieveFolder, SieveFlowLabels, SieveRule } from "./lib/types";

    let filters = $state<SieveRule[]>([]);
    let folders = $state<SieveFolder[]>([]);
    let isSaving = $state(false);

    const flowLabels = $derived<SieveFlowLabels>({
        sourceNode: t("tools.sieve_filters.flow_source"),
        sourceHint: t("tools.sieve_filters.flow_source_hint"),
        rulePrefix: t("tools.sieve_filters.flow_if"),
        hide: t("tools.sieve_filters.flow_hide"),
        ignore: t("tools.sieve_filters.action_ignore"),
        banish: t("tools.sieve_filters.flow_banish"),
        folder: t("tools.sieve_filters.flow_folder"),
        noRules: t("tools.sieve_filters.flow_no_rules"),
        graphScopeEveryone: t("tools.sieve_filters.graph_scope_everyone"),
        graphScopeContacts: t("tools.sieve_filters.graph_scope_contacts"),
        graphScopeNonContacts: t("tools.sieve_filters.graph_scope_non_contacts"),
        graphMatchPeer: t("tools.sieve_filters.graph_match_peer"),
        graphMatchMessage: t("tools.sieve_filters.graph_match_message"),
        graphMatchModeSubstring: t("tools.sieve_filters.graph_match_mode_substring"),
        graphMatchModeRegex: t("tools.sieve_filters.graph_match_mode_regex"),
    });

    function addRule(): void {
        const rule = createDefaultRule(folders);
        filters = [...filters, rule];
    }

    function removeRule(index: number): void {
        filters = filters.filter((_, i) => i !== index);
    }

    function moveRule(index: number, delta: number): void {
        filters = reorderRules(filters, index, delta);
    }

    function handleActionChange(rule: SieveRule): void {
        ensureValidAction(rule, folders);
    }

    function handleMatchTargetsChange(rule: SieveRule): void {
        ensureValidMatchTargets(rule);
    }

    function onActionChangeForAll(): void {
        for (const rule of filters) {
            ensureValidAction(rule, folders);
        }
    }

    async function reload(): Promise<void> {
        try {
            const [fRes, foldersRes] = await Promise.all([
                window.api.get("/api/v1/lxmf/sieve-filters"),
                window.api.get("/api/v1/lxmf/folders"),
            ]);
            const fData = fRes?.data as { filters?: Array<Partial<SieveRule>> } | undefined;
            const raw = fData?.filters || [];
            filters = raw.map((r) => mapRuleFromApi(r));
            const foldersData = foldersRes?.data as SieveFolder[] | undefined;
            folders = Array.isArray(foldersData) ? foldersData : [];
            onActionChangeForAll();
        } catch (e) {
            console.error(e);
            ToastUtils.error(t("tools.sieve_filters.load_failed"));
        }
    }

    async function save(): Promise<void> {
        isSaving = true;
        try {
            const payload = { filters: normalizeFiltersForSave(filters) };
            const res = await window.api.put("/api/v1/lxmf/sieve-filters", payload);
            const putData = res?.data as { filters?: Array<Partial<SieveRule>> } | undefined;
            const savedFilters = putData?.filters || [];
            filters = savedFilters.map((r) => mapRuleFromApi(r));
            ToastUtils.success(t("tools.sieve_filters.saved"));
        } catch (e: any) {
            const msg =
                (e?.response && e.response.data && e.response.data.message) ||
                e?.message ||
                t("tools.sieve_filters.save_failed");
            ToastUtils.error(msg);
        } finally {
            isSaving = false;
        }
    }

    onMount(() => {
        reload();
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas" data-testid="sieve-filters-page">
    <ToolsPageHeader
        icon="filter-variant"
        title={t("tools.sieve_filters.title")}
        description={t("tools.sieve_filters.description")}
        accent="violet"
    />
    <div class="flex-1 overflow-y-auto w-full pb-[max(1rem,env(safe-area-inset-bottom))]">
        <div class="p-3 sm:p-4 md:p-6 max-w-6xl mx-auto w-full space-y-4 min-w-0">
            <div class="grid grid-cols-1 xl:grid-cols-2 gap-4 items-start">
                <div class="space-y-4 min-w-0 order-2 xl:order-1">
                    <div class="rounded-xl border border-sem-border bg-sem-surface p-4 space-y-3">
                        <div class="flex items-center justify-between gap-2">
                            <h2 class="text-base font-semibold text-sem-fg">
                                {t("tools.sieve_filters.rules_heading")}
                            </h2>
                            <button
                                type="button"
                                class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-violet-600 text-white hover:bg-violet-700 transition-colors"
                                onclick={addRule}
                            >
                                <MaterialDesignIcon iconName="plus" />
                                {t("tools.sieve_filters.add_rule")}
                            </button>
                        </div>
                        <p class="text-xs text-sem-fg-muted">
                            {t("tools.sieve_filters.order_hint")}
                        </p>

                        {#if filters.length === 0}
                            <div class="text-sm text-sem-fg-muted py-6 text-center">
                                {t("tools.sieve_filters.empty_rules")}
                            </div>
                        {:else}
                            <div class="space-y-3">
                                {#each filters as rule, index (rule.id)}
                                    <SieveRuleCard
                                        {rule}
                                        {index}
                                        totalRules={filters.length}
                                        {folders}
                                        onMove={moveRule}
                                        onRemove={removeRule}
                                        onActionChange={handleActionChange}
                                        onMatchTargetsChange={handleMatchTargetsChange}
                                    />
                                {/each}
                            </div>
                        {/if}

                        <div class="flex flex-wrap gap-2 pt-2">
                            <button
                                type="button"
                                class="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-gray-900 text-white dark:bg-zinc-100 dark:text-zinc-900 hover:opacity-90"
                                disabled={isSaving}
                                onclick={save}
                            >
                                {#if !isSaving}
                                    <MaterialDesignIcon iconName="content-save-outline" />
                                {/if}
                                {#if isSaving}
                                    <span>{t("tools.sieve_filters.saving")}</span>
                                {:else}
                                    <span>{t("tools.sieve_filters.save")}</span>
                                {/if}
                            </button>
                            <button
                                type="button"
                                class="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border border-gray-300 dark:border-zinc-600 text-gray-800 dark:text-gray-200 hover:bg-sem-surface-muted"
                                disabled={isSaving}
                                onclick={reload}
                            >
                                <MaterialDesignIcon iconName="restore" />
                                {t("tools.sieve_filters.revert")}
                            </button>
                        </div>
                    </div>
                </div>

                <div class="min-w-0 order-1 xl:order-2 space-y-2">
                    <h2 class="text-base font-semibold text-sem-fg px-1">
                        {t("tools.sieve_filters.flow_heading")}
                    </h2>
                    <SieveFlowNetwork {filters} {folders} labels={flowLabels} />
                </div>
            </div>
        </div>
    </div>
</div>
