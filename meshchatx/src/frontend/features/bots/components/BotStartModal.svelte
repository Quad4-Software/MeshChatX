<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import type { BotTemplate, LxmfConfigDraft, LxmfConfigPatch } from "../lib/types.js";
    import { buildLxmfConfigPatch, defaultLxmfConfigDraft } from "../lib/botLxmfConfigForm.js";
    import BotLxmfConfigFields from "./BotLxmfConfigFields.svelte";

    interface Props {
        open?: boolean;
        template: BotTemplate | null;
        busy?: boolean;
        onClose: () => void;
        onStart: (templateId: string, name: string, lxmfConfig?: LxmfConfigPatch) => void;
    }

    let { open = false, template = null, busy = false, onClose, onStart }: Props = $props();

    let botName = $state("");
    let lxmfDraft = $state<LxmfConfigDraft>(defaultLxmfConfigDraft());

    $effect(() => {
        if (open && template) {
            botName = template.name || "";
            lxmfDraft = defaultLxmfConfigDraft();
        }
    });

    function submit(): void {
        if (!template) {
            return;
        }
        const name = botName.trim() || template.name;
        const patch = buildLxmfConfigPatch(lxmfDraft);
        onStart(template.id, name, patch);
    }
</script>

{#if open && template}
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
            class="w-full sm:max-w-md rounded-t-2xl sm:rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-6 space-y-4 max-h-[90vh] overflow-y-auto"
        >
            <div class="flex justify-between items-start gap-2">
                <h3 class="text-lg sm:text-xl font-bold text-sem-fg pr-2">
                    {t("bots.start_bot")}: {template.name}
                </h3>
                <button
                    type="button"
                    class="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80"
                    onclick={onClose}
                >
                    <MaterialDesignIcon iconName="close" class="size-5" />
                </button>
            </div>

            <div class="space-y-4">
                <div>
                    <label
                        class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1"
                        for="bot-start-name">{t("bots.bot_name")}</label
                    >
                    <input
                        id="bot-start-name"
                        bind:value={botName}
                        type="text"
                        placeholder={template.name}
                        class="input-field"
                    />
                </div>

                <div class="text-sm text-gray-600 dark:text-gray-400">
                    {template.description}
                </div>

                <details class="rounded-lg border border-sem-border p-3">
                    <summary class="cursor-pointer text-sm font-semibold text-gray-800 dark:text-gray-200">
                        {t("bots.advanced_lxmf_settings")}
                    </summary>
                    <div class="mt-3 space-y-3">
                        <BotLxmfConfigFields bind:draft={lxmfDraft} />
                    </div>
                </details>

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
                        disabled={busy}
                        onclick={submit}
                    >
                        {#if busy}
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
