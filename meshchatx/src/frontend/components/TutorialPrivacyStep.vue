<!-- SPDX-License-Identifier: 0BSD -->
<template>
    <div class="tutorial-privacy" :class="compact ? 'tutorial-privacy--compact' : ''">
        <div class="tutorial-privacy__intro">
            <span class="tutorial-privacy__icon">
                <MaterialDesignIcon icon-name="shield-lock-outline" class="size-6" />
            </span>
            <div class="min-w-0">
                <h2 class="tutorial-privacy__title">
                    {{ $t("tutorial.privacy_title") }}
                </h2>
                <p class="tutorial-privacy__desc">
                    {{ $t("tutorial.privacy_desc") }}
                </p>
            </div>
        </div>

        <div class="tutorial-privacy__list">
            <div v-if="showWindowsScreenSecurity" class="tutorial-privacy__callout">
                <div class="tutorial-privacy__callout-title">
                    {{ $t("app.screen_security_drm_eyebrow") }}
                </div>
                <p class="tutorial-privacy__callout-body">
                    {{ $t("tutorial.privacy_screen_security_desc") }}
                </p>
                <SettingToggleRow
                    id="tutorial-screen-security"
                    v-model="screenSecurityEnabled"
                    :title="$t('app.screen_security_enabled')"
                    :description="$t('app.screen_security_description_short')"
                    :disabled="screenSecuritySaving || stackReloading"
                    @update:model-value="onScreenSecurityChange"
                />
            </div>

            <SettingToggleRow
                v-if="showAndroidScreenshotBlock"
                id="tutorial-android-block-screenshots"
                v-model="androidBlockScreenshots"
                :title="$t('settings.android_block_screenshots')"
                :description="$t('tutorial.privacy_android_screenshots_desc')"
                :disabled="androidSaving || stackReloading"
                @update:model-value="onAndroidBlockScreenshotsChange"
            />

            <SettingToggleRow
                id="tutorial-obfuscate-hops"
                v-model="localHopsDelta"
                :title="$t('app.obfuscate_hops')"
                :description="$t('tutorial.privacy_obfuscate_hops_desc')"
                :disabled="reticulumSaving || stackReloading"
                @update:model-value="onLocalHopsDeltaChange"
            />

            <SettingToggleRow
                id="tutorial-privacy-mode"
                v-model="privacyModeEnabled"
                :title="$t('app.privacy_mode_enabled')"
                :description="$t('tutorial.privacy_mode_desc')"
                :disabled="configSaving || stackReloading"
                @update:model-value="onPrivacyModeChange"
            />

            <SettingToggleRow
                id="tutorial-telemetry"
                v-model="telemetryEnabled"
                :title="$t('app.telemetry_enabled')"
                :description="$t('tutorial.privacy_telemetry_desc')"
                :disabled="configSaving || stackReloading"
                @update:model-value="onTelemetryChange"
            />
        </div>

        <p class="tutorial-privacy__hint">
            {{ $t("tutorial.privacy_later_hint") }}
        </p>
    </div>
</template>

<script>
import { useAuthStore } from "../js/stores/authStore";

import DesktopUtils from "../js/DesktopUtils.js";
import AndroidBridge from "../js/rnode/AndroidBridge.js";
import ToastUtils from "../js/ToastUtils";
import { apiPath, EMITTER_EVENTS, WS_EVENTS } from "../js/constants";
import { onWsEvent, offWsEvent } from "../js/registries/wsEventRegistry.js";
import GlobalEmitter from "../js/GlobalEmitter";
import SettingToggleRow from "./settings/SettingToggleRow.vue";
import MaterialDesignIcon from "./MaterialDesignIcon.vue";

