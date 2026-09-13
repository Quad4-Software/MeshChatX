<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import Utils from "../../../js/Utils.js";
    import { t } from "../../../js/i18n.js";
    import type { RrcDiscoveredHub } from "../lib/types.js";

    interface Props {
        discoveredHubs: RrcDiscoveredHub[];
        isLoading?: boolean;
        onrefresh?: () => void;
        onconnect?: (hub: RrcDiscoveredHub) => void;
        oncopyhash?: (hash: string) => void;
    }

    let { discoveredHubs = [], isLoading = false, onrefresh, onconnect, oncopyhash }: Props = $props();

    let searchTerm = $state("");

    const filteredDiscovered = $derived.by(() => {
        if (!searchTerm.trim()) return discoveredHubs;
        const clean = searchTerm.toLowerCase();
        return discoveredHubs.filter((h) => {
            const name = String(h.name || h.display_name || h.custom_display_name || "").toLowerCase();
            const hash = String(h.hub_hash || h.destination_hash || "").toLowerCase();
            return name.includes(clean) || hash.includes(clean);
        });
    });
</script>

<div class="flex flex-1 flex-col overflow-hidden bg-sem-canvas p-4 sm:p-6 text-sem-fg">
    <div class="flex items-center justify-between mb-4">
        <div>
            <h2 class="text-lg font-bold">{t("relay_chat.discovery_title")}</h2>
            <p class="text-xs text-sem-fg-muted">{t("relay_chat.discovery_subtitle")}</p>
        </div>
        <button
            type="button"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-sem-border bg-sem-surface text-xs font-semibold hover:bg-sem-surface-muted transition-colors cursor-pointer"
            disabled={isLoading}
            onclick={() => onrefresh?.()}
        >
            <MaterialDesignIcon
                iconName={isLoading ? "loading" : "refresh"}
                class="size-4 {isLoading ? 'animate-spin' : ''}"
            />
            <span>{t("common.refresh")}</span>
        </button>
    </div>

    <div class="mb-4">
        <input
            type="text"
            bind:value={searchTerm}
            placeholder={t("relay_chat.search_discovered_hubs")}
            class="w-full max-w-md px-3 py-2 text-sm bg-sem-surface border border-sem-border rounded-xl text-sem-fg focus:outline-hidden focus:border-sem-accent"
        />
    </div>

    <div class="flex-1 overflow-y-auto space-y-2">
        {#if filteredDiscovered.length === 0}
            <div class="p-8 text-center text-sm text-sem-fg-muted">
                {isLoading ? t("relay_chat.discovering_hubs") : t("relay_chat.no_discovered_hubs")}
            </div>
        {:else}
            {#each filteredDiscovered as hub (hub.hub_hash || hub.destination_hash)}
                <div
                    class="flex items-center justify-between p-3 rounded-xl border border-sem-border bg-sem-surface hover:border-sem-accent/50 transition-colors"
                >
                    <div class="min-w-0 flex-1 mr-3">
                        <div class="font-semibold text-sm truncate">
                            {hub.name || hub.display_name || hub.custom_display_name || t("relay_chat.unnamed_hub")}
                        </div>
                        <div class="font-mono text-xs text-sem-fg-muted truncate">
                            {hub.hub_hash || hub.destination_hash}
                        </div>
                        <div class="flex items-center gap-2 mt-1 text-[11px] text-sem-fg-muted">
                            {#if hub.hops !== undefined}
                                <span>{hub.hops} {hub.hops === 1 ? t("app.hop") : t("app.hops_plural")}</span>
                            {/if}
                            {#if hub.last_heard}
                                <span>· {Utils.formatTimeAgo(String(hub.last_heard))}</span>
                            {/if}
                        </div>
                    </div>

                    <div class="flex items-center gap-1.5 shrink-0">
                        <button
                            type="button"
                            class="p-2 rounded-lg border border-sem-border text-sem-fg-muted hover:text-sem-fg hover:bg-sem-surface-muted transition-colors cursor-pointer"
                            title={t("relay_chat.copy_hub_hash")}
                            onclick={() => oncopyhash?.(String(hub.hub_hash || hub.destination_hash || ""))}
                        >
                            <MaterialDesignIcon iconName="content-copy" class="size-4" />
                        </button>
                        <button
                            type="button"
                            class="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-sem-action-primary text-xs font-semibold text-white hover:bg-sem-action-primary-hover transition-colors cursor-pointer"
                            onclick={() => onconnect?.(hub)}
                        >
                            <MaterialDesignIcon iconName="plus" class="size-4" />
                            <span>{t("relay_chat.connect_hub")}</span>
                        </button>
                    </div>
                </div>
            {/each}
        {/if}
    </div>
</div>
