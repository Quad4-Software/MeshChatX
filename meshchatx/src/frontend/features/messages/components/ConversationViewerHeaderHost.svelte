<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import ConversationPeerHeader from "./ConversationPeerHeader.svelte";
    import ConversationStrangerBanner from "./ConversationStrangerBanner.svelte";
    import type { Peer } from "../lib/types.js";
    import type { ViewerPathSnapshot } from "../lib/conversationViewerCtx.js";

    let {
        selectedPeer,
        hasFailedOrCancelledMessages = false,
        peerPathSnapshot = null as ViewerPathSnapshot | null,
        peerPathLoading = false,
        peerPathWarming = false,
        selectedPeerSignalMetrics = null as Record<string, unknown> | null,
        selectedPeerLxmfStampInfo = null as Record<string, unknown> | null,
        pathfinderInProgress = false,
        isPopout = false,
        isPeerBlocked = false,
        isStrangerPeer = false,
        strangerBannerDismissed = false,
        oneditdisplayname,
        oncopyhash,
        ondestinationpathclick,
        onsignalmetricsclick,
        onstampinfoclick,
        onpathfinderquick,
        onpathfinderforce,
        onpathfinderdrop,
        onping,
        onstartcall,
        onsharecontact,
        onopentelemetryhistory,
        onbanish,
        onunbanish,
        onconversationdeleted,
        onretryfailed,
        onclose,
        onpopout,
        onaddstranger,
        ondismissstranger,
    }: {
        selectedPeer: Peer;
        hasFailedOrCancelledMessages?: boolean;
        peerPathSnapshot?: ViewerPathSnapshot | null;
        peerPathLoading?: boolean;
        peerPathWarming?: boolean;
        selectedPeerSignalMetrics?: Record<string, unknown> | null;
        selectedPeerLxmfStampInfo?: Record<string, unknown> | null;
        pathfinderInProgress?: boolean;
        isPopout?: boolean;
        isPeerBlocked?: boolean;
        isStrangerPeer?: boolean;
        strangerBannerDismissed?: boolean;
        oneditdisplayname?: () => void;
        oncopyhash?: (hash: string) => void;
        ondestinationpathclick?: (path: unknown) => void;
        onsignalmetricsclick?: (metrics: any) => void;
        onstampinfoclick?: (info: any) => void;
        onpathfinderquick?: () => void;
        onpathfinderforce?: () => void;
        onpathfinderdrop?: () => void;
        onping?: () => void;
        onstartcall?: () => void;
        onsharecontact?: () => void;
        onopentelemetryhistory?: () => void;
        onbanish?: () => void;
        onunbanish?: () => void;
        onconversationdeleted?: () => void;
        onretryfailed?: () => void;
        onclose?: () => void;
        onpopout?: () => void;
        onaddstranger?: () => void;
        ondismissstranger?: () => void;
    } = $props();

    const showStrangerBanner = $derived((isStrangerPeer || !selectedPeer.is_known_contact) && !strangerBannerDismissed);
</script>

<ConversationPeerHeader
    selectedPeer={selectedPeer as never}
    compactPeerActions={false}
    {hasFailedOrCancelledMessages}
    selectedPeerPath={(peerPathSnapshot?.path || null) as never}
    {peerPathSnapshot}
    {peerPathLoading}
    {peerPathWarming}
    selectedPeerSignalMetrics={selectedPeerSignalMetrics as never}
    selectedPeerLxmfStampInfo={selectedPeerLxmfStampInfo as never}
    {pathfinderInProgress}
    {isPeerBlocked}
    {oneditdisplayname}
    {oncopyhash}
    {ondestinationpathclick}
    {onsignalmetricsclick}
    {onstampinfoclick}
    {onpathfinderquick}
    {onpathfinderforce}
    {onpathfinderdrop}
    {onping}
    {onstartcall}
    {onsharecontact}
    {onopentelemetryhistory}
    {onbanish}
    {onunbanish}
    {onconversationdeleted}
    {onretryfailed}
    {onclose}
    onpopout={isPopout ? undefined : onpopout}
/>

{#if showStrangerBanner}
    <ConversationStrangerBanner onadd={() => onaddstranger?.()} ondismiss={() => ondismissstranger?.()} />
{/if}