export default {
    name: "TutorialPrivacyStep",
    components: {
        SettingToggleRow,
        MaterialDesignIcon,
    },
    props: {
        compact: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            screenSecurityEnabled: false,
            screenSecuritySaving: false,
            showWindowsScreenSecurity: false,
            androidBlockScreenshots: false,
            androidSaving: false,
            showAndroidScreenshotBlock: false,
            localHopsDelta: false,
            reticulumSaving: false,
            stackReloading: false,
            privacyModeEnabled: false,
            telemetryEnabled: false,
            configSaving: false,
        };
    },
    async mounted() {
        onWsEvent(WS_EVENTS.RETICULUM_RELOAD_STATUS, this.onReticulumReloadStatus);
        GlobalEmitter.on(EMITTER_EVENTS.WEBSOCKET_RECONNECTED, this.onWebsocketReconnected);
        await this.loadPrivacyOptions();
    },
    beforeUnmount() {
        offWsEvent(WS_EVENTS.RETICULUM_RELOAD_STATUS, this.onReticulumReloadStatus);
        GlobalEmitter.off(EMITTER_EVENTS.WEBSOCKET_RECONNECTED, this.onWebsocketReconnected);
    },
    methods: {
        onReticulumReloadStatus(json) {
            this.stackReloading = Boolean(json && typeof json === "object" && json.in_progress !== false);
        },
        onWebsocketReconnected() {
            this.stackReloading = false;
        },
        async loadPrivacyOptions() {
            this.showWindowsScreenSecurity =
                typeof DesktopUtils.isWindowsDesktop === "function" && DesktopUtils.isWindowsDesktop();
            this.showAndroidScreenshotBlock =
                typeof window !== "undefined" &&
                window.MeshChatXAndroid &&
                typeof window.MeshChatXAndroid.getPlatform === "function" &&
                window.MeshChatXAndroid.getPlatform() === "android";

            if (this.showWindowsScreenSecurity) {
                try {
                    const settings = await DesktopUtils.getScreenSecuritySettings();
                    this.screenSecurityEnabled = settings?.enabled === true;
                } catch {
                    this.screenSecurityEnabled = false;
                }
            }

            if (this.showAndroidScreenshotBlock) {
                try {
                    const bridge = new AndroidBridge();
                    this.androidBlockScreenshots = bridge.getBlockScreenshots() === true;
                } catch {
                    this.androidBlockScreenshots = false;
                }
            }

            try {
                const [configResponse, instanceResponse] = await Promise.all([
                    window.api.get(apiPath("/config")),
                    window.api.get(apiPath("/reticulum/instance")),
                ]);
                const config = configResponse?.data?.config || {};
                this.privacyModeEnabled = config.privacy_mode_enabled === true;
                this.telemetryEnabled = config.telemetry_enabled === true;
                this.localHopsDelta = instanceResponse?.data?.instance?.local_hops_delta === true;
            } catch (e) {
                console.error("Failed to load tutorial privacy options:", e);
            }
        },
        async onScreenSecurityChange(value) {
            if (this.screenSecuritySaving) {
                return;
            }
            this.screenSecuritySaving = true;
            try {
                const settings = await DesktopUtils.setScreenSecurityEnabled(value === true);
                this.screenSecurityEnabled = settings?.enabled === true;
                ToastUtils.success(
                    this.screenSecurityEnabled
                        ? this.$t("app.screen_security_enabled_toast")
                        : this.$t("app.screen_security_disabled_toast")
                );
            } catch (e) {
                console.error(e);
                this.screenSecurityEnabled = !value;
                ToastUtils.error(this.$t("common.save_failed"));
            } finally {
                this.screenSecuritySaving = false;
            }
        },
        async onAndroidBlockScreenshotsChange(value) {
            if (this.androidSaving) {
                return;
            }
            this.androidSaving = true;
            try {
                const bridge = new AndroidBridge();
                if (!bridge.setBlockScreenshots(value === true)) {
                    throw new Error("setBlockScreenshots failed");
                }
                this.androidBlockScreenshots = value === true;
            } catch (e) {
                console.error(e);
                this.androidBlockScreenshots = !value;
                ToastUtils.error(this.$t("common.save_failed"));
            } finally {
                this.androidSaving = false;
            }
        },
        async onLocalHopsDeltaChange(value) {
            if (this.reticulumSaving) {
                return;
            }
            this.reticulumSaving = true;
            try {
                await window.api.patch(apiPath("/reticulum/instance"), {
                    local_hops_delta: value === true,
                });
                this.localHopsDelta = value === true;
            } catch (e) {
                console.error(e);
                this.localHopsDelta = !value;
                ToastUtils.error(this.$t("settings.failed_update_reticulum_instance"));
            } finally {
                this.reticulumSaving = false;
            }
        },
        async onPrivacyModeChange(value) {
            if (this.configSaving) {
                return;
            }
            if (useAuthStore().demoMode) {
                // Demo forces privacy mode on the server. Keep the toggle on.
                this.privacyModeEnabled = true;
                ToastUtils.info(this.$t("app.demo_mode_active"));
                return;
            }
            this.configSaving = true;
            try {
                await window.api.patch(apiPath("/config"), {
                    privacy_mode_enabled: value === true,
                });
                this.privacyModeEnabled = value === true;
            } catch (e) {
                console.error(e);
                this.privacyModeEnabled = !value;
                ToastUtils.error(this.$t("common.save_failed"));
            } finally {
                this.configSaving = false;
            }
        },
        async onTelemetryChange(value) {
            if (this.configSaving) {
                return;
            }
            if (useAuthStore().demoMode) {
                this.telemetryEnabled = value === true;
                return;
            }
            this.configSaving = true;
            try {
                await window.api.patch(apiPath("/config"), {
                    telemetry_enabled: value === true,
                });
                this.telemetryEnabled = value === true;
            } catch (e) {
                console.error(e);
                this.telemetryEnabled = !value;
                ToastUtils.error(this.$t("common.save_failed"));
            } finally {
                this.configSaving = false;
            }
        },
    },
};
</script>

