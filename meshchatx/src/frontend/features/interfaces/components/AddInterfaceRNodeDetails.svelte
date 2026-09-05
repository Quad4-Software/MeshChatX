<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "./Toggle.svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { RNODE_DEFAULTS } from "../lib/constants.js";
    import type { Comport } from "../lib/types.js";

    interface Props {
        rnodeTransport: "serial" | "tcp" | "bluetooth" | "ble";
        port: string | null;
        rnodeTcpHost: string | null;
        rnodeTcpPort: number | string | null;
        frequency: number | string | null;
        bandwidth: number | string | null;
        spreadingFactor: number | string | null;
        codingRate: number | string | null;
        txpower: number | string | null;
        flowControl: boolean;
        autotune: boolean;
        idCallsign: string | null;
        idInterval: number | string | null;
        comports?: Comport[];
        comportsLoading?: boolean;
        onrnodetransportchange?: (val: "serial" | "tcp" | "bluetooth" | "ble") => void;
        onportchange?: (val: string) => void;
        onrnodetcphostchange?: (val: string) => void;
        onrnodetcpportchange?: (val: string) => void;
        onfrequencychange?: (val: string) => void;
        onbandwidthchange?: (val: string) => void;
        onspreadingfactorchange?: (val: string) => void;
        oncodingratechange?: (val: string) => void;
        ontxpowerchange?: (val: string) => void;
        onflowcontrolchange?: (val: boolean) => void;
        onautotunechange?: (val: boolean) => void;
        onidcallsignchange?: (val: string) => void;
        onidintervalchange?: (val: string) => void;
        onrefreshcomports?: () => void;
    }

    let {
        rnodeTransport = "serial",
        port = null,
        rnodeTcpHost = null,
        rnodeTcpPort = null,
        frequency = null,
        bandwidth = 125000,
        spreadingFactor = 7,
        codingRate = 5,
        txpower = 17,
        flowControl = false,
        autotune = false,
        idCallsign = null,
        idInterval = null,
        comports = [],
        comportsLoading = false,
        onrnodetransportchange,
        onportchange,
        onrnodetcphostchange,
        onrnodetcpportchange,
        onfrequencychange,
        onbandwidthchange,
        onspreadingfactorchange,
        oncodingratechange,
        ontxpowerchange,
        onflowcontrolchange,
        onautotunechange,
        onidcallsignchange,
        onidintervalchange,
        onrefreshcomports,
    }: Props = $props();

    const frequencyInMhz = $derived(
        frequency ? (Number(frequency) > 1000000 ? Number(frequency) / 1000000 : Number(frequency)) : ""
    );

    function handleFrequencyInput(val: string) {
        const num = parseFloat(val);
        if (Number.isFinite(num)) {
            // If user enters MHz like 915 or 868, store in Hz
            const hz = num < 10000 ? Math.round(num * 1000000) : num;
            onfrequencychange?.(String(hz));
        } else {
            onfrequencychange?.(val);
        }
    }
</script>

