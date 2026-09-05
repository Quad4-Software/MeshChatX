<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import RelayAddHubModal from "./RelayAddHubModal.svelte";
    import RelayHubSettingsModal from "./RelayHubSettingsModal.svelte";
    import { t } from "../../../js/i18n.js";
    import { BTN_PRIMARY, BTN_SECONDARY } from "../lib/constants.js";
    import type { RrcHub, RrcMessage } from "../lib/types.js";

    interface Props {
        showAddHubModal?: boolean;
        showCreateHostModal?: boolean;
        showHubSettingsModal?: boolean;
        showRoomKeyModal?: boolean;
        editingHub?: RrcHub | null;
        sidebarMenu?: { show: boolean; x: number; y: number; hub?: RrcHub | null };
        messageMenu?: { show: boolean; x: number; y: number; msg?: RrcMessage | null };
        canModerateSelectedHub?: boolean;
        oncloseaddhub?: () => void;
        onsubmitaddhub?: (hubHash: string, name: string, autoReconnect: boolean, icon: string) => void;
        onclosecreatehost?: () => void;
        onsubmitcreatehost?: (name: string, announceInterval: number) => void;
        onclosehubsettings?: () => void;
        onsubmithubsettings?: (hub: RrcHub, name: string, autoReconnect: boolean, icon: string) => void;
        onremovehub?: (hub: RrcHub) => void;
        oncloseroomkey?: () => void;
        onsubmitroomkey?: (key: string) => void;
        onclosesidebarmenu?: () => void;
        onclosemessagemenu?: () => void;
        oncopytext?: (text: string) => void;
        oncopylink?: (hub: RrcHub) => void;
        onkickmessageauthor?: (msg: RrcMessage) => void;
        onbanmessageauthor?: (msg: RrcMessage) => void;
    }

    let {
        showAddHubModal = false,
        showCreateHostModal = false,
        showHubSettingsModal = false,
        showRoomKeyModal = false,
        editingHub = null,
        sidebarMenu = { show: false, x: 0, y: 0 },
        messageMenu = { show: false, x: 0, y: 0 },
        canModerateSelectedHub = false,
        oncloseaddhub,
        onsubmitaddhub,
        onclosecreatehost,
        onsubmitcreatehost,
        onclosehubsettings,
        onsubmithubsettings,
        onremovehub,
        oncloseroomkey,
        onsubmitroomkey,
        onclosesidebarmenu,
        onclosemessagemenu,
        oncopytext,
        oncopylink,
        onkickmessageauthor,
        onbanmessageauthor,
    }: Props = $props();

    let createHostName = $state("");
    let createHostAnnounceMinutes = $state(15);
    let roomKeyInput = $state("");
</script>

<svelte:window
    onclick={() => {
        if (sidebarMenu.show) onclosesidebarmenu?.();
        if (messageMenu.show) onclosemessagemenu?.();
    }}
/>

<RelayAddHubModal show={showAddHubModal} onclose={oncloseaddhub} onsubmit={onsubmitaddhub} />

<RelayHubSettingsModal
    show={showHubSettingsModal}
    hub={editingHub}
    onclose={onclosehubsettings}
    onsubmit={onsubmithubsettings}
    onremove={onremovehub}
/>

