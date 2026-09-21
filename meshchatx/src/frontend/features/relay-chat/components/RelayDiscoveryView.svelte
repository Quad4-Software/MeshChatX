<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import SearchInput from "../../../ui/svelte/SearchInput.svelte";
    import { t } from "../../../js/i18n.js";
    import { BTN_PRIMARY, BTN_SECONDARY } from "../lib/constants.js";
    import type { RrcDiscoveredHub } from "../lib/types.js";

    interface Props {
        discovered?: RrcDiscoveredHub[];
        searchTerm?: string;
        isLoading?: boolean;
        isHubAdded?: (destinationHash?: string | null) => boolean;
        nodeName?: (node: RrcDiscoveredHub) => string;
        formatHash?: (hash: string | null | undefined) => string;
        timeAgo?: (datetime?: string | null) => string;
        onsearchchange?: () => void;
        onrefresh?: () => void;
        oncopyhash?: (hash: string) => void;
        onadd?: (node: RrcDiscoveredHub) => void;
        onopen?: (node: RrcDiscoveredHub) => void;
    }

    let {
        discovered = [],
        searchTerm = $bindable(""),
        isLoading = false,
        isHubAdded = () => false,
        nodeName = (n) => n?.display_name || n?.custom_display_name || "",
        formatHash = (h) => h || "-",
        timeAgo = () => "",
        onsearchchange,
        onrefresh,
        oncopyhash,
        onadd,
        onopen,
    }: Props = $props();
</script>

<div class="flex-1 overflow-y-auto custom-scrollbar p-3 sm:p-4">
    <div class="mx-auto w-full max-w-3xl space-y-3">
        <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
                <h2 class="text-lg font-semibold">{t("relay_chat.discovery_title")}</h2>
                <p class="text-sm text-sem-fg-muted">{t("relay_chat.discovery_subtitle")}</p>
            </div>
            <button type="button" class={BTN_SECONDARY} disabled={isLoading} onclick={() => onrefresh?.()}>
                <MaterialDesignIcon iconName="refresh" class="size-4 {isLoading ? 'animate-spin' : ''}" />
                {t("relay_chat.refresh")}
            </button>
        </div>

        <SearchInput
            bind:value={searchTerm}
            placeholder={t("relay_chat.discovery_search", { count: discovered.length })}
            oninput={() => onsearchchange?.()}
        />

        {#if discovered.length === 0}
            <div
                class="flex flex-col items-center gap-2 rounded-xl border border-sem-border bg-sem-canvas p-8 text-center text-sm text-sem-fg-muted"
            >
                <MaterialDesignIcon iconName="radar" class="size-10 opacity-40" />
                {t("relay_chat.discovery_empty")}
            </div>
        {/if}

        <div class="space-y-2">
            {#each discovered as node (node.destination_hash)}
                <div
                    class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-sem-border bg-sem-canvas p-4 transition-colors hover:border-sem-border-strong"
                >
                    <div class="min-w-0 flex-1">
                        <div class="flex items-center gap-2">
                            <MaterialDesignIcon iconName="forum-outline" class="size-4 shrink-0 text-sem-accent" />
                            <span class="truncate font-semibold">{nodeName(node)}</span>
                        </div>
                        <button
                            type="button"
                            class="mt-1 flex items-center gap-1.5 font-mono text-xs text-sem-fg-muted hover:text-sem-accent cursor-pointer"
                            title={t("relay_chat.copy_hash")}
                            onclick={() => oncopyhash?.(node.destination_hash)}
                        >
                            <MaterialDesignIcon iconName="content-copy" class="size-3.5" />
                            <span class="truncate">{formatHash(node.destination_hash)}</span>
                        </button>
                        <div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-sem-fg-muted">
                            <span class="inline-flex items-center gap-1">
                                <MaterialDesignIcon iconName="clock-outline" class="size-3.5" />
                                {t("relay_chat.announced_ago", { time: timeAgo(node.updated_at) })}
                            </span>
                            {#if node.hops != null}
                                <span class="inline-flex items-center gap-1">
                                    <MaterialDesignIcon iconName="transit-connection-variant" class="size-3.5" />
                                    {t("relay_chat.hops_away", { count: node.hops })}
                                </span>
                            {/if}
                        </div>
                    </div>
                    {#if isHubAdded(node.destination_hash)}
                        <button type="button" class={BTN_SECONDARY} onclick={() => onopen?.(node)}>
                            <MaterialDesignIcon iconName="open-in-app" class="size-4" />
                            {t("relay_chat.discovery_open")}
                        </button>
                    {:else}
                        <button type="button" class={BTN_PRIMARY} onclick={() => onadd?.(node)}>
                            <MaterialDesignIcon iconName="plus" class="size-4" />
                            {t("relay_chat.discovery_add")}
                        </button>
                    {/if}
                </div>
            {/each}
        </div>
    </div>
</div>
