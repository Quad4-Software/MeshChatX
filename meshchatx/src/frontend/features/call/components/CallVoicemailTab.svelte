<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../ui/svelte/LxmfUserIcon.svelte";
    import AudioWaveformPlayer from "../../messages/components/AudioWaveformPlayer.svelte";
    import { t } from "../../../js/i18n.js";
    import {
        type VoicemailItem,
        type VoicemailConfig,
        type VoicemailStatusState,
        type ContactLookupResult,
        resolveCallbackHash,
        getVoicemailAudioSrc,
        getVoicemailDownloadFileName,
    } from "../lib/callVoicemailUi.js";

    interface Props {
        active?: boolean;
        voicemailSearch?: string;
        config?: VoicemailConfig | null;
        voicemailStatus?: VoicemailStatusState;
        voicemails?: VoicemailItem[];
        isGeneratingGreeting?: boolean;
        isUploadingGreeting?: boolean;
        isPlayingGreeting?: boolean;
        getContactByHash?: (hash: string) => ContactLookupResult | undefined;
        formatDateTime?: (timestamp: number) => string;
        formatDuration?: (seconds?: number) => string;
        formatDestinationHash?: (hash?: string) => string;
        onsearchinput?: (value: string) => void;
        onupdateconfig?: (patch: Partial<VoicemailConfig>) => void;
        onpatchconfig?: (patch: Partial<VoicemailConfig>) => void;
        onsaveandgenerate?: () => void;
        onuploadgreeting?: (event: Event) => void;
        onstartrecordinggreeting?: () => void;
        onstoprecordinggreeting?: () => void;
        ondeletegreeting?: () => void;
        onplaygreeting?: () => void;
        oncopyhash?: (hash: string) => void;
        onmarkread?: (voicemail: VoicemailItem) => void;
        oncallback?: (destination: string) => void;
        ondelete?: (id: number | string) => void;
    }

    let {
        active = false,
        voicemailSearch = "",
        config = null,
        voicemailStatus = {},
        voicemails = [],
        isGeneratingGreeting = false,
        isUploadingGreeting = false,
        isPlayingGreeting = false,
        getContactByHash = () => undefined,
        formatDateTime = (ts) => String(ts),
        formatDuration = (s = 0) => String(s),
        formatDestinationHash = (h = "") => h,
        onsearchinput,
        onupdateconfig,
        onpatchconfig,
        onsaveandgenerate,
        onuploadgreeting,
        onstartrecordinggreeting,
        onstoprecordinggreeting,
        ondeletegreeting,
        onplaygreeting,
        oncopyhash,
        onmarkread,
        oncallback,
        ondelete,
    }: Props = $props();

    let isVoicemailSettingsExpanded = $state(false);
    let greetingUploadInput: HTMLInputElement | undefined = $state();

    function handleSearchInput(event: Event): void {
        const value = (event.target as HTMLInputElement).value;
        onsearchinput?.(value);
    }
</script>

