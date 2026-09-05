<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import type { NomadSection } from "../lib/types.js";

    interface Props {
        sec: NomadSection;
        isEditing?: boolean;
        editingName?: string;
        onToggleCollapse?: () => void;
        onContextMenu?: (e: MouseEvent) => void;
        onStartEditing?: () => void;
        onSaveName?: () => void;
        onCancelEditing?: () => void;
        onNameChange?: (name: string) => void;
    }

    let {
        sec,
        isEditing = false,
        editingName = "",
        onToggleCollapse,
        onContextMenu,
        onStartEditing,
        onSaveName,
        onCancelEditing,
        onNameChange,
    }: Props = $props();
</script>

<div
    class="flex items-center justify-between px-2 py-1 cursor-pointer select-none"
    onclick={onToggleCollapse}
    oncontextmenu={onContextMenu}
    role="button"
    tabindex="0"
    onkeydown={(e) => {
        if (e.key === "Enter") onToggleCollapse?.();
    }}
>
    <div class="flex items-center gap-2 flex-1 min-w-0">
        <MaterialDesignIcon
            iconName={sec.collapsed ? "chevron-right" : "chevron-down"}
            class="size-4 text-gray-400 shrink-0"
        />
        {#if isEditing}
            <input
                value={editingName}
                type="text"
                class="flex-1 bg-transparent border-b border-blue-500 text-xs font-medium text-sem-fg focus:outline-hidden min-w-0"
                onclick={(e) => e.stopPropagation()}
                oninput={(e) => onNameChange?.((e.target as HTMLInputElement).value)}
                onkeydown={(e) => {
                    if (e.key === "Enter") onSaveName?.();
                    if (e.key === "Escape") onCancelEditing?.();
                }}
                onblur={onSaveName}
            />
            <button
                type="button"
                class="p-1 text-green-500 hover:text-green-600 shrink-0"
                onclick={(e) => {
                    e.stopPropagation();
                    onSaveName?.();
                }}
            >
                <MaterialDesignIcon iconName="check" class="size-4" />
            </button>
        {:else}
            <span
                class="text-xs font-medium text-sem-fg-muted truncate"
                onclick={(e) => {
                    e.stopPropagation();
                    onStartEditing?.();
                }}
                role="button"
                tabindex="0"
                onkeydown={(e) => {
                    if (e.key === "Enter") onStartEditing?.();
                }}
            >
                {sec.name}
            </span>
            {#if sec.collapsed}
                <span
                    class="text-[10px] font-semibold text-sem-fg-muted bg-sem-surface-muted px-2 py-0.5 rounded-full shrink-0"
                >
                    {sec.favourites?.length || 0}
                </span>
            {/if}
        {/if}
    </div>
</div>
