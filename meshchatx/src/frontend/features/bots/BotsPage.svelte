<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ToastUtils from "../../js/ToastUtils.js";
    import DialogUtils from "../../js/DialogUtils.js";
    import DownloadUtils from "../../js/DownloadUtils.js";
    import GlobalEmitter from "../../js/GlobalEmitter.js";
    import { t } from "../../js/i18n.js";
    import {
        deleteBot,
        exportBotIdentity,
        fetchBotProcessLog,
        fetchBotsStatus,
        forceBotAnnounce,
        patchBotLxmfConfig,
        restartBot,
        startBot,
        stopBot,
        updateBotName,
    } from "./lib/botsApi.js";
    import type { BotRecord, BotTemplate, LxmfConfigPatch } from "./lib/types.js";
    import BotCard from "./components/BotCard.svelte";
    import BotStartModal from "./components/BotStartModal.svelte";
    import BotLxmfConfigModal from "./components/BotLxmfConfigModal.svelte";
    import BotProcessLogModal from "./components/BotProcessLogModal.svelte";

    let bots = $state<BotRecord[]>([]);
    let templates = $state<BotTemplate[]>([]);
    let loading = $state(true);
    let error = $state<string | null>(null);
    let actionInProgress = $state(false);
    let relativeTimerTick = $state(0);

    let selectedTemplate = $state<BotTemplate | null>(null);
    let startModalBusy = $state(false);

    let configModalBot = $state<BotRecord | null>(null);
    let configModalSaving = $state(false);

    let logModalBot = $state<BotRecord | null>(null);
    let logModalText = $state("");
    let logModalTruncated = $state(false);
    let logModalLoading = $state(false);

    let pollInterval: ReturnType<typeof setInterval> | null = null;
    let relativeTimerInterval: ReturnType<typeof setInterval> | null = null;

    async function loadStatus(silent = false): Promise<void> {
        if (!silent) {
            loading = true;
        }
        error = null;
        try {
            const data = await fetchBotsStatus();
            bots = data.bots;
            templates = data.templates;
        } catch (err: unknown) {
            const e = err as { message?: string };
            error = e?.message || t("common.error");
            if (!silent) {
                ToastUtils.error(error);
            }
        } finally {
            if (!silent) {
                loading = false;
            }
        }
    }

    function selectTemplate(template: BotTemplate): void {
        selectedTemplate = template;
    }

    function closeStartModal(): void {
        selectedTemplate = null;
        startModalBusy = false;
    }

    async function handleStartBot(templateId: string, name: string, lxmfConfig?: LxmfConfigPatch): Promise<void> {
        startModalBusy = true;
        try {
            await startBot({ template_id: templateId, name, lxmf_config: lxmfConfig });
            ToastUtils.success(t("bots.bot_started"));
            closeStartModal();
            await loadStatus(true);
        } catch (err: unknown) {
            const e = err as { response?: { data?: { message?: string } }; message?: string };
            ToastUtils.error(e?.response?.data?.message || e?.message || t("bots.failed_to_start"));
        } finally {
            startModalBusy = false;
        }
    }

    async function handleStopBot(bot: BotRecord): Promise<void> {
        actionInProgress = true;
        try {
            await stopBot(bot.id);
            ToastUtils.success(t("bots.bot_stopped"));
            await loadStatus(true);
        } catch (err: unknown) {
            const e = err as { response?: { data?: { message?: string } }; message?: string };
            ToastUtils.error(e?.response?.data?.message || e?.message || t("bots.failed_to_stop"));
        } finally {
            actionInProgress = false;
        }
    }

    async function handleRestartBot(bot: BotRecord): Promise<void> {
        actionInProgress = true;
        try {
            await restartBot(bot.id);
            ToastUtils.success(t("bots.bot_ready"));
            await loadStatus(true);
        } catch (err: unknown) {
            const e = err as { response?: { data?: { message?: string } }; message?: string };
            ToastUtils.error(e?.response?.data?.message || e?.message || t("bots.failed_to_start"));
        } finally {
            actionInProgress = false;
        }
    }

    async function handleDeleteBot(bot: BotRecord): Promise<void> {
        const confirmed = await DialogUtils.confirm(t("common.delete_confirm"));
        if (!confirmed) {
            return;
        }
        actionInProgress = true;
        try {
            await deleteBot(bot.id);
            ToastUtils.success(t("bots.bot_deleted"));
            await loadStatus(true);
        } catch (err: unknown) {
            const e = err as { response?: { data?: { message?: string } }; message?: string };
            ToastUtils.error(e?.response?.data?.message || e?.message || t("bots.failed_to_delete"));
        } finally {
            actionInProgress = false;
        }
    }

    function handleChatWithBot(bot: BotRecord): void {
        const h = bot.lxmf_address || bot.full_address || bot.address;
        if (!h) {
            return;
        }
        window.location.hash = `#/messages/${h.trim()}`;
    }

    async function handleForceAnnounce(bot: BotRecord): Promise<void> {
        actionInProgress = true;
        try {
            await forceBotAnnounce(bot.id);
            ToastUtils.success(t("bots.announce_triggered"));
            await loadStatus(true);
        } catch (err: unknown) {
            const e = err as { response?: { data?: { message?: string } }; message?: string };
            ToastUtils.error(e?.response?.data?.message || e?.message || t("bots.announce_failed"));
        } finally {
            actionInProgress = false;
        }
    }

    async function handleViewLog(bot: BotRecord): Promise<void> {
        logModalBot = bot;
        logModalText = "";
        logModalTruncated = false;
        logModalLoading = true;
        try {
            const data = await fetchBotProcessLog(bot.id);
            logModalText = data.log;
            logModalTruncated = data.truncated;
        } catch (err: unknown) {
            const e = err as { response?: { data?: { message?: string } }; message?: string };
            ToastUtils.error(e?.response?.data?.message || e?.message || t("bots.process_log_failed"));
        } finally {
            logModalLoading = false;
        }
    }

    function handleOpenConfig(bot: BotRecord): void {
        configModalBot = bot;
    }

    async function handleSaveConfig(botId: string, patch: LxmfConfigPatch): Promise<void> {
        configModalSaving = true;
        try {
            await patchBotLxmfConfig(botId, patch);
            ToastUtils.success(t("bots.lxmf_config_saved"));
            configModalBot = null;
            await loadStatus(true);
        } catch (err: unknown) {
            const e = err as { response?: { data?: { message?: string } }; message?: string };
            ToastUtils.error(e?.response?.data?.message || e?.message || t("bots.lxmf_config_failed"));
        } finally {
            configModalSaving = false;
        }
    }

    async function handleExportIdentity(bot: BotRecord): Promise<void> {
        try {
            const response = await exportBotIdentity(bot.id);
            await DownloadUtils.downloadFromApiResponse(response, `bot_${bot.id}_identity`);
            ToastUtils.success(t("common.copied"));
        } catch (err: unknown) {
            const e = err as { response?: { data?: { message?: string } }; message?: string };
            ToastUtils.error(e?.response?.data?.message || e?.message || t("bots.export_failed"));
        }
    }

    async function handleEditName(bot: BotRecord): Promise<void> {
        const next = await DialogUtils.prompt(t("bots.edit_name"), bot.name);
        if (next === null || next === undefined || !next.trim() || next.trim() === bot.name) {
            return;
        }
        actionInProgress = true;
        try {
            await updateBotName(bot.id, next.trim());
            ToastUtils.success(t("bots.bot_renamed"));
            await loadStatus(true);
        } catch (err: unknown) {
            const e = err as { response?: { data?: { message?: string } }; message?: string };
            ToastUtils.error(e?.response?.data?.message || e?.message || t("bots.rename_failed"));
        } finally {
            actionInProgress = false;
        }
    }

    onMount(() => {
        void loadStatus();
        pollInterval = setInterval(() => {
            void loadStatus(true);
        }, 10000);
        relativeTimerInterval = setInterval(() => {
            relativeTimerTick = Date.now();
        }, 10000);
        GlobalEmitter.on("websocket-reconnected", () => {
            void loadStatus(true);
        });
    });

    onDestroy(() => {
        if (pollInterval) {
            clearInterval(pollInterval);
        }
        if (relativeTimerInterval) {
            clearInterval(relativeTimerInterval);
        }
        GlobalEmitter.off("websocket-reconnected", () => {
            void loadStatus(true);
        });
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
    <ToolsPageHeader
        icon="robot"
        title={t("tools.bots.title")}
        description={t("tools.bots.description")}
        accent="blue"
    />
    <div
        class="flex-1 overflow-y-auto w-full px-3 sm:px-4 md:px-5 lg:px-8 py-4 sm:py-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]"
    >
        <div class="space-y-8 w-full max-w-4xl mx-auto">
            <div class="space-y-6">
                <div class="space-y-4">
                    <h3 class="text-lg font-semibold text-sem-fg">
                        {t("bots.create_new_bot")}
                    </h3>
                    {#if loading}
                        <div class="text-sm text-sem-fg-muted">{t("common.loading")}</div>
                    {:else if templates.length === 0}
                        <div class="text-sm text-sem-fg-muted">{t("bots.more_bots_coming")}</div>
                    {:else}
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                            {#each templates as template (template.id)}
                                <!-- svelte-ignore a11y_click_events_have_key_events -->
                                <!-- svelte-ignore a11y_no_static_element_interactions -->
                                <div
                                    class="relative rounded-lg border border-sem-border bg-sem-surface p-4 hover:border-blue-400 dark:hover:border-blue-600 transition cursor-pointer flex flex-col justify-between min-h-[140px] pr-12"
                                    onclick={() => selectTemplate(template)}
                                >
                                    <div class="min-w-0">
                                        <div class="font-bold text-sem-fg">{template.name}</div>
                                        <div class="text-sm text-gray-600 dark:text-gray-400 mt-1">
                                            {template.description}
                                        </div>
                                    </div>
                                    <div
                                        class="absolute bottom-3 right-3 p-2 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors pointer-events-none"
                                    >
                                        <MaterialDesignIcon iconName="chevron-right" class="size-6" />
                                    </div>
                                </div>
                            {/each}
                        </div>
                    {/if}
                </div>

                <div class="space-y-4">
                    <h3 class="text-lg font-semibold text-sem-fg">
                        {t("bots.saved_bots")}
                    </h3>
                    {#if loading}
                        <div class="text-sm text-sem-fg-muted">{t("common.loading")}</div>
                    {:else if bots.length === 0}
                        <div class="text-sm text-sem-fg-muted">{t("bots.no_bots_running")}</div>
                    {:else}
                        <div class="grid grid-cols-1 gap-4">
                            {#each bots as bot (bot.id)}
                                <BotCard
                                    {bot}
                                    {actionInProgress}
                                    {relativeTimerTick}
                                    onStart={() => handleStartBot(bot.template_id || "", bot.name || "")}
                                    onStop={handleStopBot}
                                    onRestart={handleRestartBot}
                                    onDelete={handleDeleteBot}
                                    onChat={handleChatWithBot}
                                    onAnnounce={handleForceAnnounce}
                                    onViewLog={handleViewLog}
                                    onConfig={handleOpenConfig}
                                    onExport={handleExportIdentity}
                                    onEditName={handleEditName}
                                />
                            {/each}
                        </div>
                    {/if}
                </div>
            </div>
        </div>
    </div>

    <BotStartModal
        open={Boolean(selectedTemplate)}
        template={selectedTemplate}
        busy={startModalBusy}
        onClose={closeStartModal}
        onStart={handleStartBot}
    />

    <BotLxmfConfigModal
        open={Boolean(configModalBot)}
        bot={configModalBot}
        saving={configModalSaving}
        onClose={() => (configModalBot = null)}
        onSave={handleSaveConfig}
    />

    {#if logModalBot}
        <BotProcessLogModal
            bot={logModalBot}
            logText={logModalText}
            truncated={logModalTruncated}
            loading={logModalLoading}
            onClose={() => (logModalBot = null)}
        />
    {/if}
</div>
