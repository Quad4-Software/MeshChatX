<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import MdiIconPickerModal from "./MdiIconPickerModal.svelte";
    import { t } from "../../../js/i18n.js";
    import { BTN_PRIMARY, BTN_SECONDARY } from "../lib/constants.js";

    interface Props {
        show?: boolean;
        onclose?: () => void;
        onsubmit?: (hubHash: string, name: string, autoReconnect: boolean, icon: string) => void;
    }

    let { show = false, onclose, onsubmit }: Props = $props();

    let addHubHash = $state("");
    let addHubName = $state("");
    let addHubAutoReconnect = $state(true);
    let addHubIcon = $state("forum");
    let iconPickerShowing = $state(false);

    function handleSubmit() {
        if (!addHubHash.trim()) return;
        onsubmit?.(addHubHash.trim(), addHubName.trim(), addHubAutoReconnect, addHubIcon);
        addHubHash = "";
        addHubName = "";
        addHubAutoReconnect = true;
        addHubIcon = "forum";
    }
</script>

{#if show}
    <div class="fixed inset-0 z-100 flex items-center justify-center bg-black/60 p-4">
        <div class="w-full max-w-md rounded-2xl border border-sem-border bg-sem-surface p-6 shadow-xl text-sem-fg">
            <h3 class="text-lg font-bold mb-4">{t("relay_chat.add_hub_dialog_title")}</h3>
            <div class="space-y-4">
                <div>
                    <label
                        class="block text-xs font-semibold text-sem-fg-muted uppercase tracking-wider mb-1"
                        for="add-hub-hash-input"
                    >
                        {t("relay_chat.hub_hash")}
                    </label>
                    <input
                        id="add-hub-hash-input"
                        type="text"
                        bind:value={addHubHash}
                        placeholder={t("relay_chat.enter_hub_hash")}
                        class="w-full px-3 py-2 text-sm bg-sem-canvas border border-sem-border rounded-xl text-sem-fg focus:outline-hidden focus:border-sem-accent"
                    />
                </div>
                <div>
                    <label
                        class="block text-xs font-semibold text-sem-fg-muted uppercase tracking-wider mb-1"
                        for="add-hub-name-input"
                    >
                        {t("relay_chat.hub_name_optional")}
                    </label>
                    <input
                        id="add-hub-name-input"
                        type="text"
                        bind:value={addHubName}
                        placeholder={t("relay_chat.enter_hub_name")}
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
                        <MaterialDesignIcon iconName={addHubIcon} class="size-4" />
                        <span>{addHubIcon}</span>
                    </button>
                </div>
                <label class="flex items-center gap-2 cursor-pointer select-none">
                    <input
                        type="checkbox"
                        bind:checked={addHubAutoReconnect}
                        class="size-4 rounded border-sem-border text-sem-accent focus:ring-sem-accent"
                    />
                    <span class="text-xs font-medium">{t("relay_chat.auto_reconnect")}</span>
                </label>
            </div>
            <div class="mt-6 flex justify-end gap-3">
                <button type="button" class={BTN_SECONDARY} onclick={() => onclose?.()}>
                    {t("common.cancel")}
                </button>
                <button type="button" class={BTN_PRIMARY} disabled={!addHubHash.trim()} onclick={handleSubmit}>
                    {t("relay_chat.add_hub_action")}
                </button>
            </div>
        </div>
    </div>
{/if}

<MdiIconPickerModal
    open={iconPickerShowing}
    selectedIcon={addHubIcon}
    onselect={(icon) => {
        addHubIcon = icon || "";
        iconPickerShowing = false;
    }}
    onclose={() => {
        iconPickerShowing = false;
    }}
/>
