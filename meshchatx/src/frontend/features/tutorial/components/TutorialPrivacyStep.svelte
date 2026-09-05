<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Step 7. Privacy switches that a first run should decide before any
     * traffic leaves the machine. Privacy mode only gates backend clearnet
     * calls, it never touches Reticulum traffic.
     */
    import { onMount } from "svelte";
    import ElectronUtils from "../../../js/ElectronUtils.js";
    import AndroidBridge from "../../../js/rnode/AndroidBridge.js";
    import GlobalState from "../../../js/GlobalState.js";
    import ToastUtils from "../../../js/ToastUtils.js";
    import { t } from "../../../js/i18n.js";
    import SettingToggleRow from "../../settings/components/SettingToggleRow.svelte";

    interface Props {
        compact?: boolean;
    }

    let { compact = false }: Props = $props();

    let screenSecurityEnabled = $state(false);
    let screenSecuritySaving = $state(false);
    let showWindowsScreenSecurity = $state(false);
    let androidBlockScreenshots = $state(false);
    let androidSaving = $state(false);
    let showAndroidScreenshotBlock = $state(false);
    let localHopsDelta = $state(false);
    let reticulumSaving = $state(false);
    let privacyModeEnabled = $state(false);
    let telemetryEnabled = $state(false);
    let configSaving = $state(false);

    onMount(() => {
        void loadPrivacyOptions();
    });

    async function loadPrivacyOptions(): Promise<void> {
        showWindowsScreenSecurity =
            typeof ElectronUtils.isWindowsElectron === "function" && ElectronUtils.isWindowsElectron();
        showAndroidScreenshotBlock =
            typeof window !== "undefined" &&
            Boolean(window.MeshChatXAndroid) &&
            typeof window.MeshChatXAndroid.getPlatform === "function" &&
            window.MeshChatXAndroid.getPlatform() === "android";

        if (showWindowsScreenSecurity) {
            try {
                const settings = await ElectronUtils.getScreenSecuritySettings();
                screenSecurityEnabled = settings?.enabled === true;
            } catch {
                screenSecurityEnabled = false;
            }
        }

        if (showAndroidScreenshotBlock) {
            try {
                const bridge = new AndroidBridge();
                androidBlockScreenshots = bridge.getBlockScreenshots() === true;
            } catch {
                androidBlockScreenshots = false;
            }
        }

        try {
            const [configResponse, instanceResponse] = await Promise.all([
                window.api.get("/api/v1/config"),
                window.api.get("/api/v1/reticulum/instance"),
            ]);
            const config = configResponse?.data?.config || {};
            privacyModeEnabled = config.privacy_mode_enabled === true;
            telemetryEnabled = config.telemetry_enabled === true;
            localHopsDelta = instanceResponse?.data?.instance?.local_hops_delta === true;
        } catch (e) {
            console.error("Failed to load tutorial privacy options:", e);
        }
    }

    async function onScreenSecurityChange(value: boolean): Promise<void> {
        if (screenSecuritySaving) {
            return;
        }
        screenSecuritySaving = true;
        try {
            const settings = await ElectronUtils.setScreenSecurityEnabled(value === true);
            screenSecurityEnabled = settings?.enabled === true;
            ToastUtils.success(
                screenSecurityEnabled ? t("app.screen_security_enabled_toast") : t("app.screen_security_disabled_toast")
            );
        } catch (e) {
            console.error(e);
            screenSecurityEnabled = !value;
            ToastUtils.error(t("common.save_failed"));
        } finally {
            screenSecuritySaving = false;
        }
    }

    async function onAndroidBlockScreenshotsChange(value: boolean): Promise<void> {
        if (androidSaving) {
            return;
        }
        androidSaving = true;
        try {
            const bridge = new AndroidBridge();
            if (!bridge.setBlockScreenshots(value === true)) {
                throw new Error("setBlockScreenshots failed");
            }
            androidBlockScreenshots = value === true;
        } catch (e) {
            console.error(e);
            androidBlockScreenshots = !value;
            ToastUtils.error(t("common.save_failed"));
        } finally {
            androidSaving = false;
        }
    }

    async function onLocalHopsDeltaChange(value: boolean): Promise<void> {
        if (reticulumSaving) {
            return;
        }
        reticulumSaving = true;
        try {
            await window.api.patch("/api/v1/reticulum/instance", { local_hops_delta: value === true });
            localHopsDelta = value === true;
        } catch (e) {
            console.error(e);
            localHopsDelta = !value;
            ToastUtils.error(t("settings.failed_update_reticulum_instance"));
        } finally {
            reticulumSaving = false;
        }
    }

    async function onPrivacyModeChange(value: boolean): Promise<void> {
        if (configSaving) {
            return;
        }
        if (GlobalState.demoMode) {
            // Demo forces privacy mode on the server. Keep the toggle on.
            privacyModeEnabled = true;
            ToastUtils.info(t("app.demo_mode_active"));
            return;
        }
        configSaving = true;
        try {
            await window.api.patch("/api/v1/config", { privacy_mode_enabled: value === true });
            privacyModeEnabled = value === true;
        } catch (e) {
            console.error(e);
            privacyModeEnabled = !value;
            ToastUtils.error(t("common.save_failed"));
        } finally {
            configSaving = false;
        }
    }

    async function onTelemetryChange(value: boolean): Promise<void> {
        if (configSaving) {
            return;
        }
        if (GlobalState.demoMode) {
            telemetryEnabled = value === true;
            return;
        }
        configSaving = true;
        try {
            await window.api.patch("/api/v1/config", { telemetry_enabled: value === true });
            telemetryEnabled = value === true;
        } catch (e) {
            console.error(e);
            telemetryEnabled = !value;
            ToastUtils.error(t("common.save_failed"));
        } finally {
            configSaving = false;
        }
    }