<div class="space-y-4">
    <!-- RNode Transport Sub-selector -->
    <div class="flex flex-wrap gap-2 pb-2">
        <button
            type="button"
            class="text-xs py-1 px-3 rounded-full border transition-colors {rnodeTransport === 'serial'
                ? 'bg-emerald-500/10 border-emerald-500 text-emerald-700 dark:text-emerald-400 font-bold'
                : 'border-sem-border text-sem-fg-muted'}"
            onclick={() => onrnodetransportchange?.("serial")}
        >
            Serial / USB
        </button>
        <button
            type="button"
            class="text-xs py-1 px-3 rounded-full border transition-colors {rnodeTransport === 'tcp'
                ? 'bg-emerald-500/10 border-emerald-500 text-emerald-700 dark:text-emerald-400 font-bold'
                : 'border-sem-border text-sem-fg-muted'}"
            onclick={() => onrnodetransportchange?.("tcp")}
        >
            TCP / IP
        </button>
        <button
            type="button"
            class="text-xs py-1 px-3 rounded-full border transition-colors {rnodeTransport === 'bluetooth'
                ? 'bg-emerald-500/10 border-emerald-500 text-emerald-700 dark:text-emerald-400 font-bold'
                : 'border-sem-border text-sem-fg-muted'}"
            onclick={() => onrnodetransportchange?.("bluetooth")}
        >
            Bluetooth (Classic)
        </button>
        <button
            type="button"
            class="text-xs py-1 px-3 rounded-full border transition-colors {rnodeTransport === 'ble'
                ? 'bg-emerald-500/10 border-emerald-500 text-emerald-700 dark:text-emerald-400 font-bold'
                : 'border-sem-border text-sem-fg-muted'}"
            onclick={() => onrnodetransportchange?.("ble")}
        >
            Bluetooth LE
        </button>
    </div>

    {#if rnodeTransport === "serial"}
        <div>
            <div class="flex items-center justify-between mb-1">
                <label for="rnode-serial-port" class="glass-label block font-medium mb-0!">Serial Port</label>
                <button
                    type="button"
                    class="text-xs text-blue-500 hover:underline flex items-center gap-1"
                    disabled={comportsLoading}
                    onclick={onrefreshcomports}
                >
                    <MaterialDesignIcon
                        iconName="refresh"
                        class="w-3.5 h-3.5 {comportsLoading ? 'animate-spin' : ''}"
                    />
                    <span>Scan Ports</span>
                </button>
            </div>
            {#if comports.length > 0}
                <select
                    id="rnode-serial-port"
                    value={port || ""}
                    class="input-field"
                    onchange={(e) => onportchange?.((e.target as HTMLSelectElement).value)}
                >
                    <option value="">Select a port...</option>
                    {#each comports as cp (cp.device)}
                        <option value={cp.device}>{cp.device} ({cp.description || "Serial"})</option>
                    {/each}
                </select>
            {:else}
                <input
                    id="rnode-serial-port"
                    value={port ?? ""}
                    type="text"
                    placeholder="/dev/ttyUSB0 or COM3"
                    class="input-field"
                    oninput={(e) => onportchange?.((e.target as HTMLInputElement).value)}
                />
            {/if}
        </div>
    {:else if rnodeTransport === "tcp"}
        <div class="grid grid-cols-2 gap-4">
            <div>
                <label for="rnode-tcp-host" class="glass-label block font-medium mb-1">RNode IP / Host</label>
                <input
                    id="rnode-tcp-host"
                    value={rnodeTcpHost ?? ""}
                    type="text"
                    placeholder="192.168.1.50"
                    class="input-field"
                    oninput={(e) => onrnodetcphostchange?.((e.target as HTMLInputElement).value)}
                />
            </div>
            <div>
                <label for="rnode-tcp-port" class="glass-label block font-medium mb-1">Port</label>
                <input
                    id="rnode-tcp-port"
                    value={rnodeTcpPort ?? ""}
                    type="number"
                    placeholder="4242"
                    class="input-field"
                    oninput={(e) => onrnodetcpportchange?.((e.target as HTMLInputElement).value)}
                />
            </div>
        </div>
    {:else}
        <div>
            <label for="rnode-bt-port" class="glass-label block font-medium mb-1">Bluetooth Address / Device</label>
            <input
                id="rnode-bt-port"
                value={port ?? ""}
                type="text"
                placeholder="00:11:22:33:44:55 or device name"
                class="input-field"
                oninput={(e) => onportchange?.((e.target as HTMLInputElement).value)}
            />
        </div>
    {/if}

    <!-- LoRa Parameters Grid -->
    <div class="grid grid-cols-2 gap-4">
        <div>
            <label for="rnode-freq" class="glass-label block font-medium mb-1">Frequency (MHz)</label>
            <input
                id="rnode-freq"
                value={frequencyInMhz}
                type="number"
                step="0.025"
                placeholder="868.0 or 915.0"
                class="input-field"
                oninput={(e) => handleFrequencyInput((e.target as HTMLInputElement).value)}
            />
        </div>
        <div>
            <label for="rnode-bw" class="glass-label block font-medium mb-1">Bandwidth (Hz)</label>
            <select
                id="rnode-bw"
                value={String(bandwidth ?? 125000)}
                class="input-field"
                onchange={(e) => onbandwidthchange?.((e.target as HTMLSelectElement).value)}
            >
                {#each RNODE_DEFAULTS.bandwidths as bw (bw)}
                    <option value={String(bw)}>{bw >= 1000 ? `${bw / 1000} kHz` : `${bw} Hz`}</option>
                {/each}
            </select>
        </div>
    </div>

    <div class="grid grid-cols-3 gap-3">
        <div>
            <label for="rnode-sf" class="glass-label block font-medium mb-1">SF</label>
            <select
                id="rnode-sf"
                value={String(spreadingFactor ?? 7)}
                class="input-field"
                onchange={(e) => onspreadingfactorchange?.((e.target as HTMLSelectElement).value)}
            >
                {#each RNODE_DEFAULTS.spreadingfactors as sf (sf)}
                    <option value={String(sf)}>SF{sf}</option>
                {/each}
            </select>
        </div>
        <div>
            <label for="rnode-cr" class="glass-label block font-medium mb-1">CR</label>
            <select
                id="rnode-cr"
                value={String(codingRate ?? 5)}
                class="input-field"
                onchange={(e) => oncodingratechange?.((e.target as HTMLSelectElement).value)}
            >
                {#each RNODE_DEFAULTS.codingrates as cr (cr)}
                    <option value={String(cr)}>4/{cr}</option>
                {/each}
            </select>
        </div>
        <div>
            <label for="rnode-txpower" class="glass-label block font-medium mb-1">Tx Power (dBm)</label>
            <input
                id="rnode-txpower"
                value={txpower ?? 17}
                type="number"
                min={RNODE_DEFAULTS.txpowerMin}
                max={RNODE_DEFAULTS.txpowerMax}
                class="input-field"
                oninput={(e) => ontxpowerchange?.((e.target as HTMLInputElement).value)}
            />
        </div>
    </div>

    <div class="flex items-center gap-4 pt-2">
        <div class="flex items-center gap-2">
            <Toggle id="rnode-flow-control" checked={flowControl} onchange={(val) => onflowcontrolchange?.(val)} />
            <label for="rnode-flow-control" class="cursor-pointer mb-0! text-xs font-medium">Flow Control</label>
        </div>
        <div class="flex items-center gap-2">
            <Toggle id="rnode-autotune" checked={autotune} onchange={(val) => onautotunechange?.(val)} />
            <label for="rnode-autotune" class="cursor-pointer mb-0! text-xs font-medium">Autotune</label>
        </div>
    </div>

    <div class="grid grid-cols-2 gap-4 pt-2">
        <div>
            <label for="rnode-id-callsign" class="glass-label block font-medium mb-1">ID Callsign (optional)</label>
            <input
                id="rnode-id-callsign"
                value={idCallsign ?? ""}
                type="text"
                placeholder="N0CALL"
                class="input-field uppercase"
                oninput={(e) => onidcallsignchange?.((e.target as HTMLInputElement).value)}
            />
        </div>
        <div>
            <label for="rnode-id-interval" class="glass-label block font-medium mb-1">ID Interval (s)</label>
            <input
                id="rnode-id-interval"
                value={idInterval ?? ""}
                type="number"
                placeholder="600"
                class="input-field"
                oninput={(e) => onidintervalchange?.((e.target as HTMLInputElement).value)}
            />
        </div>
    </div>
</div>
