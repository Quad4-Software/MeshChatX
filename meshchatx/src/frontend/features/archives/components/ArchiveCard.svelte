<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import { cardPreviewHtml, formatArchiveDate, previewClasses, shortHash } from "../lib/archiveRender.js";
    import type { ArchiveItem, NomadRenderOptions } from "../lib/types.js";

    interface Props {
        archive: ArchiveItem;
        isSelected?: boolean;
        searchQuery?: string;
        cardPreviewCache?: Record<string, string>;
        nomadMicronWasmActive?: boolean;
        nomadRenderOptions: NomadRenderOptions;
        onSelect?: (archive: ArchiveItem) => void;
    }

    let {
        archive,
        isSelected = false,
        searchQuery = "",
        cardPreviewCache = {},
        nomadMicronWasmActive = false,
        nomadRenderOptions,
        onSelect,
    }: Props = $props();

    const previewClassesList = $derived(previewClasses(archive).join(" "));
    const previewHtml = $derived(
        cardPreviewHtml(
            archive,
            searchQuery,
            cardPreviewCache,
            nomadMicronWasmActive,
            nomadRenderOptions
        )
    );
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
<article
    class="group flex cursor-pointer flex-col overflow-hidden rounded-2xl border border-sem-border/70 bg-sem-surface/40 shadow-sm transition-colors hover:border-sem-accent/40 hover:bg-sem-surface/70 {isSelected
        ? 'ring-2 ring-sem-accent/40 border-sem-accent/40'
        : ''}"
    onclick={() => onSelect?.(archive)}
>
    <div class="flex items-start justify-between gap-2 border-b border-sem-border/50 px-3 py-2.5">
        <div class="min-w-0">
            <h2 class="truncate text-sm font-semibold group-hover:text-sem-accent">
                {archive.node_name}
            </h2>
            <p class="mt-0.5 truncate font-mono text-[11px] text-sem-fg-muted">
                {archive.page_path || "/"}
            </p>
        </div>
        <div class="shrink-0 text-right text-[10px] text-sem-fg-muted">
            <div>{formatArchiveDate(archive.created_at)}</div>
            <div class="mt-0.5 font-mono opacity-70">
                {(archive.hash || "").substring(0, 8)}
            </div>
        </div>
    </div>

    <div class="archive-card-preview min-h-[5.5rem] flex-1 overflow-hidden px-3 py-2">
        <div
            class="pointer-events-none max-h-36 overflow-hidden text-xs leading-relaxed text-sem-fg-muted {previewClassesList}"
        >
            <!-- eslint-disable-next-line svelte/no-at-html-tags -->
            {@html previewHtml}
        </div>
    </div>

    <div class="flex items-center justify-between gap-2 border-t border-sem-border/50 px-3 py-2">
        <span class="rounded bg-sem-surface-muted px-1.5 py-0.5 font-mono text-[10px] text-sem-fg-muted">
            {shortHash(archive.destination_hash)}
        </span>
        <span class="text-[10px] font-medium text-sem-accent opacity-0 transition-opacity group-hover:opacity-100">
            {t("archives.view")}
        </span>
    </div>
</article>

<style>
    .archive-card-preview {
        mask-image: linear-gradient(to bottom, #000 70%, transparent 100%);
    }

    :global(.archive-card-preview a) {
        color: #3b82f6;
        text-decoration: underline;
    }

    :global(.archive-card-preview p) {
        margin: 0.5rem 0;
    }

    :global(.archive-card-preview h1),
    :global(.archive-card-preview h2),
    :global(.archive-card-preview h3) {
        margin: 1.25rem 0 0.75rem 0;
        font-weight: bold;
        line-height: 1.2;
    }

    :global(.archive-card-preview h1) {
        font-size: 1.5rem;
    }
    :global(.archive-card-preview h2) {
        font-size: 1.25rem;
    }
    :global(.archive-card-preview h3) {
        font-size: 1.1rem;
    }
</style>
