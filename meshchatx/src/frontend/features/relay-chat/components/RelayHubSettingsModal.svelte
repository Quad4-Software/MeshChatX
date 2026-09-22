<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import Toggle from "../../../ui/svelte/Toggle.svelte";
    import MdiIconPickerModal from "./MdiIconPickerModal.svelte";
    import { t } from "../../../js/i18n.js";
    import { DEFAULT_RRC_HUB_ICON, normalizeMdiIconName } from "../../../js/mdiIconNames.js";
    import { BTN_PRIMARY, BTN_SECONDARY } from "../lib/constants.js";
    import { statusIconColor } from "../lib/relayFormatters.js";
    import type { RrcHub } from "../lib/types.js";

    interface Props {
        show?: boolean;
        hub?: RrcHub | null;
        applyingOptionsToAllHubs?: boolean;
        onclose?: () => void;
        onsubmit?: (payload: Record<string, unknown>) => void;
        onapplyoptionsall?: (options: { auto_reconnect: boolean; auto_list: boolean; auto_who: boolean }) => void;
    }

    let {
        show = false,
        hub = null,
        applyingOptionsToAllHubs = false,
        onclose,
        onsubmit,
        onapplyoptionsall,
    }: Props = $props();

    let autoReconnect = $state(true);
    let autoList = $state(true);
    let autoWho = $state(false);
    let nick = $state("");
    let customName = $state("");
    let defaultName = $state("");
    let hasCustomName = $state(false);
    let hubIcon = $state<string | null>(null);
    let showIconPicker = $state(false);

    const iconPreview = $derived(normalizeMdiIconName(hubIcon) || DEFAULT_RRC_HUB_ICON);
    const statusIconClass = $derived(statusIconColor(hub?.status ?? 0));

    $effect(() => {
        if (show && hub) {
            defaultName = hub.hub_name_announced || hub.name || "";
            autoReconnect = hub.auto_reconnect !== false;
            autoList = !!hub.auto_list;
            autoWho = !!hub.auto_who;
            nick = hub.nick_override || "";
            customName = hub.custom_name || "";
            hasCustomName = Boolean(hub.custom_name);
            hubIcon = normalizeMdiIconName(hub.hub_icon);
            showIconPicker = false;
        }
    });

    function onHubIconPicked(iconName: string | null) {
        hubIcon = normalizeMdiIconName(iconName);
    }

    function handleSubmit() {
        if (!hub) return;
        const payload: Record<string, unknown> = {
            auto_reconnect: autoReconnect,
            auto_list: autoList,
            auto_who: autoWho,
            nick,
        };
        const trimmed = (customName || "").trim();
        if (!trimmed && hasCustomName) {
            payload.revert_custom_name = true;
        } else if (trimmed) {
            payload.custom_name = trimmed;
        }
        const icon = normalizeMdiIconName(hubIcon);
        const hadIcon = Boolean(hub.hub_icon);
        if (!icon && hadIcon) {
            payload.revert_hub_icon = true;
        } else if (icon) {
            payload.hub_icon = icon;
        }
        onsubmit?.(payload);
    }
</script>

