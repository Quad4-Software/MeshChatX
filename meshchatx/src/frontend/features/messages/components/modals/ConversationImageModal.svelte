<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { fade } from "svelte/transition";
    import MaterialDesignIcon from "../../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../../js/i18n.js";

    let {
        url = "",
        gallery = null as string[] | null,
        index = 0,
        onclose,
        onnavigate,
        ondownload,
        oncontextmenu,
    }: {
        url?: string;
        gallery?: string[] | null;
        index?: number;
        onclose?: () => void;
        onnavigate?: (delta: number) => void;
        ondownload?: () => void;
        oncontextmenu?: (event: MouseEvent) => void;
    } = $props();

    let overlay: HTMLDivElement | undefined = $state();

    const hasGallery = $derived(Array.isArray(gallery) && gallery.length > 1);

    $effect(() => {
        if (url && overlay) {
            overlay.focus?.();
        }
    });

    function onKeydown(event: KeyboardEvent) {
        if (event.key === "ArrowLeft") {
            event.preventDefault();
            onnavigate?.(-1);
        } else if (event.key === "ArrowRight") {
            event.preventDefault();
            onnavigate?.(1);
        } else if (event.key === "Escape") {
            event.preventDefault();
            onclose?.();
        }
    }
</script>

{#if url}
    <div
        bind:this={overlay}
        tabindex="0"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 dark:bg-black/90 backdrop-blur-xs p-4 pt-[max(1rem,env(safe-area-inset-top))] pb-[max(1rem,env(safe-area-inset-bottom))] outline-hidden"
        transition:fade={{ duration: 150 }}
        onclick={() => onclose?.()}
        onkeydown={onKeydown}
        role="dialog"
        aria-modal="true"
    >
        <div
            class="relative max-w-7xl max-h-full group/image-modal"
            onclick={(e) => e.stopPropagation()}
            onkeydown={(e) => e.stopPropagation()}
            role="presentation"
        >
            <button
                type="button"
                class="absolute -top-12 left-0 inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/10 dark:bg-zinc-900/10 hover:bg-white/20 dark:hover:bg-zinc-900/20 text-white transition-colors opacity-0 group-hover/image-modal:opacity-100 focus:opacity-100"
                title={t("messages.save_image_to_device")}
                onclick={() => ondownload?.()}
            >
                <MaterialDesignIcon iconName="download" class="size-5" />
            </button>
            <button
                type="button"
                class="absolute -top-12 right-0 inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/10 dark:bg-zinc-900/10 hover:bg-white/20 dark:hover:bg-zinc-900/20 text-white transition-colors"
                onclick={() => onclose?.()}
            >
                <MaterialDesignIcon iconName="close" class="size-5" />
            </button>
            {#if hasGallery}
                <button
                    type="button"
                    class="absolute left-0 top-1/2 z-10 -translate-y-1/2 inline-flex items-center justify-center w-11 h-11 rounded-full bg-black/40 hover:bg-black/55 text-white transition-colors"
                    aria-label="Previous image"
                    onclick={(e) => {
                        e.stopPropagation();
                        onnavigate?.(-1);
                    }}
                >
                    <MaterialDesignIcon iconName="chevron-left" class="size-7" />
                </button>
                <button
                    type="button"
                    class="absolute right-0 top-1/2 z-10 -translate-y-1/2 inline-flex items-center justify-center w-11 h-11 rounded-full bg-black/40 hover:bg-black/55 text-white transition-colors"
                    aria-label="Next image"
                    onclick={(e) => {
                        e.stopPropagation();
                        onnavigate?.(1);
                    }}
                >
                    <MaterialDesignIcon iconName="chevron-right" class="size-7" />
                </button>
                <div
                    class="pointer-events-none absolute bottom-2 left-1/2 z-10 -translate-x-1/2 rounded-full bg-black/50 px-3 py-1 text-xs font-medium text-white"
                >
                    {index + 1} / {gallery!.length}
                </div>
            {/if}
            <img
                src={url}
                class="max-w-full max-h-[90vh] rounded-xl shadow-2xl"
                alt=""
                oncontextmenu={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    oncontextmenu?.(e);
                }}
            />
        </div>
    </div>
{/if}
