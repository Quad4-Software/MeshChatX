<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <section v-show="visible" class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">Android</div>
                <h2>{{ $t("settings.android_privacy_heading") }}</h2>
                <p>{{ $t("settings.android_privacy_desc") }}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <label class="setting-toggle">
                <input
                    :checked="androidShellPrivacy.blockScreenshots"
                    type="checkbox"
                    class="rounded-sm"
                    @change="$emit('update:blockScreenshots', $event.target.checked)"
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{{ $t("settings.android_block_screenshots") }}</span>
                    <span class="setting-toggle__description">{{ $t("settings.android_block_screenshots_desc") }}</span>
                </span>
            </label>
            <label class="setting-toggle">
                <input
                    :checked="androidShellPrivacy.clearClipboardOnBackground"
                    type="checkbox"
                    class="rounded-sm"
                    @change="$emit('update:clearClipboardOnBackground', $event.target.checked)"
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{{
                        $t("settings.android_clear_clipboard_on_background")
                    }}</span>
                    <span class="setting-toggle__description">{{
                        $t("settings.android_clear_clipboard_on_background_desc")
                    }}</span>
                </span>
            </label>
            <button
                type="button"
                class="btn-maintenance border-blue-200 dark:border-blue-900/30 text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/10 hover:bg-blue-100 dark:hover:bg-blue-900/20"
                @click="$emit('share-apk')"
            >
                <div class="flex flex-col items-start text-left">
                    <div class="font-bold flex items-center gap-2">
                        <MaterialDesignIcon icon-name="share-variant" class="size-4" />
                        {{ $t("settings.share_apk") }}
                    </div>
                    <div class="text-xs opacity-80">
                        {{ $t("settings.share_apk_short_hint") }}
                    </div>
                </div>
            </button>
        </div>
    </section>
</template>

<script>
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";

export default {
    name: "AndroidSettingsSection",
    components: {
        MaterialDesignIcon,
    },
    props: {
        visible: {
            type: Boolean,
            default: true,
        },
        androidShellPrivacy: {
            type: Object,
            required: true,
        },
    },
    emits: ["update:blockScreenshots", "update:clearClipboardOnBackground", "share-apk"],
};
</script>
