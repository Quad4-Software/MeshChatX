<template>
    <div
        v-if="activeCall"
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
                <span class="text-[10px] font-bold text-gray-500 dark:text-zinc-400 uppercase tracking-wider">
                    {{
                        wasDeclined
                            ? $t("call.call_declined")
                            : isEnded
                              ? $t("call.call_ended")
                              : activeCall.is_voicemail
                                ? $t("call.recording_voicemail")
                                : activeCall.status === 6
                                  ? $t("call.active_call")
                                  : $t("call.call_status")
                    }}
                </span>
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
                    class="p-4 rounded-full mb-3"
                    :class="
                        isEnded || wasDeclined ? 'bg-red-100 dark:bg-red-900/30' : 'bg-blue-100 dark:bg-blue-900/30'
                    "
                >
                    <LxmfUserIcon
                        v-if="activeCall.remote_icon"
                        :icon-name="activeCall.remote_icon.icon_name"
                        :icon-foreground-colour="activeCall.remote_icon.foreground_colour"
                        :icon-background-colour="activeCall.remote_icon.background_colour"
                        class="size-8"
                    />
                    <MaterialDesignIcon
                        v-else
                        icon-name="account"
                        class="size-8"
                        :class="
                            isEnded || wasDeclined
                                ? 'text-red-600 dark:text-red-400'
                                : 'text-blue-600 dark:text-blue-400'
                        "
                    />
                </div>
                <div class="text-center w-full min-w-0">
                    <div class="font-bold text-gray-900 dark:text-white truncate px-2">
                        {{ activeCall.remote_identity_name || $t("call.unknown") }}
                    </div>
                    <div
                        v-if="activeCall.is_contact"
                        class="text-[10px] text-blue-600 dark:text-blue-400 font-medium mt-0.5"
                    >
                        In contacts
                    </div>
                    <div class="text-[10px] text-gray-500 dark:text-zinc-500 font-mono truncate px-4">
                        {{
                            activeCall.remote_identity_hash
                                ? formatDestinationHash(activeCall.remote_identity_hash)
                                : ""
                        }}
                    </div>
                </div>
            </div>

            <!-- Status -->
            <div class="text-center mb-6">
                <div
                    class="text-sm font-medium"
                    :class="[
                        isEnded || wasDeclined
                            ? 'text-red-600 dark:text-red-400 animate-pulse'
                            : activeCall.status === 6
                              ? 'text-green-600 dark:text-green-400'
                              : 'text-gray-600 dark:text-zinc-400',
                    ]"
                >
                    <span v-if="wasDeclined">{{ $t("call.call_declined") }}</span>
                    <span v-else-if="isEnded">{{ $t("call.call_ended") }}</span>
                    <span v-else-if="activeCall.is_incoming && activeCall.status === 4">{{
                        $t("call.incoming_call")
                    }}</span>
                    <span v-else-if="activeCall.status === 0">{{ $t("call.busy") }}</span>
                    <span v-else-if="activeCall.status === 1">{{ $t("call.rejected") }}</span>
                    <span v-else-if="activeCall.status === 2">{{ $t("call.calling") }}</span>
                    <span v-else-if="activeCall.status === 3">{{ $t("call.available") }}</span>
                    <span v-else-if="activeCall.status === 4">{{ $t("call.ringing") }}</span>
                    <span v-else-if="activeCall.status === 5">{{ $t("call.connecting") }}</span>
                    <span v-else-if="activeCall.status === 6">{{ $t("call.connected") }}</span>
                    <span v-else>{{ $t("call.status") }}: {{ activeCall.status }}</span>
                </div>
                <div
                    v-if="activeCall.status === 6 && !isEnded && elapsedTime"
                    class="text-xs text-gray-500 dark:text-zinc-400 mt-1 font-mono"
                >
                    {{ elapsedTime }}
                </div>
            </div>

            <!-- Stats (only when connected and not minimized) -->
            <div
                v-if="activeCall.status === 6 && !isEnded"
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
                        activeCall.is_incoming && activeCall.status === 4
                            ? $t('call.decline_call')
                            : $t('call.hangup_call')
                    "
                    class="p-2.5 rounded-full bg-red-600 text-white hover:bg-red-700 shadow-lg shadow-red-600/30 transition-all duration-200"
                    @click="hangupCall"
                >
                    <MaterialDesignIcon icon-name="phone-hangup" class="size-5 rotate-[135deg]" />
                </button>

                <!-- Send to Voicemail (if incoming) -->
                <button
                    v-if="activeCall.is_incoming && activeCall.status === 4"
                    type="button"
                    :title="$t('call.send_to_voicemail')"
                    class="p-2.5 rounded-full bg-blue-600 text-white hover:bg-blue-700 shadow-lg shadow-blue-600/30 transition-all duration-200"
                    @click="sendToVoicemail"
                >
                    <MaterialDesignIcon icon-name="voicemail" class="size-5" />
                </button>

                <!-- Answer (if incoming) -->
                <button
                    v-if="activeCall.is_incoming && activeCall.status === 4"
                    type="button"
                    :title="$t('call.answer_call')"
                    class="p-2.5 rounded-full bg-green-600 text-white hover:bg-green-700 shadow-lg shadow-green-600/30 animate-bounce"
                    @click="answerCall"
                >
                    <MaterialDesignIcon icon-name="phone" class="size-5" />
                </button>
            </div>
        </div>

        <!-- Minimized State -->
        <div
            v-show="isMinimized && !isEnded"
            class="px-4 py-2 flex items-center justify-between bg-white dark:bg-zinc-900"
        >
            <div class="flex items-center space-x-2 overflow-hidden mr-2 min-w-0">
                <LxmfUserIcon
                    v-if="activeCall.remote_icon"
                    :icon-name="activeCall.remote_icon.icon_name"
                    :icon-foreground-colour="activeCall.remote_icon.foreground_colour"
                    :icon-background-colour="activeCall.remote_icon.background_colour"
                    class="size-5 shrink-0"
                />
                <MaterialDesignIcon v-else icon-name="account" class="size-5 text-blue-500 shrink-0" />
                <div class="flex flex-col min-w-0">
                    <span class="text-sm font-medium text-gray-700 dark:text-zinc-200 truncate block">
                        {{ activeCall.remote_identity_name || $t("call.unknown") }}
                    </span>
                    <span
                        v-if="activeCall.status === 6 && elapsedTime"
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
import Utils from "../../js/Utils";
import ToastUtils from "../../js/ToastUtils";

