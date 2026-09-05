<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { fade } from "svelte/transition";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../ui/svelte/LxmfUserIcon.svelte";
    import EmptyState from "../../../ui/svelte/EmptyState.svelte";
    import Skeleton from "../../../ui/svelte/Skeleton.svelte";
    import { t } from "../../../js/i18n.js";
    import type { DiscoveryAnnounce } from "../lib/types.js";

    export interface CallDiscoveryIcon {
        icon_name?: string;
        foreground_colour?: string;
        background_colour?: string;
    }

    export interface CallDiscoveryAnnounce {
        destination_hash: string;
        display_name?: string;
        contact_image?: string;
        lxmf_destination_hash?: string;
        updated_at?: number | string;
        hops?: number | null;
        lxmf_user_icon?: CallDiscoveryIcon | null;
        [key: string]: unknown;
    }

    interface Props {
        active?: boolean;
        discoverySearch?: string;
        totalDiscoveryCount?: number;
        discoveryAnnounces?: (CallDiscoveryAnnounce | DiscoveryAnnounce)[];
        hasMoreDiscovery?: boolean;
        isLoading?: boolean;
        formatTimeAgo?: (timestamp?: number | string | null) => string;
        formatDestinationHash: (hash?: string) => string;
        onsearchinput?: (value: string) => void;
        oncopyhash?: (hash: string) => void;
        onloadmore?: () => void;
        oncall?: (destinationHash: string) => void;
    }

    let {
        active = false,
        discoverySearch = "",
        totalDiscoveryCount: _totalDiscoveryCount = 0,
        discoveryAnnounces = [],
        hasMoreDiscovery = false,
        isLoading = false,
        formatTimeAgo = (ts?: number | string | null) => (ts ? String(ts) : ""),
        formatDestinationHash,
        onsearchinput,
        oncopyhash,
        onloadmore,
        oncall,
    }: Props = $props();

    const transitionDuration = $derived(
        typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 120
    );

    function handleSearchInput(event: Event): void {
        const value = (event.target as HTMLInputElement).value;
        onsearchinput?.(value);
    }
</script>

{#if active}
    <div class="flex-1 flex flex-col max-w-3xl mx-auto w-full pt-2" transition:fade={{ duration: transitionDuration }}>
        <div class="mb-4">
            <div class="relative">
                <input
                    value={discoverySearch}
                    type="text"
                    placeholder={t("call.search_phonebook")}
                    class="input-field w-full pl-10"
                    oninput={handleSearchInput}
                />
                <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                    <MaterialDesignIcon iconName="magnify" class="size-5 text-sem-fg-muted" />
                </div>
            </div>
        </div>

        {#if isLoading && discoveryAnnounces.length === 0}
            <div class="space-y-4 p-4">
                <div class="flex items-center gap-4">
                    <Skeleton variant="avatar" />
                    <div class="flex-1 space-y-2">
                        <Skeleton variant="line" class="w-1/3" />
                        <Skeleton variant="line" class="w-1/2" />
                    </div>
                </div>
                <div class="flex items-center gap-4">
                    <Skeleton variant="avatar" />
                    <div class="flex-1 space-y-2">
                        <Skeleton variant="line" class="w-1/4" />
                        <Skeleton variant="line" class="w-2/3" />
                    </div>
                </div>
            </div>
        {:else if discoveryAnnounces.length === 0}
            <EmptyState
                icon="satellite-uplink"
                title={t("call.no_telephony_peers")}
                description={t("call.waiting_for_announces")}
                class="my-auto py-12"
            />
        {:else}
            <div class="space-y-4">
                <div class="border-b border-sem-border overflow-hidden">
                    <ul class="divide-y divide-sem-border-subtle">
                        {#each discoveryAnnounces as announce (announce.destination_hash)}
                            <li class="px-4 py-4 hover:bg-sem-surface-muted/50 transition-colors">
                                <div class="flex items-center space-x-4">
                                    <div class="shrink-0">
                                        <LxmfUserIcon
                                            customImage={announce.contact_image ?? undefined}
                                            iconName={announce.lxmf_user_icon?.icon_name || ""}
                                            iconForegroundColour={announce.lxmf_user_icon?.foreground_colour || ""}
                                            iconBackgroundColour={announce.lxmf_user_icon?.background_colour || ""}
                                            iconClass="size-10"
                                        />
                                    </div>
                                    <div class="flex-1 min-w-0">
                                        <div class="flex items-center justify-between">
                                            <div class="flex items-center min-w-0">
                                                <p class="text-sm font-bold text-sem-fg truncate">
                                                    {announce.display_name || t("call.anonymous_peer")}
                                                </p>
                                                {#if announce.lxmf_destination_hash}
                                                    <a
                                                        href={`/#/messages/${announce.lxmf_destination_hash}`}
                                                        class="ml-2 p-1 text-sem-fg-muted hover:text-sem-accent transition-colors focus-ring-sem rounded-md"
                                                        title={t("call.message_via_lxmf")}
                                                        onclick={(e) => e.stopPropagation()}
                                                    >
                                                        <MaterialDesignIcon
                                                            iconName="message-text-outline"
                                                            class="size-4"
                                                        />
                                                    </a>
                                                {/if}
                                            </div>
                                            <span class="text-[10px] text-sem-fg-muted font-mono ml-2 shrink-0">
                                                {formatTimeAgo(announce.updated_at)}
                                            </span>
                                        </div>
                                        <div class="flex items-center justify-between mt-1">
                                            <div class="flex items-center space-x-2 min-w-0">
                                                <button
                                                    type="button"
                                                    class="text-[10px] text-left text-sem-fg-muted font-mono truncate cursor-pointer hover:text-sem-accent transition-colors focus-ring-sem"
                                                    title={announce.destination_hash}
                                                    onclick={(e) => {
                                                        e.stopPropagation();
                                                        oncopyhash?.(announce.destination_hash);
                                                    }}
                                                >
                                                    {formatDestinationHash(announce.destination_hash)}
                                                </button>
                                                {#if announce.hops != null}
                                                    <span class="text-[10px] text-sem-fg-muted">
                                                        &bull; {announce.hops}
                                                        {t("call.hops")}
                                                    </span>
                                                {/if}
                                            </div>
                                            <button
                                                type="button"
                                                class="text-[10px] bg-sem-accent-subtle text-sem-accent px-3 py-1 rounded-full font-bold uppercase tracking-wider hover:bg-sem-accent-subtle/80 transition-colors shrink-0 focus-ring-sem cursor-pointer"
                                                onclick={() => oncall?.(announce.destination_hash)}
                                            >
                                                {t("call.call_action")}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </li>
                        {/each}
                    </ul>
                    {#if hasMoreDiscovery}
                        <div class="p-3 border-t border-sem-border text-center">
                            <button
                                type="button"
                                class="text-xs text-sem-accent hover:underline font-bold uppercase tracking-widest focus-ring-sem cursor-pointer"
                                onclick={() => onloadmore?.()}
                            >
                                {t("call.load_more")}
                            </button>
                        </div>
                    {/if}
                </div>
            </div>
        {/if}
    </div>
{/if}
