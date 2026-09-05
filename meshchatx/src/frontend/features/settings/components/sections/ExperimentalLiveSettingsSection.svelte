<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "../Toggle.svelte";
    import { t } from "../../../../js/i18n.js";

    interface Props {
        visible?: boolean;
        liveTransportMode?: string;
        sidecarEnabled?: boolean;
        onmodechange?: (mode: string) => void;
        onsidecarchange?: (enabled: boolean) => void;
    }

    let {
        visible = false,
        liveTransportMode = "auto",
        sidecarEnabled = false,
        onmodechange,
        onsidecarchange,
    }: Props = $props();
</script>

{#if visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">{t("settings.experimental.eyebrow")}</div>
                <h2>{t("settings.experimental.title")}</h2>
                <p>{t("settings.experimental.description")}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <label class="setting-toggle">
                <Toggle id="settings-wt-sidecar-enabled" checked={sidecarEnabled} onchange={onsidecarchange} />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("settings.experimental.webtransport_sidecar")}</span>
                    <span class="setting-toggle__description">
                        {t("settings.experimental.webtransport_sidecar_desc")}
                    </span>
                </span>
            </label>

            <div class="space-y-2">
                <label for="settings-live-transport-mode" class="text-sm font-medium text-sem-fg block">
                    {t("settings.experimental.live_transport_mode")}
                </label>
                <p class="text-xs text-sem-fg-muted">
                    {t("settings.experimental.live_transport_mode_desc")}
                </p>
                <select
                    id="settings-live-transport-mode"
                    class="input-field"
                    value={liveTransportMode}
                    onchange={(e) => onmodechange?.((e.target as HTMLSelectElement).value)}
                >
                    <option value="auto">{t("settings.experimental.mode_auto")}</option>
                    <option value="websocket">{t("settings.experimental.mode_websocket")}</option>
                    <option value="webtransport">{t("settings.experimental.mode_webtransport")}</option>
                </select>
            </div>
        </div>
    </section>
{/if}
