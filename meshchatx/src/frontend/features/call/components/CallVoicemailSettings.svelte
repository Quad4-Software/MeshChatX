<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import {
        type CallVoicemailSettingsProps,
        type VoicemailConfig,
        type VoicemailTtsField,
        VOICEMAIL_TTS_FIELDS,
        VOICEMAIL_TIMING_FIELDS,
        VOICEMAIL_STYLES,
        getSwitchBgClass,
        getSwitchThumbClass,
        getRecordBtnClass,
    } from "../lib/callVoicemailUi.js";

    let props: CallVoicemailSettingsProps = $props();
    let greetingUploadInput: HTMLInputElement | undefined = $state();

    function handleToggleRecording(): void {
        if (props.voicemailStatus?.is_greeting_recording) {
            props.onstoprecordinggreeting?.();
        } else {
            props.onstartrecordinggreeting?.();
        }
    }

    function handleToggleVoicemailEnabled(): void {
        props.onupdateconfig?.({ voicemail_enabled: !props.config?.voicemail_enabled });
    }

    function handleGreetingInput(event: Event): void {
        const value = (event.target as HTMLTextAreaElement).value;
        props.onpatchconfig?.({ voicemail_greeting: value });
    }

    function handleTtsChange(field: VoicemailTtsField, event: Event): void {
        const raw = (event.target as HTMLInputElement).value;
        const value = field.type === "number" ? Number(raw) : raw;
        props.onupdateconfig?.({ [field.key]: value });
    }

    function handleTimingChange(key: keyof VoicemailConfig, event: Event): void {
        const value = Number((event.target as HTMLInputElement).value);
        props.onupdateconfig?.({ [key]: value });
    }
</script>

