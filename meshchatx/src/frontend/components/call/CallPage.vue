<template>
    <div class="flex flex-col w-full h-full bg-gray-100 dark:bg-zinc-950">
        <div class="w-full h-full overflow-y-auto">
            <div class="mx-auto w-full max-w-4xl p-4 md:p-6 flex-1 flex flex-col min-h-full">
                <!-- Tabs -->
                <div class="flex flex-wrap justify-center border-b border-gray-200 dark:border-zinc-800 mb-6 shrink-0">
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
                            activeTab === 'phonebook'
                                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-zinc-400 dark:hover:text-zinc-200 hover:border-gray-300',
                        ]"
                        class="py-2 px-4 border-b-2 font-medium text-sm transition-all"
                        @click="activeTab = 'phonebook'"
                    >
                        Phonebook
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
                            activeTab === 'contacts'
                                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-zinc-400 dark:hover:text-zinc-200 hover:border-gray-300',
                        ]"
                        class="py-2 px-4 border-b-2 font-medium text-sm transition-all"
                        @click="activeTab = 'contacts'"
                    >
                        Contacts
                    </button>
                    <button
                        :class="[
                            activeTab === 'ringtone'
                                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-zinc-400 dark:hover:text-zinc-200 hover:border-gray-300',
                        ]"
                        class="py-2 px-4 border-b-2 font-medium text-sm transition-all"
                        @click="activeTab = 'ringtone'"
                    >
                        {{ $t("call.ringtone") }}
                    </button>
                    <!-- <button
                        :class="[
                            activeTab === 'recordings'
                                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-zinc-400 dark:hover:text-zinc-200 hover:border-gray-300',
                        ]"
                        class="py-2 px-4 border-b-2 font-medium text-sm transition-all"
                        @click="activeTab = 'recordings'"
                    >
                        {{ $t("call.recordings") }}
                    </button> -->
                </div>

                <!-- Phone Tab -->
                <div v-if="activeTab === 'phone'" class="flex-1 flex flex-col">
                    <div
                        v-if="activeCall || isCallEnded || initiationStatus"
                        class="flex-1 flex flex-col items-center justify-center py-12 px-4"
                    >
                        <div
                            class="glass-card w-full max-w-md !p-8 flex flex-col items-center text-center relative overflow-hidden"
                        >
                            <!-- Status pulse background -->
                            <div
                                v-if="activeCall && activeCall.status === 6"
                                class="absolute inset-0 bg-green-500/5 animate-pulse"
                            ></div>

                            <!-- Recording indicator -->
                            <div
                                v-if="activeCall && activeCall.is_recording"
                                class="absolute top-4 right-4 z-20 flex items-center gap-1.5 px-2 py-1 bg-red-500/10 rounded-full border border-red-500/20"
                            >
                                <div class="size-2 bg-red-500 rounded-full animate-pulse"></div>
                                <span class="text-[10px] font-bold text-red-500 uppercase tracking-wider"
                                    >Recording</span
                                >
                            </div>

                            <div class="relative mb-8">
                                <div
                                    class="size-32 mx-auto bg-gray-100 dark:bg-zinc-800 rounded-full flex items-center justify-center border-4 border-white dark:border-zinc-900 shadow-2xl relative z-10"
                                    :class="{
                                        'ring-4 ring-blue-500/20 animate-pulse': activeCall && activeCall.status === 4,
                                    }"
                                >
                                    <LxmfUserIcon
                                        :custom-image="(activeCall || lastCall)?.custom_image"
                                        :icon-name="
                                            (activeCall || lastCall)?.remote_icon
                                                ? (activeCall || lastCall).remote_icon.icon_name
                                                : ''
                                        "
                                        :icon-foreground-colour="
                                            (activeCall || lastCall)?.remote_icon
                                                ? (activeCall || lastCall).remote_icon.foreground_colour
                                                : ''
                                        "
                                        :icon-background-colour="
                                            (activeCall || lastCall)?.remote_icon
                                                ? (activeCall || lastCall).remote_icon.background_colour
                                                : ''
                                        "
                                        icon-class="size-28"
                                    />
                                </div>

                                <div
                                    v-if="activeCall && activeCall.status === 6"
                                    class="absolute -bottom-2 -right-2 bg-green-500 text-white p-2 rounded-full shadow-lg border-4 border-white dark:border-zinc-900 z-20"
                                >
                                    <MaterialDesignIcon icon-name="phone-in-talk" class="size-5" />
                                </div>
                            </div>

                            <div class="relative z-10 space-y-1 mb-8">
                                <h2 class="text-2xl font-bold text-gray-900 dark:text-white truncate max-w-[280px]">
                                    {{
                                        (activeCall || lastCall)?.remote_identity_name ||
                                        initiationTargetName ||
                                        $t("call.unknown")
                                    }}
                                </h2>
                                <div
                                    v-if="(activeCall || lastCall)?.remote_identity_hash || initiationTargetHash"
                                    class="text-xs font-mono text-gray-400 dark:text-zinc-500 tracking-wider"
                                >
                                    {{
                                        formatDestinationHash(
                                            (activeCall || lastCall)?.remote_identity_hash || initiationTargetHash
                                        )
                                    }}
                                </div>
                                <div
                                    v-if="(activeCall || lastCall)?.is_contact || !!initiationTargetName"
                                    class="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 text-[10px] font-bold rounded-full uppercase tracking-wider"
                                >
                                    <MaterialDesignIcon icon-name="check-decagram" class="size-3" />
                                    Contact
                                </div>
                            </div>

                            <!-- call status -->
                            <div class="relative z-10 mb-8">
                                <div
                                    class="px-4 py-2 bg-gray-50 dark:bg-zinc-800/50 rounded-2xl inline-block border border-gray-100 dark:border-zinc-800"
                                >
                                    <template v-if="wasDeclined">
                                        <span class="text-red-500 font-bold text-sm">{{
                                            $t("call.call_declined")
                                        }}</span>
                                    </template>
                                    <template v-else-if="isCallEnded">
                                        <span class="text-gray-500 dark:text-zinc-400 font-bold text-sm">{{
                                            $t("call.call_ended")
                                        }}</span>
                                    </template>
                                    <template v-else-if="activeCall">
                                        <div class="flex flex-col items-center">
                                            <span
                                                v-if="activeCall.is_voicemail"
                                                class="text-red-500 font-bold text-sm animate-pulse flex items-center gap-2"
                                            >
                                                <MaterialDesignIcon icon-name="record" class="size-4" />
                                                {{ $t("call.recording_voicemail") }}
                                            </span>
                                            <span
                                                v-else-if="
                                                    activeCall && activeCall.is_incoming && activeCall.status === 4
                                                "
                                                class="text-blue-600 dark:text-blue-400 font-bold text-sm animate-bounce"
                                                >{{ $t("call.incoming_call") }}</span
                                            >
                                            <span
                                                v-else
                                                class="text-gray-700 dark:text-zinc-300 font-bold text-sm flex items-center gap-2"
                                            >
                                                <span v-if="activeCall && activeCall.status === 0">Busy...</span>
                                                <span
                                                    v-else-if="activeCall && activeCall.status === 1"
                                                    class="text-red-500"
                                                    >Rejected</span
                                                >
                                                <span
                                                    v-else-if="activeCall && activeCall.status === 2"
                                                    class="animate-pulse"
                                                    >Calling...</span
                                                >
                                                <span v-else-if="activeCall && activeCall.status === 3">Available</span>
                                                <span
                                                    v-else-if="activeCall && activeCall.status === 4"
                                                    class="animate-pulse"
                                                    >Ringing...</span
                                                >
                                                <span v-else-if="activeCall && activeCall.status === 5"
                                                    >Connecting...</span
                                                >
                                                <span
                                                    v-else-if="activeCall && activeCall.status === 6"
                                                    class="text-green-500 flex items-center gap-2"
                                                >
                                                    <span class="size-2 bg-green-500 rounded-full animate-ping"></span>
                                                    Connected
                                                </span>
                                                <span v-else-if="activeCall">Status: {{ activeCall.status }}</span>
                                            </span>

                                            <!-- Duration -->
                                            <div
                                                v-if="activeCall && activeCall.status === 6 && elapsedTime"
                                                class="text-xs font-mono text-gray-400 dark:text-zinc-500 mt-1"
                                            >
                                                {{ elapsedTime }}
                                            </div>
                                        </div>
                                    </template>
                                    <template v-else-if="initiationStatus">
                                        <div class="flex flex-col items-center">
                                            <span
                                                class="text-blue-600 dark:text-blue-400 font-bold text-sm animate-pulse"
                                            >
                                                {{ initiationStatus }}
                                            </span>
                                        </div>
                                    </template>
                                </div>
                                <div
                                    v-if="isCallEnded && callDuration"
                                    class="text-xs font-mono text-gray-400 dark:text-zinc-500 mt-2"
                                >
                                    Duration: {{ callDuration }}
                                </div>
                                <!-- Play Voicemail Button -->
                                <div v-if="isCallEnded && wasVoicemail" class="mt-6 animate-fade-in">
                                    <button
                                        type="button"
                                        class="px-6 py-3 rounded-full bg-blue-500 hover:bg-blue-600 text-white font-bold flex items-center gap-2 shadow-lg shadow-blue-500/30 transition-all hover:scale-105"
                                        @click="playLatestVoicemail"
                                    >
                                        <MaterialDesignIcon
                                            :icon-name="playingVoicemailId ? 'stop' : 'play'"
                                            class="size-6"
                                        />
                                        <span>{{ playingVoicemailId ? "Stop" : "Play Voicemail" }}</span>
                                    </button>
                                </div>
                            </div>

                            <!-- settings during connected call -->
                            <div v-if="activeCall && activeCall.status === 6" class="w-full relative z-10 mb-8">
                                <div class="flex flex-col gap-4">
                                    <select
                                        v-model="selectedAudioProfileId"
                                        class="input-field !rounded-xl !py-2 shadow-sm"
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

                                    <div class="flex justify-center gap-4">
                                        <!-- mute/unmute mic -->
                                        <button
                                            type="button"
                                            :class="[
                                                isMicMuted
                                                    ? 'bg-red-500 text-white shadow-red-500/20'
                                                    : 'bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-200 hover:bg-gray-200 dark:hover:bg-zinc-700 shadow-gray-200/20 dark:shadow-black/20',
                                            ]"
                                            class="p-4 rounded-full shadow-lg transition-all duration-200"
                                            @click="toggleMicrophone"
                                        >
                                            <MaterialDesignIcon
                                                :icon-name="isMicMuted ? 'microphone-off' : 'microphone'"
                                                class="size-6"
                                            />
                                        </button>

                                        <!-- mute/unmute speaker -->
                                        <button
                                            type="button"
                                            :class="[
                                                isSpeakerMuted
                                                    ? 'bg-red-500 text-white shadow-red-500/20'
                                                    : 'bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-200 hover:bg-gray-200 dark:hover:bg-zinc-700 shadow-gray-200/20 dark:shadow-black/20',
                                            ]"
                                            class="p-4 rounded-full shadow-lg transition-all duration-200"
                                            @click="toggleSpeaker"
                                        >
                                            <MaterialDesignIcon
                                                :icon-name="isSpeakerMuted ? 'volume-off' : 'volume-high'"
                                                class="size-6"
                                            />
                                        </button>

                                        <!-- toggle stats -->
                                        <button
                                            type="button"
                                            :class="[
                                                isShowingStats
                                                    ? 'bg-blue-500 text-white shadow-blue-500/20'
                                                    : 'bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-200 hover:bg-gray-200 dark:hover:bg-zinc-700 shadow-gray-200/20 dark:shadow-black/20',
                                            ]"
                                            class="p-4 rounded-full shadow-lg transition-all duration-200"
                                            @click="isShowingStats = !isShowingStats"
                                        >
                                            <MaterialDesignIcon icon-name="chart-bar" class="size-6" />
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <!-- actions -->
                            <div v-if="activeCall" class="w-full relative z-10 flex flex-col gap-3">
                                <div class="flex gap-3">
                                    <!-- answer call -->
                                    <button
                                        v-if="activeCall && activeCall.is_incoming && activeCall.status === 4"
                                        type="button"
                                        class="flex-1 flex items-center justify-center gap-2 rounded-2xl bg-green-600 py-4 text-sm font-bold text-white shadow-xl shadow-green-600/20 hover:bg-green-500 transition-all duration-200"
                                        @click="answerCall"
                                    >
                                        <MaterialDesignIcon icon-name="phone" class="size-5" />
                                        <span>{{ $t("call.accept") }}</span>
                                    </button>

                                    <!-- send to voicemail -->
                                    <button
                                        v-if="activeCall && activeCall.is_incoming && activeCall.status === 4"
                                        type="button"
                                        class="flex-1 flex items-center justify-center gap-2 rounded-2xl bg-blue-600 py-4 text-sm font-bold text-white shadow-xl shadow-blue-600/20 hover:bg-blue-500 transition-all duration-200"
                                        @click="sendToVoicemail"
                                    >
                                        <MaterialDesignIcon icon-name="voicemail" class="size-5" />
                                        <span>Voicemail</span>
                                    </button>
                                </div>

                                <!-- hangup/decline call -->
                                <button
                                    type="button"
                                    class="w-full flex items-center justify-center gap-2 rounded-2xl bg-red-600 py-4 text-sm font-bold text-white shadow-xl shadow-red-600/20 hover:bg-red-500 transition-all duration-200"
                                    @click="hangupCall"
                                >
                                    <MaterialDesignIcon icon-name="phone-hangup" class="size-5 rotate-[135deg]" />
                                    <span>{{
                                        activeCall && activeCall.is_incoming && activeCall.status === 4
                                            ? $t("call.decline")
                                            : $t("call.hangup")
                                    }}</span>
                                </button>
                            </div>

                            <!-- stats -->
                            <div
                                v-if="isShowingStats && activeCall"
                                class="w-full mt-6 p-4 text-left bg-gray-50 dark:bg-zinc-800/50 rounded-2xl text-[10px] text-gray-500 dark:text-zinc-400 font-mono border border-gray-100 dark:border-zinc-800 relative z-10"
                            >
                                <div class="grid grid-cols-2 gap-4">
                                    <div class="flex flex-col gap-1">
                                        <div class="flex justify-between">
                                            <span>TX Pkts</span><span>{{ activeCall.tx_packets }}</span>
                                        </div>
                                        <div class="flex justify-between">
                                            <span>TX Data</span><span>{{ formatBytes(activeCall.tx_bytes) }}</span>
                                        </div>
                                    </div>
                                    <div class="flex flex-col gap-1">
                                        <div class="flex justify-between">
                                            <span>RX Pkts</span><span>{{ activeCall.rx_packets }}</span>
                                        </div>
                                        <div class="flex justify-between">
                                            <span>RX Data</span><span>{{ formatBytes(activeCall.rx_bytes) }}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div v-else class="space-y-6 my-6 max-w-3xl mx-auto w-full">
                        <div class="glass-card">
                            <div class="flex items-center gap-3 mb-6">
                                <div class="bg-blue-100 dark:bg-blue-900/30 p-2.5 rounded-2xl">
                                    <MaterialDesignIcon
                                        icon-name="phone-plus"
                                        class="size-6 text-blue-600 dark:text-blue-400"
                                    />
                                </div>
                                <div>
                                    <h2 class="text-lg font-bold text-gray-900 dark:text-white leading-tight">
                                        New Call
                                    </h2>
                                    <p class="text-xs text-gray-500 dark:text-zinc-400">Enter an identity to call.</p>
                                </div>
                            </div>

                            <div class="space-y-4">
                                <div class="relative">
                                    <div class="flex gap-2">
                                        <div class="relative flex-1">
                                            <input
                                                v-model="destinationHash"
                                                type="text"
                                                placeholder="Identity Hash or Name"
                                                class="input-field"
                                                @keydown.enter.prevent="handleCallInputEnter"
                                                @keydown.up.prevent="handleCallInputUp"
                                                @keydown.down.prevent="handleCallInputDown"
                                                @focus="isCallInputFocused = true"
                                                @blur="onCallInputBlur"
                                            />
                                            <!-- Suggestions Dropdown -->
                                            <div
                                                v-if="isCallInputFocused && newCallSuggestions.length > 0"
                                                class="absolute z-50 left-0 right-0 mt-1 bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 rounded-xl shadow-xl overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200"
                                            >
                                                <div
                                                    v-for="(suggestion, index) in newCallSuggestions"
                                                    :key="suggestion.hash"
                                                    class="px-4 py-2.5 flex items-center gap-3 cursor-pointer transition-colors"
                                                    :class="[
                                                        index === selectedSuggestionIndex
                                                            ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                                                            : 'hover:bg-gray-50 dark:hover:bg-zinc-800/50 text-gray-700 dark:text-zinc-300',
                                                    ]"
                                                    @mousedown.prevent="selectSuggestion(suggestion)"
                                                >
                                                    <div
                                                        class="shrink-0 size-8 rounded-full flex items-center justify-center text-xs"
                                                        :class="
                                                            suggestion.type === 'contact'
                                                                ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-600'
                                                                : 'bg-gray-100 dark:bg-zinc-800 text-gray-500'
                                                        "
                                                    >
                                                        <MaterialDesignIcon
                                                            :icon-name="suggestion.icon"
                                                            class="size-4"
                                                        />
                                                    </div>
                                                    <div class="flex-1 min-w-0">
                                                        <div class="text-sm font-bold truncate">
                                                            {{ suggestion.name }}
                                                        </div>
                                                        <div
                                                            class="text-[10px] font-mono opacity-50 truncate hover:text-blue-500 transition-colors cursor-copy"
                                                            :title="suggestion.hash"
                                                            @mousedown.stop="copyHash(suggestion.hash)"
                                                        >
                                                            {{ formatDestinationHash(suggestion.hash) }}
                                                        </div>
                                                    </div>
                                                    <div
                                                        v-if="suggestion.type === 'contact'"
                                                        class="text-[10px] uppercase font-bold tracking-widest opacity-30"
                                                    >
                                                        Contact
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        <button
                                            type="button"
                                            class="bg-blue-600 hover:bg-blue-500 text-white px-6 rounded-2xl font-bold shadow-lg shadow-blue-500/20 transition-all flex items-center gap-2"
                                            @click="call(destinationHash)"
                                        >
                                            <MaterialDesignIcon icon-name="phone" class="size-5" />
                                            Call
                                        </button>
                                    </div>
                                </div>

                                <div class="pt-2 flex items-start justify-between gap-4">
                                    <div class="flex flex-col gap-2 flex-1">
                                        <Toggle
                                            id="dnd-toggle"
                                            :model-value="config?.do_not_disturb_enabled"
                                            :label="$t('call.do_not_disturb')"
                                            @update:model-value="toggleDoNotDisturb"
                                        />
                                        <Toggle
                                            id="contacts-only-toggle"
                                            :model-value="config?.telephone_allow_calls_from_contacts_only"
                                            :label="$t('call.allow_calls_from_contacts_only')"
                                            @update:model-value="toggleAllowCallsFromContactsOnly"
                                        />
                                        <Toggle
                                            id="web-audio-toggle"
                                            :model-value="config?.telephone_web_audio_enabled"
                                            label="Browser/Electron Audio"
                                            @update:model-value="onToggleWebAudio"
                                        />
                                    </div>
                                    <div class="flex flex-col gap-2 shrink-0">
                                        <!-- <Toggle
                                            id="call-recording-toggle"
                                            :model-value="config?.call_recording_enabled"
                                            :label="$t('call.call_recording')"
                                            @update:model-value="toggleCallRecording"
                                        /> -->
                                        <div class="flex flex-col gap-1">
                                            <div
                                                class="text-[10px] font-bold text-gray-500 uppercase tracking-widest px-1"
                                            >
                                                {{ $t("call.default_quality") }}
                                            </div>
                                            <select
                                                v-if="config"
                                                v-model="config.telephone_audio_profile_id"
                                                class="input-field !py-1 !px-2 !text-xs !rounded-lg !border-gray-200 dark:!border-zinc-800 min-w-[120px]"
                                                @change="
                                                    updateConfig({
                                                        telephone_audio_profile_id: config.telephone_audio_profile_id,
                                                    })
                                                "
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

                                        <!-- Web Audio Device Selection -->
                                        <div
                                            v-if="config?.telephone_web_audio_enabled"
                                            class="flex flex-col gap-2 mt-2"
                                        >
                                            <div class="flex flex-col gap-1">
                                                <div
                                                    class="text-[10px] font-bold text-gray-500 uppercase tracking-widest px-1"
                                                >
                                                    Microphone
                                                </div>
                                                <select
                                                    v-model="selectedAudioInputId"
                                                    class="input-field !py-1 !px-2 !text-[10px] !rounded-lg !border-gray-200 dark:!border-zinc-800 min-w-[120px]"
                                                    @change="
                                                        stopWebAudio();
                                                        startWebAudio();
                                                    "
                                                >
                                                    <option
                                                        v-for="d in audioInputDevices"
                                                        :key="d.deviceId"
                                                        :value="d.deviceId"
                                                    >
                                                        {{ d.label || "Microphone" }}
                                                    </option>
                                                </select>
                                            </div>
                                            <div class="flex flex-col gap-1">
                                                <div
                                                    class="text-[10px] font-bold text-gray-500 uppercase tracking-widest px-1"
                                                >
                                                    Speaker
                                                </div>
                                                <select
                                                    v-model="selectedAudioOutputId"
                                                    class="input-field !py-1 !px-2 !text-[10px] !rounded-lg !border-gray-200 dark:!border-zinc-800 min-w-[120px]"
                                                    @change="
                                                        stopWebAudio();
                                                        startWebAudio();
                                                    "
                                                >
                                                    <option
                                                        v-for="d in audioOutputDevices"
                                                        :key="d.deviceId"
                                                        :value="d.deviceId"
                                                    >
                                                        {{ d.label || "Speaker" }}
                                                    </option>
                                                </select>
                                            </div>
                                            <button
                                                class="text-[10px] bg-gray-100 text-gray-600 dark:bg-zinc-800 dark:text-zinc-400 py-1 rounded-lg font-bold uppercase tracking-wider hover:bg-gray-200 dark:hover:bg-zinc-700 transition-colors"
                                                type="button"
                                                @click="requestAudioPermission"
                                            >
                                                Refresh Devices
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Call History -->
                    <div
                        v-if="callHistory.length > 0 && !activeCall && !isCallEnded"
                        class="space-y-4 max-w-3xl mx-auto w-full"
                    >
                        <div class="glass-card !p-0 overflow-hidden">
                            <div
                                class="px-5 py-4 border-b border-gray-100 dark:border-zinc-800 flex flex-col gap-4 bg-gray-50/50 dark:bg-zinc-800/20"
                            >
                                <div class="flex justify-between items-center">
                                    <div class="flex items-center gap-2">
                                        <div class="p-1.5 bg-gray-200/50 dark:bg-zinc-800 rounded-lg">
                                            <MaterialDesignIcon
                                                icon-name="history"
                                                class="size-4 text-gray-600 dark:text-zinc-400"
                                            />
                                        </div>
                                        <h3
                                            class="text-xs font-bold text-gray-500 dark:text-zinc-400 uppercase tracking-widest"
                                        >
                                            Call History
                                        </h3>
                                    </div>
                                    <button
                                        type="button"
                                        class="text-[10px] text-gray-400 hover:text-red-500 font-bold uppercase tracking-wider transition-colors bg-white dark:bg-zinc-900 px-2 py-1 rounded-md border border-gray-200 dark:border-zinc-800"
                                        @click="clearHistory"
                                    >
                                        {{ $t("app.clear_history") }}
                                    </button>
                                </div>
                                <div class="relative">
                                    <input
                                        v-model="callHistorySearch"
                                        type="text"
                                        :placeholder="$t('call.search_history')"
                                        class="input-field !py-2 !pl-10"
                                        @input="onCallHistorySearchInput"
                                    />
                                    <MaterialDesignIcon
                                        icon-name="magnify"
                                        class="absolute left-3.5 top-1/2 -translate-y-1/2 size-4 text-gray-400"
                                    />
                                </div>
                            </div>
                            <ul class="divide-y divide-gray-100 dark:divide-zinc-800">
                                <li
                                    v-for="entry in callHistory"
                                    :key="entry.id"
                                    class="px-5 py-4 hover:bg-blue-50/30 dark:hover:bg-blue-900/10 transition-colors group"
                                >
                                    <div class="flex items-center space-x-4">
                                        <div class="relative shrink-0">
                                            <LxmfUserIcon
                                                :custom-image="
                                                    getContactByHash(entry.remote_identity_hash)?.custom_image
                                                "
                                                :icon-name="entry.remote_icon ? entry.remote_icon.icon_name : ''"
                                                :icon-foreground-colour="
                                                    entry.remote_icon ? entry.remote_icon.foreground_colour : ''
                                                "
                                                :icon-background-colour="
                                                    entry.remote_icon ? entry.remote_icon.background_colour : ''
                                                "
                                                icon-class="size-10"
                                            />
                                            <div
                                                class="absolute -bottom-1 -right-1 bg-white dark:bg-zinc-900 rounded-full p-0.5 shadow-sm border border-gray-100 dark:border-zinc-800 shrink-0 flex items-center justify-center size-5"
                                            >
                                                <MaterialDesignIcon
                                                    :icon-name="entry.is_incoming ? 'phone-incoming' : 'phone-outgoing'"
                                                    :class="entry.is_incoming ? 'text-blue-500' : 'text-green-500'"
                                                    class="size-3"
                                                />
                                            </div>
                                        </div>

                                        <div class="flex-1 min-w-0">
                                            <div class="flex items-center justify-between">
                                                <div class="text-sm font-bold text-gray-900 dark:text-white truncate">
                                                    {{ entry.remote_identity_name || $t("call.unknown") }}
                                                </div>
                                                <div
                                                    class="text-[10px] text-gray-500 dark:text-zinc-500 font-mono shrink-0"
                                                >
                                                    {{ entry.timestamp ? formatDateTime(entry.timestamp * 1000) : "" }}
                                                </div>
                                            </div>

                                            <div class="flex items-center justify-between mt-0.5">
                                                <div class="min-w-0">
                                                    <div
                                                        class="flex items-center gap-2 text-[10px] text-gray-500 dark:text-zinc-400"
                                                    >
                                                        <span class="capitalize">{{ entry.status }}</span>
                                                        <span
                                                            v-if="entry.duration_seconds > 0"
                                                            class="text-gray-300 dark:text-zinc-700"
                                                            >•</span
                                                        >
                                                        <span v-if="entry.duration_seconds > 0">{{
                                                            formatDuration(entry.duration_seconds)
                                                        }}</span>
                                                    </div>
                                                    <div
                                                        class="text-[10px] font-mono text-gray-400 dark:text-zinc-600 truncate mt-0.5 cursor-pointer hover:text-blue-500 transition-colors"
                                                        :title="
                                                            entry.remote_telephony_hash ||
                                                            entry.remote_destination_hash ||
                                                            entry.remote_identity_hash
                                                        "
                                                        @click.stop="
                                                            copyHash(
                                                                entry.remote_telephony_hash ||
                                                                    entry.remote_destination_hash ||
                                                                    entry.remote_identity_hash
                                                            )
                                                        "
                                                    >
                                                        {{
                                                            formatDestinationHash(
                                                                entry.remote_telephony_hash ||
                                                                    entry.remote_destination_hash ||
                                                                    entry.remote_identity_hash
                                                            )
                                                        }}
                                                    </div>
                                                </div>

                                                <div
                                                    class="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0 ml-4"
                                                >
                                                    <button
                                                        v-if="!entry.is_contact"
                                                        type="button"
                                                        class="p-1.5 rounded-lg text-gray-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all shrink-0"
                                                        title="Add to contacts"
                                                        @click="addContactFromHistory(entry)"
                                                    >
                                                        <MaterialDesignIcon icon-name="account-plus" class="size-4" />
                                                    </button>
                                                    <button
                                                        type="button"
                                                        class="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all shrink-0"
                                                        :title="$t('common.block')"
                                                        @click="blockIdentity(entry.remote_identity_hash)"
                                                    >
                                                        <MaterialDesignIcon icon-name="account-remove" class="size-4" />
                                                    </button>
                                                    <button
                                                        type="button"
                                                        class="flex items-center gap-1.5 px-3 py-1 bg-blue-600 text-white rounded-lg text-[10px] font-bold hover:bg-blue-500 transition-all shadow-md shadow-blue-500/10 shrink-0"
                                                        @click="
                                                            destinationHash =
                                                                entry.remote_telephony_hash ||
                                                                entry.remote_destination_hash ||
                                                                entry.remote_identity_hash;
                                                            activeTab = 'phone';
                                                            $nextTick(() => call(destinationHash));
                                                        "
                                                    >
                                                        <MaterialDesignIcon icon-name="phone" class="size-3" />
                                                        {{ $t("call.call_back") }}
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </li>
                            </ul>
                            <div
                                v-if="hasMoreCallHistory"
                                class="p-4 border-t border-gray-100 dark:border-zinc-800 text-center bg-gray-50/30 dark:bg-zinc-800/10"
                            >
                                <button
                                    type="button"
                                    class="text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline uppercase tracking-wider"
                                    @click="loadMoreCallHistory"
                                >
                                    {{ $t("call.load_more") }}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Phonebook Tab -->
                <div v-if="activeTab === 'phonebook'" class="flex-1 flex flex-col max-w-3xl mx-auto w-full">
                    <div class="mb-4">
                        <div class="relative">
                            <input
                                v-model="discoverySearch"
                                type="text"
                                :placeholder="`Search phonebook (${totalDiscoveryCount})...`"
                                class="block w-full rounded-lg border-0 py-2 pl-10 text-gray-900 dark:text-white shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
                                @input="onDiscoverySearchInput"
                            />
                            <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                                <MaterialDesignIcon icon-name="magnify" class="size-5 text-gray-400" />
                            </div>
                        </div>
                    </div>

                    <div v-if="discoveryAnnounces.length === 0" class="my-auto text-center">
                        <div class="bg-gray-200 dark:bg-zinc-800 p-6 rounded-full inline-block mb-4">
                            <MaterialDesignIcon icon-name="satellite-uplink" class="size-12 text-gray-400" />
                        </div>
                        <h3 class="text-lg font-medium text-gray-900 dark:text-white">No Telephony Peers</h3>
                        <p class="text-gray-500 dark:text-zinc-400">Waiting for announces on the mesh.</p>
                    </div>

                    <div v-else class="space-y-4">
                        <div
                            class="bg-white dark:bg-zinc-900 rounded-xl shadow-sm border border-gray-200 dark:border-zinc-800 overflow-hidden"
                        >
                            <ul class="divide-y divide-gray-100 dark:divide-zinc-800">
                                <li
                                    v-for="announce in discoveryAnnounces"
                                    :key="announce.destination_hash"
                                    class="px-4 py-4 hover:bg-gray-50 dark:hover:bg-zinc-800/50 transition-colors"
                                >
                                    <div class="flex items-center space-x-4">
                                        <div class="shrink-0">
                                            <LxmfUserIcon
                                                v-if="announce.lxmf_user_icon"
                                                :icon-name="announce.lxmf_user_icon.icon_name"
                                                :icon-foreground-colour="announce.lxmf_user_icon.foreground_colour"
                                                :icon-background-colour="announce.lxmf_user_icon.background_colour"
                                                class="size-10"
                                            />
                                            <div
                                                v-else
                                                class="size-10 rounded-full bg-blue-50 dark:bg-blue-900/20 text-blue-500 flex items-center justify-center font-bold shrink-0"
                                            >
                                                {{ (announce.display_name || "A")[0].toUpperCase() }}
                                            </div>
                                        </div>
                                        <div class="flex-1 min-w-0">
                                            <div class="flex items-center justify-between">
                                                <div class="flex items-center min-w-0">
                                                    <p class="text-sm font-bold text-gray-900 dark:text-white truncate">
                                                        {{ announce.display_name || "Anonymous Peer" }}
                                                    </p>
                                                    <a
                                                        v-if="announce.lxmf_destination_hash"
                                                        :href="`/#/messages/${announce.lxmf_destination_hash}`"
                                                        class="ml-2 p-1 text-gray-400 hover:text-blue-500 transition-colors"
                                                        title="Message via LXMF"
                                                        @click.stop
                                                    >
                                                        <MaterialDesignIcon
                                                            icon-name="message-text-outline"
                                                            class="size-4"
                                                        />
                                                    </a>
                                                </div>
                                                <span
                                                    class="text-[10px] text-gray-500 dark:text-zinc-500 font-mono ml-2 shrink-0"
                                                >
                                                    {{ formatTimeAgo(announce.updated_at) }} ago
                                                </span>
                                            </div>
                                            <div class="flex items-center justify-between mt-1">
                                                <div class="flex items-center space-x-2 min-w-0">
                                                    <span
                                                        class="text-[10px] text-gray-500 dark:text-zinc-500 font-mono truncate cursor-pointer hover:text-blue-500 transition-colors"
                                                        :title="announce.destination_hash"
                                                        @click.stop="copyHash(announce.destination_hash)"
                                                    >
                                                        {{ formatDestinationHash(announce.destination_hash) }}
                                                    </span>
                                                    <span
                                                        v-if="announce.hops != null"
                                                        class="text-[10px] text-gray-400 dark:text-zinc-600"
                                                    >
                                                        • {{ announce.hops }} hops
                                                    </span>
                                                </div>
                                                <button
                                                    type="button"
                                                    class="text-[10px] bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 px-3 py-1 rounded-full font-bold uppercase tracking-wider hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors shrink-0"
                                                    @click="
                                                        destinationHash = announce.destination_hash;
                                                        activeTab = 'phone';
                                                        $nextTick(() => call(destinationHash));
                                                    "
                                                >
                                                    Call
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </li>
                            </ul>
                            <div
                                v-if="hasMoreDiscovery"
                                class="p-3 border-t border-gray-100 dark:border-zinc-800 text-center"
                            >
                                <button
                                    type="button"
                                    class="text-xs text-blue-500 hover:text-blue-600 font-bold uppercase tracking-widest"
                                    @click="loadMoreDiscovery"
                                >
                                    {{ $t("call.load_more") }}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Voicemail Tab -->
                <div v-if="activeTab === 'voicemail'" class="flex-1 flex flex-col max-w-3xl mx-auto w-full">
                    <div class="mb-4">
                        <div class="relative">
                            <input
                                v-model="voicemailSearch"
                                type="text"
                                placeholder="Search voicemails..."
                                class="block w-full rounded-lg border-0 py-2 pl-10 text-gray-900 dark:text-white shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
                                @input="onVoicemailSearchInput"
                            />
                            <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                                <MaterialDesignIcon icon-name="magnify" class="size-5 text-gray-400" />
                            </div>
                        </div>
                    </div>

                    <!-- Voicemail Settings Card -->
                    <div
                        v-if="config"
                        class="mb-4 bg-white dark:bg-zinc-900 rounded-xl shadow-sm border border-gray-200 dark:border-zinc-800 overflow-hidden"
                    >
                        <button
                            type="button"
                            class="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-zinc-800/50 transition-colors"
                            @click="isVoicemailSettingsExpanded = !isVoicemailSettingsExpanded"
                        >
                            <div class="flex items-center gap-2">
                                <MaterialDesignIcon icon-name="cog" class="size-5 text-blue-500" />
                                <h3 class="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider">
                                    Voicemail Settings
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
                                v-if="!voicemailStatus.has_espeak || !voicemailStatus.has_ffmpeg"
                                class="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg flex gap-3 items-start"
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
                                    <p
                                        v-if="!voicemailStatus.has_ffmpeg"
                                        :class="{ 'mt-1': !voicemailStatus.has_espeak }"
                                    >
                                        Voicemail requires `ffmpeg` to process audio files. Please install it on your
                                        system.
                                    </p>
                                </div>
                            </div>

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

                                <!-- TTS Settings -->
                                <div class="grid grid-cols-2 gap-3 mt-2">
                                    <div class="space-y-1">
                                        <label
                                            class="text-[10px] font-bold text-gray-500 dark:text-zinc-500 uppercase tracking-tighter"
                                            >{{ $t("call.tts_speed") }}</label
                                        >
                                        <input
                                            v-model.number="config.voicemail_tts_speed"
                                            type="number"
                                            min="80"
                                            max="450"
                                            class="block w-full rounded-lg border-0 py-1 text-gray-900 dark:text-white shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-blue-600 text-xs dark:bg-zinc-900"
                                            @change="updateConfig({ voicemail_tts_speed: config.voicemail_tts_speed })"
                                        />
                                    </div>
                                    <div class="space-y-1">
                                        <label
                                            class="text-[10px] font-bold text-gray-500 dark:text-zinc-500 uppercase tracking-tighter"
                                            >{{ $t("call.tts_pitch") }}</label
                                        >
                                        <input
                                            v-model.number="config.voicemail_tts_pitch"
                                            type="number"
                                            min="0"
                                            max="99"
                                            class="block w-full rounded-lg border-0 py-1 text-gray-900 dark:text-white shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-blue-600 text-xs dark:bg-zinc-900"
                                            @change="updateConfig({ voicemail_tts_pitch: config.voicemail_tts_pitch })"
                                        />
                                    </div>
                                    <div class="space-y-1">
                                        <label
                                            class="text-[10px] font-bold text-gray-500 dark:text-zinc-500 uppercase tracking-tighter"
                                            >{{ $t("call.tts_word_gap") }}</label
                                        >
                                        <input
                                            v-model.number="config.voicemail_tts_word_gap"
                                            type="number"
                                            min="0"
                                            max="100"
                                            class="block w-full rounded-lg border-0 py-1 text-gray-900 dark:text-white shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-blue-600 text-xs dark:bg-zinc-900"
                                            @change="
                                                updateConfig({ voicemail_tts_word_gap: config.voicemail_tts_word_gap })
                                            "
                                        />
                                    </div>
                                    <div class="space-y-1">
                                        <label
                                            class="text-[10px] font-bold text-gray-500 dark:text-zinc-500 uppercase tracking-tighter"
                                            >{{ $t("call.tts_voice") }}</label
                                        >
                                        <input
                                            v-model="config.voicemail_tts_voice"
                                            type="text"
                                            class="block w-full rounded-lg border-0 py-1 text-gray-900 dark:text-white shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 focus:ring-2 focus:ring-inset focus:ring-blue-600 text-xs dark:bg-zinc-900"
                                            @change="updateConfig({ voicemail_tts_voice: config.voicemail_tts_voice })"
                                        />
                                    </div>
                                </div>

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
                                <div class="flex items-center gap-3 flex-wrap">
                                    <input
                                        ref="greetingUpload"
                                        type="file"
                                        accept="audio/*"
                                        class="hidden"
                                        @change="uploadGreeting"
                                    />
                                    <button
                                        :disabled="
                                            !voicemailStatus.has_ffmpeg ||
                                            isUploadingGreeting ||
                                            voicemailStatus.is_greeting_recording
                                        "
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
                                                ? stopRecordingGreetingMic()
                                                : startRecordingGreetingMic()
                                        "
                                    >
                                        <MaterialDesignIcon
                                            :icon-name="voicemailStatus.is_greeting_recording ? 'stop' : 'microphone'"
                                            class="size-4"
                                        />
                                        {{
                                            voicemailStatus.is_greeting_recording ? "Stop Recording" : "Record from Mic"
                                        }}
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
                                        <!-- Icon / Play/Pause Button -->
                                        <div class="relative shrink-0">
                                            <LxmfUserIcon
                                                :custom-image="
                                                    getContactByHash(voicemail.remote_identity_hash)?.custom_image
                                                "
                                                :icon-name="
                                                    voicemail.remote_icon ? voicemail.remote_icon.icon_name : ''
                                                "
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
                                                <span
                                                    class="text-[10px] text-gray-500 dark:text-zinc-500 font-mono shrink-0"
                                                >
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
                                                <span
                                                    class="opacity-60 font-mono text-[10px] truncate cursor-pointer hover:text-blue-500 transition-colors"
                                                    :title="voicemail.remote_identity_hash"
                                                    @click.stop="copyHash(voicemail.remote_identity_hash)"
                                                    >{{ formatDestinationHash(voicemail.remote_identity_hash) }}</span
                                                >
                                            </div>

                                            <div class="mb-4">
                                                <AudioWaveformPlayer
                                                    :src="`/api/v1/telephone/voicemails/${voicemail.id}/audio`"
                                                    @play="markVoicemailAsRead(voicemail)"
                                                />
                                            </div>

                                            <div class="flex items-center gap-4">
                                                <button
                                                    type="button"
                                                    class="text-[10px] flex items-center gap-1 text-gray-500 hover:text-blue-500 font-bold uppercase tracking-wider transition-colors"
                                                    @click="
                                                        destinationHash =
                                                            voicemail.remote_telephony_hash ||
                                                            voicemail.remote_destination_hash ||
                                                            voicemail.remote_identity_hash;
                                                        activeTab = 'phone';
                                                        $nextTick(() => call(destinationHash));
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

                <!-- Contacts Tab -->
                <div v-if="activeTab === 'contacts'" class="flex-1 flex flex-col max-w-3xl mx-auto w-full">
                    <div class="mb-4 flex gap-2">
                        <div class="relative flex-1">
                            <input
                                v-model="contactsSearch"
                                type="text"
                                placeholder="Search contacts..."
                                class="block w-full rounded-lg border-0 py-2 pl-10 text-gray-900 dark:text-white shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
                                @input="onContactsSearchInput"
                            />
                            <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                                <MaterialDesignIcon icon-name="magnify" class="size-5 text-gray-400" />
                            </div>
                        </div>
                        <button
                            type="button"
                            class="rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 transition-colors flex items-center gap-2"
                            @click="openAddContactModal"
                        >
                            <MaterialDesignIcon icon-name="plus" class="size-5" />
                            Add
                        </button>
                    </div>

                    <div v-if="contacts.length === 0" class="my-auto text-center">
                        <div class="bg-gray-200 dark:bg-zinc-800 p-6 rounded-full inline-block mb-4">
                            <MaterialDesignIcon icon-name="account-multiple" class="size-12 text-gray-400" />
                        </div>
                        <h3 class="text-lg font-medium text-gray-900 dark:text-white">No Contacts</h3>
                        <p class="text-gray-500 dark:text-zinc-400">Add contacts to quickly call them.</p>
                    </div>

                    <div v-else class="space-y-4">
                        <div
                            class="bg-white dark:bg-zinc-900 rounded-xl shadow-sm border border-gray-200 dark:border-zinc-800 overflow-hidden"
                        >
                            <ul class="divide-y divide-gray-100 dark:divide-zinc-800">
                                <li
                                    v-for="contact in contacts"
                                    :key="contact.id"
                                    class="px-4 py-3 hover:bg-gray-50 dark:hover:bg-zinc-800/50 transition-colors"
                                >
                                    <div class="flex items-center space-x-3">
                                        <div class="shrink-0">
                                            <LxmfUserIcon
                                                :custom-image="contact.custom_image"
                                                :icon-name="contact.remote_icon ? contact.remote_icon.icon_name : ''"
                                                :icon-foreground-colour="
                                                    contact.remote_icon ? contact.remote_icon.foreground_colour : ''
                                                "
                                                :icon-background-colour="
                                                    contact.remote_icon ? contact.remote_icon.background_colour : ''
                                                "
                                                class="size-10"
                                            />
                                        </div>
                                        <div class="flex-1 min-w-0">
                                            <div class="flex items-center justify-between">
                                                <p class="text-sm font-bold text-gray-900 dark:text-white truncate">
                                                    {{ contact.name }}
                                                </p>
                                                <div class="flex items-center gap-2">
                                                    <span
                                                        v-if="contact.preferred_ringtone_id"
                                                        class="text-[9px] px-1.5 py-0.5 rounded bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 border border-amber-100 dark:border-amber-800/50 flex items-center gap-1"
                                                        title="Custom Ringtone Set"
                                                    >
                                                        <MaterialDesignIcon icon-name="music" class="size-2.5" />
                                                        {{ contact.preferred_ringtone_id === -1 ? "Random" : "Custom" }}
                                                    </span>
                                                    <div class="flex items-center gap-1">
                                                        <button
                                                            type="button"
                                                            class="p-1.5 text-gray-400 hover:text-blue-500 transition-colors"
                                                            @click="openEditContactModal(contact)"
                                                        >
                                                            <MaterialDesignIcon icon-name="pencil" class="size-4" />
                                                        </button>
                                                        <button
                                                            type="button"
                                                            class="p-1.5 text-gray-400 hover:text-red-500 transition-colors"
                                                            @click="deleteContact(contact.id)"
                                                        >
                                                            <MaterialDesignIcon icon-name="delete" class="size-4" />
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                            <div class="flex items-center justify-between mt-1">
                                                <span
                                                    class="text-[10px] text-gray-500 dark:text-zinc-500 font-mono truncate cursor-pointer hover:text-blue-500 transition-colors"
                                                    :title="contact.remote_identity_hash"
                                                    @click.stop="copyHash(contact.remote_identity_hash)"
                                                >
                                                    {{ formatDestinationHash(contact.remote_identity_hash) }}
                                                </span>
                                                <button
                                                    type="button"
                                                    class="text-[10px] bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 px-3 py-1 rounded-full font-bold uppercase tracking-wider hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors"
                                                    @click="
                                                        destinationHash =
                                                            contact.remote_telephony_hash ||
                                                            contact.remote_destination_hash ||
                                                            contact.remote_identity_hash;
                                                        activeTab = 'phone';
                                                        $nextTick(() => call(destinationHash));
                                                    "
                                                >
                                                    Call
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </li>
                            </ul>
                        </div>
                    </div>
                </div>

                <!-- Ringtone Tab -->
                <div v-if="activeTab === 'ringtone' && config" class="flex-1 space-y-6 max-w-3xl mx-auto w-full">
                    <div
                        class="bg-white dark:bg-zinc-900 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-zinc-800"
                    >
                        <template v-if="isRingtoneEditorOpen">
                            <RingtoneEditor
                                :ringtone="editingRingtoneForAudio"
                                @close="isRingtoneEditorOpen = false"
                                @saved="onRingtoneSaved"
                            />
                        </template>
                        <template v-else>
                            <h3
                                class="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider mb-6 flex items-center gap-2"
                            >
                                <MaterialDesignIcon icon-name="music" class="size-5 text-blue-500" />
                                {{ $t("call.ringtone_settings") }}
                            </h3>

                            <div class="space-y-6">
                                <!-- Enabled Toggle & Volume -->
                                <div class="flex flex-col md:flex-row md:items-center justify-between gap-6">
                                    <div class="flex-1">
                                        <div class="flex items-center justify-between mb-1">
                                            <div class="text-sm font-semibold text-gray-900 dark:text-white">
                                                {{ $t("call.enable_custom_ringtone") }}
                                            </div>
                                            <button
                                                class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none"
                                                :class="
                                                    config.custom_ringtone_enabled
                                                        ? 'bg-blue-600'
                                                        : 'bg-gray-200 dark:bg-zinc-700'
                                                "
                                                @click="
                                                    config.custom_ringtone_enabled = !config.custom_ringtone_enabled;
                                                    updateConfig({
                                                        custom_ringtone_enabled: config.custom_ringtone_enabled,
                                                    });
                                                "
                                            >
                                                <span
                                                    class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
                                                    :class="
                                                        config.custom_ringtone_enabled
                                                            ? 'translate-x-5'
                                                            : 'translate-x-0'
                                                    "
                                                ></span>
                                            </button>
                                        </div>
                                        <div class="text-xs text-gray-500 dark:text-zinc-400">
                                            {{ $t("call.enable_custom_ringtone_description") }}
                                        </div>
                                    </div>

                                    <div class="flex-1 md:max-w-xs">
                                        <div class="flex items-center justify-between mb-2">
                                            <label
                                                class="text-xs font-bold text-gray-500 dark:text-zinc-400 uppercase tracking-wider"
                                            >
                                                {{ $t("call.ringtone_volume") }}
                                            </label>
                                            <span class="text-xs font-mono text-gray-400"
                                                >{{ config.ringtone_volume }}%</span
                                            >
                                        </div>
                                        <input
                                            v-model.number="config.ringtone_volume"
                                            type="range"
                                            min="0"
                                            max="100"
                                            class="w-full h-1.5 bg-gray-200 dark:bg-zinc-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
                                            @change="updateConfig({ ringtone_volume: config.ringtone_volume })"
                                        />
                                    </div>
                                </div>

                                <!-- Tone Generator Settings -->
                                <div
                                    class="flex flex-col md:flex-row md:items-center justify-between gap-6 pt-4 border-t border-gray-100 dark:border-zinc-800/50"
                                >
                                    <div class="flex-1">
                                        <div class="flex items-center justify-between mb-1">
                                            <div class="text-sm font-semibold text-gray-900 dark:text-white">
                                                Tone Generator
                                            </div>
                                            <button
                                                class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none"
                                                :class="
                                                    config.telephone_tone_generator_enabled
                                                        ? 'bg-blue-600'
                                                        : 'bg-gray-200 dark:bg-zinc-700'
                                                "
                                                @click="
                                                    config.telephone_tone_generator_enabled =
                                                        !config.telephone_tone_generator_enabled;
                                                    updateConfig({
                                                        telephone_tone_generator_enabled:
                                                            config.telephone_tone_generator_enabled,
                                                    });
                                                "
                                            >
                                                <span
                                                    class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
                                                    :class="
                                                        config.telephone_tone_generator_enabled
                                                            ? 'translate-x-5'
                                                            : 'translate-x-0'
                                                    "
                                                ></span>
                                            </button>
                                        </div>
                                        <div class="text-xs text-gray-500 dark:text-zinc-400">
                                            Play audio feedback during call dialing and disconnection.
                                        </div>
                                    </div>

                                    <div v-if="config.telephone_tone_generator_enabled" class="flex-1 md:max-w-xs">
                                        <div class="flex items-center justify-between mb-2">
                                            <label
                                                class="text-xs font-bold text-gray-500 dark:text-zinc-400 uppercase tracking-wider"
                                            >
                                                Tone Volume
                                            </label>
                                            <span class="text-xs font-mono text-gray-400"
                                                >{{ config.telephone_tone_generator_volume }}%</span
                                            >
                                        </div>
                                        <input
                                            v-model.number="config.telephone_tone_generator_volume"
                                            type="range"
                                            min="0"
                                            max="100"
                                            class="w-full h-1.5 bg-gray-200 dark:bg-zinc-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
                                            @change="
                                                updateConfig({
                                                    telephone_tone_generator_volume:
                                                        config.telephone_tone_generator_volume,
                                                })
                                            "
                                        />
                                    </div>
                                </div>

                                <!-- Preferred Ringtone for Non-Contacts -->
                                <div
                                    class="p-4 rounded-xl bg-blue-50/50 dark:bg-blue-900/10 border border-blue-100/50 dark:border-blue-900/30"
                                >
                                    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                        <div>
                                            <div class="text-sm font-semibold text-gray-900 dark:text-white">
                                                {{ $t("call.default_ringtone") }}
                                            </div>
                                            <div class="text-xs text-gray-500 dark:text-zinc-400">
                                                {{ $t("call.ringtone_for_non_contacts") }}
                                            </div>
                                        </div>
                                        <select
                                            v-model="config.ringtone_preferred_id"
                                            class="input-field !py-1.5 !px-3 !text-sm !rounded-xl !border-gray-200 dark:!border-zinc-800 min-w-[200px]"
                                            @change="
                                                updateConfig({ ringtone_preferred_id: config.ringtone_preferred_id })
                                            "
                                        >
                                            <option :value="0">{{ $t("call.primary_system_default") }}</option>
                                            <option :value="-1">{{ $t("call.random") }}</option>
                                            <optgroup :label="$t('call.uploaded_ringtones')">
                                                <option v-for="rt in ringtones" :key="rt.id" :value="rt.id">
                                                    {{ rt.display_name }}
                                                </option>
                                            </optgroup>
                                        </select>
                                    </div>
                                </div>

                                <!-- Ringtone List -->
                                <div class="space-y-4">
                                    <div class="flex items-center justify-between">
                                        <label class="text-sm font-semibold text-gray-700 dark:text-zinc-300">
                                            My Ringtones
                                        </label>
                                        <button
                                            type="button"
                                            class="text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
                                            @click="$refs.ringtoneUpload.click()"
                                        >
                                            <MaterialDesignIcon icon-name="plus" class="size-4" />
                                            Upload New
                                        </button>
                                        <input
                                            ref="ringtoneUpload"
                                            type="file"
                                            class="hidden"
                                            accept="audio/*"
                                            @change="uploadRingtone"
                                        />
                                    </div>

                                    <div v-if="ringtones.length > 0" class="grid gap-3">
                                        <div
                                            v-for="ringtone in ringtones"
                                            :key="ringtone.id"
                                            class="group p-4 rounded-xl border border-gray-100 dark:border-zinc-800 bg-gray-50/50 dark:bg-zinc-800/30 flex items-center gap-4 transition-all hover:shadow-md overflow-hidden"
                                            :class="{
                                                'ring-2 ring-blue-500/20 bg-blue-50/20 dark:bg-blue-900/10':
                                                    ringtone.is_primary,
                                            }"
                                        >
                                            <div class="flex-1 min-w-0 overflow-hidden">
                                                <div
                                                    v-if="editingRingtoneId === ringtone.id"
                                                    class="flex items-center gap-2"
                                                >
                                                    <input
                                                        v-model="editingRingtoneName"
                                                        class="text-sm bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-700 rounded px-2 py-1 flex-1 min-w-0"
                                                        @keyup.enter="saveRingtoneName"
                                                        @blur="saveRingtoneName"
                                                    />
                                                </div>
                                                <div v-else class="flex items-center gap-2 min-w-0">
                                                    <span
                                                        class="text-sm font-medium text-gray-900 dark:text-white truncate"
                                                        :title="ringtone.display_name"
                                                    >
                                                        {{ ringtone.display_name }}
                                                    </span>
                                                    <span
                                                        v-if="ringtone.is_primary"
                                                        class="shrink-0 text-[10px] uppercase font-bold text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/40 px-1.5 py-0.5 rounded"
                                                    >
                                                        Primary
                                                    </span>
                                                    <button
                                                        class="shrink-0 opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-blue-500 transition-opacity"
                                                        @click="startEditingRingtone(ringtone)"
                                                    >
                                                        <MaterialDesignIcon icon-name="pencil" class="size-3" />
                                                    </button>
                                                </div>
                                                <div
                                                    class="text-[10px] text-gray-500 dark:text-zinc-500 truncate"
                                                    :title="ringtone.filename"
                                                >
                                                    {{ ringtone.filename }}
                                                </div>
                                            </div>

                                            <div class="flex items-center gap-1">
                                                <a
                                                    :href="`/api/v1/telephone/ringtones/${ringtone.id}/audio?download=1`"
                                                    class="p-2 rounded-lg hover:bg-white dark:hover:bg-zinc-800 text-gray-500 dark:text-gray-400 hover:text-blue-500 transition-colors"
                                                    title="Download"
                                                >
                                                    <MaterialDesignIcon icon-name="download" class="size-5" />
                                                </a>
                                                <button
                                                    class="p-2 rounded-lg hover:bg-white dark:hover:bg-zinc-800 text-gray-500 dark:text-gray-400 transition-colors"
                                                    :title="
                                                        isPlayingRingtone && playingRingtoneId === ringtone.id
                                                            ? 'Stop'
                                                            : 'Preview'
                                                    "
                                                    @click="playRingtonePreview(ringtone)"
                                                >
                                                    <MaterialDesignIcon
                                                        :icon-name="
                                                            isPlayingRingtone && playingRingtoneId === ringtone.id
                                                                ? 'stop'
                                                                : 'play'
                                                        "
                                                        class="size-5"
                                                    />
                                                </button>
                                                <button
                                                    class="p-2 rounded-lg hover:bg-white dark:hover:bg-zinc-800 text-gray-500 dark:text-gray-400 hover:text-blue-500 transition-colors"
                                                    title="Edit Audio"
                                                    @click="openRingtoneEditor(ringtone)"
                                                >
                                                    <MaterialDesignIcon icon-name="content-cut" class="size-5" />
                                                </button>
                                                <button
                                                    v-if="!ringtone.is_primary"
                                                    class="p-2 rounded-lg hover:bg-white dark:hover:bg-zinc-800 text-gray-500 dark:text-gray-400 hover:text-blue-500 transition-colors"
                                                    title="Set as Primary"
                                                    @click="setPrimaryRingtone(ringtone)"
                                                >
                                                    <MaterialDesignIcon icon-name="star-outline" class="size-5" />
                                                </button>
                                                <button
                                                    class="p-2 rounded-lg hover:bg-white dark:hover:bg-zinc-800 text-gray-500 dark:text-gray-400 hover:text-red-500 transition-colors"
                                                    title="Delete"
                                                    @click="deleteRingtone(ringtone)"
                                                >
                                                    <MaterialDesignIcon icon-name="delete-outline" class="size-5" />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                    <div
                                        v-else
                                        class="flex flex-col items-center justify-center p-8 border-2 border-dashed border-gray-100 dark:border-zinc-800 rounded-2xl bg-gray-50/30 dark:bg-zinc-900/20"
                                    >
                                        <MaterialDesignIcon
                                            icon-name="music-off"
                                            class="size-8 text-gray-300 dark:text-zinc-700 mb-2"
                                        />
                                        <div class="text-xs text-gray-500 dark:text-zinc-500">
                                            {{ $t("call.no_custom_ringtone_uploaded") }}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </template>
                    </div>
                </div>

                <!-- Recordings Tab -->
                <div v-if="activeTab === 'recordings'" class="flex-1 flex flex-col max-w-3xl mx-auto w-full">
                    <div class="mb-4">
                        <div class="relative">
                            <input
                                v-model="recordingSearch"
                                type="text"
                                placeholder="Search recordings..."
                                class="block w-full rounded-lg border-0 py-2 pl-10 text-gray-900 dark:text-white shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
                                @input="onRecordingSearchInput"
                            />
                            <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                                <MaterialDesignIcon icon-name="magnify" class="size-5 text-gray-400" />
                            </div>
                        </div>
                    </div>

                    <div class="flex-1 overflow-y-auto min-h-0">
                        <div
                            class="bg-white dark:bg-zinc-900 rounded-xl shadow-sm border border-gray-200 dark:border-zinc-800 overflow-hidden"
                        >
                            <div v-if="recordings.length === 0" class="py-12 text-center">
                                <MaterialDesignIcon
                                    icon-name="microphone-off"
                                    class="size-12 text-gray-300 dark:text-zinc-700 mx-auto mb-2"
                                />
                                <p class="text-gray-500 dark:text-zinc-500 text-sm">{{ $t("call.no_recordings") }}</p>
                            </div>
                            <ul v-else class="divide-y divide-gray-100 dark:divide-zinc-800">
                                <li
                                    v-for="recording in recordings"
                                    :key="recording.id"
                                    class="px-4 py-4 hover:bg-gray-50 dark:hover:bg-zinc-800/50 transition-colors"
                                >
                                    <div class="flex items-start space-x-4">
                                        <div class="shrink-0">
                                            <LxmfUserIcon
                                                v-if="recording.remote_icon"
                                                :icon-name="recording.remote_icon.icon_name"
                                                :icon-foreground-colour="recording.remote_icon.foreground_colour"
                                                :icon-background-colour="recording.remote_icon.background_colour"
                                                class="size-10"
                                            />
                                            <div
                                                v-else
                                                class="size-10 rounded-full bg-gray-100 dark:bg-zinc-800 flex items-center justify-center text-gray-400"
                                            >
                                                <MaterialDesignIcon icon-name="account" class="size-6" />
                                            </div>
                                        </div>
                                        <div class="flex-1 min-w-0">
                                            <div class="flex items-center justify-between mb-1">
                                                <p class="text-sm font-bold text-gray-900 dark:text-white truncate">
                                                    {{ recording.remote_identity_name || $t("call.unknown") }}
                                                </p>
                                                <span class="text-[10px] text-gray-500 dark:text-zinc-500 font-mono">
                                                    {{ formatDateTime(recording.timestamp * 1000) }}
                                                </span>
                                            </div>
                                            <div
                                                class="flex items-center text-xs text-gray-500 dark:text-zinc-400 space-x-3 mb-3"
                                            >
                                                <span class="flex items-center gap-1">
                                                    <MaterialDesignIcon icon-name="clock-outline" class="size-3" />
                                                    {{ formatDuration(recording.duration_seconds) }}
                                                </span>
                                                <span
                                                    class="opacity-60 font-mono text-[10px] truncate"
                                                    @click.stop="copyHash(recording.remote_identity_hash)"
                                                    >{{ formatDestinationHash(recording.remote_identity_hash) }}</span
                                                >
                                            </div>
                                            <div class="flex items-center gap-2">
                                                <!-- RX Play -->
                                                <button
                                                    type="button"
                                                    class="px-2 py-1 rounded-md bg-blue-500/10 hover:bg-blue-500/20 text-blue-600 dark:text-blue-400 text-[10px] font-bold uppercase tracking-wider transition-all flex items-center gap-1"
                                                    @click="playRecording(recording, 'rx')"
                                                >
                                                    <MaterialDesignIcon
                                                        :icon-name="
                                                            playingRecordingId === recording.id && playingSide === 'rx'
                                                                ? 'stop'
                                                                : 'play'
                                                        "
                                                        class="size-3"
                                                    />
                                                    {{ $t("call.remote_rx") }}
                                                </button>
                                                <!-- TX Play -->
                                                <button
                                                    type="button"
                                                    class="px-2 py-1 rounded-md bg-green-500/10 hover:bg-green-500/20 text-green-600 dark:text-green-400 text-[10px] font-bold uppercase tracking-wider transition-all flex items-center gap-1"
                                                    @click="playRecording(recording, 'tx')"
                                                >
                                                    <MaterialDesignIcon
                                                        :icon-name="
                                                            playingRecordingId === recording.id && playingSide === 'tx'
                                                                ? 'stop'
                                                                : 'play'
                                                        "
                                                        class="size-3"
                                                    />
                                                    {{ $t("call.local_tx") }}
                                                </button>
                                                <div class="flex-1"></div>
                                                <!-- Download RX -->
                                                <a
                                                    :href="`/api/v1/telephone/recordings/${recording.id}/audio/rx`"
                                                    :download="`recording_${recording.id}_rx.opus`"
                                                    class="p-1.5 text-gray-400 hover:text-blue-500 transition-colors"
                                                    :title="$t('call.download_rx')"
                                                >
                                                    <MaterialDesignIcon icon-name="download" class="size-4" />
                                                </a>
                                                <!-- Download TX -->
                                                <a
                                                    :href="`/api/v1/telephone/recordings/${recording.id}/audio/tx`"
                                                    :download="`recording_${recording.id}_tx.opus`"
                                                    class="p-1.5 text-gray-400 hover:text-green-500 transition-colors"
                                                    :title="$t('call.download_tx')"
                                                >
                                                    <MaterialDesignIcon icon-name="download" class="size-4" />
                                                </a>
                                                <button
                                                    type="button"
                                                    class="p-1.5 text-gray-400 hover:text-red-500 transition-colors"
                                                    @click="deleteRecording(recording.id)"
                                                >
                                                    <MaterialDesignIcon icon-name="delete" class="size-4" />
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
        </div>
    </div>

    <!-- Contact Modal -->
    <div
        v-if="isContactModalOpen"
        class="fixed inset-0 z-[150] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm transition-opacity"
        @click.self="isContactModalOpen = false"
    >
        <div
            class="w-full max-w-lg bg-white dark:bg-zinc-900 rounded-3xl shadow-2xl overflow-hidden transform transition-all scale-100"
        >
            <div
                class="px-6 py-5 border-b border-gray-100 dark:border-zinc-800 flex items-center justify-between bg-gray-50/50 dark:bg-zinc-900/50"
            >
                <div class="flex items-center gap-3">
                    <div class="p-2 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-xl">
                        <MaterialDesignIcon icon-name="account-plus" class="size-6" />
                    </div>
                    <h3 class="text-xl font-bold text-gray-900 dark:text-white tracking-tight">
                        {{ editingContact ? $t("call.edit_contact") : $t("call.add_contact") }}
                    </h3>
                </div>
                <button
                    type="button"
                    class="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-zinc-200 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-full transition-all"
                    @click="isContactModalOpen = false"
                >
                    <MaterialDesignIcon icon-name="close" class="size-6" />
                </button>
            </div>

            <div class="p-6 space-y-6">
                <div class="space-y-4">
                    <div class="flex flex-col items-center justify-center pb-4">
                        <div class="relative group">
                            <div
                                class="size-24 rounded-full overflow-hidden bg-gray-100 dark:bg-zinc-800 border-2 border-dashed border-gray-300 dark:border-zinc-700 flex items-center justify-center"
                            >
                                <img
                                    v-if="contactForm.custom_image"
                                    :src="contactForm.custom_image"
                                    class="w-full h-full object-cover"
                                />
                                <MaterialDesignIcon v-else icon-name="camera-plus" class="size-8 text-gray-400" />
                            </div>
                            <button
                                type="button"
                                class="absolute inset-0 flex items-center justify-center bg-black/40 text-white opacity-0 group-hover:opacity-100 transition-opacity rounded-full"
                                @click="$refs.contactImageInput.click()"
                            >
                                <span class="text-xs font-bold">{{
                                    contactForm.custom_image ? "Change" : "Upload"
                                }}</span>
                            </button>
                            <button
                                v-if="contactForm.custom_image"
                                type="button"
                                class="absolute -top-1 -right-1 p-1 bg-red-500 text-white rounded-full shadow-lg hover:bg-red-600 transition-colors"
                                @click="contactForm.custom_image = null"
                            >
                                <MaterialDesignIcon icon-name="close" class="size-3" />
                            </button>
                        </div>
                        <input
                            ref="contactImageInput"
                            type="file"
                            class="hidden"
                            accept="image/*"
                            @change="onContactImageChange"
                        />
                        <p class="text-[10px] text-gray-400 mt-2 uppercase font-bold tracking-widest">Profile Image</p>
                    </div>
                    <div>
                        <label
                            class="block text-xs font-bold text-gray-500 dark:text-zinc-400 uppercase tracking-wider mb-1.5 ml-1"
                        >
                            {{ $t("call.contact_name") }}
                        </label>
                        <input v-model="contactForm.name" type="text" class="input-field" placeholder="e.g. John Doe" />
                    </div>
                    <div>
                        <label
                            class="block text-xs font-bold text-gray-500 dark:text-zinc-400 uppercase tracking-wider mb-1.5 ml-1"
                        >
                            {{ $t("call.identity_hash") }}
                        </label>
                        <input
                            v-model="contactForm.remote_identity_hash"
                            type="text"
                            class="input-field font-mono text-sm"
                            placeholder="e.g. a39610c89d18bb48c73e429582423c24"
                        />
                    </div>
                    <div>
                        <label
                            class="block text-xs font-bold text-gray-500 dark:text-zinc-400 uppercase tracking-wider mb-1.5 ml-1"
                        >
                            {{ $t("call.preferred_ringtone") }}
                        </label>
                        <select v-model="contactForm.preferred_ringtone_id" class="input-field">
                            <option :value="null">{{ $t("call.default_global_setting") }}</option>
                            <option :value="-1">{{ $t("call.random") }}</option>
                            <optgroup :label="$t('call.uploaded_ringtones')">
                                <option v-for="rt in ringtones" :key="rt.id" :value="rt.id">
                                    {{ rt.display_name }}
                                </option>
                            </optgroup>
                        </select>
                    </div>
                </div>

                <div class="flex gap-3 mt-8">
                    <button
                        type="button"
                        class="flex-1 px-6 py-3 rounded-2xl bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 font-bold hover:bg-gray-200 dark:hover:bg-zinc-700 transition-all active:scale-95"
                        @click="isContactModalOpen = false"
                    >
                        {{ $t("common.cancel") }}
                    </button>
                    <button
                        type="button"
                        class="flex-[2] px-6 py-3 rounded-2xl bg-blue-600 text-white font-bold shadow-lg shadow-blue-600/20 hover:bg-blue-500 transition-all active:scale-95"
                        @click="saveContact(contactForm)"
                    >
                        {{ $t("call.save_contact") }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import GlobalState from "../../js/GlobalState";
import GlobalEmitter from "../../js/GlobalEmitter";
import Utils from "../../js/Utils";
import Compressor from "compressorjs";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import LxmfUserIcon from "../LxmfUserIcon.vue";
import Toggle from "../forms/Toggle.vue";
import ToastUtils from "../../js/ToastUtils";
import RingtoneEditor from "./RingtoneEditor.vue";
import AudioWaveformPlayer from "../messages/AudioWaveformPlayer.vue";

export default {
    name: "CallPage",
    components: {
        MaterialDesignIcon,
        LxmfUserIcon,
        Toggle,
        RingtoneEditor,
        AudioWaveformPlayer,
    },
    data() {
        return {
            config: null,
            activeCall: null,
            audioProfiles: [],
            selectedAudioProfileId: null,
            destinationHash: "",
            isShowingStats: false,
            callHistory: [],
            callHistorySearch: "",
            callHistoryLimit: 10,
            callHistoryOffset: 0,
            hasMoreCallHistory: true,
            isCallEnded: false,
            wasDeclined: false,
            wasVoicemail: false,
            lastCall: null,
            endedTimeout: null,
            activeTab: "phone",
            voicemails: [],
            unreadVoicemailsCount: 0,
            voicemailStatus: {
                has_espeak: false,
                has_ffmpeg: false,
                is_recording: false,
                is_greeting_recording: false,
                has_greeting: false,
            },
            isGeneratingGreeting: false,
            isUploadingGreeting: false,
            isUploadingRingtone: false,
            playingVoicemailId: null,
            audioPlayer: null,
            isPlayingGreeting: false,
            isPlayingRingtone: false,
            ringtoneStatus: {
                has_custom_ringtone: false,
                enabled: false,
            },
            ringtones: [],
            editingRingtoneId: null,
            editingRingtoneName: "",
            elapsedTimeInterval: null,
            voicemailSearch: "",
            discoverySearch: "",
            discoveryAnnounces: [],
            totalDiscoveryCount: 0,
            discoveryLimit: 10,
            discoveryOffset: 0,
            hasMoreDiscovery: true,
            contactsSearch: "",
            contacts: [],
            isContactModalOpen: false,
            editingContact: null,
            contactForm: {
                name: "",
                remote_identity_hash: "",
            },
            searchDebounceTimeout: null,
            isVoicemailSettingsExpanded: false,
            selectedSuggestionIndex: -1,
            isCallInputFocused: false,
            recordings: [],
            isMicMuting: false,
            isSpeakerMuting: false,
            recordingSearch: "",
            playingRecordingId: null,
            playingSide: null,
            isRingtoneEditorOpen: false,
            editingRingtoneForAudio: null,
            localMicMuted: false,
            localSpeakerMuted: false,
            initiationStatus: null,
            initiationTargetHash: null,
            initiationTargetName: null,
            audioWs: null,
            audioCtx: null,
            audioStream: null,
            audioProcessor: null,
            audioWorkletNode: null,
            audioSilentGain: null,
            audioFrameMs: 60,
            audioInputDevices: [],
            audioOutputDevices: [],
            selectedAudioInputId: null,
            selectedAudioOutputId: null,
            remoteAudioEl: null,
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
            if (!this.isCallEnded || !this.lastCall?.call_start_time) {
                return null;
            }
            const duration = Math.floor(Date.now() / 1000 - this.lastCall.call_start_time);
            return Utils.formatMinutesSeconds(duration);
        },
        newCallSuggestions() {
            if (!this.isCallInputFocused) return [];

            const search = this.destinationHash.toLowerCase().trim();
            const suggestions = [];
            const seenHashes = new Set();

            // 1. Check contacts
            this.contacts.forEach((c) => {
                if (!seenHashes.has(c.remote_identity_hash)) {
                    if (
                        !search ||
                        c.name.toLowerCase().includes(search) ||
                        c.remote_identity_hash.toLowerCase().includes(search)
                    ) {
                        suggestions.push({
                            name: c.name,
                            hash: c.remote_telephony_hash || c.remote_destination_hash || c.remote_identity_hash,
                            type: "contact",
                            icon: "account",
                        });
                        seenHashes.add(c.remote_identity_hash);
                    }
                }
            });

            // 2. Check call history
            this.callHistory.forEach((h) => {
                if (!seenHashes.has(h.remote_identity_hash)) {
                    if (
                        !search ||
                        (h.remote_identity_name && h.remote_identity_name.toLowerCase().includes(search)) ||
                        h.remote_identity_hash.toLowerCase().includes(search)
                    ) {
                        suggestions.push({
                            name: h.remote_identity_name || h.remote_identity_hash.substring(0, 8),
                            hash: h.remote_telephony_hash || h.remote_destination_hash || h.remote_identity_hash,
                            type: "history",
                            icon: "history",
                        });
                        seenHashes.add(h.remote_identity_hash);
                    }
                }
            });

            return suggestions.slice(0, 8);
        },
    },
    watch: {
        destinationHash() {
            this.selectedSuggestionIndex = -1;
        },
        activeTab(newTab) {
            GlobalState.activeCallTab = newTab;
            if (newTab === "recordings") {
                this.getRecordings();
            }
        },
    },
    mounted() {
        this.getConfig();
        this.getAudioProfiles();
        this.getStatus();
        this.getHistory();
        this.getVoicemails();
        this.getRecordings();
        this.getContacts();
        this.getDiscovery();
        this.getVoicemailStatus();
        this.getRingtones();
        this.getRingtoneStatus();

        GlobalEmitter.on("telephone-history-updated", this.getHistory);
        GlobalEmitter.on("telephone-history-updated", this.getVoicemails);

        // poll for status
        this.statusInterval = setInterval(() => {
            this.getStatus();
            this.getVoicemailStatus();
            this.getRingtoneStatus();
        }, 1000);

        // poll for history/voicemails less frequently
        this.historyInterval = setInterval(() => {
            this.getHistory();
            this.getVoicemails();
            this.getRecordings();
            this.getContacts();
            this.getDiscovery();
        }, 10000);

        // update elapsed time every second
        this.elapsedTimeInterval = setInterval(() => {
            this.$forceUpdate();
        }, 1000);

        // autofill destination hash and tab from query string
        const destinationHash = this.$route.query.destination_hash;
        if (destinationHash) {
            this.destinationHash = destinationHash;
        }
        const tab = this.$route.query.tab;
        if (tab) {
            this.activeTab = tab;
        }
    },
    beforeUnmount() {
        GlobalEmitter.off("telephone-history-updated", this.getHistory);
        GlobalEmitter.off("telephone-history-updated", this.getVoicemails);

        if (this.statusInterval) clearInterval(this.statusInterval);
        if (this.historyInterval) clearInterval(this.historyInterval);
        if (this.elapsedTimeInterval) clearInterval(this.elapsedTimeInterval);
        if (this.endedTimeout) clearTimeout(this.endedTimeout);
        if (this.audioPlayer) {
            this.audioPlayer.pause();
            this.audioPlayer = null;
        }
        this.stopWebAudio();
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
        formatTimeAgo(datetimeString) {
            return Utils.formatTimeAgo(datetimeString);
        },
        formatDuration(seconds) {
            return Utils.formatMinutesSeconds(seconds);
        },
        async ensureWebAudio(webAudioStatus) {
            if (!this.config?.telephone_web_audio_enabled) {
                this.stopWebAudio();
                return;
            }
            if (this.activeCall && webAudioStatus?.enabled) {
                this.audioFrameMs = webAudioStatus.frame_ms || 60;
                await this.startWebAudio();
            } else {
                this.stopWebAudio();
            }
        },
        async onToggleWebAudio(newVal) {
            if (!this.config) return;
            this.config.telephone_web_audio_enabled = newVal;
            try {
                await this.updateConfig({ telephone_web_audio_enabled: newVal });
                if (newVal) {
                    await this.requestAudioPermission();
                    await this.startWebAudio();
                } else {
                    this.stopWebAudio();
                }
            } catch (e) {
                // revert on failure
                this.config.telephone_web_audio_enabled = !newVal;
            }
        },
        async startWebAudio() {
            if (this.audioWs) {
                return;
            }
            try {
                const constraints = this.selectedAudioInputId
                    ? { audio: { deviceId: { exact: this.selectedAudioInputId } } }
                    : { audio: true };
                const stream = await navigator.mediaDevices.getUserMedia(constraints);
                this.audioStream = stream;

                if (!this.audioCtx) {
                    this.audioCtx = new AudioContext({ sampleRate: 48000 });
                }

                const source = this.audioCtx.createMediaStreamSource(stream);
                const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
                const url = `${wsProtocol}//${window.location.host}/ws/telephone/audio`;

                const workletLoaded = false; // disabled to avoid CSP violations from blob worklets
                if (!workletLoaded) {
                    const processor = this.audioCtx.createScriptProcessor(1024, 1, 1);
                    processor.onaudioprocess = (event) => {
                        if (!this.audioWs || this.audioWs.readyState !== WebSocket.OPEN) return;
                        const input = event.inputBuffer.getChannelData(0);
                        const pcm = new Int16Array(input.length);
                        for (let i = 0; i < input.length; i += 1) {
                            pcm[i] = Math.max(-1, Math.min(1, input[i])) * 0x7fff;
                        }
                        this.audioWs.send(pcm.buffer);
                    };
                    source.connect(processor);
                    this.audioProcessor = processor;
                }

                const ws = new WebSocket(url);
                ws.binaryType = "arraybuffer";
                ws.onopen = () => {
                    ws.send(JSON.stringify({ type: "attach" }));
                };
                ws.onmessage = (event) => {
                    if (typeof event.data === "string") {
                        return;
                    }
                    this.playRemotePcm(event.data);
                };
                ws.onerror = () => {
                    this.stopWebAudio();
                };
                ws.onclose = () => {
                    this.stopWebAudio();
                };
                this.audioWs = ws;
                this.refreshAudioDevices();
            } catch (err) {
                console.error("Web audio failed", err);
                ToastUtils.error("Web audio not available");
                this.stopWebAudio();
            }
        },
        async requestAudioPermission() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                stream.getTracks().forEach((t) => t.stop());
                await this.refreshAudioDevices();
            } catch (e) {
                console.error("Permission or device request failed", e);
            }
        },
        async refreshAudioDevices() {
            try {
                const devices = await navigator.mediaDevices.enumerateDevices();
                this.audioInputDevices = devices.filter((d) => d.kind === "audioinput");
                this.audioOutputDevices = devices.filter((d) => d.kind === "audiooutput");
                if (!this.selectedAudioInputId && this.audioInputDevices.length) {
                    this.selectedAudioInputId = this.audioInputDevices[0].deviceId;
                }
                if (!this.selectedAudioOutputId && this.audioOutputDevices.length) {
                    this.selectedAudioOutputId = this.audioOutputDevices[0].deviceId;
                }
            } catch (e) {
                console.error("Failed to enumerate audio devices", e);
            }
        },
        playRemotePcm(arrayBuffer) {
            if (!this.audioCtx) {
                return;
            }
            const pcm = new Int16Array(arrayBuffer);
            if (pcm.length === 0) return;
            const floatBuf = new Float32Array(pcm.length);
            for (let i = 0; i < pcm.length; i += 1) {
                floatBuf[i] = pcm[i] / 0x7fff;
            }
            const audioBuffer = this.audioCtx.createBuffer(1, floatBuf.length, 48000);
            audioBuffer.copyToChannel(floatBuf, 0);
            const bufferSource = this.audioCtx.createBufferSource();
            bufferSource.buffer = audioBuffer;
            if (this.selectedAudioOutputId && "setSinkId" in HTMLMediaElement.prototype) {
                if (!this.remoteAudioEl) {
                    this.remoteAudioEl = new Audio();
                    this.remoteAudioEl.autoplay = true;
                }
                const dest = this.audioCtx.createMediaStreamDestination();
                bufferSource.connect(dest);
                bufferSource.start();
                this.remoteAudioEl.srcObject = dest.stream;
                this.remoteAudioEl
                    .setSinkId(this.selectedAudioOutputId)
                    .catch((err) => console.warn("setSinkId failed", err));
            } else {
                bufferSource.connect(this.audioCtx.destination);
                bufferSource.start();
            }
        },
        stopWebAudio() {
            if (this.audioProcessor) {
                try {
                    this.audioProcessor.disconnect();
                } catch (_) {}
                this.audioProcessor = null;
            }
            if (this.audioStream) {
                this.audioStream.getTracks().forEach((t) => t.stop());
                this.audioStream = null;
            }
            if (this.audioWs) {
                try {
                    this.audioWs.close();
                } catch (_) {}
                this.audioWs = null;
            }
            if (this.remoteAudioEl) {
                this.remoteAudioEl.srcObject = null;
                this.remoteAudioEl = null;
            }
            if (this.audioWorkletNode) {
                try {
                    this.audioWorkletNode.disconnect();
                } catch (_) {}
                this.audioWorkletNode = null;
            }
            if (this.audioSilentGain) {
                try {
                    this.audioSilentGain.disconnect();
                } catch (_) {}
                this.audioSilentGain = null;
            }
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
                const response = await window.axios.patch("/api/v1/config", config);
                if (response.data?.config) {
                    this.config = response.data.config;
                }
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
                const newCall = response.data.active_call;

                // Sync local mute state from backend
                if (newCall) {
                    if (!oldCall || newCall.hash !== oldCall.hash) {
                        this.localMicMuted = newCall.is_mic_muted;
                        this.localSpeakerMuted = newCall.is_speaker_muted;
                    }
                }

                this.activeCall = newCall;
                this.initiationStatus = response.data.initiation_status;
                this.initiationTargetHash = response.data.initiation_target_hash;
                this.initiationTargetName = response.data.initiation_target_name;

                if (this.activeCall?.is_voicemail) {
                    this.wasVoicemail = true;
                }

                if (response.data.voicemail) {
                    this.unreadVoicemailsCount = response.data.voicemail.unread_count;
                }

                if (response.data.web_audio) {
                    await this.ensureWebAudio(response.data.web_audio);
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

                        // Close window if we are in a popout
                        if (this.$route.meta.isPopout) {
                            window.close();
                        }
                    }, 5000);
                } else if (this.activeCall != null) {
                    // if a new call starts, clear ended state
                    this.isCallEnded = false;
                    this.wasDeclined = false;
                    this.wasVoicemail = false;
                    this.lastCall = null;
                    if (this.endedTimeout) clearTimeout(this.endedTimeout);
                } else if (!this.endedTimeout) {
                    // If no call and no ended state timeout active, ensure everything is reset
                    this.isCallEnded = false;
                    this.wasDeclined = false;
                    this.wasVoicemail = false;
                    this.lastCall = null;
                }
            } catch (e) {
                console.log(e);
            }
        },
        async addContactFromHistory(entry) {
            this.editingContact = null;
            this.contactForm = {
                name: entry.remote_identity_name || "",
                remote_identity_hash:
                    entry.remote_telephony_hash || entry.remote_destination_hash || entry.remote_identity_hash,
                preferred_ringtone_id: null,
            };
            this.isContactModalOpen = true;
        },
        async getHistory(loadMore = false) {
            try {
                if (!loadMore) {
                    this.callHistoryOffset = 0;
                    this.hasMoreCallHistory = true;
                }

                const response = await window.axios.get(
                    `/api/v1/telephone/history?limit=${this.callHistoryLimit}&offset=${this.callHistoryOffset}${
                        this.callHistorySearch ? `&search=${encodeURIComponent(this.callHistorySearch)}` : ""
                    }`
                );

                const newItems = response.data.call_history || [];
                if (loadMore) {
                    this.callHistory = [...this.callHistory, ...newItems];
                } else {
                    this.callHistory = newItems;
                }

                this.hasMoreCallHistory = newItems.length === this.callHistoryLimit;
            } catch (e) {
                console.log(e);
            }
        },
        async loadMoreCallHistory() {
            this.callHistoryOffset += this.callHistoryLimit;
            await this.getHistory(true);
        },
        onCallHistorySearchInput() {
            if (this.searchDebounceTimeout) clearTimeout(this.searchDebounceTimeout);
            this.searchDebounceTimeout = setTimeout(() => {
                this.getHistory();
            }, 500);
        },
        async getDiscovery(loadMore = false) {
            try {
                if (!loadMore) {
                    this.discoveryOffset = 0;
                    this.hasMoreDiscovery = true;
                }

                const response = await window.axios.get("/api/v1/announces", {
                    params: {
                        aspect: "lxst.telephony",
                        limit: this.discoveryLimit,
                        offset: this.discoveryOffset,
                        search: this.discoverySearch,
                    },
                });

                const newItems = response.data.announces || [];
                this.totalDiscoveryCount = response.data.total_count || 0;
                if (loadMore) {
                    this.discoveryAnnounces = [...this.discoveryAnnounces, ...newItems];
                } else {
                    this.discoveryAnnounces = newItems;
                }

                this.hasMoreDiscovery = newItems.length === this.discoveryLimit;
            } catch (e) {
                console.log(e);
            }
        },
        async loadMoreDiscovery() {
            this.discoveryOffset += this.discoveryLimit;
            await this.getDiscovery(true);
        },
        onDiscoverySearchInput() {
            if (this.searchDebounceTimeout) clearTimeout(this.searchDebounceTimeout);
            this.searchDebounceTimeout = setTimeout(() => {
                this.getDiscovery();
            }, 500);
        },
        async toggleDoNotDisturb(value) {
            try {
                await window.axios.patch("/api/v1/config", {
                    do_not_disturb_enabled: value,
                });
                if (this.config) {
                    this.config.do_not_disturb_enabled = value;
                }
                ToastUtils.success(value ? "Do Not Disturb enabled" : "Do Not Disturb disabled");
            } catch {
                ToastUtils.error("Failed to update Do Not Disturb status");
            }
        },
        async toggleAllowCallsFromContactsOnly(value) {
            try {
                await window.axios.patch("/api/v1/config", {
                    telephone_allow_calls_from_contacts_only: value,
                });
                if (this.config) {
                    this.config.telephone_allow_calls_from_contacts_only = value;
                }
                ToastUtils.success(value ? "Calls limited to contacts" : "Calls allowed from everyone");
            } catch {
                ToastUtils.error("Failed to update call settings");
            }
        },
        async toggleCallRecording(value) {
            try {
                await window.axios.patch("/api/v1/config", {
                    call_recording_enabled: value,
                });
                if (this.config) {
                    this.config.call_recording_enabled = value;
                }
                ToastUtils.success(value ? "Call recording enabled" : "Call recording disabled");
            } catch {
                ToastUtils.error("Failed to update call recording status");
            }
        },
        async clearHistory() {
            if (!confirm(this.$t("common.delete_confirm"))) return;
            try {
                await window.axios.delete("/api/v1/telephone/history");
                this.callHistory = [];
                ToastUtils.success("Call history cleared");
            } catch (e) {
                console.error(e);
                ToastUtils.error("Failed to clear call history");
            }
        },
        async blockIdentity(hash) {
            if (!confirm(`Are you sure you want to banish this identity?`)) return;
            try {
                await window.axios.post("/api/v1/blocked-destinations", {
                    destination_hash: hash,
                });
                ToastUtils.success("Identity banished");
                this.getHistory();
            } catch {
                ToastUtils.error("Failed to banish identity");
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
        async getRingtoneStatus() {
            try {
                const response = await window.axios.get("/api/v1/telephone/ringtones/status");
                this.ringtoneStatus = response.data;
            } catch (e) {
                console.log(e);
            }
        },
        async getRingtones() {
            try {
                const response = await window.axios.get("/api/v1/telephone/ringtones");
                this.ringtones = response.data;
            } catch (e) {
                console.error("Failed to get ringtones:", e);
            }
        },
        async deleteRingtone(ringtone) {
            if (!confirm(this.$t("common.delete_confirm"))) return;
            try {
                await window.axios.delete(`/api/v1/telephone/ringtones/${ringtone.id}`);
                ToastUtils.success(this.$t("call.ringtone_deleted"));
                await this.getRingtones();
                await this.getRingtoneStatus();
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("call.failed_to_delete_ringtone"));
            }
        },
        async setPrimaryRingtone(ringtone) {
            try {
                await window.axios.patch(`/api/v1/telephone/ringtones/${ringtone.id}`, {
                    is_primary: true,
                });
                ToastUtils.success(this.$t("call.primary_ringtone_set"));
                await this.getRingtones();
                await this.getRingtoneStatus();
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("call.failed_to_set_primary_ringtone"));
            }
        },
        startEditingRingtone(ringtone) {
            this.editingRingtoneId = ringtone.id;
            this.editingRingtoneName = ringtone.display_name;
        },
        async saveRingtoneName() {
            try {
                await window.axios.patch(`/api/v1/telephone/ringtones/${this.editingRingtoneId}`, {
                    display_name: this.editingRingtoneName,
                });
                this.editingRingtoneId = null;
                await this.getRingtones();
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("call.failed_to_update_ringtone_name"));
            }
        },
        async uploadRingtone(event) {
            const file = event.target.files[0];
            if (!file) return;

            this.isUploadingRingtone = true;
            const formData = new FormData();
            formData.append("file", file);

            try {
                await window.axios.post("/api/v1/telephone/ringtones/upload", formData, {
                    headers: {
                        "Content-Type": "multipart/form-data",
                    },
                });
                ToastUtils.success(this.$t("call.ringtone_uploaded_successfully"));
                await this.getRingtones();
                await this.getRingtoneStatus();
            } catch (e) {
                console.error(e);
                ToastUtils.error(e.response?.data?.message || this.$t("call.failed_to_upload_ringtone"));
            } finally {
                this.isUploadingRingtone = false;
                event.target.value = "";
            }
        },
        async playRingtonePreview(ringtone) {
            if (this.isPlayingRingtone && this.playingRingtoneId === ringtone.id) {
                this.audioPlayer.pause();
                this.isPlayingRingtone = false;
                this.playingRingtoneId = null;
                return;
            }

            if (this.audioPlayer) {
                this.audioPlayer.pause();
            }

            this.playingRingtoneId = ringtone.id;
            this.audioPlayer = new Audio(`/api/v1/telephone/ringtones/${ringtone.id}/audio`);
            if (this.config?.ringtone_volume !== undefined) {
                this.audioPlayer.volume = this.config.ringtone_volume / 100.0;
            }
            this.audioPlayer.onended = () => {
                this.isPlayingRingtone = false;
                this.playingRingtoneId = null;
            };

            try {
                await this.audioPlayer.play();
                this.isPlayingRingtone = true;
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("call.failed_to_play_ringtone"));
            }
        },
        openRingtoneEditor(ringtone) {
            this.editingRingtoneForAudio = ringtone;
            this.isRingtoneEditorOpen = true;
        },
        onRingtoneSaved() {
            this.getRingtones();
            this.getRingtoneStatus();
        },
        async getVoicemails() {
            try {
                const response = await window.axios.get("/api/v1/telephone/voicemails", {
                    params: { search: this.voicemailSearch },
                });
                this.voicemails = response.data.voicemails || [];
                this.unreadVoicemailsCount = response.data.unread_count || 0;
            } catch (e) {
                console.log(e);
            }
        },
        onVoicemailSearchInput() {
            if (this.searchDebounceTimeout) clearTimeout(this.searchDebounceTimeout);
            this.searchDebounceTimeout = setTimeout(() => {
                this.getVoicemails();
            }, 300);
        },
        getContactByHash(hash) {
            if (!hash) return null;
            return this.contacts.find((c) => c.remote_identity_hash === hash);
        },
        async getContacts() {
            try {
                const response = await window.axios.get("/api/v1/telephone/contacts", {
                    params: { search: this.contactsSearch },
                });
                this.contacts = response.data.contacts || (Array.isArray(response.data) ? response.data : []);
            } catch (e) {
                console.log(e);
            }
        },
        onContactsSearchInput() {
            if (this.searchDebounceTimeout) clearTimeout(this.searchDebounceTimeout);
            this.searchDebounceTimeout = setTimeout(() => {
                this.getContacts();
            }, 300);
        },
        openAddContactModal() {
            this.editingContact = null;
            this.contactForm = {
                name: "",
                remote_identity_hash: "",
                preferred_ringtone_id: null,
                custom_image: null,
            };
            this.isContactModalOpen = true;
        },
        openEditContactModal(contact) {
            this.editingContact = contact;
            this.contactForm = {
                id: contact.id,
                name: contact.name,
                remote_identity_hash: contact.remote_identity_hash,
                preferred_ringtone_id: contact.preferred_ringtone_id,
                custom_image: contact.custom_image,
            };
            this.isContactModalOpen = true;
        },
        async saveContact(contact) {
            if (!contact.name || !contact.remote_identity_hash) {
                ToastUtils.error("Name and identity hash required");
                return;
            }
            try {
                if (contact.id) {
                    // if editing and image was cleared, let backend know
                    if (this.editingContact && this.editingContact.custom_image && !contact.custom_image) {
                        contact.clear_image = true;
                    }
                    await window.axios.patch(`/api/v1/telephone/contacts/${contact.id}`, contact);
                    ToastUtils.success("Contact updated");
                } else {
                    await window.axios.post("/api/v1/telephone/contacts", contact);
                    ToastUtils.success("Contact added");
                }
                this.isContactModalOpen = false;
                this.getContacts();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || "Failed to save contact");
            }
        },
        async deleteContact(contactId) {
            if (!confirm("Are you sure you want to delete this contact?")) return;
            try {
                await window.axios.delete(`/api/v1/telephone/contacts/${contactId}`);
                ToastUtils.success("Contact deleted");
                this.getContacts();
            } catch {
                ToastUtils.error("Failed to delete contact");
            }
        },
        onContactImageChange(event) {
            const file = event.target.files[0];
            if (!file) return;

            new Compressor(file, {
                maxWidth: 256,
                maxHeight: 256,
                quality: 0.7,
                mimeType: "image/webp",
                success: (result) => {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        this.contactForm.custom_image = e.target.result;
                    };
                    reader.readAsDataURL(result);
                },
                error: (err) => {
                    ToastUtils.error(err.message);
                },
            });
            event.target.value = "";
        },
        async copyHash(hash) {
            try {
                await navigator.clipboard.writeText(hash);
                ToastUtils.success("Hash copied to clipboard");
            } catch (e) {
                console.error(e);
                ToastUtils.error("Failed to copy hash");
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
            } catch {
                ToastUtils.error("Failed to delete greeting");
            }
        },
        async startRecordingGreetingMic() {
            try {
                await window.axios.post("/api/v1/telephone/voicemail/greeting/record/start");
                await this.getVoicemailStatus();
            } catch {
                ToastUtils.error("Failed to start recording greeting");
            }
        },
        async stopRecordingGreetingMic() {
            try {
                await window.axios.post("/api/v1/telephone/voicemail/greeting/record/stop");
                await this.getVoicemailStatus();
                ToastUtils.success("Greeting recorded from mic");
            } catch {
                ToastUtils.error("Failed to stop recording greeting");
            }
        },
        async playVoicemail(voicemail) {
            // This is now handled by AudioWaveformPlayer, but we keep it for backward compatibility or direct calls
            if (this.playingVoicemailId === voicemail.id) {
                if (this.audioPlayer) {
                    this.audioPlayer.pause();
                }
                this.playingVoicemailId = null;
                return;
            }

            if (this.audioPlayer) {
                this.audioPlayer.pause();
            }

            this.playingVoicemailId = voicemail.id;
            this.audioPlayer = new Audio(`/api/v1/telephone/voicemails/${voicemail.id}/audio`);

            this.audioPlayer.addEventListener("error", (e) => {
                console.error("Audio player error:", e);
                ToastUtils.error(this.$t("call.failed_to_play_voicemail") || "Failed to load voicemail audio");
                this.playingVoicemailId = null;
                this.audioPlayer = null;
            });

            this.audioPlayer.onended = () => {
                this.playingVoicemailId = null;
            };

            try {
                await this.audioPlayer.play();
            } catch (e) {
                console.error("Audio play failed:", e);
                this.playingVoicemailId = null;
            }

            this.markVoicemailAsRead(voicemail);
        },
        async markVoicemailAsRead(voicemail) {
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
        playLatestVoicemail() {
            if (this.voicemails.length > 0) {
                this.playVoicemail(this.voicemails[0]);
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
        async getRecordings() {
            try {
                const response = await window.axios.get("/api/v1/telephone/recordings", {
                    params: { search: this.recordingSearch },
                });
                this.recordings = response.data.recordings || [];
            } catch (e) {
                console.error("Failed to get recordings:", e);
            }
        },
        onRecordingSearchInput() {
            if (this.searchDebounceTimeout) clearTimeout(this.searchDebounceTimeout);
            this.searchDebounceTimeout = setTimeout(() => {
                this.getRecordings();
            }, 500);
        },
        async playRecording(recording, side) {
            if (this.playingRecordingId === recording.id && this.playingSide === side) {
                if (this.audioPlayer) {
                    this.audioPlayer.pause();
                }
                this.playingRecordingId = null;
                this.playingSide = null;
                return;
            }

            if (this.audioPlayer) {
                this.audioPlayer.pause();
            }

            this.playingRecordingId = recording.id;
            this.playingSide = side;
            this.audioPlayer = new Audio(`/api/v1/telephone/recordings/${recording.id}/audio/${side}`);

            this.audioPlayer.onended = () => {
                this.playingRecordingId = null;
                this.playingSide = null;
                this.audioPlayer = null;
            };

            try {
                await this.audioPlayer.play();
            } catch (e) {
                console.error("Failed to play recording:", e);
                ToastUtils.error("Failed to load recording audio");
                this.playingRecordingId = null;
                this.playingSide = null;
            }
        },
        async deleteRecording(recordingId) {
            if (!confirm("Are you sure you want to delete this recording?")) return;
            try {
                await window.axios.delete(`/api/v1/telephone/recordings/${recordingId}`);
                this.getRecordings();
                ToastUtils.success("Recording deleted");
            } catch {
                ToastUtils.error("Failed to delete recording");
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
                ToastUtils.error(this.$t("call.no_greeting_audio_found"));
                this.isPlayingGreeting = false;
            });
            this.audioPlayer.onended = () => {
                this.isPlayingGreeting = false;
            };
        },
        async call(identityHash) {
            if (!identityHash) {
                ToastUtils.error("Enter an identity to call");
                return;
            }

            let hashToCall = identityHash.trim();
            // Accept lxmf:// URIs or pasted text; extract first 64-char hex
            const hexMatch = hashToCall.match(/[0-9a-fA-F]{64}/);
            if (hexMatch) {
                hashToCall = hexMatch[0];
            }
            hashToCall = hashToCall.toLowerCase();

            // Try to resolve name from contacts
            const contact = this.contacts.find((c) => c.name.toLowerCase() === hashToCall.toLowerCase());
            if (contact) {
                hashToCall = contact.remote_identity_hash;
            }

            // Provide immediate feedback
            this.destinationHash = hashToCall;
            const targetContact = this.contacts.find((c) => c.remote_identity_hash === hashToCall);
            this.initiationTargetHash = hashToCall;
            this.initiationTargetName = targetContact ? targetContact.name : null;
            this.activeTab = "phone";
            this.initiationStatus = "Initiating...";
            this.isCallEnded = false;
            this.wasDeclined = false;

            try {
                await window.axios.get(`/api/v1/telephone/call/${hashToCall}`);
            } catch (e) {
                this.initiationStatus = null;
                ToastUtils.error(e.response?.data?.message || "Failed to initiate call");
            }
        },
        handleCallInputUp() {
            if (this.newCallSuggestions.length > 0) {
                if (this.selectedSuggestionIndex > 0) {
                    this.selectedSuggestionIndex--;
                } else {
                    this.selectedSuggestionIndex = this.newCallSuggestions.length - 1;
                }
            }
        },
        handleCallInputDown() {
            if (this.newCallSuggestions.length > 0) {
                if (this.selectedSuggestionIndex < this.newCallSuggestions.length - 1) {
                    this.selectedSuggestionIndex++;
                } else {
                    this.selectedSuggestionIndex = 0;
                }
            }
        },
        handleCallInputEnter() {
            if (this.selectedSuggestionIndex >= 0 && this.selectedSuggestionIndex < this.newCallSuggestions.length) {
                const suggestion = this.newCallSuggestions[this.selectedSuggestionIndex];
                this.selectSuggestion(suggestion);
            } else {
                this.call(this.destinationHash);
            }
        },
        selectSuggestion(suggestion) {
            this.destinationHash = suggestion.hash;
            this.isCallInputFocused = false;
            this.selectedSuggestionIndex = -1;
            this.call(this.destinationHash);
        },
        onCallInputBlur() {
            // Delay blur to allow mousedown on suggestions
            setTimeout(() => {
                this.isCallInputFocused = false;
                this.selectedSuggestionIndex = -1;
            }, 200);
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
                if (this.activeCall && this.activeCall.is_incoming && this.activeCall.status === 4) {
                    this.wasDeclined = true;
                }
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
        async switchAudioProfile(audioProfileId) {
            try {
                await window.axios.get(`/api/v1/telephone/switch-audio-profile/${audioProfileId}`);
            } catch {
                ToastUtils.error("Failed to switch audio profile");
            }
        },
        async toggleMicrophone() {
            try {
                const isCurrentlyMuted = this.localMicMuted;
                this.isMicMuting = true;

                // Optimistic update
                this.localMicMuted = !isCurrentlyMuted;
                if (this.activeCall) {
                    this.activeCall.is_mic_muted = this.localMicMuted;
                }

                const endpoint = isCurrentlyMuted
                    ? "/api/v1/telephone/unmute-transmit"
                    : "/api/v1/telephone/mute-transmit";
                await window.axios.get(endpoint);

                // clear muting state after a short delay to allow backend to catch up
                setTimeout(() => {
                    this.isMicMuting = false;
                }, 500);
            } catch {
                this.isMicMuting = false;
                // Revert on error
                this.localMicMuted = !this.localMicMuted;
                ToastUtils.error("Failed to toggle microphone");
            }
        },
        async toggleSpeaker() {
            try {
                const isCurrentlyMuted = this.localSpeakerMuted;
                this.isSpeakerMuting = true;

                // Optimistic update
                this.localSpeakerMuted = !isCurrentlyMuted;
                if (this.activeCall) {
                    this.activeCall.is_speaker_muted = this.localSpeakerMuted;
                }

                const endpoint = isCurrentlyMuted
                    ? "/api/v1/telephone/unmute-receive"
                    : "/api/v1/telephone/mute-receive";
                await window.axios.get(endpoint);

                // clear muting state after a short delay to allow backend to catch up
                setTimeout(() => {
                    this.isSpeakerMuting = false;
                }, 500);
            } catch {
                this.isSpeakerMuting = false;
                // Revert on error
                this.localSpeakerMuted = !this.localSpeakerMuted;
                ToastUtils.error("Failed to toggle speaker");
            }
        },
    },
};
</script>
