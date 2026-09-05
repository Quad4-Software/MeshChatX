<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "./Toggle.svelte";
    import BundledDocsHint from "./BundledDocsHint.svelte";
    import { t } from "../../../js/i18n.js";
    import { RETICULUM_MIN_FIXED_MTU } from "../lib/constants.js";
    import type { KernelInterface } from "../lib/types.js";

    interface Props {
        listenMode: boolean;
        targetHost: string | null;
        targetPort: number | string | null;
        transportIdentity: string | null;
        bootstrapOnly: boolean;
        listenIp: string | null;
        listenPort: number | string | null;
        listenDevice: string | null;
        connectTimeout: number | string | null;
        maxReconnectTries: number | string | null;
        fixedMtu: number | string | null;
        blockFastFlapping: boolean;
        fastFlappingBlockTime: number | string | null;
        fastFlappingThreshold: number | string | null;
        fastFlappingGrace: number | string | null;
        hostKernelInterfaces?: KernelInterface[];
        hostKernelInterfacesLoading?: boolean;
        onlistenmodechange?: (val: boolean) => void;
        ontargethostchange?: (val: string) => void;
        ontargetportchange?: (val: string) => void;
        ontransportidentitychange?: (val: string) => void;
        onbootstraponlychange?: (val: boolean) => void;
        onlistenipchange?: (val: string) => void;
        onlistenportchange?: (val: string) => void;
        onlistendevicechange?: (val: string) => void;
        onconnecttimeoutchange?: (val: string) => void;
        onmaxreconnecttrieschange?: (val: string) => void;
        onfixedmtuchange?: (val: string) => void;
        onblockfastflappingchange?: (val: boolean) => void;
        onfastflappingblocktimechange?: (val: string) => void;
        onfastflappingthresholdchange?: (val: string) => void;
        onfastflappinggracechange?: (val: string) => void;
    }

    let {
        listenMode = false,
        targetHost = null,
        targetPort = null,
        transportIdentity = null,
        bootstrapOnly = true,
        listenIp = null,
        listenPort = null,
        listenDevice = null,
        connectTimeout = null,
        maxReconnectTries = null,
        fixedMtu = null,
        blockFastFlapping = true,
        fastFlappingBlockTime = 720,
        fastFlappingThreshold = 20,
        fastFlappingGrace = 5,
        hostKernelInterfaces = [],
        hostKernelInterfacesLoading = false,
        onlistenmodechange,
        ontargethostchange,
        ontargetportchange,
        ontransportidentitychange,
        onbootstraponlychange,
        onlistenipchange,
        onlistenportchange,
        onlistendevicechange,
        onconnecttimeoutchange,
        onmaxreconnecttrieschange,
        onfixedmtuchange,
        onblockfastflappingchange,
        onfastflappingblocktimechange,
        onfastflappingthresholdchange,
        onfastflappinggracechange,
    }: Props = $props();
</script>

