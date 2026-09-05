<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { DEFAULT_COLOR_SWATCHES, normalizeHexColour } from "../lib/profileIcon.js";

    interface Props {
        colour?: string;
        onchange?: (colour: string) => void;
    }

    let { colour = $bindable(""), onchange }: Props = $props();

    let isShowingMenu = $state(false);
    let rootEl: HTMLDivElement | null = $state(null);

    const normalizedColour = $derived(normalizeHexColour(colour) || "#3b82f6");

    function toggleMenu(): void {
        isShowingMenu = !isShowingMenu;
    }

    function onNativeColorInput(event: Event): void {
        const target = event.target as HTMLInputElement | null;
        const val = target?.value;
        if (typeof val === "string" && val) {
            const hex = normalizeHexColour(val);
            colour = hex;
            onchange?.(hex);
        }
    }

    function selectSwatch(swatch: string): void {
        const hex = normalizeHexColour(swatch);
        colour = hex;
        onchange?.(hex);
        isShowingMenu = false;
    }

    $effect(() => {
        if (!isShowingMenu) return;
        const onDocMouseDown = (event: MouseEvent) => {
            if (rootEl && !rootEl.contains(event.target as Node)) {
                isShowingMenu = false;
            }
        };
        document.addEventListener("mousedown", onDocMouseDown, true);
        return () => document.removeEventListener("mousedown", onDocMouseDown, true);
    });
</script>

<div bind:this={rootEl} class="cursor-default relative inline-block text-left">
    <!-- Menu button trigger -->
    <button
        type="button"
        class="block p-0 border-0 bg-transparent cursor-pointer rounded-sm focus-ring-sem"
        onclick={toggleMenu}
        aria-label="Pick color"
        aria-expanded={isShowingMenu}
    >
        <div
            class="size-8 border border-gray-300 dark:border-zinc-700 rounded-sm shadow-xs"
            style="background-color: {colour};"
        ></div>
    </button>

    {#if isShowingMenu}
        <div
            class="absolute left-0 z-100 mt-2 rounded-xl border border-gray-200 bg-white p-3 shadow-xl dark:border-zinc-700 dark:bg-zinc-900"
        >
            <input
                value={normalizedColour}
                type="color"
                class="block h-10 w-full cursor-pointer rounded-lg border border-gray-200 bg-transparent p-0 dark:border-zinc-700"
                oninput={onNativeColorInput}
            />
            <div class="mt-2 grid grid-cols-6 gap-1.5">
                {#each DEFAULT_COLOR_SWATCHES as swatch (swatch)}
                    <button
                        type="button"
                        class="size-6 rounded-md border border-sem-border hover:scale-105 transition-transform"
                        style="background-color: {swatch};"
                        title={swatch}
                        aria-label={swatch}
                        onclick={() => selectSwatch(swatch)}
                    ></button>
                {/each}
            </div>
        </div>
    {/if}
</div>
