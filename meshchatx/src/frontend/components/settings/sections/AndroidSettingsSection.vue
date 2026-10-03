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

            <div class="space-y-2">
                <div class="setting-toggle__title">{{ $t("settings.android_remote_backend_heading") }}</div>
                <p class="text-xs opacity-80">{{ $t("settings.android_remote_backend_desc") }}</p>
                <input
                    :value="remoteBackendUrl"
                    type="url"
                    inputmode="url"
                    autocomplete="off"
                    spellcheck="false"
                    class="w-full rounded-sm border border-sem-border bg-sem-surface px-3 py-2 text-sm"
                    :placeholder="$t('settings.android_remote_backend_placeholder')"
                    @input="$emit('update:remoteBackendUrl', $event.target.value)"
                />
                <p v-if="remoteBackendActive" class="text-xs text-sem-success">
                    {{ $t("settings.android_remote_backend_active", { url: effectiveBackendUrl }) }}
                </p>
                <div class="flex flex-wrap gap-2">
                    <button
                        type="button"
                        class="btn-maintenance border-sem-info dark:border-sem-info text-sem-info bg-sem-info/15 hover:bg-sem-info/15 dark:hover:bg-sem-info/15"
                        @click="$emit('apply-remote-backend')"
                    >
                        {{ $t("settings.android_remote_backend_apply") }}
                    </button>
                    <button
                        type="button"
                        class="btn-maintenance border-sem-border text-sem-fg bg-sem-surface-muted/40 hover:bg-gray-100 dark:hover:bg-sem-surface"
                        :disabled="!remoteBackendActive && !(remoteBackendUrl || '').trim()"
                        @click="$emit('clear-remote-backend')"
                    >
                        {{ $t("settings.android_remote_backend_use_local") }}
                    </button>
                </div>
            </div>

            <button
                type="button"
                class="btn-maintenance border-sem-info dark:border-sem-info text-sem-info bg-sem-info/15 hover:bg-sem-info/15 dark:hover:bg-sem-info/15"
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
        remoteBackendUrl: {
            type: String,
            default: "",
        },
        effectiveBackendUrl: {
            type: String,
            default: "",
        },
        remoteBackendActive: {
            type: Boolean,
            default: false,
        },
    },
    emits: [
        "update:blockScreenshots",
        "update:clearClipboardOnBackground",
        "update:remoteBackendUrl",
        "apply-remote-backend",
        "clear-remote-backend",
        "share-apk",
    ],
};
</script>
