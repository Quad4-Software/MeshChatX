<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../ui/svelte/LxmfUserIcon.svelte";
    import { t } from "../../../js/i18n.js";

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
        discoveryAnnounces?: CallDiscoveryAnnounce[];
        hasMoreDiscovery?: boolean;
        formatTimeAgo: (timestamp?: number | string) => string;
        formatDestinationHash: (hash?: string) => string;
        onsearchinput?: (value: string) => void;
        oncopyhash?: (hash: string) => void;
        onloadmore?: () => void;
        oncall?: (destinationHash: string) => void;
    }

    let {
        active = false,
        discoverySearch = "",
        totalDiscoveryCount = 0,
        discoveryAnnounces = [],
        hasMoreDiscovery = false,
        formatTimeAgo,
        formatDestinationHash,
        onsearchinput,
        oncopyhash,
        onloadmore,
        oncall,
    }: Props = $props();

    function handleSearchInput(event: Event): void {
        const value = (event.target as HTMLInputElement).value;
        onsearchinput?.(value);
    }
</script>

{#if active}
    <div class="flex-1 flex flex-col max-w-3xl mx-auto w-full pt-2">
        <div class="mb-4">
            <div class="relative">
                <input
                    value={discoverySearch}
                    type="text"
                    placeholder={`Search phonebook (${totalDiscoveryCount})...`}
                    class="block w-full rounded-lg border-0 py-2 pl-10 text-sem-fg shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
                    oninput={handleSearchInput}
                />
                <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                    <MaterialDesignIcon iconName="magnify" class="size-5 text-gray-400" />
                </div>
            </div>
        </div>

        {#if discoveryAnnounces.length === 0}
            <div class="my-auto text-center">
                <div class="bg-gray-200 dark:bg-zinc-800 p-6 rounded-full inline-block mb-4">
                    <MaterialDesignIcon iconName="satellite-uplink" class="size-12 text-gray-400" />
                </div>
                <h3 class="text-lg font-medium text-sem-fg">No Telephony Peers</h3>
                <p class="text-sem-fg-muted">Waiting for announces on the mesh.</p>
            </div>
        {:else}
            <div class="space-y-4">
                <div class="border-b border-sem-border overflow-hidden">
                    <ul class="divide-y divide-gray-100 dark:divide-zinc-800">
                        {#each discoveryAnnounces as announce (announce.destination_hash)}
                            <li class="px-4 py-4 hover:bg-sem-surface-muted/50 transition-colors">
                                <div class="flex items-center space-x-4">
                                    <div class="shrink-0">
                                        <LxmfUserIcon
                                            customImage={announce.contact_image}
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
                                                    {announce.display_name || "Anonymous Peer"}
                                                </p>
                                                {#if announce.lxmf_destination_hash}
                                                    <a
                                                        href={`/#/messages/${announce.lxmf_destination_hash}`}
                                                        class="ml-2 p-1 text-gray-400 hover:text-blue-500 transition-colors"
                                                        title="Message via LXMF"
                                                        onclick={(e) => e.stopPropagation()}
                                                    >
                                                        <MaterialDesignIcon iconName="message-text-outline" class="size-4" />
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
                                                    class="text-[10px] text-left text-sem-fg-muted font-mono truncate cursor-pointer hover:text-blue-500 transition-colors"
                                                    title={announce.destination_hash}
                                                    onclick={(e) => {
                                                        e.stopPropagation();
                                                        oncopyhash?.(announce.destination_hash);
                                                    }}
                                                >
                                                    {formatDestinationHash(announce.destination_hash)}
                                                </button>
                                                {#if announce.hops != null}
                                                    <span class="text-[10px] text-gray-400 dark:text-zinc-600">
                                                        • {announce.hops} hops
                                                    </span>
                                                {/if}
                                            </div>
                                            <button
                                                type="button"
                                                class="text-[10px] bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 px-3 py-1 rounded-full font-bold uppercase tracking-wider hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors shrink-0"
                                                onclick={() => oncall?.(announce.destination_hash)}
                                            >
                                                Call
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
                                class="text-xs text-blue-500 hover:text-blue-600 font-bold uppercase tracking-widest"
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
