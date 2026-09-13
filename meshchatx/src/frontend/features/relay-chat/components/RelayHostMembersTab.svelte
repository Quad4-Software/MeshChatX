<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import ToastUtils from "../../../js/ToastUtils.js";
    import { t } from "../../../js/i18n.js";
    import { formatTime } from "../lib/relayFormatters.js";
    import type { RrcMember } from "../lib/types.js";

    interface Props {
        hubId: string;
        members?: RrcMember[];
        roomFilter?: string | null;
        localIdentityHash?: string | null;
        onRefresh?: () => void;
        onFetchMembers?: () => void;
        onEnsureLocalIdentity?: () => Promise<void>;
    }

    let {
        hubId,
        members = [],
        roomFilter = null,
        localIdentityHash = null,
        onRefresh,
        onFetchMembers,
        onEnsureLocalIdentity,
    }: Props = $props();

    let membersSearch = $state("");
    let selectedMember = $state<RrcMember | null>(null);
    let memberMessages = $state<{ ts: number; room?: string; text: string }[]>([]);
    let messagesLoading = $state(false);

    const filteredMembers = $derived.by(() => {
        if (!membersSearch.trim()) return members;
        const clean = membersSearch.toLowerCase();
        return members.filter(
            (m) =>
                (m.nickname || (m as any).name || "").toLowerCase().includes(clean) ||
                (m.identity_hash || (m as any).hash || "").toLowerCase().includes(clean)
        );
    });

    export async function moderate(member: any, action: string) {
        if (!hubId || !member) return;
        const mHash = member.hash || member.identity_hash;
        if (!mHash) return;

        if (onEnsureLocalIdentity) {
            await onEnsureLocalIdentity();
        }
        if (localIdentityHash && mHash.toLowerCase() === localIdentityHash.toLowerCase()) {
            ToastUtils.warning(t("relay_chat.host_moderation_cannot_target_self"));
            return;
        }

        const room = roomFilter || (member.rooms && member.rooms[0]) || null;
        const api = (window as any).api;
        if (!api) return;
        try {
            await api.post(`/api/v1/rrc/servers/${hubId}/moderate`, {
                action,
                peer: mHash,
                room,
            });
            ToastUtils.success(t("relay_chat.host_moderation_success"));
            onFetchMembers?.();
            onRefresh?.();
        } catch (e: any) {
            ToastUtils.error(e.response?.data?.message || t("relay_chat.action_failed"));
        }
    }

    async function loadMemberMessages(member: any) {
        selectedMember = member;
        if (!hubId || !member) return;
        const mHash = member.hash || member.identity_hash;
        if (!mHash) return;
        messagesLoading = true;
        const api = (window as any).api;
        if (!api) return;
        try {
            const params: Record<string, unknown> = { peer: mHash, limit: 200 };
            if (roomFilter) params.room = roomFilter;
            const res = await api.get(`/api/v1/rrc/servers/${hubId}/messages`, { params });
            memberMessages = res.data?.messages || [];
        } catch {
            memberMessages = [];
        } finally {
            messagesLoading = false;
        }
    }
</script>

<div class="flex flex-1 min-h-0 overflow-hidden">
    <div class="flex flex-col w-full sm:w-80 border-r border-sem-border bg-sem-surface p-3 space-y-3 overflow-y-auto">
        <div class="relative">
            <MaterialDesignIcon
                iconName="magnify"
                class="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-sem-fg-muted"
            />
            <input
                type="search"
                bind:value={membersSearch}
                placeholder={t("relay_chat.filter_members")}
                class="w-full pl-8 pr-2 py-1.5 text-xs bg-sem-canvas border border-sem-border rounded-lg text-sem-fg"
            />
        </div>

        <div class="space-y-1">
            {#each filteredMembers as member (member.hash || member.identity_hash || member.name)}
                <div
                    class="flex w-full items-center justify-between p-2 rounded-lg border border-sem-border hover:bg-sem-surface-muted text-left text-xs {selectedMember ===
                    member
                        ? 'ring-2 ring-sem-accent'
                        : ''}"
                >
                    <button
                        type="button"
                        class="min-w-0 flex-1 text-left cursor-pointer"
                        onclick={() => loadMemberMessages(member)}
                    >
                        <div class="font-semibold">{member.name || member.nickname || "Unknown"}</div>
                        <div class="font-mono text-[10px] text-sem-fg-muted truncate">
                            {member.hash || member.identity_hash}
                        </div>
                    </button>
                    <div class="flex items-center gap-1 shrink-0">
                        <button
                            type="button"
                            class="p-1 text-sem-fg-muted hover:text-amber-500 rounded cursor-pointer"
                            title={t("relay_chat.kick_member")}
                            onclick={() => moderate(member, "kick")}
                        >
                            <MaterialDesignIcon iconName="account-remove" class="size-3.5" />
                        </button>
                        <button
                            type="button"
                            class="p-1 text-sem-fg-muted hover:text-red-500 rounded cursor-pointer"
                            title={t("relay_chat.ban_member")}
                            onclick={() => moderate(member, "ban")}
                        >
                            <MaterialDesignIcon iconName="account-cancel" class="size-3.5" />
                        </button>
                    </div>
                </div>
            {/each}
        </div>
    </div>

    <div class="flex-1 flex flex-col min-h-0 bg-sem-canvas p-4 overflow-y-auto">
        {#if selectedMember}
            <div class="mb-3 pb-2 border-b border-sem-border flex items-center justify-between">
                <div>
                    <div class="font-bold text-sm">{selectedMember.name || selectedMember.nickname}</div>
                    <div class="font-mono text-xs text-sem-fg-muted">
                        {selectedMember.hash || selectedMember.identity_hash}
                    </div>
                </div>
            </div>

            <div class="flex-1 overflow-y-auto space-y-1">
                {#if messagesLoading}
                    <div class="p-4 text-center text-xs text-sem-fg-muted">{t("common.loading")}</div>
                {:else if memberMessages.length === 0}
                    <div class="p-4 text-center text-xs text-sem-fg-muted">
                        {t("relay_chat.no_messages_for_member")}
                    </div>
                {:else}
                    {#each memberMessages as msg, idx (msg.ts || idx)}
                        <div class="p-2 rounded bg-sem-surface border border-sem-border text-xs">
                            <div class="flex items-center justify-between text-[10px] text-sem-fg-muted mb-0.5">
                                <span>#{msg.room || "unknown"}</span>
                                <span>{formatTime(msg.ts)}</span>
                            </div>
                            <div class="break-words">{msg.text}</div>
                        </div>
                    {/each}
                {/if}
            </div>
        {:else}
            <div class="flex-1 flex items-center justify-center text-center text-sm text-sem-fg-muted">
                {t("relay_chat.select_member_to_view_activity")}
            </div>
        {/if}
    </div>
</div>
