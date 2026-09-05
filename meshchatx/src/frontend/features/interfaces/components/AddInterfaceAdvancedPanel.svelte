<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import ExpandingSection from "./ExpandingSection.svelte";
    import Toggle from "./Toggle.svelte";
    import BundledDocsHint from "./BundledDocsHint.svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import type { SharedInterfaceSettings, RNodeLoRaParameters, ReticulumDiscovery } from "../lib/types.js";

    interface Props {
        interfaceType: string | null;
        sharedSettings: SharedInterfaceSettings;
        loraParams: RNodeLoRaParameters;
        reticulumDiscovery: ReticulumDiscovery;
        savingDiscovery?: boolean;
        onpatchshared?: (patch: Partial<SharedInterfaceSettings>) => void;
        onpatchlora?: (patch: Partial<RNodeLoRaParameters>) => void;
        onpatchdiscovery?: (patch: Partial<ReticulumDiscovery>) => void;
        onsavediscovery?: () => void;
    }

    let {
        interfaceType,
        sharedSettings,
        loraParams,
        reticulumDiscovery,
        savingDiscovery = false,
        onpatchshared,
        onpatchlora,
        onpatchdiscovery,
        onsavediscovery,
    }: Props = $props();
</script>

<div class="space-y-4 pt-4">
    <!-- RNode LoRa Calculated Parameters -->
    {#if interfaceType && ["RNodeInterface", "RNodeIPInterface"].includes(interfaceType)}
        <ExpandingSection class="glass-card p-0! overflow-hidden">
            {#snippet title()}
                <span class="text-sm font-bold">Calculated LoRa Parameters</span>
            {/snippet}
            {#snippet content()}
                <div class="p-6 space-y-6">
                    <div>
                        <label for="adv-antenna-gain" class="glass-label block font-medium mb-1"
                            >Antenna Gain (dBi)</label
                        >
                        <input
                            id="adv-antenna-gain"
                            value={loraParams.antennaGain ?? 0}
                            type="number"
                            class="input-field"
                            oninput={(e) =>
                                onpatchlora?.({ antennaGain: Number((e.target as HTMLInputElement).value) })}
                        />
                    </div>
                    <div class="grid grid-cols-3 gap-3">
                        <div class="bg-blue-500/5 p-3 rounded-2xl border border-blue-500/10 text-center">
                            <div class="text-[10px] uppercase font-bold text-blue-500 mb-1">Sensitivity</div>
                            <div class="text-lg font-mono font-bold">{loraParams.sensitivity ?? "—"}</div>
                        </div>
                        <div class="bg-blue-500/5 p-3 rounded-2xl border border-blue-500/10 text-center">
                            <div class="text-[10px] uppercase font-bold text-blue-500 mb-1">Data Rate</div>
                            <div class="text-lg font-mono font-bold">{loraParams.dataRate ?? "—"}</div>
                        </div>
                        <div class="bg-blue-500/5 p-3 rounded-2xl border border-blue-500/10 text-center">
                            <div class="text-[10px] uppercase font-bold text-blue-500 mb-1">Link Budget</div>
                            <div class="text-lg font-mono font-bold">{loraParams.linkBudget ?? "—"}</div>
                        </div>
                    </div>
                </div>
            {/snippet}
        </ExpandingSection>
    {/if}

    <!-- Discovery Listener (Peer) -->
    <ExpandingSection class="glass-card p-0! overflow-hidden">
        {#snippet title()}
            <span class="text-sm font-bold">Discovery Listener (Peer)</span>
        {/snippet}
        {#snippet content()}
            <div class="p-6 space-y-6">
                <div class="flex items-center justify-between">
                    <div class="max-w-md">
                        <label for="adv-disc-listener-toggle" class="glass-label mb-0! block font-medium"
                            >Enable Discovery Listener</label
                        >
                        <p class="text-xs text-gray-400">
                            Listen for announced interfaces and optionally auto-connect.
                        </p>
                    </div>
                    <Toggle
                        id="adv-disc-listener-toggle"
                        checked={reticulumDiscovery.discover_interfaces}
                        onchange={(val) => onpatchdiscovery?.({ discover_interfaces: val })}
                    />
                </div>
                <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between pt-2">
                    <div class="max-w-xl min-w-0">
                        <label for="adv-disc-bootstrap-toggle" class="glass-label mb-0! text-sm block font-medium">
                            {t("interfaces.discovery_default_bootstrap_only")}
                        </label>
                        <BundledDocsHint paragraphClass="text-xs text-gray-400" />
                    </div>
                    <Toggle
                        id="adv-disc-bootstrap-toggle"
                        checked={reticulumDiscovery.default_bootstrap_only}
                        onchange={(val) => onpatchdiscovery?.({ default_bootstrap_only: val })}
                    />
                </div>
                {#if reticulumDiscovery.discover_interfaces}
                    <div class="space-y-4 pt-4 border-t border-sem-border animate-in fade-in slide-in-from-top-2">
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label for="adv-disc-whitelist" class="glass-label block font-medium mb-1"
                                    >Whitelist (names, hosts, IDs)</label
                                >
                                <input
                                    id="adv-disc-whitelist"
                                    value={reticulumDiscovery.interface_discovery_whitelist || ""}
                                    type="text"
                                    placeholder="Whitelist"
                                    class="input-field"
                                    oninput={(e) =>
                                        onpatchdiscovery?.({
                                            interface_discovery_whitelist: (e.target as HTMLInputElement).value,
                                        })}
                                />
                            </div>
                            <div>
                                <label for="adv-disc-blacklist" class="glass-label block font-medium mb-1"
                                    >Blacklist (names, hosts, IDs)</label
                                >
                                <input
                                    id="adv-disc-blacklist"
                                    value={reticulumDiscovery.interface_discovery_blacklist || ""}
                                    type="text"
                                    placeholder="Blacklist"
                                    class="input-field"
                                    oninput={(e) =>
                                        onpatchdiscovery?.({
                                            interface_discovery_blacklist: (e.target as HTMLInputElement).value,
                                        })}
                                />
                            </div>
                        </div>
                        <div class="flex justify-end">
                            <button
                                type="button"
                                class="primary-chip text-[10px]!"
                                disabled={savingDiscovery}
                                onclick={onsavediscovery}
                            >
                                <MaterialDesignIcon iconName="content-save" class="w-3 h-3" />
                                <span>Save Listener Prefs</span>
                            </button>
                        </div>
                    </div>
                {/if}
            </div>
        {/snippet}
    </ExpandingSection>

    <!-- Shared Advanced Settings (Mode, Bitrate, IFAC) -->
    <ExpandingSection class="glass-card p-0! overflow-hidden">
        {#snippet title()}
            <span class="text-sm font-bold">Advanced Parameters (IFAC, Mode)</span>
        {/snippet}
        {#snippet content()}
            <div class="p-6 space-y-6">
                <div class="grid grid-cols-2 gap-4">
                    {#if interfaceType !== "HTTPInterface"}
                        <div>
                            <label for="adv-iface-mode" class="glass-label block font-medium mb-1">Interface Mode</label
                            >
                            <select
                                id="adv-iface-mode"
                                value={sharedSettings.mode || ""}
                                class="input-field"
                                onchange={(e) =>
                                    onpatchshared?.({ mode: (e.target as HTMLSelectElement).value || null })}
                            >
                                <option value="">{t("interfaces.mode_default_full")}</option>
                                <option value="full">{t("interfaces.mode_full")}</option>
                                <option value="gateway">{t("interfaces.mode_gateway")}</option>
                                <option value="access_point">{t("interfaces.mode_access_point")}</option>
                                <option value="roaming">{t("interfaces.mode_roaming")}</option>
                                <option value="boundary">{t("interfaces.mode_boundary")}</option>
                                <option value="internal">{t("interfaces.mode_internal")}</option>
                            </select>
                        </div>
                    {:else}
                        <div class="col-span-2">
                            <p class="text-xs text-sem-fg-muted">{t("interfaces.http_tunnel_mode_note")}</p>
                        </div>
                    {/if}
                    <div>
                        <label for="adv-forced-bitrate" class="glass-label block font-medium mb-1">Forced Bitrate</label
                        >
                        <input
                            id="adv-forced-bitrate"
                            value={sharedSettings.bitrate ?? ""}
                            type="number"
                            placeholder="bps"
                            class="input-field"
                            oninput={(e) =>
                                onpatchshared?.({ bitrate: Number((e.target as HTMLInputElement).value) || null })}
                        />
                    </div>
                </div>

                <div class="space-y-4 pt-2">
                    <div class="flex items-start justify-between gap-4">
                        <div class="min-w-0 max-w-md">
                            <label for="adv-rec-prs" class="glass-label mb-0! block font-medium"
                                >{t("interfaces.recursive_prs_label")}</label
                            >
                            <p class="text-xs text-gray-400 mt-1">{t("interfaces.recursive_prs_hint")}</p>
                        </div>
                        <Toggle
                            id="adv-rec-prs"
                            checked={Boolean(sharedSettings.recursive_prs)}
                            onchange={(val) => onpatchshared?.({ recursive_prs: val })}
                        />
                    </div>
                    <div class="flex items-start justify-between gap-4">
                        <div class="min-w-0 max-w-md">
                            <label for="adv-ann-from-int" class="glass-label mb-0! block font-medium"
                                >{t("interfaces.announces_from_internal_label")}</label
                            >
                            <p class="text-xs text-gray-400 mt-1">{t("interfaces.announces_from_internal_hint")}</p>
                        </div>
                        <Toggle
                            id="adv-ann-from-int"
                            checked={Boolean(sharedSettings.announces_from_internal)}
                            onchange={(val) => onpatchshared?.({ announces_from_internal: val })}
                        />
                    </div>
                    <div class="flex items-start justify-between gap-4">
                        <div class="min-w-0 max-w-md">
                            <label for="adv-ann-to-int" class="glass-label mb-0! block font-medium"
                                >{t("interfaces.announces_to_internal_label")}</label
                            >
                            <p class="text-xs text-gray-400 mt-1">{t("interfaces.announces_to_internal_hint")}</p>
                        </div>
                        <Toggle
                            id="adv-ann-to-int"
                            checked={Boolean(sharedSettings.announces_to_internal)}
                            onchange={(val) => onpatchshared?.({ announces_to_internal: val })}
                        />
                    </div>
                    <div>
                        <label for="adv-gravity" class="glass-label block font-medium mb-1"
                            >{t("interfaces.gravity_label")}</label
                        >
                        <input
                            id="adv-gravity"
                            value={sharedSettings.gravity ?? ""}
                            type="number"
                            placeholder={t("interfaces.gravity_placeholder")}
                            class="input-field"
                            oninput={(e) =>
                                onpatchshared?.({ gravity: Number((e.target as HTMLInputElement).value) || null })}
                        />
                        <p class="text-xs text-gray-400 mt-1">{t("interfaces.gravity_hint")}</p>
                    </div>
                </div>

                <div class="space-y-4 pt-4 border-t border-sem-border">
                    <label for="adv-net-name" class="glass-label block font-medium mb-1"
                        >Interface Access Code (IFAC)</label
                    >
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <input
                            id="adv-net-name"
                            value={sharedSettings.network_name || ""}
                            type="text"
                            placeholder="Network Name"
                            class="input-field"
                            oninput={(e) =>
                                onpatchshared?.({ network_name: (e.target as HTMLInputElement).value || null })}
                        />
                        <input
                            id="adv-passphrase"
                            value={sharedSettings.passphrase || ""}
                            type="text"
                            placeholder="Passphrase"
                            class="input-field"
                            oninput={(e) =>
                                onpatchshared?.({ passphrase: (e.target as HTMLInputElement).value || null })}
                        />
                    </div>
                </div>
            </div>
        {/snippet}
    </ExpandingSection>
</div>
