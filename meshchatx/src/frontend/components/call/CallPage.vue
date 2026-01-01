<template>
    <div class="flex w-full h-full bg-gray-100 dark:bg-zinc-950" :class="{ dark: config?.theme === 'dark' }">
        <div class="mx-auto my-auto w-full max-w-xl p-4">
            <div v-if="activeCall || isCallEnded" class="flex">
                <div class="mx-auto my-auto min-w-64">
                    <div class="text-center">
                        <div>
                            <!-- icon -->
                            <div class="flex mb-4">
                                <div
                                    class="mx-auto bg-gray-300 dark:bg-zinc-700 text-gray-500 dark:text-gray-400 p-4 rounded-full"
                                    :class="{ 'animate-pulse': activeCall && activeCall.status === 4 }"
                                >
                                    <MaterialDesignIcon icon-name="account" class="size-12" />
                                </div>
                            </div>

                            <!-- name -->
                            <div class="text-xl font-semibold text-gray-500 dark:text-zinc-100">
                                <span v-if="(activeCall || lastCall)?.remote_identity_name != null">{{
                                    (activeCall || lastCall).remote_identity_name
                                }}</span>
                                <span v-else>Unknown</span>
                            </div>

                            <!-- identity hash -->
                            <div
                                v-if="(activeCall || lastCall)?.remote_identity_hash != null"
                                class="text-gray-500 dark:text-zinc-100 opacity-60 text-sm"
                            >
                                {{
                                    (activeCall || lastCall).remote_identity_hash
                                        ? formatDestinationHash((activeCall || lastCall).remote_identity_hash)
                                        : ""
                                }}
                            </div>
                        </div>

                        <!-- call status -->
                        <div class="text-gray-500 dark:text-zinc-100 mb-4 mt-2">
                            <template v-if="isCallEnded">
                                <span class="text-red-500 font-bold animate-pulse">Call Ended</span>
                            </template>
                            <template v-else-if="activeCall">
                                <span v-if="activeCall.is_incoming && activeCall.status === 4" class="animate-bounce inline-block">Incoming Call...</span>
                                <span v-else>
                                    <span v-if="activeCall.status === 0">Busy...</span>
                                    <span v-else-if="activeCall.status === 1">Rejected...</span>
                                    <span v-else-if="activeCall.status === 2">Calling...</span>
                                    <span v-else-if="activeCall.status === 3">Available...</span>
                                    <span v-else-if="activeCall.status === 4">Ringing...</span>
                                    <span v-else-if="activeCall.status === 5">Connecting...</span>
                                    <span v-else-if="activeCall.status === 6" class="text-green-500 font-medium">Connected</span>
                                    <span v-else>Status: {{ activeCall.status }}</span>
                                </span>
                            </template>
                        </div>

                        <!-- settings during connected call -->
                        <div v-if="activeCall && activeCall.status === 6" class="mb-4">
                            <div class="w-full">
                                <select
                                    v-model="selectedAudioProfileId"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-600"
                                    @change="switchAudioProfile(selectedAudioProfileId)"
                                >
                                    <option
                                        v-for="audioProfile in audioProfiles"
                                        :key="audioProfile.id"
                                        :value="audioProfile.id"
                                    >
                                        {{ audioProfile.name }}
                                    </option>
                                </select>
                            </div>
                        </div>

                        <!-- controls during connected call -->
                        <div v-if="activeCall && activeCall.status === 6" class="mx-auto space-x-4 mb-8">
                            <!-- mute/unmute mic -->
                            <button
                                type="button"
                                :title="isMicMuted ? 'Unmute Mic' : 'Mute Mic'"
                                :class="[
                                    isMicMuted
                                        ? 'bg-red-500 hover:bg-red-400'
                                        : 'bg-gray-200 dark:bg-zinc-800 text-gray-700 dark:text-zinc-200 hover:bg-gray-300 dark:hover:bg-zinc-700',
                                ]"
                                class="inline-flex items-center gap-x-1 rounded-full p-4 text-sm font-semibold shadow-sm transition-all duration-200"
                                @click="toggleMicrophone"
                            >
                                <MaterialDesignIcon
                                    :icon-name="isMicMuted ? 'microphone-off' : 'microphone'"
                                    class="size-8"
                                />
                            </button>

                            <!-- mute/unmute speaker -->
                            <button
                                type="button"
                                :title="isSpeakerMuted ? 'Unmute Speaker' : 'Mute Speaker'"
                                :class="[
                                    isSpeakerMuted
                                        ? 'bg-red-500 hover:bg-red-400'
                                        : 'bg-gray-200 dark:bg-zinc-800 text-gray-700 dark:text-zinc-200 hover:bg-gray-300 dark:hover:bg-zinc-700',
                                ]"
                                class="inline-flex items-center gap-x-1 rounded-full p-4 text-sm font-semibold shadow-sm transition-all duration-200"
                                @click="toggleSpeaker"
                            >
                                <MaterialDesignIcon
                                    :icon-name="isSpeakerMuted ? 'volume-off' : 'volume-high'"
                                    class="size-8"
                                />
                            </button>

                            <!-- toggle stats -->
                            <button
                                type="button"
                                :class="[
                                    isShowingStats
                                        ? 'bg-blue-500 text-white'
                                        : 'bg-gray-200 dark:bg-zinc-800 text-gray-700 dark:text-zinc-200 hover:bg-gray-300 dark:hover:bg-zinc-700',
                                ]"
                                class="inline-flex items-center gap-x-1 rounded-full p-4 text-sm font-semibold shadow-sm transition-all duration-200"
                                @click="isShowingStats = !isShowingStats"
                            >
                                <MaterialDesignIcon icon-name="chart-bar" class="size-8" />
                            </button>
                        </div>

                        <!-- actions -->
                        <div v-if="activeCall" class="mx-auto space-x-4">
                            <!-- answer call -->
                            <button
                                v-if="activeCall.is_incoming && activeCall.status === 4"
                                title="Answer Call"
                                type="button"
                                class="inline-flex items-center gap-x-2 rounded-2xl bg-green-600 px-6 py-4 text-lg font-bold text-white shadow-xl hover:bg-green-500 transition-all duration-200 animate-bounce"
                                @click="answerCall"
                            >
                                <MaterialDesignIcon icon-name="phone" class="size-6" />
                                <span>Accept</span>
                            </button>

                            <!-- hangup/decline call -->
                            <button
                                :title="
                                    activeCall.is_incoming && activeCall.status === 4 ? 'Decline Call' : 'Hangup Call'
                                "
                                type="button"
                                class="inline-flex items-center gap-x-2 rounded-2xl bg-red-600 px-6 py-4 text-lg font-bold text-white shadow-xl hover:bg-red-500 transition-all duration-200"
                                @click="hangupCall"
                            >
                                <MaterialDesignIcon icon-name="phone-hangup" class="size-6 rotate-[135deg]" />
                                <span>{{
                                    activeCall.is_incoming && activeCall.status === 4 ? "Decline" : "Hangup"
                                }}</span>
                            </button>
                        </div>

                        <!-- stats -->
                        <div
                            v-if="isShowingStats"
                            class="mt-4 p-4 text-left bg-gray-200 dark:bg-zinc-800 rounded-lg text-sm text-gray-600 dark:text-zinc-300"
                        >
                            <div class="grid grid-cols-2 gap-2">
                                <div>
                                    TX: {{ activeCall.tx_packets }} ({{ formatBytes(activeCall.tx_bytes) }})
                                </div>
                                <div>
                                    RX: {{ activeCall.rx_packets }} ({{ formatBytes(activeCall.rx_bytes) }})
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div v-else class="flex">
                <div class="mx-auto my-auto w-full">
                    <div class="text-center mb-4">
                        <div class="text-xl font-semibold text-gray-500 dark:text-zinc-100">Telephone</div>
                        <div class="text-gray-500 dark:text-zinc-400">Enter an identity hash to call.</div>
                    </div>

                    <div class="flex space-x-2">
                        <input
                            v-model="destinationHash"
                            type="text"
                            placeholder="Identity Hash"
                            class="block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm sm:leading-6 dark:bg-zinc-900 dark:text-zinc-100 dark:ring-zinc-800"
                            @keydown.enter="call(destinationHash)"
                        />
                        <button
                            type="button"
                            class="rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
                            @click="call(destinationHash)"
                        >
                            Call
                        </button>
                    </div>
                </div>
            </div>

            <div v-if="callHistory.length > 0 && !activeCall" class="mt-8">
                <div
                    class="bg-white dark:bg-zinc-900 rounded-xl shadow-sm border border-gray-200 dark:border-zinc-800 overflow-hidden"
                >
                    <div
                        class="px-4 py-3 border-b border-gray-200 dark:border-zinc-800 flex justify-between items-center"
                    >
                        <h3 class="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider">
                            Call History
                        </h3>
                        <MaterialDesignIcon icon-name="history" class="size-4 text-gray-400" />
                    </div>
                    <ul class="divide-y divide-gray-100 dark:divide-zinc-800">
                        <li
                            v-for="entry in callHistory"
                            :key="entry.id"
                            class="px-4 py-3 hover:bg-gray-50 dark:hover:bg-zinc-800/50 transition-colors"
                        >
                            <div class="flex items-center space-x-3">
                                <div :class="entry.is_incoming ? 'text-blue-500' : 'text-green-500'">
                                    <MaterialDesignIcon
                                        :icon-name="entry.is_incoming ? 'phone-incoming' : 'phone-outgoing'"
                                        class="size-5"
                                    />
                                </div>
                                <div class="flex-1 min-w-0">
                                    <div class="flex items-center justify-between">
                                        <p class="text-sm font-semibold text-gray-900 dark:text-white truncate">
                                            {{ entry.remote_identity_name || "Unknown" }}
                                        </p>
                                        <span class="text-[10px] text-gray-500 dark:text-zinc-500 font-mono ml-2">
                                            {{
                                                entry.timestamp
                                                    ? formatDateTime(
                                                          entry.timestamp * 1000
                                                      )
                                                    : ""
                                            }}
                                        </span>
                                    </div>
                                    <div class="flex items-center justify-between mt-0.5">
                                        <div
                                            class="flex items-center text-xs text-gray-500 dark:text-zinc-400 space-x-2"
                                        >
                                            <span>{{ entry.status }}</span>
                                            <span v-if="entry.duration_seconds > 0"
                                                >• {{ formatDuration(entry.duration_seconds) }}</span
                                            >
                                        </div>
                                        <button
                                            type="button"
                                            class="text-[10px] text-blue-500 hover:text-blue-600 font-bold uppercase tracking-tighter"
                                            @click="
                                                destinationHash = entry.remote_identity_hash;
                                                call(destinationHash);
                                            "
                                        >
                                            Call Back
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import Utils from "../../js/Utils";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";

