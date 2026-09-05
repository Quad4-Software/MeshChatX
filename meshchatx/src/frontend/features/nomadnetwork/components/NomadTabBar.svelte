<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import IconButton from "../../../ui/svelte/IconButton.svelte";
    import { t } from "../../../js/i18n.js";
    import type { NomadTab } from "../lib/types.js";

    interface Props {
        tabs: NomadTab[];
        selectedTabId: number | null;
        onselecttab?: (id: number) => void;
        onclosetab?: (id: number) => void;
        onnewtab?: () => void;
        onnewprivatetab?: () => void;
        ontabcontextmenu?: (e: MouseEvent, tabId: number) => void;
    }

    let {
        tabs = [],
        selectedTabId = null,
        onselecttab,
        onclosetab,
        onnewtab,
        onnewprivatetab,
        ontabcontextmenu,
    }: Props = $props();
</script>

<div
    class="nomad-tab-bar flex h-9 w-full min-w-0 items-center overflow-x-auto border-b border-sem-border bg-sem-surface-muted px-1.5"
    role="tablist"
    aria-label="Nomad tabs"
>
    <div class="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto">
        {#each tabs as tab (tab.id)}
            <div
                class="group flex h-7 max-w-44 min-w-24 items-center gap-1.5 rounded-t-md px-2 text-xs transition-colors cursor-pointer {tab.id ===
                selectedTabId
                    ? 'bg-sem-surface text-sem-fg font-medium border-t-2 border-blue-500'
                    : 'text-sem-fg-muted hover:bg-sem-surface/50'} {tab.private
                    ? 'border-t-purple-500 bg-purple-950/30 text-purple-200'
                    : ''}"
                role="tab"
                tabindex="0"
                aria-selected={tab.id === selectedTabId}
                onclick={() => onselecttab?.(tab.id)}
                onkeydown={(e) => {
                    if (e.key === "Enter" || e.key === " ") onselecttab?.(tab.id);
                }}
                oncontextmenu={(e) => ontabcontextmenu?.(e, tab.id)}
            >
                {#if tab.private}
                    <MaterialDesignIcon iconName="incognito" class="size-3.5 shrink-0 text-purple-300" />
                {:else}
                    <MaterialDesignIcon iconName="earth" class="size-3.5 shrink-0 text-sem-fg-muted" />
                {/if}

                <span class="truncate flex-1 min-w-0">{tab.title || tab.destinationHash || t("nomadnet.new_tab")}</span>

                {#if tabs.length > 1}
                    <span
                        role="button"
                        tabindex="0"
                        class="hidden group-hover:flex shrink-0 p-0.5 rounded hover:bg-sem-surface-muted text-sem-fg-muted hover:text-sem-fg cursor-pointer"
                        title={t("common.close")}
                        onclick={(e) => {
                            e.stopPropagation();
                            onclosetab?.(tab.id);
                        }}
                        onkeydown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                                e.stopPropagation();
                                onclosetab?.(tab.id);
                            }
                        }}
                    >
                        <MaterialDesignIcon iconName="close" class="size-3" />
                    </span>
                {/if}
            </div>
        {/each}
    </div>

    <div class="flex shrink-0 items-center gap-0.5 ml-1">
        <IconButton
            class="nomad-icon-btn size-7 text-sem-fg-muted hover:text-sem-fg"
            title={t("nomadnet.new_tab")}
            onclick={() => onnewtab?.()}
        >
            <MaterialDesignIcon iconName="plus" class="size-4" />
        </IconButton>

        <IconButton
            class="nomad-icon-btn size-7 text-purple-400 hover:text-purple-300"
            title={t("nomadnet.new_private_tab")}
            onclick={() => onnewprivatetab?.()}
        >
            <MaterialDesignIcon iconName="incognito" class="size-4" />
        </IconButton>
    </div>
</div>
