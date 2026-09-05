<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { getDiscoveredIconName } from "../lib/discoveredIcons.js";

    interface ClusterItem {
        kind: string;
        label: string;
        identifier?: string;
        iconKey?: any;
        peer?: {
            lxmf_user_icon?: {
                icon_name?: string;
            };
        };
        [key: string]: unknown;
    }

    interface ClusterData {
        count: number;
        items: ClusterItem[];
    }

    interface Props {
        cluster: ClusterData;
        onclose?: () => void;
        onselect?: (item: ClusterItem) => void;
    }

    let { cluster, onclose, onselect }: Props = $props();
</script>

<div
    class="absolute bottom-4 left-4 right-4 sm:left-4 sm:right-auto sm:w-80 md:max-lg:w-72 lg:w-80 z-20 bg-sem-surface rounded-xl shadow-2xl border border-sem-border overflow-hidden text-sem-fg"
>
    <div class="p-4 border-b border-sem-border flex items-center justify-between">
        <div class="flex items-center gap-3">
            <div class="size-8 rounded-full flex items-center justify-center bg-blue-600 text-white text-sm font-bold">
                {cluster.count}
            </div>
            <div>
                <h3 class="font-bold text-sem-fg">{cluster.count} interfaces here</h3>
                <div class="text-[10px] font-mono text-gray-500 uppercase tracking-tighter">Tap an item to focus</div>
            </div>
        </div>
        <button
            type="button"
            class="text-gray-500 hover:text-gray-700 dark:hover:text-zinc-300 p-1 cursor-pointer"
            title="Close"
            onclick={() => onclose?.()}
        >
            <MaterialDesignIcon iconName="close" class="size-5" />
        </button>
    </div>
    <div class="max-h-72 overflow-y-auto divide-y divide-gray-100 dark:divide-zinc-800">
        {#each cluster.items as item, idx (idx)}
            <button
                type="button"
                class="w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-sem-surface-muted transition-colors cursor-pointer"
                onclick={() => onselect?.(item)}
            >
                {#if item.kind === "discovered"}
                    <div
                        class="size-7 rounded-full flex items-center justify-center border-2 border-emerald-500 bg-emerald-50 text-emerald-600 shrink-0"
                    >
                        <MaterialDesignIcon iconName={getDiscoveredIconName(item.iconKey)} class="size-[14px]" />
                    </div>
                {:else if item.kind === "telemetry"}
                    <div
                        class="size-7 rounded-full flex items-center justify-center border-2 border-blue-500 bg-blue-50 text-blue-600 shrink-0"
                    >
                        <MaterialDesignIcon
                            iconName={item.peer?.lxmf_user_icon?.icon_name || "account"}
                            class="size-3.5"
                        />
                    </div>
                {:else}
                    <div
                        class="size-7 rounded-full flex items-center justify-center border-2 border-gray-400 bg-sem-surface-muted text-sem-fg-muted shrink-0"
                    >
                        <MaterialDesignIcon iconName="help" class="size-3.5" />
                    </div>
                {/if}
                <div class="min-w-0 flex-1">
                    <div class="text-sm font-medium truncate">{item.label}</div>
                    {#if item.identifier}
                        <div class="text-[10px] font-mono text-gray-500 truncate">
                            {item.identifier}
                        </div>
                    {/if}
                </div>
                <MaterialDesignIcon iconName="chevron-right" class="size-4 text-gray-400 shrink-0" />
            </button>
        {/each}
    </div>
</div>