{#if active}
    <div class="flex-1 flex flex-col max-w-3xl mx-auto w-full pt-2">
        <div class="mb-4">
            <div class="relative">
                <input
                    value={voicemailSearch}
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

        {#if config}
            <div class="mb-4 border-b border-sem-border overflow-hidden">
                <button
                    type="button"
                    class="w-full px-4 py-3 flex items-center justify-between hover:bg-sem-surface-muted/50 transition-colors"
                    onclick={() => (isVoicemailSettingsExpanded = !isVoicemailSettingsExpanded)}
                >
                    <div class="flex items-center gap-2">
                        <MaterialDesignIcon iconName="cog" class="size-5 text-blue-500" />
                        <h3 class="text-sm font-bold text-sem-fg uppercase tracking-wider">{t("call.voicemail_settings")}</h3>
                    </div>
                    <MaterialDesignIcon iconName={isVoicemailSettingsExpanded ? "chevron-up" : "chevron-down"} class="size-5 text-gray-400" />
                </button>

                {#if isVoicemailSettingsExpanded}
                    <div class="px-4 pb-6 space-y-6">
                        {#if !voicemailStatus.has_espeak}
                            <div class="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg flex gap-3 items-start">
                                <MaterialDesignIcon iconName="alert" class="size-5 text-amber-600 dark:text-amber-400 shrink-0" />
                                <div class="text-xs text-amber-800 dark:text-amber-200">
                                    <p class="font-bold mb-1">Dependencies Missing</p>
                                    <p>Voicemail requires espeak-ng to generate greetings. Please install it on your system.</p>
                                </div>
                            </div>
                        {/if}

                        <div class="flex items-center justify-between">
                            <div>
                                <div class="text-sm font-semibold text-sem-fg">Enable Voicemail</div>
                                <div class="text-xs text-sem-fg-muted">Accept calls automatically and record messages</div>
                            </div>
                            <button
                                type="button"
                                role="switch"
                                aria-label={t("call.enable_voicemail")}
                                aria-checked={Boolean(config.voicemail_enabled)}
                                disabled={!voicemailStatus.has_espeak}
                                class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden disabled:opacity-50 disabled:cursor-not-allowed {config.voicemail_enabled ? 'bg-blue-600' : 'bg-gray-200 dark:bg-zinc-700'}"
                                onclick={() => onupdateconfig?.({ voicemail_enabled: !config.voicemail_enabled })}
                            >
                                <span class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out {config.voicemail_enabled ? 'translate-x-5' : 'translate-x-0'}"></span>
                            </button>
                        </div>

                        <div class="space-y-2">
                            <label class="text-xs font-bold text-sem-fg-muted uppercase tracking-tighter" for="voicemail-greeting-input">Greeting Message</label>
                            <textarea
                                id="voicemail-greeting-input"
                                value={config.voicemail_greeting || ""}
                                rows={3}
                                class="block w-full rounded-lg border-0 py-2 text-sem-fg shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm sm:leading-6 dark:bg-zinc-900"
                                placeholder={t("call.enter_greeting_text")}
                                oninput={(e) => onpatchconfig?.({ voicemail_greeting: (e.target as HTMLTextAreaElement).value })}
                            ></textarea>

                            <div class="grid grid-cols-2 gap-3 mt-2">
                                <div class="space-y-1">
                                    <label class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-tighter" for="voicemail-tts-speed">{t("call.tts_speed")}</label>
                                    <input
                                        id="voicemail-tts-speed"
                                        value={config.voicemail_tts_speed ?? ""}
                                        type="number"
                                        min="80"
                                        max="450"
                                        class="block w-full rounded-lg border-0 py-1 text-sem-fg shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-blue-600 text-xs dark:bg-zinc-900"
                                        onchange={(e) => onupdateconfig?.({ voicemail_tts_speed: Number((e.target as HTMLInputElement).value) })}
                                    />
                                </div>
                                <div class="space-y-1">
                                    <label class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-tighter" for="voicemail-tts-pitch">{t("call.tts_pitch")}</label>
                                    <input
                                        id="voicemail-tts-pitch"
                                        value={config.voicemail_tts_pitch ?? ""}
                                        type="number"
                                        min="0"
                                        max="99"
                                        class="block w-full rounded-lg border-0 py-1 text-sem-fg shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-blue-600 text-xs dark:bg-zinc-900"
                                        onchange={(e) => onupdateconfig?.({ voicemail_tts_pitch: Number((e.target as HTMLInputElement).value) })}
                                    />
                                </div>
                                <div class="space-y-1">
                                    <label class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-tighter" for="voicemail-tts-gap">{t("call.tts_word_gap")}</label>
                                    <input
                                        id="voicemail-tts-gap"
                                        value={config.voicemail_tts_word_gap ?? ""}
                                        type="number"
                                        min="0"
                                        max="100"
                                        class="block w-full rounded-lg border-0 py-1 text-sem-fg shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-blue-600 text-xs dark:bg-zinc-900"
                                        onchange={(e) => onupdateconfig?.({ voicemail_tts_word_gap: Number((e.target as HTMLInputElement).value) })}
                                    />
                                </div>
                                <div class="space-y-1">
                                    <label class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-tighter" for="voicemail-tts-voice">{t("call.tts_voice")}</label>
                                    <input
                                        id="voicemail-tts-voice"
                                        value={config.voicemail_tts_voice ?? ""}
                                        type="text"
                                        class="block w-full rounded-lg border-0 py-1 text-sem-fg shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-blue-600 text-xs dark:bg-zinc-900"
                                        onchange={(e) => onupdateconfig?.({ voicemail_tts_voice: (e.target as HTMLInputElement).value })}
                                    />
                                </div>
                            </div>

                            <div class="flex justify-between items-center">
                                <p class="text-[10px] text-sem-fg-muted">This text will be converted to speech using eSpeak NG.</p>
                                <div class="flex gap-2">
                                    <button
                                        type="button"
                                        disabled={!voicemailStatus.has_espeak || isGeneratingGreeting}
                                        class="text-[10px] bg-sem-surface-muted text-sem-fg-muted px-3 py-1 rounded-full font-bold hover:bg-gray-200 transition-colors disabled:opacity-50"
                                        onclick={() => onsaveandgenerate?.()}
                                    >
                                        {isGeneratingGreeting ? "Generating..." : "Save & Generate"}
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div class="space-y-2">
                            <span class="block text-xs font-bold text-sem-fg-muted uppercase tracking-tighter">Custom Audio Greeting</span>
                            <div class="flex items-center gap-3 flex-wrap">
                                <input
                                    bind:this={greetingUploadInput}
                                    type="file"
                                    accept="audio/*"
                                    class="hidden"
                                    onchange={(e) => onuploadgreeting?.(e)}
                                />
                                <button
                                    type="button"
                                    disabled={isUploadingGreeting || Boolean(voicemailStatus.is_greeting_recording)}
                                    class="text-xs bg-sem-surface-muted text-sem-fg-muted px-4 py-2 rounded-lg font-bold hover:bg-gray-200 transition-colors disabled:opacity-50 flex items-center gap-2"
                                    onclick={() => greetingUploadInput?.click()}
                                >
                                    <MaterialDesignIcon iconName="upload" class="size-4" />
                                    {isUploadingGreeting ? "Uploading..." : "Upload Audio File"}
                                </button>
                                <button
                                    type="button"
                                    class="text-xs px-4 py-2 rounded-lg font-bold transition-colors flex items-center gap-2 {voicemailStatus.is_greeting_recording ? 'bg-red-500 text-white animate-pulse' : 'bg-sem-surface-muted text-sem-fg-muted hover:bg-gray-200'}"
                                    onclick={() => voicemailStatus.is_greeting_recording ? onstoprecordinggreeting?.() : onstartrecordinggreeting?.()}
                                >
                                    <MaterialDesignIcon iconName={voicemailStatus.is_greeting_recording ? "stop" : "microphone"} class="size-4" />
                                    {voicemailStatus.is_greeting_recording ? "Stop Recording" : "Record from Mic"}
                                </button>

                                {#if voicemailStatus.has_greeting}
                                    <div class="flex items-center gap-2">
                                        <button
                                            type="button"
                                            class="text-xs bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 px-4 py-2 rounded-lg font-bold hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors flex items-center gap-2"
                                            onclick={() => ondeletegreeting?.()}
                                        >
                                            <MaterialDesignIcon iconName="delete" class="size-4" />
                                            Remove Greeting
                                        </button>
                                        <button
                                            type="button"
                                            class="text-xs bg-blue-100 dark:bg-blue-900/30 text-sem-accent px-4 py-2 rounded-lg font-bold hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors flex items-center gap-2"
                                            onclick={() => onplaygreeting?.()}
                                        >
                                            <MaterialDesignIcon iconName={isPlayingGreeting ? "stop" : "play"} class="size-4" />
                                            {isPlayingGreeting ? "Stop Preview" : "Preview"}
                                        </button>
                                    </div>
                                {:else}
                                    <div class="text-[10px] text-sem-fg-muted italic">
                                        No custom greeting uploaded (default text will be used)
                                    </div>
                                {/if}
                            </div>
                            <p class="text-[10px] text-sem-fg-muted">Supports MP3, OGG, WAV, M4A, FLAC. Will be converted to Opus.</p>
                        </div>

                        <div class="grid grid-cols-2 gap-4">
                            <div class="space-y-2">
                                <label class="text-xs font-bold text-sem-fg-muted uppercase tracking-tighter" for="voicemail-answer-delay">Answer Delay (s)</label>
                                <input
                                    id="voicemail-answer-delay"
                                    value={config.voicemail_auto_answer_delay_seconds ?? ""}
                                    type="number"
                                    min="1"
                                    max="120"
                                    class="block w-full rounded-lg border-0 py-1.5 text-sem-fg shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
                                    onchange={(e) => onupdateconfig?.({ voicemail_auto_answer_delay_seconds: Number((e.target as HTMLInputElement).value) })}
                                />
                            </div>
                            <div class="space-y-2">
                                <label class="text-xs font-bold text-sem-fg-muted uppercase tracking-tighter" for="voicemail-max-rec">Max Recording (s)</label>
                                <input
                                    id="voicemail-max-rec"
                                    value={config.voicemail_max_recording_seconds ?? ""}
                                    type="number"
                                    min="5"
                                    max="600"
                                    class="block w-full rounded-lg border-0 py-1.5 text-sem-fg shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
                                    onchange={(e) => onupdateconfig?.({ voicemail_max_recording_seconds: Number((e.target as HTMLInputElement).value) })}
                                />
                            </div>
                        </div>
                    </div>
                {/if}
            </div>
        {/if}

        {#if voicemails.length === 0}
            <div class="my-auto text-center py-12">
                <div class="bg-gray-200 dark:bg-zinc-800 p-6 rounded-full inline-block mb-4">
                    <MaterialDesignIcon iconName="voicemail" class="size-12 text-gray-400" />
                </div>
                <h3 class="text-lg font-medium text-sem-fg">No Voicemails</h3>
                <p class="text-sem-fg-muted text-sm">When people leave you messages, they'll show up here.</p>
            </div>
        {:else}
            <div class="space-y-4">
                <div class="border-b border-sem-border overflow-hidden">
                    <div class="px-4 py-3 border-b border-sem-border flex justify-between items-center">
                        <h3 class="text-sm font-bold text-sem-fg uppercase tracking-wider">Voicemail Inbox</h3>
                        <span class="text-[10px] bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 px-2 py-0.5 rounded-full font-bold uppercase">
                            {voicemails.length} Messages
                        </span>
                    </div>
                    <ul class="divide-y divide-gray-100 dark:divide-zinc-800">
                        {#each voicemails as voicemail (voicemail.id)}
                            <li class="px-4 py-4 hover:bg-sem-surface-muted/50 transition-colors {voicemail.is_read ? '' : 'bg-blue-50/50 dark:bg-blue-900/10'}">
                                <div class="flex items-start space-x-4">
                                    <div class="relative shrink-0">
                                        <LxmfUserIcon
                                            customImage={getContactByHash(voicemail.remote_identity_hash || "")?.custom_image || undefined}
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
                                                    <span class="ml-2 shrink-0 size-2 inline-block rounded-full bg-blue-500"></span>
                                                {/if}
                                            </div>
                                            <span class="text-[10px] text-sem-fg-muted font-mono shrink-0">
                                                {formatDateTime(Number(voicemail.timestamp || 0) * 1000)}
                                            </span>
                                        </div>

                                        <div class="flex items-center text-xs text-sem-fg-muted space-x-3 mb-3">
                                            <span class="flex items-center gap-1">
                                                <MaterialDesignIcon iconName="clock-outline" class="size-3" />
                                                {formatDuration(voicemail.duration_seconds ?? voicemail.duration)}
                                            </span>
                                            <button
                                                type="button"
                                                class="opacity-60 font-mono text-[10px] text-left truncate cursor-pointer hover:text-blue-500 transition-colors"
                                                title={voicemail.remote_identity_hash}
                                                onclick={(e) => {
                                                    e.stopPropagation();
                                                    oncopyhash?.(voicemail.remote_identity_hash || "");
                                                }}
                                            >
                                                {formatDestinationHash(voicemail.remote_identity_hash)}
                                            </button>
                                        </div>

                                        <div class="mb-4">
                                            <AudioWaveformPlayer
                                                src={getVoicemailAudioSrc(voicemail.id)}
                                                onplay={() => onmarkread?.(voicemail)}
                                            />
                                        </div>

                                        <div class="flex items-center gap-4">
                                            <button
                                                type="button"
                                                class="text-[10px] flex items-center gap-1 text-gray-500 hover:text-blue-500 font-bold uppercase tracking-wider transition-colors"
                                                onclick={() => oncallback?.(resolveCallbackHash(voicemail))}
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
                                                onclick={() => ondelete?.(voicemail.id)}
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
