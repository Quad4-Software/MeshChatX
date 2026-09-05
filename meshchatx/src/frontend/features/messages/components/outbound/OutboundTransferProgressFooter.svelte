<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script lang="ts">
    import type { ConversationViewerActions, LxmfMessageLike, MessageChatItem } from "../../lib/viewerActions.js";

    let {
        lxmfMessage,
        chatItem,
        actions,
        variant = "bubble",
    }: {
        lxmfMessage: LxmfMessageLike;
        chatItem: MessageChatItem;
        actions: ConversationViewerActions;
        variant?: "bubble" | "image";
    } = $props();

    const statsLabel = $derived(actions.outboundTransferStatsLabel(lxmfMessage, chatItem));
    const shellClass = $derived(
        variant === "image"
            ? "bg-black/75 backdrop-blur-md px-2.5 py-1.5"
            : "border-t border-black/8 dark:border-white/10 bg-black/[0.04] dark:bg-white/[0.05] px-3 py-1.5"
    );
    const trackClass = $derived(variant === "image" ? "bg-white/20" : "bg-gray-200/90 dark:bg-zinc-700/90");
    const barClass = $derived(variant === "image" ? "bg-white" : "bg-blue-500 dark:bg-blue-400");
    const percentClass = $derived(variant === "image" ? "text-white/95" : "text-sem-fg-muted");
    const statsClass = $derived(variant === "image" ? "text-white/75" : "text-sem-fg-muted");
</script>

{#if actions.showOutboundTransferProgress(lxmfMessage)}
    <div class="w-full shrink-0 {shellClass}">
        <div class="flex items-center gap-1.5">
            <div class="flex-1 h-1 rounded-full overflow-hidden {trackClass}">
                <div
                    class="h-full rounded-full transition-all duration-300 {barClass}"
                    style:width={`${actions.outboundTransferProgressPercent(lxmfMessage)}%`}
                ></div>
            </div>
            <span class="text-[10px] font-semibold tabular-nums shrink-0 {percentClass}">
                {actions.outboundSendingProgressLabel(lxmfMessage)}
            </span>
        </div>
        {#if statsLabel}
            <div class="text-[9px] tabular-nums truncate mt-0.5 leading-tight {statsClass}">
                {statsLabel}
            </div>
        {/if}
    </div>
{/if}
