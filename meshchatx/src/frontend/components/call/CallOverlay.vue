<template>
    <div
        v-if="activeCall || initiationStatus || isEnded || wasDeclined"
        class="fixed bottom-4 right-4 z-[100] w-80 bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-zinc-800 overflow-hidden transition-all duration-300"
        :class="{ 'ring-2 ring-red-500 ring-opacity-50': isEnded || wasDeclined }"
    >
        <!-- Header -->
        <div class="p-3 flex items-center bg-gray-50 dark:bg-zinc-800/50 border-b border-gray-100 dark:border-zinc-800">
            <div class="flex-1 flex items-center space-x-2">
                <div
                    class="size-2 rounded-full"
                    :class="isEnded || wasDeclined ? 'bg-red-500' : 'bg-green-500 animate-pulse'"
                ></div>
                <button
                    type="button"
                    class="flex items-center space-x-2 hover:opacity-70 transition-opacity group"
                    :title="$t('call.go_to_phone_page')"
                    @click="goToPhonePage"
                >
                    <span
                        class="text-[10px] font-bold text-gray-500 dark:text-zinc-400 uppercase tracking-wider group-hover:text-gray-700 dark:group-hover:text-zinc-200"
                    >
                        {{
                            wasDeclined
                                ? $t("call.call_declined")
                                : isEnded
                                  ? $t("call.call_ended")
                                  : activeCall && activeCall.is_voicemail
                                    ? $t("call.recording_voicemail")
                                    : activeCall && activeCall.status === 6
                                      ? $t("call.active_call")
                                      : initiationStatus
                                        ? $t("call.initiation")
                                        : $t("call.call_status")
                        }}
                    </span>
                    <MaterialDesignIcon
                        icon-name="open-in-new"
                        class="size-3 text-gray-400 dark:text-zinc-500 group-hover:text-gray-600 dark:group-hover:text-zinc-300"
                    />
                </button>
                <div v-if="activeCall && activeCall.is_recording && !isEnded" class="flex items-center gap-1 ml-2">
                    <div class="size-1.5 bg-red-500 rounded-full animate-pulse"></div>
                    <span class="text-[8px] font-bold text-red-500 uppercase tracking-tighter">REC</span>
                </div>
            </div>
            <button
                v-if="!isEnded"
                type="button"
                class="p-1 hover:bg-gray-200 dark:hover:bg-zinc-700 rounded-lg transition-colors"
                @click="isMinimized = !isMinimized"
            >
                <MaterialDesignIcon
                    :icon-name="isMinimized ? 'chevron-up' : 'chevron-down'"
                    class="size-4 text-gray-500"
                />
            </button>
        </div>

        <div v-show="!isMinimized" class="p-4">
            <!-- icon and name -->
            <div class="flex flex-col items-center mb-4">
                <div
                    class="p-2 rounded-full mb-3"
                    :class="
                        isEnded || wasDeclined ? 'bg-red-100 dark:bg-red-900/30' : 'bg-blue-100 dark:bg-blue-900/30'
                    "
                >
                    <LxmfUserIcon
                        :custom-image="activeCall ? activeCall.custom_image : null"
                        :icon-name="activeCall && activeCall.remote_icon ? activeCall.remote_icon.icon_name : ''"
                        :icon-foreground-colour="
                            activeCall && activeCall.remote_icon ? activeCall.remote_icon.foreground_colour : ''
                        "
                        :icon-background-colour="
                            activeCall && activeCall.remote_icon ? activeCall.remote_icon.background_colour : ''
                        "
                        icon-class="size-14"
                    />
                </div>
                <div class="text-center w-full min-w-0">
                    <div class="font-bold text-gray-900 dark:text-white truncate px-2">
                        {{
                            (activeCall ? activeCall.remote_identity_name : initiationTargetName) || $t("call.unknown")
                        }}
                    </div>
                    <div
                        v-if="activeCall ? activeCall.is_contact : !!initiationTargetName"
                        class="text-[10px] text-blue-600 dark:text-blue-400 font-medium mt-0.5"
                    >
                        In contacts
                    </div>
                    <div class="text-[10px] text-gray-500 dark:text-zinc-500 font-mono truncate px-4">
                        {{
                            (activeCall ? activeCall.remote_identity_hash : initiationTargetHash)
                                ? formatDestinationHash(
                                      activeCall ? activeCall.remote_identity_hash : initiationTargetHash
                                  )
                                : ""
                        }}
                    </div>
                </div>
            </div>

            <!-- Status -->
            <div class="text-center mb-6">
                <div
                    v-if="activeCall"
                    class="text-sm font-medium"
                    :class="[
                        isEnded || wasDeclined
                            ? 'text-red-600 dark:text-red-400 animate-pulse'
                            : activeCall.is_voicemail
                              ? 'text-red-600 dark:text-red-400 animate-pulse'
                              : activeCall && activeCall.status === 6
                                ? 'text-green-600 dark:text-green-400'
                                : 'text-gray-600 dark:text-zinc-400',
                    ]"
                >
                    <span v-if="wasDeclined">{{ $t("call.call_declined") }}</span>
                    <span v-else-if="isEnded">{{ $t("call.call_ended") }}</span>
                    <span v-else-if="activeCall.is_voicemail" class="flex items-center justify-center gap-2">
                        <MaterialDesignIcon icon-name="record" class="size-4" />
                        {{ $t("call.recording_voicemail") }}
                    </span>
                    <span v-else-if="activeCall && activeCall.is_incoming && activeCall.status === 4">{{
                        $t("call.incoming_call")
                    }}</span>
                    <span v-else-if="activeCall && activeCall.status === 0">{{ $t("call.busy") }}</span>
                    <span v-else-if="activeCall && activeCall.status === 1">{{ $t("call.rejected") }}</span>
                    <span v-else-if="activeCall && activeCall.status === 2">{{ $t("call.calling") }}</span>
                    <span v-else-if="activeCall && activeCall.status === 3">{{ $t("call.available") }}</span>
                    <span v-else-if="activeCall && activeCall.status === 4">{{ $t("call.ringing") }}</span>
                    <span v-else-if="activeCall && activeCall.status === 5">{{ $t("call.connecting") }}</span>
                    <span v-else-if="activeCall && activeCall.status === 6">{{ $t("call.connected") }}</span>
                    <span v-else-if="activeCall">{{ $t("call.status") }}: {{ activeCall.status }}</span>
                </div>
                <div
                    v-else-if="initiationStatus"
                    class="text-sm font-medium text-blue-600 dark:text-blue-400 animate-pulse"
                >
                    {{ initiationStatus }}
                </div>
                <div
                    v-if="activeCall && activeCall.status === 6 && !isEnded && elapsedTime"
                    class="text-xs text-gray-500 dark:text-zinc-400 mt-1 font-mono"
                >
                    {{ elapsedTime }}
                </div>
                <div v-if="isEnded && callDuration" class="text-xs text-gray-500 dark:text-zinc-400 mt-1 font-mono">
                    {{ callDuration }}
                </div>
            </div>

            <!-- Stats (only when connected and not minimized) -->
            <div
                v-if="activeCall && activeCall.status === 6 && !isEnded"
                class="mb-4 p-2 bg-gray-50 dark:bg-zinc-800/50 rounded-lg text-[10px] text-gray-500 dark:text-zinc-400 grid grid-cols-2 gap-1"
            >
                <div class="flex items-center space-x-1">
                    <MaterialDesignIcon icon-name="arrow-up" class="size-3" />
                    <span>{{ formatBytes(activeCall.tx_bytes || 0) }}</span>
                </div>
                <div class="flex items-center space-x-1">
                    <MaterialDesignIcon icon-name="arrow-down" class="size-3" />
                    <span>{{ formatBytes(activeCall.rx_bytes || 0) }}</span>
                </div>
            </div>

            <!-- Controls -->
            <div v-if="!isEnded && !wasDeclined" class="flex flex-wrap justify-center gap-2 px-2">
                <!-- Mute Mic -->
                <button
                    type="button"
                    :title="isMicMuted ? $t('call.unmute_mic') : $t('call.mute_mic')"
                    class="p-2.5 rounded-full transition-all duration-200"
                    :class="
                        isMicMuted
                            ? 'bg-red-500 text-white shadow-lg shadow-red-500/30'
                            : 'bg-gray-100 dark:bg-zinc-800 text-gray-600 dark:text-zinc-300 hover:bg-gray-200 dark:hover:bg-zinc-700'
                    "
                    @click="toggleMicrophone"
                >
                    <MaterialDesignIcon :icon-name="isMicMuted ? 'microphone-off' : 'microphone'" class="size-5" />
                </button>

                <!-- Mute Speaker -->
                <button
                    type="button"
                    :title="isSpeakerMuted ? $t('call.unmute_speaker') : $t('call.mute_speaker')"
                    class="p-2.5 rounded-full transition-all duration-200"
                    :class="
                        isSpeakerMuted
                            ? 'bg-red-500 text-white shadow-lg shadow-red-500/30'
                            : 'bg-gray-100 dark:bg-zinc-800 text-gray-600 dark:text-zinc-300 hover:bg-gray-200 dark:hover:bg-zinc-700'
                    "
                    @click="toggleSpeaker"
                >
                    <MaterialDesignIcon :icon-name="isSpeakerMuted ? 'volume-off' : 'volume-high'" class="size-5" />
                </button>

                <!-- Hangup -->
                <button
                    type="button"
                    :title="
                        activeCall && activeCall.is_incoming && activeCall.status === 4
                            ? $t('call.decline_call')
                            : $t('call.hangup_call')
                    "
                    class="p-2.5 rounded-full bg-red-600 text-white hover:bg-red-700 shadow-lg shadow-red-600/30 transition-all duration-200"
                    @click="hangupCall(null)"
                >
                    <MaterialDesignIcon icon-name="phone-hangup" class="size-5 rotate-[135deg]" />
                </button>

                <!-- Send to Voicemail (if incoming) -->
                <button
                    v-if="activeCall && activeCall.is_incoming && activeCall.status === 4"
                    type="button"
                    :title="$t('call.send_to_voicemail')"
                    class="p-2.5 rounded-full bg-blue-600 text-white hover:bg-blue-700 shadow-lg shadow-blue-600/30 transition-all duration-200"
                    @click="sendToVoicemail"
                >
                    <MaterialDesignIcon icon-name="voicemail" class="size-5" />
                </button>

                <!-- Answer (if incoming) -->
                <button
                    v-if="activeCall && activeCall.is_incoming && activeCall.status === 4"
                    type="button"
                    :title="$t('call.answer_call')"
                    class="p-2.5 rounded-full bg-green-600 text-white hover:bg-green-700 shadow-lg shadow-green-600/30 animate-bounce"
                    @click="answerCall(null)"
                >
                    <MaterialDesignIcon icon-name="phone" class="size-5" />
                </button>
            </div>
        </div>

        <!-- Ended State Voicemail Playback -->
        <div
            v-if="isEnded && activeCall && activeCall.is_voicemail && voicemailStatus && voicemailStatus.latest_id"
            class="px-4 pb-4"
        >
            <AudioWaveformPlayer :src="`/api/v1/telephone/voicemails/${voicemailStatus.latest_id}/audio`" />
        </div>

        <!-- Minimized State -->
        <div
            v-show="isMinimized && !isEnded"
            class="px-4 py-2 flex items-center justify-between bg-white dark:bg-zinc-900"
        >
            <div class="flex items-center space-x-2 overflow-hidden mr-2 min-w-0">
                <LxmfUserIcon
                    :custom-image="activeCall ? activeCall.custom_image : null"
                    :icon-name="activeCall && activeCall.remote_icon ? activeCall.remote_icon.icon_name : ''"
                    :icon-foreground-colour="
                        activeCall && activeCall.remote_icon ? activeCall.remote_icon.foreground_colour : ''
                    "
                    :icon-background-colour="
                        activeCall && activeCall.remote_icon ? activeCall.remote_icon.background_colour : ''
                    "
                    icon-class="size-6 shrink-0"
                />
                <div class="flex flex-col min-w-0">
                    <span class="text-sm font-medium text-gray-700 dark:text-zinc-200 truncate block">
                        {{
                            (activeCall ? activeCall.remote_identity_name : initiationTargetName) || $t("call.unknown")
                        }}
                    </span>
                    <span
                        v-if="activeCall && activeCall.status === 6 && elapsedTime"
                        class="text-[10px] text-gray-500 dark:text-zinc-400 font-mono"
                    >
                        {{ elapsedTime }}
                    </span>
                </div>
            </div>
            <div class="flex items-center space-x-1">
                <button
                    type="button"
                    class="p-1.5 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded transition-colors"
                    @click="toggleMicrophone"
                >
                    <MaterialDesignIcon
                        :icon-name="isMicMuted ? 'microphone-off' : 'microphone'"
                        class="size-4"
                        :class="isMicMuted ? 'text-red-500' : 'text-gray-400'"
                    />
                </button>
                <button
                    type="button"
                    class="p-1.5 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-colors"
                    @click="hangupCall"
                >
                    <MaterialDesignIcon icon-name="phone-hangup" class="size-4 text-red-500 rotate-[135deg]" />
                </button>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import LxmfUserIcon from "../LxmfUserIcon.vue";
