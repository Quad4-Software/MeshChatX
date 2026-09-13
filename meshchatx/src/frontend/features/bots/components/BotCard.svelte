<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import ToastUtils from "../../../js/ToastUtils.js";
    import { t } from "../../../js/i18n.js";
    import { botLastError, formatRelativeSince, lxmfAddressFor } from "../lib/botUtils.js";
    import type { BotRecord } from "../lib/types.js";

    interface Props {
        bot: BotRecord;
        actionInProgress?: boolean;
        relativeTimerTick?: number;
        onStart: (bot: BotRecord) => void;
        onStop: (bot: BotRecord) => void;
        onRestart: (bot: BotRecord) => void;
        onDelete: (bot: BotRecord) => void;
        onChat: (bot: BotRecord) => void;
        onAnnounce: (bot: BotRecord) => void;
        onViewLog: (bot: BotRecord) => void;
        onConfig: (bot: BotRecord) => void;
        onExport: (bot: BotRecord) => void;
        onEditName: (bot: BotRecord) => void;
    }

    let {
        bot,
        actionInProgress = false,
        relativeTimerTick = 0,
        onStart,
        onStop,
        onRestart,
        onDelete,
        onChat,
        onAnnounce,
        onViewLog,
        onConfig,
        onExport,
        onEditName,
    }: Props = $props();

    const address = $derived(lxmfAddressFor(bot));
    const lastError = $derived(botLastError(bot));

    async function copyAddress(): Promise<void> {
        if (!address) {
            return;
        }
        try {
            await navigator.clipboard.writeText(address);
            ToastUtils.success(t("translator.copied_to_clipboard"));
        } catch {
            ToastUtils.error(t("common.failed_to_copy"));
        }
    }
</script>

