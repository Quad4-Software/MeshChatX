<template>
    <div
        v-if="activeCall"
        class="fixed bottom-4 right-4 z-[100] w-72 bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-zinc-800 overflow-hidden transition-all duration-300"
        :class="{ 'ring-2 ring-red-500 ring-opacity-50': isEnded }"
    >
        <!-- Header -->
        <div class="p-3 flex items-center bg-gray-50 dark:bg-zinc-800/50 border-b border-gray-100 dark:border-zinc-800">
            <div class="flex-1 flex items-center space-x-2">
                <div class="size-2 rounded-full" :class="isEnded ? 'bg-red-500' : 'bg-green-500 animate-pulse'"></div>
                <span class="text-[10px] font-bold text-gray-500 dark:text-zinc-400 uppercase tracking-wider">
                    {{
                        isEnded
                            ? "Call Ended"
                            : activeCall.is_voicemail
                              ? "Recording Voicemail"
                              : activeCall.status === 6
                                ? "Active Call"
                                : "Call Status"
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
                    :class="isEnded ? 'bg-red-100 dark:bg-red-900/30' : 'bg-blue-100 dark:bg-blue-900/30'"
                >
                    <MaterialDesignIcon
                        icon-name="account"
                        class="size-8"
                        :class="isEnded ? 'text-red-600 dark:text-red-400' : 'text-blue-600 dark:text-blue-400'"
                    />
                </div>
                <div class="text-center w-full">
                    <div class="font-bold text-gray-900 dark:text-white truncate px-2">
                        {{ activeCall.remote_identity_name || "Unknown" }}
                    </div>
                    <div class="text-[10px] text-gray-500 dark:text-zinc-500 font-mono">
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
                        isEnded
                            ? 'text-red-600 dark:text-red-400 animate-pulse'
                            : activeCall.status === 6
                              ? 'text-green-600 dark:text-green-400'
                              : 'text-gray-600 dark:text-zinc-400',
                    ]"
                >
                    <span v-if="isEnded">Call Ended</span>
                    <span v-else-if="activeCall.is_incoming && activeCall.status === 4">Incoming Call...</span>
                    <span v-else-if="activeCall.status === 0">Busy</span>
                    <span v-else-if="activeCall.status === 1">Rejected</span>
                    <span v-else-if="activeCall.status === 2">Calling...</span>
                    <span v-else-if="activeCall.status === 3">Available</span>
                    <span v-else-if="activeCall.status === 4">Ringing...</span>
                    <span v-else-if="activeCall.status === 5">Connecting...</span>
                    <span v-else-if="activeCall.status === 6">Connected</span>
                    <span v-else>Status: {{ activeCall.status }}</span>
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
            <div v-if="!isEnded" class="flex justify-center space-x-3">
                <!-- Mute Mic -->
                <button
                    type="button"
                    :title="isMicMuted ? 'Unmute Mic' : 'Mute Mic'"
                    class="p-3 rounded-full transition-all duration-200"
                    :class="
                        isMicMuted
                            ? 'bg-red-500 text-white shadow-lg shadow-red-500/30'
                            : 'bg-gray-100 dark:bg-zinc-800 text-gray-600 dark:text-zinc-300 hover:bg-gray-200 dark:hover:bg-zinc-700'
                    "
                    @click="toggleMicrophone"
                >
                    <MaterialDesignIcon :icon-name="isMicMuted ? 'microphone-off' : 'microphone'" class="size-6" />
                </button>

                <!-- Mute Speaker -->
                <button
                    type="button"
                    :title="isSpeakerMuted ? 'Unmute Speaker' : 'Mute Speaker'"
                    class="p-3 rounded-full transition-all duration-200"
                    :class="
                        isSpeakerMuted
                            ? 'bg-red-500 text-white shadow-lg shadow-red-500/30'
                            : 'bg-gray-100 dark:bg-zinc-800 text-gray-600 dark:text-zinc-300 hover:bg-gray-200 dark:hover:bg-zinc-700'
                    "
                    @click="toggleSpeaker"
                >
                    <MaterialDesignIcon :icon-name="isSpeakerMuted ? 'volume-off' : 'volume-high'" class="size-6" />
                </button>

                <!-- Hangup -->
                <button
                    type="button"
                    :title="activeCall.is_incoming && activeCall.status === 4 ? 'Decline' : 'Hangup'"
                    class="p-3 rounded-full bg-red-600 text-white hover:bg-red-700 shadow-lg shadow-red-600/30 transition-all duration-200"
                    @click="hangupCall"
                >
                    <MaterialDesignIcon icon-name="phone-hangup" class="size-6 rotate-[135deg]" />
                </button>

                <!-- Answer (if incoming) -->
                <button
                    v-if="activeCall.is_incoming && activeCall.status === 4"
                    type="button"
                    title="Answer"
                    class="p-3 rounded-full bg-green-600 text-white hover:bg-green-700 shadow-lg shadow-green-600/30 animate-bounce"
                    @click="answerCall"
                >
                    <MaterialDesignIcon icon-name="phone" class="size-6" />
                </button>
            </div>
        </div>

        <!-- Minimized State -->
        <div
            v-show="isMinimized && !isEnded"
            class="px-4 py-2 flex items-center justify-between bg-white dark:bg-zinc-900"
        >
            <div class="flex items-center space-x-2 overflow-hidden mr-2">
                <MaterialDesignIcon icon-name="account" class="size-5 text-blue-500" />
                <span class="text-sm font-medium text-gray-700 dark:text-zinc-200 truncate">
                    {{ activeCall.remote_identity_name || "Unknown" }}
                </span>
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
import Utils from "../../js/Utils";
import ToastUtils from "../../js/ToastUtils";

export default {
    name: "CallOverlay",
    components: { MaterialDesignIcon },
    props: {
        activeCall: {
            type: Object,
            required: true,
        },
        isEnded: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            isMinimized: false,
        };
    },
    computed: {
        isMicMuted() {
            return this.activeCall?.is_mic_muted ?? false;
        },
        isSpeakerMuted() {
            return this.activeCall?.is_speaker_muted ?? false;
        },
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
                await window.axios.get("/api/v1/telephone/hangup");
            } catch {
                ToastUtils.error("Failed to hangup call");
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
