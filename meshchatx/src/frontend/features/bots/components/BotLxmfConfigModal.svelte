<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import BotLxmfConfigFields from "./BotLxmfConfigFields.svelte";
    import { t } from "../../../js/i18n.js";
    import type { BotRecord, LxmfConfigDraft, LxmfConfigPatch } from "../lib/types.js";
    import { buildLxmfConfigPatch, defaultLxmfConfigDraft, draftFromBotLxmfConfig } from "../lib/botLxmfConfigForm.js";
    import { formatEffectiveLxmfConfig } from "../lib/botUtils.js";

    interface Props {
        open?: boolean;
        bot: BotRecord | null;
        saving?: boolean;
        onClose: () => void;
        onSave: (botId: string, patch: LxmfConfigPatch) => void;
    }

    let { open = false, bot = null, saving = false, onClose, onSave }: Props = $props();

    let lxmfDraft = $state<LxmfConfigDraft>(defaultLxmfConfigDraft());

    $effect(() => {
        if (open && bot) {
            lxmfDraft = draftFromBotLxmfConfig(bot.lxmf_config);
        }
    });

    function submit(): void {
        if (!bot) {
            return;
        }
        const patch = buildLxmfConfigPatch(lxmfDraft);
        onSave(bot.id, patch);
    }
</script>

{#if open && bot}
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
            class="w-full sm:max-w-lg rounded-t-2xl sm:rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-6 space-y-4 max-h-[90vh] overflow-y-auto"
        >
            <div class="flex justify-between items-start gap-2">
                <div class="min-w-0 pr-2">
                    <h3 class="text-lg sm:text-xl font-bold text-sem-fg">
                        {t("bots.lxmf_config_title")}
                    </h3>
                    <p class="text-sm text-gray-600 dark:text-gray-400 mt-0.5 truncate">
                        {bot.name}
                    </p>
                </div>
                <button
                    type="button"
                    class="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80"
                    onclick={onClose}
                >
                    <MaterialDesignIcon iconName="close" class="size-5" />
                </button>
            </div>

            <div class="space-y-4">
                {#if bot.effective_lxmf_config}
                    <details class="rounded-lg border border-sem-border p-3 text-xs">
                        <summary class="cursor-pointer font-semibold text-gray-700 dark:text-gray-300">
                            {t("bots.effective_settings_heading")}
                        </summary>
                        <pre
                            class="mt-2 max-h-40 overflow-auto rounded bg-black/5 dark:bg-white/5 p-2 font-mono text-[11px] whitespace-pre-wrap">{formatEffectiveLxmfConfig(
                                bot.effective_lxmf_config
                            )}</pre>
                    </details>
                {/if}

                <BotLxmfConfigFields bind:draft={lxmfDraft} />

                <div class="flex justify-end gap-2 pt-2">
                    <button
                        type="button"
                        class="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80"
                        onclick={onClose}
                    >
                        <MaterialDesignIcon iconName="close" class="size-6" />
                    </button>
                    <button
                        type="button"
                        class="p-2 rounded-lg text-gray-500 hover:text-emerald-600 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 disabled:opacity-40"
                        disabled={saving}
                        onclick={submit}
                    >
                        {#if saving}
                            <span
                                class="inline-block w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin"
                            ></span>
                        {:else}
                            <MaterialDesignIcon iconName="check" class="size-6" />
                        {/if}
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}
