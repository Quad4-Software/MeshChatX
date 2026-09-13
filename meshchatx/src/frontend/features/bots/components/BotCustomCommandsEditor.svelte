<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { defaultCustomDraft, type BotCustomCommandDraft, type BotCustomDraft } from "../lib/botDrafts.js";

    interface Props {
        draft?: BotCustomDraft;
    }

    let { draft = $bindable(defaultCustomDraft()) }: Props = $props();

    function patch(update: Partial<BotCustomDraft>): void {
        draft = { ...(draft || defaultCustomDraft()), ...update };
    }

    function patchCommand(index: number, update: Partial<BotCustomCommandDraft>): void {
        const commands = draft.commands.map((c, i) => (i === index ? { ...c, ...update } : c));
        patch({ commands });
    }

    function addCommand(): void {
        patch({
            commands: [...draft.commands, { name: "", response: "", description: "" }],
        });
    }

    function removeCommand(index: number): void {
        patch({
            commands: draft.commands.filter((_, i) => i !== index),
        });
    }
</script>

<div class="space-y-3">
    <div>
        <label class="glass-label" for="bot-custom-welcome">{t("bots.custom_welcome")}</label>
        <textarea
            id="bot-custom-welcome"
            value={draft.welcome}
            class="input-field"
            rows="2"
            placeholder={t("bots.custom_welcome_placeholder")}
            oninput={(e) => patch({ welcome: (e.target as HTMLTextAreaElement).value })}></textarea>
        <p class="text-xs text-sem-fg-muted mt-1">
            {t("bots.custom_welcome_hint")}
        </p>
    </div>

    <div class="space-y-2">
        <span class="glass-label">{t("bots.custom_commands")}</span>
        {#each draft.commands as cmd, index (index)}
            <div class="flex items-start gap-2">
                <input
                    value={cmd.name}
                    type="text"
                    class="input-field font-mono text-xs w-28 sm:w-32 shrink-0"
                    maxlength="32"
                    spellcheck="false"
                    placeholder={t("bots.custom_command_name")}
                    oninput={(e) => patchCommand(index, { name: (e.target as HTMLInputElement).value })}
                />
                <input
                    value={cmd.response}
                    type="text"
                    class="input-field text-xs min-w-0 flex-1"
                    placeholder={t("bots.custom_command_response")}
                    oninput={(e) => patchCommand(index, { response: (e.target as HTMLInputElement).value })}
                />
                <button
                    type="button"
                    class="p-2 rounded-lg text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 shrink-0"
                    title={t("bots.custom_command_remove")}
                    onclick={() => removeCommand(index)}
                >
                    <MaterialDesignIcon iconName="close" class="size-4" />
                </button>
            </div>
        {/each}
        <button
            type="button"
            class="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline disabled:opacity-40"
            disabled={draft.commands.length >= 64}
            onclick={addCommand}
        >
            <MaterialDesignIcon iconName="plus" class="size-4" />
            {t("bots.custom_command_add")}
        </button>
        <p class="text-xs text-sem-fg-muted">
            {t("bots.custom_commands_hint")}
        </p>
    </div>
</div>
