<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import type { KernelInterface } from "../lib/types.js";

    interface Props {
        groupId: string | null;
        multicastAddressType: string | null;
        devices: string | null;
        ignoredDevices: string | null;
        discoveryScope: string | null;
        discoveryPort: number | string | null;
        dataPort: number | string | null;
        hostKernelInterfaces?: KernelInterface[];
        hostKernelInterfacesLoading?: boolean;
        ongroupidchange?: (val: string) => void;
        onmulticastaddresstypechange?: (val: string) => void;
        ondeviceschange?: (val: string) => void;
        onignoreddeviceschange?: (val: string) => void;
        ondiscoveryscopechange?: (val: string) => void;
        ondiscoveryportchange?: (val: string) => void;
        ondataportchange?: (val: string) => void;
    }

    let {
        groupId = null,
        multicastAddressType = null,
        devices = null,
        ignoredDevices = null,
        discoveryScope = null,
        discoveryPort = null,
        dataPort = null,
        hostKernelInterfaces = [],
        ongroupidchange,
        onmulticastaddresstypechange,
        ondeviceschange,
        onignoreddeviceschange,
        ondiscoveryscopechange,
        ondiscoveryportchange,
        ondataportchange,
    }: Props = $props();

    function isChipActive(fieldValue: string | null, token: string): boolean {
        if (!fieldValue) return false;
        const parts = fieldValue.split(",").map((p) => p.trim());
        return parts.includes(token.trim());
    }

    function toggleChip(fieldValue: string | null, token: string): string {
        const parts = (fieldValue || "")
            .split(",")
            .map((p) => p.trim())
            .filter(Boolean);
        const idx = parts.indexOf(token.trim());
        if (idx >= 0) {
            parts.splice(idx, 1);
        } else {
            parts.push(token.trim());
        }
        return parts.join(", ");
    }
</script>

<div class="space-y-4">
    <div class="p-3 bg-pink-500/10 border border-pink-500/20 rounded-2xl text-xs text-pink-700 dark:text-pink-300">
        <div class="font-semibold">Auto Interface (Local Network)</div>
        <p class="mt-0.5 opacity-80">
            Automatically discovers and peers with other Reticulum nodes on your local ethernet / Wi-Fi segment.
        </p>
    </div>

    <div>
        <label for="auto-group-id" class="glass-label block font-medium mb-1">Group ID (optional)</label>
        <input
            id="auto-group-id"
            value={groupId ?? ""}
            type="text"
            placeholder="e.g. reticulum or my-mesh"
            class="input-field"
            oninput={(e) => ongroupidchange?.((e.target as HTMLInputElement).value)}
        />
    </div>

    <div class="grid grid-cols-2 gap-4">
        <div>
            <label for="auto-multicast-type" class="glass-label block font-medium mb-1">Multicast Address Type</label>
            <select
                id="auto-multicast-type"
                value={multicastAddressType ?? "link"}
                class="input-field"
                onchange={(e) => onmulticastaddresstypechange?.((e.target as HTMLSelectElement).value)}
            >
                <option value="link">Link-local</option>
                <option value="admin">Admin-local</option>
                <option value="site">Site-local</option>
                <option value="org">Org-local</option>
                <option value="global">Global</option>
            </select>
        </div>
        <div>
            <label for="auto-discovery-scope" class="glass-label block font-medium mb-1">Discovery Scope</label>
            <input
                id="auto-discovery-scope"
                value={discoveryScope ?? ""}
                type="text"
                placeholder="default"
                class="input-field"
                oninput={(e) => ondiscoveryscopechange?.((e.target as HTMLInputElement).value)}
            />
        </div>
    </div>

    <div class="grid grid-cols-2 gap-4">
        <div>
            <label for="auto-discovery-port" class="glass-label block font-medium mb-1">Discovery Port</label>
            <input
                id="auto-discovery-port"
                value={discoveryPort ?? ""}
                type="number"
                placeholder="default (29716)"
                class="input-field"
                oninput={(e) => ondiscoveryportchange?.((e.target as HTMLInputElement).value)}
            />
        </div>
        <div>
            <label for="auto-data-port" class="glass-label block font-medium mb-1">Data Port</label>
            <input
                id="auto-data-port"
                value={dataPort ?? ""}
                type="number"
                placeholder="default (29717)"
                class="input-field"
                oninput={(e) => ondataportchange?.((e.target as HTMLInputElement).value)}
            />
        </div>
    </div>

    <div>
        <label for="auto-devices" class="glass-label block font-medium mb-1">Allowed Devices (comma-separated)</label>
        <input
            id="auto-devices"
            value={devices ?? ""}
            type="text"
            placeholder="eth0, wlan0"
            class="input-field"
            oninput={(e) => ondeviceschange?.((e.target as HTMLInputElement).value)}
        />
        {#if hostKernelInterfaces.length > 0}
            <div class="flex flex-wrap gap-1 mt-1.5 max-h-20 overflow-y-auto">
                {#each hostKernelInterfaces as k (k.name)}
                    <button
                        type="button"
                        class="px-2 py-0.5 rounded-md text-[10px] font-mono border transition-colors {isChipActive(
                            devices,
                            k.name
                        )
                            ? 'bg-pink-500 text-white border-pink-500'
                            : 'bg-sem-surface border-sem-border text-sem-fg'}"
                        onclick={() => ondeviceschange?.(toggleChip(devices, k.name))}
                    >
                        {k.name}
                    </button>
                {/each}
            </div>
        {/if}
    </div>

    <div>
        <label for="auto-ignored-devices" class="glass-label block font-medium mb-1"
            >Ignored Devices (comma-separated)</label
        >
        <input
            id="auto-ignored-devices"
            value={ignoredDevices ?? ""}
            type="text"
            placeholder="docker0, veth*"
            class="input-field"
            oninput={(e) => onignoreddeviceschange?.((e.target as HTMLInputElement).value)}
        />
        {#if hostKernelInterfaces.length > 0}
            <div class="flex flex-wrap gap-1 mt-1.5 max-h-20 overflow-y-auto">
                {#each hostKernelInterfaces as k (k.name)}
                    <button
                        type="button"
                        class="px-2 py-0.5 rounded-md text-[10px] font-mono border transition-colors {isChipActive(
                            ignoredDevices,
                            k.name
                        )
                            ? 'bg-red-500 text-white border-red-500'
                            : 'bg-sem-surface border-sem-border text-sem-fg'}"
                        onclick={() => onignoreddeviceschange?.(toggleChip(ignoredDevices, k.name))}
                    >
                        {k.name}
                    </button>
                {/each}
            </div>
        {/if}
    </div>
</div>
