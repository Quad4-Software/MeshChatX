<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import IconButton from "../../../ui/svelte/IconButton.svelte";
    import { formatDate } from "../../../libs/datetime.js";
    import GlobalState from "../../../js/GlobalState.js";
    import { t } from "../../../js/i18n.js";
    import { MICRON_PARSER_GO_REPO_URL } from "../lib/constants.js";
    import type {
        NomadDestinationPath,
        NomadNode,
        NomadPageArchive,
        NomadPageRendererChip,
        NomadPageStats,
    } from "../lib/types.js";

    interface Props {
        selectedNode: NomadNode;
        isPrivate?: boolean;
        isFavouriteNode?: boolean;
        selectedNodePath?: NomadDestinationPath | null;
        navbarPageStats?: NomadPageStats | null;
        rendererChip?: NomadPageRendererChip | null;
        isLoadingNodePage?: boolean;
        showMicronRendererInMobileMenu?: boolean;
        pageArchives?: NomadPageArchive[];
        nodePageContent?: string | null;
        isArchiveDropdownOpen?: boolean;
        identifiesOnConnect?: boolean;
        isShowingSource?: boolean;
        ontogglefavourite?: () => void;
        onpathclick?: (path: NomadDestinationPath) => void;
        ontogglearchivedropdown?: () => void;
        onmanualarchive?: () => void;
        onloadarchivedpage?: (id: string | number) => void;
        ontoggleidentifyonconnect?: () => void;
        onpopout?: () => void;
        onclosenode?: () => void;
        ontogglesource?: () => void;
        onapplymicronengine?: (engine: string) => void;
    }

    let {
        selectedNode,
        isPrivate = false,
        isFavouriteNode = false,
        selectedNodePath = null,
        navbarPageStats = null,
        rendererChip = null,
        isLoadingNodePage = false,
        showMicronRendererInMobileMenu = false,
        pageArchives = [],
        nodePageContent = null,
        isArchiveDropdownOpen = false,
        identifiesOnConnect = false,
        isShowingSource = false,
        ontogglefavourite,
        onpathclick,
        ontogglearchivedropdown,
        onmanualarchive,
        onloadarchivedpage,
        ontoggleidentifyonconnect,
        onpopout,
        onclosenode,
        ontogglesource,
        onapplymicronengine,
    }: Props = $props();

    let rendererPopoverOpen = $state(false);
    let mobileMenuOpen = $state(false);
</script>

<div
    class="flex min-w-0 items-center gap-1 border-b px-2 py-0.5 sm:px-3 {isPrivate
        ? 'border-purple-500/50 bg-[#1a0b33] text-purple-100'
        : 'border-sem-border bg-sem-surface'}"
