<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../ui/svelte/LxmfUserIcon.svelte";
    import Utils from "../../../js/Utils.js";
    import GlobalState from "../../../js/GlobalState.js";
    import { fromNow } from "../../../libs/datetime.js";
    import { t } from "../../../js/i18n.js";

    type Peer = {
        destination_hash?: string;
        display_name?: string;
        custom_display_name?: string | null;
        contact_image?: string;
        lxmf_user_icon?: {
            icon_name?: string;
            foreground_colour?: string;
            background_colour?: string;
        } | null;
    };

    type PathInfo = {
        hops?: number;
        next_hop?: string;
        next_hop_interface?: string;
    } | null;
    type PathSnapshot = { path_stale?: boolean; path_unresponsive?: boolean } | null;
    type SignalMetrics = { snr?: number | null } | null;
    type StampInfo = {
        stamp_cost?: number | string | null;
        outbound_ticket_expiry?: number | null;
    } | null;

    let {
        selectedPeer,
        compactPeerActions = false,
        hasFailedOrCancelledMessages = false,
        selectedPeerPath = null as PathInfo,
        peerPathSnapshot = null as PathSnapshot,
        peerPathLoading = false,
        peerPathWarming = false,
        selectedPeerSignalMetrics = null as SignalMetrics,
        selectedPeerLxmfStampInfo = null as StampInfo,
        pathfinderInProgress = false,
        isPeerBlocked = false,
        oneditdisplayname,
        oncopyhash,
        ondestinationpathclick,
        onsignalmetricsclick,
        onstampinfoclick,
        onconversationdeleted,
        onpopout,
        onretryfailed,
        onopentelemetryhistory,
        onstartcall,
        onsharecontact,
        onping,
        onbanish,
        onunbanish,
        onclose,
        onpathfinderquick,
        onpathfinderforce,
        onpathfinderdrop,
    }: {
        selectedPeer: Peer;
        compactPeerActions?: boolean;
        hasFailedOrCancelledMessages?: boolean;
        selectedPeerPath?: PathInfo;
        peerPathSnapshot?: PathSnapshot;
        peerPathLoading?: boolean;
        peerPathWarming?: boolean;
        selectedPeerSignalMetrics?: SignalMetrics;
        selectedPeerLxmfStampInfo?: StampInfo;
        pathfinderInProgress?: boolean;
        isPeerBlocked?: boolean;
        oneditdisplayname?: () => void;
        oncopyhash?: (hash: string) => void;
        ondestinationpathclick?: (path: PathInfo) => void;
        onsignalmetricsclick?: (metrics: SignalMetrics) => void;
        onstampinfoclick?: (info: StampInfo) => void;
        onconversationdeleted?: () => void;
        onpopout?: () => void;
        onretryfailed?: () => void;
        onopentelemetryhistory?: () => void;
        onstartcall?: () => void;
        onsharecontact?: () => void;
        onping?: () => void;
        onbanish?: () => void;
        onunbanish?: () => void;
        onclose?: () => void;
        onpathfinderquick?: () => void;
        onpathfinderforce?: () => void;
        onpathfinderdrop?: () => void;
    } = $props();

    let pathMenuOpen = $state(false);
    let moreMenuOpen = $state(false);
    let pathMenuRoot: HTMLDivElement | undefined = $state();
    let moreMenuRoot: HTMLDivElement | undefined = $state();

    const destinationDisplay = $derived(Utils.formatDestinationHash(selectedPeer?.destination_hash));
    const messageIconStyle = $derived.by(() => {
        const cfg = GlobalState.config as { message_icon_size?: number } | null | undefined;
        const size = Number(cfg?.message_icon_size) || 28;
        return { width: `${size}px`, height: `${size}px` };
    });
    const peerPathBusy = $derived(pathfinderInProgress || peerPathWarming);
    const showPeerPathRow = $derived(
        peerPathBusy || peerPathLoading || selectedPeerPath != null || (peerPathSnapshot != null && !selectedPeerPath)
    );

    const peerPathRowLabel = $derived.by(() => {
        if (peerPathBusy) return t("messages.outbound_pathfinding_short");
        if (peerPathLoading && !selectedPeerPath) return t("messages.path_loading");
        if (selectedPeerPath) {
            let label =
                selectedPeerPath.hops === 0 || selectedPeerPath.hops === 1
                    ? t("messages.direct")
                    : t("messages.hops_away", { count: selectedPeerPath.hops });
            if (peerPathSnapshot?.path_stale) label += ` (${t("messages.path_stale_label")})`;
            else if (peerPathSnapshot?.path_unresponsive) label += ` (${t("messages.path_unresponsive_label")})`;
            return label;
        }
        return t("messages.path_no_route");
    });

    const peerPathRowClass = $derived.by(() => {
        const base = "cursor-pointer hover:text-gray-700 hover:text-sem-fg";
        if (peerPathBusy) return `${base} text-sem-accent`;
        if (!selectedPeerPath) return `${base} text-amber-700 dark:text-amber-400`;
        if (peerPathSnapshot?.path_stale || peerPathSnapshot?.path_unresponsive) {
            return `${base} text-amber-700 dark:text-amber-400`;
        }
        return base;
    });

    const peerPathRowTitle = $derived.by(() => {
        if (peerPathBusy) return t("messages.outbound_pathfinding_tooltip");
        if (!selectedPeerPath) return t("messages.path_no_route_hint");
        return t("messages.path_info_title");
    });

    const lxmfHasOutboundTicket = $derived(selectedPeerLxmfStampInfo?.outbound_ticket_expiry != null);
    const lxmfStampTicketExpiryMs = $derived.by(() => {
        const e = selectedPeerLxmfStampInfo?.outbound_ticket_expiry;
        if (e == null) return null;
        const n = Number(e);
        return Number.isFinite(n) ? n * 1000 : null;
    });
    const lxmfStampTicketValid = $derived(lxmfStampTicketExpiryMs != null && lxmfStampTicketExpiryMs > Date.now());
    const lxmfStampTicketTitle = $derived(
        lxmfStampTicketValid
            ? t("messages.stamp_ticket_valid", {
                  expires: lxmfStampTicketExpiryMs != null ? fromNow(lxmfStampTicketExpiryMs) : "",
              })
            : t("messages.stamp_ticket_expired")
    );

    $effect(() => {
        if (!pathMenuOpen && !moreMenuOpen) return;
        const onDoc = (event: MouseEvent) => {
            const target = event.target as Node;
            if (pathMenuOpen && pathMenuRoot && !pathMenuRoot.contains(target)) pathMenuOpen = false;
            if (moreMenuOpen && moreMenuRoot && !moreMenuRoot.contains(target)) moreMenuOpen = false;
        };
        document.addEventListener("mousedown", onDoc, true);
        return () => document.removeEventListener("mousedown", onDoc, true);
    });
