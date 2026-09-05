<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "./Toggle.svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { RETICULUM_MIN_FIXED_MTU } from "../lib/constants.js";

    interface Props {
        connectable: boolean;
        peers: string[];
        connectTimeout: number | string | null;
        fixedMtu: number | string | null;
        onconnectablechange?: (val: boolean) => void;
        onpeerschange?: (peers: string[]) => void;
        onconnecttimeoutchange?: (val: string) => void;
        onfixedmtuchange?: (val: string) => void;
    }

    let {
        connectable = false,
        peers = [],
        connectTimeout = null,
        fixedMtu = null,
        onconnectablechange,
        onpeerschange,
        onconnecttimeoutchange,
        onfixedmtuchange,
    }: Props = $props();

    function updatePeer(index: number, val: string) {
        const next = [...peers];
        next[index] = val;
        onpeerschange?.(next);
    }

    function addPeer() {
        onpeerschange?.([...peers, ""]);
    }

    function removePeer(index: number) {
        onpeerschange?.(peers.filter((_, i) => i !== index));
    }
</script>

<div class="space-y-4">
    <div
        class="p-3 bg-purple-500/10 border border-purple-500/20 rounded-2xl text-xs text-purple-700 dark:text-purple-300"
    >
        <div class="font-semibold">I2P SAM Bridge Interface</div>
        <p class="mt-0.5 opacity-80">Creates an anonymous tunnel over the I2P network using the local I2P router.</p>
    </div>

    <div class="flex items-center gap-2">
        <Toggle id="i2p-connectable" checked={connectable} onchange={(val) => onconnectablechange?.(val)} />
        <label for="i2p-connectable" class="cursor-pointer mb-0! text-sm font-medium">
            Connectable (Allow inbound connections from other I2P nodes)
        </label>
    </div>

    <div>
        <label for="i2p-peers-section" class="glass-label block font-medium mb-1" id="i2p-peers-section">
            I2P Peers (B32 Addresses)
        </label>
        <div class="space-y-2">
            {#each peers as peer, index (index)}
                <div class="flex items-center gap-2">
                    <input
                        value={peer}
                        type="text"
                        placeholder="e.g. abcd...1234.b32.i2p"
                        class="input-field font-mono text-xs"
                        oninput={(e) => updatePeer(index, (e.target as HTMLInputElement).value)}
                    />
                    <button type="button" class="secondary-chip text-red-500 p-2!" onclick={() => removePeer(index)}>
                        <MaterialDesignIcon iconName="trash-can" class="w-4 h-4" />
                    </button>
                </div>
            {/each}
            <button type="button" class="secondary-chip text-xs py-1.5! px-3!" onclick={addPeer}>
                <MaterialDesignIcon iconName="plus" class="w-3.5 h-3.5" />
                <span>Add Peer</span>
            </button>
        </div>
    </div>

    <div class="grid grid-cols-2 gap-4">
        <div>
            <label for="i2p-connect-timeout" class="glass-label block font-medium mb-1">Connect Timeout (s)</label>
            <input
                id="i2p-connect-timeout"
                value={connectTimeout ?? ""}
                type="number"
                min="0"
                placeholder="default"
                class="input-field"
                oninput={(e) => onconnecttimeoutchange?.((e.target as HTMLInputElement).value)}
            />
        </div>
        <div>
            <label for="i2p-fixed-mtu" class="glass-label block font-medium mb-1">Fixed MTU</label>
            <input
                id="i2p-fixed-mtu"
                value={fixedMtu ?? ""}
                type="number"
                min={RETICULUM_MIN_FIXED_MTU}
                placeholder="auto"
                class="input-field"
                oninput={(e) => onfixedmtuchange?.((e.target as HTMLInputElement).value)}
            />
        </div>
    </div>
</div>
