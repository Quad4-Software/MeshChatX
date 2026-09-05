<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import DialogUtils from "../../../js/DialogUtils.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import IconButton from "../../../ui/svelte/IconButton.svelte";
    import { t } from "../../../js/i18n.js";
    import {
        formatBitsPerSecond,
        formatBytes,
        getInterfaceIcon,
        getInterfaceDescription,
        isInterfaceEnabled,
        getLinkStatus,
        isDiscoverable,
    } from "../lib/interfacesFormat.js";
    import type { ConfiguredInterface } from "../lib/types.js";
    import InterfaceCardDetails from "./InterfaceCardDetails.svelte";

    interface Props {
        iface: ConfiguredInterface;
        isReticulumRunning?: boolean;
        showRestartBanner?: boolean;
        onenable?: () => void;
        ondisable?: () => void;
        onedit?: () => void;
        onexport?: () => void;
        ondelete?: () => void;
    }

    let {
        iface,
        isReticulumRunning = true,
        showRestartBanner = false,
        onenable,
        ondisable,
        onedit,
        onexport,
        ondelete,
    }: Props = $props();

    let isMenuOpen = $state(false);

    const iconName = $derived(getInterfaceIcon(iface));
    const description = $derived(getInterfaceDescription(iface));
    const enabled = $derived(isInterfaceEnabled(iface));
    const linkStatus = $derived(getLinkStatus(iface, isReticulumRunning));
    const discoverable = $derived(isDiscoverable(iface.discoverable));

    const statusChipClass = $derived(
        enabled
            ? "inline-flex items-center rounded-full bg-green-500/15 text-green-600 dark:text-green-400 px-2 py-0.5 text-xs font-semibold"
            : "inline-flex items-center rounded-full bg-red-500/15 text-red-600 dark:text-red-400 px-2 py-0.5 text-xs font-semibold"
    );

    function isIfaceStatBytesZero(field: "txb" | "rxb"): boolean {
        const st = iface._stats;
        if (!st) return false;
        const raw = st[field];
        const n = raw == null ? 0 : Number(raw);
        return (Number.isFinite(n) ? n : 0) === 0;
    }

    function onIFACSignatureClick(sig: string) {
        DialogUtils.alert(sig);
    }

    function toggleMenu() {
        isMenuOpen = !isMenuOpen;
    }

    function handleEdit() {
        isMenuOpen = false;
        onedit?.();
    }

    function handleExport() {
        isMenuOpen = false;
        onexport?.();
    }

    function handleDelete() {
        isMenuOpen = false;
        ondelete?.();
    }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<div
    class="interface-card min-w-0 transition-all duration-300 {!enabled ||
    iface._restart_required ||
    !isReticulumRunning
        ? 'opacity-60 grayscale-[0.5]'
        : ''} {iface._restart_required && showRestartBanner && isReticulumRunning
        ? 'border-amber-500 ring-amber-500 ring-2'
        : ''}"