import AudioWaveformPlayer from "../messages/AudioWaveformPlayer.vue";
import Utils from "../../js/Utils";
import ToastUtils from "../../js/ToastUtils";

export default {
    name: "CallOverlay",
    components: { MaterialDesignIcon, LxmfUserIcon, AudioWaveformPlayer },
    props: {
        activeCall: {
            type: Object,
            default: null,
        },
        isEnded: {
            type: Boolean,
            default: false,
        },
        wasDeclined: {
            type: Boolean,
            default: false,
        },
        voicemailStatus: {
            type: Object,
            default: null,
        },
        initiationStatus: {
            type: String,
            default: null,
        },
        initiationTargetHash: {
            type: String,
            default: null,
        },
        initiationTargetName: {
            type: String,
            default: null,
        },
    },
    emits: ["hangup", "toggle-mic", "toggle-speaker"],
    data() {
        return {
            isMinimized: false,
            isMicMuting: false,
            isSpeakerMuting: false,
            elapsedTimeInterval: null,
            isPlayingVoicemail: false,
            audioPlayer: null,
            localMicMuted: false,
            localSpeakerMuted: false,
        };
    },
    computed: {
        isMicMuted() {
            return this.localMicMuted;
        },
        isSpeakerMuted() {
            return this.localSpeakerMuted;
        },
        elapsedTime() {
            if (!this.activeCall?.call_start_time) {
                return null;
            }
            const elapsed = Math.floor(Date.now() / 1000 - this.activeCall.call_start_time);
            return Utils.formatMinutesSeconds(elapsed);
        },
        callDuration() {
            if (!this.isEnded || !this.activeCall?.call_start_time) {
                return null;
            }
            const duration = Math.floor(Date.now() / 1000 - this.activeCall.call_start_time);
            return Utils.formatMinutesSeconds(duration);
        },
    },
    watch: {
        activeCall(newCall, oldCall) {
            if (newCall) {
                if (!oldCall || newCall.hash !== oldCall.hash) {
                    this.localMicMuted = newCall.is_mic_muted;
                    this.localSpeakerMuted = newCall.is_speaker_muted;
                }
            }
        },
    },
    mounted() {
        this.elapsedTimeInterval = setInterval(() => {
            this.$forceUpdate();
        }, 1000);
    },
    beforeUnmount() {
        if (this.elapsedTimeInterval) {
            clearInterval(this.elapsedTimeInterval);
        }
    },
    methods: {
        goToPhonePage() {
            this.$router.push({ name: "call", query: { tab: "phone" } });
        },
        formatDestinationHash(hash) {
            return Utils.formatDestinationHash(hash);
        },
        formatBytes(bytes) {
            return Utils.formatBytes(bytes || 0);
        },
        async answerCall() {
            try {
                await window.axios.get("/api/v1/telephone/answer");
            } catch {
                ToastUtils.error(this.$t("call.failed_to_answer_call"));
            }
        },
        async hangupCall() {
            try {
                this.$emit("hangup");
                await window.axios.get("/api/v1/telephone/hangup");
            } catch {
                ToastUtils.error(this.$t("call.failed_to_hangup_call"));
            }
        },
        async sendToVoicemail() {
            try {
                await window.axios.get("/api/v1/telephone/send-to-voicemail");
                ToastUtils.success(this.$t("call.call_sent_to_voicemail"));
            } catch {
                ToastUtils.error(this.$t("call.failed_to_send_to_voicemail"));
            }
        },
        async toggleMicrophone() {
            try {
                const isCurrentlyMuted = this.localMicMuted;
                this.isMicMuting = true;

                // Optimistic update
                this.localMicMuted = !isCurrentlyMuted;
                this.$emit("toggle-mic", !isCurrentlyMuted);

                const endpoint = isCurrentlyMuted
                    ? "/api/v1/telephone/unmute-transmit"
                    : "/api/v1/telephone/mute-transmit";
                await window.axios.get(endpoint);

                setTimeout(() => {
                    this.isMicMuting = false;
                }, 500);
            } catch {
                this.isMicMuting = false;
                // Revert on error
                this.localMicMuted = !this.localMicMuted;
                ToastUtils.error(this.$t("call.failed_to_toggle_microphone"));
            }
        },
        async toggleSpeaker() {
            try {
                const isCurrentlyMuted = this.localSpeakerMuted;
                this.isSpeakerMuting = true;

                // Optimistic update
                this.localSpeakerMuted = !isCurrentlyMuted;
                this.$emit("toggle-speaker", !isCurrentlyMuted);

                const endpoint = isCurrentlyMuted
                    ? "/api/v1/telephone/unmute-receive"
                    : "/api/v1/telephone/mute-receive";
                await window.axios.get(endpoint);

                setTimeout(() => {
                    this.isSpeakerMuting = false;
                }, 500);
            } catch {
                this.isSpeakerMuting = false;
                // Revert on error
                this.localSpeakerMuted = !this.localSpeakerMuted;
                ToastUtils.error(this.$t("call.failed_to_toggle_speaker"));
            }
        },
        async playLatestVoicemail() {
            if (this.isPlayingVoicemail) {
                if (this.audioPlayer) {
                    this.audioPlayer.pause();
                }
                this.isPlayingVoicemail = false;
                return;
            }

            const voicemailId = this.voicemailStatus?.latest_id;
            if (!voicemailId) return;

            this.isPlayingVoicemail = true;
            this.audioPlayer = new Audio(`/api/v1/telephone/voicemails/${voicemailId}/audio`);
            this.audioPlayer.onended = () => {
                this.isPlayingVoicemail = false;
                this.audioPlayer = null;
            };

            try {
                await this.audioPlayer.play();
            } catch (e) {
                console.error("Failed to play voicemail:", e);
                this.isPlayingVoicemail = false;
            }
        },
    },
};
</script>
