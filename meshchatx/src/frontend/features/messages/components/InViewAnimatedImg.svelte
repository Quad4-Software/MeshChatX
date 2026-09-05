<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { attachInView } from "../../../js/inViewObserver.js";

    let {
        src,
        imgClass = "",
        fitParent = false,
        alt = "",
        loading = "lazy" as "eager" | "lazy",
        decoding = "async" as "async" | "sync" | "auto",
        onclick,
    }: {
        src: string;
        imgClass?: string;
        fitParent?: boolean;
        alt?: string;
        loading?: "eager" | "lazy";
        decoding?: "async" | "sync" | "auto";
        onclick?: (event: MouseEvent) => void;
    } = $props();

    let wrap: HTMLDivElement | undefined = $state();
    let show = $state(false);

    const wrapClass = $derived(fitParent ? "absolute inset-0 overflow-hidden" : "relative w-full");
    const placeholderClass = $derived(
        fitParent
            ? "absolute inset-0 bg-zinc-200/30 dark:bg-white/10"
            : "min-h-32 w-full rounded-2xl bg-gray-100/90 dark:bg-zinc-800/60"
    );

    $effect(() => {
        const el = wrap;
        if (!el) {
            return;
        }
        const cleanup = attachInView(el, (entry: IntersectionObserverEntry) => {
            if (entry.isIntersecting) {
                show = true;
            }
        });
        return () => {
            cleanup?.();
        };
    });
</script>

<div bind:this={wrap} class={wrapClass}>
    {#if show}
        {#if onclick}
            <button type="button" class="block w-full p-0 border-0 bg-transparent cursor-pointer" {onclick}>
                <img {src} {loading} {decoding} class={imgClass} {alt} draggable="false" />
            </button>
        {:else}
            <img {src} {loading} {decoding} class={imgClass} {alt} draggable="false" />
        {/if}
    {:else}
        <div class={placeholderClass} aria-hidden="true"></div>
    {/if}
</div>
