<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div v-if="active" class="flex-1 flex flex-col max-w-3xl mx-auto w-full pt-2">
        <div class="mb-4">
            <div class="relative">
                <input
                    :value="voicemailSearch"
                    type="text"
                    :placeholder="$t('call.search_voicemails')"
                    class="block w-full rounded-lg border-0 py-2 pl-10 text-gray-900 dark:text-white shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
                    @input="onSearchInput"
                />
                <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                    <MaterialDesignIcon icon-name="magnify" class="size-5 text-gray-400" />
                </div>
            </div>
        </div>

        <!-- Voicemail Settings Card -->
        <div v-if="config" class="mb-4 border-b border-gray-200 dark:border-zinc-800 overflow-hidden">
            <button
                type="button"
                class="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-zinc-800/50 transition-colors"
                @click="isVoicemailSettingsExpanded = !isVoicemailSettingsExpanded"
            >
                <div class="flex items-center gap-2">
                    <MaterialDesignIcon icon-name="cog" class="size-5 text-blue-500" />
                    <h3 class="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider">
                        {{ $t("call.voicemail_settings") }}
                    </h3>
                </div>
                <MaterialDesignIcon
                    :icon-name="isVoicemailSettingsExpanded ? 'chevron-up' : 'chevron-down'"
                    class="size-5 text-gray-400"
                />
            </button>

            <div v-if="isVoicemailSettingsExpanded" class="px-4 pb-6 space-y-6">
                <!-- Status Banner -->
                <div
                    v-if="!voicemailStatus.has_espeak"
                    class="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg flex gap-3 items-start"
                >
                    <MaterialDesignIcon icon-name="alert" class="size-5 text-amber-600 dark:text-amber-400 shrink-0" />
                    <div class="text-xs text-amber-800 dark:text-amber-200">
                        <p class="font-bold mb-1">Dependencies Missing</p>
                        <p>Voicemail requires `espeak-ng` to generate greetings. Please install it on your system.</p>
                    </div>
                </div>

                <!-- Enabled Toggle -->
                <div class="flex items-center justify-between">
                    <div>
                        <div class="text-sm font-semibold text-gray-900 dark:text-white">Enable Voicemail</div>
                        <div class="text-xs text-gray-500 dark:text-zinc-400">
                            Accept calls automatically and record messages
                        </div>
                    </div>
                    <button
                        :disabled="!voicemailStatus.has_espeak"
                        class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden disabled:opacity-50 disabled:cursor-not-allowed"
                        :class="config.voicemail_enabled ? 'bg-blue-600' : 'bg-gray-200 dark:bg-zinc-700'"
                        @click="$emit('update-config', { voicemail_enabled: !config.voicemail_enabled })"
                    >
                        <span
                            class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out"
                            :class="config.voicemail_enabled ? 'translate-x-5' : 'translate-x-0'"
                        ></span>
                    </button>
                </div>

                <!-- Greeting Text -->
                <div class="space-y-2">
                    <label class="text-xs font-bold text-gray-500 dark:text-zinc-400 uppercase tracking-tighter"
                        >Greeting Message</label
                    >
                    <textarea
                        :value="config.voicemail_greeting"
                        rows="3"
                        class="block w-full rounded-lg border-0 py-2 text-gray-900 dark:text-white shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm sm:leading-6 dark:bg-zinc-900"
                        :placeholder="$t('call.enter_greeting_text')"
                        @input="$emit('patch-config', { voicemail_greeting: $event.target.value })"
                    ></textarea>

                    <!-- TTS Settings -->
                    <div class="grid grid-cols-2 gap-3 mt-2">
                        <div class="space-y-1">
                            <label
                                class="text-[10px] font-bold text-gray-500 dark:text-zinc-500 uppercase tracking-tighter"
                                >{{ $t("call.tts_speed") }}</label
                            >
                            <input
                                :value="config.voicemail_tts_speed"
                                type="number"
                                min="80"
                                max="450"
                                class="block w-full rounded-lg border-0 py-1 text-gray-900 dark:text-white shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-blue-600 text-xs dark:bg-zinc-900"
                                @change="
                                    $emit('update-config', {
                                        voicemail_tts_speed: Number($event.target.value),
                                    })
                                "
                            />
                        </div>
                        <div class="space-y-1">
                            <label
                                class="text-[10px] font-bold text-gray-500 dark:text-zinc-500 uppercase tracking-tighter"
                                >{{ $t("call.tts_pitch") }}</label
                            >
                            <input
                                :value="config.voicemail_tts_pitch"
                                type="number"
                                min="0"
                                max="99"
                                class="block w-full rounded-lg border-0 py-1 text-gray-900 dark:text-white shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-blue-600 text-xs dark:bg-zinc-900"
                                @change="
                                    $emit('update-config', {
                                        voicemail_tts_pitch: Number($event.target.value),
                                    })
                                "
                            />
                        </div>
                        <div class="space-y-1">
                            <label
                                class="text-[10px] font-bold text-gray-500 dark:text-zinc-500 uppercase tracking-tighter"
                                >{{ $t("call.tts_word_gap") }}</label
                            >
                            <input
                                :value="config.voicemail_tts_word_gap"
                                type="number"
                                min="0"
                                max="100"
                                class="block w-full rounded-lg border-0 py-1 text-gray-900 dark:text-white shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-blue-600 text-xs dark:bg-zinc-900"
                                @change="
                                    $emit('update-config', {
                                        voicemail_tts_word_gap: Number($event.target.value),
                                    })
                                "
                            />
                        </div>
                        <div class="space-y-1">
                            <label
                                class="text-[10px] font-bold text-gray-500 dark:text-zinc-500 uppercase tracking-tighter"
                                >{{ $t("call.tts_voice") }}</label
                            >
                            <input
                                :value="config.voicemail_tts_voice"
                                type="text"
                                class="block w-full rounded-lg border-0 py-1 text-gray-900 dark:text-white shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-blue-600 text-xs dark:bg-zinc-900"
                                @change="$emit('update-config', { voicemail_tts_voice: $event.target.value })"
                            />
                        </div>
                    </div>

                    <div class="flex justify-between items-center">
                        <p class="text-[10px] text-gray-500 dark:text-zinc-500">
                            This text will be converted to speech using eSpeak NG.
                        </p>
                        <div class="flex gap-2">
                            <button
                                :disabled="!voicemailStatus.has_espeak || isGeneratingGreeting"
                                class="text-[10px] bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 px-3 py-1 rounded-full font-bold hover:bg-gray-200 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50"
                                @click="$emit('save-and-generate')"
                            >
                                {{ isGeneratingGreeting ? "Generating..." : "Save & Generate" }}
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Custom Greeting Upload -->
                <div class="space-y-2">
                    <label class="text-xs font-bold text-gray-500 dark:text-zinc-400 uppercase tracking-tighter"
                        >Custom Audio Greeting</label
                    >
                    <div class="flex items-center gap-3 flex-wrap">
                        <input
                            ref="greetingUpload"
                            type="file"
                            accept="audio/*"
                            class="hidden"
                            @change="$emit('upload-greeting', $event)"
                        />
                        <button
                            :disabled="isUploadingGreeting || voicemailStatus.is_greeting_recording"
                            class="text-xs bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 px-4 py-2 rounded-lg font-bold hover:bg-gray-200 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                            @click="$refs.greetingUpload.click()"
                        >
                            <MaterialDesignIcon icon-name="upload" class="size-4" />
                            {{ isUploadingGreeting ? "Uploading..." : "Upload Audio File" }}
                        </button>
                        <button
                            class="text-xs px-4 py-2 rounded-lg font-bold transition-colors flex items-center gap-2"
                            :class="
                                voicemailStatus.is_greeting_recording
                                    ? 'bg-red-500 text-white animate-pulse'
                                    : 'bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 hover:bg-gray-200 dark:hover:bg-zinc-700'
                            "
                            @click="
                                voicemailStatus.is_greeting_recording
                                    ? $emit('stop-recording-greeting')
                                    : $emit('start-recording-greeting')
                            "
                        >
                            <MaterialDesignIcon
                                :icon-name="voicemailStatus.is_greeting_recording ? 'stop' : 'microphone'"
                                class="size-4"
                            />
                            {{ voicemailStatus.is_greeting_recording ? "Stop Recording" : "Record from Mic" }}
                        </button>

                        <div v-if="voicemailStatus.has_greeting" class="flex items-center gap-2">
                            <button
                                class="text-xs bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 px-4 py-2 rounded-lg font-bold hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors flex items-center gap-2"
                                @click="$emit('delete-greeting')"
                            >
                                <MaterialDesignIcon icon-name="delete" class="size-4" />
                                Remove Greeting
                            </button>
                            <button
                                class="text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 px-4 py-2 rounded-lg font-bold hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors flex items-center gap-2"
                                @click="$emit('play-greeting')"
                            >
                                <MaterialDesignIcon :icon-name="isPlayingGreeting ? 'stop' : 'play'" class="size-4" />
                                {{ isPlayingGreeting ? "Stop Preview" : "Preview" }}
                            </button>
                        </div>
                        <div v-else class="text-[10px] text-gray-500 dark:text-zinc-500 italic">
                            No custom greeting uploaded (default text will be used)
                        </div>
                    </div>
                    <p class="text-[10px] text-gray-500 dark:text-zinc-500">
                        Supports MP3, OGG, WAV, M4A, FLAC. Will be converted to Opus.
                    </p>
                </div>

                <!-- Delays -->
                <div class="grid grid-cols-2 gap-4">
                    <div class="space-y-2">
                        <label class="text-xs font-bold text-gray-500 dark:text-zinc-400 uppercase tracking-tighter"
                            >Answer Delay (s)</label
                        >
                        <input
                            :value="config.voicemail_auto_answer_delay_seconds"
                            type="number"
                            min="1"
                            max="120"
                            class="block w-full rounded-lg border-0 py-1.5 text-gray-900 dark:text-white shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
                            @change="
                                $emit('update-config', {
                                    voicemail_auto_answer_delay_seconds: Number($event.target.value),
                                })
                            "
                        />
                    </div>
                    <div class="space-y-2">
                        <label class="text-xs font-bold text-gray-500 dark:text-zinc-400 uppercase tracking-tighter"
                            >Max Recording (s)</label
                        >
                        <input
                            :value="config.voicemail_max_recording_seconds"
                            type="number"
                            min="5"
                            max="600"
                            class="block w-full rounded-lg border-0 py-1.5 text-gray-900 dark:text-white shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
                            @change="
                                $emit('update-config', {
                                    voicemail_max_recording_seconds: Number($event.target.value),
                                })
                            "
                        />
                    </div>
                </div>
            </div>
        </div>

        <div v-if="voicemails.length === 0" class="my-auto text-center">
            <div class="bg-gray-200 dark:bg-zinc-800 p-6 rounded-full inline-block mb-4">
                <MaterialDesignIcon icon-name="voicemail" class="size-12 text-gray-400" />
            </div>
            <h3 class="text-lg font-medium text-gray-900 dark:text-white">No Voicemails</h3>
            <p class="text-gray-500 dark:text-zinc-400">When people leave you messages, they'll show up here.</p>
        </div>

        <div v-else class="space-y-4">
            <div class="border-b border-gray-200 dark:border-zinc-800 overflow-hidden">
                <div class="px-4 py-3 border-b border-gray-200 dark:border-zinc-800 flex justify-between items-center">
                    <h3 class="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider">
                        Voicemail Inbox
                    </h3>
                    <span
                        class="text-[10px] bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 px-2 py-0.5 rounded-full font-bold uppercase"
                    >
                        {{ voicemails.length }} Messages
                    </span>
                </div>
                <ul class="divide-y divide-gray-100 dark:divide-zinc-800">
                    <li
                        v-for="voicemail in voicemails"
                        :key="voicemail.id"
                        class="px-4 py-4 hover:bg-gray-50 dark:hover:bg-zinc-800/50 transition-colors"
                        :class="{ 'bg-blue-50/50 dark:bg-blue-900/10': !voicemail.is_read }"
                    >
                        <div class="flex items-start space-x-4">
                            <!-- Icon / Play/Pause Button -->
                            <div class="relative shrink-0">
                                <LxmfUserIcon
                                    :custom-image="getContactByHash(voicemail.remote_identity_hash)?.custom_image"
                                    :icon-name="voicemail.remote_icon ? voicemail.remote_icon.icon_name : ''"
                                    :icon-foreground-colour="
                                        voicemail.remote_icon ? voicemail.remote_icon.foreground_colour : ''
                                    "
                                    :icon-background-colour="
                                        voicemail.remote_icon ? voicemail.remote_icon.background_colour : ''
                                    "
                                    class="size-10"
                                />
                            </div>

                            <div class="flex-1 min-w-0">
                                <div class="flex items-center justify-between mb-1">
                                    <div class="flex items-center min-w-0 mr-2">
                                        <p class="text-sm font-bold text-gray-900 dark:text-white truncate">
                                            {{ voicemail.remote_identity_name || $t("call.unknown") }}
                                        </p>
                                        <span
                                            v-if="!voicemail.is_read"
                                            class="ml-2 shrink-0 size-2 inline-block rounded-full bg-blue-500"
                                        ></span>
                                    </div>
                                    <span class="text-[10px] text-gray-500 dark:text-zinc-500 font-mono shrink-0">
                                        {{ formatDateTime(voicemail.timestamp * 1000) }}
                                    </span>
                                </div>

                                <div class="flex items-center text-xs text-gray-500 dark:text-zinc-400 space-x-3 mb-3">
                                    <span class="flex items-center gap-1">
                                        <MaterialDesignIcon icon-name="clock-outline" class="size-3" />
                                        {{ formatDuration(voicemail.duration_seconds) }}
                                    </span>
                                    <span
                                        class="opacity-60 font-mono text-[10px] truncate cursor-pointer hover:text-blue-500 transition-colors"
                                        :title="voicemail.remote_identity_hash"
                                        @click.stop="$emit('copy-hash', voicemail.remote_identity_hash)"
                                        >{{ formatDestinationHash(voicemail.remote_identity_hash) }}</span
                                    >
                                </div>

                                <div class="mb-4">
                                    <AudioWaveformPlayer
                                        :src="`/api/v1/telephone/voicemails/${voicemail.id}/audio`"
                                        @play="$emit('mark-read', voicemail)"
                                    />
                                </div>

                                <div class="flex items-center gap-4">
                                    <button
                                        type="button"
                                        class="text-[10px] flex items-center gap-1 text-gray-500 hover:text-blue-500 font-bold uppercase tracking-wider transition-colors"
                                        @click="
                                            $emit(
                                                'call-back',
                                                voicemail.remote_telephony_hash ||
                                                    voicemail.remote_destination_hash ||
                                                    voicemail.remote_identity_hash
                                            )
                                        "
                                    >
                                        <MaterialDesignIcon icon-name="phone" class="size-3" />
                                        Call Back
                                    </button>
                                    <a
                                        :href="`/api/v1/telephone/voicemails/${voicemail.id}/audio`"
                                        :download="`voicemail_${voicemail.id}.opus`"
                                        class="text-[10px] flex items-center gap-1 text-gray-500 hover:text-blue-500 font-bold uppercase tracking-wider transition-colors"
                                    >
                                        <MaterialDesignIcon icon-name="download" class="size-3" />
                                        Download
                                    </a>
                                    <button
                                        type="button"
                                        class="text-[10px] flex items-center gap-1 text-red-500 hover:text-red-600 font-bold uppercase tracking-wider transition-colors"
                                        @click="$emit('delete', voicemail.id)"
                                    >
                                        <MaterialDesignIcon icon-name="delete" class="size-3" />
                                        Delete
                                    </button>
                                </div>
                            </div>
                        </div>
                    </li>
                </ul>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";