<style scoped>
@reference "../style.css";
.tutorial-privacy {
    @apply space-y-4;
}
.tutorial-privacy--compact {
    @apply space-y-3;
}
.tutorial-privacy__intro {
    @apply flex items-center gap-3 sm:gap-4;
}
.tutorial-privacy__icon {
    @apply flex size-11 shrink-0 items-center justify-center rounded-2xl bg-sem-accent/10 text-sem-accent;
}
.tutorial-privacy__title {
    @apply text-xl sm:text-2xl font-bold tracking-tight text-sem-fg;
}
.tutorial-privacy__desc {
    @apply mt-1 text-sm text-sem-fg-muted;
}
.tutorial-privacy__list {
    @apply space-y-2 w-full;
}
.tutorial-privacy__callout {
    @apply p-3 rounded-2xl border border-sem-warning dark:border-sem-warning bg-sem-warning/15 dark:bg-sem-warning/15 text-left space-y-2;
}
.tutorial-privacy__callout-title {
    @apply text-sm font-semibold text-sem-warning dark:text-sem-warning;
}
.tutorial-privacy__callout-body {
    @apply text-xs text-sem-warning dark:text-amber-100/90;
}
.tutorial-privacy__hint {
    @apply text-xs text-sem-fg-muted;
}
.tutorial-privacy :deep(.setting-toggle) {
    @apply relative flex flex-row-reverse items-start gap-3 rounded-2xl border border-sem-border bg-white/70 dark:bg-sem-surface px-3 py-2.5;
}
.tutorial-privacy :deep(.setting-toggle > label) {
    @apply shrink-0 self-start mt-0.5;
}
.tutorial-privacy :deep(.setting-toggle .sr-only) {
    @apply absolute w-px h-px p-0 -m-px overflow-hidden whitespace-nowrap border-0;
}
.tutorial-privacy :deep(.setting-toggle__label) {
    @apply flex-1 min-w-0 flex flex-col gap-0.5;
}
.tutorial-privacy :deep(.setting-toggle__title) {
    @apply text-sm font-semibold text-sem-fg wrap-break-word leading-snug;
}
.tutorial-privacy :deep(.setting-toggle__description) {
    @apply text-xs text-sem-fg-muted wrap-break-word leading-snug;
}
</style>
