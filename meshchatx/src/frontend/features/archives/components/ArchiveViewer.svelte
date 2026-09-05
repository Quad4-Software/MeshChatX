<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { pathViewerClasses } from "../lib/archiveRender.js";
    import type { ArchiveItem } from "../lib/types.js";

    interface Props {
        viewingArchive: ArchiveItem;
        renderedContent: string;
        isLoadingViewer?: boolean;
        isRecrawling?: boolean;
        isWideSplit?: boolean;
        onClose?: () => void;
        onRecrawl?: (archive: ArchiveItem) => void;
        onExport?: (archive: ArchiveItem) => void;
        onOpenLive?: (archive: ArchiveItem) => void;
        onOptOut?: (archive: ArchiveItem) => void;
        onDelete?: (archive: ArchiveItem) => void;
        onContentClick?: (event: MouseEvent) => void;
    }

    let {
        viewingArchive,
        renderedContent,
        isLoadingViewer = false,
        isRecrawling = false,
        isWideSplit = false,
        onClose,
        onRecrawl,
        onExport,
        onOpenLive,
        onOptOut,
        onDelete,
        onContentClick,
    }: Props = $props();

    const viewerClassesList = $derived(pathViewerClasses(viewingArchive.page_path).join(" "));
</script>

<div
    class="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-sem-canvas {isWideSplit
        ? ''
        : 'border-t border-sem-border lg:border-t-0'}"
>
    <div class="flex shrink-0 items-center gap-1 border-b border-sem-border px-2 py-2">
        <button
            type="button"
            class="rounded-lg p-1 text-sem-fg-muted hover:bg-sem-surface/60 lg:hidden"
            title={t("archives.back_to_list")}
            onclick={onClose}
        >
            <MaterialDesignIcon iconName="arrow-left" class="size-5" />
        </button>
        <div class="min-w-0 flex-1 px-1">
            <div class="truncate text-xs text-sem-fg-muted">{viewingArchive.node_name}</div>
            <div class="truncate font-mono text-sm">{viewingArchive.page_path || "/"}</div>
        </div>
        <button
            type="button"
            class="rounded-lg p-2 text-sem-fg hover:bg-sem-surface/60 disabled:opacity-40"
            disabled={isRecrawling}
            title={t("archives.recrawl")}
            onclick={() => onRecrawl?.(viewingArchive)}
        >
            <MaterialDesignIcon
                iconName={isRecrawling ? "loading" : "refresh"}
                class="size-4 {isRecrawling ? 'animate-spin' : ''}"
            />
        </button>
        <button
            type="button"
            class="rounded-lg p-2 text-sem-fg hover:bg-sem-surface/60"
            title={t("archives.export_mu")}
            onclick={() => onExport?.(viewingArchive)}
        >
            <MaterialDesignIcon iconName="download" class="size-4" />
        </button>
        <button
            type="button"
            class="rounded-lg p-2 text-sem-accent hover:bg-sem-surface/60"
            title={t("archives.open_live")}
            onclick={() => onOpenLive?.(viewingArchive)}
        >
            <MaterialDesignIcon iconName="open-in-new" class="size-4" />
        </button>
        <button
            type="button"
            class="rounded-lg p-2 text-sem-fg-muted hover:bg-sem-surface/60"
            title={t("archives.never_crawl")}
            onclick={() => onOptOut?.(viewingArchive)}
        >
            <MaterialDesignIcon iconName="cancel" class="size-4" />
        </button>
        <button
            type="button"
            class="rounded-lg p-2 text-red-500 hover:bg-sem-surface/60"
            title={t("archives.delete_snapshot")}
            onclick={() => onDelete?.(viewingArchive)}
        >
            <MaterialDesignIcon iconName="trash-can-outline" class="size-4" />
        </button>
        <button
            type="button"
            class="hidden rounded-lg p-2 text-sem-fg-muted hover:bg-sem-surface/60 lg:inline-flex"
            title={t("archives.close_viewer")}
            onclick={onClose}
        >
            <MaterialDesignIcon iconName="close" class="size-5" />
        </button>
    </div>

    <div class="nodeContainer flex-1 overflow-y-auto overscroll-contain p-4">
        {#if isLoadingViewer}
            <div class="flex h-full items-center justify-center text-sem-fg-muted">
                <MaterialDesignIcon iconName="refresh" class="size-8 animate-spin-reverse" />
            </div>
        {:else}
            <div
                class="h-full selection:bg-sem-accent/30 {viewerClassesList}"
                onclickcapture={onContentClick}
            >
                <!-- eslint-disable-next-line svelte/no-at-html-tags -->
                {@html renderedContent}
            </div>
        {/if}
    </div>
</div>

<style>
    .nodeContainer {
        contain: content;
    }

    :global(.nodeContainer a) {
        color: #3b82f6;
        text-decoration: underline;
    }

    :global(.nodeContainer p) {
        margin: 0.5rem 0;
    }

    :global(.nodeContainer h1),
    :global(.nodeContainer h2),
    :global(.nodeContainer h3) {
        margin: 1.25rem 0 0.75rem 0;
        font-weight: bold;
        line-height: 1.2;
    }

    :global(.nodeContainer h1) {
        font-size: 1.5rem;
    }
    :global(.nodeContainer h2) {
        font-size: 1.25rem;
    }
    :global(.nodeContainer h3) {
        font-size: 1.1rem;
    }

    :global(.nodeContainer hr) {
        margin: 1.5rem 0;
        border: 0;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
    }
</style>
