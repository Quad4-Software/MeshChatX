<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <section v-show="showSection" class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">{{ $t("app.notifications") }}</div>
                <h2>{{ $t("app.notification_sound_settings") }}</h2>
                <p>{{ $t("app.notification_sound_settings_description") }}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <div class="rounded-2xl border border-sem-border bg-white/70 dark:bg-zinc-900/70 px-3 py-3">
                <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0 flex-1 space-y-1">
                        <div class="text-sm font-semibold text-sem-fg">
                            {{ $t("app.enable_notification_sound") }}
                        </div>
                        <p class="text-sm text-sem-fg-muted leading-relaxed">
                            {{ $t("app.enable_notification_sound_description") }}
                        </p>
                    </div>
                    <Toggle
                        id="notification-sound-enabled"
                        class="shrink-0 mt-0.5"
                        :model-value="config.notification_sound_enabled"
                        @update:model-value="onEnabledChange"
                    />
                </div>
            </div>

            <div v-if="config.notification_sound_enabled" class="space-y-4">
                <div>
                    <div class="flex items-center justify-between mb-2">
                        <label class="text-sm font-semibold text-sem-fg-muted">
                            {{ $t("app.notification_sound_volume") }}
                        </label>
                        <span class="text-xs font-mono text-gray-400">{{ config.notification_sound_volume }}%</span>
                    </div>
                    <input
                        :value="config.notification_sound_volume"
                        type="range"
                        min="0"
                        max="100"
                        class="w-full h-1.5 bg-gray-200 dark:bg-zinc-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
                        @input="onVolumeChange"
                    />
                </div>

                <div class="space-y-2">
                    <label class="text-sm font-semibold text-sem-fg-muted">
                        {{ $t("app.notification_sound_default") }}
                    </label>
                    <select
                        :value="config.notification_sound_preferred_id"
                        class="input-field py-1.5! px-3! text-sm! rounded-xl! border-gray-200! dark:border-zinc-800! w-full max-w-md"
                        @change="onPreferredChange"
                    >
                        <option :value="0">{{ $t("app.notification_sound_primary_default") }}</option>
                        <option v-for="sound in sounds" :key="sound.id" :value="sound.id">
                            {{ sound.display_name }}
                        </option>
                    </select>
                </div>

                <div class="flex items-center justify-between">
                    <label class="text-sm font-semibold text-sem-fg-muted">
                        {{ $t("app.notification_sounds") }}
                    </label>
                    <button
                        type="button"
                        class="text-xs font-bold text-sem-accent hover:underline flex items-center gap-1"
                        :disabled="isUploading"
                        @click="$refs.soundUpload.click()"
                    >
                        <MaterialDesignIcon icon-name="plus" class="size-4" />
                        {{ isUploading ? $t("app.notification_sound_uploading") : $t("app.notification_sound_upload") }}
                    </button>
                    <input
                        ref="soundUpload"
                        type="file"
                        accept=".mp3,.ogg,.wav,.m4a,.flac,audio/*"
                        class="hidden"
                        @change="uploadSound"
                    />
                </div>

                <p v-if="sounds.length === 0" class="text-sm text-sem-fg-muted">
                    {{ $t("app.notification_sound_none_uploaded") }}
                </p>

                <div v-else class="grid gap-3">
                    <div
                        v-for="sound in sounds"
                        :key="sound.id"
                        class="flex items-center justify-between gap-3 rounded-xl border border-sem-border px-3 py-2"
                    >
                        <div class="min-w-0 flex-1">
                            <div class="text-sm font-semibold truncate">{{ sound.display_name }}</div>
                            <div v-if="sound.is_primary" class="text-xs text-sem-accent">
                                {{ $t("app.notification_sound_primary") }}
                            </div>
                        </div>
                        <div class="flex items-center gap-2 shrink-0">
                            <button
                                type="button"
                                class="rounded-lg p-1.5 text-gray-500 hover:bg-sem-surface-muted"
                                :title="$t('app.notification_sound_preview')"
                                @click="previewSound(sound)"
                            >
                                <MaterialDesignIcon
                                    :icon-name="playingSoundId === sound.id ? 'stop' : 'play'"
                                    class="size-4"
                                />
                            </button>
                            <button
                                v-if="!sound.is_primary"
                                type="button"
                                class="rounded-lg px-2 py-1 text-xs font-semibold text-sem-accent hover:bg-blue-50 dark:hover:bg-blue-900/20"
                                @click="setPrimarySound(sound)"
                            >
                                {{ $t("app.notification_sound_set_primary") }}
                            </button>
                            <button
                                type="button"
                                class="rounded-lg p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
                                :title="$t('app.notification_sound_remove')"
                                @click="deleteSound(sound)"
                            >
                                <MaterialDesignIcon icon-name="delete" class="size-4" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import Toggle from "../forms/Toggle.vue";
