<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import ToastUtils from "../../../js/ToastUtils.js";
    import { t } from "../../../js/i18n.js";
    import type { BotRecord } from "../lib/types.js";

    interface Props {
        bot: BotRecord | null;
        logText?: string;
        truncated?: boolean;
        loading?: boolean;
        onClose: () => void;
    }

    let { bot = null, logText = "", truncated = false, loading = false, onClose }: Props = $props();

    const displayText = $derived.by(() => {
        const text = (logText || "").trim();
        if (text) {
            return logText;
        }
        return loading ? "" : t("bots.process_log_empty");
    });

    async function copyProcessLog(): Promise<void> {
        const text = (logText || "").trim();
        if (!text) {
            return;
        }
        try {
            await navigator.clipboard.writeText(logText);
            ToastUtils.success(t("bots.process_log_copied"));
        } catch {
            ToastUtils.error(t("common.failed_to_copy"));
        }
    }
</script>

{#if bot}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class="fixed inset-0 z-100 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/50"
        onclick={(e) => {
            if (e.target === e.currentTarget) {
                onClose();
            }
        }}
    >
        <div
            class="w-full sm:max-w-2xl rounded-t-2xl sm:rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-6 space-y-4 max-h-[90vh] flex flex-col"
        >
            <div class="flex justify-between items-start gap-2 shrink-0">
                <div class="min-w-0 pr-2">
                    <h3 class="text-lg sm:text-xl font-bold text-sem-fg truncate">
                        {t("bots.process_log_title")}: {bot.name}
                    </h3>
                    {#if truncated}
                        <p class="text-xs text-amber-600 dark:text-amber-400 mt-0.5">
                            {t("bots.process_log_truncated")}
                        </p>
                    {/if}
                </div>
                <button
                    type="button"
                    class="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80"
                    onclick={onClose}
                >
                    <MaterialDesignIcon iconName="close" class="size-5" />
                </button>
            </div>

            <div class="flex-1 min-h-[160px] max-h-[50vh] overflow-hidden flex flex-col">
                {#if loading}
                    <div class="py-12 text-center text-sm text-sem-fg-muted">
                        {t("common.loading")}
                    </div>
                {:else}
                    <pre
                        class="flex-1 overflow-auto rounded-lg bg-black/5 dark:bg-white/5 p-3 font-mono text-xs text-gray-800 dark:text-gray-200 whitespace-pre-wrap">{displayText}</pre>
                {/if}
            </div>

            <div class="flex justify-end gap-2 shrink-0 pt-2 border-t border-sem-border">
                <button
                    type="button"
                    class="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 disabled:opacity-40"
                    disabled={!logText || loading}
                    title={t("common.copy")}
                    onclick={copyProcessLog}
                >
                    <MaterialDesignIcon iconName="content-copy" class="size-6" />
                </button>
                <button
                    type="button"
                    class="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80"
                    onclick={onClose}
                >
                    <MaterialDesignIcon iconName="close" class="size-6" />
                </button>
            </div>
        </div>
    </div>
{/if}