export default {
    name: "CallOverlay",
    components: { MaterialDesignIcon, LxmfUserIcon },
    props: {
        activeCall: {
            type: Object,
            required: true,
        },
        isEnded: {
            type: Boolean,
            default: false,
        },
        wasDeclined: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["hangup"],
    data() {
        return {
            isMinimized: false,
            elapsedTimeInterval: null,
        };
    },
    computed: {
        isMicMuted() {
            return this.activeCall?.is_mic_muted ?? false;
        },
        isSpeakerMuted() {
            return this.activeCall?.is_speaker_muted ?? false;
        },
        elapsedTime() {
            if (!this.activeCall?.call_start_time) {
                return null;
            }
            const elapsed = Math.floor(Date.now() / 1000 - this.activeCall.call_start_time);
            return Utils.formatMinutesSeconds(elapsed);
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
                ToastUtils.error("Failed to answer call");
            }
        },
        async hangupCall() {
            try {
                this.$emit("hangup");
                await window.axios.get("/api/v1/telephone/hangup");
            } catch {
                ToastUtils.error("Failed to hangup call");
            }
        },
        async sendToVoicemail() {
            try {
                await window.axios.get("/api/v1/telephone/send-to-voicemail");
                ToastUtils.success("Call sent to voicemail");
            } catch {
                ToastUtils.error("Failed to send call to voicemail");
            }
        },
        async toggleMicrophone() {
            try {
                const endpoint = this.isMicMuted
                    ? "/api/v1/telephone/unmute-transmit"
                    : "/api/v1/telephone/mute-transmit";
                await window.axios.get(endpoint);
                // eslint-disable-next-line vue/no-mutating-props
                this.activeCall.is_mic_muted = !this.isMicMuted;
            } catch {
                ToastUtils.error("Failed to toggle microphone");
            }
        },
        async toggleSpeaker() {
            try {
                const endpoint = this.isSpeakerMuted
                    ? "/api/v1/telephone/unmute-receive"
                    : "/api/v1/telephone/mute-receive";
                await window.axios.get(endpoint);
                // eslint-disable-next-line vue/no-mutating-props
                this.activeCall.is_speaker_muted = !this.isSpeakerMuted;
            } catch {
                ToastUtils.error("Failed to toggle speaker");
            }
        },
    },
};
</script>
