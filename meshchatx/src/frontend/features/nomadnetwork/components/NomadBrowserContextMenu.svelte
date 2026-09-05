<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { tick } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { clampFloatingToViewport } from "../../../js/clampFloatingToViewport.js";
    import { t } from "../../../js/i18n.js";

    interface Props {
        show: boolean;
        x: number;
        y: number;
        justOpened?: boolean;
        hasActivePage?: boolean;
        canFavourite?: boolean;
        isFavourite?: boolean;
        canDownloadPage?: boolean;
        showTabActions?: boolean;
        canCloseTabsRight?: boolean;
        canCloseOtherTabs?: boolean;
        canCloseAllTabs?: boolean;
        contextTabIsPrivate?: boolean;
        onclose?: () => void;
        onviewsource?: () => void;
        onreload?: () => void;
        onfavorite?: () => void;
        ondownloadpage?: () => void;
        onnewprivatetab?: () => void;
        onclosetabsright?: () => void;
        oncloseothertabs?: () => void;
        onclosealltabs?: () => void;
    }

    let {
        show = false,
        x = 0,
        y = 0,
        justOpened = false,
        hasActivePage = false,
        canFavourite = false,
        isFavourite = false,
        canDownloadPage = false,
        showTabActions = false,
        canCloseTabsRight = false,
        canCloseOtherTabs = false,
        canCloseAllTabs = false,
        contextTabIsPrivate: _contextTabIsPrivate = false,
        onclose,
        onviewsource,
        onreload,
        onfavorite,
        ondownloadpage,
        onnewprivatetab,
        onclosetabsright,
        oncloseothertabs,
        onclosealltabs,
    }: Props = $props();

    let panel = $state<HTMLDivElement | null>(null);
    let adjustedLeft = $state(0);
    let adjustedTop = $state(0);

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

    function handleWindowClick(e: MouseEvent) {
        if (!show || justOpened) return;
        if (panel && !panel.contains(e.target as Node)) {
            onclose?.();
        }
    }
</script>

<svelte:window onclick={handleWindowClick} onresize={() => void reposition()} />

{#if show}
    <div
        bind:this={panel}
        class="context-menu-panel fixed z-200 min-w-48 rounded-xl shadow-xl border border-sem-border bg-sem-surface py-1 text-sem-fg"
        style="left: {adjustedLeft}px; top: {adjustedTop}px;"
        role="menu"
        tabindex="-1"
    >
        <button
            type="button"
            class="context-item flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-sem-surface-muted disabled:pointer-events-none disabled:opacity-40"
            disabled={!hasActivePage}
            onclick={() => {
                onclose?.();
                onviewsource?.();
            }}
        >
            <MaterialDesignIcon iconName="code-tags" class="size-5 shrink-0" />
            <span>{t("app.toggle_source")}</span>
        </button>

        <button
            type="button"
            class="context-item flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-sem-surface-muted disabled:pointer-events-none disabled:opacity-40"
            disabled={!hasActivePage}
            onclick={() => {
                onclose?.();
                onreload?.();
            }}
        >
            <MaterialDesignIcon iconName="refresh" class="size-5 shrink-0" />
            <span>{t("common.refresh")}</span>
        </button>

        <button
            type="button"
            class="context-item flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-sem-surface-muted disabled:pointer-events-none disabled:opacity-40"
            disabled={!canFavourite}
            onclick={() => {
                onclose?.();
                onfavorite?.();
            }}
        >
            <MaterialDesignIcon iconName={isFavourite ? "star-off" : "star"} class="size-5 shrink-0" />
            <span>{isFavourite ? t("nomadnet.remove_favourite") : t("nomadnet.add_favourite")}</span>
        </button>

        <button
            type="button"
            class="context-item flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-sem-surface-muted disabled:pointer-events-none disabled:opacity-40"
            disabled={!canDownloadPage}
            onclick={() => {
                onclose?.();
                ondownloadpage?.();
            }}
        >
            <MaterialDesignIcon iconName="download" class="size-5 shrink-0" />
            <span>{t("nomadnet.download_page")}</span>
        </button>

        {#if showTabActions}
            <div class="context-menu-divider my-1 h-px bg-sem-border"></div>
            <div
                class="context-menu-section-label px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-sem-fg-muted"
            >
                {t("nomadnet.context_tabs")}
            </div>

            <button
                type="button"
                class="context-item flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-sem-surface-muted"
                onclick={() => {
                    onclose?.();
                    onnewprivatetab?.();
                }}
            >
                <MaterialDesignIcon iconName="incognito" class="size-5 shrink-0 text-purple-400" />
                <span>{t("nomadnet.new_private_tab")}</span>
            </button>

            <button
                type="button"
                class="context-item flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-sem-surface-muted disabled:pointer-events-none disabled:opacity-40"
                disabled={!canCloseTabsRight}
                onclick={() => {
                    onclose?.();
                    onclosetabsright?.();
                }}
            >
                <MaterialDesignIcon iconName="tab-remove" class="size-5 shrink-0" />
                <span>{t("nomadnet.close_tabs_to_right")}</span>
            </button>

            <button
                type="button"
                class="context-item flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-sem-surface-muted disabled:pointer-events-none disabled:opacity-40"
                disabled={!canCloseOtherTabs}
                onclick={() => {
                    onclose?.();
                    oncloseothertabs?.();
                }}
            >
                <MaterialDesignIcon iconName="tab-minus" class="size-5 shrink-0" />
                <span>{t("nomadnet.close_other_tabs")}</span>
            </button>

            <button
                type="button"
                class="context-item flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-sem-surface-muted disabled:pointer-events-none disabled:opacity-40"
                disabled={!canCloseAllTabs}
                onclick={() => {
                    onclose?.();
                    onclosealltabs?.();
                }}
            >
                <MaterialDesignIcon iconName="close-box-multiple-outline" class="size-5 shrink-0" />
                <span>{t("nomadnet.close_all_tabs")}</span>
            </button>
        {/if}
    </div>
{/if}