{#if showCreateHostModal}
    <div class="fixed inset-0 z-100 flex items-center justify-center bg-black/60 p-4">
        <div class="w-full max-w-md rounded-2xl border border-sem-border bg-sem-surface p-6 shadow-xl text-sem-fg">
            <h3 class="text-lg font-bold mb-4">{t("relay_chat.create_hub_dialog_title")}</h3>
            <div class="space-y-4">
                <div>
                    <label
                        class="block text-xs font-semibold text-sem-fg-muted uppercase tracking-wider mb-1"
                        for="create-host-name-input"
                    >
                        {t("relay_chat.hub_name")}
                    </label>
                    <input
                        id="create-host-name-input"
                        type="text"
                        bind:value={createHostName}
                        placeholder={t("relay_chat.hub_name_placeholder")}
                        class="w-full px-3 py-2 text-sm bg-sem-canvas border border-sem-border rounded-xl text-sem-fg focus:outline-hidden focus:border-sem-accent"
                    />
                </div>
                <div>
                    <label
                        class="block text-xs font-semibold text-sem-fg-muted uppercase tracking-wider mb-1"
                        for="create-host-announce-input"
                    >
                        {t("relay_chat.announce_interval_minutes")}
                    </label>
                    <input
                        id="create-host-announce-input"
                        type="number"
                        min="1"
                        bind:value={createHostAnnounceMinutes}
                        class="w-full px-3 py-2 text-sm bg-sem-canvas border border-sem-border rounded-xl text-sem-fg focus:outline-hidden focus:border-sem-accent"
                    />
                </div>
            </div>
            <div class="mt-6 flex justify-end gap-3">
                <button type="button" class={BTN_SECONDARY} onclick={() => onclosecreatehost?.()}>
                    {t("common.cancel")}
                </button>
                <button
                    type="button"
                    class={BTN_PRIMARY}
                    disabled={!createHostName.trim()}
                    onclick={() => {
                        onsubmitcreatehost?.(createHostName.trim(), (createHostAnnounceMinutes || 15) * 60);
                        createHostName = "";
                        createHostAnnounceMinutes = 15;
                    }}
                >
                    {t("relay_chat.create_hub_action")}
                </button>
            </div>
        </div>
    </div>
{/if}

{#if showRoomKeyModal}
    <div class="fixed inset-0 z-100 flex items-center justify-center bg-black/60 p-4">
        <div class="w-full max-w-sm rounded-2xl border border-sem-border bg-sem-surface p-6 shadow-xl text-sem-fg">
            <h3 class="text-lg font-bold mb-4">{t("relay_chat.enter_room_key_title")}</h3>
            <div class="space-y-4">
                <div>
                    <label
                        class="block text-xs font-semibold text-sem-fg-muted uppercase tracking-wider mb-1"
                        for="room-key-input"
                    >
                        {t("relay_chat.room_key")}
                    </label>
                    <input
                        id="room-key-input"
                        type="password"
                        bind:value={roomKeyInput}
                        placeholder={t("relay_chat.room_key_placeholder")}
                        class="w-full px-3 py-2 text-sm bg-sem-canvas border border-sem-border rounded-xl text-sem-fg focus:outline-hidden focus:border-sem-accent"
                    />
                </div>
            </div>
            <div class="mt-6 flex justify-end gap-3">
                <button type="button" class={BTN_SECONDARY} onclick={() => oncloseroomkey?.()}>
                    {t("common.cancel")}
                </button>
                <button
                    type="button"
                    class={BTN_PRIMARY}
                    onclick={() => {
                        onsubmitroomkey?.(roomKeyInput);
                        roomKeyInput = "";
                    }}
                >
                    {t("common.join")}
                </button>
            </div>
        </div>
    </div>
{/if}

{#if sidebarMenu.show && sidebarMenu.hub}
    <div
        class="fixed z-100 min-w-44 rounded-xl border border-sem-border bg-sem-surface p-1 shadow-2xl text-xs text-sem-fg"
        style="top: {sidebarMenu.y}px; left: {sidebarMenu.x}px;"
    >
        <button
            type="button"
            class="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left hover:bg-sem-surface-muted transition-colors cursor-pointer"
            onclick={() => {
                if (sidebarMenu.hub) oncopylink?.(sidebarMenu.hub);
                onclosesidebarmenu?.();
            }}
        >
            <MaterialDesignIcon iconName="link-variant" class="size-3.5 text-sem-fg-muted" />
            <span>{t("relay_chat.copy_hub_link")}</span>
        </button>
    </div>
{/if}

{#if messageMenu.show && messageMenu.msg}
    <div
        class="fixed z-100 min-w-48 rounded-xl border border-sem-border bg-sem-surface p-1 shadow-2xl text-xs text-sem-fg"
        style="top: {messageMenu.y}px; left: {messageMenu.x}px;"
    >
        <button
            type="button"
            class="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left hover:bg-sem-surface-muted transition-colors cursor-pointer"
            onclick={() => {
                if (messageMenu.msg?.text) oncopytext?.(messageMenu.msg.text);
                onclosemessagemenu?.();
            }}
        >
            <MaterialDesignIcon iconName="content-copy" class="size-3.5 text-sem-fg-muted" />
            <span>{t("common.copy_text")}</span>
        </button>

        {#if canModerateSelectedHub && messageMenu.msg.src}
            <div class="my-1 border-t border-sem-border"></div>
            <button
                type="button"
                class="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-amber-500 hover:bg-sem-surface-muted transition-colors cursor-pointer"
                onclick={() => {
                    if (messageMenu.msg) onkickmessageauthor?.(messageMenu.msg);
                    onclosemessagemenu?.();
                }}
            >
                <MaterialDesignIcon iconName="account-remove" class="size-3.5" />
                <span>{t("relay_chat.kick_user")}</span>
            </button>
            <button
                type="button"
                class="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-red-500 hover:bg-sem-surface-muted transition-colors cursor-pointer"
                onclick={() => {
                    if (messageMenu.msg) onbanmessageauthor?.(messageMenu.msg);
                    onclosemessagemenu?.();
                }}
            >
                <MaterialDesignIcon iconName="account-cancel" class="size-3.5" />
                <span>{t("relay_chat.ban_user")}</span>
            </button>
        {/if}
    </div>
{/if}