{#if show}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
        onclick={(e) => {
            if (e.target === e.currentTarget) onclose?.();
        }}
    >
        <div class="w-full max-w-md rounded-2xl border border-sem-border-card bg-sem-surface p-5 shadow-xl text-sem-fg">
            <h2 class="mb-4 text-lg font-semibold">{t("relay_chat.settings")}</h2>
            <form
                class="space-y-4"
                onsubmit={(e) => {
                    e.preventDefault();
                    handleSubmit();
                }}
            >
                <div class="space-y-2">
                    <span class="block text-sm font-semibold text-sem-fg-secondary">{t("relay_chat.hub_icon")}</span>
                    <div class="flex items-center gap-3">
                        <div
                            class="flex size-12 shrink-0 items-center justify-center rounded-xl border border-sem-border bg-sem-canvas"
                        >
                            <MaterialDesignIcon iconName={iconPreview} class="size-7 {statusIconClass}" />
                        </div>
                        <div class="flex min-w-0 flex-1 flex-wrap gap-2">
                            <button
                                type="button"
                                class="{BTN_SECONDARY} py-1.5! text-xs!"
                                onclick={() => {
                                    showIconPicker = true;
                                }}
                            >
                                <MaterialDesignIcon iconName="image-edit-outline" class="size-4" />
                                {t("relay_chat.hub_icon_choose")}
                            </button>
                            {#if hubIcon}
                                <button
                                    type="button"
                                    class="text-xs text-sem-accent hover:underline cursor-pointer"
                                    onclick={() => {
                                        hubIcon = null;
                                    }}
                                >
                                    {t("relay_chat.hub_icon_reset_default")}
                                </button>
                            {/if}
                        </div>
                    </div>
                </div>
                <div class="space-y-1.5">
                    <label class="block text-sm font-semibold text-sem-fg-secondary" for="hub-settings-name">
                        {t("relay_chat.hub_display_name")}
                    </label>
                    <input
                        id="hub-settings-name"
                        bind:value={customName}
                        type="text"
                        placeholder={defaultName}
                        class="input-field"
                    />
                    {#if hasCustomName}
                        <button
                            type="button"
                            class="text-xs text-sem-accent hover:underline cursor-pointer"
                            onclick={() => {
                                customName = "";
                            }}
                        >
                            {t("relay_chat.revert_hub_name")}
                        </button>
                    {/if}
                </div>
                <label class="setting-toggle flex items-start gap-3 cursor-pointer">
                    <Toggle id="rrc-auto-reconnect" bind:checked={autoReconnect} />
                    <span class="min-w-0 text-sm">
                        <span class="font-medium text-sem-fg">{t("relay_chat.auto_reconnect")}</span>
                    </span>
                </label>
                <label class="setting-toggle flex items-start gap-3 cursor-pointer">
                    <Toggle id="rrc-auto-list" bind:checked={autoList} />
                    <span class="min-w-0 text-sm">
                        <span class="font-medium text-sem-fg">{t("relay_chat.auto_list")}</span>
                    </span>
                </label>
                <label class="setting-toggle flex items-start gap-3 cursor-pointer">
                    <Toggle id="rrc-auto-who" bind:checked={autoWho} />
                    <span class="min-w-0 text-sm">
                        <span class="font-medium text-sem-fg">{t("relay_chat.auto_who")}</span>
                    </span>
                </label>
                <div>
                    <button
                        type="button"
                        class="text-xs text-sem-accent hover:underline disabled:opacity-50 cursor-pointer"
                        disabled={applyingOptionsToAllHubs}
                        onclick={() =>
                            onapplyoptionsall?.({
                                auto_reconnect: autoReconnect,
                                auto_list: autoList,
                                auto_who: autoWho,
                            })}
                    >
                        {t("relay_chat.apply_auto_options_all_hubs")}
                    </button>
                </div>
                <div class="space-y-1.5">
                    <label class="block text-sm font-semibold text-sem-fg-secondary" for="hub-settings-nick">
                        {t("relay_chat.nickname")}
                    </label>
                    <input
                        id="hub-settings-nick"
                        bind:value={nick}
                        type="text"
                        placeholder={t("relay_chat.nickname_placeholder")}
                        class="input-field"
                    />
                </div>
                <div class="flex justify-end gap-2 pt-1">
                    <button type="button" class={BTN_SECONDARY} onclick={() => onclose?.()}>
                        {t("common.cancel")}
                    </button>
                    <button type="submit" class={BTN_PRIMARY}>{t("relay_chat.save")}</button>
                </div>
            </form>
        </div>
    </div>
{/if}

<MdiIconPickerModal
    open={showIconPicker}
    selectedIcon={hubIcon}
    previewIconClass={statusIconClass}
    onclose={() => {
        showIconPicker = false;
    }}
    onselect={onHubIconPicked}
/>
