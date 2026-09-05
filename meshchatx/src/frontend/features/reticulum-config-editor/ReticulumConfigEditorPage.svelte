<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import ToastUtils from "../../js/ToastUtils.js";
    import DialogUtils from "../../js/DialogUtils.js";
    import GlobalState from "../../js/GlobalState.js";
    import { t } from "../../js/i18n.js";
    import {
        RETICULUM_CONFIG_RAW_ENDPOINT,
        RETICULUM_CONFIG_RESET_ENDPOINT,
        RETICULUM_RELOAD_ENDPOINT,
        TOAST_ID_CONFIG_SAVE,
        TOAST_ID_CONFIG_RESTORE,
        TOAST_ID_CONFIG_RELOAD,
    } from "./lib/constants.js";
    import {
        insertTabAtSelection,
        isConfigDirty,
        shouldShowRestartReminder,
        extractErrorMessage,
    } from "./lib/configFormat.js";
    import type {
        ReticulumConfigRawResponse,
        ReticulumConfigResetResponse,
        ReticulumReloadResponse,
    } from "./lib/types.js";

    let content = $state("");
    let originalContent = $state("");
    let configPath = $state("");
    let loading = $state(false);
    let saving = $state(false);
    let resetting = $state(false);
    let reloadingRns = $state(false);
    let hasSavedChanges = $state(false);

    const isDirty = $derived(isConfigDirty(content, originalContent));
    const showRestartReminder = $derived(
        shouldShowRestartReminder(hasSavedChanges, Boolean(GlobalState.hasPendingInterfaceChanges))
    );

    async function loadConfig(): Promise<void> {
        if (loading) return;
        try {
            loading = true;
            const response = await window.api.get(RETICULUM_CONFIG_RAW_ENDPOINT);
            const data = (response.data || {}) as ReticulumConfigRawResponse;
            content = data.content || "";
            originalContent = content;
            configPath = data.path || "";
        } catch (e) {
            ToastUtils.error(extractErrorMessage(e, t("tools.reticulum_config_editor.failed_load")));
        } finally {
            loading = false;
        }
    }

    async function saveConfig(): Promise<void> {
        if (saving || !isDirty) return;
        try {
            saving = true;
            ToastUtils.loading(t("tools.reticulum_config_editor.saving"), 0, TOAST_ID_CONFIG_SAVE);
            const response = await window.api.put(RETICULUM_CONFIG_RAW_ENDPOINT, {
                content,
            });
            const data = (response.data || {}) as ReticulumConfigRawResponse;
            originalContent = content;
            configPath = data.path || configPath;
            hasSavedChanges = true;
            GlobalState.hasPendingInterfaceChanges = true;
            ToastUtils.success(data.message || t("tools.reticulum_config_editor.saved"));
        } catch (e) {
            ToastUtils.error(extractErrorMessage(e, t("tools.reticulum_config_editor.failed_save")));
        } finally {
            ToastUtils.dismiss(TOAST_ID_CONFIG_SAVE);
            saving = false;
        }
    }

    async function restoreDefaults(): Promise<void> {
        if (resetting) return;
        const confirmed = await DialogUtils.confirm(t("tools.reticulum_config_editor.confirm_restore"));
        if (!confirmed) return;
        try {
            resetting = true;
            ToastUtils.loading(t("tools.reticulum_config_editor.restoring"), 0, TOAST_ID_CONFIG_RESTORE);
            const response = await window.api.post(RETICULUM_CONFIG_RESET_ENDPOINT);
            const data = (response.data || {}) as ReticulumConfigResetResponse;
            content = data.content || "";
            originalContent = content;
            configPath = data.path || configPath;
            hasSavedChanges = true;
            GlobalState.hasPendingInterfaceChanges = true;
            ToastUtils.success(data.message || t("tools.reticulum_config_editor.restored"));
        } catch (e) {
            ToastUtils.error(extractErrorMessage(e, t("tools.reticulum_config_editor.failed_restore")));
        } finally {
            ToastUtils.dismiss(TOAST_ID_CONFIG_RESTORE);
            resetting = false;
        }
    }

    function discardChanges(): void {
        if (!isDirty) return;
        content = originalContent;
    }

    async function reloadRns(): Promise<void> {
        if (reloadingRns) return;
        try {
            reloadingRns = true;
            ToastUtils.loading(t("app.reloading_rns"), 0, TOAST_ID_CONFIG_RELOAD);
            const response = await window.api.post(RETICULUM_RELOAD_ENDPOINT);
            const data = (response.data || {}) as ReticulumReloadResponse;
            ToastUtils.success(data.message || t("tools.reticulum_config_editor.restart_done"));
            hasSavedChanges = false;
            GlobalState.hasPendingInterfaceChanges = false;
            if (GlobalState.modifiedInterfaceNames?.clear) {
                GlobalState.modifiedInterfaceNames.clear();
            }
            await loadConfig();
        } catch (e) {
            ToastUtils.error(extractErrorMessage(e, t("tools.reticulum_config_editor.failed_restart")));
        } finally {
            ToastUtils.dismiss(TOAST_ID_CONFIG_RELOAD);
            reloadingRns = false;
        }
    }

    function handleKeyDown(event: KeyboardEvent): void {
        if (event.key === "Tab") {
            event.preventDefault();
            const target = event.target as HTMLTextAreaElement | null;
            if (!target) return;
            const start = target.selectionStart ?? 0;
            const end = target.selectionEnd ?? 0;
            const result = insertTabAtSelection(content, start, end);
            content = result.content;
            queueMicrotask(() => {
                target.selectionStart = target.selectionEnd = result.newCursor;
            });
        }
    }

    onMount(() => {
        void loadConfig();
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas" data-testid="reticulum-config-editor-page">
    <ToolsPageHeader
        icon="file-cog"
        title={t("tools.reticulum_config_editor.title")}
        description={t("tools.reticulum_config_editor.description")}
        accent="blue"
    >
        <button
            type="button"
            class="secondary-chip py-1! px-3!"
            disabled={loading}
            onclick={loadConfig}
        >
            <MaterialDesignIcon iconName="refresh" class="w-3.5 h-3.5" />
            <span class="hidden sm:inline">{t("tools.reticulum_config_editor.reload")}</span>
        </button>
        <button
            type="button"
            class="secondary-chip py-1! px-3! text-red-500! hover:bg-red-50! dark:hover:bg-red-900/20!"
            disabled={loading || resetting}
            onclick={restoreDefaults}
        >
            <MaterialDesignIcon iconName="restore" class="w-3.5 h-3.5" />
            <span class="hidden sm:inline">{t("tools.reticulum_config_editor.restore_defaults")}</span>
        </button>
        <button
            type="button"
            class="secondary-chip py-1! px-3!"
            disabled={!isDirty || saving}
            onclick={discardChanges}
        >
            <MaterialDesignIcon iconName="undo" class="w-3.5 h-3.5" />
            <span class="hidden sm:inline">{t("tools.reticulum_config_editor.discard")}</span>
        </button>
        <button
            type="button"
            class="primary-chip py-1! px-3!"
            disabled={!isDirty || saving}
            onclick={saveConfig}
        >
            <MaterialDesignIcon iconName="content-save" class="w-3.5 h-3.5" />
            <span class="hidden sm:inline">
                {saving ? t("tools.reticulum_config_editor.saving") : t("tools.reticulum_config_editor.save")}
            </span>
        </button>
    </ToolsPageHeader>

    <div
        class="flex-1 min-h-0 overflow-hidden w-full px-3 sm:px-5 py-4 pb-[max(1rem,env(safe-area-inset-bottom))] flex flex-col"
    >
        <div class="space-y-4 w-full min-w-0 max-w-6xl mx-auto flex-1 min-h-0 flex flex-col">
            {#if configPath}
                <p class="text-xs text-sem-fg-muted font-mono truncate shrink-0" title={configPath}>
                    {configPath}
                </p>
            {/if}
            {#if showRestartReminder}
                <div
                    class="bg-amber-600 text-white border border-amber-500/30 p-4 sm:rounded-xl flex flex-wrap gap-3 items-center shrink-0"
                >
                    <div class="flex items-center gap-3">
                        <MaterialDesignIcon iconName="alert" class="w-6 h-6" />
                        <div>
                            <div class="text-lg font-semibold">
                                {t("tools.reticulum_config_editor.restart_required")}
                            </div>
                            <div class="text-sm">
                                {t("tools.reticulum_config_editor.restart_description")}
                            </div>
                        </div>
                    </div>
                    <button
                        type="button"
                        class="ml-auto inline-flex items-center gap-2 rounded-full bg-white px-4 py-1.5 text-sm font-bold text-amber-600 hover:bg-white/90 transition shadow-xs disabled:opacity-50 {reloadingRns ? '' : 'animate-pulse motion-reduce:animate-none'}"
                        disabled={reloadingRns}
                        onclick={reloadRns}
                    >
                        <MaterialDesignIcon iconName="restart" class="w-4 h-4" />
                        {reloadingRns ? t("app.reloading_rns") : t("tools.reticulum_config_editor.restart_now")}
                    </button>
                </div>
            {/if}

            <div
                class="rounded-xl border border-sem-border bg-sem-surface overflow-hidden flex-1 min-h-0 flex flex-col"
            >
                <div
                    class="flex flex-wrap items-center justify-between gap-2 px-3 py-2 border-b border-sem-border bg-sem-surface-muted/60 text-xs text-sem-fg-muted shrink-0"
                >
                    <span class="flex items-center gap-1.5">
                        <MaterialDesignIcon iconName="information-outline" class="w-3.5 h-3.5" />
                        {t("tools.reticulum_config_editor.info")}
                    </span>
                    {#if isDirty}
                        <span class="text-amber-600 dark:text-amber-400 font-semibold">
                            {t("tools.reticulum_config_editor.unsaved")}
                        </span>
                    {/if}
                </div>
                <div class="relative flex-1 min-h-[12rem]">
                    <textarea
                        bind:value={content}
                        spellcheck="false"
                        autocapitalize="off"
                        autocomplete="off"
                        placeholder={loading ? t("tools.reticulum_config_editor.loading") : ""}
                        class="absolute inset-0 w-full h-full bg-sem-surface text-sem-fg p-4 font-mono text-xs sm:text-sm resize-none focus:outline-hidden"
                        onkeydown={handleKeyDown}
                    ></textarea>
                </div>
            </div>
        </div>
    </div>
</div>
