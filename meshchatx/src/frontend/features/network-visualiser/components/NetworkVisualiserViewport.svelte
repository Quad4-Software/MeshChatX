<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import type { RendererMode } from "../lib/types.js";

    interface Props {
        networkContainer?: HTMLDivElement | null;
        webglCanvas?: HTMLCanvasElement | null;
        rendererMode?: RendererMode;
        hoverTooltip?: { text: string; x: number; y: number } | null;
    }

    let {
        networkContainer = $bindable(null),
        webglCanvas = $bindable(null),
        rendererMode = "vis",
        hoverTooltip = null,
    }: Props = $props();
</script>

<div
    bind:this={networkContainer}
    id="network"
    class="absolute inset-0 w-full h-full min-h-0 {rendererMode === 'webgl' ? 'hidden' : ''}"
></div>

<canvas
    bind:this={webglCanvas}
    id="network-webgl"
    class="absolute inset-0 w-full h-full min-h-0 {rendererMode !== 'webgl' ? 'hidden' : ''}"
></canvas>

{#if rendererMode === "webgl" && hoverTooltip}
    <div
        class="pointer-events-none absolute z-20 max-w-xs rounded-xl border border-zinc-600/50 bg-zinc-950/90 px-3 py-2 text-xs font-medium text-zinc-100 shadow-lg whitespace-pre-line"
        style="left: {hoverTooltip.x + 12}px; top: {hoverTooltip.y + 12}px;"
    >
        {hoverTooltip.text}
    </div>
{/if}
