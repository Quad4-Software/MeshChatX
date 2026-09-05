<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../ui/svelte/LxmfUserIcon.svelte";
    import EmptyState from "../../../ui/svelte/EmptyState.svelte";
    import AudioWaveformPlayer from "../../messages/components/AudioWaveformPlayer.svelte";
    import { t } from "../../../js/i18n.js";
    import {
        type CallVoicemailTabProps,
        VOICEMAIL_TTS_FIELDS,
        VOICEMAIL_TIMING_FIELDS,
        resolveCallbackHash,
        getVoicemailAudioSrc,
        getVoicemailDownloadFileName,
        formatVoicemailTimestamp,
        formatVoicemailDuration,
        formatVoicemailHash,
    } from "../lib/callVoicemailUi.js";

    let props: CallVoicemailTabProps = $props();

    let isVoicemailSettingsExpanded = $state(false);
    let greetingUploadInput: HTMLInputElement | undefined = $state();

    function handleSearchInput(event: Event): void {
        const value = (event.target as HTMLInputElement).value;
        props.onsearchinput?.(value);
    }
</script>

{#if props.active}
    <div class="flex-1 flex flex-col max-w-3xl mx-auto w-full pt-2">
        <div class="mb-4">
            <div class="relative">
                <input
                    value={props.voicemailSearch ?? ""}
                    type="text"
                    placeholder={t("call.search_voicemails")}
                    class="block w-full rounded-lg border-0 py-2 pl-10 text-sem-fg shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
                    oninput={handleSearchInput}
                />
                <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                    <MaterialDesignIcon iconName="magnify" class="size-5 text-gray-400" />
                </div>
            </div>
        </div>

        {#if props.config}
            <div class="mb-4 border-b border-sem-border overflow-hidden">
                <button
                    type="button"
                    class="w-full px-4 py-3 flex items-center justify-between hover:bg-sem-surface-muted/50 transition-colors"
                    onclick={() => (isVoicemailSettingsExpanded = !isVoicemailSettingsExpanded)}
                >
                    <div class="flex items-center gap-2">
                        <MaterialDesignIcon iconName="cog" class="size-5 text-blue-500" />
                        <h3 class="text-sm font-bold text-sem-fg uppercase tracking-wider">
                            {t("call.voicemail_settings")}
                        </h3>
                    </div>
                    <MaterialDesignIcon
                        iconName={isVoicemailSettingsExpanded ? "chevron-up" : "chevron-down"}
                        class="size-5 text-gray-400"
                    />
                </button>

                {#if isVoicemailSettingsExpanded}
                    <div class="px-4 pb-6 space-y-6">
                        {#if !props.voicemailStatus?.has_espeak}
                            <div
                                class="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg flex gap-3 items-start"
                            >
                                <MaterialDesignIcon
                                    iconName="alert"
                                    class="size-5 text-amber-600 dark:text-amber-400 shrink-0"
                                />
                                <div class="text-xs text-amber-800 dark:text-amber-200">
                                    <p class="font-bold mb-1">Dependencies Missing</p>
                                    <p>
                                        Voicemail requires espeak-ng to generate greetings. Please install it on your
                                        system.
                                    </p>
                                </div>
                            </div>
                        {/if}

                        <div class="flex items-center justify-between">
                            <div>
                                <div class="text-sm font-semibold text-sem-fg">Enable Voicemail</div>
                                <div class="text-xs text-sem-fg-muted">
                                    Accept calls automatically and record messages
                                </div>
                            </div>
                            <button
                                type="button"
                                role="switch"
                                aria-label="Enable Voicemail"
                                aria-checked={Boolean(props.config.voicemail_enabled)}
                                disabled={!props.voicemailStatus?.has_espeak}
                                class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden disabled:opacity-50 disabled:cursor-not-allowed {props
                                    .config.voicemail_enabled
                                    ? 'bg-blue-600'
                                    : 'bg-gray-200 dark:bg-zinc-700'}"
                                onclick={() =>
                                    props.onupdateconfig?.({
                                        voicemail_enabled: !props.config?.voicemail_enabled,
                                    })}
                            >
                                <span
                                    class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out {props
                                        .config.voicemail_enabled
                                        ? 'translate-x-5'
                                        : 'translate-x-0'}"
                                ></span>
                            </button>
                        </div>

                        <div class="space-y-2">
                            <label
                                class="text-xs font-bold text-sem-fg-muted uppercase tracking-tighter"
                                for="voicemail-greeting-input">Greeting Message</label
                            >
                            <textarea
                                id="voicemail-greeting-input"
                                value={props.config.voicemail_greeting || ""}
                                rows={3}
                                class="block w-full rounded-lg border-0 py-2 text-sem-fg shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm sm:leading-6 dark:bg-zinc-900"
                                placeholder={t("call.enter_greeting_text")}
                                oninput={(e) =>
                                    props.onpatchconfig?.({
                                        voicemail_greeting: (e.target as HTMLTextAreaElement).value,
                                    })}></textarea>

                            <div class="grid grid-cols-2 gap-3 mt-2">
                                {#each VOICEMAIL_TTS_FIELDS as field (field.key)}
                                    <div class="space-y-1">
                                        <label
                                            class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-tighter"
                                            for={field.id}>{t(field.labelKey)}</label
                                        >
                                        <input
                                            id={field.id}
                                            value={props.config?.[field.key] ?? ""}
                                            type={field.type}
                                            min={field.min}
                                            max={field.max}
                                            class="block w-full rounded-lg border-0 py-1 text-sem-fg shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-blue-600 text-xs dark:bg-zinc-900"
                                            onchange={(e) =>
                                                props.onupdateconfig?.({
                                                    [field.key]:
                                                        field.type === "number"
                                                            ? Number((e.target as HTMLInputElement).value)
                                                            : (e.target as HTMLInputElement).value,
                                                })}
                                        />
                                    </div>
                                {/each}
                            </div>

                            <div class="flex justify-between items-center">
                                <p class="text-[10px] text-sem-fg-muted">
                                    This text will be converted to speech using eSpeak NG.
                                </p>
                                <div class="flex gap-2">
                                    <button
                                        type="button"
                                        disabled={!props.voicemailStatus?.has_espeak || props.isGeneratingGreeting}
                                        class="text-[10px] bg-sem-surface-muted text-sem-fg-muted px-3 py-1 rounded-full font-bold hover:bg-gray-200 transition-colors disabled:opacity-50"
                                        onclick={() => props.onsaveandgenerate?.()}
                                    >
                                        {props.isGeneratingGreeting ? "Generating..." : "Save & Generate"}
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div class="space-y-2">
                            <span class="block text-xs font-bold text-sem-fg-muted uppercase tracking-tighter"
                                >Custom Audio Greeting</span
                            >
                            <div class="flex items-center gap-3 flex-wrap">
                                <input
                                    bind:this={greetingUploadInput}
                                    type="file"
                                    accept="audio/*"
                                    class="hidden"
                                    onchange={(e) => props.onuploadgreeting?.(e)}
                                />
                                <button
                                    type="button"
                                    disabled={props.isUploadingGreeting ||
                                        Boolean(props.voicemailStatus?.is_greeting_recording)}
                                    class="text-xs bg-sem-surface-muted text-sem-fg-muted px-4 py-2 rounded-lg font-bold hover:bg-gray-200 transition-colors disabled:opacity-50 flex items-center gap-2"
                                    onclick={() => greetingUploadInput?.click()}
                                >
                                    <MaterialDesignIcon iconName="upload" class="size-4" />
                                    {props.isUploadingGreeting ? "Uploading..." : "Upload Audio File"}
                                </button>
                                <button
                                    type="button"
                                    class="text-xs px-4 py-2 rounded-lg font-bold transition-colors flex items-center gap-2 {props
                                        .voicemailStatus?.is_greeting_recording
                                        ? 'bg-red-500 text-white animate-pulse'
                                        : 'bg-sem-surface-muted text-sem-fg-muted hover:bg-gray-200'}"
                                    onclick={() =>
                                        props.voicemailStatus?.is_greeting_recording
                                            ? props.onstoprecordinggreeting?.()
                                            : props.onstartrecordinggreeting?.()}
                                >
                                    <MaterialDesignIcon
                                        iconName={props.voicemailStatus?.is_greeting_recording ? "stop" : "microphone"}
                                        class="size-4"
                                    />
                                    {props.voicemailStatus?.is_greeting_recording
                                        ? "Stop Recording"
                                        : "Record from Mic"}
                                </button>

                                {#if props.voicemailStatus?.has_greeting}
                                    <div class="flex items-center gap-2">
                                        <button
                                            type="button"
                                            class="text-xs bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 px-4 py-2 rounded-lg font-bold hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors flex items-center gap-2"
                                            onclick={() => props.ondeletegreeting?.()}
                                        >
                                            <MaterialDesignIcon iconName="delete" class="size-4" />
                                            Remove Greeting
                                        </button>
                                        <button
                                            type="button"
                                            class="text-xs bg-blue-100 dark:bg-blue-900/30 text-sem-accent px-4 py-2 rounded-lg font-bold hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors flex items-center gap-2"
                                            onclick={() => props.onplaygreeting?.()}
                                        >
                                            <MaterialDesignIcon
                                                iconName={props.isPlayingGreeting ? "stop" : "play"}
                                                class="size-4"
                                            />
                                            {props.isPlayingGreeting ? "Stop Preview" : "Preview"}
                                        </button>
                                    </div>
                                {:else}
                                    <div class="text-[10px] text-sem-fg-muted italic">
                                        No custom greeting uploaded (default text will be used)
                                    </div>
                                {/if}
                            </div>
                            <p class="text-[10px] text-sem-fg-muted">
                                Supports MP3, OGG, WAV, M4A, FLAC. Will be converted to Opus.
                            </p>
                        </div>

                        <div class="grid grid-cols-2 gap-4">
                            {#each VOICEMAIL_TIMING_FIELDS as field (field.key)}
                                <div class="space-y-2">
                                    <label
                                        class="text-xs font-bold text-sem-fg-muted uppercase tracking-tighter"
                                        for={field.id}>{field.label}</label
                                    >
                                    <input
                                        id={field.id}
                                        value={props.config?.[field.key] ?? ""}
                                        type="number"
                                        min={field.min}
                                        max={field.max}
                                        class="block w-full rounded-lg border-0 py-1.5 text-sem-fg shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
                                        onchange={(e) =>
                                            props.onupdateconfig?.({
                                                [field.key]: Number((e.target as HTMLInputElement).value),
                                            })}
                                    />
                                </div>
                            {/each}
                        </div>
                    </div>
                {/if}
            </div>
        {/if}

        {#if !props.voicemails || props.voicemails.length === 0}
            <EmptyState
                icon="voicemail"
                title="No Voicemails"
                description="When people leave you messages, they'll show up here."
                class="my-auto py-12"
            />
        {:else}
            <div class="space-y-4">
                <div class="border-b border-sem-border overflow-hidden">
                    <div class="px-4 py-3 border-b border-sem-border flex justify-between items-center">
                        <h3 class="text-sm font-bold text-sem-fg uppercase tracking-wider">Voicemail Inbox</h3>
                        <span
                            class="text-[10px] bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 px-2 py-0.5 rounded-full font-bold uppercase"
                        >
                            {props.voicemails.length} Messages
                        </span>
                    </div>
                    <ul class="divide-y divide-gray-100 dark:divide-zinc-800">
                        {#each props.voicemails as voicemail (voicemail.id)}
                            <li
                                class="px-4 py-4 hover:bg-sem-surface-muted/50 transition-colors {voicemail.is_read
                                    ? ''
                                    : 'bg-blue-50/50 dark:bg-blue-900/10'}"
                            >
                                <div class="flex items-start space-x-4">
                                    <div class="relative shrink-0">
                                        <LxmfUserIcon
                                            customImage={props.getContactByHash?.(voicemail.remote_identity_hash || "")
                                                ?.custom_image || undefined}
                                            iconName={voicemail.remote_icon?.icon_name || ""}
                                            iconForegroundColour={voicemail.remote_icon?.foreground_colour || ""}
                                            iconBackgroundColour={voicemail.remote_icon?.background_colour || ""}
                                            iconClass="size-10"
                                        />
                                    </div>

                                    <div class="flex-1 min-w-0">
                                        <div class="flex items-center justify-between mb-1">
                                            <div class="flex items-center min-w-0 mr-2">
                                                <p class="text-sm font-bold text-sem-fg truncate">
                                                    {voicemail.remote_identity_name || t("call.unknown")}
                                                </p>
                                                {#if !voicemail.is_read}
                                                    <span
                                                        class="ml-2 shrink-0 size-2 inline-block rounded-full bg-blue-500"
                                                    ></span>
                                                {/if}
                                            </div>
                                            <span class="text-[10px] text-sem-fg-muted font-mono shrink-0">
                                                {formatVoicemailTimestamp(voicemail.timestamp, props.formatDateTime)}
                                            </span>
                                        </div>

                                        <div class="flex items-center text-xs text-sem-fg-muted space-x-3 mb-3">
                                            <span class="flex items-center gap-1">
                                                <MaterialDesignIcon iconName="clock-outline" class="size-3" />
                                                {formatVoicemailDuration(voicemail, props.formatDuration)}
                                            </span>
                                            <button
                                                type="button"
                                                class="opacity-60 font-mono text-[10px] text-left truncate cursor-pointer hover:text-blue-500 transition-colors"
                                                title={voicemail.remote_identity_hash}
                                                onclick={(e) => {
                                                    e.stopPropagation();
                                                    props.oncopyhash?.(voicemail.remote_identity_hash || "");
                                                }}
                                            >
                                                {formatVoicemailHash(
                                                    voicemail.remote_identity_hash,
                                                    props.formatDestinationHash
                                                )}
                                            </button>
                                        </div>

                                        <div class="mb-4">
                                            <AudioWaveformPlayer
                                                src={getVoicemailAudioSrc(voicemail.id)}
                                                onplay={() => props.onmarkread?.(voicemail)}
                                            />
                                        </div>

                                        <div class="flex items-center gap-4">
                                            <button
                                                type="button"
                                                class="text-[10px] flex items-center gap-1 text-gray-500 hover:text-blue-500 font-bold uppercase tracking-wider transition-colors"
                                                onclick={() => props.oncallback?.(resolveCallbackHash(voicemail))}
                                            >
                                                <MaterialDesignIcon iconName="phone" class="size-3" />
                                                Call Back
                                            </button>
                                            <a
                                                href={getVoicemailAudioSrc(voicemail.id)}
                                                download={getVoicemailDownloadFileName(voicemail.id)}
                                                class="text-[10px] flex items-center gap-1 text-gray-500 hover:text-blue-500 font-bold uppercase tracking-wider transition-colors"
                                            >
                                                <MaterialDesignIcon iconName="download" class="size-3" />
                                                Download
                                            </a>
                                            <button
                                                type="button"
                                                class="text-[10px] flex items-center gap-1 text-red-500 hover:text-red-600 font-bold uppercase tracking-wider transition-colors"
                                                onclick={() => props.ondelete?.(voicemail.id)}
                                            >
                                                <MaterialDesignIcon iconName="delete" class="size-3" />
                                                Delete
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </li>
                        {/each}
                    </ul>
                </div>
            </div>
        {/if}
    </div>
{/if}
