<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { peerStatusLabel } from "../lib/filesyncFormat.js";
    import type { FilesyncPeer, FilesyncStatus } from "../lib/types.js";

    interface Props {
        status: FilesyncStatus;
        peers: FilesyncPeer[];
        connectHash: string;
        busy: boolean;
        onConnect: () => void;
        onDisconnect: (peerId: string) => void;
        onRefresh: () => void;
    }

    let { status, peers = [], connectHash = $bindable(""), busy, onConnect, onDisconnect, onRefresh }: Props = $props();
</script>

<div class="space-y-4">
    <p class="text-sm text-sem-fg-muted">{t("rns_filesync.devices_help")}</p>
    <div class="flex flex-col sm:flex-row gap-2">
        <input
            bind:value={connectHash}
            type="text"
            class="input-field flex-1 font-mono text-sm"
            placeholder={t("rns_filesync.peer_hash_placeholder")}
        />
        <button
            type="button"
            class="primary-chip px-4 py-2 text-sm cursor-pointer"
            disabled={busy || !status.running}
            onclick={onConnect}
        >
            <MaterialDesignIcon iconName="link-variant" class="w-4 h-4" />
            {t("rns_filesync.connect")}
        </button>
    </div>
    <button type="button" class="secondary-chip px-3 py-1.5 text-sm cursor-pointer" disabled={busy} onclick={onRefresh}>
        {t("rns_filesync.refresh")}
    </button>
    {#if peers.length === 0}
        <div class="text-sm text-sem-fg-muted">
            {t("rns_filesync.no_peers")}
        </div>
    {:else}
        <ul class="space-y-2">
            {#each peers as peer (peer.peer_id)}
                <li
                    class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-lg border border-sem-border"
                >
                    <div class="min-w-0">
                        <div class="font-mono text-xs break-all text-sem-fg">{peer.peer_id}</div>
                        <div class="text-xs text-sem-fg-muted mt-1">
                            {peerStatusLabel(peer)}
                            {#if peer.destination_hash}
                                <span class="font-mono">
                                    · {peer.destination_hash}
                                </span>
                            {/if}
                        </div>
                    </div>
                    <button
                        type="button"
                        class="secondary-chip px-3 py-1.5 text-sm text-red-600 dark:text-red-300 cursor-pointer"
                        disabled={busy}
                        onclick={() => onDisconnect(peer.peer_id)}
                    >
                        {t("rns_filesync.disconnect")}
                    </button>
                </li>
            {/each}
        </ul>
    {/if}
</div>
