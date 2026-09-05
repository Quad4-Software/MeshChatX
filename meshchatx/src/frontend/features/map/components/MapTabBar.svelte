<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import type { MapTab } from "../lib/types.js";

    interface Props {
        tabs: MapTab[];
        activeTabId: number | null;
        renamingTabId: number | null;
        renameDraft: string;
        canAddTab: boolean;
        renameInputEl?: HTMLInputElement | null;
        tabTitle: (tab: MapTab) => string;
        onselect: (id: number) => void;
        onstartrename: (id: number) => void;
        oncommitrename: () => void;
        oncancelrename: () => void;
        ontablabeltouchend: (tab: MapTab, event: TouchEvent) => void;
        onclosetab: (id: number) => void;
        onaddtab: () => void;
    }

    let {
        tabs,
        activeTabId,
        renamingTabId,
        renameDraft = $bindable(""),
        canAddTab,
        renameInputEl = $bindable(null),
        tabTitle,
        onselect,
        onstartrename,
        oncommitrename,
        oncancelrename,
        ontablabeltouchend,
        onclosetab,
        onaddtab,
    }: Props = $props();
</script>

<div
    class="flex min-h-9 md:min-h-8 shrink-0 items-center gap-1 overflow-x-auto border-b border-sem-border bg-sem-surface-muted px-1.5 py-0.5 md:py-0.5"
    role="tablist"
>
    {#each tabs as tab (tab.id)}
        <div
            role="tab"
            tabindex="0"
            aria-selected={tab.id === activeTabId}
            class="group flex min-w-[7rem] max-w-[14rem] items-center gap-1.5 rounded-lg px-2 py-1 md:py-0.5 text-sm transition-colors cursor-pointer {tab.id ===
            activeTabId
                ? 'bg-sem-canvas font-medium text-sem-fg shadow-xs ring-1 ring-sem-border'
                : 'text-sem-fg-muted hover:bg-sem-surface/80 hover:text-sem-fg'}"
            onclick={() => onselect(tab.id)}
            onkeydown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onselect(tab.id);
                }
            }}
        >
            <MaterialDesignIcon iconName="map" class="size-4 shrink-0 opacity-70" />
            {#if renamingTabId === tab.id}
                <input
                    bind:this={renameInputEl}
                    bind:value={renameDraft}
                    type="text"
                    class="min-w-0 flex-1 border-b border-sem-accent bg-transparent text-sm text-sem-fg outline-hidden"
                    maxlength={64}
                    onclick={(e) => e.stopPropagation()}
                    onkeydown={(e) => {
                        if (e.key === "Enter") {
                            e.preventDefault();
                            oncommitrename();
                        } else if (e.key === "Escape") {
                            e.preventDefault();
                            oncancelrename();
                        }
                    }}
                    onblur={oncommitrename}
                />
            {:else}
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <span
                    class="min-w-0 flex-1 truncate text-left"
                    title={t("map.tab_rename_hint")}
                    ondblclick={(e) => {
                        e.stopPropagation();
                        onstartrename(tab.id);
                    }}
                    ontouchend={(e) => {
                        e.stopPropagation();
                        ontablabeltouchend(tab, e);
                    }}
                >
                    {tabTitle(tab)}
                </span>
            {/if}
            <span
                role="button"
                tabindex="0"
                class="shrink-0 rounded-md p-0.5 text-sem-fg-muted opacity-0 transition-opacity hover:bg-sem-surface-muted hover:text-sem-fg group-hover:opacity-100 group-focus-within:opacity-100 cursor-pointer {tab.id ===
                activeTabId
                    ? 'opacity-70'
                    : ''}"
                title={t("common.cancel")}
                onclick={(e) => {
                    e.stopPropagation();
                    onclosetab(tab.id);
                }}
                onkeydown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                        e.stopPropagation();
                        e.preventDefault();
                        onclosetab(tab.id);
                    }
                }}
            >
                <MaterialDesignIcon iconName="close" class="size-4" />
            </span>
        </div>
    {/each}
    <button
        type="button"
        class="flex size-8 shrink-0 items-center justify-center rounded-lg text-sem-fg-muted transition-colors hover:bg-sem-surface/80 hover:text-sem-fg disabled:opacity-40 disabled:pointer-events-none cursor-pointer"
        title={canAddTab ? t("map.new_tab_shortcut") : t("map.tab_limit_reached")}
        disabled={!canAddTab}
        onclick={onaddtab}
    >
        <MaterialDesignIcon iconName="plus" class="size-5" />
    </button>
    <div
        id="map-browser-toolbar-host"
        class="ml-auto flex items-center gap-1.5 px-2 shrink-0 min-w-0 max-w-[min(100%,42rem)]"
    ></div>
</div>