</script>

<div class="tutorial-privacy {compact ? 'space-y-3' : 'space-y-4'}">
    <div class="space-y-1 text-center sm:text-left">
        <h2 class="text-xl sm:text-2xl font-black text-sem-fg">
            {t("tutorial.privacy_title")}
        </h2>
        <p class="text-sm text-sem-fg-muted max-w-xl mx-auto sm:mx-0">
            {t("tutorial.privacy_desc")}
        </p>
    </div>

    <div class="space-y-2 w-full max-w-xl mx-auto sm:mx-0">
        {#if showWindowsScreenSecurity}
            <div
                class="p-3 rounded-2xl border border-amber-200 dark:border-amber-900/50 bg-amber-50/90 dark:bg-amber-950/40 text-left space-y-2"
            >
                <div class="text-sm font-semibold text-amber-950 dark:text-amber-100">
                    {t("app.screen_security_drm_eyebrow")}
                </div>
                <p class="text-xs text-amber-950/90 dark:text-amber-100/90">
                    {t("tutorial.privacy_screen_security_desc")}
                </p>
                <SettingToggleRow
                    id="tutorial-screen-security"
                    checked={screenSecurityEnabled}
                    title={t("app.screen_security_enabled")}
                    description={t("app.screen_security_description_short")}
                    disabled={screenSecuritySaving}
                    onchange={(value) => void onScreenSecurityChange(value)}
                />
            </div>
        {/if}

        {#if showAndroidScreenshotBlock}
            <SettingToggleRow
                id="tutorial-android-block-screenshots"
                checked={androidBlockScreenshots}
                title={t("settings.android_block_screenshots")}
                description={t("tutorial.privacy_android_screenshots_desc")}
                disabled={androidSaving}
                onchange={(value) => void onAndroidBlockScreenshotsChange(value)}
            />
        {/if}

        <SettingToggleRow
            id="tutorial-obfuscate-hops"
            checked={localHopsDelta}
            title={t("app.obfuscate_hops")}
            description={t("tutorial.privacy_obfuscate_hops_desc")}
            disabled={reticulumSaving}
            onchange={(value) => void onLocalHopsDeltaChange(value)}
        />

        <SettingToggleRow
            id="tutorial-privacy-mode"
            checked={privacyModeEnabled}
            title={t("app.privacy_mode_enabled")}
            description={t("tutorial.privacy_mode_desc")}
            disabled={configSaving}
            onchange={(value) => void onPrivacyModeChange(value)}
        />

        <SettingToggleRow
            id="tutorial-telemetry"
            checked={telemetryEnabled}
            title={t("app.telemetry_enabled")}
            description={t("tutorial.privacy_telemetry_desc")}
            disabled={configSaving}
            onchange={(value) => void onTelemetryChange(value)}
        />
    </div>

    <p class="text-xs text-center sm:text-left text-sem-fg-muted max-w-xl mx-auto sm:mx-0">
        {t("tutorial.privacy_later_hint")}
    </p>
</div>
