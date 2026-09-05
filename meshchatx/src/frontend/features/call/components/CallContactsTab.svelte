<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../ui/svelte/LxmfUserIcon.svelte";
    import EmptyState from "../../../ui/svelte/EmptyState.svelte";
    import { t } from "../../../js/i18n.js";

    export interface CallContactIcon {
        icon_name?: string;
        foreground_colour?: string;
        background_colour?: string;
    }

    export interface CallContact {
        id: number | string;
        name: string;
        remote_identity_hash: string;
        remote_telephony_hash?: string;
        remote_destination_hash?: string;
        lxmf_address?: string;
        lxst_address?: string;
        custom_image?: string;
        preferred_ringtone_id?: number | null;
        remote_icon?: CallContactIcon | null;
        [key: string]: unknown;
    }

    interface Props {
        active?: boolean;
        contactsSearch?: string;
        contacts?: CallContact[];
        formatDestinationHash: (hash?: string) => string;
        onsearchinput?: (value: string) => void;
        onadd?: () => void;
        onedit?: (contact: CallContact) => void;
        ondelete?: (id: number | string) => void;
        oncopyhash?: (hash: string) => void;
        oncall?: (destination: string) => void;
    }

    let {
        active = false,
        contactsSearch = "",
        contacts = [],
        formatDestinationHash,
        onsearchinput,
        onadd,
        onedit,
        ondelete,
        oncopyhash,
        oncall,
    }: Props = $props();

    function handleSearchInput(event: Event): void {
        const value = (event.target as HTMLInputElement).value;
        onsearchinput?.(value);
    }
</script>

{#if active}
    <div class="flex-1 flex flex-col max-w-3xl mx-auto w-full pt-2">
        <div class="mb-4 flex gap-2">
            <div class="relative flex-1">
                <input
                    value={contactsSearch}
                    type="text"
                    placeholder={t("contacts.search_placeholder")}
                    class="input-field w-full pl-10"
                    oninput={handleSearchInput}
                />
                <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                    <MaterialDesignIcon iconName="magnify" class="size-5 text-sem-fg-muted" />
                </div>
            </div>
            <button type="button" class="primary-chip rounded-lg! focus-ring-sem" onclick={() => onadd?.()}>
                <MaterialDesignIcon iconName="plus" class="size-5" />
                {t("common.add")}
            </button>
        </div>

        {#if contacts.length === 0}
            <EmptyState
                icon="account-multiple"
                title={t("contacts.no_contacts")}
                description={t("call.no_contacts_hint")}
                class="my-auto"
            />
        {:else}
            <div class="space-y-4">
                <div class="border-b border-sem-border overflow-hidden">
                    <ul class="divide-y divide-gray-100 dark:divide-zinc-800">
                        {#each contacts as contact (contact.id)}
                            <li class="px-4 py-3 hover:bg-sem-surface-muted/50 transition-colors">
                                <div class="flex items-center space-x-3">
                                    <div class="shrink-0">
                                        <LxmfUserIcon
                                            customImage={contact.custom_image}
                                            iconName={contact.remote_icon?.icon_name || ""}
                                            iconForegroundColour={contact.remote_icon?.foreground_colour || ""}
                                            iconBackgroundColour={contact.remote_icon?.background_colour || ""}
                                            iconClass="size-10"
                                        />
                                    </div>
                                    <div class="flex-1 min-w-0">
                                        <div class="flex items-center justify-between">
                                            <p class="text-sm font-bold text-sem-fg truncate">
                                                {contact.name}
                                            </p>
                                            <div class="flex items-center gap-2">
                                                {#if contact.preferred_ringtone_id}
                                                    <span
                                                        class="text-[9px] px-1.5 py-0.5 rounded-sm bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 border border-amber-100 dark:border-amber-800/50 flex items-center gap-1"
                                                        title={t("call.custom_ringtone_set")}
                                                    >
                                                        <MaterialDesignIcon iconName="music" class="size-2.5" />
                                                        {contact.preferred_ringtone_id === -1
                                                            ? t("call.random")
                                                            : t("call.custom")}
                                                    </span>
                                                {/if}
                                                <div class="flex items-center gap-1">
                                                    <button
                                                        type="button"
                                                        class="p-1.5 text-gray-400 hover:text-blue-500 transition-colors"
                                                        aria-label={t("common.edit")}
                                                        title={t("common.edit")}
                                                        onclick={() => onedit?.(contact)}
                                                    >
                                                        <MaterialDesignIcon iconName="pencil" class="size-4" />
                                                    </button>
                                                    <button
                                                        type="button"
                                                        class="p-1.5 text-gray-400 hover:text-red-500 transition-colors"
                                                        aria-label={t("common.delete")}
                                                        title={t("common.delete")}
                                                        onclick={() => ondelete?.(contact.id)}
                                                    >
                                                        <MaterialDesignIcon iconName="delete" class="size-4" />
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                        <div class="flex items-center justify-between mt-1">
                                            <div class="flex flex-col min-w-0">
                                                <button
                                                    type="button"
                                                    class="text-[10px] text-left text-sem-fg-muted font-mono truncate cursor-pointer hover:text-blue-500 transition-colors"
                                                    title={contact.remote_identity_hash}
                                                    onclick={(e) => {
                                                        e.stopPropagation();
                                                        oncopyhash?.(contact.remote_identity_hash);
                                                    }}
                                                >
                                                    ID: {formatDestinationHash(contact.remote_identity_hash)}
                                                </button>
                                                {#if contact.lxmf_address}
                                                    <button
                                                        type="button"
                                                        class="text-[9px] text-left text-sem-fg-muted font-mono truncate cursor-pointer hover:text-blue-500 transition-colors"
                                                        title={contact.lxmf_address}
                                                        onclick={(e) => {
                                                            e.stopPropagation();
                                                            if (contact.lxmf_address) {
                                                                oncopyhash?.(contact.lxmf_address);
                                                            }
                                                        }}
                                                    >
                                                        LXMF: {formatDestinationHash(contact.lxmf_address)}
                                                    </button>
                                                {/if}
                                                {#if contact.lxst_address}
                                                    <button
                                                        type="button"
                                                        class="text-[9px] text-left text-sem-fg-muted font-mono truncate cursor-pointer hover:text-blue-500 transition-colors"
                                                        title={contact.lxst_address}
                                                        onclick={(e) => {
                                                            e.stopPropagation();
                                                            if (contact.lxst_address) {
                                                                oncopyhash?.(contact.lxst_address);
                                                            }
                                                        }}
                                                    >
                                                        LXST: {formatDestinationHash(contact.lxst_address)}
                                                    </button>
                                                {/if}
                                            </div>
                                            <button
                                                type="button"
                                                class="text-[10px] bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 px-3 py-1 rounded-full font-bold uppercase tracking-wider hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors shrink-0"
                                                onclick={() =>
                                                    oncall?.(
                                                        contact.remote_telephony_hash ||
                                                            contact.remote_destination_hash ||
                                                            contact.remote_identity_hash
                                                    )}
                                            >
                                                Call
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </li>
                        {/each}
                    </ul>
                </div>
            </div>
        {/if}
    </div>
{/if}
