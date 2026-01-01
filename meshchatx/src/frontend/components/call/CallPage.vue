<template>
    <div class="flex flex-col w-full h-full bg-gray-100 dark:bg-zinc-950" :class="{ dark: config?.theme === 'dark' }">
        <div class="w-full h-full overflow-y-auto">
            <div class="mx-auto w-full max-w-xl p-4 flex-1 flex flex-col min-h-full">
                <!-- Tabs -->
                <div class="flex border-b border-gray-200 dark:border-zinc-800 mb-6 shrink-0">
                    <button
                        :class="[
                            activeTab === 'phone'
                                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-zinc-400 dark:hover:text-zinc-200 hover:border-gray-300',
                        ]"
                        class="py-2 px-4 border-b-2 font-medium text-sm transition-all"
                        @click="activeTab = 'phone'"
                    >
                        Phone
                    </button>
                    <button
                        :class="[
                            activeTab === 'voicemail'
                                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-zinc-400 dark:hover:text-zinc-200 hover:border-gray-300',
                        ]"
                        class="py-2 px-4 border-b-2 font-medium text-sm flex items-center gap-2 transition-all"
                        @click="activeTab = 'voicemail'"
                    >
                        Voicemail
                        <span
                            v-if="unreadVoicemailsCount > 0"
                            class="bg-red-500 text-white text-[10px] px-1.5 py-0.5 rounded-full animate-pulse"
                            >{{ unreadVoicemailsCount }}</span
                        >
                    </button>
                    <button
                        :class="[
                            activeTab === 'settings'
                                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-zinc-400 dark:hover:text-zinc-200 hover:border-gray-300',
                        ]"
                        class="py-2 px-4 border-b-2 font-medium text-sm ml-auto transition-all"
                        @click="activeTab = 'settings'"
                    >
                        <MaterialDesignIcon icon-name="cog" class="size-4" />
                    </button>
                </div>

                <!-- Phone Tab -->
                <div v-if="activeTab === 'phone'" class="flex-1 flex flex-col">
                    <div v-if="activeCall || isCallEnded" class="flex mt-8 mb-12">
                        <div class="mx-auto min-w-64">
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
                                        <span
                                            v-if="activeCall.is_incoming && activeCall.status === 4"
                                            class="animate-bounce inline-block"
                                            >Incoming Call...</span
                                        >
                                        <span v-else>
                                            <span v-if="activeCall.status === 0">Busy...</span>
                                            <span v-else-if="activeCall.status === 1">Rejected...</span>
                                            <span v-else-if="activeCall.status === 2">Calling...</span>
                                            <span v-else-if="activeCall.status === 3">Available...</span>
                                            <span v-else-if="activeCall.status === 4">Ringing...</span>
                                            <span v-else-if="activeCall.status === 5">Connecting...</span>
                                            <span v-else-if="activeCall.status === 6" class="text-green-500 font-medium"
                                                >Connected</span
                                            >
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
                                            activeCall.is_incoming && activeCall.status === 4
                                                ? 'Decline Call'
                                                : 'Hangup Call'
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

                    <div v-else class="mt-8 mb-12">
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

                    <!-- Call History -->
                    <div v-if="callHistory.length > 0 && !activeCall && !isCallEnded" class="mt-4">
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
                                                <span
                                                    class="text-[10px] text-gray-500 dark:text-zinc-500 font-mono ml-2"
                                                >
                                                    {{ entry.timestamp ? formatDateTime(entry.timestamp * 1000) : "" }}
                                                </span>
                                            </div>
                                            <div class="flex items-start justify-between mt-0.5">
                                                <div class="flex-1 min-w-0">
                                                    <div
                                                        class="flex items-center text-xs text-gray-500 dark:text-zinc-400 space-x-2"
                                                    >
                                                        <span class="capitalize">{{ entry.status }}</span>
                                                        <span v-if="entry.duration_seconds > 0"
                                                            >• {{ formatDuration(entry.duration_seconds) }}</span
                                                        >
                                                    </div>
                                                    <div
                                                        class="text-[10px] text-gray-400 dark:text-zinc-600 font-mono truncate mt-0.5"
                                                    >
                                                        {{ entry.remote_identity_hash }}
                                                    </div>
                                                </div>
                                                <button
                                                    type="button"
                                                    class="text-[10px] text-blue-500 hover:text-blue-600 font-bold uppercase tracking-tighter ml-4"
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

                <!-- Voicemail Tab -->
                <div v-if="activeTab === 'voicemail'" class="flex-1 flex flex-col">
                    <div v-if="voicemails.length === 0" class="my-auto text-center">
                        <div class="bg-gray-200 dark:bg-zinc-800 p-6 rounded-full inline-block mb-4">
                            <MaterialDesignIcon icon-name="voicemail" class="size-12 text-gray-400" />
                        </div>
                        <h3 class="text-lg font-medium text-gray-900 dark:text-white">No Voicemails</h3>
                        <p class="text-gray-500 dark:text-zinc-400">
                            When people leave you messages, they'll show up here.
                        </p>
                    </div>

                    <div v-else class="space-y-4">
                        <div
                            class="bg-white dark:bg-zinc-900 rounded-xl shadow-sm border border-gray-200 dark:border-zinc-800 overflow-hidden"
                        >
                            <div
                                class="px-4 py-3 border-b border-gray-200 dark:border-zinc-800 flex justify-between items-center"
                            >
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
                                        <!-- Play/Pause Button -->
                                        <button
                                            class="shrink-0 size-10 rounded-full flex items-center justify-center transition-all"
                                            :class="
                                                playingVoicemailId === voicemail.id
                                                    ? 'bg-red-500 text-white animate-pulse'
                                                    : 'bg-blue-500 text-white hover:bg-blue-600'
                                            "
                                            @click="playVoicemail(voicemail)"
                                        >
                                            <MaterialDesignIcon
                                                :icon-name="playingVoicemailId === voicemail.id ? 'stop' : 'play'"
                                                class="size-6"
                                            />
                                        </button>

                                        <div class="flex-1 min-w-0">
                                            <div class="flex items-center justify-between mb-1">
                                                <p class="text-sm font-bold text-gray-900 dark:text-white truncate">
                                                    {{ voicemail.remote_identity_name || "Unknown" }}
                                                    <span
                                                        v-if="!voicemail.is_read"
                                                        class="ml-2 size-2 inline-block rounded-full bg-blue-500"
                                                    ></span>
                                                </p>
                                                <span class="text-[10px] text-gray-500 dark:text-zinc-500 font-mono">
                                                    {{ formatDateTime(voicemail.timestamp * 1000) }}
                                                </span>
                                            </div>

                                            <div
                                                class="flex items-center text-xs text-gray-500 dark:text-zinc-400 space-x-3 mb-3"
                                            >
                                                <span class="flex items-center gap-1">
                                                    <MaterialDesignIcon icon-name="clock-outline" class="size-3" />
                                                    {{ formatDuration(voicemail.duration_seconds) }}
                                                </span>
                                                <span class="opacity-60 font-mono text-[10px]">{{
                                                    formatDestinationHash(voicemail.remote_identity_hash)
                                                }}</span>
                                            </div>

                                            <div class="flex items-center gap-4">
                                                <button
                                                    type="button"
                                                    class="text-[10px] flex items-center gap-1 text-blue-500 hover:text-blue-600 font-bold uppercase tracking-wider transition-colors"
                                                    @click="
                                                        destinationHash = voicemail.remote_identity_hash;
                                                        activeTab = 'phone';
                                                        call(destinationHash);
                                                    "
                                                >
                                                    <MaterialDesignIcon icon-name="phone" class="size-3" />
                                                    Call Back
                                                </button>
                                                <button
                                                    type="button"
                                                    class="text-[10px] flex items-center gap-1 text-red-500 hover:text-red-600 font-bold uppercase tracking-wider transition-colors"
                                                    @click="deleteVoicemail(voicemail.id)"
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

                <!-- Settings Tab -->
                <div v-if="activeTab === 'settings' && config" class="flex-1 space-y-6">
                    <div
                        class="bg-white dark:bg-zinc-900 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-zinc-800"
                    >
                        <h3
                            class="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider mb-6 flex items-center gap-2"
                        >
                            <MaterialDesignIcon icon-name="voicemail" class="size-5 text-blue-500" />
                            Voicemail Settings
                        </h3>

                        <!-- Status Banner -->
                        <div
                            v-if="!voicemailStatus.has_espeak || !voicemailStatus.has_ffmpeg"
                            class="mb-6 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg flex gap-3 items-start"
                        >
                            <MaterialDesignIcon
                                icon-name="alert"
                                class="size-5 text-amber-600 dark:text-amber-400 shrink-0"
                            />
                            <div class="text-xs text-amber-800 dark:text-amber-200">
                                <p class="font-bold mb-1">Dependencies Missing</p>
                                <p v-if="!voicemailStatus.has_espeak">
                                    Voicemail requires `espeak-ng` to generate greetings. Please install it on your
                                    system.
                                </p>
                                <p v-if="!voicemailStatus.has_ffmpeg" :class="{ 'mt-1': !voicemailStatus.has_espeak }">
                                    Voicemail requires `ffmpeg` to process audio files. Please install it on your
                                    system.
                                </p>
                            </div>
                        </div>

                        <div class="space-y-6">
                            <!-- Enabled Toggle -->
                            <div class="flex items-center justify-between">
                                <div>
                                    <div class="text-sm font-semibold text-gray-900 dark:text-white">
                                        Enable Voicemail
                                    </div>
                                    <div class="text-xs text-gray-500 dark:text-zinc-400">
                                        Accept calls automatically and record messages
                                    </div>
                                </div>
                                <button
                                    :disabled="!voicemailStatus.has_espeak || !voicemailStatus.has_ffmpeg"
                                    class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
                                    :class="config.voicemail_enabled ? 'bg-blue-600' : 'bg-gray-200 dark:bg-zinc-700'"
                                    @click="
                                        config.voicemail_enabled = !config.voicemail_enabled;
                                        updateConfig({ voicemail_enabled: config.voicemail_enabled });
                                    "
                                >
                                    <span
                                        class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
                                        :class="config.voicemail_enabled ? 'translate-x-5' : 'translate-x-0'"
                                    ></span>
                                </button>
                            </div>

                            <!-- Greeting Text -->
                            <div class="space-y-2">
                                <label
                                    class="text-xs font-bold text-gray-500 dark:text-zinc-400 uppercase tracking-tighter"
                                    >Greeting Message</label
                                >
                                <textarea
                                    v-model="config.voicemail_greeting"
                                    rows="3"
                                    class="block w-full rounded-lg border-0 py-2 text-gray-900 dark:text-white shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm sm:leading-6 dark:bg-zinc-900"
                                    placeholder="Enter greeting text..."
                                ></textarea>
                                <div class="flex justify-between items-center">
                                    <p class="text-[10px] text-gray-500 dark:text-zinc-500">
                                        This text will be converted to speech using eSpeak NG.
                                    </p>
                                    <div class="flex gap-2">
                                        <button
                                            :disabled="
                                                !voicemailStatus.has_espeak ||
                                                !voicemailStatus.has_ffmpeg ||
                                                isGeneratingGreeting
                                            "
                                            class="text-[10px] bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 px-3 py-1 rounded-full font-bold hover:bg-gray-200 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50"
                                            @click="
                                                updateConfig({ voicemail_greeting: config.voicemail_greeting });
                                                generateGreeting();
                                            "
                                        >
                                            {{ isGeneratingGreeting ? "Generating..." : "Save & Generate" }}
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <!-- Custom Greeting Upload -->
                            <div class="space-y-2">
                                <label
                                    class="text-xs font-bold text-gray-500 dark:text-zinc-400 uppercase tracking-tighter"
                                    >Custom Audio Greeting</label
                                >
                                <div class="flex items-center gap-3">
                                    <input
                                        ref="greetingUpload"
                                        type="file"
                                        accept="audio/*"
                                        class="hidden"
                                        @change="uploadGreeting"
                                    />
                                    <button
                                        :disabled="!voicemailStatus.has_ffmpeg || isUploadingGreeting"
                                        class="text-xs bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 px-4 py-2 rounded-lg font-bold hover:bg-gray-200 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                                        @click="$refs.greetingUpload.click()"
                                    >
                                        <MaterialDesignIcon icon-name="upload" class="size-4" />
                                        {{ isUploadingGreeting ? "Uploading..." : "Upload Audio File" }}
                                    </button>
                                    <div v-if="voicemailStatus.has_greeting" class="flex items-center gap-2">
                                        <button
                                            class="text-xs bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 px-4 py-2 rounded-lg font-bold hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors flex items-center gap-2"
                                            @click="deleteGreeting"
                                        >
                                            <MaterialDesignIcon icon-name="delete" class="size-4" />
                                            Remove Greeting
                                        </button>
                                        <button
                                            class="text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 px-4 py-2 rounded-lg font-bold hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors flex items-center gap-2"
                                            @click="playGreeting"
                                        >
                                            <MaterialDesignIcon
                                                :icon-name="isPlayingGreeting ? 'stop' : 'play'"
                                                class="size-4"
                                            />
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
                                    <label
                                        class="text-xs font-bold text-gray-500 dark:text-zinc-400 uppercase tracking-tighter"
                                        >Answer Delay (s)</label
                                    >
                                    <input
                                        v-model.number="config.voicemail_auto_answer_delay_seconds"
                                        type="number"
                                        min="1"
                                        max="120"
                                        class="block w-full rounded-lg border-0 py-1.5 text-gray-900 dark:text-white shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
                                        @change="
                                            updateConfig({
                                                voicemail_auto_answer_delay_seconds:
                                                    config.voicemail_auto_answer_delay_seconds,
                                            })
                                        "
                                    />
                                </div>
                                <div class="space-y-2">
                                    <label
                                        class="text-xs font-bold text-gray-500 dark:text-zinc-400 uppercase tracking-tighter"
                                        >Max Recording (s)</label
                                    >
                                    <input
                                        v-model.number="config.voicemail_max_recording_seconds"
                                        type="number"
                                        min="5"
                                        max="600"
                                        class="block w-full rounded-lg border-0 py-1.5 text-gray-900 dark:text-white shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
                                        @change="
                                            updateConfig({
                                                voicemail_max_recording_seconds: config.voicemail_max_recording_seconds,
                                            })
                                        "
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
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
            activeTab: "phone",
            voicemails: [],
            unreadVoicemailsCount: 0,
            voicemailStatus: {
                has_espeak: false,
                has_ffmpeg: false,
                is_recording: false,
                has_greeting: false,
            },
            isGeneratingGreeting: false,
            isUploadingGreeting: false,
            playingVoicemailId: null,
            audioPlayer: null,
            isPlayingGreeting: false,
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
        this.getVoicemails();
        this.getVoicemailStatus();

        // poll for status
        this.statusInterval = setInterval(() => {
            this.getStatus();
            this.getVoicemailStatus();
        }, 1000);

        // poll for history/voicemails less frequently
        this.historyInterval = setInterval(() => {
            this.getHistory();
            this.getVoicemails();
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
        if (this.audioPlayer) {
            this.audioPlayer.pause();
            this.audioPlayer = null;
        }
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
        async updateConfig(config) {
            try {
                await window.axios.patch("/api/v1/config", config);
                await this.getConfig();
                ToastUtils.success("Settings saved");
            } catch {
                ToastUtils.error("Failed to save settings");
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

                if (response.data.voicemail) {
                    this.unreadVoicemailsCount = response.data.voicemail.unread_count;
                }

                // If call just ended, refresh history and show ended state
                if (oldCall != null && this.activeCall == null) {
                    this.getHistory();
                    this.getVoicemails();
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
        async getVoicemailStatus() {
            try {
                const response = await window.axios.get("/api/v1/telephone/voicemail/status");
                this.voicemailStatus = response.data;
            } catch (e) {
                console.log(e);
            }
        },
        async getVoicemails() {
            try {
                const response = await window.axios.get("/api/v1/telephone/voicemails");
                this.voicemails = response.data.voicemails;
                this.unreadVoicemailsCount = response.data.unread_count;
            } catch (e) {
                console.log(e);
            }
        },
        async generateGreeting() {
            this.isGeneratingGreeting = true;
            try {
                await window.axios.post("/api/v1/telephone/voicemail/generate-greeting");
                ToastUtils.success("Greeting generated successfully");
                await this.getVoicemailStatus();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || "Failed to generate greeting");
            } finally {
                this.isGeneratingGreeting = false;
            }
        },
        async uploadGreeting(event) {
            const file = event.target.files[0];
            if (!file) return;

            this.isUploadingGreeting = true;
            const formData = new FormData();
            formData.append("file", file);

            try {
                await window.axios.post("/api/v1/telephone/voicemail/greeting/upload", formData, {
                    headers: {
                        "Content-Type": "multipart/form-data",
                    },
                });
                ToastUtils.success("Greeting uploaded successfully");
                await this.getVoicemailStatus();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || "Failed to upload greeting");
            } finally {
                this.isUploadingGreeting = false;
                event.target.value = "";
            }
        },
        async deleteGreeting() {
            if (!confirm("Are you sure you want to delete your custom greeting?")) return;

            try {
                await window.axios.delete("/api/v1/telephone/voicemail/greeting");
                ToastUtils.success("Greeting deleted");
                await this.getVoicemailStatus();
            } catch (e) {
                ToastUtils.error("Failed to delete greeting");
            }
        },
        async playVoicemail(voicemail) {
            if (this.playingVoicemailId === voicemail.id) {
                this.audioPlayer.pause();
                this.playingVoicemailId = null;
                return;
            }

            if (this.audioPlayer) {
                this.audioPlayer.pause();
            }

            this.playingVoicemailId = voicemail.id;
            this.audioPlayer = new Audio(`/api/v1/telephone/voicemails/${voicemail.id}/audio`);
            this.audioPlayer.play();
            this.audioPlayer.onended = () => {
                this.playingVoicemailId = null;
            };

            // Mark as read
            if (!voicemail.is_read) {
                try {
                    await window.axios.post(`/api/v1/telephone/voicemails/${voicemail.id}/read`);
                    voicemail.is_read = 1;
                    this.unreadVoicemailsCount = Math.max(0, this.unreadVoicemailsCount - 1);
                } catch (e) {
                    console.error(e);
                }
            }
        },
        async deleteVoicemail(voicemailId) {
            try {
                await window.axios.delete(`/api/v1/telephone/voicemails/${voicemailId}`);
                this.getVoicemails();
                ToastUtils.success("Voicemail deleted");
            } catch {
                ToastUtils.error("Failed to delete voicemail");
            }
        },
        async playGreeting() {
            if (this.isPlayingGreeting) {
                this.audioPlayer.pause();
                this.isPlayingGreeting = false;
                return;
            }

            if (this.audioPlayer) {
                this.audioPlayer.pause();
            }

            this.isPlayingGreeting = true;
            this.audioPlayer = new Audio("/api/v1/telephone/voicemail/greeting/audio");
            this.audioPlayer.play().catch(() => {
                ToastUtils.error("No greeting audio found. Please generate one first.");
                this.isPlayingGreeting = false;
            });
            this.audioPlayer.onended = () => {
                this.isPlayingGreeting = false;
            };
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
