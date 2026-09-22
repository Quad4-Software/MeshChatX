<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../ui/svelte/LxmfUserIcon.svelte";
    import Utils from "../../../js/Utils.js";
    import { t } from "../../../js/i18n.js";

    let {
        contact,
        onOpenConversation,
        onCall,
        onContextMenu,
        onCopyHash,
    }: {
        contact: Record<string, unknown>;
        onOpenConversation?: (contact: Record<string, unknown>) => void;
        onCall?: (contact: Record<string, unknown>) => void;
        onContextMenu?: (event: MouseEvent, contact: Record<string, unknown>) => void;
        onCopyHash?: (hash: string) => void;
    } = $props();

    const remoteIcon = $derived(
        contact.remote_icon && typeof contact.remote_icon === "object"
            ? (contact.remote_icon as Record<string, unknown>)
            : null
    );

    function handleContextMenu(event: MouseEvent) {
        event.preventDefault();
        onContextMenu?.(event, contact);
    }
</script>

<div
    class="group flex cursor-default items-center gap-3 px-1 py-3 transition-colors hover:bg-gray-50/80 dark:hover:bg-zinc-900/70"
    oncontextmenu={handleContextMenu}
    role="listitem"
>
    <div class="shrink-0">
        <LxmfUserIcon
            customImage={String(contact.custom_image || "")}
            iconName={String(remoteIcon?.icon_name || "")}
            iconForegroundColour={String(remoteIcon?.foreground_colour || "")}
            iconBackgroundColour={String(remoteIcon?.background_colour || "")}
            iconClass="size-10 sm:size-12"
        />
    </div>
    <div class="min-w-0 flex-1">
        <div class="font-semibold text-sem-fg truncate">{String(contact.name || "")}</div>
        <div class="flex flex-col gap-0.5">
            {#if contact.remote_destination_hash}
                <div class="flex items-center gap-1.5 min-w-0">
                    <MaterialDesignIcon
                        iconName="message-text-outline"
                        class="size-4 text-blue-500 dark:text-blue-400 shrink-0"
                    />
                    <button
                        type="button"
                        class="text-xs font-mono text-sem-fg-muted truncate hover:text-blue-600 dark:hover:text-blue-400 text-left focus-ring-sem rounded"
                        title={String(contact.remote_destination_hash)}
                        onclick={(e) => {
                            e.stopPropagation();
                            onCopyHash?.(String(contact.remote_destination_hash));
                        }}
                    >
                        {Utils.formatDestinationHash(String(contact.remote_destination_hash))}
                    </button>
                </div>
            {/if}
            {#if contact.remote_telephony_hash}
                <div class="flex items-center gap-1.5">
                    <MaterialDesignIcon
                        iconName="phone-outline"
                        class="size-4 text-green-600 dark:text-green-400 shrink-0"
                    />
                    <span class="text-xs font-mono text-sem-fg-muted break-all"
                        >{String(contact.remote_telephony_hash)}</span
                    >
                </div>
            {/if}
            {#if !contact.remote_destination_hash && !contact.remote_telephony_hash}
                <span class="text-xs font-mono text-sem-fg-muted break-all"
                    >{String(contact.lxmf_address || contact.remote_identity_hash || "")}</span
                >
            {/if}
        </div>
    </div>
    <div class="flex items-center gap-1 opacity-100 transition-opacity lg:opacity-0 lg:group-hover:opacity-100">
        <button
            type="button"
            class="p-1.5 rounded-lg text-sem-fg-muted hover:bg-blue-100 dark:hover:bg-blue-900/40 hover:text-blue-600 dark:hover:text-blue-400 transition-colors focus-ring-sem"
            title={t("contacts.send_message")}
            onclick={(e) => {
                e.stopPropagation();
                onOpenConversation?.(contact);
            }}
        >
            <MaterialDesignIcon iconName="message-text-outline" class="size-5" />
        </button>
        <button
            type="button"
            class="p-1.5 rounded-lg text-sem-fg-muted hover:bg-green-100 dark:hover:bg-green-900/40 hover:text-green-600 dark:hover:text-green-400 transition-colors focus-ring-sem"
            title={t("contacts.call_contact")}
            onclick={(e) => {
                e.stopPropagation();
                onCall?.(contact);
            }}
        >
            <MaterialDesignIcon iconName="phone-outline" class="size-5" />
        </button>
    </div>
    <button
        type="button"
        class="p-1.5 rounded-lg text-sem-fg-muted hover:bg-sem-surface-muted hover:text-sem-fg transition-colors focus-ring-sem"
        title={t("contacts.actions")}
        onclick={(e) => {
            e.stopPropagation();
            onContextMenu?.(e, contact);
        }}
    >
        <MaterialDesignIcon iconName="dots-vertical" class="size-5" />
    </button>
</div>
