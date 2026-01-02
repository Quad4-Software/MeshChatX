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
                </div>

                <!-- Phone Tab -->
                <div v-if="activeTab === 'phone'" class="flex-1 flex flex-col">
                    <div class="flex items-center justify-between mb-4 px-1">
                        <Toggle
                            id="dnd-toggle"
                            :model-value="config?.do_not_disturb_enabled"
                            :label="$t('call.do_not_disturb')"
                            @update:model-value="toggleDoNotDisturb"
                        />
                    </div>

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
                                            <LxmfUserIcon
                                                v-if="(activeCall || lastCall)?.remote_icon"
                                                :icon-name="(activeCall || lastCall).remote_icon.icon_name"
                                                :icon-foreground-colour="
                                                    (activeCall || lastCall).remote_icon.foreground_colour
                                                "
                                                :icon-background-colour="
                                                    (activeCall || lastCall).remote_icon.background_colour
                                                "
                                                class="size-12"
                                            />
                                            <MaterialDesignIcon v-else icon-name="account" class="size-12" />
                                        </div>
                                    </div>

                                    <!-- name -->
                                    <div class="text-xl font-semibold text-gray-500 dark:text-zinc-100 truncate px-4">
                                        <span v-if="(activeCall || lastCall)?.remote_identity_name != null">{{
                                            (activeCall || lastCall).remote_identity_name
                                        }}</span>
                                        <span v-else>{{ $t("call.unknown") }}</span>
                                    </div>
                                    <div
                                        v-if="(activeCall || lastCall)?.is_contact"
                                        class="text-xs text-blue-600 dark:text-blue-400 font-medium mt-1"
                                    >
                                        In contacts
                                    </div>

                                    <!-- identity hash -->
                                    <div
                                        v-if="(activeCall || lastCall)?.remote_identity_hash != null"
                                        class="text-gray-500 dark:text-zinc-100 opacity-60 text-sm truncate px-8 font-mono"
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
                                    <template v-if="wasDeclined">
                                        <span class="text-red-500 font-bold animate-pulse">{{
                                            $t("call.call_declined")
                                        }}</span>
                                    </template>
                                    <template v-else-if="isCallEnded">
                                        <span class="text-red-500 font-bold animate-pulse">{{
                                            $t("call.call_ended")
                                        }}</span>
                                    </template>
                                    <template v-else-if="activeCall">
                                        <span
                                            v-if="activeCall.is_incoming && activeCall.status === 4"
                                            class="animate-bounce inline-block"
                                            >{{ $t("call.incoming_call") }}</span
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
                                <div
                                    v-if="activeCall && activeCall.status === 6 && !isCallEnded && elapsedTime"
                                    class="text-gray-500 dark:text-zinc-400 mb-4 text-center font-mono text-lg"
                                >
                                    {{ elapsedTime }}
                                </div>
                                <div
                                    v-if="isCallEnded && callDuration"
                                    class="text-gray-500 dark:text-zinc-400 mb-4 text-center font-mono text-lg"
                                >
                                    {{ callDuration }}
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
                                <div v-if="activeCall" class="flex flex-wrap justify-center gap-4 mt-8 mb-4">
                                    <!-- answer call -->
                                    <button
                                        v-if="activeCall.is_incoming && activeCall.status === 4"
                                        :title="$t('call.answer_call')"
                                        type="button"
                                        class="inline-flex items-center gap-x-2 rounded-2xl bg-green-600 px-4 py-2 text-sm font-bold text-white shadow-xl hover:bg-green-500 transition-all duration-200 animate-bounce"
                                        @click="answerCall"
                                    >
                                        <MaterialDesignIcon icon-name="phone" class="size-4" />
                                        <span>{{ $t("call.accept") }}</span>
                                    </button>

                                    <!-- send to voicemail -->
                                    <button
                                        v-if="activeCall.is_incoming && activeCall.status === 4"
                                        :title="$t('call.send_to_voicemail')"
                                        type="button"
                                        class="inline-flex items-center gap-x-2 rounded-2xl bg-blue-600 px-4 py-2 text-sm font-bold text-white shadow-xl hover:bg-blue-500 transition-all duration-200"
                                        @click="sendToVoicemail"
                                    >
                                        <MaterialDesignIcon icon-name="voicemail" class="size-4" />
                                        <span>{{ $t("call.send_to_voicemail") }}</span>
                                    </button>

                                    <!-- hangup/decline call -->
                                    <button
                                        :title="
                                            activeCall.is_incoming && activeCall.status === 4
                                                ? $t('call.decline_call')
                                                : $t('call.hangup_call')
                                        "
                                        type="button"
                                        class="inline-flex items-center gap-x-2 rounded-2xl bg-red-600 px-4 py-2 text-sm font-bold text-white shadow-xl hover:bg-red-500 transition-all duration-200"
                                        @click="hangupCall"
                                    >
                                        <MaterialDesignIcon icon-name="phone-hangup" class="size-4 rotate-[135deg]" />
                                        <span>{{
                                            activeCall.is_incoming && activeCall.status === 4
                                                ? $t("call.decline")
                                                : $t("call.hangup")
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
                            <div class="text-gray-500 dark:text-zinc-400">Enter an identity to call.</div>
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
                            <div class="px-4 py-3 border-b border-gray-200 dark:border-zinc-800 flex flex-col gap-3">
                                <div class="flex justify-between items-center">
                                    <h3
                                        class="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider"
                                    >
                                        Call History
                                    </h3>
                                    <div class="flex items-center gap-2">
                                        <button
                                            type="button"
                                            class="text-[10px] text-gray-400 hover:text-red-500 font-bold uppercase tracking-tighter transition-colors"
                                            @click="clearHistory"
                                        >
                                            {{ $t("app.clear_history") }}
                                        </button>
                                        <MaterialDesignIcon icon-name="history" class="size-4 text-gray-400" />
                                    </div>
                                </div>
                                <div class="relative">
                                    <input
                                        v-model="callHistorySearch"
                                        type="text"
                                        :placeholder="$t('call.search_history')"
                                        class="w-full pl-9 pr-4 py-2 bg-gray-50 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-lg text-sm focus:ring-blue-500 focus:border-blue-500 dark:text-white"
                                        @input="onCallHistorySearchInput"
                                    />
                                    <MaterialDesignIcon
                                        icon-name="magnify"
                                        class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-gray-400"
                                    />
                                </div>
                            </div>
                            <ul class="divide-y divide-gray-100 dark:divide-zinc-800">
                                <li
                                    v-for="entry in callHistory"
                                    :key="entry.id"
                                    class="px-4 py-3 hover:bg-gray-50 dark:hover:bg-zinc-800/50 transition-colors"
                                >
                                    <div class="flex items-center space-x-3">
                                        <div class="shrink-0">
                                            <LxmfUserIcon
                                                v-if="entry.remote_icon"
                                                :icon-name="entry.remote_icon.icon_name"
                                                :icon-foreground-colour="entry.remote_icon.foreground_colour"
                                                :icon-background-colour="entry.remote_icon.background_colour"
                                                class="size-8"
                                            />
                                            <div
                                                v-else
                                                :class="
                                                    entry.is_incoming
                                                        ? 'text-blue-500 bg-blue-50 dark:bg-blue-900/20'
                                                        : 'text-green-500 bg-green-50 dark:bg-green-900/20'
                                                "
                                                class="size-8 rounded-full flex items-center justify-center"
                                            >
                                                <MaterialDesignIcon
                                                    :icon-name="entry.is_incoming ? 'phone-incoming' : 'phone-outgoing'"
                                                    class="size-5"
                                                />
                                            </div>
                                        </div>
                                        <div class="flex-1 min-w-0">
                                            <div class="flex items-center justify-between">
                                                <p class="text-sm font-semibold text-gray-900 dark:text-white truncate">
                                                    {{ entry.remote_identity_name || $t("call.unknown") }}
                                                </p>
                                                <span
                                                    class="text-[10px] text-gray-500 dark:text-zinc-500 font-mono ml-2 shrink-0"
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
                                                        :title="entry.remote_identity_hash"
                                                    >
                                                        {{ entry.remote_identity_hash }}
                                                    </div>
                                                </div>
                                                <div class="flex items-center gap-1">
                                                    <button
                                                        v-if="!entry.is_contact"
                                                        type="button"
                                                        class="p-1.5 text-gray-400 hover:text-blue-500 transition-colors"
                                                        :title="'Add to contacts'"
                                                        @click="addContactFromHistory(entry)"
                                                    >
                                                        <MaterialDesignIcon icon-name="account-plus" class="size-4" />
                                                    </button>
                                                    <button
                                                        type="button"
                                                        class="p-1.5 text-gray-400 hover:text-red-500 transition-colors"
                                                        :title="$t('common.block')"
                                                        @click="blockIdentity(entry.remote_identity_hash)"
                                                    >
                                                        <MaterialDesignIcon icon-name="account-remove" class="size-4" />
                                                    </button>
                                                    <button
                                                        type="button"
                                                        class="text-[10px] text-blue-500 hover:text-blue-600 font-bold uppercase tracking-tighter"
                                                        @click="
                                                            destinationHash = entry.remote_identity_hash;
                                                            call(destinationHash);
                                                        "
                                                    >
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
                                class="p-3 border-t border-gray-100 dark:border-zinc-800 text-center"
                            >
                                <button
                                    type="button"
                                    class="text-xs text-blue-500 hover:text-blue-600 font-bold uppercase tracking-widest"
                                    @click="loadMoreCallHistory"
                                >
                                    {{ $t("call.load_more") }}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Voicemail Tab -->
                <div v-if="activeTab === 'voicemail'" class="flex-1 flex flex-col">
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
                                                v-if="voicemail.remote_icon"
                                                :icon-name="voicemail.remote_icon.icon_name"
                                                :icon-foreground-colour="voicemail.remote_icon.foreground_colour"
                                                :icon-background-colour="voicemail.remote_icon.background_colour"
                                                class="size-10"
                                            />
                                            <div
                                                v-else
                                                class="size-10 rounded-full bg-gray-200 dark:bg-zinc-800 flex items-center justify-center text-gray-400"
                                            >
                                                <MaterialDesignIcon icon-name="account" class="size-6" />
                                            </div>

                                            <button
                                                class="absolute inset-0 size-10 rounded-full flex items-center justify-center transition-all opacity-0 hover:opacity-100 bg-black/20 text-white"
                                                :class="{
                                                    'opacity-100 bg-red-500/80 animate-pulse':
                                                        playingVoicemailId === voicemail.id,
                                                }"
                                                @click="playVoicemail(voicemail)"
                                            >
                                                <MaterialDesignIcon
                                                    :icon-name="playingVoicemailId === voicemail.id ? 'stop' : 'play'"
                                                    class="size-6"
                                                />
                                            </button>
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
                                                    class="opacity-60 font-mono text-[10px] truncate"
                                                    :title="voicemail.remote_identity_hash"
                                                    >{{ formatDestinationHash(voicemail.remote_identity_hash) }}</span
                                                >
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

                <!-- Contacts Tab -->
                <div v-if="activeTab === 'contacts'" class="flex-1 flex flex-col">
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
                                                v-if="contact.remote_icon"
                                                :icon-name="contact.remote_icon.icon_name"
                                                :icon-foreground-colour="contact.remote_icon.foreground_colour"
                                                :icon-background-colour="contact.remote_icon.background_colour"
                                                class="size-10"
                                            />
                                            <div
                                                v-else
                                                class="size-10 rounded-full bg-blue-50 dark:bg-blue-900/20 text-blue-500 flex items-center justify-center"
                                            >
                                                <MaterialDesignIcon icon-name="account" class="size-6" />
                                            </div>
                                        </div>
                                        <div class="flex-1 min-w-0">
                                            <div class="flex items-center justify-between">
                                                <p class="text-sm font-bold text-gray-900 dark:text-white truncate">
                                                    {{ contact.name }}
                                                </p>
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
                                            <div class="flex items-center justify-between mt-1">
                                                <span
                                                    class="text-[10px] text-gray-500 dark:text-zinc-500 font-mono truncate"
                                                    :title="contact.remote_identity_hash"
                                                >
                                                    {{ formatDestinationHash(contact.remote_identity_hash) }}
                                                </span>
                                                <button
                                                    type="button"
                                                    class="text-[10px] bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 px-3 py-1 rounded-full font-bold uppercase tracking-wider hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors"
                                                    @click="
                                                        destinationHash = contact.remote_identity_hash;
                                                        activeTab = 'phone';
                                                        call(destinationHash);
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
                <div v-if="activeTab === 'ringtone' && config" class="flex-1 space-y-6">
                    <div
                        class="bg-white dark:bg-zinc-900 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-zinc-800"
                    >
                        <h3
                            class="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider mb-6 flex items-center gap-2"
                        >
                            <MaterialDesignIcon icon-name="music" class="size-5 text-blue-500" />
                            {{ $t("call.ringtone_settings") }}
                        </h3>

                        <div class="space-y-6">
                            <!-- Enabled Toggle -->
                            <div class="flex items-center justify-between">
                                <div>
                                    <div class="text-sm font-semibold text-gray-900 dark:text-white">
                                        {{ $t("call.enable_custom_ringtone") }}
                                    </div>
                                    <div class="text-xs text-gray-500 dark:text-zinc-400">
                                        {{ $t("call.enable_custom_ringtone_description") }}
                                    </div>
                                </div>
                                <button
                                    class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none"
                                    :class="
                                        config.custom_ringtone_enabled ? 'bg-blue-600' : 'bg-gray-200 dark:bg-zinc-700'
                                    "
                                    @click="
                                        config.custom_ringtone_enabled = !config.custom_ringtone_enabled;
                                        updateConfig({ custom_ringtone_enabled: config.custom_ringtone_enabled });
                                    "
                                >
                                    <span
                                        class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
                                        :class="config.custom_ringtone_enabled ? 'translate-x-5' : 'translate-x-0'"
                                    ></span>
                                </button>
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
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import Utils from "../../js/Utils";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import LxmfUserIcon from "../LxmfUserIcon.vue";
import Toggle from "../forms/Toggle.vue";
import ToastUtils from "../../js/ToastUtils";

export default {
    name: "CallPage",
    components: { MaterialDesignIcon, LxmfUserIcon, Toggle },
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
        callDuration() {
            if (!this.isCallEnded || !this.lastCall?.call_start_time) {
                return null;
            }
            const duration = Math.floor(Date.now() / 1000 - this.lastCall.call_start_time);
            return Utils.formatMinutesSeconds(duration);
        },
    },
    mounted() {
        this.getConfig();
        this.getAudioProfiles();
        this.getStatus();
        this.getHistory();
        this.getVoicemails();
        this.getContacts();
        this.getVoicemailStatus();
        this.getRingtones();
        this.getRingtoneStatus();

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
            this.getContacts();
        }, 10000);

        // update elapsed time every second
        this.elapsedTimeInterval = setInterval(() => {
            this.$forceUpdate();
        }, 1000);

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
        if (this.elapsedTimeInterval) clearInterval(this.elapsedTimeInterval);
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
        async addContactFromHistory(entry) {
            const name = prompt("Enter contact name:", entry.remote_identity_name || "");
            if (!name) return;
            try {
                await window.axios.post("/api/v1/telephone/contacts", {
                    name: name,
                    remote_identity_hash: entry.remote_identity_hash,
                });
                ToastUtils.success("Contact added");
                this.getHistory();
                this.getContacts();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || "Failed to add contact");
            }
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

                const newItems = response.data.call_history;
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
        async toggleDoNotDisturb(value) {
            try {
                await window.axios.post("/api/v1/config", {
                    key: "do_not_disturb_enabled",
                    value: value ? "true" : "false",
                });
                if (this.config) {
                    this.config.do_not_disturb_enabled = value;
                }
                ToastUtils.success(value ? "Do Not Disturb enabled" : "Do Not Disturb disabled");
            } catch {
                ToastUtils.error("Failed to update Do Not Disturb status");
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
            if (!confirm(`Are you sure you want to block this identity?`)) return;
            try {
                await window.axios.post("/api/v1/blocked-destinations", {
                    destination_hash: hash,
                });
                ToastUtils.success("Identity blocked");
                this.getHistory();
            } catch {
                ToastUtils.error("Failed to block identity");
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
        async getVoicemails() {
            try {
                const response = await window.axios.get("/api/v1/telephone/voicemails", {
                    params: { search: this.voicemailSearch },
                });
                this.voicemails = response.data.voicemails;
                this.unreadVoicemailsCount = response.data.unread_count;
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
        async getContacts() {
            try {
                const response = await window.axios.get("/api/v1/telephone/contacts", {
                    params: { search: this.contactsSearch },
                });
                this.contacts = response.data;
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
            this.contactForm = { name: "", remote_identity_hash: "" };
            const name = prompt("Enter contact name:");
            if (!name) return;
            const hash = prompt("Enter identity hash:");
            if (!hash) return;
            this.saveContact({ name, remote_identity_hash: hash });
        },
        openEditContactModal(contact) {
            this.editingContact = contact;
            const name = prompt("Edit contact name:", contact.name);
            if (!name) return;
            const hash = prompt("Edit identity hash:", contact.remote_identity_hash);
            if (!hash) return;
            this.saveContact({ id: contact.id, name, remote_identity_hash: hash });
        },
        async saveContact(contact) {
            try {
                if (contact.id) {
                    await window.axios.patch(`/api/v1/telephone/contacts/${contact.id}`, contact);
                    ToastUtils.success("Contact updated");
                } else {
                    await window.axios.post("/api/v1/telephone/contacts", contact);
                    ToastUtils.success("Contact added");
                }
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
        async playVoicemail(voicemail) {
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
