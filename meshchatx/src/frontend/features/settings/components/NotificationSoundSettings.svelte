<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import Toggle from "./Toggle.svelte";
    import ToastUtils from "../../../js/ToastUtils.js";
    import DialogUtils from "../../../js/DialogUtils.js";
    import NotificationSoundUtils from "../../../js/NotificationSoundUtils.js";
    import { t } from "../../../js/i18n.js";

    interface SoundItem {
        id: number;
        display_name: string;
        is_primary?: boolean;
    }

    interface Props {
        config?: Record<string, any>;
        showSection?: boolean;
        updateConfig?: (patch: Record<string, any>, key?: string) => void;
        onsoundschanged?: () => void;
    }

    let { config = {}, showSection = true, updateConfig, onsoundschanged }: Props = $props();

    let sounds = $state<SoundItem[]>([]);
    let isUploading = $state(false);
    let playingSoundId = $state<number | null>(null);
    let fileInputEl: HTMLInputElement | undefined = $state();

    onMount(() => {
        void loadSounds();
    });

    async function loadSounds() {
        if (!window.api?.get) return;
        try {
            const response = await window.api.get("/api/v1/notification-sounds");
            sounds = response.data ?? [];
        } catch (error) {
            console.error("Failed to load notification sounds:", error);
            sounds = [];
        }
    }

    function onEnabledChange(value: boolean) {
        updateConfig?.({ notification_sound_enabled: value }, "notification_sound_enabled");
    }

    function onVolumeChange(event: Event) {
        const target = event.target as HTMLInputElement;
        const value = Number(target.value);
        updateConfig?.({ notification_sound_volume: value }, "notification_sound_volume");
    }

    function onPreferredChange(event: Event) {
        const target = event.target as HTMLSelectElement;
        const value = Number(target.value);
        updateConfig?.({ notification_sound_preferred_id: value }, "notification_sound_preferred_id");
    }

    async function uploadSound(event: Event) {
        const target = event.target as HTMLInputElement;
        const file = target.files?.[0];
        if (!file) return;

        isUploading = true;
        const formData = new FormData();
        formData.append("file", file);

        try {
            await window.api.post("/api/v1/notification-sounds/upload", formData, {
                headers: {
                    "Content-Type": "multipart/form-data",
                },
            });
            ToastUtils.success(t("app.notification_sound_uploaded"));
            await loadSounds();
            onsoundschanged?.();
        } catch (error: any) {
            console.error(error);
            ToastUtils.error(error.response?.data?.message || t("app.notification_sound_upload_failed"));
        } finally {
            isUploading = false;
            target.value = "";
        }
    }

    async function deleteSound(sound: SoundItem) {
        if (!(await DialogUtils.confirm(t("common.delete_confirm")))) {
            return;
        }
        try {
            await window.api.delete(`/api/v1/notification-sounds/${sound.id}`);
            ToastUtils.success(t("app.notification_sound_deleted"));
            if (playingSoundId === sound.id) {
                NotificationSoundUtils.stop();
                playingSoundId = null;
            }
            await loadSounds();
            onsoundschanged?.();
        } catch (error) {
            console.error(error);
            ToastUtils.error(t("app.notification_sound_delete_failed"));
        }
    }

    async function setPrimarySound(sound: SoundItem) {
        try {
            await window.api.patch(`/api/v1/notification-sounds/${sound.id}`, {
                is_primary: true,
            });
            ToastUtils.success(t("app.notification_sound_primary_set"));
            await loadSounds();
        } catch (error) {
            console.error(error);
            ToastUtils.error(t("app.notification_sound_primary_set_failed"));
        }
    }

    async function previewSound(sound: SoundItem) {
        if (playingSoundId === sound.id) {
            NotificationSoundUtils.stop();
            playingSoundId = null;
            return;
        }

        const played = await NotificationSoundUtils.preview(sound.id, config.notification_sound_volume ?? 100);
        if (played) {
            playingSoundId = sound.id;
            return;
        }
        ToastUtils.warning(t("app.notification_sound_preview_failed"));
    }
</script>

