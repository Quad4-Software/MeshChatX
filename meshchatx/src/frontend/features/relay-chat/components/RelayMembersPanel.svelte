<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import IconButton from "../../../ui/svelte/IconButton.svelte";
    import { t } from "../../../js/i18n.js";
    import { filterRelayMembers } from "../../../js/relayMessageSearch.js";
    import type { RrcMember } from "../lib/types.js";

    interface Props {
        members: RrcMember[];
        canModerate?: boolean;
        onclose?: () => void;
        onkickmember?: (member: RrcMember) => void;
        onbanmember?: (member: RrcMember) => void;
        ontogglememberop?: (member: RrcMember) => void;
    }

    let { members = [], canModerate = false, onclose, onkickmember, onbanmember, ontogglememberop }: Props = $props();

    let searchTerm = $state("");

    const filteredMembers = $derived.by(() => {
        return filterRelayMembers(members, searchTerm);
    });
</script>

<div class="flex flex-col w-56 sm:w-64 border-l border-sem-border bg-sem-surface h-full min-h-0 text-sem-fg">
    <div class="flex items-center justify-between px-3 py-2 border-b border-sem-border">
        <div class="flex items-center gap-1.5 font-semibold text-sm">
            <MaterialDesignIcon iconName="account-group" class="size-4 text-sem-fg-muted" />
            <span>{t("relay_chat.members")} ({members.length})</span>
        </div>
        <IconButton
            class="size-7 text-sem-fg-muted hover:text-sem-fg"
            title={t("common.close")}
            onclick={() => onclose?.()}
        >
            <MaterialDesignIcon iconName="close" class="size-4" />
        </IconButton>
    </div>

    <div class="p-2 border-b border-sem-border">
        <div class="relative">
            <MaterialDesignIcon
                iconName="magnify"
                class="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-sem-fg-muted"
            />
            <input
                type="text"
                bind:value={searchTerm}
                placeholder={t("relay_chat.filter_members")}
                class="w-full pl-8 pr-2 py-1 text-xs bg-sem-canvas border border-sem-border rounded-md text-sem-fg focus:outline-hidden focus:border-sem-accent"
            />
        </div>
    </div>

    <div class="flex-1 overflow-y-auto p-1.5 space-y-0.5">
        {#if filteredMembers.length === 0}
            <div class="p-3 text-center text-xs text-sem-fg-muted">
                {t("relay_chat.no_members_found")}
            </div>
        {:else}
            {#each filteredMembers as member, idx (member.identity_hash || member.nickname || idx)}
                <div
                    class="group flex items-center justify-between px-2 py-1.5 rounded-md hover:bg-sem-surface-muted text-xs"
                >
                    <div class="flex items-center gap-1.5 min-w-0 flex-1">
                        {#if member.is_founder}
                            <span title={t("relay_chat.role_founder")}>
                                <MaterialDesignIcon iconName="crown" class="size-3.5 shrink-0 text-amber-500" />
                            </span>
                        {:else if member.is_operator}
                            <span title={t("relay_chat.role_operator")}>
                                <MaterialDesignIcon iconName="shield-star" class="size-3.5 shrink-0 text-blue-500" />
                            </span>
                        {:else if member.has_voice}
                            <span title={t("relay_chat.role_voice")}>
                                <MaterialDesignIcon iconName="volume-high" class="size-3.5 shrink-0 text-emerald-500" />
                            </span>
                        {:else}
                            <MaterialDesignIcon iconName="account" class="size-3.5 shrink-0 text-sem-fg-muted" />
                        {/if}

                        <span class="truncate font-medium"
                            >{member.nickname || member.identity_hash?.substring(0, 8) || "Unknown"}</span
                        >
                    </div>

                    {#if canModerate && !member.is_founder}
                        <div class="hidden group-hover:flex items-center gap-0.5 shrink-0">
                            <button
                                type="button"
                                class="p-0.5 text-sem-fg-muted hover:text-blue-500 rounded"
                                title={member.is_operator ? t("relay_chat.demote_op") : t("relay_chat.promote_op")}
                                onclick={() => ontogglememberop?.(member)}
                            >
                                <MaterialDesignIcon iconName="shield-edit" class="size-3.5" />
                            </button>
                            <button
                                type="button"
                                class="p-0.5 text-sem-fg-muted hover:text-amber-500 rounded"
                                title={t("relay_chat.kick_member")}
                                onclick={() => onkickmember?.(member)}
                            >
                                <MaterialDesignIcon iconName="account-remove" class="size-3.5" />
                            </button>
                            <button
                                type="button"
                                class="p-0.5 text-sem-fg-muted hover:text-red-500 rounded"
                                title={t("relay_chat.ban_member")}
                                onclick={() => onbanmember?.(member)}
                            >
                                <MaterialDesignIcon iconName="account-cancel" class="size-3.5" />
                            </button>
                        </div>
                    {/if}
                </div>
            {/each}
        {/if}
    </div>
</div>
