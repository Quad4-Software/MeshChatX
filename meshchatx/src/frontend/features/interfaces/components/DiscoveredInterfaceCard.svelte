<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import {
        getDiscoveryIcon,
        formatLastHeard,
        isDiscoveredConnected,
        isDiscoveredBlacklisted,
        discoveredBytes,
        discoveredNetworkName,
        discoveredPassphrase,
        maskPassphrase,
    } from "../lib/interfacesFormat.js";
    import type { DiscoveredInterface, DiscoveredActiveInterface, InterfaceStats } from "../lib/types.js";

    interface Props {
        iface: DiscoveredInterface;
        activeList?: DiscoveredActiveInterface[];
        statsList?: InterfaceStats[];
        activeTransportIds?: Set<string>;
        metadataPresent?: boolean;
        blacklistStr?: string;
        isOpenActionMenu?: boolean;
        savingDiscoveryAction?: boolean;
        ontogglemenu?: () => void;
        onusediscovered?: () => void;
        oncopydiscoveredconfig?: () => void;
        onaddtolist?: (action: "allow" | "block") => void;
        ongotomap?: () => void;
        oncopytext?: (text: string, label: string) => void;
    }

    let {
        iface,
        activeList = [],
        statsList = [],
        activeTransportIds = new Set(),
        metadataPresent = false,
        blacklistStr = "",
        isOpenActionMenu = false,
        savingDiscoveryAction = false,
        ontogglemenu,
        onusediscovered,
        oncopydiscoveredconfig,
        onaddtolist,
        ongotomap,
        oncopytext,
    }: Props = $props();

    const iconName = $derived(getDiscoveryIcon(iface));
    const isConnected = $derived(
        isDiscoveredConnected(iface, activeList, statsList, activeTransportIds, metadataPresent)
    );
    const isBlacklisted = $derived(isDiscoveredBlacklisted(iface, blacklistStr));
    const traffic = $derived(discoveredBytes(iface, activeList, statsList, activeTransportIds, metadataPresent));
    const netName = $derived(discoveredNetworkName(iface));
    const passphrase = $derived(discoveredPassphrase(iface));
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<div
    class="interface-card group transition-all duration-300 min-w-0 {!isConnected
        ? 'opacity-85 md:opacity-70 md:grayscale-[0.3]'
        : ''}"