{#if showSection}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">{t("app.notifications")}</div>
                <h2>{t("app.notification_sound_settings")}</h2>
                <p>{t("app.notification_sound_settings_description")}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <div class="rounded-2xl border border-sem-border bg-sem-surface px-3 py-3">
                <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0 flex-1 space-y-1">
                        <div class="text-sm font-semibold text-sem-fg">
                            {t("app.enable_notification_sound")}
                        </div>
                        <p class="text-sm text-sem-fg-muted leading-relaxed">
                            {t("app.enable_notification_sound_description")}
                        </p>
                    </div>
                    <Toggle
                        id="notification-sound-enabled"
                        checked={Boolean(config.notification_sound_enabled)}
                        onchange={onEnabledChange}
                    />
                </div>
            </div>

            {#if config.notification_sound_enabled}
                <div class="space-y-4">
                    <div>
                        <div class="flex items-center justify-between mb-2">
                            <label for="notification-volume-range" class="text-sm font-semibold text-sem-fg-muted">
                                {t("app.notification_sound_volume")}
                            </label>
                            <span class="text-xs font-mono text-sem-fg-muted">{config.notification_sound_volume}%</span>
                        </div>
                        <input
                            id="notification-volume-range"
                            value={config.notification_sound_volume}
                            type="range"
                            min="0"
                            max="100"
                            class="w-full h-1.5 bg-sem-surface-muted rounded-lg appearance-none cursor-pointer accent-blue-600"
                            oninput={onVolumeChange}
                        />
                    </div>

                    <div class="space-y-2">
                        <label for="notification-sound-select" class="text-sm font-semibold text-sem-fg-muted">
                            {t("app.notification_sound_default")}
                        </label>
                        <select
                            id="notification-sound-select"
                            value={config.notification_sound_preferred_id}
                            class="input-field py-1.5! px-3! text-sm! rounded-xl! border-gray-200! dark:border-zinc-800! w-full max-w-md"
                            onchange={onPreferredChange}
                        >
                            <option value={0}>{t("app.notification_sound_primary_default")}</option>
                            {#each sounds as sound (sound.id)}
                                <option value={sound.id}>
                                    {sound.display_name}
                                </option>
                            {/each}
                        </select>
                    </div>

                    <div class="flex items-center justify-between">
                        <span class="text-sm font-semibold text-sem-fg-muted">
                            {t("app.notification_sounds")}
                        </span>
                        <button
                            type="button"
                            class="text-xs font-bold text-sem-accent hover:underline flex items-center gap-1"
                            disabled={isUploading}
                            onclick={() => fileInputEl?.click()}
                        >
                            <MaterialDesignIcon iconName="plus" class="size-4" />
                            {isUploading ? t("app.notification_sound_uploading") : t("app.notification_sound_upload")}
                        </button>
                        <input
                            bind:this={fileInputEl}
                            type="file"
                            accept=".mp3,.ogg,.wav,.m4a,.flac,audio/*"
                            class="hidden"
                            onchange={uploadSound}
                        />
                    </div>

                    {#if sounds.length === 0}
                        <p class="text-sm text-sem-fg-muted">
                            {t("app.notification_sound_none_uploaded")}
                        </p>
                    {:else}
                        <div class="grid gap-3">
                            {#each sounds as sound (sound.id)}
                                <div
                                    class="flex items-center justify-between gap-3 rounded-xl border border-sem-border px-3 py-2"
                                >
                                    <div class="min-w-0 flex-1">
                                        <div class="text-sm font-semibold truncate">{sound.display_name}</div>
                                        {#if sound.is_primary}
                                            <div class="text-xs text-sem-accent">
                                                {t("app.notification_sound_primary")}
                                            </div>
                                        {/if}
                                    </div>
                                    <div class="flex items-center gap-2 shrink-0">
                                        <button
                                            type="button"
                                            class="rounded-lg p-1.5 text-gray-500 hover:bg-sem-surface-muted"
                                            title={t("app.notification_sound_preview")}
                                            onclick={() => previewSound(sound)}
                                        >
                                            <MaterialDesignIcon
                                                iconName={playingSoundId === sound.id ? "stop" : "play"}
                                                class="size-4"
                                            />
                                        </button>
                                        {#if !sound.is_primary}
                                            <button
                                                type="button"
                                                class="rounded-lg px-2 py-1 text-xs font-semibold text-sem-accent hover:bg-blue-50 dark:hover:bg-blue-900/20"
                                                onclick={() => setPrimarySound(sound)}
                                            >
                                                {t("app.notification_sound_set_primary")}
                                            </button>
                                        {/if}
                                        <button
                                            type="button"
                                            class="rounded-lg p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
                                            title={t("app.notification_sound_remove")}
                                            onclick={() => deleteSound(sound)}
                                        >
                                            <MaterialDesignIcon iconName="delete" class="size-4" />
                                        </button>
                                    </div>
                                </div>
                            {/each}
                        </div>
                    {/if}
                </div>
            {/if}
        </div>
    </section>
{/if}
