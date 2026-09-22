<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import type { DocContentResponse, DocTocEntry } from "../lib/types.js";

    interface Props {
        selectedDocContent: DocContentResponse | null;
        docLoadError: string | null;
        meshchatxDocsCount: number;
        docToc: DocTocEntry[];
        onDocClick: (event: MouseEvent) => void;
        onScrollToHeading: (id: string) => void;
    }

    let { selectedDocContent, docLoadError, meshchatxDocsCount, docToc, onDocClick, onScrollToHeading }: Props =
        $props();

    let scrollerEl = $state<HTMLElement | null>(null);
    let proseEl = $state<HTMLElement | null>(null);

    export function scrollToTop(): void {
        if (scrollerEl) {
            scrollerEl.scrollTop = 0;
        }
    }

    export function getProseElement(): HTMLElement | null {
        return proseEl;
    }
</script>

<div class="flex flex-1 min-h-0 overflow-hidden">
    <div class="flex-1 flex min-w-0 bg-sem-surface dark:bg-zinc-900 overflow-hidden">
        <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
            {#if selectedDocContent}
                <div bind:this={scrollerEl} class="flex-1 overflow-y-auto scroll-smooth custom-scroll">
                    <div class="max-w-3xl mx-auto px-5 py-8 md:px-10 md:py-12">
                        <!-- eslint-disable svelte/no-at-html-tags -- sanitized via MarkdownRenderer on backend -->
                        <article
                            bind:this={proseEl}
                            class="docs-prose max-w-none wrap-break-word"
                            onclick={onDocClick}
                            onkeydown={(e) => {
                                if (e.key === "Enter") {
                                    onDocClick(e as unknown as MouseEvent);
                                }
                            }}
                            role="presentation"
                        >
                            {@html selectedDocContent.html || ""}
                        </article>
                        <!-- eslint-enable svelte/no-at-html-tags -->
                    </div>
                </div>
            {:else if docLoadError}
                <div class="flex-1 flex flex-col items-center justify-center p-8 text-center">
                    <MaterialDesignIcon iconName="alert-circle-outline" class="w-12 h-12 mb-4 text-red-400" />
                    <h3 class="text-sm font-semibold text-sem-fg">{t("docs.load_doc_failed")}</h3>
                    <p class="text-xs mt-2 max-w-sm text-sem-fg-muted">{docLoadError}</p>
                </div>
            {:else if meshchatxDocsCount > 0}
                <div class="flex-1 flex flex-col items-center justify-center p-8 text-center text-sem-fg-muted">
                    <MaterialDesignIcon iconName="book-open-outline" class="w-12 h-12 mb-4 opacity-40" />
                    <h3 class="text-sm font-semibold text-sem-fg">{t("docs.select_doc")}</h3>
                </div>
            {:else}
                <div class="flex-1 flex flex-col items-center justify-center p-8 text-center text-sem-fg-muted">
                    <MaterialDesignIcon iconName="alert-circle-outline" class="w-12 h-12 mb-4 opacity-40" />
                    <h3 class="text-sm font-semibold text-sem-fg">{t("docs.no_docs_found")}</h3>
                    <p class="text-xs mt-1 max-w-xs">{t("docs.no_docs_hint")}</p>
                </div>
            {/if}
        </div>

        {#if docToc.length > 0 && selectedDocContent}
            <aside
                class="hidden xl:flex flex-col w-56 shrink-0 border-l border-sem-border bg-sem-canvas/50 dark:bg-zinc-950/50"
            >
                <div class="p-4 border-b border-sem-border">
                    <h3 class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest">
                        {t("docs.on_this_page")}
                    </h3>
                </div>
                <nav class="flex-1 overflow-y-auto p-3 space-y-1 custom-scroll">
                    {#each docToc as entry (entry.id)}
                        <a
                            href="#{entry.id}"
                            class="block py-1 text-xs text-sem-fg-muted hover:text-cyan-600 dark:hover:text-cyan-400 transition-colors {entry.level ===
                            3
                                ? 'pl-3'
                                : ''}"
                            onclick={(e) => {
                                e.preventDefault();
                                onScrollToHeading(entry.id);
                            }}
                        >
                            {entry.text}
                        </a>
                    {/each}
                </nav>
            </aside>
        {/if}
    </div>
</div>

<style>
    .docs-prose {
        color: var(--mc-fg, var(--mc-text-secondary));
        font-size: 0.9375rem;
        line-height: 1.7;
    }

    .docs-prose :global(h1) {
        letter-spacing: -0.02em;
    }

    .docs-prose :global(h2 a),
    .docs-prose :global(h3 a) {
        color: inherit;
        text-decoration: none;
    }

    .docs-prose :global(pre) {
        color: #f4f4f5 !important;
    }

    .docs-prose :global(pre code) {
        color: inherit !important;
    }

    .docs-prose :global(code) {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    }

    .docs-prose :global(table) {
        width: 100%;
        border-collapse: collapse;
        margin: 1.25rem 0;
        font-size: 0.875rem;
    }

    .docs-prose :global(th),
    .docs-prose :global(td) {
        border: 1px solid var(--mc-border);
        padding: 0.5rem 0.75rem;
        text-align: left;
    }

    .docs-prose :global(th) {
        background-color: var(--mc-surface-muted);
        font-weight: 700;
    }

    .docs-prose :global(tr:nth-child(even)) {
        background-color: color-mix(in srgb, var(--mc-surface-muted) 65%, transparent);
    }

    .docs-prose :global(a) {
        color: #0369a1;
        text-decoration: underline;
        text-decoration-thickness: 1px;
        text-underline-offset: 2px;
    }

    .docs-prose :global(blockquote) {
        border-left-color: color-mix(in srgb, var(--mc-accent) 55%, transparent);
    }

    :global(.dark) .docs-prose {
        color: #e4e4e7;
    }

    :global(.dark) .docs-prose :global(p),
    :global(.dark) .docs-prose :global(li),
    :global(.dark) .docs-prose :global(td),
    :global(.dark) .docs-prose :global(th),
    :global(.dark) .docs-prose :global(strong),
    :global(.dark) .docs-prose :global(em),
    :global(.dark) .docs-prose :global(span),
    :global(.dark) .docs-prose :global(blockquote) {
        color: #e4e4e7 !important;
    }

    :global(.dark) .docs-prose :global(h1),
    :global(.dark) .docs-prose :global(h2),
    :global(.dark) .docs-prose :global(h3),
    :global(.dark) .docs-prose :global(h4) {
        color: #f4f4f5 !important;
    }

    :global(.dark) .docs-prose :global(a) {
        color: #7dd3fc !important;
    }

    :global(.dark) .docs-prose :global(h2 a),
    :global(.dark) .docs-prose :global(h3 a) {
        color: inherit !important;
        text-decoration: none;
    }
</style>