>
    {#if isPrivate}
        <div
            class="my-auto flex shrink-0 items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium text-purple-200"
            title={t("nomadnet.private_browsing_hint")}
        >
            <MaterialDesignIcon iconName="incognito" class="size-4 text-purple-300" />
            <span class="hidden sm:inline">{t("nomadnet.private_tab")}</span>
        </div>
    {/if}

    {#if !isPrivate}
        <div class="my-auto shrink-0">
            <IconButton
                class="nomad-icon-btn {isFavouriteNode ? 'text-yellow-500 dark:text-yellow-300' : 'text-sem-fg-muted'}"
                title={isFavouriteNode ? t("nomadnet.remove_favourite") : t("nomadnet.add_favourite")}
                onclick={() => ontogglefavourite?.()}
            >
                <MaterialDesignIcon iconName={isFavouriteNode ? "star" : "star-outline"} class="size-5" />
            </IconButton>
        </div>
    {/if}

    <div class="my-auto text-sem-fg flex-1 min-w-0 flex items-center gap-2 overflow-hidden">
        <span
            class="font-medium truncate inline-block min-w-0 max-w-[min(100%,12rem)] sm:max-w-xs md:max-w-sm"
            title={selectedNode.custom_display_name || selectedNode.display_name}
        >
            {selectedNode.custom_display_name || selectedNode.display_name}
        </span>

        {#if selectedNodePath}
            <button
                type="button"
                class="text-xs text-sem-fg-muted cursor-pointer whitespace-nowrap shrink-0 hidden sm:inline hover:text-sem-fg"
                onclick={() => onpathclick?.(selectedNodePath)}
            >
                {selectedNodePath.hops}
                {selectedNodePath.hops === 1 ? t("app.hop") : t("app.hops_plural")}
                {#if navbarPageStats}
                    · {navbarPageStats.duration} · {navbarPageStats.sizeLabel}
                {/if}
            </button>
        {/if}

        {#if rendererChip && !isLoadingNodePage}
            <div class="relative shrink-0 hidden sm:inline-flex">
                <button
                    type="button"
                    class="shrink-0 max-w-[7.5rem] md:max-w-[9rem] truncate rounded px-1 py-0.5 text-[11px] font-medium leading-tight text-sem-fg-muted hover:bg-sem-surface-muted cursor-pointer outline-hidden"
                    onclick={() => {
                        rendererPopoverOpen = !rendererPopoverOpen;
                    }}
                >
                    {rendererChip.label}
                </button>
                {#if rendererPopoverOpen}
                    <div
                        class="absolute left-0 top-full mt-1 z-60 w-64 rounded-lg border border-sem-border bg-sem-surface px-3 py-2 text-xs leading-snug text-sem-fg shadow-lg"
                    >
                        {#if rendererChip.popoverVariant === "wasm_active"}
                            <span>{t("nomadnet.renderer_popover_micron_wasm_powered")}</span>
                            <a
                                class="font-medium underline underline-offset-2 hover:opacity-90 ml-1"
                                href={MICRON_PARSER_GO_REPO_URL}
                                target="_blank"
                                rel="noopener noreferrer">{t("settings.nomad_micron_wasm_link_label")}</a
                            >
                            <span
                                >{t("nomadnet.renderer_popover_micron_wasm_active_tail", {
                                    version: rendererChip.micronGoRelease,
                                })}</span
                            >
                        {:else if rendererChip.popoverVariant === "wasm_pending"}
                            <a
                                class="font-medium underline underline-offset-2 hover:opacity-90 mr-1"
                                href={MICRON_PARSER_GO_REPO_URL}
                                target="_blank"
                                rel="noopener noreferrer">{t("settings.nomad_micron_wasm_link_label")}</a
                            >
                            <span
                                >{t("nomadnet.renderer_popover_micron_wasm_pending_tail", {
                                    version: rendererChip.micronGoRelease,
                                })}</span
                            >
                        {:else}
                            {rendererChip.tooltipBody}
                        {/if}

                        {#if showMicronRendererInMobileMenu}
                            <div class="mt-2 pt-2 border-t border-sem-border flex flex-col gap-1.5">
                                <div class="text-[10px] font-bold uppercase tracking-wider text-sem-fg-muted">
                                    {t("nomadnet.renderer_switch_title")}
                                </div>
                                <div class="flex gap-1">
                                    <button
                                        type="button"
                                        class="flex-1 rounded px-2 py-1 text-[10px] font-bold transition-colors {(GlobalState
                                            .config?.nomad_micron_default_engine || 'js') === 'js'
                                            ? 'bg-blue-600 text-white dark:bg-blue-500'
                                            : 'bg-sem-surface-muted text-sem-fg hover:bg-sem-border'}"
                                        disabled={!GlobalState.config?.nomad_micron_wasm_enabled}
                                        onclick={() => onapplymicronengine?.("js")}
                                    >
                                        JS
                                    </button>
                                    <button
                                        type="button"
                                        class="flex-1 rounded px-2 py-1 text-[10px] font-bold transition-colors {(GlobalState
                                            .config?.nomad_micron_default_engine || 'js') === 'wasm'
                                            ? 'bg-blue-600 text-white dark:bg-blue-500'
                                            : 'bg-sem-surface-muted text-sem-fg hover:bg-sem-border'}"
                                        disabled={!GlobalState.config?.nomad_micron_wasm_enabled}
                                        onclick={() => onapplymicronengine?.("wasm")}
                                    >
                                        WASM
                                    </button>
                                </div>
                            </div>
                        {/if}
                    </div>
                {/if}
            </div>
        {/if}
    </div>

    {#if !isPrivate && (pageArchives.length > 0 || nodePageContent)}
        <div class="my-auto shrink-0 relative">
            <IconButton
                class="nomad-icon-btn {pageArchives.length > 0 ? 'text-sem-accent' : 'text-sem-fg-muted'}"
                title={t("app.archives")}
                onclick={() => ontogglearchivedropdown?.()}
            >
                <MaterialDesignIcon iconName="archive" class="size-5" />
            </IconButton>

            {#if isArchiveDropdownOpen}
                <div
                    class="absolute right-0 mt-2 w-64 bg-sem-surface border border-sem-border rounded-lg shadow-lg z-50 overflow-hidden text-sem-fg"
                >
                    <div
                        class="p-2 border-b border-sem-border font-semibold text-xs text-sem-fg-muted uppercase tracking-wider flex justify-between items-center"
                    >
                        <span>{t("nomadnet.page_archives")}</span>
                        {#if nodePageContent}
                            <button
                                type="button"
                                title={t("nomadnet.archive_current_version")}
                                class="text-blue-500 hover:text-sem-accent dark:hover:text-blue-300"
                                onclick={() => onmanualarchive?.()}
                            >
                                <MaterialDesignIcon iconName="plus" class="size-5" />
                            </button>
                        {/if}
                    </div>
                    <div class="max-h-64 overflow-y-auto">
                        {#if pageArchives.length === 0}
                            <div class="p-3 text-sm text-sem-fg-muted text-center">
                                {t("nomadnet.no_archives_for_this_page")}
                            </div>
                        {:else}
                            {#each pageArchives as arch (arch.id)}
                                <button
                                    type="button"
                                    class="w-full text-left p-2 hover:bg-sem-surface-muted cursor-pointer border-b last:border-b-0 border-sem-border"
                                    onclick={() => onloadarchivedpage?.(arch.id)}
                                >
                                    <div class="text-sm font-medium">
                                        {formatDate(new Date(arch.created_at), "MMM D, h:mm A")}
                                    </div>
                                    <div class="text-xs text-sem-fg-muted truncate">
                                        {arch.hash?.substring(0, 16)}...
                                    </div>
                                </button>
                            {/each}
                        {/if}
                    </div>
                </div>
            {/if}
        </div>
    {/if}

    {#if !isPrivate}
        <IconButton
            class="nomad-icon-btn shrink-0 {identifiesOnConnect ? 'text-sem-accent' : 'text-sem-fg-muted'}"
            title={identifiesOnConnect ? t("nomadnet.identify_on_connect_on") : t("nomadnet.identify_on_connect_off")}
            aria-pressed={identifiesOnConnect ? "true" : "false"}
            onclick={() => ontoggleidentifyonconnect?.()}
        >
            <MaterialDesignIcon iconName="fingerprint" class="size-5" />
        </IconButton>

        <div class="hidden shrink-0 items-center gap-0 lg:flex">
            <IconButton
                class="nomad-icon-btn text-sem-fg-muted"
                title={t("nomadnet.pop_out_browser")}
                onclick={() => onpopout?.()}
            >
                <MaterialDesignIcon iconName="open-in-new" class="size-5" />
            </IconButton>
        </div>
    {/if}

    <div class="relative shrink-0 lg:hidden">
        <IconButton
            title={t("messages.more_actions")}
            class="nomad-icon-btn text-sem-fg-muted"
            onclick={() => {
                mobileMenuOpen = !mobileMenuOpen;
            }}
        >
            <MaterialDesignIcon iconName="dots-horizontal" class="size-5" />
        </IconButton>

        {#if mobileMenuOpen}
            <div
                class="absolute right-0 top-full mt-1 z-50 min-w-44 bg-sem-surface border border-sem-border rounded-xl shadow-xl py-1 text-sem-fg"
            >
                <button
                    type="button"
                    class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-sem-surface-muted"
                    onclick={() => {
                        mobileMenuOpen = false;
                        ontogglesource?.();
                    }}
                >
                    <MaterialDesignIcon iconName="code-tags" class="size-5" />
                    <span>{isShowingSource ? t("nomadnet.hide_source") : t("app.toggle_source")}</span>
                </button>
                {#if showMicronRendererInMobileMenu}
                    <button
                        type="button"
                        class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-sem-surface-muted"
                        onclick={() => {
                            mobileMenuOpen = false;
                            onapplymicronengine?.("js");
                        }}
                    >
                        <MaterialDesignIcon iconName="language-javascript" class="size-5" />
                        <span>{t("nomadnet.renderer_menu_js")}</span>
                    </button>
                    <button
                        type="button"
                        class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-sem-surface-muted"
                        onclick={() => {
                            mobileMenuOpen = false;
                            onapplymicronengine?.("wasm");
                        }}
                    >
                        <MaterialDesignIcon iconName="memory" class="size-5" />
                        <span>{t("nomadnet.renderer_menu_wasm")}</span>
                    </button>
                {/if}
            </div>
        {/if}
    </div>

    <IconButton
        class="nomad-icon-btn shrink-0 text-sem-fg-muted"
        title={t("common.cancel")}
        onclick={() => onclosenode?.()}
    >
        <MaterialDesignIcon iconName="close" class="size-5" />
    </IconButton>
</div>