<div class="px-4 pb-6 space-y-6">
    {#if !props.voicemailStatus?.has_espeak}
        <div class="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl flex gap-3 items-start">
            <MaterialDesignIcon iconName="alert" class="size-5 text-amber-500 shrink-0" />
            <div class="text-xs text-sem-fg">
                <p class="font-bold mb-1">{t("call.dependencies_missing")}</p>
                <p>{t("call.voicemail_requires_espeak")}</p>
            </div>
        </div>
    {/if}

    <div class="flex items-center justify-between">
        <div>
            <div class="text-sm font-semibold text-sem-fg">{t("call.enable_voicemail")}</div>
            <div class="text-xs text-sem-fg-muted">{t("call.enable_voicemail_description")}</div>
        </div>
        <button
            type="button"
            role="switch"
            aria-label={t("call.enable_voicemail")}
            aria-checked={Boolean(props.config?.voicemail_enabled)}
            disabled={!props.voicemailStatus?.has_espeak}
            class="{VOICEMAIL_STYLES.switchBtn} {getSwitchBgClass(props.config?.voicemail_enabled)}"
            onclick={handleToggleVoicemailEnabled}
        >
            <span class="{VOICEMAIL_STYLES.switchThumb} {getSwitchThumbClass(props.config?.voicemail_enabled)}"></span>
        </button>
    </div>

    <div class="space-y-2">
        <label class={VOICEMAIL_STYLES.label} for="voicemail-greeting-input">{t("call.greeting_message")}</label>
        <textarea
            id="voicemail-greeting-input"
            value={props.config?.voicemail_greeting || ""}
            rows={3}
            class={VOICEMAIL_STYLES.textarea}
            placeholder={t("call.enter_greeting_text")}
            oninput={handleGreetingInput}></textarea>

        <div class="grid grid-cols-2 gap-3 mt-2">
            {#each VOICEMAIL_TTS_FIELDS as field (field.key)}
                <div class="space-y-1">
                    <label class={VOICEMAIL_STYLES.labelMini} for={field.id}>{t(field.labelKey)}</label>
                    <input
                        id={field.id}
                        value={props.config?.[field.key] ?? ""}
                        type={field.type}
                        min={field.min}
                        max={field.max}
                        class={VOICEMAIL_STYLES.inputSm}
                        onchange={(e) => handleTtsChange(field, e)}
                    />
                </div>
            {/each}
        </div>

        <div class="flex justify-between items-center">
            <p class="text-[10px] text-sem-fg-muted">{t("call.greeting_text_description")}</p>
            <button
                type="button"
                disabled={!props.voicemailStatus?.has_espeak || props.isGeneratingGreeting}
                class="text-[10px] bg-sem-surface-muted text-sem-fg-muted px-3 py-1 rounded-full font-bold hover:bg-sem-surface-subtle transition-colors disabled:opacity-50 focus-ring-sem cursor-pointer"
                onclick={() => props.onsaveandgenerate?.()}
            >
                {props.isGeneratingGreeting ? t("call.generating") : t("call.save_and_generate")}
            </button>
        </div>
    </div>

    <div class="space-y-2">
        <span class="block {VOICEMAIL_STYLES.label}">{t("call.custom_audio_greeting")}</span>
        <div class="flex items-center gap-3 flex-wrap">
            <input
                bind:this={greetingUploadInput}
                type="file"
                accept="audio/*"
                class="hidden"
                onchange={(e) => {
                    const file = (e.target as HTMLInputElement).files?.[0];
                    if (file) props.onuploadgreeting?.(e, file);
                }}
            />
            <button
                type="button"
                disabled={props.isUploadingGreeting || Boolean(props.voicemailStatus?.is_greeting_recording)}
                class={VOICEMAIL_STYLES.greetingUploadBtn}
                onclick={() => greetingUploadInput?.click()}
            >
                <MaterialDesignIcon iconName="upload" class="size-4" />
                {props.isUploadingGreeting ? t("call.uploading") : t("call.upload_audio_file")}
            </button>
            <button
                type="button"
                class="text-xs px-4 py-2 rounded-xl font-bold transition-colors flex items-center gap-2 focus-ring-sem cursor-pointer {getRecordBtnClass(
                    props.voicemailStatus?.is_greeting_recording
                )}"
                onclick={handleToggleRecording}
            >
                <MaterialDesignIcon
                    iconName={props.voicemailStatus?.is_greeting_recording ? "stop" : "microphone"}
                    class="size-4"
                />
                {props.voicemailStatus?.is_greeting_recording ? t("call.stop_recording") : t("call.record_from_mic")}
            </button>

            {#if props.voicemailStatus?.has_greeting}
                <div class="flex items-center gap-2">
                    <button
                        type="button"
                        class={VOICEMAIL_STYLES.greetingDeleteBtn}
                        onclick={() => props.ondeletegreeting?.()}
                    >
                        <MaterialDesignIcon iconName="delete" class="size-4" />
                        {t("call.remove_greeting")}
                    </button>
                    <button
                        type="button"
                        class={VOICEMAIL_STYLES.greetingPlayBtn}
                        onclick={() => props.onplaygreeting?.()}
                    >
                        <MaterialDesignIcon iconName={props.isPlayingGreeting ? "stop" : "play"} class="size-4" />
                        {props.isPlayingGreeting ? t("call.stop_preview") : t("call.preview")}
                    </button>
                </div>
            {:else}
                <div class="text-[10px] text-sem-fg-muted italic">
                    {t("call.no_custom_greeting_uploaded")}
                </div>
            {/if}
        </div>
        <p class="text-[10px] text-sem-fg-muted">Supports MP3, OGG, WAV, M4A, FLAC. Will be converted to Opus.</p>
    </div>

    <div class="grid grid-cols-2 gap-4">
        {#each VOICEMAIL_TIMING_FIELDS as field (field.key)}
            <div class="space-y-2">
                <label class={VOICEMAIL_STYLES.label} for={field.id}>{t(field.labelKey)}</label>
                <input
                    id={field.id}
                    value={props.config?.[field.key] ?? ""}
                    type="number"
                    min={field.min}
                    max={field.max}
                    class={VOICEMAIL_STYLES.inputLg}
                    onchange={(e) => handleTimingChange(field.key, e)}
                />
            </div>
        {/each}
    </div>
</div>
