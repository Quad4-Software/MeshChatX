<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { paneFlexValue } from "../lib/paneLayout.js";
    import type { Conversation, MessagesConfig, Pane, Peer } from "../lib/types.js";
    import ConversationViewer, { type ConversationViewerApi } from "./ConversationViewer.svelte";

    type Props = {
        visiblePanes?: Pane[];
        focusedPaneId?: number;
        multiPaneActive?: boolean;
        canAddPane?: boolean;
        paneFlex?: Record<number, number>;
        resizingPaneIds?: string | null;
        dragOverPaneId?: number | null;
        isDragOverAddZone?: boolean;
        config?: MessagesConfig | null;
        conversations?: Conversation[];
        isPopout?: boolean;
        onfocusPane?: (paneId: number) => void;
        onaddPane?: () => void;
        onstartPaneResize?: (event: PointerEvent, leftPaneId: number, rightPaneId: number) => void;
        onresetPaneSizes?: () => void;
        onpaneDragOver?: (paneId: number) => void;
        onpaneDragLeave?: (paneId: number) => void;
        onpaneDrop?: (paneId: number, event: DragEvent) => void;
        onaddZoneDragOver?: () => void;
        onaddZoneDragLeave?: () => void;
        onaddZoneDrop?: (event: DragEvent) => void;
        onpanePeerUpdate?: (paneId: number, peer: Peer | null) => void;
        onpaneClose?: (paneId: number) => void;
        onupdatePeerTracking?: (payload: { destination_hash: string; is_tracking: boolean }) => void;
        onreloadConversations?: () => void;
        onoutboundComposeEnqueued?: (payload: Record<string, unknown>) => void;
        onregisterPaneViewer?: (paneId: number, api: ConversationViewerApi | null) => void;
    };

    let {
        visiblePanes = [],
        focusedPaneId = 1,
        multiPaneActive = false,
        canAddPane = false,
        paneFlex = {},
        resizingPaneIds = null,
        dragOverPaneId = null,
        isDragOverAddZone = false,
        config = null,
        conversations = [],
        isPopout = false,
        onfocusPane,
        onaddPane,
        onstartPaneResize,
        onresetPaneSizes,
        onpaneDragOver,
        onpaneDragLeave,
        onpaneDrop,
        onaddZoneDragOver,
        onaddZoneDragLeave,
        onaddZoneDrop,
        onpanePeerUpdate,
        onpaneClose,
        onupdatePeerTracking,
        onreloadConversations,
        onoutboundComposeEnqueued,
        onregisterPaneViewer,
    }: Props = $props();

    function flexFor(paneId: number): number {
        return paneFlexValue(paneId, paneFlex, visiblePanes);
    }
</script>

{#each visiblePanes as pane, paneIndex (pane.id)}
    {#if paneIndex > 0}
        <div
            class="group/resizer relative w-1 shrink-0 cursor-col-resize bg-sem-border transition-colors hover:bg-sem-accent {resizingPaneIds
                ? 'bg-sem-accent'
                : ''}"
            role="separator"
            aria-orientation="vertical"
            onpointerdown={(e) => onstartPaneResize?.(e, visiblePanes[paneIndex - 1].id, pane.id)}
            ondblclick={() => onresetPaneSizes?.()}
        >
            <div class="absolute inset-y-0 -left-1.5 -right-1.5"></div>
        </div>
    {/if}
    <div
        class={[
            "relative flex flex-col min-w-0 overflow-hidden transition-[box-shadow]",
            multiPaneActive && pane.id === focusedPaneId ? "ring-2 ring-inset ring-sem-accent/60" : "",
            dragOverPaneId === pane.id ? "ring-2 ring-inset ring-sem-accent bg-sem-accent/5" : "",
        ].join(" ")}
        style="flex-grow: {flexFor(pane.id)}; flex-shrink: 1; flex-basis: 0%"
        onmousedown={() => onfocusPane?.(pane.id)}
        ondragover={(e) => {
            e.preventDefault();
            onpaneDragOver?.(pane.id);
        }}
        ondragleave={() => onpaneDragLeave?.(pane.id)}
        ondrop={(e) => {
            e.preventDefault();
            onpaneDrop?.(pane.id, e);
        }}
        role="presentation"
    >
        <ConversationViewer
            {config}
            myLxmfAddressHash={config?.lxmf_address_hash || ""}
            selectedPeer={pane.peer}
            {conversations}
            {isPopout}
            onupdateSelectedPeer={(peer) => onpanePeerUpdate?.(pane.id, peer)}
            onupdatePeerTracking={(payload) => onupdatePeerTracking?.(payload)}
            onclose={() => onpaneClose?.(pane.id)}
            onreloadConversations={() => onreloadConversations?.()}
            onoutboundComposeEnqueued={(payload) => onoutboundComposeEnqueued?.(payload)}
            onviewerReady={(api) => onregisterPaneViewer?.(pane.id, api)}
        />
        {#if !pane.peer}
            <div
                class="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-2 text-center text-sem-fg-secondary {!multiPaneActive &&
                dragOverPaneId !== pane.id
                    ? 'hidden'
                    : ''}"
            >
                <MaterialDesignIcon iconName="message-text-outline" class="size-8 opacity-70" />
                <span class="text-sm">{t("messages.select_conversation_for_pane")}</span>
            </div>
        {/if}
    </div>
{/each}

{#if canAddPane}
    <div
        class={[
            "hidden shrink-0 items-center border-l border-sem-border bg-sem-surface-muted sm:flex transition-colors",
            isDragOverAddZone ? "bg-sem-accent/10 ring-2 ring-inset ring-sem-accent" : "",
        ].join(" ")}
        ondragover={(e) => {
            e.preventDefault();
            onaddZoneDragOver?.();
        }}
        ondragleave={() => onaddZoneDragLeave?.()}
        ondrop={(e) => {
            e.preventDefault();
            onaddZoneDrop?.(e);
        }}
        role="presentation"
    >
        <button
            type="button"
            class="px-1.5 py-2 text-sem-fg-secondary transition-colors hover:bg-sem-surface-raised hover:text-sem-fg"
            title={t("messages.open_in_split")}
            onclick={() => onaddPane?.()}
        >
            <MaterialDesignIcon iconName="dock-right" class="size-5" />
        </button>
    </div>
{/if}
