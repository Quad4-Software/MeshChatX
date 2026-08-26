<!-- SPDX-License-Identifier: 0BSD -->
<template>
    <div class="tutorial-privacy" :class="compact ? 'tutorial-privacy--compact' : ''">
        <div class="tutorial-privacy__intro">
            <h2 class="tutorial-privacy__title">
                {{ $t("tutorial.privacy_title") }}
            </h2>
            <p class="tutorial-privacy__desc">
                {{ $t("tutorial.privacy_desc") }}
            </p>
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
                    :disabled="screenSecuritySaving"
                    @update:model-value="onScreenSecurityChange"
                />
            </div>

            <SettingToggleRow
                v-if="showAndroidScreenshotBlock"
                id="tutorial-android-block-screenshots"
                v-model="androidBlockScreenshots"
                :title="$t('settings.android_block_screenshots')"
                :description="$t('tutorial.privacy_android_screenshots_desc')"
                :disabled="androidSaving"
                @update:model-value="onAndroidBlockScreenshotsChange"
            />

            <SettingToggleRow
                id="tutorial-obfuscate-hops"
                v-model="localHopsDelta"
                :title="$t('app.obfuscate_hops')"
                :description="$t('tutorial.privacy_obfuscate_hops_desc')"
                :disabled="reticulumSaving"
                @update:model-value="onLocalHopsDeltaChange"
            />

            <SettingToggleRow
                id="tutorial-privacy-mode"
                v-model="privacyModeEnabled"
                :title="$t('app.privacy_mode_enabled')"
                :description="$t('tutorial.privacy_mode_desc')"
                :disabled="configSaving"
                @update:model-value="onPrivacyModeChange"
            />

            <SettingToggleRow
                id="tutorial-telemetry"
                v-model="telemetryEnabled"
                :title="$t('app.telemetry_enabled')"
                :description="$t('tutorial.privacy_telemetry_desc')"
                :disabled="configSaving"
                @update:model-value="onTelemetryChange"
            />
        </div>

        <p class="tutorial-privacy__hint">
            {{ $t("tutorial.privacy_later_hint") }}
        </p>
    </div>
</template>

<script>
import ElectronUtils from "../js/ElectronUtils.js";
import AndroidBridge from "../js/rnode/AndroidBridge.js";
import ToastUtils from "../js/ToastUtils";
import SettingToggleRow from "./settings/SettingToggleRow.vue";

export default {
    name: "TutorialPrivacyStep",
    components: {
        SettingToggleRow,
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
            privacyModeEnabled: false,
            telemetryEnabled: false,
            configSaving: false,
        };
    },
    async mounted() {
        await this.loadPrivacyOptions();
    },
    methods: {
        async loadPrivacyOptions() {
            this.showWindowsScreenSecurity =
                typeof ElectronUtils.isWindowsElectron === "function" && ElectronUtils.isWindowsElectron();
            this.showAndroidScreenshotBlock =
                typeof window !== "undefined" &&
                window.MeshChatXAndroid &&
                typeof window.MeshChatXAndroid.getPlatform === "function" &&
                window.MeshChatXAndroid.getPlatform() === "android";

            if (this.showWindowsScreenSecurity) {
                try {
                    const settings = await ElectronUtils.getScreenSecuritySettings();
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
                    window.api.get("/api/v1/config"),
                    window.api.get("/api/v1/reticulum/instance"),
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
                const settings = await ElectronUtils.setScreenSecurityEnabled(value === true);
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
                await window.api.patch("/api/v1/reticulum/instance", {
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
            this.configSaving = true;
            try {
                await window.api.patch("/api/v1/config", {
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
            this.configSaving = true;
            try {
                await window.api.patch("/api/v1/config", {
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
    @apply space-y-1 text-center sm:text-left;
}
.tutorial-privacy__title {
    @apply text-xl sm:text-2xl font-black text-sem-fg;
}
.tutorial-privacy__desc {
    @apply text-sm text-sem-fg-muted max-w-xl mx-auto sm:mx-0;
}
.tutorial-privacy__list {
    @apply space-y-2 w-full max-w-xl mx-auto sm:mx-0;
}
.tutorial-privacy__callout {
    @apply p-3 rounded-2xl border border-amber-200 dark:border-amber-900/50 bg-amber-50/90 dark:bg-amber-950/40 text-left space-y-2;
}
.tutorial-privacy__callout-title {
    @apply text-sm font-semibold text-amber-950 dark:text-amber-100;
}
.tutorial-privacy__callout-body {
    @apply text-xs text-amber-950/90 dark:text-amber-100/90;
}
.tutorial-privacy__hint {
    @apply text-xs text-center sm:text-left text-sem-fg-muted max-w-xl mx-auto sm:mx-0;
}
.tutorial-privacy :deep(.setting-toggle) {
    @apply relative flex flex-row-reverse items-start gap-3 rounded-2xl border border-sem-border bg-white/70 dark:bg-zinc-900/70 px-3 py-2.5;
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
