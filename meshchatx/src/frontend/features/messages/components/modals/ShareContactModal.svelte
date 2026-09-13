<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../../ui/svelte/LxmfUserIcon.svelte";
    import { t } from "../../../../js/i18n.js";

    type ContactRow = {
        id?: string | number;
        name?: string;
        custom_image?: string;
        remote_identity_hash?: string;
        lxmf_address?: string;
        lxst_address?: string;
        [key: string]: unknown;
    };

    type IconResolved = {
        iconName?: string;
        foreground?: string;
        background?: string;
    };

    let {
        show = false,
        search = $bindable(""),
        contacts = [] as ContactRow[],
        resolveIcon,
        destinationHex,
        onclose,
        onshare,
    }: {
        show?: boolean;
        search?: string;
        contacts?: ContactRow[];
        resolveIcon: (contact: ContactRow) => IconResolved;
        destinationHex: (contact: ContactRow) => string;
        onclose?: () => void;
        onshare?: (contact: ContactRow) => void;
    } = $props();
</script>

{#if show}
    <div
        class="fixed inset-0 z-100 flex items-center justify-center p-4 pt-[max(0.75rem,env(safe-area-inset-top))] pb-[max(0.75rem,env(safe-area-inset-bottom))] bg-black/50 backdrop-blur-xs"
        onclick={(e) => {
            if (e.target === e.currentTarget) onclose?.();
        }}
        onkeydown={(e) => {
            if (e.key === "Escape") onclose?.();
        }}
        role="presentation"
    >
        <div
            class="w-full max-w-md bg-sem-surface rounded-2xl shadow-2xl overflow-hidden max-h-[min(90dvh,40rem)] flex flex-col"
            role="dialog"
            aria-modal="true"
        >
            <div class="px-6 py-4 border-b border-sem-border flex items-center justify-between">
                <h3 class="text-lg font-bold text-sem-fg">
                    {t("messages.share_contact_modal_title")}
                </h3>
                <button
                    type="button"
                    class="text-gray-400 hover:text-gray-500 dark:hover:text-zinc-300 transition-colors"
                    onclick={() => onclose?.()}
                >
                    <MaterialDesignIcon iconName="close" class="size-6" />
                </button>
            </div>
            <div class="p-6">
                <div class="mb-4">
                    <div class="relative">
                        <input
                            value={search}
                            type="text"
                            placeholder={t("messages.share_contact_search_placeholder")}
                            class="block w-full rounded-lg border-0 py-2 pl-10 text-sem-fg shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-sem-focus sm:text-sm dark:bg-zinc-900"
                            oninput={(e) => {
                                search = (e.currentTarget as HTMLInputElement).value;
                            }}
                        />
                        <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                            <MaterialDesignIcon iconName="magnify" class="size-5 text-gray-400" />
                        </div>
                    </div>
                </div>
                <div class="max-h-64 overflow-y-auto space-y-2">
                    {#each contacts as contact (contact.id ?? contact.remote_identity_hash ?? contact.name)}
                        {@const icon = resolveIcon(contact)}
                        <button
                            type="button"
                            class="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-sem-surface-muted transition-colors text-left"
                            onclick={() => onshare?.(contact)}
                        >
                            <div class="shrink-0">
                                <LxmfUserIcon
                                    customImage={contact.custom_image || ""}
                                    iconName={icon.iconName || ""}
                                    iconForegroundColour={icon.foreground || ""}
                                    iconBackgroundColour={icon.background || ""}
                                    iconClass="size-10"
                                />
                            </div>
                            <div class="min-w-0">
                                <div class="font-bold text-sem-fg truncate">{contact.name}</div>
                                <div class="text-[10px] text-sem-fg-muted font-mono truncate">
                                    {destinationHex(contact) || contact.remote_identity_hash}
                                </div>
                                {#if contact.lxmf_address}
                                    <div class="text-[9px] text-sem-fg-muted font-mono truncate">
                                        LXMF: {contact.lxmf_address}
                                    </div>
                                {/if}
                                {#if contact.lxst_address}
                                    <div class="text-[9px] text-sem-fg-muted font-mono truncate">
                                        LXST: {contact.lxst_address}
                                    </div>
                                {/if}
                            </div>
                        </button>
                    {/each}
                </div>
            </div>
        </div>
    </div>
{/if}
