<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "../Toggle.svelte";
    import { t } from "../../../../js/i18n.js";

    interface Props {
        visible?: boolean;
        batterySaver?: {
            enabled?: boolean;
            disableVisualiserDiscovery?: boolean;
            hideOfflineInterfaces?: boolean;
            maxVisualiserInterfaces?: number;
            visualiserReloadSeconds?: number;
            disableVisualiserLiveLayout?: boolean;
            reduceBackgroundPolling?: boolean;
            backgroundPollMultiplier?: number;
            reduceInterfacesDiscovery?: boolean;
            interfacesStatsPollSeconds?: number;
            interfacesDiscoveryPollSeconds?: number;
            applyInterfaceBitrateLimits?: boolean;
            interfaceBitrateLimits?: Record<string, number>;
            [k: string]: any;
        };
        batteryInterfaceRows?: Array<{ name: string; type?: string }>;
        batteryBitrateBusy?: boolean;
        onenabledchange?: (val: boolean) => void;
        onpatch?: (patch: Record<string, any>) => void;
        onapplybitrates?: () => void;
        onrestorebitrates?: () => void;
    }

    let {
        visible = true,
        batterySaver = {},
        batteryInterfaceRows = [],
        batteryBitrateBusy = false,
        onenabledchange,
        onpatch,
        onapplybitrates,
        onrestorebitrates,
    }: Props = $props();

    function onBitrateInput(name: string, raw: string) {
        const limits = { ...(batterySaver?.interfaceBitrateLimits || {}) };
        if (raw === "" || raw == null || Number.isNaN(Number(raw))) {
            delete limits[name];
        } else {
            limits[name] = Math.max(0, Math.round(Number(raw)));
        }
        onpatch?.({ interfaceBitrateLimits: limits });
    }
</script>

