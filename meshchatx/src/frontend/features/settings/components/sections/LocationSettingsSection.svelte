<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "../Toggle.svelte";
    import { t } from "../../../../js/i18n.js";

    interface Props {
        visible?: boolean;
        config?: Record<string, any>;
        onupdatefield?: (data: { key: string; value: any }) => void;
    }

    let { visible = true, config = {}, onupdatefield }: Props = $props();

    const mapOverlayLimitFields = [
        {
            key: "map_overlay_max_bytes",
            labelKey: "app.map_overlay_max_bytes",
            min: 65536,
            max: 67108864,
        },
        {
            key: "map_overlay_max_features",
            labelKey: "app.map_overlay_max_features",
            min: 100,
            max: 500000,
        },
        {
            key: "map_overlay_max_kmz_uncompressed_bytes",
            labelKey: "app.map_overlay_max_kmz_uncompressed_bytes",
            min: 262144,
            max: 134217728,
        },
        {
            key: "map_overlay_max_sources",
            labelKey: "app.map_overlay_max_sources",
            min: 1,
            max: 256,
        },
    ];

    function emitValue(key: string, value: any) {
        onupdatefield?.({ key, value });
    }

    function emitOverlayLimit(key: string, rawValue: string, min: number, max: number) {
        let val = Number(rawValue);
        if (Number.isNaN(val)) val = min;
        val = Math.max(min, Math.min(max, val));
        onupdatefield?.({ key, value: val });
    }
</script>

