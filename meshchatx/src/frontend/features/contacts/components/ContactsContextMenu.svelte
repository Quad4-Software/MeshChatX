<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { tick } from "svelte";
    import { fade } from "svelte/transition";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { clampFloatingToViewport } from "../../../js/clampFloatingToViewport.js";
    import { t } from "../../../js/i18n.js";

    let {
        visible = false,
        x = 0,
        y = 0,
        onSendMessage,
        onCall,
        onEdit,
        onShare,
        onCopyUri,
        onRemove,
    }: {
        visible?: boolean;
        x?: number;
        y?: number;
        onSendMessage?: () => void;
        onCall?: () => void;
        onEdit?: () => void;
        onShare?: () => void;
        onCopyUri?: () => void;
        onRemove?: () => void;
    } = $props();

    let panel: HTMLDivElement | undefined = $state();
    let adjustedLeft = $state(0);
    let adjustedTop = $state(0);
    let panelMaxHeight: number | null = $state(null);

    function isReducedMotion(): boolean {
        return (
            typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true
        );
    }

    const transitionDuration = $derived(isReducedMotion() ? 0 : 120);

    async function reposition() {
        await tick();
        if (!panel || !visible) {
            return;
        }
        const rect = panel.getBoundingClientRect();
        const result = clampFloatingToViewport(x, y, rect.width, rect.height);
        adjustedLeft = result.left;
        adjustedTop = result.top;
        panelMaxHeight = result.maxHeight;
    }

    $effect(() => {
        if (visible) {
            adjustedLeft = x;
            adjustedTop = y;
            panelMaxHeight = null;
            void reposition();
        }
    });
</script>

{#if visible}
    <div
        bind:this={panel}
        transition:fade={{ duration: transitionDuration }}
        class="context-menu-panel z-210"
        style="top: {adjustedTop}px; left: {adjustedLeft}px; {panelMaxHeight != null
            ? `max-height: ${panelMaxHeight}px; overflow-y: auto;`
            : ''}"
        role="menu"
    >
        <button type="button" class="context-item focus-ring-sem" role="menuitem" onclick={() => onSendMessage?.()}>
            <MaterialDesignIcon iconName="message-text-outline" class="size-4" />
            {t("contacts.send_message")}
        </button>
        <button type="button" class="context-item focus-ring-sem" role="menuitem" onclick={() => onCall?.()}>
            <MaterialDesignIcon iconName="phone-outline" class="size-4" />
            {t("contacts.call_contact")}
        </button>
        <div class="context-menu-divider" role="separator"></div>
        <button type="button" class="context-item focus-ring-sem" role="menuitem" onclick={() => onEdit?.()}>
            <MaterialDesignIcon iconName="pencil-outline" class="size-4" />
            {t("contacts.edit_contact")}
        </button>
        <button type="button" class="context-item focus-ring-sem" role="menuitem" onclick={() => onShare?.()}>
            <MaterialDesignIcon iconName="share-variant" class="size-4" />
            {t("contacts.share_contact")}
        </button>
        <button type="button" class="context-item focus-ring-sem" role="menuitem" onclick={() => onCopyUri?.()}>
            <MaterialDesignIcon iconName="content-copy" class="size-4" />
            {t("contacts.copy_contact_uri")}
        </button>
        <div class="context-menu-divider" role="separator"></div>
        <button
            type="button"
            class="context-item text-red-600 dark:text-red-400 focus-ring-sem"
            role="menuitem"
            onclick={() => onRemove?.()}
        >
            <MaterialDesignIcon iconName="delete-outline" class="size-4" />
            {t("contacts.remove_contact")}
        </button>
    </div>
{/if}
