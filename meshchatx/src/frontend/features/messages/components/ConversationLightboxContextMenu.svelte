<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { tick } from "svelte";
    import { fade } from "svelte/transition";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { clampFloatingToViewport } from "../../../js/clampFloatingToViewport.js";
    import { t } from "../../../js/i18n.js";

    let {
        show = false,
        x = 0,
        y = 0,
        ondownload,
        oncopy,
        onclose,
    }: {
        show?: boolean;
        x?: number;
        y?: number;
        ondownload?: () => void;
        oncopy?: () => void;
        onclose?: () => void;
    } = $props();

    let panel: HTMLDivElement | undefined = $state();
    let adjustedLeft = $state(0);
    let adjustedTop = $state(0);

    function isReducedMotion(): boolean {
        if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
            return false;
        }
        return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    const transitionDuration = $derived(isReducedMotion() ? 0 : 120);

    async function reposition() {
        await tick();
        if (!panel || !show) return;
        const rect = panel.getBoundingClientRect();
        const result = clampFloatingToViewport(x, y, rect.width, rect.height);
        adjustedLeft = result.left;
        adjustedTop = result.top;
    }

    $effect(() => {
        if (show) {
            adjustedLeft = x;
            adjustedTop = y;
            void reposition();
        }
    });

    $effect(() => {
        if (!show) return;
        const onDoc = () => onclose?.();
        document.addEventListener("mousedown", onDoc, true);
        return () => document.removeEventListener("mousedown", onDoc, true);
    });
</script>

{#if show}
    <div
        bind:this={panel}
        class="context-menu-panel z-200"
        style="top: {adjustedTop}px; left: {adjustedLeft}px;"
        role="menu"
        tabindex="-1"
        onclick={(e) => e.stopPropagation()}
        onkeydown={(e) => e.stopPropagation()}
        transition:fade={{ duration: transitionDuration }}
    >
        <button type="button" class="context-item" role="menuitem" onclick={() => ondownload?.()}>
            <MaterialDesignIcon iconName="download" class="size-4 text-blue-500" />
            {t("messages.save_image_to_device")}
        </button>
        <button type="button" class="context-item" role="menuitem" onclick={() => oncopy?.()}>
            <MaterialDesignIcon iconName="content-copy" class="size-4 text-blue-500" />
            {t("messages.copy_image_to_clipboard")}
        </button>
    </div>
{/if}