{#if visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">{t("app.settings_map_eyebrow")}</div>
                <h2>{t("app.map_settings_title")}</h2>
                <p>{t("app.map_settings_desc")}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <div class="space-y-2">
                <label for="location-source-select" class="text-sm font-medium text-sem-fg block">
                    {t("app.location_source")}
                </label>
                <select
                    id="location-source-select"
                    value={config.location_source}
                    class="input-field"
                    onchange={(e) => emitValue("location_source", (e.target as HTMLSelectElement).value)}
                >
                    <option value="disabled">{t("app.location_source_disabled")}</option>
                    <option value="browser">{t("app.location_source_browser")}</option>
                    <option value="manual">{t("app.location_source_manual")}</option>
                </select>
                {#if config.location_source === "disabled"}
                    <div class="text-xs text-sem-fg-muted">
                        {t("app.location_source_disabled_desc")}
                    </div>
                {:else if config.location_source === "browser"}
                    <div class="text-xs text-sem-fg-muted">
                        {t("app.location_source_browser_desc")}
                    </div>
                {:else if config.location_source === "manual"}
                    <div class="text-xs text-sem-fg-muted">
                        {t("app.location_source_manual_desc")}
                    </div>
                {/if}
            </div>

            {#if config.location_source === "manual"}
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div class="space-y-2">
                        <label for="loc-manual-lat" class="text-sm font-medium text-sem-fg block">
                            {t("app.location_manual_lat")}
                        </label>
                        <input
                            id="loc-manual-lat"
                            value={config.location_manual_lat}
                            type="text"
                            class="input-field"
                            placeholder="0.0"
                            oninput={(e) => emitValue("location_manual_lat", (e.target as HTMLInputElement).value)}
                        />
                    </div>
                    <div class="space-y-2">
                        <label for="loc-manual-lon" class="text-sm font-medium text-sem-fg block">
                            {t("app.location_manual_lon")}
                        </label>
                        <input
                            id="loc-manual-lon"
                            value={config.location_manual_lon}
                            type="text"
                            class="input-field"
                            placeholder="0.0"
                            oninput={(e) => emitValue("location_manual_lon", (e.target as HTMLInputElement).value)}
                        />
                    </div>
                    <div class="space-y-2">
                        <label for="loc-manual-alt" class="text-sm font-medium text-sem-fg block">
                            {t("app.location_manual_alt")}
                        </label>
                        <input
                            id="loc-manual-alt"
                            value={config.location_manual_alt}
                            type="text"
                            class="input-field"
                            placeholder="0.0"
                            oninput={(e) => emitValue("location_manual_alt", (e.target as HTMLInputElement).value)}
                        />
                    </div>
                </div>
            {/if}

            <div class="space-y-2 border-t border-sem-border pt-4">
                <div class="text-sm font-medium text-sem-fg">
                    {t("app.map_defaults_heading")}
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div class="space-y-2">
                        <label for="map-def-lat" class="text-sm font-medium text-sem-fg block">
                            {t("app.map_default_lat")}
                        </label>
                        <input
                            id="map-def-lat"
                            value={config.map_default_lat}
                            type="text"
                            class="input-field"
                            oninput={(e) => emitValue("map_default_lat", (e.target as HTMLInputElement).value)}
                        />
                    </div>
                    <div class="space-y-2">
                        <label for="map-def-lon" class="text-sm font-medium text-sem-fg block">
                            {t("app.map_default_lon")}
                        </label>
                        <input
                            id="map-def-lon"
                            value={config.map_default_lon}
                            type="text"
                            class="input-field"
                            oninput={(e) => emitValue("map_default_lon", (e.target as HTMLInputElement).value)}
                        />
                    </div>
                    <div class="space-y-2">
                        <label for="map-def-zoom" class="text-sm font-medium text-sem-fg block">
                            {t("app.map_default_zoom")}
                        </label>
                        <input
                            id="map-def-zoom"
                            value={config.map_default_zoom}
                            type="number"
                            class="input-field"
                            oninput={(e) => emitValue("map_default_zoom", Number((e.target as HTMLInputElement).value))}
                        />
                    </div>
                </div>
            </div>

            <div class="space-y-2 border-t border-sem-border pt-4">
                <div class="text-sm font-medium text-sem-fg">
                    {t("app.map_tiles_heading")}
                </div>
                <div class="space-y-2">
                    <label for="map-tile-url" class="text-sm font-medium text-sem-fg block">
                        {t("app.map_tile_server_url")}
                    </label>
                    <input
                        id="map-tile-url"
                        value={config.map_tile_server_url}
                        type="text"
                        class="input-field"
                        oninput={(e) => emitValue("map_tile_server_url", (e.target as HTMLInputElement).value)}
                    />
                </div>
                <div class="space-y-2">
                    <label for="map-nominatim-url" class="text-sm font-medium text-sem-fg block">
                        {t("app.map_nominatim_api_url")}
                    </label>
                    <input
                        id="map-nominatim-url"
                        value={config.map_nominatim_api_url}
                        type="text"
                        class="input-field"
                        oninput={(e) => emitValue("map_nominatim_api_url", (e.target as HTMLInputElement).value)}
                    />
                </div>
                <div>
                    <label for="map-coord-format" class="text-sm font-medium text-sem-fg block">
                        {t("app.map_coordinate_format")}
                    </label>
                    <select
                        id="map-coord-format"
                        value={config.map_coordinate_format}
                        class="input-field"
                        onchange={(e) => emitValue("map_coordinate_format", (e.target as HTMLSelectElement).value)}
                    >
                        <option value="wgs84">{t("app.map_coordinate_format_wgs84")}</option>
                        <option value="utm">{t("app.map_coordinate_format_utm")}</option>
                        <option value="mgrs">{t("app.map_coordinate_format_mgrs")}</option>
                        <option value="olc">{t("app.map_coordinate_format_olc")}</option>
                    </select>
                </div>
                <label class="setting-toggle">
                    <Toggle
                        id="map-offline-enabled"
                        checked={Boolean(config.map_offline_enabled)}
                        onchange={(val) => emitValue("map_offline_enabled", val)}
                    />
                    <span class="setting-toggle__label">
                        <span class="setting-toggle__title">{t("app.map_offline_enabled")}</span>
                    </span>
                </label>
                <label class="setting-toggle">
                    <Toggle
                        id="map-tile-cache-enabled"
                        checked={Boolean(config.map_tile_cache_enabled)}
                        onchange={(val) => emitValue("map_tile_cache_enabled", val)}
                    />
                    <span class="setting-toggle__label">
                        <span class="setting-toggle__title">{t("app.map_tile_cache_enabled")}</span>
                    </span>
                </label>
            </div>

            <div class="space-y-3 border-t border-sem-border pt-4">
                <div>
                    <div class="text-sm font-medium text-sem-fg">
                        {t("app.map_overlay_limits_heading")}
                    </div>
                    <div class="text-xs text-sem-fg-muted">
                        {t("app.map_overlay_limits_desc")}
                    </div>
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {#each mapOverlayLimitFields as field (field.key)}
                        <div class="space-y-2">
                            <label for={field.key} class="text-sm font-medium text-sem-fg block">
                                {t(field.labelKey)}
                            </label>
                            <input
                                id={field.key}
                                value={config[field.key]}
                                type="number"
                                class="input-field"
                                min={field.min}
                                max={field.max}
                                onchange={(e) =>
                                    emitOverlayLimit(
                                        field.key,
                                        (e.target as HTMLInputElement).value,
                                        field.min,
                                        field.max
                                    )}
                            />
                            <div class="text-[10px] text-sem-fg-muted">
                                {field.min} .. {field.max}
                            </div>
                        </div>
                    {/each}
                </div>
            </div>
        </div>
    </section>
{/if}
