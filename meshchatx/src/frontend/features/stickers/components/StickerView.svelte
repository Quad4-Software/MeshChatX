<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { attachInView } from "../../../js/inViewObserver.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";

    interface Props {
        src: string;
        imageType?: string;
        alt?: string;
        size?: "auto" | "xs" | "sm" | "md" | "lg" | string;
        class?: string;
        onerror?: (event: Event) => void;
    }

    let { src, imageType = "", alt = "", size = "auto", class: className = "", onerror }: Props = $props();

    let stickerRoot = $state<HTMLDivElement | null>(null);
    let videoEl = $state<HTMLVideoElement | null>(null);
    let inView = $state(false);
    let ioCleanup: (() => void) | null = null;

    let isVideo = $derived((imageType || "").toLowerCase() === "webm");
    let isAnimated = $derived((imageType || "").toLowerCase() === "tgs");
    let sizeClass = $derived(`sticker-view--${size}`);

    function syncVideoPlayback(): void {
        if (!videoEl || !isVideo) {
            return;
        }
        if (inView) {
            try {
                const res = videoEl.play?.();
                if (res && typeof res.catch === "function") {
                    res.catch(() => {});
                }
            } catch {
                // Ignore playback failure
            }
        } else {
            try {
                videoEl.pause?.();
            } catch {
                // Ignore pause failure
            }
        }
    }

    $effect(() => {
        if (isVideo) {
            const _inView = inView;
            const _src = src;
            const _videoEl = videoEl;
            syncVideoPlayback();
        }
    });

    onMount(() => {
        if (stickerRoot) {
            ioCleanup = attachInView(stickerRoot, (entry) => {
                inView = entry.isIntersecting;
            });
        }
    });

    onDestroy(() => {
        if (ioCleanup) {
            ioCleanup();
            ioCleanup = null;
        }
    });
</script>

<div bind:this={stickerRoot} class="sticker-view {sizeClass} {className}">
    {#if isVideo}
        <video bind:this={videoEl} {src} class="sticker-media" loop muted playsinline onerror={(e) => onerror?.(e)}
        ></video>
    {:else if isAnimated}
        <div
            class="w-full h-full flex items-center justify-center bg-gray-200/80 dark:bg-zinc-700/50 text-sem-fg-muted"
            title={alt || "TGS"}
            aria-label={alt || "Animated sticker"}
        >
            <MaterialDesignIcon iconName="animation-outline" class="w-[42%] h-[42%] opacity-70" />
        </div>
    {:else}
        <img
            {src}
            class="sticker-media"
            decoding="async"
            loading="lazy"
            alt={alt || ""}
            onerror={(e) => onerror?.(e)}
        />
    {/if}
</div>

<style>
    .sticker-view {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        line-height: 0;
    }
    .sticker-view--auto {
        width: 100%;
        height: 100%;
    }
    .sticker-view--xs {
        width: 32px;
        height: 32px;
    }
    .sticker-view--sm {
        width: 56px;
        height: 56px;
    }
    .sticker-view--md {
        width: 96px;
        height: 96px;
    }
    .sticker-view--lg {
        width: 192px;
        height: 192px;
    }
    .sticker-media {
        width: 100%;
        height: 100%;
        object-fit: contain;
        display: block;
    }
</style>
