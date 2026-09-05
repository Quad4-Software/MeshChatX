<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../ui/svelte/LxmfUserIcon.svelte";
    import EmptyState from "../../../ui/svelte/EmptyState.svelte";
    import Skeleton from "../../../ui/svelte/Skeleton.svelte";
    import Utils from "../../../js/Utils.js";
    import { t } from "../../../js/i18n.js";

    interface CallHistoryItem {
        id: number | string;
        remote_identity_name?: string;
        remote_identity_hash?: string;
        remote_destination_hash?: string;
        remote_telephony_hash?: string;
        is_incoming?: boolean;
        is_contact?: boolean;
        timestamp?: number;
        status?: string;
        duration_seconds?: number;
        contact_image?: string;
        remote_icon?: {
            icon_name?: string;
            foreground_colour?: string;
            background_colour?: string;
        };
        [key: string]: unknown;
    }

    interface Props {
        callHistory?: CallHistoryItem[];
        hasMoreCallHistory?: boolean;
        callHistorySearch?: string;
        isLoading?: boolean;
        getContactByHash?: (hash: string) => { custom_image?: string } | null | undefined;
        formatDestinationHash?: (hash?: string) => string;
        formatDateTime?: (timestampMs: number) => string;
        formatDuration?: (seconds: number) => string;
        onclearhistory?: () => void;
        onsearchinput?: (value: string) => void;
        onaddcontact?: (entry: CallHistoryItem) => void;
        onblockidentity?: (hash: string) => void;
        onopenmessage?: (entry: CallHistoryItem) => void;
        oncallback?: (hash: string) => void;
        onloadmore?: () => void;
        oncopyhash?: (hash: string) => void;
    }

    let {
        callHistory = [],
        hasMoreCallHistory = false,
        callHistorySearch = "",
        isLoading = false,
        getContactByHash,
        formatDestinationHash = (h?: string) => Utils.formatDestinationHash(h),
        formatDateTime = (ms: number) => Utils.convertUnixMillisToLocalDateTimeString(ms),
        formatDuration = (s: number) => Utils.formatMinutesSeconds(s),
        onclearhistory,
        onsearchinput,
        onaddcontact,
        onblockidentity,
        onopenmessage,
        oncallback,
        onloadmore,
        oncopyhash = (hash: string) => {
            if (typeof navigator !== "undefined" && navigator.clipboard) {
                void navigator.clipboard.writeText(hash);
            }
        },
    }: Props = $props();

    function entryTargetHash(entry: CallHistoryItem): string {
        return entry.remote_telephony_hash || entry.remote_destination_hash || entry.remote_identity_hash || "";
    }
</script>

