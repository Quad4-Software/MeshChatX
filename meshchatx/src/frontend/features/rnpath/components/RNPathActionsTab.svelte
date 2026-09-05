<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { DESTINATION_HASH_HEX_LENGTH } from "../lib/constants.js";

    let {
        onRequestPath,
        onDropAllVia,
        onDropAnnounceQueues,
    }: {
        onRequestPath?: (hash: string) => Promise<void> | void;
        onDropAllVia?: (hash: string) => Promise<void> | void;
        onDropAnnounceQueues?: () => Promise<void> | void;
    } = $props();

    let requestHash = $state("");
    let dropViaHash = $state("");

    async function handleRequestPath(): Promise<void> {
        if (requestHash.length !== DESTINATION_HASH_HEX_LENGTH) {
            return;
        }
        await onRequestPath?.(requestHash);
        requestHash = "";
    }

    async function handleDropAllVia(): Promise<void> {
        if (dropViaHash.length !== DESTINATION_HASH_HEX_LENGTH) {
            return;
        }
        await onDropAllVia?.(dropViaHash);
        dropViaHash = "";
    }
</script>

<div class="max-w-2xl mx-auto space-y-6">
    <!-- request path -->
    <section class="rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-6 space-y-4">
        <h2 class="text-lg font-bold">Request Path</h2>
        <p class="text-sm text-gray-500">Broadcast a path request for a destination hash.</p>
        <div class="flex flex-col sm:flex-row gap-2">
            <input
                bind:value={requestHash}
                type="text"
                placeholder="Destination Hash (32 hex chars)"
                class="input-field flex-1 min-w-0 font-mono"
            />
            <button
                type="button"
                class="px-4 py-2.5 sm:py-2 bg-indigo-600 text-white rounded-lg font-semibold hover:bg-indigo-500 transition active:scale-95 disabled:opacity-50 shrink-0 cursor-pointer disabled:cursor-not-allowed"
                disabled={requestHash.length !== DESTINATION_HASH_HEX_LENGTH}
                onclick={handleRequestPath}
            >
                Request
            </button>
        </div>
    </section>

    <!-- drop all via -->
    <section class="rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-6 space-y-4">
        <h2 class="text-lg font-bold">Drop All Via</h2>
        <p class="text-sm text-gray-500">Remove all known paths routed through a specific transport instance.</p>
        <div class="flex flex-col sm:flex-row gap-2">
            <input
                bind:value={dropViaHash}
                type="text"
                placeholder="Transport Instance Hash"
                class="input-field flex-1 min-w-0 font-mono"
            />
            <button
                type="button"
                class="px-4 py-2.5 sm:py-2 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-500 transition active:scale-95 disabled:opacity-50 shrink-0 cursor-pointer disabled:cursor-not-allowed"
                disabled={dropViaHash.length !== DESTINATION_HASH_HEX_LENGTH}
                onclick={handleDropAllVia}
            >
                Drop All
            </button>
        </div>
    </section>

    <!-- drop queues -->
    <section class="rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-6 space-y-4">
        <h2 class="text-lg font-bold">Drop Announce Queues</h2>
        <p class="text-sm text-gray-500">Clear all outbound announce packets currently queued on all interfaces.</p>
        <button
            type="button"
            class="w-full px-4 py-3 bg-zinc-800 text-white rounded-lg font-semibold hover:bg-zinc-700 transition active:scale-95 cursor-pointer"
            onclick={() => onDropAnnounceQueues?.()}
        >
            Purge All Queues
        </button>
    </section>
</div>
