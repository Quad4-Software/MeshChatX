<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import type { Comport } from "../lib/types.js";

    interface Props {
        interfaceType: string;
        port: string | null;
        speed: number | string | null;
        databits: number | string | null;
        parity: string | null;
        stopbits: number | string | null;
        callsign?: string | null;
        ssid?: number | string | null;
        preamble?: number | string | null;
        txtail?: number | string | null;
        comports?: Comport[];
        comportsLoading?: boolean;
        onportchange?: (val: string) => void;
        onspeedchange?: (val: string) => void;
        ondatabitschange?: (val: string) => void;
        onparitychange?: (val: string) => void;
        onstopbitschange?: (val: string) => void;
        oncallsignchange?: (val: string) => void;
        onssidchange?: (val: string) => void;
        onpreamblechange?: (val: string) => void;
        ontxtailchange?: (val: string) => void;
        onrefreshcomports?: () => void;
    }

    let {
        interfaceType,
        port = null,
        speed = 115200,
        databits = 8,
        parity = "none",
        stopbits = 1,
        callsign = null,
        ssid = 0,
        preamble = null,
        txtail = null,
        comports = [],
        comportsLoading = false,
        onportchange,
        onspeedchange,
        ondatabitschange,
        onparitychange,
        onstopbitschange,
        oncallsignchange,
        onssidchange,
        onpreamblechange,
        ontxtailchange,
        onrefreshcomports,
    }: Props = $props();
</script>

<div class="space-y-4">
    <div>
        <div class="flex items-center justify-between mb-1">
            <label for="serial-port" class="glass-label block font-medium mb-0!">Serial Port</label>
            <button
                type="button"
                class="text-xs text-blue-500 hover:underline flex items-center gap-1"
                disabled={comportsLoading}
                onclick={onrefreshcomports}
            >
                <MaterialDesignIcon iconName="refresh" class="w-3.5 h-3.5 {comportsLoading ? 'animate-spin' : ''}" />
                <span>Scan Ports</span>
            </button>
        </div>
        {#if comports.length > 0}
            <select
                id="serial-port"
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
                id="serial-port"
                value={port ?? ""}
                type="text"
                placeholder="/dev/ttyUSB0 or COM3"
                class="input-field"
                oninput={(e) => onportchange?.((e.target as HTMLInputElement).value)}
            />
        {/if}
    </div>

    <div class="grid grid-cols-2 gap-4">
        <div>
            <label for="serial-speed" class="glass-label block font-medium mb-1">Speed (Baud)</label>
            <select
                id="serial-speed"
                value={String(speed ?? 115200)}
                class="input-field"
                onchange={(e) => onspeedchange?.((e.target as HTMLSelectElement).value)}
            >
                <option value="9600">9600</option>
                <option value="19200">19200</option>
                <option value="38400">38400</option>
                <option value="57600">57600</option>
                <option value="115200">115200</option>
                <option value="230400">230400</option>
                <option value="460800">460800</option>
                <option value="921600">921600</option>
            </select>
        </div>
        <div>
            <label for="serial-databits" class="glass-label block font-medium mb-1">Data Bits</label>
            <select
                id="serial-databits"
                value={String(databits ?? 8)}
                class="input-field"
                onchange={(e) => ondatabitschange?.((e.target as HTMLSelectElement).value)}
            >
                <option value="8">8</option>
                <option value="7">7</option>
            </select>
        </div>
    </div>

    <div class="grid grid-cols-2 gap-4">
        <div>
            <label for="serial-parity" class="glass-label block font-medium mb-1">Parity</label>
            <select
                id="serial-parity"
                value={parity ?? "none"}
                class="input-field"
                onchange={(e) => onparitychange?.((e.target as HTMLSelectElement).value)}
            >
                <option value="none">None</option>
                <option value="even">Even</option>
                <option value="odd">Odd</option>
            </select>
        </div>
        <div>
            <label for="serial-stopbits" class="glass-label block font-medium mb-1">Stop Bits</label>
            <select
                id="serial-stopbits"
                value={String(stopbits ?? 1)}
                class="input-field"
                onchange={(e) => onstopbitschange?.((e.target as HTMLSelectElement).value)}
            >
                <option value="1">1</option>
                <option value="2">2</option>
            </select>
        </div>
    </div>

    {#if interfaceType === "AX25KISSInterface"}
        <div class="grid grid-cols-2 gap-4 pt-2 border-t border-sem-border">
            <div>
                <label for="ax25-callsign" class="glass-label block font-medium mb-1">Callsign</label>
                <input
                    id="ax25-callsign"
                    value={callsign ?? ""}
                    type="text"
                    placeholder="N0CALL"
                    class="input-field uppercase"
                    oninput={(e) => oncallsignchange?.((e.target as HTMLInputElement).value)}
                />
            </div>
            <div>
                <label for="ax25-ssid" class="glass-label block font-medium mb-1">SSID</label>
                <input
                    id="ax25-ssid"
                    value={ssid ?? 0}
                    type="number"
                    min="0"
                    max="15"
                    class="input-field"
                    oninput={(e) => onssidchange?.((e.target as HTMLInputElement).value)}
                />
            </div>
        </div>
    {/if}

    {#if ["KISSInterface", "AX25KISSInterface"].includes(interfaceType)}
        <div class="grid grid-cols-2 gap-4 pt-2">
            <div>
                <label for="kiss-preamble" class="glass-label block font-medium mb-1">Preamble (ms)</label>
                <input
                    id="kiss-preamble"
                    value={preamble ?? ""}
                    type="number"
                    placeholder="default"
                    class="input-field"
                    oninput={(e) => onpreamblechange?.((e.target as HTMLInputElement).value)}
                />
            </div>
            <div>
                <label for="kiss-txtail" class="glass-label block font-medium mb-1">Tx Tail (ms)</label>
                <input
                    id="kiss-txtail"
                    value={txtail ?? ""}
                    type="number"
                    placeholder="default"
                    class="input-field"
                    oninput={(e) => ontxtailchange?.((e.target as HTMLInputElement).value)}
                />
            </div>
        </div>
    {/if}
</div>