<div class="space-y-4 max-w-3xl mx-auto w-full">
    <div class="w-full border-b border-sem-border p-0! overflow-hidden">
        <div class="px-5 py-4 border-b border-sem-border flex flex-col gap-4 bg-transparent">
            <div class="flex justify-between items-center">
                <div class="flex items-center gap-2">
                    <div class="p-1.5 bg-sem-surface-muted rounded-lg">
                        <MaterialDesignIcon iconName="history" class="size-4 text-sem-fg-muted" />
                    </div>
                    <h3 class="text-xs font-bold text-sem-fg-muted uppercase tracking-widest">
                        {t("call.call_history")}
                    </h3>
                </div>
                {#if callHistory.length > 0}
                    <button
                        type="button"
                        class="text-[10px] text-sem-fg-muted hover:text-sem-danger font-bold uppercase tracking-wider transition-colors bg-sem-surface px-2 py-1 rounded-md border border-sem-border focus-ring-sem cursor-pointer"
                        onclick={() => onclearhistory?.()}
                    >
                        {t("app.clear_history")}
                    </button>
                {/if}
            </div>
            <div class="relative">
                <input
                    value={callHistorySearch}
                    type="text"
                    placeholder={t("call.search_history")}
                    class="input-field py-2! pl-10!"
                    oninput={(e) => onsearchinput?.((e.target as HTMLInputElement).value)}
                />
                <MaterialDesignIcon
                    iconName="magnify"
                    class="absolute left-3.5 top-1/2 -translate-y-1/2 size-4 text-sem-fg-muted"
                />
            </div>
        </div>

        {#if isLoading && callHistory.length === 0}
            <div class="p-6 space-y-4">
                <div class="flex items-center gap-4">
                    <Skeleton variant="avatar" />
                    <div class="flex-1 space-y-2">
                        <Skeleton variant="line" class="w-1/3" />
                        <Skeleton variant="line" class="w-1/2" />
                    </div>
                </div>
                <div class="flex items-center gap-4">
                    <Skeleton variant="avatar" />
                    <div class="flex-1 space-y-2">
                        <Skeleton variant="line" class="w-1/4" />
                        <Skeleton variant="line" class="w-2/3" />
                    </div>
                </div>
                <div class="flex items-center gap-4">
                    <Skeleton variant="avatar" />
                    <div class="flex-1 space-y-2">
                        <Skeleton variant="line" class="w-1/3" />
                        <Skeleton variant="line" class="w-1/2" />
                    </div>
                </div>
            </div>
        {:else if callHistory.length === 0}
            <EmptyState
                icon="history"
                title={t("call.no_history")}
                description={t("call.no_history_hint")}
                class="py-12"
            />
        {:else}
            <ul class="divide-y divide-sem-border-subtle">
                {#each callHistory as entry (entry.id)}
                    <li class="px-5 py-4 hover:bg-sem-surface-muted/50 transition-colors group">
                        <div class="flex items-center space-x-4">
                            <div class="relative shrink-0">
                                <LxmfUserIcon
                                    customImage={entry.contact_image ||
                                        getContactByHash?.(entry.remote_identity_hash || "")?.custom_image}
                                    iconName={entry.remote_icon ? entry.remote_icon.icon_name : ""}
                                    iconForegroundColour={entry.remote_icon ? entry.remote_icon.foreground_colour : ""}
                                    iconBackgroundColour={entry.remote_icon ? entry.remote_icon.background_colour : ""}
                                    iconClass="size-10"
                                />
                                <div
                                    class="absolute -bottom-1 -right-1 bg-sem-surface rounded-full p-0.5 shadow-xs border border-sem-border shrink-0 flex items-center justify-center size-5"
                                >
                                    <MaterialDesignIcon
                                        iconName={entry.is_incoming ? "phone-incoming" : "phone-outgoing"}
                                        class="size-3 {entry.is_incoming ? 'text-sem-accent' : 'text-green-500'}"
                                    />
                                </div>
                            </div>

                            <div class="flex-1 min-w-0">
                                <div class="flex items-center justify-between">
                                    <div class="text-sm font-bold text-sem-fg truncate">
                                        {entry.remote_identity_name || t("call.unknown")}
                                    </div>
                                    <div class="text-[10px] text-sem-fg-muted font-mono shrink-0">
                                        {entry.timestamp ? formatDateTime(entry.timestamp * 1000) : ""}
                                    </div>
                                </div>

                                <div class="flex items-center justify-between mt-0.5">
                                    <div class="min-w-0">
                                        <div class="flex items-center gap-2 text-[10px] text-sem-fg-muted">
                                            <span class="capitalize">{entry.status}</span>
                                            {#if (entry.duration_seconds || 0) > 0}
                                                <span class="text-sem-fg-muted">•</span>
                                                <span>{formatDuration(entry.duration_seconds || 0)}</span>
                                            {/if}
                                        </div>
                                        <button
                                            type="button"
                                            class="text-[10px] font-mono text-sem-fg-muted truncate mt-0.5 cursor-pointer hover:text-sem-accent transition-colors text-left block"
                                            title={entryTargetHash(entry)}
                                            onclick={(e) => {
                                                e.stopPropagation();
                                                oncopyhash?.(entryTargetHash(entry));
                                            }}
                                        >
                                            {formatDestinationHash(entryTargetHash(entry))}
                                        </button>
                                    </div>

                                    <div
                                        class="flex items-center gap-1.5 opacity-100 transition-opacity shrink-0 ml-4 lg:opacity-0 lg:group-hover:opacity-100"
                                    >
                                        {#if !entry.is_contact}
                                            <button
                                                type="button"
                                                class="p-1.5 rounded-lg text-sem-fg-muted hover:text-sem-accent hover:bg-sem-accent-subtle transition-all shrink-0 focus-ring-sem cursor-pointer"
                                                title={t("call.add_to_contacts")}
                                                onclick={() => onaddcontact?.(entry)}
                                            >
                                                <MaterialDesignIcon iconName="account-plus" class="size-4" />
                                            </button>
                                        {/if}
                                        <button
                                            type="button"
                                            class="p-1.5 rounded-lg text-sem-fg-muted hover:text-sem-danger hover:bg-sem-danger/10 transition-all shrink-0 focus-ring-sem cursor-pointer"
                                            title={t("common.block")}
                                            onclick={() => onblockidentity?.(entry.remote_identity_hash || "")}
                                        >
                                            <MaterialDesignIcon iconName="account-remove" class="size-4" />
                                        </button>
                                        <button
                                            type="button"
                                            class="p-1.5 rounded-lg text-sem-fg-muted hover:text-sem-accent hover:bg-sem-accent-subtle transition-all shrink-0 focus-ring-sem cursor-pointer"
                                            title={t("contacts.send_message")}
                                            onclick={() => onopenmessage?.(entry)}
                                        >
                                            <MaterialDesignIcon iconName="message-text-outline" class="size-4" />
                                        </button>
                                        <button
                                            type="button"
                                            class="flex items-center gap-1.5 px-3 py-1 bg-sem-accent text-white rounded-lg text-[10px] font-bold hover:bg-sem-accent/90 transition-all shadow-md shadow-sem-accent/10 shrink-0 focus-ring-sem cursor-pointer"
                                            onclick={() => oncallback?.(entryTargetHash(entry))}
                                        >
                                            <MaterialDesignIcon iconName="phone" class="size-3" />
                                            {t("call.call_back")}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </li>
                {/each}
            </ul>

            {#if hasMoreCallHistory}
                <div class="p-4 border-t border-sem-border text-center bg-sem-surface-muted/30">
                    <button
                        type="button"
                        class="text-xs font-bold text-sem-accent hover:underline uppercase tracking-wider cursor-pointer focus-ring-sem"
                        onclick={() => onloadmore?.()}
                    >
                        {t("call.load_more")}
                    </button>
                </div>
            {/if}
        {/if}
    </div>
</div>
