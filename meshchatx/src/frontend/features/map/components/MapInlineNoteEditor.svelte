<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        show?: boolean;
        text?: string;
        pos?: { x: number; y: number } | null;
        onclose?: () => void;
        onsave?: () => void;
        ondelete?: () => void;
        onupdatetext?: (text: string) => void;
    }

    let { show = false, text = $bindable(""), pos = null, onclose, onsave, ondelete, onupdatetext }: Props = $props();
</script>

{#if show}
    <div class="absolute z-40 pointer-events-auto" style={pos ? `left: ${pos.x}px; top: ${pos.y}px;` : undefined}>
        <div
            class="bg-sem-surface rounded-xl shadow-2xl border border-sem-border p-4 w-64 transform -translate-x-1/2 -translate-y-full mb-6"
        >
            <div class="flex items-center justify-between mb-2">
                <span class="text-sm font-bold text-sem-fg flex items-center gap-1">
                    <MaterialDesignIcon iconName="note-edit" class="size-4 text-amber-500" />
                    Edit Note
                </span>
                <button
                    type="button"
                    class="text-sem-fg-muted hover:text-sem-fg cursor-pointer"
                    onclick={() => onclose?.()}
                >
                    <MaterialDesignIcon iconName="close" class="size-4" />
                </button>
            </div>
            <textarea
                bind:value={text}
                class="w-full h-24 p-2 text-sm bg-gray-50 dark:bg-zinc-800 border border-sem-border rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent outline-hidden resize-none text-sem-fg"
                placeholder="Type your note here..."
                oninput={(e) => onupdatetext?.((e.target as HTMLTextAreaElement).value)}></textarea>
            <div class="flex justify-between mt-3">
                <button
                    type="button"
                    class="px-3 py-1.5 text-xs font-semibold text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors flex items-center gap-1 cursor-pointer"
                    onclick={() => ondelete?.()}
                >
                    <MaterialDesignIcon iconName="trash-can-outline" class="size-3.5" />
                    {t("common.delete")}
                </button>
                <button
                    type="button"
                    class="px-3 py-1.5 text-xs font-semibold bg-amber-500 text-white hover:bg-amber-600 rounded-lg shadow-xs transition-colors cursor-pointer"
                    onclick={() => onsave?.()}
                >
                    {t("common.save")}
                </button>
            </div>
        </div>
    </div>
{/if}
