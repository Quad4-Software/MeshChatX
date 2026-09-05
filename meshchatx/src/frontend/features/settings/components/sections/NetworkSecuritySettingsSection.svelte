<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "../Toggle.svelte";
    import { t } from "../../../../js/i18n.js";

    interface Props {
        visible?: boolean;
        config?: Record<string, any>;
        onupdatefield?: (data: { key: string; value: any }) => void;
        onannouncelimitschange?: () => void;
    }

    let { visible = true, config = {}, onupdatefield, onannouncelimitschange }: Props = $props();

    function emitToggle(key: string, value: boolean) {
        onupdatefield?.({ key, value });
    }

    function emitNumber(key: string, value: string) {
        const num = Number(value);
        if (!Number.isNaN(num)) {
            onupdatefield?.({ key, value: num });
            onannouncelimitschange?.();
        }
    }
</script>

{#if visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">RNS Security</div>
                <h2>Network Security</h2>
                <p>Manage mesh-level security features.</p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <label class="setting-toggle">
                <Toggle
                    id="blackhole-integration-enabled"
                    checked={Boolean(config.blackhole_integration_enabled)}
                    onchange={(val) => emitToggle("blackhole_integration_enabled", val)}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("app.blackhole_integration_enabled")}</span>
                    <span class="setting-toggle__description">{t("app.blackhole_integration_description")}</span>
                </span>
            </label>

            <div class="space-y-4">
                <div class="text-sm font-medium text-sem-fg">
                    {t("app.announce_limits")}
                </div>
                <div class="text-xs text-sem-fg-muted">
                    {t("app.announce_limits_description")}
                </div>
                <div class="text-xs font-medium text-sem-fg">
                    {t("app.announce_store_heading")}
                </div>
                <div class="text-xs text-sem-fg-muted">
                    {t("app.announce_store_description")}
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <label class="setting-toggle">
                        <Toggle
                            id="announce-store-lxmf"
                            checked={Boolean(config.announce_store_lxmf_delivery)}
                            onchange={(val) => emitToggle("announce_store_lxmf_delivery", val)}
                        />
                        <span class="setting-toggle__label">
                            <span class="setting-toggle__title">{t("app.announce_store_lxmf")}</span>
                        </span>
                    </label>
                    <label class="setting-toggle">
                        <Toggle
                            id="announce-store-lxst"
                            checked={Boolean(config.announce_store_lxst_telephony)}
                            onchange={(val) => emitToggle("announce_store_lxst_telephony", val)}
                        />
                        <span class="setting-toggle__label">
                            <span class="setting-toggle__title">{t("app.announce_store_lxst")}</span>
                        </span>
                    </label>
                    <label class="setting-toggle">
                        <Toggle
                            id="announce-store-nomad"
                            checked={Boolean(config.announce_store_nomadnetwork_node)}
                            onchange={(val) => emitToggle("announce_store_nomadnetwork_node", val)}
                        />
                        <span class="setting-toggle__label">
                            <span class="setting-toggle__title">{t("app.announce_store_nomad")}</span>
                        </span>
                    </label>
                    <label class="setting-toggle">
                        <Toggle
                            id="announce-store-prop"
                            checked={Boolean(config.announce_store_lxmf_propagation)}
                            onchange={(val) => emitToggle("announce_store_lxmf_propagation", val)}
                        />
                        <span class="setting-toggle__label">
                            <span class="setting-toggle__title">{t("app.announce_store_prop")}</span>
                        </span>
                    </label>
                    <label class="setting-toggle">
                        <Toggle
                            id="announce-store-map"
                            checked={Boolean(config.announce_store_map_data)}
                            onchange={(val) => emitToggle("announce_store_map_data", val)}
                        />
                        <span class="setting-toggle__label">
                            <span class="setting-toggle__title">{t("app.announce_store_map_data")}</span>
                        </span>
                    </label>
                </div>
                <div class="text-xs font-semibold text-sem-fg-muted uppercase tracking-wide">
                    {t("app.announce_max_stored_heading")}
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div class="space-y-1">
                        <label for="ann-max-lxmf" class="text-xs font-medium block"
                            >{t("app.announce_limit_lxmf")}</label
                        >
                        <input
                            id="ann-max-lxmf"
                            value={config.announce_max_stored_lxmf_delivery}
                            type="number"
                            min="1"
                            class="input-field"
                            onchange={(e) =>
                                emitNumber("announce_max_stored_lxmf_delivery", (e.target as HTMLInputElement).value)}
                        />
                    </div>
                    <div class="space-y-1">
                        <label for="ann-max-nomad" class="text-xs font-medium block"
                            >{t("app.announce_limit_nomadnet")}</label
                        >
                        <input
                            id="ann-max-nomad"
                            value={config.announce_max_stored_nomadnetwork_node}
                            type="number"
                            min="1"
                            class="input-field"
                            onchange={(e) =>
                                emitNumber(
                                    "announce_max_stored_nomadnetwork_node",
                                    (e.target as HTMLInputElement).value
                                )}
                        />
                    </div>
                    <div class="space-y-1">
                        <label for="ann-max-prop" class="text-xs font-medium block"
                            >{t("app.announce_limit_prop")}</label
                        >
                        <input
                            id="ann-max-prop"
                            value={config.announce_max_stored_lxmf_propagation}
                            type="number"
                            min="1"
                            class="input-field"
                            onchange={(e) =>
                                emitNumber(
                                    "announce_max_stored_lxmf_propagation",
                                    (e.target as HTMLInputElement).value
                                )}
                        />
                    </div>
                    <div class="space-y-1">
                        <label for="ann-max-map" class="text-xs font-medium block"
                            >{t("app.announce_limit_map_data")}</label
                        >
                        <input
                            id="ann-max-map"
                            value={config.announce_max_stored_map_data}
                            type="number"
                            min="1"
                            class="input-field"
                            onchange={(e) =>
                                emitNumber("announce_max_stored_map_data", (e.target as HTMLInputElement).value)}
                        />
                    </div>
                </div>
                <div class="text-xs font-semibold text-sem-fg-muted uppercase tracking-wide">
                    {t("app.announce_fetch_limit_heading")}
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div class="space-y-1">
                        <label for="ann-fetch-lxmf" class="text-xs font-medium block"
                            >{t("app.announce_limit_lxmf")}</label
                        >
                        <input
                            id="ann-fetch-lxmf"
                            value={config.announce_fetch_limit_lxmf_delivery}
                            type="number"
                            min="1"
                            class="input-field"
                            onchange={(e) =>
                                emitNumber("announce_fetch_limit_lxmf_delivery", (e.target as HTMLInputElement).value)}
                        />
                    </div>
                    <div class="space-y-1">
                        <label for="ann-fetch-nomad" class="text-xs font-medium block"
                            >{t("app.announce_limit_nomadnet")}</label
                        >
                        <input
                            id="ann-fetch-nomad"
                            value={config.announce_fetch_limit_nomadnetwork_node}
                            type="number"
                            min="1"
                            class="input-field"
                            onchange={(e) =>
                                emitNumber(
                                    "announce_fetch_limit_nomadnetwork_node",
                                    (e.target as HTMLInputElement).value
                                )}
                        />
                    </div>
                    <div class="space-y-1">
                        <label for="ann-fetch-prop" class="text-xs font-medium block"
                            >{t("app.announce_limit_prop")}</label
                        >
                        <input
                            id="ann-fetch-prop"
                            value={config.announce_fetch_limit_lxmf_propagation}
                            type="number"
                            min="1"
                            class="input-field"
                            onchange={(e) =>
                                emitNumber(
                                    "announce_fetch_limit_lxmf_propagation",
                                    (e.target as HTMLInputElement).value
                                )}
                        />
                    </div>
                    <div class="space-y-1">
                        <label for="ann-fetch-map" class="text-xs font-medium block"
                            >{t("app.announce_limit_map_data")}</label
                        >
                        <input
                            id="ann-fetch-map"
                            value={config.announce_fetch_limit_map_data}
                            type="number"
                            min="1"
                            class="input-field"
                            onchange={(e) =>
                                emitNumber("announce_fetch_limit_map_data", (e.target as HTMLInputElement).value)}
                        />
                    </div>
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div class="space-y-1">
                        <label for="ann-search-max" class="text-xs font-medium block"
                            >{t("app.announce_search_max_fetch")}</label
                        >
                        <input
                            id="ann-search-max"
                            value={config.announce_search_max_fetch}
                            type="number"
                            min="100"
                            class="input-field"
                            onchange={(e) =>
                                emitNumber("announce_search_max_fetch", (e.target as HTMLInputElement).value)}
                        />
                        <p class="text-[10px] text-sem-fg-muted">
                            {t("app.announce_search_max_fetch_hint")}
                        </p>
                    </div>
                    <div class="space-y-1">
                        <label for="disc-ifaces-max" class="text-xs font-medium block"
                            >{t("app.discovered_interfaces_max_return")}</label
                        >
                        <input
                            id="disc-ifaces-max"
                            value={config.discovered_interfaces_max_return}
                            type="number"
                            min="1"
                            class="input-field"
                            onchange={(e) =>
                                emitNumber("discovered_interfaces_max_return", (e.target as HTMLInputElement).value)}
                        />
                        <p class="text-[10px] text-sem-fg-muted">
                            {t("app.discovered_interfaces_max_return_hint")}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </section>
{/if}