<div class="relative rounded-lg border border-sem-border bg-sem-surface p-3 sm:p-4 pr-10 sm:pr-12">
    <div
        class="absolute top-2 right-2 flex flex-wrap items-center justify-end gap-0.5 z-10 max-w-[min(100%,calc(100%-2rem))]"
    >
        {#if address}
            <button
                type="button"
                class="p-2 rounded-lg text-sem-fg-muted hover:text-blue-600 dark:hover:text-blue-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors cursor-pointer"
                title={t("bots.chat_with_bot")}
                onclick={() => onChat(bot)}
            >
                <MaterialDesignIcon iconName="message-text" class="size-5" />
            </button>
        {/if}
        {#if bot.running}
            <button
                type="button"
                class="p-2 rounded-lg text-sem-fg-muted hover:text-amber-600 dark:hover:text-amber-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors cursor-pointer"
                title={t("bots.force_announce")}
                disabled={actionInProgress}
                onclick={() => onAnnounce(bot)}
            >
                <MaterialDesignIcon iconName="bullhorn" class="size-5" />
            </button>
            <button
                type="button"
                class="p-2 rounded-lg text-sem-fg-muted hover:text-blue-600 dark:hover:text-blue-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors cursor-pointer"
                title={t("bots.restart_bot")}
                disabled={actionInProgress}
                onclick={() => onRestart(bot)}
            >
                <MaterialDesignIcon iconName="refresh" class="size-5" />
            </button>
            <button
                type="button"
                class="p-2 rounded-lg text-sem-fg-muted hover:text-red-600 dark:hover:text-red-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors cursor-pointer"
                title={t("bots.stop_bot")}
                disabled={actionInProgress}
                onclick={() => onStop(bot)}
            >
                <MaterialDesignIcon iconName="stop" class="size-5" />
            </button>
        {:else}
            <button
                type="button"
                class="p-2 rounded-lg text-sem-fg-muted hover:text-emerald-600 dark:hover:text-emerald-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors cursor-pointer"
                title={t("bots.start_bot")}
                disabled={actionInProgress}
                onclick={() => onStart(bot)}
            >
                <MaterialDesignIcon iconName="play" class="size-5" />
            </button>
        {/if}
        <button
            type="button"
            class="p-2 rounded-lg text-sem-fg-muted hover:text-violet-600 dark:hover:text-violet-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors cursor-pointer"
            title={t("bots.view_process_log")}
            onclick={() => onViewLog(bot)}
        >
            <MaterialDesignIcon iconName="bug-outline" class="size-5" />
        </button>
        <button
            type="button"
            class="p-2 rounded-lg text-sem-fg-muted hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors cursor-pointer"
            title={t("bots.edit_lxmf_config")}
            onclick={() => onConfig(bot)}
        >
            <MaterialDesignIcon iconName="cog" class="size-5" />
        </button>
        <button
            type="button"
            class="p-2 rounded-lg text-sem-fg-muted hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors cursor-pointer"
            title={t("bots.export_identity")}
            onclick={() => onExport(bot)}
        >
            <MaterialDesignIcon iconName="export" class="size-5" />
        </button>
        <button
            type="button"
            class="p-2 rounded-lg text-sem-fg-muted hover:text-red-600 dark:hover:text-red-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors cursor-pointer"
            title={t("bots.delete_bot")}
            disabled={actionInProgress}
            onclick={() => onDelete(bot)}
        >
            <MaterialDesignIcon iconName="delete" class="size-5" />
        </button>
    </div>

    <div class="flex items-start gap-3 min-w-0">
        <div class="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg shrink-0">
            <MaterialDesignIcon iconName="robot" class="size-6 text-sem-accent" />
        </div>
        <div class="min-w-0 flex-1 space-y-1.5 sm:pr-2">
            <div class="flex items-center gap-1 min-w-0">
                <span class="font-bold text-sem-fg truncate">{bot.name}</span>
                <button
                    type="button"
                    class="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 shrink-0 cursor-pointer"
                    title={t("bots.edit_name")}
                    onclick={() => onEditName(bot)}
                >
                    <MaterialDesignIcon iconName="pencil" class="size-4" />
                </button>
            </div>
            <div class="flex items-center gap-2 text-[11px] text-sem-fg-muted">
                <span
                    class="inline-block size-2 rounded-full shrink-0 {bot.running
                        ? 'bg-emerald-500'
                        : 'bg-gray-400 dark:bg-gray-500'}"
                ></span>
                <span>
                    {bot.running ? t("bots.status_running") : t("bots.status_stopped")}
                </span>
            </div>
            <dl class="space-y-2.5 text-[11px] text-sem-fg-muted min-w-0">
                <div class="min-w-0">
                    <dt class="text-[10px] font-semibold uppercase tracking-wide text-sem-fg-muted mb-1">
                        {t("bots.lxmf_address")}
                    </dt>
                    <dd class="m-0 min-w-0">
                        {#if address}
                            <button
                                type="button"
                                class="font-mono text-[11px] break-all text-left w-full max-w-full text-gray-800 dark:text-gray-200 hover:underline leading-snug cursor-pointer"
                                onclick={copyAddress}
                            >
                                {address}
                            </button>
                        {:else}
                            <span class="text-sem-fg-muted">{t("bots.address_pending")}</span>
                        {/if}
                    </dd>
                </div>
                <div class="min-w-0">
                    <dt class="text-[10px] font-semibold uppercase tracking-wide text-sem-fg-muted mb-1">
                        {t("bots.last_announce")}
                    </dt>
                    <dd class="m-0 text-gray-700 dark:text-gray-200 leading-snug">
                        {#if bot.last_announce_at}
                            <span>{formatRelativeSince(bot.last_announce_at, relativeTimerTick)}</span>
                        {:else if address}
                            <span>{t("bots.never_announced")}</span>
                        {:else}
                            <span>-</span>
                        {/if}
                    </dd>
                </div>
            </dl>
            {#if lastError}
                <div
                    class="rounded-lg border border-red-200/90 dark:border-red-900/70 bg-red-50/90 dark:bg-red-950/50 px-2.5 py-2 text-[11px] text-red-900 dark:text-red-100"
                >
                    <div class="font-semibold flex items-center gap-1.5">
                        <MaterialDesignIcon iconName="alert-circle-outline" class="size-4 shrink-0 opacity-90" />
                        {t("bots.last_error_heading")}
                    </div>
                    <pre
                        class="mt-1.5 m-0 whitespace-pre-wrap wrap-break-word font-mono text-[10px] leading-relaxed text-red-800/95 dark:text-red-100/90">{lastError}</pre>
                </div>
            {/if}
        </div>
    </div>
</div>
