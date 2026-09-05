<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import ConversationEmptyState from "./ConversationEmptyState.svelte";
    import GlobalEmitter from "../../../js/GlobalEmitter.js";
    import { copyTextToClipboard } from "../../../js/clipboardUtils.js";
    import type { Conversation, Peer } from "../lib/types.js";
    import type { ComposeSuggestion } from "../lib/conversationViewerSession.js";

    let {
        latestConversations = [] as Conversation[],
        composeAddress = $bindable(""),
        isComposeInputFocused = $bindable(false),
        composeSuggestions = [] as ComposeSuggestion[],
        selectedComposeSuggestionIndex = $bindable(-1),
        myLxmfAddressHash = "",
        formatTimeAgo,
        onupdateSelectedPeer,
        oncomposeenter,
    }: {
        latestConversations?: Conversation[];
        composeAddress?: string;
        isComposeInputFocused?: boolean;
        composeSuggestions?: ComposeSuggestion[];
        selectedComposeSuggestionIndex?: number;
        myLxmfAddressHash?: string;
        formatTimeAgo: (value: unknown) => string;
        onupdateSelectedPeer?: (peer: Peer | null) => void;
        oncomposeenter?: () => void;
    } = $props();
</script>

<ConversationEmptyState
    {latestConversations}
    bind:composeAddress
    bind:isComposeInputFocused
    {composeSuggestions}
    {selectedComposeSuggestionIndex}
    {formatTimeAgo}
    oncompose={() => document.getElementById("compose-input")?.focus()}
    onsync={() => GlobalEmitter.emit("sync-propagation-node")}
    oncopyaddress={() => void copyTextToClipboard(myLxmfAddressHash)}
    onidentities={() => {
        location.hash = "#/identities";
    }}
    onselectpeer={(peer) => onupdateSelectedPeer?.(peer as Peer)}
    oncomposeenter={() => oncomposeenter?.()}
    oncomposeup={() => {
        selectedComposeSuggestionIndex =
            selectedComposeSuggestionIndex > 0
                ? selectedComposeSuggestionIndex - 1
                : composeSuggestions.length - 1;
    }}
    oncomposedown={() => {
        selectedComposeSuggestionIndex =
            selectedComposeSuggestionIndex < composeSuggestions.length - 1
                ? selectedComposeSuggestionIndex + 1
                : 0;
    }}
    oncomposebblur={() =>
        setTimeout(() => {
            isComposeInputFocused = false;
            selectedComposeSuggestionIndex = -1;
        }, 200)}
    onselectsuggestion={(suggestion) => {
        composeAddress = suggestion.hash;
        isComposeInputFocused = false;
        selectedComposeSuggestionIndex = -1;
        oncomposeenter?.();
    }}
/>
