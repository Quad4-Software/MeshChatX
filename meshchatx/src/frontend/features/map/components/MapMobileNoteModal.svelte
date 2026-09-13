<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";

    interface Props {
        show?: boolean;
        text?: string;
        onclose?: () => void;
        onsave?: () => void;
        ondelete?: () => void;
    }

    let { show = false, text = $bindable(""), onclose, onsave, ondelete }: Props = $props();
</script>

{#if show}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class="fixed inset-0 z-100 flex items-end sm:items-center justify-center p-4 bg-black/50 backdrop-blur-xs"
        onclick={(e) => {
            if (e.target === e.currentTarget) {
                onclose?.();
            }
        }}
    >
        <div
            class="bg-sem-surface w-full max-w-lg rounded-t-2xl sm:rounded-2xl shadow-2xl overflow-hidden animate-slide-up sm:animate-fade-in"
        >
            <div class="p-4 border-b border-sem-border flex items-center justify-between">
                <h3 class="text-lg font-bold text-sem-fg flex items-center gap-2">
                    <MaterialDesignIcon iconName="note-edit" class="size-5 text-amber-500" />
                    Edit Note
                </h3>
                <button
                    type="button"
                    class="p-2 text-gray-400 hover:bg-sem-surface-muted rounded-full transition-colors cursor-pointer"
                    onclick={() => onclose?.()}
                >
                    <MaterialDesignIcon iconName="close" class="size-5" />
                </button>
            </div>
            <div class="p-4">
                <textarea
                    bind:value={text}
                    class="w-full h-40 p-4 text-base bg-gray-50 dark:bg-zinc-800 border border-sem-border rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-transparent outline-hidden resize-none text-sem-fg"
                    placeholder="Type your note here..."></textarea>
            </div>
            <div class="p-4 bg-gray-50 dark:bg-zinc-800/50 flex justify-between gap-3">
                <button
                    type="button"
                    class="flex-1 px-4 py-3 text-sm font-bold text-red-500 hover:bg-red-100 dark:hover:bg-red-900/20 rounded-xl transition-colors flex items-center justify-center gap-2 cursor-pointer"
                    onclick={() => ondelete?.()}
                >
                    <MaterialDesignIcon iconName="trash-can-outline" class="size-5" />
                    Delete
                </button>
                <button
                    type="button"
                    class="flex-2 px-4 py-3 text-sm font-bold bg-amber-500 text-white hover:bg-amber-600 rounded-xl shadow-lg shadow-amber-500/30 transition-colors cursor-pointer"
                    onclick={() => onsave?.()}
                >
                    Save Note
                </button>
            </div>
        </div>
    </div>
{/if}
