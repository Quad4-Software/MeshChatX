<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { handleRichHtmlLinkClick } from "../../../js/NomadRichHtmlLinks.js";

    interface Props {
        renderedContent: string;
        isMobileView: boolean;
        showEditor: boolean;
        onNomadDestination: (destination: string) => void;
    }

    let { renderedContent, isMobileView, showEditor, onNomadDestination }: Props = $props();

    let previewRef = $state<HTMLElement | null>(null);

    export function onPreviewClick(event: MouseEvent): void {
        handleRichHtmlLinkClick(event, {
            scrollRoot: previewRef,
            onNomadUrl: (url) => onNomadDestination(url),
            onOpenNode: (destination) => onNomadDestination(destination),
        });
    }
</script>

<div class="flex-1 overflow-hidden flex flex-col bg-zinc-950 {isMobileView && showEditor ? 'hidden' : ''}">
    <!-- eslint-disable svelte/no-at-html-tags -- sanitized via convertMicronToHtml on client -->
    <div
        bind:this={previewRef}
        class="flex-1 overflow-auto text-zinc-100 p-4 font-mono text-sm whitespace-pre-wrap wrap-break-word nodeContainer"
        onclick={onPreviewClick}
        onkeydown={(e) => {
            if (e.key === "Enter") {
                onPreviewClick(e as unknown as MouseEvent);
            }
        }}
        role="presentation"
    >
        {@html renderedContent}
    </div>
    <!-- eslint-enable svelte/no-at-html-tags -->
</div>

<style>
    .nodeContainer {
        font-family: "Roboto Mono Nerd Font", ui-monospace, monospace;
        line-height: normal;
        letter-spacing: normal;
        font-variant-ligatures: none;
        font-feature-settings: normal;
    }

    .nodeContainer :global(.Mu-nl) {
        cursor: pointer;
        text-decoration: none;
    }
    .nodeContainer :global(.Mu-mnt) {
        display: inline-block;
        box-sizing: border-box;
        min-width: 1ch;
        width: 1ch;
        max-width: 1ch;
        text-align: center;
        white-space: pre;
        text-decoration: inherit;
        vertical-align: baseline;
        line-height: 1.25;
    }
    .nodeContainer :global(.Mu-mnt-full) {
        display: inline-block;
        box-sizing: border-box;
        min-width: 2ch;
        width: 2ch;
        max-width: 2ch;
        text-align: center;
        white-space: pre;
        text-decoration: inherit;
        vertical-align: baseline;
        line-height: 1.25;
    }
    .nodeContainer :global(.Mu-mws) {
        text-decoration: inherit;
        display: inline-flex;
        flex-wrap: wrap;
        align-items: baseline;
        column-gap: 0;
        row-gap: 0;
        gap: 0;
    }

    .nodeContainer :global(a.Mu-nl),
    .nodeContainer :global(a.nomadnet-link) {
        cursor: pointer;
        text-decoration: none;
        color: inherit;
    }
</style>
