<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { formatTermsText, parseTermsInput } from "../lib/sieveRules";
    import type { SieveFolder, SieveRule } from "../lib/types";

    interface Props {
        rule: SieveRule;
        index: number;
        totalRules: number;
        folders: SieveFolder[];
        onMove: (index: number, delta: number) => void;
        onRemove: (index: number) => void;
        onActionChange: (rule: SieveRule) => void;
        onMatchTargetsChange: (rule: SieveRule) => void;
    }

    let { rule, index, totalRules, folders, onMove, onRemove, onActionChange, onMatchTargetsChange }: Props = $props();

    function onTermsInput(raw: string): void {
        rule.terms = parseTermsInput(raw);
    }
</script>

<div class="rounded-lg border border-sem-border p-3 space-y-3 bg-gray-50/80 dark:bg-zinc-900/40">
    <div class="flex flex-wrap items-center justify-between gap-2">
        <label class="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
            <input bind:checked={rule.enabled} type="checkbox" class="rounded-sm border-gray-300" />
            {t("tools.sieve_filters.enabled")}
        </label>
        <div class="flex items-center gap-1">
            <button
                type="button"
                class="p-1.5 rounded-lg text-gray-500 hover:bg-gray-200 dark:hover:bg-zinc-800 disabled:opacity-40"
                title={t("tools.sieve_filters.move_up")}
                disabled={index === 0}
                onclick={() => onMove(index, -1)}
            >
                <MaterialDesignIcon iconName="chevron-up" />
            </button>
            <button
                type="button"
                class="p-1.5 rounded-lg text-gray-500 hover:bg-gray-200 dark:hover:bg-zinc-800 disabled:opacity-40"
                title={t("tools.sieve_filters.move_down")}
                disabled={index === totalRules - 1}
                onclick={() => onMove(index, 1)}
            >
                <MaterialDesignIcon iconName="chevron-down" />
            </button>
            <button
                type="button"
                class="p-1.5 rounded-lg text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40"
                title={t("tools.sieve_filters.remove_rule")}
                onclick={() => onRemove(index)}
            >
                <MaterialDesignIcon iconName="delete-outline" />
            </button>
        </div>
    </div>

    <div>
        <label
            class="block text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest mb-1"
            for="terms-{rule.id}"
        >
            {t("tools.sieve_filters.terms_label")}
        </label>
        <textarea
            id="terms-{rule.id}"
            value={formatTermsText(rule.terms)}
            rows={3}
            class="w-full px-3 py-2 rounded-lg border border-sem-border bg-sem-surface text-sm text-sem-fg font-mono"
            placeholder={t("tools.sieve_filters.terms_placeholder")}
            oninput={(e) => onTermsInput(e.currentTarget.value)}></textarea>
    </div>

    <div>
        <label
            class="block text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest mb-1"
            for="scope-{rule.id}"
        >
            {t("tools.sieve_filters.scope_label")}
        </label>
        <select
            id="scope-{rule.id}"
            bind:value={rule.scope}
            class="w-full px-3 py-2 rounded-lg border border-sem-border bg-sem-surface text-sm text-sem-fg"
        >
            <option value="everyone">
                {t("tools.sieve_filters.scope_everyone")}
            </option>
            <option value="contacts">
                {t("tools.sieve_filters.scope_contacts")}
            </option>
            <option value="non_contacts">
                {t("tools.sieve_filters.scope_non_contacts")}
            </option>
        </select>
    </div>

    <div class="space-y-2">
        <div class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest">
            {t("tools.sieve_filters.match_targets_label")}
        </div>
        <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
            <input
                bind:checked={rule.match_peer_fields}
                type="checkbox"
                class="rounded-sm border-gray-300"
                onchange={() => onMatchTargetsChange(rule)}
            />
            {t("tools.sieve_filters.match_peer_fields")}
        </label>
        <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
            <input
                bind:checked={rule.match_message}
                type="checkbox"
                class="rounded-sm border-gray-300"
                onchange={() => onMatchTargetsChange(rule)}
            />
            {t("tools.sieve_filters.match_message")}
        </label>
        <p class="text-xs text-sem-fg-muted">
            {t("tools.sieve_filters.match_targets_hint")}
        </p>
    </div>

    <div>
        <label
            class="block text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest mb-1"
            for="match-mode-{rule.id}"
        >
            {t("tools.sieve_filters.match_mode_label")}
        </label>
        <select
            id="match-mode-{rule.id}"
            bind:value={rule.match_mode}
            class="w-full px-3 py-2 rounded-lg border border-sem-border bg-sem-surface text-sm text-sem-fg"
        >
            <option value="substring">
                {t("tools.sieve_filters.match_mode_substring")}
            </option>
            <option value="regex">
                {t("tools.sieve_filters.match_mode_regex")}
            </option>
        </select>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
            <label
                class="block text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest mb-1"
                for="action-{rule.id}"
            >
                {t("tools.sieve_filters.action_label")}
            </label>
            <select
                id="action-{rule.id}"
                bind:value={rule.action}
                class="w-full px-3 py-2 rounded-lg border border-sem-border bg-sem-surface text-sm text-sem-fg"
                onchange={() => onActionChange(rule)}
            >
                <option value="hide">
                    {t("tools.sieve_filters.action_hide")}
                </option>
                <option value="ignore">
                    {t("tools.sieve_filters.action_ignore")}
                </option>
                <option value="folder">
                    {t("tools.sieve_filters.action_folder")}
                </option>
                <option value="banish">
                    {t("tools.sieve_filters.action_banish")}
                </option>
            </select>
        </div>
        {#if rule.action === "folder"}
            <div>
                <label
                    class="block text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest mb-1"
                    for="folder-{rule.id}"
                >
                    {t("tools.sieve_filters.folder_label")}
                </label>
                <select
                    id="folder-{rule.id}"
                    bind:value={rule.folder_id}
                    class="w-full px-3 py-2 rounded-lg border border-sem-border bg-sem-surface text-sm text-sem-fg"
                >
                    {#each folders as f (f.id)}
                        <option value={f.id}>
                            {f.name}
                        </option>
                    {/each}
                </select>
            </div>
        {/if}
    </div>
</div>
