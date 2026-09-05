<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import MdiIconPickerModal from "./MdiIconPickerModal.svelte";
    import { t } from "../../../js/i18n.js";
    import { BTN_PRIMARY, BTN_SECONDARY, BTN_DANGER } from "../lib/constants.js";
    import type { RrcHub } from "../lib/types.js";

    interface Props {
        show?: boolean;
        hub?: RrcHub | null;
        onclose?: () => void;
        onsubmit?: (hub: RrcHub, name: string, autoReconnect: boolean, icon: string) => void;
        onremove?: (hub: RrcHub) => void;
    }

    let { show = false, hub = null, onclose, onsubmit, onremove }: Props = $props();

    let editName = $state("");
    let editAutoReconnect = $state(true);
    let editIcon = $state("forum");
    let iconPickerShowing = $state(false);

    $effect(() => {
        if (hub) {
            editName = hub.custom_display_name || hub.display_name || hub.name || "";
            editAutoReconnect = hub.auto_reconnect ?? true;
            editIcon = hub.icon || "forum";
        }
    });

    function handleSubmit() {
        if (!hub) return;
        onsubmit?.(hub, editName.trim(), editAutoReconnect, editIcon);
    }
</script>

{#if show && hub}
    <div class="fixed inset-0 z-100 flex items-center justify-center bg-black/60 p-4">
        <div class="w-full max-w-md rounded-2xl border border-sem-border bg-sem-surface p-6 shadow-xl text-sem-fg">
            <h3 class="text-lg font-bold mb-4">{t("relay_chat.hub_settings")}</h3>
            <div class="space-y-4">
                <div>
                    <label
                        class="block text-xs font-semibold text-sem-fg-muted uppercase tracking-wider mb-1"
                        for="edit-hub-name-input"
                    >
                        {t("relay_chat.hub_name")}
                    </label>
                    <input
                        id="edit-hub-name-input"
                        type="text"
                        bind:value={editName}
                        class="w-full px-3 py-2 text-sm bg-sem-canvas border border-sem-border rounded-xl text-sem-fg focus:outline-hidden focus:border-sem-accent"
                    />
                </div>
                <div class="flex items-center justify-between">
                    <span class="text-xs font-semibold text-sem-fg-muted uppercase tracking-wider">
                        {t("relay_chat.hub_icon")}
                    </span>
                    <button
                        type="button"
                        class="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-sem-border bg-sem-canvas hover:bg-sem-surface-muted transition-colors cursor-pointer text-xs"
                        onclick={() => {
                            iconPickerShowing = true;
                        }}
                    >
                        <MaterialDesignIcon iconName={editIcon} class="size-4" />
                        <span>{editIcon}</span>
                    </button>
                </div>
                <label class="flex items-center gap-2 cursor-pointer select-none">
                    <input
                        type="checkbox"
                        bind:checked={editAutoReconnect}
                        class="size-4 rounded border-sem-border text-sem-accent focus:ring-sem-accent"
                    />
                    <span class="text-xs font-medium">{t("relay_chat.auto_reconnect")}</span>
                </label>
            </div>
            <div class="mt-6 flex items-center justify-between">
                <button
                    type="button"
                    class={BTN_DANGER}
                    onclick={() => {
                        if (hub) onremove?.(hub);
                    }}
                >
                    {t("relay_chat.remove_hub")}
                </button>
                <div class="flex gap-3">
                    <button type="button" class={BTN_SECONDARY} onclick={() => onclose?.()}>
                        {t("common.cancel")}
                    </button>
                    <button type="button" class={BTN_PRIMARY} onclick={handleSubmit}>
                        {t("common.save")}
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}

<MdiIconPickerModal
    open={iconPickerShowing}
    selectedIcon={editIcon}
    onselect={(icon) => {
        editIcon = icon || "";
        iconPickerShowing = false;
    }}
    onclose={() => {
        iconPickerShowing = false;
    }}
/>