import ToastUtils from "../../js/ToastUtils";
import DialogUtils from "../../js/DialogUtils";
import NotificationSoundUtils from "../../js/NotificationSoundUtils";

export default {
    name: "NotificationSoundSettings",
    components: {
        MaterialDesignIcon,
        Toggle,
    },
    props: {
        config: {
            type: Object,
            required: true,
        },
        showSection: {
            type: Boolean,
            default: true,
        },
        updateConfig: {
            type: Function,
            required: true,
        },
    },
    emits: ["sounds-changed"],
    data() {
        return {
            sounds: [],
            isUploading: false,
            playingSoundId: null,
        };
    },
    mounted() {
        this.loadSounds();
    },
    methods: {
        async loadSounds() {
            try {
                const response = await window.api.get("/api/v1/notification-sounds");
                this.sounds = response.data ?? [];
            } catch (error) {
                console.error("Failed to load notification sounds:", error);
                this.sounds = [];
            }
        },
        onEnabledChange(value) {
            this.updateConfig({ notification_sound_enabled: value }, "notification_sound_enabled");
        },
        onVolumeChange(event) {
            const value = Number(event.target.value);
            this.updateConfig({ notification_sound_volume: value }, "notification_sound_volume");
        },
        onPreferredChange(event) {
            const value = Number(event.target.value);
            this.updateConfig({ notification_sound_preferred_id: value }, "notification_sound_preferred_id");
        },
        async uploadSound(event) {
            const file = event.target.files?.[0];
            if (!file) {
                return;
            }

            this.isUploading = true;
            const formData = new FormData();
            formData.append("file", file);

            try {
                await window.api.post("/api/v1/notification-sounds/upload", formData, {
                    headers: {
                        "Content-Type": "multipart/form-data",
                    },
                });
                ToastUtils.success(this.$t("app.notification_sound_uploaded"));
                await this.loadSounds();
                this.$emit("sounds-changed");
            } catch (error) {
                console.error(error);
                ToastUtils.error(error.response?.data?.message || this.$t("app.notification_sound_upload_failed"));
            } finally {
                this.isUploading = false;
                event.target.value = "";
            }
        },
        async deleteSound(sound) {
            if (!(await DialogUtils.confirm(this.$t("common.delete_confirm")))) {
                return;
            }
            try {
                await window.api.delete(`/api/v1/notification-sounds/${sound.id}`);
                ToastUtils.success(this.$t("app.notification_sound_deleted"));
                if (this.playingSoundId === sound.id) {
                    NotificationSoundUtils.stop();
                    this.playingSoundId = null;
                }
                await this.loadSounds();
                this.$emit("sounds-changed");
            } catch (error) {
                console.error(error);
                ToastUtils.error(this.$t("app.notification_sound_delete_failed"));
            }
        },
        async setPrimarySound(sound) {
            try {
                await window.api.patch(`/api/v1/notification-sounds/${sound.id}`, {
                    is_primary: true,
                });
                ToastUtils.success(this.$t("app.notification_sound_primary_set"));
                await this.loadSounds();
            } catch (error) {
                console.error(error);
                ToastUtils.error(this.$t("app.notification_sound_primary_set_failed"));
            }
        },
        async previewSound(sound) {
            if (this.playingSoundId === sound.id) {
                NotificationSoundUtils.stop();
                this.playingSoundId = null;
                return;
            }

            const played = await NotificationSoundUtils.preview(sound.id, this.config.notification_sound_volume ?? 100);
            if (played) {
                this.playingSoundId = sound.id;
                return;
            }
            ToastUtils.warning(this.$t("app.notification_sound_preview_failed"));
        },
    },
};
</script>
