<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { formatUptime } from "../lib/relayFormatters.js";
    import RelayHostRoomsTab from "./RelayHostRoomsTab.svelte";
    import RelayHostMembersTab from "./RelayHostMembersTab.svelte";
    import type { RrcHostedHub, RrcMember } from "../lib/types.js";

    interface Props {
        hub?: (RrcHostedHub & { id?: string }) | null;
        initialTab?: "rooms" | "members";
        roomFilter?: string | null;
        onback?: () => void;
        onrefresh?: () => void;
    }

    let { hub = null, initialTab = "rooms", roomFilter = null, onback, onrefresh }: Props = $props();

    let tab = $state<"rooms" | "members">("rooms");
    let roomsActivity = $state<{ name: string; member_count?: number; topic?: string; has_key?: boolean }[]>([]);
    let members = $state<RrcMember[]>([]);
    let localIdentityHash = $state<string | null>(null);
    let liveUptimeSeconds = $state(0);
    let uptimeTimer: ReturnType<typeof setInterval> | null = null;
    let membersTabRef = $state<RelayHostMembersTab | null>(null);

    const hubId = $derived(hub?.id || hub?.hub_hash || "");
    const pageTitle = $derived(
        hub?.name ? `${hub.name} - ${t("relay_chat.host_moderation_title")}` : t("relay_chat.host_moderation_title")
    );

    export async function fetchActivity() {
        if (!hubId) return;
        const api = (window as any).api;
        if (!api) return;
        try {
            const res = await api.get(`/api/v1/rrc/servers/${hubId}/activity`);
            roomsActivity = res.data?.rooms || [];
        } catch {
            roomsActivity = [];
        }
    }

    export async function fetchMembers() {
        if (!hubId) return;
        const api = (window as any).api;
        if (!api) return;
        try {
            const res = await api.get(`/api/v1/rrc/servers/${hubId}/members`);
            members = res.data?.members || [];
        } catch {
            members = [];
        }
    }

    export async function ensureLocalIdentity() {
        if (localIdentityHash) return;
        const api = (window as any).api;
        if (!api) return;
        try {
            const res = await api.get("/api/v1/config");
            const hash = res.data?.identity_hash;
            if (typeof hash === "string" && hash.trim()) {
                localIdentityHash = hash.trim().toLowerCase();
            }
        } catch {
            // ignore
        }
    }

    export async function moderate(member: any, action: string) {
        if (membersTabRef) {
            await membersTabRef.moderate(member, action);
        }
    }

    onMount(() => {
        tab = initialTab;
        if (hub?.uptime_seconds) liveUptimeSeconds = hub.uptime_seconds;
        uptimeTimer = setInterval(() => {
            if (hub?.running) liveUptimeSeconds++;
        }, 1000);
        fetchActivity();
        fetchMembers();
        ensureLocalIdentity();
    });

    onDestroy(() => {
        if (uptimeTimer) clearInterval(uptimeTimer);
    });
</script>

<div class="flex min-h-0 flex-1 flex-col overflow-hidden bg-sem-canvas text-sem-fg">
    <div class="flex items-center gap-3 border-b border-sem-border bg-sem-surface px-4 py-2.5">
        <button
            type="button"
            class="p-1.5 rounded-lg border border-sem-border text-sem-fg-muted hover:bg-sem-surface-muted transition-colors cursor-pointer"
            title={t("relay_chat.back")}
            onclick={() => onback?.()}
        >
            <MaterialDesignIcon iconName="arrow-left" class="size-5" />
        </button>
        <div class="min-w-0 flex-1">
            <h2 class="truncate text-base font-bold text-sem-fg">{pageTitle}</h2>
            {#if hub}
                <div class="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs text-sem-fg-muted">
                    <span class="inline-flex items-center gap-1.5">
                        <span class="size-2 rounded-full {hub.running ? 'bg-emerald-500' : 'bg-zinc-400'}"></span>
                        {hub.running ? t("relay_chat.host_status_running") : t("relay_chat.host_status_stopped")}
                    </span>
                    {#if hub.running && liveUptimeSeconds > 0}
                        <span
                            >· {t("relay_chat.host_moderation_uptime", { time: formatUptime(liveUptimeSeconds) })}</span
                        >
                    {/if}
                </div>
            {/if}
        </div>
    </div>

    <div class="flex border-b border-sem-border bg-sem-surface-muted text-xs font-semibold" role="tablist">
        <button
            type="button"
            role="tab"
            aria-selected={tab === "rooms"}
            class="flex items-center gap-1.5 px-4 py-2.5 border-b-2 transition-colors cursor-pointer {tab === 'rooms'
                ? 'border-sem-accent text-sem-fg bg-sem-surface'
                : 'border-transparent text-sem-fg-muted hover:text-sem-fg'}"
            onclick={() => {
                tab = "rooms";
            }}
        >
            <MaterialDesignIcon iconName="pound" class="size-4" />
            <span>{t("relay_chat.host_moderation_tab_rooms")}</span>
        </button>
        <button
            type="button"
            role="tab"
            aria-selected={tab === "members"}
            class="flex items-center gap-1.5 px-4 py-2.5 border-b-2 transition-colors cursor-pointer {tab === 'members'
                ? 'border-sem-accent text-sem-fg bg-sem-surface'
                : 'border-transparent text-sem-fg-muted hover:text-sem-fg'}"
            onclick={() => {
                tab = "members";
            }}
        >
            <MaterialDesignIcon iconName="account-group" class="size-4" />
            <span>{t("relay_chat.host_moderation_tab_members")}</span>
        </button>
    </div>

    {#if !hub}
        <div class="flex flex-1 items-center justify-center p-6 text-sm text-sem-fg-muted">
            {t("relay_chat.host_moderation_hub_missing")}
        </div>
    {:else if tab === "rooms"}
        <RelayHostRoomsTab {hubId} {roomsActivity} onRefresh={onrefresh} onFetchActivity={fetchActivity} />
    {:else if tab === "members"}
        <RelayHostMembersTab
            bind:this={membersTabRef}
            {hubId}
            {members}
            {roomFilter}
            {localIdentityHash}
            onRefresh={onrefresh}
            onFetchMembers={fetchMembers}
            onEnsureLocalIdentity={ensureLocalIdentity}
        />
    {/if}
</div>
