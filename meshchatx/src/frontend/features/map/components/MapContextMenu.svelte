<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { tick } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { clampFloatingToViewport } from "../../../js/clampFloatingToViewport.js";
    import { t } from "../../../js/i18n.js";

    interface CoordRow {
        format: string;
        label: string;
        text: string;
    }

    interface Props {
        show?: boolean;
        x?: number;
        y?: number;
        contextMenuFeature?: any;
        isEditable?: boolean;
        contextMenuCoordRows?: CoordRow[];
        onselectfeature?: () => void;
        oneditfeature?: () => void;
        onaddnote?: () => void;
        ondeletefeature?: () => void;
        oncopycoords?: () => void;
        onpinghere?: () => void;
        onclearmap?: () => void;
        oncopycoordformat?: (format: string) => void;
        onclose?: () => void;
    }

    let {
        show = false,
        x = 0,
        y = 0,
        contextMenuFeature = null,
        isEditable = false,
        contextMenuCoordRows = [],
        onselectfeature,
        oneditfeature,
        onaddnote,
        ondeletefeature,
        oncopycoords,
        onpinghere,
        onclearmap,
        oncopycoordformat,
        onclose,
    }: Props = $props();

    let panelEl = $state<HTMLDivElement | null>(null);
    let position = $state<{ left: number; top: number }>({ left: 0, top: 0 });

    async function reposition() {
        if (!show || !panelEl) return;
        await tick();
        if (!panelEl) return;
        const clamped = clampFloatingToViewport(x, y, panelEl.offsetWidth, panelEl.offsetHeight, { margin: 8 });
        position = { left: clamped.left, top: clamped.top };
    }

    $effect(() => {
        if (show && x !== undefined && y !== undefined) {
            reposition();
        }
    });

    function handleWindowClick(e: MouseEvent) {
        if (!show) return;
        if (panelEl && !panelEl.contains(e.target as Node)) {
            onclose?.();
        }
    }
</script>

<svelte:window onclick={handleWindowClick} />

{#if show}
    <div
        bind:this={panelEl}
        role="menu"
        tabindex="-1"
        class="context-menu-panel fixed z-120 overflow-hidden text-sm min-w-48 rounded-xl shadow-xl border border-sem-border bg-sem-surface text-sem-fg"
        style="left: {position.left}px; top: {position.top}px;"
    >
        <div
            class="px-3 py-2 font-semibold border-b border-sem-border text-sem-fg-muted text-xs uppercase tracking-wider"
        >
            {contextMenuFeature ? "Feature actions" : "Map actions"}
        </div>

        {#if contextMenuFeature && isEditable}
            <button
                type="button"
                role="menuitem"
                class="context-item w-full flex items-center gap-2 px-3 py-2 hover:bg-sem-surface-muted text-left cursor-pointer transition-colors"
                onclick={() => {
                    onselectfeature?.();
                    onclose?.();
                }}
            >
                <MaterialDesignIcon iconName="cursor-default" class="size-4" />
                <span>Select / Move</span>
            </button>
            <button
                type="button"
                role="menuitem"
                class="context-item w-full flex items-center gap-2 px-3 py-2 hover:bg-sem-surface-muted text-left cursor-pointer transition-colors"
                onclick={() => {
                    oneditfeature?.();
                    onclose?.();
                }}
            >
                <MaterialDesignIcon iconName="pencil" class="size-4" />
                <span>{t("map.feature_edit")}</span>
            </button>
            <button
                type="button"
                role="menuitem"
                class="context-item w-full flex items-center gap-2 px-3 py-2 hover:bg-sem-surface-muted text-left cursor-pointer transition-colors"
                onclick={() => {
                    onaddnote?.();
                    onclose?.();
                }}
            >
                <MaterialDesignIcon iconName="note-edit" class="size-4" />
                <span>Add / Edit Note</span>
            </button>
            <button
                type="button"
                role="menuitem"
                class="context-item w-full flex items-center gap-2 px-3 py-2 hover:bg-sem-surface-muted text-left cursor-pointer transition-colors text-red-600 dark:text-red-400"
                onclick={() => {
                    ondeletefeature?.();
                    onclose?.();
                }}
            >
                <MaterialDesignIcon iconName="delete" class="size-4" />
                <span>Delete</span>
            </button>
        {/if}

        <button
            type="button"
            role="menuitem"
            class="context-item w-full flex items-center gap-2 px-3 py-2 hover:bg-sem-surface-muted text-left cursor-pointer transition-colors"
            onclick={() => {
                oncopycoords?.();
                onclose?.();
            }}
        >
            <MaterialDesignIcon iconName="crosshairs-gps" class="size-4" />
            <span>{t("map.copy_coords")}</span>
        </button>

        <button
            type="button"
            role="menuitem"
            class="context-item w-full flex items-center gap-2 px-3 py-2 hover:bg-sem-surface-muted text-left cursor-pointer transition-colors"
            onclick={() => {
                onpinghere?.();
                onclose?.();
            }}
        >
            <MaterialDesignIcon iconName="send" class="size-4" />
            <span>{t("map.ping_here")}</span>
        </button>

        {#if !contextMenuFeature}
            <button
                type="button"
                role="menuitem"
                class="context-item w-full flex items-center gap-2 px-3 py-2 hover:bg-sem-surface-muted text-left cursor-pointer transition-colors"
                onclick={() => {
                    onclearmap?.();
                    onclose?.();
                }}
            >
                <MaterialDesignIcon iconName="delete-sweep" class="size-4" />
                <span>Clear drawings</span>
            </button>
        {/if}

        <div class="context-menu-divider border-t border-sem-border my-1"></div>

        <div class="px-3 py-2 space-y-1 max-w-[18rem]">
            <div
                class="context-menu-section-label text-[10px] font-bold uppercase tracking-wider text-sem-fg-muted mb-1"
            >
                {t("map.context_coords")}
            </div>
            {#each contextMenuCoordRows as row (row.format)}
                <button
                    type="button"
                    class="w-full text-left rounded-md px-1.5 py-1 hover:bg-sem-surface-muted transition-colors cursor-pointer"
                    title={t("map.copy_coords_format", { format: row.label })}
                    onclick={() => {
                        oncopycoordformat?.(row.format);
                        onclose?.();
                    }}
                >
                    <div class="text-[9px] uppercase tracking-wider text-sem-fg-muted">{row.label}</div>
                    <div class="text-[11px] font-mono text-sem-fg tabular-nums break-all leading-snug">
                        {row.text || "…"}
                    </div>
                </button>
            {/each}
        </div>
    </div>
{/if}