{#if visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">{t("settings.battery.eyebrow")}</div>
                <h2>{t("settings.battery.title")}</h2>
                <p>{t("settings.battery.description")}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <label class="setting-toggle">
                <Toggle
                    id="settings-battery-saver-enabled"
                    checked={Boolean(batterySaver.enabled)}
                    onchange={onenabledchange}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("settings.battery.enabled")}</span>
                    <span class="setting-toggle__description">{t("settings.battery.enabled_desc")}</span>
                </span>
            </label>

            <div class="text-sm font-medium text-sem-fg pt-2">
                {t("settings.battery.options_heading")}
            </div>

            <label class="setting-toggle">
                <Toggle
                    id="settings-battery-viz-discovery"
                    checked={Boolean(batterySaver.disableVisualiserDiscovery)}
                    onchange={(val) => onpatch?.({ disableVisualiserDiscovery: val })}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("settings.battery.disable_visualiser_discovery")}</span>
                    <span class="setting-toggle__description"
                        >{t("settings.battery.disable_visualiser_discovery_desc")}</span
                    >
                </span>
            </label>

            <label class="setting-toggle">
                <Toggle
                    id="settings-battery-hide-offline"
                    checked={Boolean(batterySaver.hideOfflineInterfaces)}
                    onchange={(val) => onpatch?.({ hideOfflineInterfaces: val })}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("settings.battery.hide_offline_interfaces")}</span>
                    <span class="setting-toggle__description">{t("settings.battery.hide_offline_interfaces_desc")}</span
                    >
                </span>
            </label>

            <div class="space-y-2">
                <label for="battery-max-viz-ifaces" class="text-sm font-medium text-sem-fg block">
                    {t("settings.battery.max_visualiser_interfaces")}
                </label>
                <p class="text-xs text-sem-fg-muted">
                    {t("settings.battery.max_visualiser_interfaces_desc")}
                </p>
                <input
                    id="battery-max-viz-ifaces"
                    value={batterySaver.maxVisualiserInterfaces}
                    type="number"
                    min="0"
                    max="128"
                    class="input-field"
                    onchange={(e) =>
                        onpatch?.({
                            maxVisualiserInterfaces: Number((e.target as HTMLInputElement).value),
                        })}
                />
            </div>

            <div class="space-y-2">
                <label for="battery-viz-reload-sec" class="text-sm font-medium text-sem-fg block">
                    {t("settings.battery.visualiser_reload_seconds")}
                </label>
                <p class="text-xs text-sem-fg-muted">
                    {t("settings.battery.visualiser_reload_seconds_desc")}
                </p>
                <input
                    id="battery-viz-reload-sec"
                    value={batterySaver.visualiserReloadSeconds}
                    type="number"
                    min="0"
                    max="600"
                    class="input-field"
                    onchange={(e) =>
                        onpatch?.({
                            visualiserReloadSeconds: Number((e.target as HTMLInputElement).value),
                        })}
                />
            </div>

            <label class="setting-toggle">
                <Toggle
                    id="settings-battery-live-layout"
                    checked={Boolean(batterySaver.disableVisualiserLiveLayout)}
                    onchange={(val) => onpatch?.({ disableVisualiserLiveLayout: val })}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("settings.battery.disable_visualiser_live_layout")}</span>
                    <span class="setting-toggle__description"
                        >{t("settings.battery.disable_visualiser_live_layout_desc")}</span
                    >
                </span>
            </label>

            <label class="setting-toggle">
                <Toggle
                    id="settings-battery-bg-poll"
                    checked={Boolean(batterySaver.reduceBackgroundPolling)}
                    onchange={(val) => onpatch?.({ reduceBackgroundPolling: val })}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("settings.battery.reduce_background_polling")}</span>
                    <span class="setting-toggle__description"
                        >{t("settings.battery.reduce_background_polling_desc")}</span
                    >
                </span>
            </label>

            <div class="space-y-2">
                <label for="battery-bg-poll-mult" class="text-sm font-medium text-sem-fg block">
                    {t("settings.battery.background_poll_multiplier")}
                </label>
                <p class="text-xs text-sem-fg-muted">
                    {t("settings.battery.background_poll_multiplier_desc")}
                </p>
                <input
                    id="battery-bg-poll-mult"
                    value={batterySaver.backgroundPollMultiplier}
                    type="number"
                    min="2"
                    max="10"
                    class="input-field"
                    onchange={(e) =>
                        onpatch?.({
                            backgroundPollMultiplier: Number((e.target as HTMLInputElement).value),
                        })}
                />
            </div>

            <label class="setting-toggle">
                <Toggle
                    id="settings-battery-ifaces-discovery"
                    checked={Boolean(batterySaver.reduceInterfacesDiscovery)}
                    onchange={(val) => onpatch?.({ reduceInterfacesDiscovery: val })}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("settings.battery.reduce_interfaces_discovery")}</span>
                    <span class="setting-toggle__description"
                        >{t("settings.battery.reduce_interfaces_discovery_desc")}</span
                    >
                </span>
            </label>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div class="space-y-2">
                    <label for="battery-iface-stats-poll" class="text-sm font-medium text-sem-fg block">
                        {t("settings.battery.interfaces_stats_poll_seconds")}
                    </label>
                    <input
                        id="battery-iface-stats-poll"
                        value={batterySaver.interfacesStatsPollSeconds}
                        type="number"
                        min="1"
                        max="120"
                        class="input-field"
                        onchange={(e) =>
                            onpatch?.({
                                interfacesStatsPollSeconds: Number((e.target as HTMLInputElement).value),
                            })}
                    />
                </div>
                <div class="space-y-2">
                    <label for="battery-iface-disc-poll" class="text-sm font-medium text-sem-fg block">
                        {t("settings.battery.interfaces_discovery_poll_seconds")}
                    </label>
                    <input
                        id="battery-iface-disc-poll"
                        value={batterySaver.interfacesDiscoveryPollSeconds}
                        type="number"
                        min="5"
                        max="300"
                        class="input-field"
                        onchange={(e) =>
                            onpatch?.({
                                interfacesDiscoveryPollSeconds: Number((e.target as HTMLInputElement).value),
                            })}
                    />
                </div>
            </div>

            <label class="setting-toggle">
                <Toggle
                    id="settings-battery-bitrate-limits"
                    checked={Boolean(batterySaver.applyInterfaceBitrateLimits)}
                    onchange={(val) => onpatch?.({ applyInterfaceBitrateLimits: val === true })}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("settings.battery.apply_interface_bitrate_limits")}</span>
                    <span class="setting-toggle__description"
                        >{t("settings.battery.apply_interface_bitrate_limits_desc")}</span
                    >
                </span>
            </label>

            {#if batterySaver.applyInterfaceBitrateLimits}
                <div class="space-y-3">
                    <p class="text-xs text-sem-fg-muted">
                        {t("settings.battery.interface_bitrate_limits_help")}
                    </p>
                    {#if batteryInterfaceRows.length === 0}
                        <div class="text-xs text-sem-fg-muted">
                            {t("settings.battery.interface_bitrate_limits_empty")}
                        </div>
                    {/if}
                    {#each batteryInterfaceRows as row (row.name)}
                        <div class="grid grid-cols-1 sm:grid-cols-[1fr_10rem] gap-2 items-center">
                            <div class="text-sm text-sem-fg truncate" title={row.name}>
                                {row.name}
                                <span class="text-xs text-sem-fg-muted"> ({row.type || "?"}) </span>
                            </div>
                            <input
                                value={batterySaver.interfaceBitrateLimits?.[row.name]}
                                type="number"
                                min="0"
                                class="input-field"
                                placeholder={t("settings.battery.interface_bitrate_placeholder")}
                                onchange={(e) => onBitrateInput(row.name, (e.target as HTMLInputElement).value)}
                            />
                        </div>
                    {/each}
                    <div class="flex flex-wrap gap-2">
                        <button
                            type="button"
                            class="secondary-button text-sm"
                            disabled={batteryBitrateBusy}
                            onclick={onapplybitrates}
                        >
                            {t("settings.battery.apply_bitrates_reload")}
                        </button>
                        <button
                            type="button"
                            class="secondary-button text-sm"
                            disabled={batteryBitrateBusy}
                            onclick={onrestorebitrates}
                        >
                            {t("settings.battery.restore_bitrates_reload")}
                        </button>
                    </div>
                </div>
            {/if}
        </div>
    </section>
{/if}