<div class="space-y-4">
    <div class="flex items-center gap-2">
        <Toggle id="backbone-listen-mode" checked={listenMode} onchange={(val) => onlistenmodechange?.(val)} />
        <label for="backbone-listen-mode" class="cursor-pointer mb-0! text-sm font-medium">
            Listen Mode (Act as Relay Server)
        </label>
    </div>

    {#if !listenMode}
        <div class="space-y-4">
            <div>
                <label for="backbone-target-host" class="glass-label block font-medium mb-1">Target Host</label>
                <input
                    id="backbone-target-host"
                    value={targetHost ?? ""}
                    type="text"
                    placeholder="e.g. 1.2.3.4 or example.com"
                    class="input-field"
                    oninput={(e) => ontargethostchange?.((e.target as HTMLInputElement).value)}
                />
            </div>
            <div>
                <label for="backbone-target-port" class="glass-label block font-medium mb-1">Target Port</label>
                <input
                    id="backbone-target-port"
                    value={targetPort ?? ""}
                    type="number"
                    placeholder="4242"
                    class="input-field"
                    oninput={(e) => ontargetportchange?.((e.target as HTMLInputElement).value)}
                />
            </div>
            <div>
                <label for="backbone-transport-id" class="glass-label block font-medium mb-1"
                    >Transport Identity (optional)</label
                >
                <input
                    id="backbone-transport-id"
                    value={transportIdentity ?? ""}
                    type="text"
                    placeholder="32 hex characters"
                    class="input-field font-mono text-xs"
                    oninput={(e) => ontransportidentitychange?.((e.target as HTMLInputElement).value)}
                />
            </div>
            <div class="flex items-start gap-2">
                <Toggle
                    id="backbone-bootstrap-only"
                    checked={bootstrapOnly}
                    onchange={(val) => onbootstraponlychange?.(val)}
                />
                <div class="min-w-0">
                    <label for="backbone-bootstrap-only" class="cursor-pointer mb-0! text-sm block">
                        {t("interfaces.discovery_default_bootstrap_only")}
                    </label>
                    <BundledDocsHint paragraphClass="text-xs text-sem-fg-muted mt-0.5" />
                </div>
            </div>
        </div>
    {:else}
        <div class="space-y-4">
            <div>
                <label for="backbone-listen-ip" class="glass-label block font-medium mb-1">Listen IP</label>
                <input
                    id="backbone-listen-ip"
                    value={listenIp ?? ""}
                    type="text"
                    placeholder="0.0.0.0 (all interfaces)"
                    class="input-field"
                    oninput={(e) => onlistenipchange?.((e.target as HTMLInputElement).value)}
                />
            </div>
            <div>
                <label for="backbone-listen-port" class="glass-label block font-medium mb-1">Listen Port</label>
                <input
                    id="backbone-listen-port"
                    value={listenPort ?? ""}
                    type="number"
                    placeholder="4242"
                    class="input-field"
                    oninput={(e) => onlistenportchange?.((e.target as HTMLInputElement).value)}
                />
            </div>
            <div>
                <label for="backbone-listen-device" class="glass-label block font-medium mb-1"
                    >Listen Device (optional)</label
                >
                <input
                    id="backbone-listen-device"
                    value={listenDevice ?? ""}
                    type="text"
                    placeholder="e.g. eth0"
                    class="input-field"
                    oninput={(e) => onlistendevicechange?.((e.target as HTMLInputElement).value)}
                />
                <div class="mt-2 text-xs text-sem-fg-muted">
                    {#if hostKernelInterfacesLoading}
                        <span class="text-xs text-gray-400">Loading interfaces...</span>
                    {:else if hostKernelInterfaces.length > 0}
                        <div class="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto">
                            {#each hostKernelInterfaces as k (k.name)}
                                <button
                                    type="button"
                                    class="secondary-chip py-0.5! px-2! text-[10px]!"
                                    onclick={() => onlistendevicechange?.(k.name)}
                                >
                                    {k.name}
                                </button>
                            {/each}
                        </div>
                    {/if}
                </div>
            </div>
            <div class="flex items-center gap-2">
                <Toggle
                    id="backbone-flapping-toggle"
                    checked={blockFastFlapping}
                    onchange={(val) => onblockfastflappingchange?.(val)}
                />
                <label for="backbone-flapping-toggle" class="cursor-pointer mb-0! text-sm font-medium">
                    Block Fast Flapping
                </label>
            </div>
            {#if blockFastFlapping}
                <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div>
                        <label for="bb-flap-block" class="glass-label block font-medium mb-1">Block Time (s)</label>
                        <input
                            id="bb-flap-block"
                            value={fastFlappingBlockTime ?? ""}
                            type="number"
                            class="input-field"
                            oninput={(e) => onfastflappingblocktimechange?.((e.target as HTMLInputElement).value)}
                        />
                    </div>
                    <div>
                        <label for="bb-flap-thresh" class="glass-label block font-medium mb-1">Threshold</label>
                        <input
                            id="bb-flap-thresh"
                            value={fastFlappingThreshold ?? ""}
                            type="number"
                            class="input-field"
                            oninput={(e) => onfastflappingthresholdchange?.((e.target as HTMLInputElement).value)}
                        />
                    </div>
                    <div>
                        <label for="bb-flap-grace" class="glass-label block font-medium mb-1">Grace Period (s)</label>
                        <input
                            id="bb-flap-grace"
                            value={fastFlappingGrace ?? ""}
                            type="number"
                            class="input-field"
                            oninput={(e) => onfastflappinggracechange?.((e.target as HTMLInputElement).value)}
                        />
                    </div>
                </div>
            {/if}
        </div>
    {/if}

    <div class="grid grid-cols-3 gap-3 pt-2">
        <div>
            <label for="bb-connect-timeout" class="glass-label block font-medium mb-1">Connect Timeout</label>
            <input
                id="bb-connect-timeout"
                value={connectTimeout ?? ""}
                type="number"
                min="0"
                placeholder="default"
                class="input-field"
                oninput={(e) => onconnecttimeoutchange?.((e.target as HTMLInputElement).value)}
            />
        </div>
        <div>
            <label for="bb-max-reconnect" class="glass-label block font-medium mb-1">Max Reconnect</label>
            <input
                id="bb-max-reconnect"
                value={maxReconnectTries ?? ""}
                type="number"
                min="0"
                placeholder="default"
                class="input-field"
                oninput={(e) => onmaxreconnecttrieschange?.((e.target as HTMLInputElement).value)}
            />
        </div>
        <div>
            <label for="bb-fixed-mtu" class="glass-label block font-medium mb-1">Fixed MTU</label>
            <input
                id="bb-fixed-mtu"
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
