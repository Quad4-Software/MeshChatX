<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { tick } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { clampFloatingToViewport } from "../../../js/clampFloatingToViewport.js";
    import { t } from "../../../js/i18n.js";
    import { ENGINE_VALUES } from "../lib/constants.js";
    import type { EngineMode, PreferredRenderer } from "../lib/types.js";

    interface Props {
        preferredRenderer?: PreferredRenderer;
        engineMode?: EngineMode;
        onupdatepreferredrenderer?: (val: PreferredRenderer) => void;
    }

    let { preferredRenderer = "auto", engineMode = "checking", onupdatepreferredrenderer }: Props = $props();

    let engineMenuOpen = $state(false);
    let engineMenuPosition = $state<{ left: number; top: number; maxHeight?: number | null } | null>(null);
    let engineMenuPanel = $state<HTMLDivElement | null>(null);

    let engineOptions = $derived([
        { value: "auto" as const, label: t("visualiser.renderer_option_auto") },
        { value: "webgl" as const, label: t("visualiser.renderer_option_webgl") },
        { value: "vis" as const, label: t("visualiser.renderer_option_vis") },
    ]);

    let engineTriggerLabel = $derived.by(() => {
        if (preferredRenderer === "webgl") return t("visualiser.renderer_option_webgl_short");
        if (preferredRenderer === "vis") return t("visualiser.renderer_option_vis_short");
        return t("visualiser.renderer_option_auto_short");
    });

    let engineSelectTitle = $derived.by(() => {
        if (engineMode === "webgl") return t("visualiser.engine_webgl_hint");
        if (engineMode === "wasm") return t("visualiser.engine_wasm_hint");
        if (engineMode === "fallback") return t("visualiser.engine_fallback_hint");
        return t("visualiser.renderer_desc");
    });

    let engineSelectClass = $derived.by(() => {
        if (engineMode === "webgl") return "text-sky-600 dark:text-sky-400";
        if (engineMode === "wasm") return "text-emerald-600 dark:text-emerald-400";
        if (engineMode === "fallback") return "text-amber-600 dark:text-amber-400";
        return "text-sem-fg";
    });

    function toggleEngineMenu() {
        if (engineMenuOpen) {
            closeEngineMenu();
        } else {
            openEngineMenu();
        }
    }

    async function openEngineMenu() {
        engineMenuOpen = true;
        await tick();
        positionEngineMenu();
    }

    function closeEngineMenu() {
        engineMenuOpen = false;
        engineMenuPosition = null;
    }

    async function positionEngineMenu() {
        if (typeof document === "undefined") return;
        const trigger = document.getElementById("visualiser-engine-select");
        if (!trigger) return;
        const rect = trigger.getBoundingClientRect();
        engineMenuPosition = {
            left: Math.max(8, rect.left),
            top: rect.bottom + 6,
            maxHeight: null,
        };
        await tick();
        if (!engineMenuPanel) return;
        const pr = engineMenuPanel.getBoundingClientRect();
        const { left, top, maxHeight } = clampFloatingToViewport(pr.left, pr.top, pr.width, pr.height);
        engineMenuPosition = { left, top, maxHeight };
    }

    function selectEngine(value: PreferredRenderer) {
        if (ENGINE_VALUES.includes(value)) {
            onupdatepreferredrenderer?.(value);
        }
        closeEngineMenu();
    }

    function handleWindowClick(e: MouseEvent) {
        if (!engineMenuOpen) return;
        const target = e.target as HTMLElement | null;
        if (target?.closest("#visualiser-engine-select") || target?.closest("#visualiser-engine-menu")) {
            return;
        }
        closeEngineMenu();
    }
</script>

<svelte:window onclick={handleWindowClick} />

<div
    class="relative min-w-0 rounded-xl px-3 py-2 border border-gray-100 dark:border-zinc-700/50 bg-gray-50/60 dark:bg-zinc-800/40"
    title={engineSelectTitle}
>
    <div class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-wider mb-0.5">
        {t("visualiser.engine")}
    </div>
    <button
        id="visualiser-engine-select"
        type="button"
        class="flex w-full min-w-0 items-center gap-1 bg-transparent text-left text-xs font-bold focus:outline-hidden focus-visible:ring-1 focus-visible:ring-blue-500/50 rounded {engineSelectClass}"
        aria-label={t("visualiser.engine")}
        aria-expanded={engineMenuOpen ? "true" : "false"}
        aria-haspopup="listbox"
        onclick={(e) => {
            e.stopPropagation();
            toggleEngineMenu();
        }}
    >
        <span class="min-w-0 flex-1 truncate">{engineTriggerLabel}</span>
        <MaterialDesignIcon
            iconName="chevron-down"
            class="w-3.5 h-3.5 shrink-0 text-gray-400 transition-transform duration-200 {engineMenuOpen
                ? 'rotate-180'
                : ''}"
        />
    </button>
    {#if engineMenuOpen && engineMenuPosition}
        <div
            id="visualiser-engine-menu"
            bind:this={engineMenuPanel}
            class="fixed z-200 w-56 overflow-hidden rounded-xl border border-sem-border bg-sem-surface shadow-lg"
            style="left: {engineMenuPosition.left}px; top: {engineMenuPosition.top}px; {engineMenuPosition.maxHeight !=
            null
                ? `max-height: ${engineMenuPosition.maxHeight}px; overflow-y: auto;`
                : ''}"
            role="listbox"
            aria-label={t("visualiser.engine")}
        >
            {#each engineOptions as opt (opt.value)}
                <button
                    type="button"
                    role="option"
                    class="flex w-full items-center justify-between gap-2 px-3 py-2.5 text-left text-xs font-semibold transition-colors hover:bg-sem-surface-muted {preferredRenderer ===
                    opt.value
                        ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300'
                        : 'text-sem-fg'}"
                    aria-selected={preferredRenderer === opt.value ? "true" : "false"}
                    onclick={(e) => {
                        e.stopPropagation();
                        selectEngine(opt.value);
                    }}
                >
                    <span class="min-w-0 flex-1">{opt.label}</span>
                    {#if preferredRenderer === opt.value}
                        <MaterialDesignIcon iconName="check" class="w-4 h-4 shrink-0" />
                    {/if}
                </button>
            {/each}
        </div>
    {/if}
</div>
