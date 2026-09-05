<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { formatDate } from "../../../libs/datetime.js";
    import { t } from "../../../js/i18n.js";
    import NomadCrashTab from "./NomadCrashTab.svelte";
    import { isFailedPageContent } from "../lib/nomadPageDownloads.js";
    import type { NomadNavigateEvent, NomadNode } from "../lib/types.js";

    interface Props {
        selectedNode?: NomadNode | null;
        nodePagePath?: string | null;
        nodePageContent?: string | null;
        isShowingArchivedVersion?: boolean;
        archivedAt?: string | null;
        showPageBusyBanner?: boolean;
        pageBusyBannerLine?: string;
        showCancelledPageState?: boolean;
        pageRenderAborted?: boolean;
        canRetryCrashTabRender?: boolean;
        hasArchivesForCurrentPage?: boolean;
        isPrivate?: boolean;
        showEmptyPageState?: boolean;
        showCrashTabHost?: boolean;
        crashTabPageContent?: string;
        isShowingNodePageSource?: boolean;
        pagePartials?: Record<string, string>;
        nomadRenderOptions?: Record<string, unknown>;
        nomadCrashTabContentClass?: string;
        nomadCrashTabColor?: string;
        nomadCrashTabBackground?: string;
        active?: boolean;
        isActive?: boolean;
        multilineHintVisible?: boolean;
        nomadRenderedShellFullBleed?: boolean;
        nomadShellDark?: boolean;
        nodeContainerShellStyle?: string;
        onreload?: () => void;
        oncancelbusy?: () => void;
        onretrycrashtab?: () => void;
        ontogglearchive?: () => void;
        oncontentclick?: (e: MouseEvent) => void;
        oncontentcontextmenu?: (e: MouseEvent) => void;
        oncrashtabnavigate?: (e: NomadNavigateEvent) => void;
        oncrashtabpartials?: (partials: unknown[]) => void;
        onviewsource?: () => void;
        oncrashtabhung?: () => void;
        oncrashtabrenderstarted?: () => void;
        oncrashtabrenderdone?: () => void;
        oncrashtababorted?: () => void;
        oncrashtabshellbackground?: (bg: string | null) => void;
    }

    let {
        selectedNode = null,
        nodePagePath = null,
        nodePageContent = null,
        isShowingArchivedVersion = false,
        archivedAt = null,
        showPageBusyBanner = false,
        pageBusyBannerLine = "",
        showCancelledPageState = false,
        pageRenderAborted = false,
        canRetryCrashTabRender = false,
        hasArchivesForCurrentPage = false,
        isPrivate = false,
        showEmptyPageState = false,
        showCrashTabHost = false,
        crashTabPageContent = "",
        isShowingNodePageSource = false,
        pagePartials = {},
        nomadRenderOptions = {},
        nomadCrashTabContentClass = "",
        nomadCrashTabColor = "",
        nomadCrashTabBackground = "#000000",
        active = true,
        isActive = true,
        multilineHintVisible = false,
        nomadRenderedShellFullBleed = false,
        nomadShellDark = false,
        nodeContainerShellStyle = "",
        onreload,
        oncancelbusy,
        onretrycrashtab,
        ontogglearchive,
        oncontentclick,
        oncontentcontextmenu,
        oncrashtabnavigate,
        oncrashtabpartials,
        onviewsource,
        oncrashtabhung,
        oncrashtabrenderstarted,
        oncrashtabrenderdone,
        oncrashtababorted,
        oncrashtabshellbackground,
    }: Props = $props();

    let crashTab = $state<NomadCrashTab | null>(null);

    export function reloadFrame() {
        crashTab?.reloadFrame();
    }

    export function abortRender() {
        crashTab?.abortRender();
    }

    export function setPartialHtml(partialId: string, html: string) {
        crashTab?.setPartialHtml(partialId, html);
    }
</script>

<div
    class="flex-1 min-h-0 min-w-0 overflow-y-auto overflow-x-hidden nodeContainer relative {nomadRenderedShellFullBleed
        ? 'p-0 bg-transparent min-h-full text-gray-900 dark:text-gray-100'
        : 'p-3 bg-black text-white'} {nomadShellDark ? 'nomad-shell-dark' : ''}"
    style={nodeContainerShellStyle}
    onclickcapture={(e) => oncontentclick?.(e)}
    onauxclickcapture={(e) => oncontentclick?.(e)}
    oncontextmenu={(e) => oncontentcontextmenu?.(e)}
    role="region"
    aria-label="Nomad page content"
