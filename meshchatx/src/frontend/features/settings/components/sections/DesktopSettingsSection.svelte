<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "../Toggle.svelte";
    import ElectronUtils from "../../../../js/ElectronUtils.js";
    import { t } from "../../../../js/i18n.js";

    interface Props {
        visible?: boolean;
        config?: Record<string, any>;
        desktopCloseSettings?: {
            trayEnabled?: boolean;
            closeBehavior?: string;
            [k: string]: any;
        };
        onhardwareaccelerationchange?: (val: boolean) => void;
        ontrayenabledchange?: (val: boolean) => void;
        onclosebehaviorchange?: (val: string) => void;
    }

    let {
        visible = true,
        config = {},
        desktopCloseSettings = {},
        onhardwareaccelerationchange,
        ontrayenabledchange,
        onclosebehaviorchange,
    }: Props = $props();

    const isElectron = $derived(ElectronUtils.isElectron());
</script>

{#if isElectron && visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">Desktop</div>
                <h2>App Behaviour</h2>
                <p>Control how MeshChat behaves on your desktop.</p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <label class="setting-toggle opacity-50 cursor-not-allowed">
                <Toggle id="desktop-open-calls-in-separate-window" checked={false} disabled={true} />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("app.desktop_open_calls_in_separate_window")}</span>
                    <span class="setting-toggle__description">
                        {t("app.desktop_open_calls_in_separate_window_description")}
                        <span class="text-blue-500 font-bold block mt-1">(Phased out for now)</span>
                    </span>
                </span>
            </label>

            <label class="setting-toggle">
                <Toggle
                    id="desktop-hardware-acceleration-enabled"
                    checked={Boolean(config.desktop_hardware_acceleration_enabled)}
                    onchange={onhardwareaccelerationchange}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("app.desktop_hardware_acceleration_enabled")}</span>
                    <span class="setting-toggle__description">
                        {t("app.desktop_hardware_acceleration_enabled_description")}
                    </span>
                    <span class="setting-toggle__hint">{t("app.requires_restart")}</span>
                </span>
            </label>

            <label class="setting-toggle">
                <Toggle
                    id="desktop-tray-enabled"
                    checked={Boolean(desktopCloseSettings.trayEnabled)}
                    onchange={ontrayenabledchange}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("app.desktop_tray_enabled")}</span>
                    <span class="setting-toggle__description">{t("app.desktop_tray_enabled_description")}</span>
                </span>
            </label>

            <div class="flex flex-col gap-2">
                <label for="desktop-close-behavior" class="text-sm font-medium text-sem-fg">
                    {t("app.desktop_close_behavior")}
                </label>
                <span class="text-xs text-sem-fg-muted">{t("app.desktop_close_behavior_description")}</span>
                <select
                    id="desktop-close-behavior"
                    value={desktopCloseSettings.closeBehavior}
                    class="input-field"
                    onchange={(e) => onclosebehaviorchange?.((e.target as HTMLSelectElement).value)}
                >
                    <option value="ask">{t("app.desktop_close_behavior_ask")}</option>
                    <option value="quit">{t("app.desktop_close_behavior_quit")}</option>
                    <option value="background">
                        {desktopCloseSettings.trayEnabled
                            ? t("app.desktop_close_behavior_background")
                            : t("app.desktop_close_behavior_background_no_tray")}
                    </option>
                </select>
            </div>
        </div>
    </section>
{/if}