>
    <div class="flex flex-col sm:flex-row gap-4 sm:items-start relative pt-11 sm:pt-0">
        <!-- Offline Overlay -->
        {#if !isReticulumRunning}
            <div
                class="absolute inset-0 z-10 flex items-center justify-center bg-white/20 dark:bg-zinc-900/20 backdrop-blur-[0.5px] rounded-3xl pointer-events-none"
            >
                <div
                    class="bg-red-500/90 text-white px-3 py-1.5 rounded-full shadow-lg flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider"
                >
                    <MaterialDesignIcon iconName="lan-disconnect" class="w-3.5 h-3.5" />
                    <span>{t("interfaces.reticulum_offline")}</span>
                </div>
            </div>
        {/if}

        <!-- Restart Required Overlay -->
        {#if isReticulumRunning && iface._restart_required}
            <div
                class="absolute inset-0 z-10 flex items-center justify-center bg-white/20 dark:bg-zinc-900/20 backdrop-blur-[0.5px] rounded-3xl pointer-events-none"
            >
                <div
                    class="bg-amber-500/90 text-white px-3 py-1.5 rounded-full shadow-lg flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider"
                >
                    <MaterialDesignIcon iconName="restart" class="w-3.5 h-3.5" />
                    <span>{t("interfaces.restart_required")}</span>
                </div>
            </div>
        {/if}

        <div class="flex gap-4 min-w-0 flex-1 sm:flex-initial">
            <div class="interface-card__icon shrink-0">
                <MaterialDesignIcon {iconName} class="w-6 h-6" />
            </div>
            <div class="flex-1 min-w-0 space-y-2 overflow-hidden">
                <div class="flex items-center gap-2 flex-wrap">
                    <div class="text-lg font-semibold text-sem-fg truncate min-w-0">
                        {iface._name}
                    </div>
                    <span
                        class="inline-flex items-center rounded-full bg-sem-surface-muted px-2 py-0.5 text-xs font-semibold text-sem-fg shrink-0"
                    >
                        {iface.type}
                    </span>
                    <span class="{statusChipClass} shrink-0">
                        {enabled ? t("app.enabled") : t("app.disabled")}
                    </span>
                    {#if isReticulumRunning && enabled}
                        <span class="{linkStatus.chipClass} shrink-0">
                            {t(linkStatus.labelKey)}
                        </span>
                    {/if}
                    {#if discoverable}
                        <span class="discoverable-chip shrink-0">Discoverable</span>
                    {/if}
                </div>
                <div class="text-sm text-sem-fg-muted wrap-break-word min-w-0">
                    {description}
                </div>
                <div class="flex flex-wrap gap-2 text-xs text-sem-fg-muted">
                    {#if iface._stats?.bitrate}
                        <span class="stat-chip">
                            {t("interface.bitrate")}
                            {formatBitsPerSecond(iface._stats.bitrate)}
                        </span>
                    {/if}
                    {#if iface._stats?.gravity != null}
                        <span class="stat-chip">
                            {t("interface.gravity")}
                            {iface._stats.gravity}
                        </span>
                    {/if}
                    <span class="stat-chip {isIfaceStatBytesZero('txb') ? 'stat-chip--zero-traffic' : ''}">
                        {t("interface.tx")}
                        {formatBytes(iface._stats?.txb ?? 0)}
                    </span>
                    <span class="stat-chip {isIfaceStatBytesZero('rxb') ? 'stat-chip--zero-traffic' : ''}">
                        {t("interface.rx")}
                        {formatBytes(iface._stats?.rxb ?? 0)}
                    </span>
                    {#if iface.type === "RNodeInterface" && iface._stats?.noise_floor}
                        <span class="stat-chip">
                            {t("interface.noise")}
                            {iface._stats.noise_floor} dBm
                        </span>
                    {/if}
                    {#if iface._stats?.clients != null}
                        <span class="stat-chip">
                            {t("interface.clients")}
                            {iface._stats.clients}
                        </span>
                    {/if}
                </div>
                {#if iface._stats?.ifac_signature}
                    <div class="ifac-line">
                        <span class="text-emerald-500 font-semibold">{(iface._stats.ifac_size || 0) * 8}-bit IFAC</span>
                        {#if iface._stats.ifac_netname}
                            <span>• {iface._stats.ifac_netname}</span>
                        {/if}
                        <span>•</span>
                        <button
                            type="button"
                            class="text-blue-500 hover:underline"
                            onclick={() => onIFACSignatureClick(iface._stats?.ifac_signature || "")}
                        >
                            <span class="font-mono">{iface._stats.ifac_signature.slice(0, 8)}</span>…<span
                                class="font-mono">{iface._stats.ifac_signature.slice(-8)}</span
                            >
                        </button>
                    </div>
                {/if}
            </div>
        </div>

        <div
            class="flex flex-row items-center gap-1 sm:relative sm:z-auto sm:flex sm:flex-row sm:gap-2 sm:items-center sm:shrink-0 sm:justify-end mt-4 sm:mt-0"
        >
            {#if enabled}
                <button
                    type="button"
                    class="inline-flex items-center justify-center rounded-full p-2 min-w-[44px] min-h-[44px] sm:min-w-0 sm:min-h-0 shrink-0 border-0 bg-transparent text-sem-fg-muted hover:bg-sem-surface-muted transition-colors"
                    title={t("interface.disable")}
                    onclick={ondisable}
                >
                    <MaterialDesignIcon iconName="power" class="w-5 h-5 sm:w-4 sm:h-4" />
                    <span class="hidden sm:inline sm:ml-1.5 text-xs font-semibold">{t("interface.disable")}</span>
                </button>
            {:else}
                <button
                    type="button"
                    class="inline-flex items-center justify-center rounded-full p-2 min-w-[44px] min-h-[44px] sm:min-w-0 sm:min-h-0 shrink-0 border-0 bg-transparent text-green-600 dark:text-green-400 hover:bg-sem-surface-muted transition-colors"
                    title={t("interface.enable")}
                    onclick={onenable}
                >
                    <MaterialDesignIcon iconName="power" class="w-5 h-5 sm:w-4 sm:h-4" />
                    <span class="hidden sm:inline sm:ml-1.5 text-xs font-semibold">{t("interface.enable")}</span>
                </button>
            {/if}

            <div class="relative z-50 shrink-0">
                <IconButton onclick={toggleMenu}>
                    <MaterialDesignIcon iconName="dots-vertical" class="w-5 h-5" />
                </IconButton>

                {#if isMenuOpen}
                    <!-- svelte-ignore a11y_no_static_element_interactions -->
                    <div class="fixed inset-0 z-40" onclick={() => (isMenuOpen = false)}></div>
                    <div
                        class="absolute right-0 mt-1 z-50 min-w-44 rounded-xl border border-sem-border bg-sem-surface shadow-lg p-1 space-y-1"
                    >
                        <button
                            type="button"
                            class="w-full flex items-center gap-2 px-3 py-2 text-xs rounded-lg hover:bg-sem-surface-muted text-sem-fg text-left"
                            onclick={handleEdit}
                        >
                            <MaterialDesignIcon iconName="pencil" class="w-4 h-4" />
                            <span>{t("interface.edit_interface")}</span>
                        </button>
                        <button
                            type="button"
                            class="w-full flex items-center gap-2 px-3 py-2 text-xs rounded-lg hover:bg-sem-surface-muted text-sem-fg text-left"
                            onclick={handleExport}
                        >
                            <MaterialDesignIcon iconName="export" class="w-4 h-4" />
                            <span>{t("interface.export_interface")}</span>
                        </button>
                        <button
                            type="button"
                            class="w-full flex items-center gap-2 px-3 py-2 text-xs rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500 text-left"
                            onclick={handleDelete}
                        >
                            <MaterialDesignIcon iconName="trash-can" class="w-4 h-4 text-red-500" />
                            <span>{t("interface.delete_interface")}</span>
                        </button>
                    </div>
                {/if}
            </div>
        </div>
    </div>

    <InterfaceCardDetails {iface} />
</div>

<style>
    .interface-card {
        position: relative;
        background-color: var(--mc-surface);
        border: 1px solid var(--mc-border-card);
        border-radius: 1.5rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        padding: 1rem;
        min-width: 0;
        overflow: visible;
    }
    .interface-card:hover {
        z-index: 10;
    }
    .interface-card__icon {
        width: 3rem;
        height: 3rem;
        border-radius: 1rem;
        background-color: color-mix(in srgb, var(--mc-accent) 15%, transparent);
        color: var(--mc-accent);
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .stat-chip {
        display: inline-flex;
        align-items: center;
        border-radius: 9999px;
        border: 1px solid var(--mc-border);
        padding: 0.125rem 0.5rem;
    }
    .stat-chip--zero-traffic {
        border-color: rgb(248 113 113);
        background-color: rgb(254 242 242);
        color: rgb(153 27 27);
        font-weight: 600;
    }
    :global(.dark) .stat-chip--zero-traffic {
        border-color: rgb(185 28 28);
        background-color: rgba(69, 10, 10, 0.5);
        color: rgb(254 202 202);
    }
    .ifac-line {
        font-size: 0.75rem;
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.25rem;
    }
    .discoverable-chip {
        display: inline-flex;
        align-items: center;
        border-radius: 9999px;
        background-color: rgb(219 234 254);
        color: rgb(29 78 216);
        padding: 0.125rem 0.5rem;
        font-size: 0.75rem;
        font-weight: 600;
    }
    :global(.dark) .discoverable-chip {
        background-color: rgba(30, 58, 138, 0.5);
        color: rgb(191 219 254);
    }
</style>
