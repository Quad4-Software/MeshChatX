<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import ExpandingSection from "./ExpandingSection.svelte";
    import Toggle from "./Toggle.svelte";
    import { t } from "../../../js/i18n.js";
    import type { DiscoveryFields } from "../lib/types.js";

    interface Props {
        discovery: DiscoveryFields;
        onpatch?: (patch: Partial<DiscoveryFields>) => void;
    }

    let { discovery, onpatch }: Props = $props();

    function patchField<K extends keyof DiscoveryFields>(key: K, value: DiscoveryFields[K]) {
        onpatch?.({ [key]: value });
    }
</script>

<ExpandingSection class="glass-card p-0! overflow-hidden">
    {#snippet title()}
        <span class="text-sm font-bold">Interface Discovery</span>
    {/snippet}
    {#snippet content()}
        <div class="p-6 space-y-6">
            <div class="flex items-center justify-between">
                <div class="max-w-md">
                    <label class="glass-label mb-0! block font-medium" for="publish-discovery-toggle">
                        Publish Discovery Announce
                    </label>
                    <p class="text-xs text-gray-400">Makes your node visible to others on the network.</p>
                </div>
                <Toggle
                    id="publish-discovery-toggle"
                    checked={Boolean(discovery.discoverable)}
                    onchange={(val) => patchField("discoverable", val)}
                />
            </div>
            {#if discovery.discoverable}
                <div class="space-y-4 pt-4 border-t border-sem-border animate-in fade-in slide-in-from-top-2">
                    <div>
                        <label class="glass-label block font-medium mb-1" for="discovery-name-input">
                            Discovery Name
                        </label>
                        <input
                            id="discovery-name-input"
                            value={discovery.discovery_name || ""}
                            type="text"
                            placeholder="Human-friendly name"
                            class="input-field"
                            oninput={(e) => patchField("discovery_name", (e.target as HTMLInputElement).value)}
                        />
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="glass-label block font-medium mb-1" for="discovery-interval-input">
                                Announce Interval (m)
                            </label>
                            <input
                                id="discovery-interval-input"
                                value={discovery.announce_interval ?? ""}
                                type="number"
                                class="input-field"
                                oninput={(e) =>
                                    patchField("announce_interval", Number((e.target as HTMLInputElement).value))}
                            />
                        </div>
                        <div>
                            <label class="glass-label block font-medium mb-1" for="discovery-reachable-input">
                                Reachable On
                            </label>
                            <input
                                id="discovery-reachable-input"
                                value={discovery.reachable_on || ""}
                                type="text"
                                placeholder="IP or Hostname"
                                class="input-field"
                                oninput={(e) => patchField("reachable_on", (e.target as HTMLInputElement).value)}
                            />
                        </div>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                            <label class="glass-label block font-medium mb-1" for="discovery-lat-input">
                                Latitude (optional)
                            </label>
                            <input
                                id="discovery-lat-input"
                                value={discovery.latitude || ""}
                                type="text"
                                inputmode="decimal"
                                autocomplete="off"
                                aria-required="false"
                                placeholder="Leave blank if unknown"
                                class="input-field"
                                oninput={(e) => patchField("latitude", (e.target as HTMLInputElement).value)}
                            />
                        </div>
                        <div>
                            <label class="glass-label block font-medium mb-1" for="discovery-lon-input">
                                Longitude (optional)
                            </label>
                            <input
                                id="discovery-lon-input"
                                value={discovery.longitude || ""}
                                type="text"
                                inputmode="decimal"
                                autocomplete="off"
                                aria-required="false"
                                placeholder="Leave blank if unknown"
                                class="input-field"
                                oninput={(e) => patchField("longitude", (e.target as HTMLInputElement).value)}
                            />
                        </div>
                        <div>
                            <label class="glass-label block font-medium mb-1" for="discovery-height-input">
                                Height in metres (optional)
                            </label>
                            <input
                                id="discovery-height-input"
                                value={discovery.height || ""}
                                type="text"
                                inputmode="decimal"
                                autocomplete="off"
                                aria-required="false"
                                placeholder="Leave blank if unknown"
                                class="input-field"
                                oninput={(e) => patchField("height", (e.target as HTMLInputElement).value)}
                            />
                        </div>
                    </div>
                    <div>
                        <label class="glass-label block font-medium mb-1" for="discovery-location-cmd">
                            {t("interfaces.location_cmd_label")}
                        </label>
                        <input
                            id="discovery-location-cmd"
                            value={discovery.location_cmd || ""}
                            type="text"
                            placeholder={t("interfaces.location_cmd_placeholder")}
                            class="input-field font-mono text-xs"
                            autocomplete="off"
                            oninput={(e) => patchField("location_cmd", (e.target as HTMLInputElement).value)}
                        />
                        <p class="text-xs text-sem-fg-muted mt-1">
                            {t("interfaces.location_cmd_hint")}
                        </p>
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="glass-label block font-medium mb-1" for="discovery-stamp-value">
                                Discovery stamp value
                            </label>
                            <input
                                id="discovery-stamp-value"
                                value={discovery.discovery_stamp_value ?? 1}
                                type="number"
                                min="1"
                                class="input-field"
                                oninput={(e) =>
                                    patchField("discovery_stamp_value", Number((e.target as HTMLInputElement).value))}
                            />
                        </div>
                    </div>
                    <div class="flex flex-wrap items-center justify-between gap-4">
                        <div class="flex items-center justify-between gap-4 max-w-md">
                            <label class="glass-label mb-0! block font-medium" for="discovery-encrypt-toggle">
                                Encrypt discovery
                            </label>
                            <Toggle
                                id="discovery-encrypt-toggle"
                                checked={Boolean(discovery.discovery_encrypt)}
                                onchange={(val) => patchField("discovery_encrypt", val)}
                            />
                        </div>
                        <div class="flex items-center justify-between gap-4 max-w-md">
                            <label class="glass-label mb-0! block font-medium" for="discovery-publish-ifac-toggle">
                                Publish IFAC in announce
                            </label>
                            <Toggle
                                id="discovery-publish-ifac-toggle"
                                checked={Boolean(discovery.publish_ifac)}
                                onchange={(val) => patchField("publish_ifac", val)}
                            />
                        </div>
                    </div>
                </div>
            {/if}
        </div>
    {/snippet}
</ExpandingSection>