import LxmfUserIcon from "../../LxmfUserIcon.vue";
import AudioWaveformPlayer from "../../messages/AudioWaveformPlayer.vue";

export default {
    name: "CallVoicemailTab",
    components: {
        MaterialDesignIcon,
        LxmfUserIcon,
        AudioWaveformPlayer,
    },
    props: {
        active: {
            type: Boolean,
            default: false,
        },
        voicemailSearch: {
            type: String,
            default: "",
        },
        config: {
            type: Object,
            default: null,
        },
        voicemailStatus: {
            type: Object,
            default: () => ({}),
        },
        voicemails: {
            type: Array,
            default: () => [],
        },
        isGeneratingGreeting: {
            type: Boolean,
            default: false,
        },
        isUploadingGreeting: {
            type: Boolean,
            default: false,
        },
        isPlayingGreeting: {
            type: Boolean,
            default: false,
        },
        getContactByHash: {
            type: Function,
            required: true,
        },
        formatDateTime: {
            type: Function,
            required: true,
        },
        formatDuration: {
            type: Function,
            required: true,
        },
        formatDestinationHash: {
            type: Function,
            required: true,
        },
    },
    emits: [
        "update:voicemailSearch",
        "search-input",
        "update-config",
        "patch-config",
        "save-and-generate",
        "upload-greeting",
        "start-recording-greeting",
        "stop-recording-greeting",
        "delete-greeting",
        "play-greeting",
        "copy-hash",
        "mark-read",
        "call-back",
        "delete",
    ],
    data() {
        return {
            isVoicemailSettingsExpanded: false,
        };
    },
    methods: {
        onSearchInput(event) {
            this.$emit("update:voicemailSearch", event.target.value);
            this.$emit("search-input");
        },
    },
};
</script>