>
    <div class="flex flex-col gap-3 sm:flex-row sm:gap-4 sm:items-start relative min-w-0">
        <!-- Disconnected Overlay -->
        {#if !isConnected}
            <div
                class="absolute inset-0 z-10 flex items-center justify-center bg-white/25 dark:bg-zinc-900/25 md:backdrop-blur-[0.5px] rounded-3xl pointer-events-none"
            >
                <div
                    class="bg-red-500/90 text-white px-3 py-1.5 rounded-full shadow-lg flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider"
                >
                    <MaterialDesignIcon iconName={isBlacklisted ? "cancel" : "lan-disconnect"} class="w-3.5 h-3.5" />
                    <span>{isBlacklisted ? "Blacklisted" : t("app.disabled")}</span>
                </div>
            </div>
        {/if}

        <div class="interface-card__icon shrink-0">
            <MaterialDesignIcon {iconName} class="w-6 h-6" />
        </div>

        <div class="flex-1 min-w-0 space-y-2">
            <div class="flex items-center gap-2 flex-nowrap min-w-0">
                <div class="text-base sm:text-lg font-semibold text-sem-fg truncate min-w-0">
                    {iface.name}
                </div>
                <span class="type-chip shrink-0">{iface.type}</span>
            </div>

            <div class="flex items-center gap-2 flex-wrap">
                {#if iface.value}
                    <span class="text-[10px] font-bold text-sem-accent">
                        Stamps: {iface.value}
                    </span>
                {/if}
                {#if isConnected}
                    <span
                        class="inline-flex items-center rounded-full bg-emerald-100 text-emerald-700 px-2 py-0.5 text-[10px] font-semibold dark:bg-emerald-900/40 dark:text-emerald-200 shrink-0"
                    >
                        Connected
                    </span>
                {/if}
                {#if iface.is_blacklisted}
                    <span
                        class="inline-flex items-center rounded-full bg-red-100 text-red-700 px-2 py-0.5 text-[10px] font-semibold dark:bg-red-900/40 dark:text-red-200 shrink-0"
                    >
                        Blocked
                    </span>
                {:else if iface.is_allowed === false}
                    <span
                        class="inline-flex items-center rounded-full bg-amber-100 text-amber-700 px-2 py-0.5 text-[10px] font-semibold dark:bg-amber-900/40 dark:text-amber-200 shrink-0"
                    >
                        Not allowed
                    </span>
                {/if}
            </div>

            <div class="flex flex-wrap gap-1.5 text-[10px] sm:text-xs">
                <span class="stat-chip bg-gray-50 dark:bg-zinc-800/50">Hops: {iface.hops ?? 0}</span>
                <span class="stat-chip capitalize bg-gray-50 dark:bg-zinc-800/50">{iface.status ?? ""}</span>
                {#if iface.last_heard}
                    <span class="stat-chip bg-gray-50 dark:bg-zinc-800/50">
                        Heard: {formatLastHeard(iface.last_heard)}
                    </span>
                {/if}
                {#if traffic}
                    <span class="stat-chip bg-gray-50 dark:bg-zinc-800/50">
                        {t("interface.tx")}
                        {traffic.tx}
                    </span>
                    <span class="stat-chip bg-gray-50 dark:bg-zinc-800/50">
                        {t("interface.rx")}
                        {traffic.rx}
                    </span>
                {/if}
            </div>

            <div class="grid gap-1.5 text-[10px] sm:text-[11px] pt-1 min-w-0">
                {#if iface.reachable_on}
                    <!-- svelte-ignore a11y_no_static_element_interactions -->
                    <div
                        class="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-blue-500 cursor-pointer transition-colors min-w-0"
                        onclick={() => oncopytext?.(`${iface.reachable_on}:${iface.port}`, "Address")}
                    >
                        <MaterialDesignIcon iconName="link-variant" class="w-3.5 h-3.5 shrink-0" />
                        <span class="truncate">Address: {iface.reachable_on}:{iface.port}</span>
                    </div>
                {/if}

                {#if iface.transport_id}
                    <!-- svelte-ignore a11y_no_static_element_interactions -->
                    <div
                        class="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-blue-500 cursor-pointer transition-colors min-w-0"
                        onclick={() => oncopytext?.(iface.transport_id || "", "Transport ID")}
                    >
                        <MaterialDesignIcon iconName="identifier" class="w-3.5 h-3.5 shrink-0" />
                        <span class="truncate font-mono">Transport ID: {iface.transport_id}</span>
                    </div>
                {/if}

                {#if iface.network_id}
                    <!-- svelte-ignore a11y_no_static_element_interactions -->
                    <div
                        class="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-blue-500 cursor-pointer transition-colors min-w-0"
                        onclick={() => oncopytext?.(iface.network_id || "", "Network ID")}
                    >
                        <MaterialDesignIcon iconName="lan" class="w-3.5 h-3.5 shrink-0" />
                        <span class="truncate font-mono">Network ID: {iface.network_id}</span>
                    </div>
                {/if}

                {#if netName}
                    <!-- svelte-ignore a11y_no_static_element_interactions -->
                    <div
                        class="flex items-center gap-2 text-amber-700 dark:text-amber-300 hover:text-amber-500 cursor-pointer transition-colors min-w-0"
                        title={t("interfaces.discovered_copy_network_name")}
                        data-testid="discovered-network-name"
                        onclick={() => oncopytext?.(netName || "", t("interfaces.discovered_network_name"))}
                    >
                        <MaterialDesignIcon iconName="shield-key" class="w-3.5 h-3.5 shrink-0" />
                        <span class="truncate font-mono">
                            {t("interfaces.discovered_network_name")}: {netName}
                        </span>
                    </div>
                {/if}

                {#if passphrase}
                    <!-- svelte-ignore a11y_no_static_element_interactions -->
                    <div
                        class="flex items-center gap-2 text-amber-700 dark:text-amber-300 hover:text-amber-500 cursor-pointer transition-colors min-w-0"
                        title={t("interfaces.discovered_copy_passphrase")}
                        data-testid="discovered-passphrase"
                        onclick={() => oncopytext?.(passphrase || "", t("interfaces.discovered_passphrase"))}
                    >
                        <MaterialDesignIcon iconName="shield-lock" class="w-3.5 h-3.5 shrink-0" />
                        <span class="truncate font-mono">
                            {t("interfaces.discovered_passphrase")}: {maskPassphrase(passphrase)}
                        </span>
                    </div>
                {/if}

                {#if iface.latitude != null && iface.longitude != null}
                    <!-- svelte-ignore a11y_no_static_element_interactions -->
                    <div
                        class="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-blue-500 cursor-pointer transition-colors min-w-0"
                        onclick={() => oncopytext?.(`${iface.latitude}, ${iface.longitude}`, "Location")}
                    >
                        <MaterialDesignIcon iconName="map-marker" class="w-3.5 h-3.5 shrink-0" />
                        <span class="truncate">Loc: {iface.latitude}, {iface.longitude}</span>
                    </div>
                {/if}
            </div>
        </div>

        <div class="flex flex-row sm:flex-col gap-2 shrink-0 self-end sm:self-auto justify-end">
            <div class="relative">
                <button
                    type="button"
                    class="secondary-chip p-2! rounded-xl!"
                    title="Discovery actions"
                    onclick={ontogglemenu}
                >
                    <MaterialDesignIcon iconName="dots-vertical" class="w-4 h-4" />
                </button>
                {#if isOpenActionMenu}
                    <!-- svelte-ignore a11y_no_static_element_interactions -->
                    <div class="fixed inset-0 z-10" onclick={ontogglemenu}></div>
                    <div
                        class="absolute right-0 mt-1 z-20 min-w-44 rounded-xl border border-sem-border bg-sem-surface shadow-lg p-1"
                    >
                        <button
                            type="button"
                            class="w-full text-left px-3 py-2 text-xs rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                            data-testid="use-discovered-interface"
                            onclick={onusediscovered}
                        >
                            {t("interfaces.discovered_use_this")}
                        </button>
                        {#if iface.config_entry}
                            <button
                                type="button"
                                class="w-full text-left px-3 py-2 text-xs rounded-lg hover:bg-sem-surface-muted text-gray-700 dark:text-gray-200"
                                data-testid="copy-discovered-config"
                                onclick={oncopydiscoveredconfig}
                            >
                                {t("interfaces.discovered_copy_config")}
                            </button>
                        {/if}
                        <button
                            type="button"
                            class="w-full text-left px-3 py-2 text-xs rounded-lg hover:bg-emerald-50 dark:hover:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300"
                            disabled={savingDiscoveryAction}
                            onclick={() => onaddtolist?.("allow")}
                        >
                            Allow this announce
                        </button>
                        <button
                            type="button"
                            class="w-full text-left px-3 py-2 text-xs rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-red-700 dark:text-red-300"
                            disabled={savingDiscoveryAction}
                            onclick={() => onaddtolist?.("block")}
                        >
                            Blacklist this announce
                        </button>
                    </div>
                {/if}
            </div>

            {#if iface.latitude != null && iface.longitude != null}
                <button
                    type="button"
                    class="secondary-chip p-2! rounded-xl!"
                    title={t("map.title")}
                    onclick={ongotomap}
                >
                    <MaterialDesignIcon iconName="map" class="w-4 h-4" />
                </button>
            {/if}
        </div>
    </div>
</div>

<style>
    .interface-card {
        position: relative;
        background-color: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(4px);
        border: 1px solid var(--sem-border, #e5e7eb);
        border-radius: 1.5rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        padding: 1rem;
        min-width: 0;
        overflow: visible;
    }
    :global(.dark) .interface-card {
        background-color: rgba(24, 24, 27, 0.85);
    }
    .interface-card__icon {
        width: 3rem;
        height: 3rem;
        border-radius: 1rem;
        background-color: rgb(239 246 255);
        color: rgb(37 99 235);
        display: flex;
        align-items: center;
        justify-content: center;
    }
    :global(.dark) .interface-card__icon {
        background-color: rgba(30, 58, 138, 0.4);
        color: rgb(191 219 254);
    }
    .type-chip {
        display: inline-flex;
        align-items: center;
        border-radius: 9999px;
        background-color: var(--sem-surface-muted, #f3f4f6);
        padding: 0.125rem 0.5rem;
        font-size: 0.75rem;
        font-weight: 600;
        color: rgb(75 85 99);
    }
    :global(.dark) .type-chip {
        color: rgb(229 231 235);
    }
    .stat-chip {
        display: inline-flex;
        align-items: center;
        border-radius: 9999px;
        border: 1px solid var(--sem-border, #e5e7eb);
        padding: 0.125rem 0.5rem;
    }
</style>