>
    {#if isShowingArchivedVersion}
        <div
            class="mb-4 flex min-w-0 items-center justify-between gap-2 rounded-sm border border-yellow-700/50 bg-yellow-900/40 p-2 text-yellow-200 {nomadRenderedShellFullBleed
                ? 'mx-3 mt-3'
                : ''}"
        >
            <div class="flex min-w-0 items-center gap-2">
                <MaterialDesignIcon iconName="clock" class="size-5 shrink-0" />
                {#if archivedAt}
                    <span class="min-w-0 text-sm font-medium">
                        {t("nomadnet.viewing_archived_version_from", {
                            time: formatDate(new Date(archivedAt), "MMM D, h:mm A"),
                        })}
                    </span>
                {:else}
                    <span class="min-w-0 text-sm font-medium">{t("nomadnet.viewing_archived_version")}</span>
                {/if}
            </div>
            <button
                type="button"
                class="shrink-0 text-xs bg-yellow-700/50 hover:bg-yellow-700 px-2 py-1 rounded-sm transition"
                onclick={() => onreload?.()}
            >
                {t("nomadnet.load_live")}
            </button>
        </div>
    {/if}

    {#if showPageBusyBanner}
        <div class="flex min-w-0 p-3" role="status" aria-live="polite">
            <div class="my-auto">
                <svg
                    class="animate-spin mr-3 h-5 w-5 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                >
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path
                        class="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                </svg>
            </div>
            <div class="my-auto min-w-0 flex-1 truncate">{pageBusyBannerLine}</div>
            <button
                type="button"
                class="my-auto text-white bg-red-600 hover:bg-red-700 rounded-sm px-3 py-1 text-sm font-semibold cursor-pointer ml-3"
                onclick={() => oncancelbusy?.()}
            >
                {t("common.cancel")}
            </button>
        </div>
    {:else if showCancelledPageState}
        <div class="flex p-3" role="status">
            <div class="my-auto flex-1">
                <div>
                    {pageRenderAborted
                        ? t("nomadnet.crash_tab_render_cancelled")
                        : t("nomadnet.page_download_cancelled")}
                </div>
                <div class="text-sm text-sem-fg-muted">{t("nomadnet.page_stopped_hint")}</div>
            </div>
            {#if pageRenderAborted && canRetryCrashTabRender}
                <button
                    type="button"
                    class="my-auto text-white bg-blue-600 hover:bg-blue-700 rounded-sm px-3 py-1 text-sm font-semibold cursor-pointer ml-3"
                    onclick={() => onretrycrashtab?.()}
                >
                    {t("nomadnet.crash_tab_reload")}
                </button>
            {:else if selectedNode?.destination_hash && nodePagePath}
                <button
                    type="button"
                    class="my-auto text-white bg-blue-600 hover:bg-blue-700 rounded-sm px-3 py-1 text-sm font-semibold cursor-pointer ml-3"
                    onclick={() => onreload?.()}
                >
                    {t("common.refresh")}
                </button>
            {/if}
        </div>
    {:else if isFailedPageContent(nodePageContent)}
        <div class="flex flex-col items-center justify-center h-full text-center space-y-4 p-4" role="alert">
            <div class="text-red-400 font-semibold text-lg">{t("nomadnet.failed_to_load_page")}</div>
            <div class="text-sem-fg-muted text-sm max-w-md break-words">{nodePageContent}</div>

            {#if !isPrivate && hasArchivesForCurrentPage}
                <div class="space-y-2">
                    <div class="text-sm text-sem-fg-muted">{t("nomadnet.archived_version_available")}</div>
                    <button
                        type="button"
                        class="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500"
                        onclick={() => ontogglearchive?.()}
                    >
                        <MaterialDesignIcon iconName="archive" class="size-5" />
                        <span>{t("nomadnet.view_archive")}</span>
                    </button>
                </div>
            {:else if selectedNode?.destination_hash}
                <button
                    type="button"
                    class="my-auto text-white bg-blue-600 hover:bg-blue-700 rounded-sm px-3 py-1 text-sm font-semibold cursor-pointer"
                    onclick={() => onreload?.()}
                >
                    {t("common.refresh")}
                </button>
            {/if}
        </div>
    {:else if showEmptyPageState}
        <div class="flex p-3">
            <div class="my-auto flex-1">
                <div>{t("nomadnet.page_empty_title")}</div>
                <div class="text-sm text-sem-fg-muted">{t("nomadnet.page_empty_body")}</div>
            </div>
            {#if selectedNode?.destination_hash}
                <button
                    type="button"
                    class="my-auto text-white bg-blue-600 hover:bg-blue-700 rounded-sm px-3 py-1 text-sm font-semibold cursor-pointer ml-3"
                    onclick={() => onreload?.()}
                >
                    {t("common.refresh")}
                </button>
            {/if}
        </div>
    {/if}

    {#if showCrashTabHost}
        <div
            class="relative min-h-0 w-full min-w-0 overflow-hidden bg-black {showPageBusyBanner ||
            showCancelledPageState ||
            isFailedPageContent(nodePageContent) ||
            showEmptyPageState
                ? 'pointer-events-none absolute inset-0 opacity-0'
                : 'h-full'}"
        >
            <NomadCrashTab
                bind:this={crashTab}
                class="absolute inset-0 h-full min-h-0 w-full min-w-0"
                path={nodePagePath || ""}
                content={crashTabPageContent}
                showSource={isShowingNodePageSource}
                {pagePartials}
                renderOptions={nomadRenderOptions}
                contentClass={nomadCrashTabContentClass}
                color={nomadCrashTabColor}
                background={nomadCrashTabBackground}
                active={active && isActive}
                reveal={!showPageBusyBanner}
                onnavigate={(e) => oncrashtabnavigate?.(e)}
                onpartials={(p) => oncrashtabpartials?.(p)}
                onviewsource={() => onviewsource?.()}
                onhung={() => oncrashtabhung?.()}
                onrenderstarted={() => oncrashtabrenderstarted?.()}
                onrenderdone={() => oncrashtabrenderdone?.()}
                onaborted={() => oncrashtababorted?.()}
                onshellbackground={(bg) => oncrashtabshellbackground?.(bg)}
            />
        </div>
    {/if}

    {#if multilineHintVisible}
        <div
            class="multiline-hint pointer-events-none fixed z-200 bottom-3 right-3 px-2 py-1 rounded text-xs bg-amber-300 text-zinc-900 shadow"
        >
            {t("nomadnet.multiline_hint")}
        </div>
    {/if}
</div>