export default {
    name: "CallPage",
    components: { MaterialDesignIcon },
    data() {
        return {
            config: null,
            activeCall: null,
            audioProfiles: [],
            selectedAudioProfileId: null,
            destinationHash: "",
            isShowingStats: false,
            callHistory: [],
            isCallEnded: false,
            lastCall: null,
            endedTimeout: null,
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
    mounted() {
        this.getConfig();
        this.getAudioProfiles();
        this.getStatus();
        this.getHistory();

        // poll for status
        this.statusInterval = setInterval(() => {
            this.getStatus();
        }, 1000);

        // poll for history less frequently
        this.historyInterval = setInterval(() => {
            this.getHistory();
        }, 10000);

        // autofill destination hash from query string
        const urlParams = new URLSearchParams(window.location.search);
        const destinationHash = urlParams.get("destination_hash");
        if (destinationHash) {
            this.destinationHash = destinationHash;
        }
    },
    beforeUnmount() {
        if (this.statusInterval) clearInterval(this.statusInterval);
        if (this.historyInterval) clearInterval(this.historyInterval);
        if (this.endedTimeout) clearTimeout(this.endedTimeout);
    },
    methods: {
        formatDestinationHash(hash) {
            return Utils.formatDestinationHash(hash);
        },
        formatBytes(bytes) {
            return Utils.formatBytes(bytes || 0);
        },
        formatDateTime(timestamp) {
            return Utils.convertUnixMillisToLocalDateTimeString(timestamp);
        },
        formatDuration(seconds) {
            return Utils.formatMinutesSeconds(seconds);
        },
        async getConfig() {
            try {
                const response = await window.axios.get("/api/v1/config");
                this.config = response.data.config;
            } catch (e) {
                console.log(e);
            }
        },
        async getAudioProfiles() {
            try {
                const response = await window.axios.get("/api/v1/telephone/audio-profiles");
                this.audioProfiles = response.data.audio_profiles;
                this.selectedAudioProfileId = response.data.default_audio_profile_id;
            } catch (e) {
                console.log(e);
            }
        },
        async getStatus() {
            try {
                const response = await window.axios.get("/api/v1/telephone/status");
                const oldCall = this.activeCall;
                this.activeCall = response.data.active_call;

                // If call just ended, refresh history and show ended state
                if (oldCall != null && this.activeCall == null) {
                    this.getHistory();
                    this.lastCall = oldCall;
                    this.isCallEnded = true;
                    
                    if (this.endedTimeout) clearTimeout(this.endedTimeout);
                    this.endedTimeout = setTimeout(() => {
                        this.isCallEnded = false;
                        this.lastCall = null;
                    }, 5000);
                } else if (this.activeCall != null) {
                    // if a new call starts, clear ended state
                    this.isCallEnded = false;
                    this.lastCall = null;
                    if (this.endedTimeout) clearTimeout(this.endedTimeout);
                }
            } catch (e) {
                console.log(e);
            }
        },
        async getHistory() {
            try {
                const response = await window.axios.get("/api/v1/telephone/history?limit=10");
                this.callHistory = response.data.call_history;
            } catch (e) {
                console.log(e);
            }
        },
        async call(identityHash) {
            if (!identityHash) {
                ToastUtils.error("Enter an identity hash to call");
                return;
            }
            try {
                await window.axios.get(`/api/v1/telephone/call/${identityHash}`);
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || "Failed to initiate call");
            }
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
        async switchAudioProfile(audioProfileId) {
            try {
                await window.axios.get(`/api/v1/telephone/switch-audio-profile/${audioProfileId}`);
            } catch {
                ToastUtils.error("Failed to switch audio profile");
            }
        },
        async toggleMicrophone() {
            try {
                const endpoint = this.isMicMuted
                    ? "/api/v1/telephone/unmute-transmit"
                    : "/api/v1/telephone/mute-transmit";
                await window.axios.get(endpoint);
                if (this.activeCall) {
                    this.activeCall.is_mic_muted = !this.isMicMuted;
                }
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
                if (this.activeCall) {
                    this.activeCall.is_speaker_muted = !this.isSpeakerMuted;
                }
            } catch {
                ToastUtils.error("Failed to toggle speaker");
            }
        },
    },
};
</script>
