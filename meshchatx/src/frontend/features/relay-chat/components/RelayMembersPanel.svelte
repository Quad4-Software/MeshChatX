<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import SearchInput from "../../../ui/svelte/SearchInput.svelte";
    import { t } from "../../../js/i18n.js";
    import { filterRelayMembers } from "../../../js/relayMessageSearch.js";
    import { colorForHash, memberAvatarStyle, memberInitial } from "../lib/relayFormatters.js";
    import type { RrcMember } from "../lib/types.js";

    interface Props {
        members: RrcMember[];
        offlineMembers?: RrcMember[];
        memberDmLoadingHash?: string | null;
        onclose?: () => void;
        oninsertmention?: (name: string) => void;
        oncopymemberhash?: (member: RrcMember) => void;
        onopenmemberdm?: (member: RrcMember) => void;
    }

    let {
        members = [],
        offlineMembers = [],
        memberDmLoadingHash = null,
        onclose,
        oninsertmention,
        oncopymemberhash,
        onopenmemberdm,
    }: Props = $props();

    let membersSearch = $state("");

    const filteredOnlineMembers = $derived.by(() => filterRelayMembers(members, membersSearch));
    const filteredOfflineMembers = $derived.by(() => filterRelayMembers(offlineMembers, membersSearch));

    function avatarStyle(hash?: string | null): string {
        const s = memberAvatarStyle(hash);
        return `background-color: ${s.backgroundColor}; color: ${s.color};`;
    }
</script>

<div
    class="absolute inset-y-0 right-0 z-40 flex w-72 max-w-[min(18rem,100%)] min-h-0 flex-col border-l border-sem-border bg-sem-canvas shadow-xl text-sem-fg md:static md:z-auto md:max-w-none md:w-72 md:shadow-none"
