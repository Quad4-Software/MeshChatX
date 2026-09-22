<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import KeyboardShortcuts from "../../../js/KeyboardShortcuts.js";

    interface Props {
        value?: string[];
        action: string;
        onchange?: (keys: string[]) => void;
        onsave?: (keys: string[]) => void;
        ondelete?: () => void;
    }

    let { value = [], action: _action, onchange, onsave, ondelete }: Props = $props();

    let isRecording = $state(false);
    let recordedKeys = $state<string[]>([]);
    const keys = $derived(isRecording ? recordedKeys : [...value]);

    function formatKey(key: string): string {
        if (key === "control") return "Ctrl";
        if (key === "alt") return "Alt";
        if (key === "shift") return "Shift";
        if (key === "meta") return "⌘";
        if (key === " ") return "Space";
        return key;
    }

    function toggleRecording() {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    }

    function startRecording() {
        isRecording = true;
        recordedKeys = [];
        KeyboardShortcuts.startRecording((newKeys: string[]) => {
            recordedKeys = newKeys;
        });
    }

    function stopRecording() {
        isRecording = false;
        KeyboardShortcuts.stopRecording();
        onchange?.(recordedKeys);
        onsave?.(recordedKeys);
    }

    function clearShortcut() {
        onchange?.([]);
        ondelete?.();
    }
</script>

<div class="flex items-center gap-2">
    <div
        class="flex-1 flex flex-wrap gap-1.5 p-2 bg-sem-surface border border-sem-border rounded-xl min-h-[44px] {isRecording
            ? 'ring-2 ring-blue-500 border-blue-500'
            : ''}"
    >
        {#if keys.length > 0}
            {#each keys as key (key)}
                <kbd
                    class="px-2 py-1 bg-sem-surface-muted border border-sem-border rounded-lg text-xs font-bold text-sem-fg-muted shadow-xs uppercase"
                >
                    {formatKey(key)}
                </kbd>
            {/each}
        {:else}
            <span class="text-sem-fg-muted text-sm my-auto px-1">
                {isRecording ? "Press keys..." : "No shortcut"}
            </span>
        {/if}
    </div>

    <button
        type="button"
        class="px-4 py-2 rounded-xl font-bold transition-all shadow-xs flex items-center gap-2 {isRecording
            ? 'bg-blue-600 text-white hover:bg-blue-700'
            : 'bg-sem-surface-muted text-sem-fg-muted hover:bg-gray-200 hover:bg-sem-surface-muted'}"
        onclick={toggleRecording}
    >
        <MaterialDesignIcon iconName={isRecording ? "check" : "record-circle-outline"} class="size-5" />
        {isRecording ? "Done" : "Record"}
    </button>

    {#if keys.length > 0 && !isRecording}
        <button
            type="button"
            class="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-all"
            title="Clear Shortcut"
            onclick={clearShortcut}
        >
            <MaterialDesignIcon iconName="trash-can-outline" class="size-5" />
        </button>
    {/if}
</div>
