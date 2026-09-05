<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "../Toggle.svelte";
    import { t } from "../../../../js/i18n.js";

    interface Props {
        visible?: boolean;
        renderer?: string;
        viewMode?: string;
        showDisabledInterfaces?: boolean;
        showDiscoveredInterfaces?: boolean;
        onrendererchange?: (val: string) => void;
        onviewmodechange?: (val: string) => void;
        onshowdisabledchange?: (val: boolean) => void;
        onshowdiscoveredchange?: (val: boolean) => void;
    }

    let {
        visible = true,
        renderer = "auto",
        viewMode = "flat",
        showDisabledInterfaces = false,
        showDiscoveredInterfaces = false,
        onrendererchange,
        onviewmodechange,
        onshowdisabledchange,
        onshowdiscoveredchange,
    }: Props = $props();
</script>

{#if visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">Visualiser</div>
                <h2>{t("visualiser.title")}</h2>
                <p>{t("visualiser.description")}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <div class="space-y-2">
                <label
                    for="settings-visualiser-renderer"
                    class="text-sm font-medium text-gray-900 dark:text-gray-100 block"
                >
                    {t("visualiser.renderer_title")}
                </label>
                <p class="text-xs text-gray-600 dark:text-gray-400">
                    {t("visualiser.renderer_desc")}
                </p>
                <select
                    id="settings-visualiser-renderer"
                    value={renderer}
                    class="input-field"
                    onchange={(e) => onrendererchange?.((e.target as HTMLSelectElement).value)}
                >
                    <option value="auto">{t("visualiser.renderer_option_auto")}</option>
                    <option value="webgl">{t("visualiser.renderer_option_webgl")}</option>
                    <option value="vis">{t("visualiser.renderer_option_vis")}</option>
                </select>
            </div>
            <div class="space-y-2">
                <label
                    for="settings-visualiser-view-mode"
                    class="text-sm font-medium text-gray-900 dark:text-gray-100 block"
                >
                    {t("visualiser.view_mode")}
                </label>
                <p class="text-xs text-gray-600 dark:text-gray-400">
                    {t("visualiser.view_mode_desc")}
                </p>
                <select
                    id="settings-visualiser-view-mode"
                    value={viewMode}
                    class="input-field"
                    onchange={(e) => onviewmodechange?.((e.target as HTMLSelectElement).value)}
                >
                    <option value="flat">{t("visualiser.view_mode_flat_full")}</option>
                    <option value="planet">{t("visualiser.view_mode_planet_full")}</option>
                </select>
            </div>
            <label class="setting-toggle">
                <Toggle
                    id="settings-visualiser-offline"
                    checked={showDisabledInterfaces}
                    onchange={onshowdisabledchange}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("visualiser.show_disabled_interfaces")}</span>
                </span>
            </label>
            <label class="setting-toggle">
                <Toggle
                    id="settings-visualiser-discovered"
                    checked={showDiscoveredInterfaces}
                    onchange={onshowdiscoveredchange}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("visualiser.show_discovered_interfaces")}</span>
                </span>
            </label>
        </div>
    </section>
{/if}
