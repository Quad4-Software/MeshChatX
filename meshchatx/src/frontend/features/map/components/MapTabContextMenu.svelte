<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script lang="ts">
    import { tick } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { clampFloatingToViewport } from "../../../js/clampFloatingToViewport.js";
    import { t } from "../../../js/i18n.js";

    interface Props {
        show?: boolean;
        x?: number;
        y?: number;
        justOpened?: boolean;
        canCloseRight?: boolean;
        canCloseOthers?: boolean;
        canCloseAll?: boolean;
        onclose?: () => void;
        onrename?: () => void;
        onnewtab?: () => void;
        onclosetab?: () => void;
        oncloseright?: () => void;
        oncloseothers?: () => void;
        oncloseall?: () => void;
    }

    let {
        show = false,
        x = 0,
        y = 0,
        justOpened = false,
        canCloseRight = false,
        canCloseOthers = false,
        canCloseAll = false,
        onclose,
        onrename,
        onnewtab,
        onclosetab,
        oncloseright,
        oncloseothers,
        oncloseall,
    }: Props = $props();

    let panelEl = $state<HTMLDivElement | null>(null);
    let position = $state<{ left: number; top: number }>({ left: 0, top: 0 });

    async function reposition(): Promise<void> {
        if (!show || !panelEl) return;
        await tick();
        if (!panelEl) return;
        const clamped = clampFloatingToViewport(x, y, panelEl.offsetWidth, panelEl.offsetHeight, { margin: 8 });
        position = { left: clamped.left, top: clamped.top };
    }

    $effect(() => {
        if (show && x !== undefined && y !== undefined) {
            void reposition();
        }
    });

    function handleWindowClick(e: MouseEvent): void {
        if (!show || justOpened) return;
        if (panelEl && !panelEl.contains(e.target as Node)) {
            onclose?.();
        }
    }

    function handleWindowKeydown(e: KeyboardEvent): void {
        if (show && e.key === "Escape") {
            onclose?.();
        }
    }
</script>

<svelte:window onclick={handleWindowClick} onkeydown={handleWindowKeydown} />

{#if show}
    <div
        bind:this={panelEl}
        role="menu"
        tabindex="-1"
        class="context-menu-panel fixed z-120 overflow-hidden text-sm min-w-48 rounded-xl shadow-xl border border-sem-border bg-sem-surface text-sem-fg py-1"
        style="left: {position.left}px; top: {position.top}px;"
    >
        <button
            type="button"
            role="menuitem"
            class="context-item w-full flex items-center gap-2 px-3 py-2 hover:bg-sem-surface-muted text-left cursor-pointer transition-colors"
            onclick={onrename}
        >
            <MaterialDesignIcon iconName="pencil-outline" class="size-5" />
            <span>{t("common.rename")}</span>
        </button>
        <button
            type="button"
            role="menuitem"
            class="context-item w-full flex items-center gap-2 px-3 py-2 hover:bg-sem-surface-muted text-left cursor-pointer transition-colors"
            onclick={onnewtab}
        >
            <MaterialDesignIcon iconName="plus" class="size-5" />
            <span>{t("map.new_tab")}</span>
        </button>
        <div class="context-menu-divider border-t border-sem-border my-1" role="separator"></div>
        <button
            type="button"
            role="menuitem"
            class="context-item w-full flex items-center gap-2 px-3 py-2 hover:bg-sem-surface-muted text-left cursor-pointer transition-colors"
            onclick={onclosetab}
        >
            <MaterialDesignIcon iconName="close" class="size-5" />
            <span>{t("common.close")}</span>
        </button>
        <button
            type="button"
            role="menuitem"
            disabled={!canCloseRight}
            class="context-item w-full flex items-center gap-2 px-3 py-2 hover:bg-sem-surface-muted text-left cursor-pointer transition-colors disabled:opacity-40"
            onclick={oncloseright}
        >
            <MaterialDesignIcon iconName="tab-remove" class="size-5" />
            <span>{t("map.close_tabs_to_right")}</span>
        </button>
        <button
            type="button"
            role="menuitem"
            disabled={!canCloseOthers}
            class="context-item w-full flex items-center gap-2 px-3 py-2 hover:bg-sem-surface-muted text-left cursor-pointer transition-colors disabled:opacity-40"
            onclick={oncloseothers}
        >
            <MaterialDesignIcon iconName="tab-minus" class="size-5" />
            <span>{t("map.close_other_tabs")}</span>
        </button>
        <button
            type="button"
            role="menuitem"
            disabled={!canCloseAll}
            class="context-item w-full flex items-center gap-2 px-3 py-2 hover:bg-sem-surface-muted text-left cursor-pointer transition-colors disabled:opacity-40"
            onclick={oncloseall}
        >
            <MaterialDesignIcon iconName="close-box-multiple-outline" class="size-5" />
            <span>{t("map.close_all_tabs")}</span>
        </button>
    </div>
{/if}