</script>

<div class="relative z-20 flex items-center gap-2 px-3 sm:px-4 py-2 border-b border-sem-border bg-sem-canvas">
    <div class="shrink-0 self-center">
        <LxmfUserIcon
            customImage={selectedPeer.contact_image || ""}
            iconName={selectedPeer.lxmf_user_icon?.icon_name || ""}
            iconForegroundColour={selectedPeer.lxmf_user_icon?.foreground_colour || ""}
            iconBackgroundColour={selectedPeer.lxmf_user_icon?.background_colour || ""}
            iconClass="shrink-0"
            iconStyle={messageIconStyle}
        />
    </div>

    <div class="min-w-0 flex-1 flex flex-col justify-center">
        <button
            type="button"
            class="flex items-center cursor-pointer min-w-0 group text-left"
            onclick={() => oneditdisplayname?.()}
        >
            {#if selectedPeer.custom_display_name != null}
                <div
                    class="mr-1.5 text-sem-fg-muted group-hover:text-gray-700 dark:group-hover:text-zinc-200 transition-colors"
                    title={t("messages.custom_display_name")}
                >
                    <MaterialDesignIcon iconName="tag-outline" class="size-4" />
                </div>
            {/if}
            <div
                class="font-semibold text-sem-fg truncate max-w-[min(40vw,12rem)] sm:max-w-sm text-base"
                title={selectedPeer.custom_display_name ?? selectedPeer.display_name}
            >
                {selectedPeer.custom_display_name ?? selectedPeer.display_name}
            </div>
        </button>
        <div class="text-xs text-sem-fg-muted mt-0.5 flex items-center gap-2 min-w-0">
            <button
                type="button"
                class="cursor-pointer hover:text-blue-500 transition-colors truncate max-w-[min(40vw,12rem)] sm:max-w-none shrink-0"
                title={selectedPeer.destination_hash}
                onclick={() => oncopyhash?.(String(selectedPeer.destination_hash || ""))}
            >
                {destinationDisplay}
            </button>

            {#if showPeerPathRow || selectedPeerSignalMetrics?.snr != null || selectedPeerLxmfStampInfo?.stamp_cost || lxmfHasOutboundTicket}
                <div class="hidden sm:flex items-center gap-2 min-w-0">
                    <span class="text-gray-300 dark:text-zinc-700 shrink-0">•</span>
                    <div class="flex items-center gap-2 truncate">
                        {#if showPeerPathRow}
                            <button
                                type="button"
                                class="flex items-center gap-1 shrink-0 {peerPathRowClass}"
                                title={peerPathRowTitle}
                                onclick={() => {
                                    if (selectedPeerPath) ondestinationpathclick?.(selectedPeerPath);
                                }}
                            >
                                {#if peerPathBusy}
                                    <MaterialDesignIcon iconName="loading" class="size-3.5 animate-spin shrink-0" />
                                {/if}
                                <span>{peerPathRowLabel}</span>
                            </button>
                        {/if}
                        {#if selectedPeerSignalMetrics?.snr != null}
                            <span class="flex items-center gap-2 shrink-0">
                                <span class="text-gray-300 dark:text-zinc-700 opacity-50">•</span>
                                <button
                                    type="button"
                                    class="cursor-pointer hover:text-sem-fg"
                                    title="Signal quality"
                                    onclick={() => onsignalmetricsclick?.(selectedPeerSignalMetrics)}
                                >
                                    {t("messages.snr", { snr: selectedPeerSignalMetrics.snr })}
                                </button>
                            </span>
                        {/if}
                        {#if selectedPeerLxmfStampInfo?.stamp_cost || lxmfHasOutboundTicket}
                            <span class="flex items-center gap-1 shrink-0">
                                <span class="text-gray-300 dark:text-zinc-700 opacity-50">•</span>
                                {#if lxmfHasOutboundTicket}
                                    <span title={lxmfStampTicketTitle}>
                                        <MaterialDesignIcon
                                            iconName="ticket-confirmation"
                                            class="size-3.5 shrink-0 {lxmfStampTicketValid
                                                ? 'text-emerald-600 dark:text-emerald-400'
                                                : 'text-amber-600 dark:text-amber-500'}"
                                        />
                                    </span>
                                {/if}
                                {#if selectedPeerLxmfStampInfo?.stamp_cost}
                                    <button
                                        type="button"
                                        class="cursor-pointer hover:text-sem-fg"
                                        title="LXMF stamp requirement"
                                        onclick={() => onstampinfoclick?.(selectedPeerLxmfStampInfo)}
                                    >
                                        {t("messages.stamp_cost", { cost: selectedPeerLxmfStampInfo.stamp_cost })}
                                    </button>
                                {/if}
                            </span>
                        {/if}
                    </div>
                </div>
            {/if}
        </div>
    </div>

    <div class="ml-auto flex items-center gap-0.5 sm:gap-1.5 min-w-0 shrink-0">
        {#if !compactPeerActions}
            <div bind:this={pathMenuRoot} class="relative shrink-0" data-testid="conversation-path-ops">
                <button
                    type="button"
                    class="inline-flex items-center justify-center size-11 rounded-xl text-sem-fg-muted hover:bg-sem-surface-muted focus-ring-sem"
                    title={t("nomadnet.path_finder")}
                    disabled={pathfinderInProgress}
                    onclick={() => {
                        pathMenuOpen = !pathMenuOpen;
                    }}
                >
                    <MaterialDesignIcon
                        iconName={pathfinderInProgress ? "loading" : "map-marker-path"}
                        class="size-5 {pathfinderInProgress ? 'animate-spin' : ''}"
                    />
                </button>
                {#if pathMenuOpen}
                    <div
                        class="absolute right-0 top-full mt-1 z-30 min-w-[14rem] rounded-xl bg-sem-surface shadow-lg ring-1 ring-sem-border overflow-hidden"
                    >
                        <button
                            type="button"
                            class="w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-sem-surface-muted"
                            onclick={() => {
                                pathMenuOpen = false;
                                onpathfinderquick?.();
                            }}
                        >
                            <MaterialDesignIcon iconName="flash" class="size-5" />
                            <span>{t("nomadnet.path_finder_quick_request")}</span>
                        </button>
                        <button
                            type="button"
                            class="w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-sem-surface-muted"
                            onclick={() => {
                                pathMenuOpen = false;
                                onpathfinderforce?.();
                            }}
                        >
                            <MaterialDesignIcon iconName="map-marker-radius" class="size-5" />
                            <span>{t("nomadnet.path_finder_force_find")}</span>
                        </button>
                        <button
                            type="button"
                            class="w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-sem-surface-muted"
                            onclick={() => {
                                pathMenuOpen = false;
                                onpathfinderdrop?.();
                            }}
                        >
                            <MaterialDesignIcon iconName="reload-alert" class="size-5" />
                            <span>{t("nomadnet.path_finder_drop_and_request")}</span>
                        </button>
                    </div>
                {/if}
            </div>
        {/if}

        <div bind:this={moreMenuRoot} class="relative shrink-0">
            <button
                type="button"
                class="inline-flex items-center justify-center size-11 rounded-xl text-sem-fg-muted hover:bg-sem-surface-muted focus-ring-sem"
                title={t("messages.more_actions")}
                onclick={() => {
                    moreMenuOpen = !moreMenuOpen;
                }}
            >
                <MaterialDesignIcon iconName="dots-vertical" class="size-5" />
            </button>
            {#if moreMenuOpen}
                <div
                    class="absolute right-0 top-full mt-1 z-30 min-w-[14rem] rounded-xl bg-sem-surface shadow-lg ring-1 ring-sem-border overflow-hidden py-1"
                >
                    <button
                        type="button"
                        class="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-sem-fg hover:bg-sem-surface-muted"
                        onclick={() => {
                            moreMenuOpen = false;
                            oneditdisplayname?.();
                        }}
                    >
                        <MaterialDesignIcon iconName="account-edit" class="size-5 shrink-0" />
                        <span>{t("messages.set_custom_display_name")}</span>
                    </button>
                    <button
                        type="button"
                        class="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-sem-fg hover:bg-sem-surface-muted"
                        onclick={() => {
                            moreMenuOpen = false;
                            onstartcall?.();
                        }}
                    >
                        <MaterialDesignIcon iconName="phone" class="size-5 shrink-0" />
                        <span>{t("messages.start_call")}</span>
                    </button>
                    <button
                        type="button"
                        class="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-sem-fg hover:bg-sem-surface-muted"
                        onclick={() => {
                            moreMenuOpen = false;
                            onsharecontact?.();
                        }}
                    >
                        <MaterialDesignIcon iconName="notebook-outline" class="size-5 shrink-0" />
                        <span>{t("messages.share_contact")}</span>
                    </button>
                    <button
                        type="button"
                        class="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-sem-fg hover:bg-sem-surface-muted"
                        onclick={() => {
                            moreMenuOpen = false;
                            onping?.();
                        }}
                    >
                        <MaterialDesignIcon iconName="flash" class="size-5 shrink-0" />
                        <span>{t("messages.ping_peer")}</span>
                    </button>
                    <button
                        type="button"
                        class="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-sem-fg hover:bg-sem-surface-muted"
                        onclick={() => {
                            moreMenuOpen = false;
                            onopentelemetryhistory?.();
                        }}
                    >
                        <MaterialDesignIcon iconName="satellite-variant" class="size-5 shrink-0" />
                        <span>{t("messages.telemetry_history")}</span>
                    </button>
                    <button
                        type="button"
                        class="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-sem-fg hover:bg-sem-surface-muted"
                        onclick={() => {
                            moreMenuOpen = false;
                            onpopout?.();
                        }}
                    >
                        <MaterialDesignIcon iconName="open-in-new" class="size-5 shrink-0" />
                        <span>{t("messages.pop_out_chat")}</span>
                    </button>
                    {#if hasFailedOrCancelledMessages}
                        <button
                            type="button"
                            class="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-amber-600 hover:bg-sem-surface-muted"
                            onclick={() => {
                                moreMenuOpen = false;
                                onretryfailed?.();
                            }}
                        >
                            <MaterialDesignIcon iconName="refresh" class="size-5 shrink-0 text-amber-600" />
                            <span>{t("messages.retry_failed")}</span>
                        </button>
                    {/if}
                    <div class="border-t border-sem-border my-1"></div>
                    {#if isPeerBlocked}
                        <button
                            type="button"
                            class="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-emerald-600 hover:bg-sem-surface-muted"
                            onclick={() => {
                                moreMenuOpen = false;
                                onunbanish?.();
                            }}
                        >
                            <MaterialDesignIcon iconName="check-circle" class="size-5 shrink-0 text-emerald-600" />
                            <span>{t("banishment.lift_banishment")}</span>
                        </button>
                    {:else}
                        <button
                            type="button"
                            class="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-red-600 hover:bg-sem-surface-muted"
                            onclick={() => {
                                moreMenuOpen = false;
                                onbanish?.();
                            }}
                        >
                            <MaterialDesignIcon iconName="gavel" class="size-5 shrink-0 text-red-600" />
                            <span>{t("messages.banish_user")}</span>
                        </button>
                    {/if}
                    <button
                        type="button"
                        class="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-red-600 hover:bg-sem-surface-muted"
                        onclick={() => {
                            moreMenuOpen = false;
                            onconversationdeleted?.();
                        }}
                    >
                        <MaterialDesignIcon iconName="delete" class="size-5 shrink-0 text-red-600" />
                        <span>{t("messages.delete_message_history")}</span>
                    </button>
                </div>
            {/if}
        </div>

        <button
            type="button"
            data-testid="conversation-close"
            title={compactPeerActions ? t("messages.back_to_list") : t("common.close")}
            class="inline-flex items-center justify-center size-11 rounded-xl text-sem-fg-muted hover:bg-sem-surface-muted focus-ring-sem shrink-0"
            onclick={() => onclose?.()}
        >
            <MaterialDesignIcon iconName={compactPeerActions ? "arrow-left" : "close"} class="size-5" />
        </button>
    </div>
</div>
