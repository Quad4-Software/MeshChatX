<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import NomadSectionHeader from "./NomadSectionHeader.svelte";
    import NomadFavouriteRow from "./NomadFavouriteRow.svelte";
    import type { NomadFavourite, NomadNode, NomadSection } from "../lib/types.js";

    interface Props {
        sec: NomadSection;
        nodes: Record<string, NomadNode>;
        selectedDestinationHash?: string;
        selectionMode?: boolean;
        selectedHashes?: string[];
        isBlockedFn?: (hash: string) => boolean;
        editingSectionId?: string | null;
        editingSectionName?: string;
        draggingFavouriteHashes?: string[];
        onFavouriteClick?: (fav: NomadFavourite) => void;
        onToggleFavouriteSelect?: (hash: string) => void;
        onOpenFavMenu?: (e: MouseEvent, fav: NomadFavourite, sectionId: string) => void;
        onOpenSecMenu?: (e: MouseEvent, sec: NomadSection) => void;
        onToggleSectionCollapse?: (secId: string) => void;
        onStartEditingSection?: (sec: NomadSection) => void;
        onSaveSectionName?: () => void;
        onCancelEditingSection?: () => void;
        onSectionNameChange?: (val: string) => void;
        onFavouritesMoved?: (targetSectionId: string, hashes: string[]) => void;
    }

    let {
        sec,
        nodes = {},
        selectedDestinationHash = "",
        selectionMode = false,
        selectedHashes = [],
        isBlockedFn,
        editingSectionId = null,
        editingSectionName = "",
        draggingFavouriteHashes = [],
        onFavouriteClick,
        onToggleFavouriteSelect,
        onOpenFavMenu,
        onOpenSecMenu,
        onToggleSectionCollapse,
        onStartEditingSection,
        onSaveSectionName,
        onCancelEditingSection,
        onSectionNameChange,
        onFavouritesMoved,
    }: Props = $props();

    let isDragOver = $state(false);
</script>

<div
    class="nomad-section border border-transparent rounded-lg transition-colors {isDragOver
        ? 'border-blue-400 bg-blue-50/20'
        : ''}"
    role="region"
    aria-label={sec.name}
    ondragover={(e) => {
        e.preventDefault();
        isDragOver = true;
    }}
    ondragleave={() => {
        isDragOver = false;
    }}
    ondrop={(e) => {
        e.preventDefault();
        isDragOver = false;
        if (draggingFavouriteHashes.length > 0) {
            onFavouritesMoved?.(sec.id, draggingFavouriteHashes);
        }
    }}
>
    <NomadSectionHeader
        {sec}
        isEditing={editingSectionId === sec.id}
        editingName={editingSectionName}
        onToggleCollapse={() => onToggleSectionCollapse?.(sec.id)}
        onContextMenu={(e) => {
            e.preventDefault();
            onOpenSecMenu?.(e, sec);
        }}
        onStartEditing={() => onStartEditingSection?.(sec)}
        onSaveName={onSaveSectionName}
        onCancelEditing={onCancelEditingSection}
        onNameChange={onSectionNameChange}
    />

    <div class="h-px bg-gray-200 dark:bg-zinc-800 mx-1"></div>

    {#if !sec.collapsed}
        <div class="space-y-2 pt-2 pb-1 px-1">
            {#each sec.favourites || [] as fav (fav.destination_hash)}
                <NomadFavouriteRow
                    {fav}
                    node={nodes[fav.destination_hash]}
                    selected={fav.destination_hash === selectedDestinationHash}
                    {selectionMode}
                    isSelectedInBulk={selectedHashes.includes(fav.destination_hash)}
                    isBlocked={isBlockedFn ? isBlockedFn(fav.destination_hash) : false}
                    onclick={() => onFavouriteClick?.(fav)}
                    oncontextmenu={(e) => {
                        e.preventDefault();
                        onOpenFavMenu?.(e, fav, sec.id);
                    }}
                    ontoggleselect={() => onToggleFavouriteSelect?.(fav.destination_hash)}
                    ondragstart={(e) => {
                        if (e.dataTransfer) {
                            e.dataTransfer.setData("text/plain", fav.destination_hash);
                        }
                    }}
                />
            {/each}
        </div>
    {/if}
</div>
