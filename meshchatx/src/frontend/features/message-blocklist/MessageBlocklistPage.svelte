<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import DialogUtils from "../../js/DialogUtils.js";
    import DownloadUtils from "../../js/DownloadUtils.js";
    import ToastUtils from "../../js/ToastUtils.js";
    import { t } from "../../js/i18n.js";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import {
        createDefaultBlocklistConfig,
        createNewBlocklistEntry,
        mapBlocklistFromApi,
        normalizeBlocklistForSave,
    } from "./lib/blocklistRules.js";
    import {
        API_MESSAGE_BLOCKLIST,
        API_MESSAGE_BLOCKLIST_EXPORT,
        API_MESSAGE_BLOCKLIST_IMPORT,
        JSON_INDENT_SPACES,
        MESSAGE_BLOCKLIST_EXPORT_FILENAME,
    } from "./lib/constants.js";
    import type { BlocklistConfig } from "./lib/types.js";

    let enabled = $state(false);
    let blocklist: BlocklistConfig = $state(createDefaultBlocklistConfig());
    let isSaving = $state(false);
    let importFileInput = $state<HTMLInputElement>();

    function addEntry(): void {
        blocklist.entries.push(createNewBlocklistEntry());
    }

    function removeEntry(index: number): void {
        blocklist.entries.splice(index, 1);
    }

    async function reload(): Promise<void> {
        try {
            const res = await window.api.get(API_MESSAGE_BLOCKLIST);
            const data = res.data as { enabled?: boolean; blocklist?: Record<string, unknown> } | undefined;
            enabled = Boolean(data?.enabled);
            blocklist = mapBlocklistFromApi(data?.blocklist || {});
        } catch (e) {
            console.error(e);
            ToastUtils.error(t("tools.message_blocklist.load_failed"));
        }
    }

    async function save(): Promise<void> {
        isSaving = true;
        try {
            const payload = {
                enabled,
                blocklist: normalizeBlocklistForSave(blocklist),
            };
            const res = await window.api.put(API_MESSAGE_BLOCKLIST, payload);
            const data = res.data as { enabled?: boolean; blocklist?: Record<string, unknown> } | undefined;
            enabled = Boolean(data?.enabled);
            blocklist = mapBlocklistFromApi(data?.blocklist || {});
            ToastUtils.success(t("tools.message_blocklist.saved"));
        } catch (e: any) {
            const msg =
                e?.response?.data?.message ||
                e?.message ||
                t("tools.message_blocklist.save_failed");
            ToastUtils.error(msg);
        } finally {
            isSaving = false;
        }
    }

    async function onEnabledChange(): Promise<void> {
        try {
            await window.api.put(API_MESSAGE_BLOCKLIST, {
                enabled,
                blocklist: normalizeBlocklistForSave(blocklist),
            });
            ToastUtils.success(
                enabled
                    ? t("tools.message_blocklist.enabled_toast")
                    : t("tools.message_blocklist.disabled_toast")
            );
        } catch {
            enabled = !enabled;
            ToastUtils.error(t("tools.message_blocklist.save_failed"));
        }
    }

    async function exportList(): Promise<void> {
        try {
            const res = await window.api.get(API_MESSAGE_BLOCKLIST_EXPORT);
            const blob = new Blob([JSON.stringify(res.data, null, JSON_INDENT_SPACES)], {
                type: "application/json",
            });
            await DownloadUtils.downloadFile(MESSAGE_BLOCKLIST_EXPORT_FILENAME, blob);
            ToastUtils.success(t("tools.message_blocklist.exported"));
        } catch (e) {
            console.error(e);
            ToastUtils.error(t("tools.message_blocklist.export_failed"));
        }
    }

    function triggerImport(): void {
        importFileInput?.click();
    }

    async function onImportFile(event: Event): Promise<void> {
        const input = event.target as HTMLInputElement;
        const file = input.files && input.files[0];
        input.value = "";
        if (!file) {
            return;
        }
        const merge = await DialogUtils.confirm(t("tools.message_blocklist.import_merge_confirm"));
        try {
            const text = await file.text();
            const document = JSON.parse(text);
            const res = await window.api.post(API_MESSAGE_BLOCKLIST_IMPORT, {
                document,
                merge,
            });
            const data = res.data as { blocklist?: Record<string, unknown> } | undefined;
            blocklist = mapBlocklistFromApi(data?.blocklist || {});
            ToastUtils.success(
                merge
                    ? t("tools.message_blocklist.imported_merge")
                    : t("tools.message_blocklist.imported_replace")
            );
        } catch (e: any) {
            const msg =
                e?.response?.data?.message ||
                e?.message ||
                t("tools.message_blocklist.import_failed");
            ToastUtils.error(msg);
        }
    }

    onMount(async () => {
        await reload();
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas" data-testid="message-blocklist-page">
    <ToolsPageHeader
        icon="shield-alert"
        title={t("tools.message_blocklist.title")}
        description={t("tools.message_blocklist.description")}
        accent="rose"
    />
    <div class="flex-1 overflow-y-auto w-full pb-[max(1rem,env(safe-area-inset-bottom))]">
        <div class="p-3 sm:p-4 md:p-6 max-w-4xl mx-auto w-full space-y-4 min-w-0">
            <div
                class="rounded-xl border border-amber-200 dark:border-amber-900/50 bg-amber-50 dark:bg-amber-950/30 px-4 py-3 flex items-start gap-3"
            >
                <MaterialDesignIcon
                    iconName="alert-circle-outline"
                    class="size-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5"
                />
                <div class="min-w-0">
                    <div class="text-sm font-semibold text-amber-900 dark:text-amber-200">
                        {t("tools.message_blocklist.beta_notice_title")}
                    </div>
                    <p class="text-xs text-amber-800/90 dark:text-amber-300/90 mt-1 leading-relaxed">
                        {t("tools.message_blocklist.beta_notice_body")}
                    </p>
                </div>
            </div>

            <div class="rounded-xl border border-sem-border bg-sem-surface p-4 space-y-4">
                <label class="inline-flex items-center gap-3 cursor-pointer">
                    <input
                        bind:checked={enabled}
                        type="checkbox"
                        class="rounded-sm border-gray-300 size-4"
                        onchange={onEnabledChange}
                    />
                    <span class="text-sm font-medium text-sem-fg">
                        {t("tools.message_blocklist.enable_label")}
                    </span>
                </label>
                <p class="text-xs text-sem-fg-muted">
                    {t("tools.message_blocklist.enable_hint")}
                </p>
            </div>

            <div
                class="rounded-xl border border-sem-border bg-sem-surface p-4 space-y-4 {enabled ? '' : 'opacity-60'}"
            >
                <div class="flex flex-wrap items-center justify-between gap-2">
                    <h2 class="text-base font-semibold text-sem-fg">
                        {t("tools.message_blocklist.entries_heading")}
                    </h2>
                    <div class="flex flex-wrap items-center gap-2">
                        <button
                            type="button"
                            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border border-sem-border text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-zinc-900 transition-colors"
                            onclick={exportList}
                        >
                            <MaterialDesignIcon iconName="export" class="size-4" />
                            {t("tools.message_blocklist.export")}
                        </button>
                        <button
                            type="button"
                            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border border-sem-border text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-zinc-900 transition-colors"
                            onclick={triggerImport}
                        >
                            <MaterialDesignIcon iconName="import" class="size-4" />
                            {t("tools.message_blocklist.import")}
                        </button>
                        <input
                            bind:this={importFileInput}
                            type="file"
                            accept=".json,application/json"
                            class="hidden"
                            onchange={onImportFile}
                        />
                        <button
                            type="button"
                            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-rose-600 text-white hover:bg-rose-700 transition-colors"
                            onclick={addEntry}
                        >
                            <MaterialDesignIcon iconName="plus" class="size-4" />
                            {t("tools.message_blocklist.add_entry")}
                        </button>
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                        <label
                            class="block text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest mb-1"
                            for="blocklist-scope"
                        >
                            {t("tools.message_blocklist.scope_label")}
                        </label>
                        <select
                            id="blocklist-scope"
                            bind:value={blocklist.scope}
                            class="w-full px-3 py-2 rounded-lg border border-sem-border bg-sem-surface text-sm text-sem-fg"
                        >
                            <option value="everyone">
                                {t("tools.message_blocklist.scope_everyone")}
                            </option>
                            <option value="contacts">
                                {t("tools.message_blocklist.scope_contacts")}
                            </option>
                            <option value="non_contacts">
                                {t("tools.message_blocklist.scope_non_contacts")}
                            </option>
                        </select>
                    </div>
                    <div class="space-y-2">
                        <div class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest">
                            {t("tools.message_blocklist.match_in_label")}
                        </div>
                        <label class="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
                            <input
                                bind:checked={blocklist.match_message}
                                type="checkbox"
                                class="rounded-sm border-gray-300"
                            />
                            {t("tools.message_blocklist.match_message")}
                        </label>
                        <label class="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
                            <input
                                bind:checked={blocklist.match_peer_fields}
                                type="checkbox"
                                class="rounded-sm border-gray-300"
                            />
                            {t("tools.message_blocklist.match_peer_fields")}
                        </label>
                    </div>
                </div>

                {#if blocklist.entries.length === 0}
                    <div class="text-sm text-sem-fg-muted py-6 text-center">
                        {t("tools.message_blocklist.empty_entries")}
                    </div>
                {:else}
                    <div class="space-y-3">
                        {#each blocklist.entries as entry, index (entry.id)}
                            <div
                                class="rounded-lg border border-sem-border p-3 space-y-3 bg-gray-50/80 dark:bg-zinc-900/40"
                            >
                                <div class="flex flex-wrap items-center justify-between gap-2">
                                    <label class="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
                                        <input
                                            bind:checked={entry.enabled}
                                            type="checkbox"
                                            class="rounded-sm border-gray-300"
                                        />
                                        {t("tools.message_blocklist.entry_enabled")}
                                    </label>
                                    <div class="flex items-center gap-1">
                                        <button
                                            type="button"
                                            class="p-1.5 rounded-lg text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40"
                                            title={t("tools.message_blocklist.remove_entry")}
                                            onclick={() => removeEntry(index)}
                                        >
                                            <MaterialDesignIcon iconName="delete-outline" class="size-5" />
                                        </button>
                                    </div>
                                </div>
                                <div class="grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-2">
                                    <input
                                        bind:value={entry.text}
                                        type="text"
                                        class="w-full px-3 py-2 rounded-lg border border-sem-border bg-sem-surface text-sm text-sem-fg font-mono"
                                        placeholder={t("tools.message_blocklist.entry_placeholder")}
                                    />
                                    <select
                                        bind:value={entry.match_mode}
                                        class="px-3 py-2 rounded-lg border border-sem-border bg-sem-surface text-sm text-sem-fg"
                                    >
                                        <option value="substring">
                                            {t("tools.message_blocklist.match_mode_substring")}
                                        </option>
                                        <option value="regex">
                                            {t("tools.message_blocklist.match_mode_regex")}
                                        </option>
                                    </select>
                                </div>
                            </div>
                        {/each}
                    </div>
                {/if}

                <div class="flex flex-wrap items-center gap-2 pt-2">
                    <button
                        type="button"
                        class="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-rose-600 text-white hover:bg-rose-700 disabled:opacity-50 transition-colors"
                        disabled={isSaving}
                        onclick={save}
                    >
                        <MaterialDesignIcon iconName="content-save-outline" class="size-4" />
                        {#if isSaving}
                            <span>{t("tools.message_blocklist.saving")}</span>
                        {:else}
                            <span>{t("tools.message_blocklist.save")}</span>
                        {/if}
                    </button>
                    <button
                        type="button"
                        class="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border border-sem-border text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-zinc-900 transition-colors"
                        onclick={reload}
                    >
                        <MaterialDesignIcon iconName="refresh" class="size-4" />
                        {t("tools.message_blocklist.revert")}
                    </button>
                </div>
            </div>
        </div>
    </div>
</div>