>
    <div class="flex shrink-0 items-center justify-between gap-2 border-b border-sem-border px-3 py-2.5">
        <div class="flex items-center gap-1.5 font-semibold">
            <MaterialDesignIcon iconName="account-group" class="size-4 text-sem-accent" />
            {t("relay_chat.members_title")}
        </div>
        <button
            type="button"
            class="rounded-lg p-1 text-sem-fg-muted hover:bg-sem-surface/60 cursor-pointer"
            title={t("relay_chat.hide_members")}
            onclick={() => onclose?.()}
        >
            <MaterialDesignIcon iconName="close" class="size-4" />
        </button>
    </div>
    <div class="shrink-0 border-b border-sem-border p-2">
        <SearchInput
            bind:value={membersSearch}
            compact
            type="search"
            placeholder={t("relay_chat.members_search_placeholder")}
        />
    </div>
    <div class="min-h-0 flex-1 overflow-y-auto custom-scrollbar">
        <div>
            <div
                class="sticky top-0 z-10 border-b border-sem-border/50 bg-sem-canvas/95 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-sem-fg-muted backdrop-blur"
            >
                {t("relay_chat.members_online")} ({filteredOnlineMembers.length})
            </div>
            <ul class="p-1.5">
                {#each filteredOnlineMembers as m (m.hash)}
                    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
                    <!-- svelte-ignore a11y_click_events_have_key_events -->
                    <li
                        class="group/member flex cursor-pointer items-center gap-2.5 rounded-lg px-2 py-1.5 transition-colors hover:bg-sem-surface/60"
                        title={m.hash}
                        onclick={() => oninsertmention?.(m.name)}
                        oncontextmenu={(e) => {
                            e.preventDefault();
                            oncopymemberhash?.(m);
                        }}
                    >
                        <span
                            class="relative flex size-7 shrink-0 items-center justify-center rounded-full text-[11px] font-bold uppercase"
                            style={avatarStyle(m.hash)}
                        >
                            {memberInitial(m.name)}
                            <span
                                class="absolute -bottom-0.5 -right-0.5 size-2.5 rounded-full border-2 border-sem-canvas bg-sem-success"
                            ></span>
                        </span>
                        <span class="min-w-0 flex-1 truncate text-sm font-medium" style="color: {colorForHash(m.hash)}"
                            >{m.name}</span
                        >
                        <span class="flex items-center gap-1 shrink-0">
                            {#if memberDmLoadingHash === m.hash}
                                <MaterialDesignIcon iconName="loading" class="size-3.5 animate-spin text-sem-accent" />
                            {:else}
                                <button
                                    type="button"
                                    class="flex items-center rounded p-0.5 text-sem-fg-muted opacity-0 transition-opacity hover:text-sem-accent focus-ring-sem group-hover/member:opacity-70 max-sm:opacity-60"
                                    title={t("relay_chat.dm_member")}
                                    onclick={(e) => {
                                        e.stopPropagation();
                                        onopenmemberdm?.(m);
                                    }}
                                >
                                    <MaterialDesignIcon iconName="message-text-outline" class="size-3.5" />
                                </button>
                            {/if}
                            <MaterialDesignIcon
                                iconName="at"
                                class="size-3.5 text-sem-fg-muted opacity-0 transition-opacity group-hover/member:opacity-70"
                            />
                        </span>
                    </li>
                {/each}
            </ul>
        </div>
        {#if filteredOfflineMembers.length > 0}
            <div>
                <div
                    class="sticky top-0 z-10 border-b border-sem-border/50 bg-sem-canvas/95 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-sem-fg-muted backdrop-blur"
                >
                    {t("relay_chat.members_offline")} ({filteredOfflineMembers.length})
                </div>
                <ul class="p-1.5">
                    {#each filteredOfflineMembers as m (m.hash)}
                        <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
                        <!-- svelte-ignore a11y_click_events_have_key_events -->
                        <li
                            class="group/member flex cursor-pointer items-center gap-2.5 rounded-lg px-2 py-1.5 opacity-60 transition-all hover:bg-sem-surface/60 hover:opacity-100"
                            title={m.hash}
                            onclick={() => oninsertmention?.(m.name)}
                            oncontextmenu={(e) => {
                                e.preventDefault();
                                oncopymemberhash?.(m);
                            }}
                        >
                            <span
                                class="flex size-7 shrink-0 items-center justify-center rounded-full bg-sem-surface-muted text-[11px] font-bold uppercase text-sem-fg-muted"
                            >
                                {memberInitial(m.name)}
                            </span>
                            <span class="min-w-0 flex-1 truncate text-sm">{m.name}</span>
                            <span class="flex items-center gap-1 shrink-0">
                                {#if memberDmLoadingHash === m.hash}
                                    <MaterialDesignIcon
                                        iconName="loading"
                                        class="size-3.5 animate-spin text-sem-accent"
                                    />
                                {:else}
                                    <button
                                        type="button"
                                        class="flex items-center rounded p-0.5 text-sem-fg-muted opacity-0 transition-opacity hover:text-sem-accent focus-ring-sem group-hover/member:opacity-70 max-sm:opacity-60"
                                        title={t("relay_chat.dm_member")}
                                        onclick={(e) => {
                                            e.stopPropagation();
                                            onopenmemberdm?.(m);
                                        }}
                                    >
                                        <MaterialDesignIcon iconName="message-text-outline" class="size-3.5" />
                                    </button>
                                {/if}
                                <MaterialDesignIcon
                                    iconName="at"
                                    class="size-3.5 text-sem-fg-muted opacity-0 transition-opacity group-hover/member:opacity-70"
                                />
                            </span>
                        </li>
                    {/each}
                </ul>
            </div>
        {/if}
        {#if membersSearch.trim() && filteredOnlineMembers.length === 0 && filteredOfflineMembers.length === 0}
            <div class="px-2 py-4 text-center text-xs text-sem-fg-muted">
                {t("relay_chat.members_search_no_results")}
            </div>
        {:else if members.length === 0 && offlineMembers.length === 0}
            <div class="px-2 py-4 text-center text-xs text-sem-fg-muted">
                {t("relay_chat.no_members")}
            </div>
        {/if}
    </div>
</div>
