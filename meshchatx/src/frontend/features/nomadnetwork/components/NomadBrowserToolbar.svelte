<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import IconButton from "../../../ui/svelte/IconButton.svelte";
    import { t } from "../../../js/i18n.js";
    import type { NomadNode } from "../lib/types.js";

    interface Props {
        selectedNode?: NomadNode | null;
        urlInput?: string;
        isShowingSource?: boolean;
        hasHistory?: boolean;
        pathfinderInProgress?: boolean;
        hasArchives?: boolean;
        isPrivate?: boolean;
        onhome?: () => void;
        onrefresh?: () => void;
        ontogglesource?: () => void;
        onback?: () => void;
        onurlsubmit?: (url: string) => void;
        onurlchange?: (url: string) => void;
        onpathfinderquick?: () => void;
        onpathfinderforce?: () => void;
        onpathfinderdrop?: () => void;
        onloadlatestarchive?: () => void;
    }

    let {
        selectedNode = null,
        urlInput = "",
        isShowingSource = false,
        hasHistory = false,
        pathfinderInProgress = false,
        hasArchives = false,
        isPrivate = false,
        onhome,
        onrefresh,
        ontogglesource,
        onback,
        onurlsubmit,
        onurlchange,
        onpathfinderquick,
        onpathfinderforce,
        onpathfinderdrop,
        onloadlatestarchive,
    }: Props = $props();

    let pathfinderMenuOpen = $state(false);
</script>

<div
    class="nomad-browser-chrome flex w-full min-w-0 items-center gap-0.5 overflow-x-auto border-b border-sem-border bg-sem-surface px-2 py-0.5 sm:gap-1 sm:px-3"
>
    <IconButton class="nomad-icon-btn shrink-0" title={t("nomadnet.nav_home")} onclick={() => onhome?.()}>
        <MaterialDesignIcon iconName="home" class="size-5" />
    </IconButton>

    <IconButton class="nomad-icon-btn shrink-0" title={t("common.refresh")} onclick={() => onrefresh?.()}>
        <MaterialDesignIcon iconName="refresh" class="size-5" />
    </IconButton>

    <IconButton
        class="nomad-icon-btn hidden lg:inline-flex shrink-0 {isShowingSource
            ? 'bg-green-500/10 text-green-600 dark:text-green-400'
            : ''}"
        title={t("app.toggle_source")}
        onclick={() => ontogglesource?.()}
    >
        <MaterialDesignIcon iconName="code-tags" class="size-5" />
    </IconButton>

    <IconButton
        class="nomad-icon-btn shrink-0"
        title={t("nomadnet.nav_back")}
        disabled={!hasHistory}
        onclick={() => onback?.()}
    >
        <MaterialDesignIcon iconName="arrow-left" class="size-5" />
    </IconButton>

    <div class="my-auto min-w-0 flex-1 px-0.5 sm:px-1">
        <input
            value={urlInput}
            type="text"
            placeholder={t("nomadnet.enter_nomadnet_url")}
            class="nomad-url-input block w-full min-w-0 bg-sem-canvas border border-sem-border rounded px-2 py-1 text-sm text-sem-fg"
            oninput={(e) => onurlchange?.((e.target as HTMLInputElement).value)}
            onkeydown={(e) => {
                if (e.key === "Enter") onurlsubmit?.(urlInput);
            }}
        />
    </div>

    <IconButton class="nomad-icon-btn shrink-0" title={t("nomadnet.nav_go")} onclick={() => onurlsubmit?.(urlInput)}>
        <MaterialDesignIcon iconName="arrow-right" class="size-5" />
    </IconButton>

    {#if selectedNode}
        <div class="relative shrink-0">
            <IconButton
                title={t("nomadnet.path_finder")}
                class="nomad-icon-btn text-sem-accent"
                disabled={pathfinderInProgress}
                onclick={() => {
                    pathfinderMenuOpen = !pathfinderMenuOpen;
                }}
            >
                <MaterialDesignIcon
                    iconName={pathfinderInProgress ? "loading" : "map-marker-path"}
                    class="size-5 {pathfinderInProgress ? 'animate-spin' : ''}"
                />
            </IconButton>

            {#if pathfinderMenuOpen}
                <div
                    class="absolute right-0 top-full mt-1 z-50 min-w-52 bg-sem-surface border border-sem-border rounded-xl shadow-xl py-1 text-sem-fg"
                >
                    <button
                        type="button"
                        class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-sem-surface-muted"
                        onclick={() => {
                            pathfinderMenuOpen = false;
                            onpathfinderquick?.();
                        }}
                    >
                        <MaterialDesignIcon iconName="flash" class="size-5" />
                        <span>{t("nomadnet.path_finder_quick_request")}</span>
                    </button>
                    <button
                        type="button"
                        class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-sem-surface-muted"
                        onclick={() => {
                            pathfinderMenuOpen = false;
                            onpathfinderforce?.();
                        }}
                    >
                        <MaterialDesignIcon iconName="map-marker-radius" class="size-5" />
                        <span>{t("nomadnet.path_finder_force_find")}</span>
                    </button>
                    <button
                        type="button"
                        class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-sem-surface-muted"
                        onclick={() => {
                            pathfinderMenuOpen = false;
                            onpathfinderdrop?.();
                        }}
                    >
                        <MaterialDesignIcon iconName="reload-alert" class="size-5" />
                        <span>{t("nomadnet.path_finder_drop_and_request")}</span>
                    </button>
                    {#if !isPrivate && hasArchives}
                        <button
                            type="button"
                            class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-sem-surface-muted"
                            onclick={() => {
                                pathfinderMenuOpen = false;
                                onloadlatestarchive?.();
                            }}
                        >
                            <MaterialDesignIcon iconName="archive-clock" class="size-5" />
                            <span>{t("nomadnet.path_finder_load_archive")}</span>
                        </button>
                    {/if}
                </div>
            {/if}
        </div>
    {/if}
</div>
