<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../../ui/svelte/MaterialDesignIcon.svelte";
    import ShortcutRecorder from "../ShortcutRecorder.svelte";
    import KeyboardShortcuts from "../../../../js/KeyboardShortcuts.js";
    import { t } from "../../../../js/i18n.js";

    interface Props {
        visible?: boolean;
    }

    let { visible = true }: Props = $props();

    let shortcutsExpanded = $state(true);
    let shortcutsVersion = $state(0);

    const defaultShortcuts = KeyboardShortcuts.getDefaultShortcuts();

    function getShortcutKeys(action: string): string[] {
        // subscribe to version change
        void shortcutsVersion;
        const found = (KeyboardShortcuts as any).shortcuts?.find((s: any) => s.action === action);
        return found?.keys || [];
    }

    function saveShortcut(action: string, keys: string[]) {
        (KeyboardShortcuts as any).saveShortcut(action, keys);
        shortcutsVersion += 1;
    }

    function deleteShortcut(action: string) {
        (KeyboardShortcuts as any).deleteShortcut(action);
        shortcutsVersion += 1;
    }
</script>

{#if visible}
    <div class="settings-section break-inside-avoid">
        <button
            type="button"
            class="settings-section__header w-full text-left cursor-pointer border-0 bg-transparent"
            aria-expanded={shortcutsExpanded}
            onclick={() => (shortcutsExpanded = !shortcutsExpanded)}
        >
            <div class="flex items-center gap-3 w-full min-w-0">
                <div class="p-2 bg-blue-100 dark:bg-blue-900/30 text-sem-accent rounded-xl shrink-0">
                    <MaterialDesignIcon iconName="keyboard-outline" class="size-6" />
                </div>
                <div class="min-w-0 flex-1">
                    <h2>{t("settings.keyboard_shortcuts_title")}</h2>
                    <p>{t("settings.keyboard_shortcuts_description")}</p>
                </div>
                <MaterialDesignIcon
                    iconName={shortcutsExpanded ? "chevron-up" : "chevron-down"}
                    class="size-6 shrink-0 text-sem-fg-muted"
                />
            </div>
        </button>
        {#if shortcutsExpanded}
            <div class="settings-section__body">
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
                    {#each defaultShortcuts as shortcut (shortcut.action)}
                        <div class="bg-gray-50/50 dark:bg-zinc-800/30 rounded-2xl p-4 sm:p-5 border border-sem-border">
                            <div class="flex items-center justify-between mb-3">
                                <span class="text-sm font-bold text-sem-fg uppercase tracking-wide">
                                    {shortcut.description}
                                </span>
                            </div>
                            <ShortcutRecorder
                                value={getShortcutKeys(shortcut.action)}
                                action={shortcut.action}
                                onsave={(keys) => saveShortcut(shortcut.action, keys)}
                                ondelete={() => deleteShortcut(shortcut.action)}
                            />
                        </div>
                    {/each}
                </div>
            </div>
        {/if}
    </div>
{/if}
