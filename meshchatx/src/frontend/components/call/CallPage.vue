<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex min-w-0 h-full flex-1 flex-col">
        <div class="flex h-full w-full flex-col bg-gray-100 dark:bg-zinc-950">
            <div class="w-full h-full overflow-y-auto">
                <div class="mx-auto w-full max-w-4xl p-4 md:p-6 flex-1 flex flex-col min-h-full">
                    <CallTabBar
                        :active-tab="activeTab"
                        :unread-voicemails-count="unreadVoicemailsCount"
                        @update:active-tab="activeTab = $event"
                    />

                    <!-- Phone Tab -->
                    <div v-if="activeTab === 'phone'" class="flex-1 flex flex-col pt-2">
                        <!-- LXST Disabled State -->
                        <div
                            v-if="config && !config.telephone_enabled"
                            class="flex-1 flex flex-col items-center justify-center py-12 px-4"
                        >
                            <div
                                class="w-full max-w-md bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 rounded-2xl p-8 flex flex-col items-center text-center shadow-xl"
                            >
                                <div
                                    class="size-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mb-4"
                                >
                                    <MaterialDesignIcon
                                        icon-name="phone-off"
                                        class="size-8 text-red-600 dark:text-red-400"
                                    />
                                </div>
                                <h2 class="text-xl font-bold text-gray-900 dark:text-white mb-2">
                                    {{ $t("call.lxst_disabled_title") }}
                                </h2>
                                <p class="text-sm text-gray-500 dark:text-zinc-400 mb-6">
                                    {{ $t("call.lxst_disabled_body") }}
                                </p>
                                <button
                                    type="button"
                                    class="flex items-center justify-center gap-2 rounded-2xl bg-blue-600 py-3 px-6 text-sm font-bold text-white shadow-lg shadow-blue-600/20 hover:bg-blue-500 transition-all duration-200"
                                    @click="updateConfig({ telephone_enabled: true })"
                                >
                                    <MaterialDesignIcon icon-name="phone" class="size-5" />
                                    {{ $t("call.enable_lxst") }}
                                </button>
                            </div>
                        </div>

                        <template v-if="config?.telephone_enabled">
                            <!-- Minimized call bar -->
                            <div
                                v-if="callMinimized && activeCall"
                                class="w-full flex-shrink-0 border-b border-gray-200 dark:border-zinc-800"
                            >
                                <div
                                    class="flex items-center gap-3 px-4 py-2 bg-blue-50/80 dark:bg-blue-900/20 backdrop-blur-sm"
                                >
                                    <div class="relative">
                                        <div
                                            class="size-8 rounded-full bg-gray-100 dark:bg-zinc-800 flex items-center justify-center overflow-hidden"
                                        >
                                            <LxmfUserIcon
                                                :custom-image="activeCall?.custom_image"
                                                :icon-name="activeCall?.remote_icon?.icon_name || 'account'"
                                                :icon-foreground-colour="activeCall?.remote_icon?.foreground_colour"
                                                :icon-background-colour="activeCall?.remote_icon?.background_colour"
                                                icon-class="size-7"
                                            />
                                        </div>
                                        <div
                                            class="absolute -bottom-0.5 -right-0.5 size-2.5 bg-green-500 rounded-full border-2 border-white dark:border-zinc-900"
                                        ></div>
                                    </div>
                                    <div class="flex-1 min-w-0">
                                        <div class="text-sm font-bold text-gray-900 dark:text-white truncate">
                                            {{ activeCall?.remote_identity_name || $t("call.unknown") }}
                                        </div>
                                        <div
                                            class="text-[10px] text-gray-500 dark:text-zinc-400 flex items-center gap-2"
                                        >
                                            <span class="size-1.5 bg-green-500 rounded-full animate-pulse"></span>
                                            <span>{{ $t("call.active") }}</span>
                                            <span v-if="elapsedTime" class="font-mono">· {{ elapsedTime }}</span>
                                        </div>
                                    </div>
                                    <div class="flex items-center gap-1 shrink-0">
                                        <button
                                            type="button"
                                            class="size-8 flex items-center justify-center rounded-full hover:bg-black/5 dark:hover:bg-white/10 transition-colors text-gray-600 dark:text-zinc-400"
                                            title="Expand call"
                                            @click="callMinimized = false"
                                        >
                                            <MaterialDesignIcon icon-name="chevron-up" class="size-5" />
                                        </button>
                                        <button
                                            type="button"
                                            class="size-8 flex items-center justify-center rounded-full hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors text-red-600 dark:text-red-400"
                                            title="Hangup"
                                            @click="hangupCall"
                                        >
                                            <MaterialDesignIcon icon-name="phone-hangup" class="size-4 rotate-135" />
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <!-- Full call UI or settings -->
                            <div
                                v-if="(activeCall || isCallEnded || initiationStatus) && !callMinimized"
                                class="flex-1 flex flex-col items-center justify-center py-12 px-4"
                            >
                                <div
                                    class="w-full max-w-md border-b border-gray-200 dark:border-zinc-800 p-8! flex flex-col items-center text-center relative overflow-hidden"
                                >
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
                                                'ring-4 ring-blue-500/20 animate-pulse':
                                                    activeCall && activeCall.status === 4,
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

                                    <div class="relative z-10 space-y-1 mb-8 flex flex-col items-center text-center">
                                        <h2
                                            class="text-2xl font-bold text-gray-900 dark:text-white truncate max-w-[280px]"
                                        >
                                            {{
                                                (activeCall || lastCall)?.remote_identity_name ||
                                                initiationTargetName ||
                                                $t("call.unknown")
                                            }}
                                        </h2>
                                        <div
                                            v-if="
                                                (activeCall || lastCall)?.remote_identity_hash || initiationTargetHash
                                            "
                                            class="text-xs font-mono text-gray-400 dark:text-zinc-500 tracking-wider"
                                        >
                                            {{
                                                formatDestinationHash(
                                                    (activeCall || lastCall)?.remote_identity_hash ||
                                                        initiationTargetHash
                                                )
                                            }}
                                        </div>
                                        <div
                                            v-if="activeCall"
                                            class="mt-1 flex items-center justify-center gap-2 text-[11px] text-gray-500 dark:text-zinc-400"
                                        >
                                            <span
                                                v-if="activeCall.path_hops != null"
                                                class="inline-flex items-center gap-1 rounded-full bg-gray-100 dark:bg-zinc-800 px-2 py-0.5"
                                            >
                                                <MaterialDesignIcon icon-name="sitemap-outline" class="size-4" />
                                                {{ activeCall.path_hops }} hops
                                            </span>
                                            <span
                                                v-if="activeCall.path_interface"
                                                class="inline-flex items-center gap-1 rounded-full bg-gray-100 dark:bg-zinc-800 px-2 py-0.5 max-w-[16rem]"
                                            >
                                                <MaterialDesignIcon icon-name="access-point-network" class="size-4" />
                                                <span class="truncate">{{ activeCall.path_interface }}</span>
                                            </span>
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
                                                            activeCall &&
                                                            activeCall.is_incoming &&
                                                            activeCall.status === 4
                                                        "
                                                        class="text-blue-600 dark:text-blue-400 font-bold text-sm"
                                                        >{{ $t("call.incoming_call") }}</span
                                                    >
                                                    <span
                                                        v-else
                                                        class="text-gray-700 dark:text-zinc-300 font-bold text-sm flex items-center gap-2"
                                                    >
                                                        <span v-if="activeCall && activeCall.status === 0"
                                                            >Busy...</span
                                                        >
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
                                                        <span v-else-if="activeCall && activeCall.status === 3"
                                                            >Available</span
                                                        >
                                                        <span
                                                            v-else-if="activeCall && activeCall.status === 4"
                                                            class="animate-pulse"
                                                            >Ringing...</span
                                                        >
                                                        <span v-else-if="activeCall && activeCall.status === 5">{{
                                                            $t("call.establishing_link")
                                                        }}</span>
                                                        <span
                                                            v-else-if="activeCall && activeCall.status === 6"
                                                            class="text-green-500 flex items-center gap-2"
                                                        >
                                                            <span
                                                                class="size-2 bg-green-500 rounded-full animate-ping"
                                                            ></span>
                                                            Connected
                                                        </span>
                                                        <span v-else-if="activeCall"
                                                            >Status: {{ activeCall.status }}</span
                                                        >
                                                    </span>

                                                    <!-- Duration -->
                                                    <div
                                                        v-if="activeCall && activeCall.status === 6 && elapsedTime"
                                                        class="text-xs font-mono text-gray-400 dark:text-zinc-500 mt-1"
                                                    >
                                                        {{ elapsedTime }}
                                                    </div>
                                                    <div
                                                        v-if="activeCall && activeCall.status === 6"
                                                        class="mt-3 grid grid-cols-2 gap-2 text-xs w-full max-w-xs"
                                                    >
                                                        <div
                                                            class="rounded-xl bg-gray-50 dark:bg-zinc-800/70 border border-gray-100 dark:border-zinc-700/70 px-2 py-1.5 text-left"
                                                        >
                                                            <div class="text-[10px] text-gray-500 dark:text-zinc-400">
                                                                {{ $t("call.tx_packets") }}
                                                            </div>
                                                            <div class="font-semibold text-gray-800 dark:text-zinc-100">
                                                                {{ formatNumber(activeCall.tx_packets) }}
                                                            </div>
                                                        </div>
                                                        <div
                                                            class="rounded-xl bg-gray-50 dark:bg-zinc-800/70 border border-gray-100 dark:border-zinc-700/70 px-2 py-1.5 text-left"
                                                        >
                                                            <div class="text-[10px] text-gray-500 dark:text-zinc-400">
                                                                {{ $t("call.rx_packets") }}
                                                            </div>
                                                            <div class="font-semibold text-gray-800 dark:text-zinc-100">
                                                                {{ formatNumber(activeCall.rx_packets) }}
                                                            </div>
                                                        </div>
                                                        <div
                                                            class="rounded-xl bg-gray-50 dark:bg-zinc-800/70 border border-gray-100 dark:border-zinc-700/70 px-2 py-1.5 text-left"
                                                        >
                                                            <div class="text-[10px] text-gray-500 dark:text-zinc-400">
                                                                {{ $t("call.tx_data") }}
                                                            </div>
                                                            <div class="font-semibold text-gray-800 dark:text-zinc-100">
                                                                {{ formatBytes(activeCall.tx_bytes) }}
                                                            </div>
                                                        </div>
                                                        <div
                                                            class="rounded-xl bg-gray-50 dark:bg-zinc-800/70 border border-gray-100 dark:border-zinc-700/70 px-2 py-1.5 text-left"
                                                        >
                                                            <div class="text-[10px] text-gray-500 dark:text-zinc-400">
                                                                {{ $t("call.rx_data") }}
                                                            </div>
                                                            <div class="font-semibold text-gray-800 dark:text-zinc-100">
                                                                {{ formatBytes(activeCall.rx_bytes) }}
                                                            </div>
                                                        </div>
                                                        <div
                                                            class="rounded-xl bg-gray-50 dark:bg-zinc-800/70 border border-gray-100 dark:border-zinc-700/70 px-2 py-1.5 text-left"
                                                        >
                                                            <div class="text-[10px] text-gray-500 dark:text-zinc-400">
                                                                {{ $t("call.tx_rate") }}
                                                            </div>
                                                            <div class="font-semibold text-gray-800 dark:text-zinc-100">
                                                                {{ formatBitrate(activeCall.tx_bps) }}
                                                            </div>
                                                        </div>
                                                        <div
                                                            class="rounded-xl bg-gray-50 dark:bg-zinc-800/70 border border-gray-100 dark:border-zinc-700/70 px-2 py-1.5 text-left"
                                                        >
                                                            <div class="text-[10px] text-gray-500 dark:text-zinc-400">
                                                                {{ $t("call.rx_rate") }}
                                                            </div>
                                                            <div class="font-semibold text-gray-800 dark:text-zinc-100">
                                                                {{ formatBitrate(activeCall.rx_bps) }}
                                                            </div>
                                                        </div>
                                                    </div>
                                                    <div
                                                        v-if="activeCall && activeCall.status === 6"
                                                        class="mt-2 text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-zinc-400"
                                                    >
                                                        {{
                                                            activeCall.is_half_duplex
                                                                ? $t("call.half_duplex")
                                                                : $t("call.full_duplex")
                                                        }}
                                                        <span v-if="activeCall.is_half_duplex">
                                                            ·
                                                            {{
                                                                localPttActive
                                                                    ? $t("call.ptt_transmitting")
                                                                    : $t("call.ptt_listening")
                                                            }}
                                                        </span>
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
                                                class="input-field rounded-xl! py-2! shadow-xs"
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

                                            <select
                                                v-model="selectedCallModeId"
                                                class="input-field rounded-xl! py-2! shadow-xs"
                                                @change="switchCallMode(selectedCallModeId)"
                                            >
                                                <option
                                                    v-for="callMode in callModes"
                                                    :key="callMode.id"
                                                    :value="callMode.id"
                                                >
                                                    {{ callMode.name }}
                                                </option>
                                            </select>

                                            <div class="flex justify-center gap-4">
                                                <!-- mute/unmute mic -->
                                                <button
                                                    type="button"
                                                    :title="isMicMuted ? $t('call.unmute_mic') : $t('call.mute_mic')"
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
                                                    :title="
                                                        isSpeakerMuted
                                                            ? $t('call.unmute_speaker')
                                                            : $t('call.mute_speaker')
                                                    "
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
                                            </div>

                                            <button
                                                v-if="isHalfDuplexCall"
                                                type="button"
                                                class="w-full flex items-center justify-center gap-2 rounded-2xl py-5 text-base font-bold text-white shadow-xl transition-all duration-150 select-none touch-none"
                                                :class="
                                                    localPttActive
                                                        ? 'bg-amber-500 shadow-amber-500/30 scale-[1.02]'
                                                        : 'bg-blue-600 shadow-blue-600/20 hover:bg-blue-500'
                                                "
                                                :title="$t('call.ptt_hold_hint')"
                                                @pointerdown.prevent="setPttActive(true)"
                                                @pointerup.prevent="setPttActive(false)"
                                                @pointerleave="setPttActive(false)"
                                                @pointercancel="setPttActive(false)"
                                            >
                                                <MaterialDesignIcon
                                                    :icon-name="localPttActive ? 'microphone' : 'access-point-network'"
                                                    class="size-7"
                                                />
                                                <span>{{
                                                    localPttActive
                                                        ? $t("call.ptt_transmitting")
                                                        : $t("call.ptt_hold_to_talk")
                                                }}</span>
                                            </button>
                                            <div
                                                v-if="isHalfDuplexCall"
                                                class="text-center text-[11px] text-gray-500 dark:text-zinc-400"
                                            >
                                                {{ $t("call.ptt_spacebar_hint") }}
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

                                        <!-- minimize call -->
                                        <button
                                            type="button"
                                            class="flex items-center justify-center gap-2 rounded-2xl bg-gray-100 dark:bg-zinc-800 py-3 px-4 text-sm font-bold text-gray-700 dark:text-zinc-300 hover:bg-gray-200 dark:hover:bg-zinc-700 transition-all duration-200"
                                            @click="callMinimized = true"
                                        >
                                            <MaterialDesignIcon icon-name="chevron-down" class="size-5" />
                                            <span>{{ $t("call.minimize") }}</span>
                                        </button>

                                        <!-- hangup/decline call -->
                                        <button
                                            type="button"
                                            class="w-full flex items-center justify-center gap-2 rounded-2xl bg-red-600 py-4 text-sm font-bold text-white shadow-xl shadow-red-600/20 hover:bg-red-500 transition-all duration-200"
                                            @click="hangupCall"
                                        >
                                            <MaterialDesignIcon icon-name="phone-hangup" class="size-5 rotate-135" />
                                            <span>{{
                                                activeCall && activeCall.is_incoming && activeCall.status === 4
                                                    ? $t("call.decline")
                                                    : $t("call.hangup")
                                            }}</span>
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <div
                                v-if="!((activeCall || isCallEnded || initiationStatus) && !callMinimized)"
                                class="space-y-6 my-6 max-w-3xl mx-auto w-full"
                            >
                                <div class="w-full border-b border-gray-200 dark:border-zinc-800 py-2">
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
                                            <p class="text-xs text-gray-500 dark:text-zinc-400">
                                                Enter an identity to call.
                                            </p>
                                        </div>
                                    </div>

                                    <div class="space-y-4">
                                        <div class="relative">
                                            <div class="flex gap-2">
                                                <div class="relative flex-1">
                                                    <input
                                                        v-model="destinationHash"
                                                        type="text"
                                                        :placeholder="$t('call.identity_or_name')"
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

                                        <div
                                            class="pt-2 flex flex-col items-stretch gap-4 lg:flex-row lg:items-start lg:justify-between"
                                        >
                                            <div class="flex min-w-0 flex-1 flex-col gap-2">
                                                <div v-if="config?.telephone_enabled" class="flex flex-col gap-2">
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
                                                        id="telephone-announce-toggle"
                                                        :model-value="config?.telephone_announce_enabled"
                                                        label="Announce Telephone Presence (LXST)"
                                                        @update:model-value="toggleTelephoneAnnounceEnabled"
                                                    />
                                                    <div class="flex flex-col gap-1">
                                                        <Toggle
                                                            id="web-audio-toggle"
                                                            :model-value="webAudioBridgeEnabled"
                                                            :disabled="webAudioBridgeRequired"
                                                            :label="
                                                                isMeshChatXAndroid()
                                                                    ? 'Native Audio Bridge'
                                                                    : 'Web Audio Bridge'
                                                            "
                                                            @update:model-value="onToggleWebAudio"
                                                        />
                                                        <div class="text-xs text-gray-500 dark:text-zinc-400 px-1">
                                                            <template v-if="isMeshChatXAndroid()">
                                                                Always on for Android calls. Audio goes through the
                                                                phone's native mic and speaker (AudioRecord and
                                                                AudioTrack), never the WebView's browser microphone API.
                                                            </template>
                                                            <template v-else-if="webAudioBridgeRequired">
                                                                Required on this host (no LXST host audio device).
                                                                Browser mic and speaker are used for calls.
                                                            </template>
                                                            <template v-else>
                                                                Web audio bridge allows web/electron to hook into LXST
                                                                backend for passing microphone and audio streams to
                                                                active telephone calls.
                                                            </template>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                            <div class="flex w-full shrink-0 flex-col gap-2 lg:w-auto">
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
                                                        class="input-field min-w-0 rounded-lg! border-gray-200! py-1! px-2! text-xs! dark:border-zinc-800! lg:min-w-[120px]"
                                                        @change="
                                                            updateConfig({
                                                                telephone_audio_profile_id:
                                                                    config.telephone_audio_profile_id,
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
                                                <div class="flex flex-col gap-1">
                                                    <div
                                                        class="text-[10px] font-bold text-gray-500 uppercase tracking-widest px-1"
                                                    >
                                                        {{ $t("call.default_duplex") }}
                                                    </div>
                                                    <select
                                                        v-if="config"
                                                        v-model="config.telephone_call_mode_id"
                                                        class="input-field min-w-0 rounded-lg! border-gray-200! py-1! px-2! text-xs! dark:border-zinc-800! lg:min-w-[120px]"
                                                        @change="
                                                            updateConfig({
                                                                telephone_call_mode_id: config.telephone_call_mode_id,
                                                            })
                                                        "
                                                    >
                                                        <option
                                                            v-for="callMode in callModes"
                                                            :key="callMode.id"
                                                            :value="callMode.id"
                                                        >
                                                            {{ callMode.name }}
                                                        </option>
                                                    </select>
                                                </div>

                                                <!-- Web Audio Device Selection -->
                                                <div v-if="showWebAudioDeviceSelector" class="flex flex-col gap-2 mt-2">
                                                    <div class="flex flex-col gap-1">
                                                        <div
                                                            class="text-[10px] font-bold text-gray-500 uppercase tracking-widest px-1"
                                                        >
                                                            Microphone
                                                        </div>
                                                        <select
                                                            v-model="selectedAudioInputId"
                                                            class="input-field py-1! px-2! text-[10px]! rounded-lg! border-gray-200! dark:border-zinc-800! min-w-[120px]"
                                                            @change="restartWebAudio"
                                                        >
                                                            <option
                                                                v-for="(d, idx) in audioInputDevices"
                                                                :key="d.deviceId || `in-${idx}`"
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
                                                            class="input-field py-1! px-2! text-[10px]! rounded-lg! border-gray-200! dark:border-zinc-800! min-w-[120px]"
                                                            @change="restartWebAudio"
                                                        >
                                                            <option
                                                                v-for="(d, idx) in audioOutputDevices"
                                                                :key="d.deviceId || `out-${idx}`"
                                                                :value="d.deviceId"
                                                            >
                                                                {{ d.label || "Speaker" }}
                                                            </option>
                                                        </select>
                                                    </div>
                                                    <button
                                                        class="text-[10px] bg-gray-100 text-gray-600 dark:bg-zinc-800 dark:text-zinc-400 py-1 rounded-lg font-bold uppercase tracking-wider hover:bg-gray-200 dark:hover:bg-zinc-700 transition-colors"
                                                        type="button"
                                                        @click="onRefreshAudioDevices"
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
                                <div class="w-full border-b border-gray-200 dark:border-zinc-800 p-0! overflow-hidden">
                                    <div
                                        class="px-5 py-4 border-b border-gray-100 dark:border-zinc-800 flex flex-col gap-4 bg-transparent"
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
                                                class="input-field py-2! pl-10!"
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
                                                            entry.contact_image ||
                                                            getContactByHash(entry.remote_identity_hash)?.custom_image
                                                        "
                                                        :icon-name="
                                                            entry.remote_icon ? entry.remote_icon.icon_name : ''
                                                        "
                                                        :icon-foreground-colour="
                                                            entry.remote_icon ? entry.remote_icon.foreground_colour : ''
                                                        "
                                                        :icon-background-colour="
                                                            entry.remote_icon ? entry.remote_icon.background_colour : ''
                                                        "
                                                        icon-class="size-10"
                                                    />
                                                    <div
                                                        class="absolute -bottom-1 -right-1 bg-white dark:bg-zinc-900 rounded-full p-0.5 shadow-xs border border-gray-100 dark:border-zinc-800 shrink-0 flex items-center justify-center size-5"
                                                    >
                                                        <MaterialDesignIcon
                                                            :icon-name="
                                                                entry.is_incoming ? 'phone-incoming' : 'phone-outgoing'
                                                            "
                                                            :class="
                                                                entry.is_incoming ? 'text-blue-500' : 'text-green-500'
                                                            "
                                                            class="size-3"
                                                        />
                                                    </div>
                                                </div>

                                                <div class="flex-1 min-w-0">
                                                    <div class="flex items-center justify-between">
                                                        <div
                                                            class="text-sm font-bold text-gray-900 dark:text-white truncate"
                                                        >
                                                            {{ entry.remote_identity_name || $t("call.unknown") }}
                                                        </div>
                                                        <div
                                                            class="text-[10px] text-gray-500 dark:text-zinc-500 font-mono shrink-0"
                                                        >
                                                            {{
                                                                entry.timestamp
                                                                    ? formatDateTime(entry.timestamp * 1000)
                                                                    : ""
                                                            }}
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
                                                            class="flex items-center gap-1.5 opacity-100 transition-opacity shrink-0 ml-4 lg:opacity-0 lg:group-hover:opacity-100"
                                                        >
                                                            <button
                                                                v-if="!entry.is_contact"
                                                                type="button"
                                                                class="p-1.5 rounded-lg text-gray-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all shrink-0"
                                                                title="Add to contacts"
                                                                @click="addContactFromHistory(entry)"
                                                            >
                                                                <MaterialDesignIcon
                                                                    icon-name="account-plus"
                                                                    class="size-4"
                                                                />
                                                            </button>
                                                            <button
                                                                type="button"
                                                                class="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all shrink-0"
                                                                :title="$t('common.block')"
                                                                @click="blockIdentity(entry.remote_identity_hash)"
                                                            >
                                                                <MaterialDesignIcon
                                                                    icon-name="account-remove"
                                                                    class="size-4"
                                                                />
                                                            </button>
                                                            <button
                                                                type="button"
                                                                class="p-1.5 rounded-lg text-gray-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all shrink-0"
                                                                :title="$t('contacts.send_message')"
                                                                @click="openMessageFromHistory(entry)"
                                                            >
                                                                <MaterialDesignIcon
                                                                    icon-name="message-text-outline"
                                                                    class="size-4"
                                                                />
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
                        </template>
                    </div>

                    <!-- Phonebook Tab -->
                    <CallPhonebookTab
                        :active="activeTab === 'phonebook'"
                        :discovery-search="discoverySearch"
                        :total-discovery-count="totalDiscoveryCount"
                        :discovery-announces="discoveryAnnounces"
                        :has-more-discovery="hasMoreDiscovery"
                        :format-time-ago="formatTimeAgo"
                        :format-destination-hash="formatDestinationHash"
                        @update:discovery-search="discoverySearch = $event"
                        @search-input="onDiscoverySearchInput"
                        @copy-hash="copyHash"
                        @load-more="loadMoreDiscovery"
                        @call="onPhonebookCall"
                    />

                    <CallVoicemailTab
                        :active="activeTab === 'voicemail'"
                        :voicemail-search="voicemailSearch"
                        :config="config"
                        :voicemail-status="voicemailStatus"
                        :voicemails="voicemails"
                        :is-generating-greeting="isGeneratingGreeting"
                        :is-uploading-greeting="isUploadingGreeting"
                        :is-playing-greeting="isPlayingGreeting"
                        :get-contact-by-hash="getContactByHash"
                        :format-date-time="formatDateTime"
                        :format-duration="formatDuration"
                        :format-destination-hash="formatDestinationHash"
                        @update:voicemail-search="voicemailSearch = $event"
                        @search-input="onVoicemailSearchInput"
                        @update-config="onVoicemailUpdateConfig"
                        @patch-config="onVoicemailPatchConfig"
                        @save-and-generate="onVoicemailSaveAndGenerate"
                        @upload-greeting="uploadGreeting"
                        @start-recording-greeting="startRecordingGreetingMic"
                        @stop-recording-greeting="stopRecordingGreetingMic"
                        @delete-greeting="deleteGreeting"
                        @play-greeting="playGreeting"
                        @copy-hash="copyHash"
                        @mark-read="markVoicemailAsRead"
                        @call-back="onPhonebookCall"
                        @delete="deleteVoicemail"
                    />

                    <!-- Contacts Tab -->
                    <CallContactsTab
                        :active="activeTab === 'contacts'"
                        :contacts-search="contactsSearch"
                        :contacts="contacts"
                        :format-destination-hash="formatDestinationHash"
                        @update:contacts-search="contactsSearch = $event"
                        @search-input="onContactsSearchInput"
                        @add="openAddContactModal"
                        @edit="openEditContactModal"
                        @delete="deleteContact"
                        @copy-hash="copyHash"
                        @call="onPhonebookCall"
                    />

                    <!-- Ringtone Tab -->
                    <div v-if="activeTab === 'ringtone' && config" class="flex-1 space-y-6 max-w-3xl mx-auto w-full">
                        <div class="w-full border-b border-gray-200 dark:border-zinc-800 py-6">
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
                                    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                                        <div class="flex-1">
                                            <div class="flex items-center justify-between mb-1">
                                                <div class="text-sm font-semibold text-gray-900 dark:text-white">
                                                    {{ $t("call.enable_custom_ringtone") }}
                                                </div>
                                                <button
                                                    class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden"
                                                    :class="
                                                        config.custom_ringtone_enabled
                                                            ? 'bg-blue-600'
                                                            : 'bg-gray-200 dark:bg-zinc-700'
                                                    "
                                                    @click="
                                                        config.custom_ringtone_enabled =
                                                            !config.custom_ringtone_enabled;
                                                        updateConfig({
                                                            custom_ringtone_enabled: config.custom_ringtone_enabled,
                                                        });
                                                    "
                                                >
                                                    <span
                                                        class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out"
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
                                        class="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pt-4 border-t border-gray-100 dark:border-zinc-800/50"
                                    >
                                        <div class="flex-1">
                                            <div class="flex items-center justify-between mb-1">
                                                <div class="text-sm font-semibold text-gray-900 dark:text-white">
                                                    Tone Generator
                                                </div>
                                                <button
                                                    class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden"
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
                                                        class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out"
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
                                        <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
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
                                                class="input-field py-1.5! px-3! text-sm! rounded-xl! border-gray-200! dark:border-zinc-800! min-w-[200px]"
                                                @change="
                                                    updateConfig({
                                                        ringtone_preferred_id: config.ringtone_preferred_id,
                                                    })
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
                                                            class="text-sm bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-700 rounded-sm px-2 py-1 flex-1 min-w-0"
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
                                                            class="shrink-0 text-[10px] uppercase font-bold text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/40 px-1.5 py-0.5 rounded-sm"
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
                                    :placeholder="$t('call.search_recordings')"
                                    class="block w-full rounded-lg border-0 py-2 pl-10 text-gray-900 dark:text-white shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
                                    @input="onRecordingSearchInput"
                                />
                                <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                                    <MaterialDesignIcon icon-name="magnify" class="size-5 text-gray-400" />
                                </div>
                            </div>
                        </div>

                        <div class="flex-1 overflow-y-auto min-h-0">
                            <div class="border-b border-gray-200 dark:border-zinc-800 overflow-hidden">
                                <div v-if="recordings.length === 0" class="py-12 text-center">
                                    <MaterialDesignIcon
                                        icon-name="microphone-off"
                                        class="size-12 text-gray-300 dark:text-zinc-700 mx-auto mb-2"
                                    />
                                    <p class="text-gray-500 dark:text-zinc-500 text-sm">
                                        {{ $t("call.no_recordings") }}
                                    </p>
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
                                                    <span
                                                        class="text-[10px] text-gray-500 dark:text-zinc-500 font-mono"
                                                    >
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
                                                        >{{
                                                            formatDestinationHash(recording.remote_identity_hash)
                                                        }}</span
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
                                                                playingRecordingId === recording.id &&
                                                                playingSide === 'rx'
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
                                                                playingRecordingId === recording.id &&
                                                                playingSide === 'tx'
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
            class="fixed inset-0 z-150 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs transition-opacity"
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
                            <p class="text-[10px] text-gray-400 mt-2 uppercase font-bold tracking-widest">
                                Profile Image
                            </p>
                        </div>
                        <div>
                            <label
                                class="block text-xs font-bold text-gray-500 dark:text-zinc-400 uppercase tracking-wider mb-1.5 ml-1"
                            >
                                {{ $t("call.contact_name") }}
                            </label>
                            <input
                                v-model="contactForm.name"
                                type="text"
                                class="input-field"
                                placeholder="e.g. John Doe"
                            />
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
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div>
                                <label
                                    class="block text-xs font-bold text-gray-500 dark:text-zinc-400 uppercase tracking-wider mb-1.5 ml-1"
                                >
                                    {{ $t("app.lxmf_address") }}
                                </label>
                                <input
                                    v-model="contactForm.lxmf_address"
                                    type="text"
                                    class="input-field font-mono text-xs"
                                    :placeholder="$t('common.optional')"
                                />
                            </div>
                            <div>
                                <label
                                    class="block text-xs font-bold text-gray-500 dark:text-zinc-400 uppercase tracking-wider mb-1.5 ml-1"
                                >
                                    {{ $t("identities.lxst_address") }}
                                </label>
                                <input
                                    v-model="contactForm.lxst_address"
                                    type="text"
                                    class="input-field font-mono text-xs"
                                    :placeholder="$t('common.optional')"
                                />
                            </div>
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
                            class="flex-2 px-6 py-3 rounded-2xl bg-blue-600 text-white font-bold shadow-lg shadow-blue-600/20 hover:bg-blue-500 transition-all active:scale-95"
                            @click="saveContact(contactForm)"
                        >
                            {{ $t("call.save_contact") }}
                        </button>
                    </div>
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
import DialogUtils from "../../js/DialogUtils";
import {
    WEB_AUDIO_MIC_TOAST_KEY,
    classifyGetUserMediaError,
    isBraveBrowser,
    isMeshChatXAndroid as detectMeshChatXAndroid,
    promptMicrophoneAccess,
    queryMicrophonePermissionState,
} from "../../js/webAudioMicPermission";
import RingtoneEditor from "./audio/RingtoneEditor.vue";
import CallPhonebookTab from "./tabs/CallPhonebookTab.vue";
import CallContactsTab from "./tabs/CallContactsTab.vue";
import CallVoicemailTab from "./tabs/CallVoicemailTab.vue";
import CallTabBar from "./tabs/CallTabBar.vue";

// Keep this as a same-origin static asset URL so strict CSP can load it.
const telephonePcmCaptureWorkletUrl = "/assets/js/telephone-pcm-capture.worklet.js";

export default {
    name: "CallPage",
    components: {
        MaterialDesignIcon,
        LxmfUserIcon,
        Toggle,
        RingtoneEditor,
        CallPhonebookTab,
        CallContactsTab,
        CallVoicemailTab,
        CallTabBar,
    },
    data() {
        return {
            config: null,
            activeCall: null,
            webAudioBridgeRequired: false,
            audioProfiles: [],
            selectedAudioProfileId: null,
            callModes: [],
            selectedCallModeId: 1,
            localPttActive: false,
            pttKeyHeld: false,
            destinationHash: "",
            callHistory: [],
            callHistorySearch: "",
            callHistoryLimit: 10,
            callHistoryOffset: 0,
            hasMoreCallHistory: false,
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
                lxmf_address: "",
                lxst_address: "",
            },
            searchDebounceTimeout: null,
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
            audioSourceNode: null,
            audioNoiseHighpass: null,
            audioNoiseCompressor: null,
            audioProcessor: null,
            audioWorkletNode: null,
            audioSilentGain: null,
            audioFrameMs: 60,
            audioInputDevices: [],
            audioOutputDevices: [],
            selectedAudioInputId: null,
            selectedAudioOutputId: null,
            webAudioStartBlocked: false,
            webAudioMicReady: false,
            webAudioStartInFlight: false,
            remoteAudioEl: null,
            useAndroidNativeTelephone: false,
            androidNativeTelephoneListener: null,
            localAudioLevel: 0,
            remoteAudioLevel: 0,
            localAudioTarget: 0,
            remoteAudioTarget: 0,
            visualizerRafId: null,
            visualizerPhase: 0,
            visualizerEnabled: true,
            prevCallTxBytes: 0,
            prevCallRxBytes: 0,
            callMinimized: false,
        };
    },
    computed: {
        webAudioBridgeEnabled() {
            return Boolean(this.webAudioBridgeRequired || this.config?.telephone_web_audio_enabled);
        },
        showWebAudioDeviceSelector() {
            // Android routes call audio through the native mic/speaker, not a
            // browser device picker, so the Web Audio device selector only
            // applies to browser/Electron hosts.
            return this.webAudioBridgeEnabled && !this.isMeshChatXAndroid();
        },
        isMicMuted() {
            return this.localMicMuted;
        },
        isSpeakerMuted() {
            return this.localSpeakerMuted;
        },
        isHalfDuplexCall() {
            return Boolean(this.activeCall && this.activeCall.status === 6 && this.activeCall.is_half_duplex);
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
        activeCall() {
            this.stopAudioVisualizer();
        },
    },
    mounted() {
        this.getConfig();
        this.getAudioProfiles();
        this.getCallModes();
        this.getStatus();
        this.getHistory();
        this.getVoicemails();
        this.getRecordings();
        this.getContacts();
        this.getDiscovery();
        this.getVoicemailStatus();
        this.getRingtones();
        this.getRingtoneStatus();
        this.markMissedCallsViewed();

        GlobalEmitter.on("telephone-history-updated", this.getHistory);
        GlobalEmitter.on("telephone-history-updated", this.getVoicemails);
        GlobalEmitter.on("telephone-history-updated", this.markMissedCallsViewed);

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

        window.addEventListener("keydown", this.onPttKeyDown);
        window.addEventListener("keyup", this.onPttKeyUp);
        window.addEventListener("blur", this.onPttWindowBlur);

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
        GlobalEmitter.off("telephone-history-updated", this.markMissedCallsViewed);

        if (this.statusInterval) clearInterval(this.statusInterval);
        if (this.historyInterval) clearInterval(this.historyInterval);
        if (this.elapsedTimeInterval) clearInterval(this.elapsedTimeInterval);
        if (this.endedTimeout) clearTimeout(this.endedTimeout);
        window.removeEventListener("keydown", this.onPttKeyDown);
        window.removeEventListener("keyup", this.onPttKeyUp);
        window.removeEventListener("blur", this.onPttWindowBlur);
        if (this.localPttActive) {
            this.setPttActive(false);
        }
        this.stopAudioVisualizer();
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
        formatNumber(value) {
            return Utils.formatNumber(value || 0);
        },
        formatBitrate(bps) {
            const rate = Number(bps) || 0;
            if (rate < 1000) return `${Math.round(rate)} bps`;
            if (rate < 1000000) return `${(rate / 1000).toFixed(1)} kbps`;
            return `${(rate / 1000000).toFixed(2)} Mbps`;
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
        capturePeakLevel(samples) {
            if (!samples || samples.length === 0) return 0;
            let peak = 0;
            for (let i = 0; i < samples.length; i += 1) {
                const value = Math.abs(samples[i]);
                if (value > peak) peak = value;
            }
            return peak;
        },
        extractInt16Samples(payload) {
            if (!payload) return null;
            if (payload instanceof ArrayBuffer) {
                return new Int16Array(payload);
            }
            if (ArrayBuffer.isView(payload)) {
                const byteLengthEven = Math.floor(payload.byteLength / 2) * 2;
                return new Int16Array(payload.buffer, payload.byteOffset, byteLengthEven / 2);
            }
            return null;
        },
        computeSignalLevel(samples, scale = 1) {
            if (!samples || samples.length === 0) return 0;
            let peak = 0;
            let sumSq = 0;
            for (let i = 0; i < samples.length; i += 1) {
                const value = Math.abs(samples[i]) / scale;
                if (value > peak) peak = value;
                sumSq += value * value;
            }
            const rms = Math.sqrt(sumSq / samples.length);
            const boosted = Math.max(peak * 0.8, rms * 2.4);
            return this.normalizeAudioLevel(boosted);
        },
        normalizeAudioLevel(level) {
            if (!Number.isFinite(level)) return 0;
            const normalized = level > 1 && level <= 100 ? level / 100 : level;
            return Math.max(0, Math.min(1, normalized));
        },
        disableAudioVisualizer() {
            this.visualizerEnabled = false;
            this.stopAudioVisualizer();
        },
        updateVisualizerFromCallStats(newCall, oldCall) {
            if (!newCall || newCall.status !== 6) {
                this.prevCallTxBytes = 0;
                this.prevCallRxBytes = 0;
                this.localAudioTarget = 0;
                this.remoteAudioTarget = 0;
                return;
            }

            // Real PCM levels are preferred, and this is a fallback when bridge/native
            // audio telemetry is unavailable but link stats are present.
            if (this.audioWs || this.useAndroidNativeTelephone) {
                this.prevCallTxBytes = Number(newCall.tx_bytes || 0);
                this.prevCallRxBytes = Number(newCall.rx_bytes || 0);
                return;
            }

            const tx = Number(newCall.tx_bytes || 0);
            const rx = Number(newCall.rx_bytes || 0);
            const prevTx = oldCall && oldCall.hash === newCall.hash ? this.prevCallTxBytes : tx;
            const prevRx = oldCall && oldCall.hash === newCall.hash ? this.prevCallRxBytes : rx;
            const txDelta = Math.max(0, tx - prevTx);
            const rxDelta = Math.max(0, rx - prevRx);

            // Convert byte deltas to subtle activity levels with soft cap.
            const txLevel = this.normalizeAudioLevel(Math.log10(1 + txDelta) / 2.8);
            const rxLevel = this.normalizeAudioLevel(Math.log10(1 + rxDelta) / 2.8);
            this.localAudioTarget = Math.max(this.localAudioTarget, txLevel);
            this.remoteAudioTarget = Math.max(this.remoteAudioTarget, rxLevel);
            this.localAudioLevel = Math.max(this.localAudioLevel, this.localAudioTarget);
            this.remoteAudioLevel = Math.max(this.remoteAudioLevel, this.remoteAudioTarget);

            this.prevCallTxBytes = tx;
            this.prevCallRxBytes = rx;
        },
        resizeAudioVisualizerCanvas(canvas) {
            if (!canvas) return false;
            const cssWidth = Math.max(160, Math.floor(canvas.clientWidth || 256));
            const cssHeight = Math.max(56, Math.floor(canvas.clientHeight || 72));
            const dpr = Math.max(1, Number(window.devicePixelRatio) || 1);
            const targetWidth = Math.floor(cssWidth * dpr);
            const targetHeight = Math.floor(cssHeight * dpr);
            if (canvas.width !== targetWidth || canvas.height !== targetHeight) {
                canvas.width = targetWidth;
                canvas.height = targetHeight;
            }
            return true;
        },
        startAudioVisualizer() {
            if (!this.visualizerEnabled || this.visualizerRafId) {
                return;
            }
            if (
                typeof window.requestAnimationFrame !== "function" ||
                typeof window.cancelAnimationFrame !== "function"
            ) {
                this.disableAudioVisualizer();
                return;
            }
            const canvas = this.$refs.callAudioVisualizer;
            if (!canvas || typeof canvas.getContext !== "function") {
                return;
            }
            if (!this.resizeAudioVisualizerCanvas(canvas)) {
                this.disableAudioVisualizer();
                return;
            }
            const ctx = canvas.getContext("2d");
            if (!ctx) {
                this.disableAudioVisualizer();
                return;
            }

            const loop = () => {
                const currentCanvas = this.$refs.callAudioVisualizer;
                if (!currentCanvas || typeof currentCanvas.getContext !== "function") {
                    this.stopAudioVisualizer();
                    return;
                }
                if (!this.resizeAudioVisualizerCanvas(currentCanvas)) {
                    this.disableAudioVisualizer();
                    return;
                }
                const currentCtx = currentCanvas.getContext("2d");
                if (!currentCtx) {
                    this.disableAudioVisualizer();
                    return;
                }

                const width = currentCanvas.width;
                const height = currentCanvas.height;
                const centerY = height / 2;
                this.visualizerPhase += 0.065;
                this.localAudioTarget *= 0.985;
                this.remoteAudioTarget *= 0.985;
                this.localAudioLevel = Math.max(this.localAudioLevel * 0.965, this.localAudioTarget);
                this.remoteAudioLevel = Math.max(this.remoteAudioLevel * 0.965, this.remoteAudioTarget);

                currentCtx.clearRect(0, 0, width, height);
                currentCtx.fillStyle = "rgba(10, 12, 18, 0.9)";
                currentCtx.fillRect(0, 0, width, height);

                currentCtx.strokeStyle = "rgba(156, 163, 175, 0.22)";
                currentCtx.lineWidth = 1;
                currentCtx.beginPath();
                currentCtx.moveTo(0, centerY);
                currentCtx.lineTo(width, centerY);
                currentCtx.stroke();

                const drawWave = (level, color, phaseOffset, direction) => {
                    const clampedLevel = this.normalizeAudioLevel(level);
                    if (clampedLevel < 0.003) {
                        return;
                    }
                    const amp = clampedLevel * (height * 0.4);
                    currentCtx.beginPath();
                    currentCtx.strokeStyle = color;
                    currentCtx.lineWidth = 2;
                    const step = 4;
                    for (let x = 0; x <= width; x += step) {
                        const t = (x / width) * Math.PI * 6 + this.visualizerPhase + phaseOffset;
                        const envelope = 0.5 + 0.5 * Math.sin((x / width) * Math.PI);
                        const y = centerY + direction * Math.sin(t) * amp * envelope;
                        if (x === 0) {
                            currentCtx.moveTo(x, y);
                        } else {
                            currentCtx.lineTo(x, y);
                        }
                    }
                    currentCtx.stroke();
                };

                drawWave(this.localAudioLevel, "rgba(34, 211, 238, 0.95)", 0, -1);
                drawWave(this.remoteAudioLevel, "rgba(167, 139, 250, 0.95)", Math.PI / 2, 1);

                this.visualizerRafId = window.requestAnimationFrame(loop);
            };

            this.visualizerRafId = window.requestAnimationFrame(loop);
        },
        stopAudioVisualizer() {
            if (this.visualizerRafId) {
                window.cancelAnimationFrame(this.visualizerRafId);
                this.visualizerRafId = null;
            }
            this.localAudioLevel = 0;
            this.remoteAudioLevel = 0;
            this.localAudioTarget = 0;
            this.remoteAudioTarget = 0;
        },
        isMeshChatXAndroid() {
            return detectMeshChatXAndroid();
        },
        getMediaDevicesApi() {
            const mediaDevices = navigator?.mediaDevices;
            if (!mediaDevices || typeof mediaDevices.getUserMedia !== "function") {
                return null;
            }
            return mediaDevices;
        },
        hasEnumerateDevicesApi(mediaDevices) {
            return Boolean(mediaDevices && typeof mediaDevices.enumerateDevices === "function");
        },
        getAudioContextConstructor() {
            return window.AudioContext || window.webkitAudioContext || null;
        },
        pickWebAudioMicConstraints(mediaDevices) {
            const processingHints = {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
            };
            const canEnumerate = this.hasEnumerateDevicesApi(mediaDevices);
            const validIds = canEnumerate
                ? new Set(
                      (this.audioInputDevices || [])
                          .filter((d) => d.kind === "audioinput" && d.deviceId)
                          .map((d) => d.deviceId)
                  )
                : new Set();
            const sid = this.selectedAudioInputId;
            // Bare audio unless a post-permission device id is selected.
            // Processing flags or deviceId.exact before the prompt yield
            // NotFoundError on Brave and Chromium with no permission dialog.
            if (!sid || sid === "__meshchat_default_in__") {
                return { audio: true };
            }
            const id = validIds.has(sid) ? sid : null;
            return id ? { audio: { ...processingHints, deviceId: { exact: id } } } : { audio: true };
        },
        async getUserMediaWithMicFallback(mediaDevices) {
            const constraints = this.pickWebAudioMicConstraints(mediaDevices);
            try {
                return await mediaDevices.getUserMedia(constraints);
            } catch (e) {
                const retryable =
                    e?.name === "NotFoundError" || e?.name === "OverconstrainedError" || e?.name === "NotReadableError";
                if (!retryable) {
                    throw e;
                }
                // Stale exact deviceId, Brave pre-permission device lists, or busy device.
                // Wide-open audio is what actually triggers the browser permission prompt.
                this.selectedAudioInputId = "__meshchat_default_in__";
                this.logWebAudioFailure("getUserMedia-fallback-wide", e);
                return await mediaDevices.getUserMedia({ audio: true });
            }
        },
        logWebAudioFailure(stage, error) {
            const appImage = Boolean(
                window.electron && typeof navigator?.userAgent === "string" && navigator.userAgent.includes("AppImage")
            );
            console.error(
                `[CallPage:web-audio] ${stage}`,
                {
                    isElectron: Boolean(window.electron),
                    isAppImage: appImage,
                    userAgent: navigator?.userAgent || "unknown",
                },
                error
            );
        },
        async disableWebAudioBridgeWithError(errorKey, error, stage = "unknown") {
            this.logWebAudioFailure(stage, error);
            ToastUtils.error(this.$t(errorKey), 5000, WEB_AUDIO_MIC_TOAST_KEY);
            // On Android / headless hosts the backend forces web audio. Permanently
            // clearing the config flag just creates a retry/toast loop.
            if (!this.isMeshChatXAndroid() && !this.webAudioBridgeRequired) {
                if (this.config) {
                    this.config.telephone_web_audio_enabled = false;
                }
                try {
                    await this.updateConfig({ telephone_web_audio_enabled: false });
                } catch (updateError) {
                    this.logWebAudioFailure("disable-config-update", updateError);
                }
            }
            this.stopWebAudio();
        },
        async ensureWebAudio(webAudioStatus) {
            if (webAudioStatus && typeof webAudioStatus.required === "boolean") {
                this.webAudioBridgeRequired = webAudioStatus.required;
            }
            if (!webAudioStatus?.enabled) {
                this.stopWebAudio();
                return;
            }
            // Do not start web audio during voicemail
            if (this.activeCall?.is_voicemail) {
                this.stopWebAudio();
                return;
            }
            if (this.activeCall && webAudioStatus.enabled) {
                this.audioFrameMs = webAudioStatus.frame_ms || 60;
                await this.startWebAudio();
            } else {
                this.stopWebAudio();
            }
        },
        async onToggleWebAudio(newVal) {
            if (!this.config) return;
            if (this.webAudioBridgeRequired && !newVal) {
                return;
            }
            const previousValue = this.config.telephone_web_audio_enabled;
            this.config.telephone_web_audio_enabled = newVal;
            try {
                if (newVal) {
                    const permitted = await this.requestAudioPermission();
                    if (!permitted) {
                        this.config.telephone_web_audio_enabled = false;
                        await this.updateConfig({ telephone_web_audio_enabled: false });
                        return;
                    }
                }
                await this.updateConfig({ telephone_web_audio_enabled: newVal });
                if (newVal) {
                    if (this.activeCall) {
                        await this.startWebAudio();
                    }
                } else {
                    this.stopWebAudio();
                }
            } catch {
                // revert on failure
                this.config.telephone_web_audio_enabled = previousValue;
            }
        },
        async restartWebAudio() {
            this.webAudioStartBlocked = false;
            this.stopWebAudio();
            await this.startWebAudio();
        },
        async startWebAudio() {
            if (!this.activeCall) {
                return;
            }
            if (this.isMeshChatXAndroid()) {
                this.stopWebAudio();
                if (
                    !window.MeshChatXAndroid ||
                    typeof window.MeshChatXAndroid.startTelephoneNativeAudio !== "function"
                ) {
                    await this.disableWebAudioBridgeWithError(
                        "call.web_audio_not_available",
                        new Error("Native audio bridge not linked"),
                        "start-android-missing"
                    );
                    return;
                }
                const telMic = window.MeshChatXAndroid.isTelephoneNativeAudioAvailable;
                const micOk =
                    typeof telMic === "function"
                        ? telMic()
                        : window.MeshChatXAndroid.isNativePcmAudioAvailable?.() === true;
                if (!micOk) {
                    await this.disableWebAudioBridgeWithError(
                        "call.microphone_permission_denied",
                        new Error("RECORD_AUDIO not granted"),
                        "start-android-perm"
                    );
                    return;
                }
                const ret = window.MeshChatXAndroid.startTelephoneNativeAudio();
                if (ret !== "ok") {
                    await this.disableWebAudioBridgeWithError(
                        "call.web_audio_not_available",
                        new Error(String(ret || "native start")),
                        "start-android"
                    );
                    return;
                }
                this._bindAndroidNativeTelephone();
                this.useAndroidNativeTelephone = true;
                return;
            }
            if (this.audioWs && this.audioWs.readyState === WebSocket.OPEN) {
                try {
                    this.audioWs.send(JSON.stringify({ type: "attach" }));
                } catch {
                    // ignore
                }
                if (
                    this.audioCtx &&
                    this.audioCtx.state === "suspended" &&
                    typeof this.audioCtx.resume === "function"
                ) {
                    try {
                        await this.audioCtx.resume();
                    } catch {
                        // ignore
                    }
                }
                return;
            }
            if (this.audioWs) {
                this.stopWebAudio();
            }
            if (this.webAudioStartInFlight || this.webAudioStartBlocked) {
                return;
            }
            this.webAudioStartInFlight = true;
            try {
                if (typeof window !== "undefined" && window.isSecureContext === false) {
                    this.webAudioStartBlocked = true;
                    await this.disableWebAudioBridgeWithError(
                        "call.microphone_insecure_context",
                        new Error("insecure context"),
                        "start-preflight-insecure"
                    );
                    return;
                }
                const mediaDevices = this.getMediaDevicesApi();
                if (!mediaDevices) {
                    this.webAudioStartBlocked = true;
                    await this.disableWebAudioBridgeWithError(
                        "call.web_audio_not_available",
                        new Error("navigator.mediaDevices is unavailable"),
                        "start-preflight-media-devices"
                    );
                    return;
                }
                // First capture must be unconstrained. enumerateDevices before
                // permission can lock onto Brave farbling ids and skip the prompt.
                this.selectedAudioInputId = "__meshchat_default_in__";
                const stream = await this.getUserMediaWithMicFallback(mediaDevices);
                this.audioStream = stream;
                this.webAudioMicReady = true;
                this.webAudioStartBlocked = false;
                await this.refreshAudioDevices();

                if (!this.audioCtx) {
                    const AudioContextCtor = this.getAudioContextConstructor();
                    if (!AudioContextCtor) {
                        throw new Error("AudioContext is unavailable");
                    }
                    try {
                        this.audioCtx = new AudioContextCtor({ sampleRate: 48000 });
                    } catch {
                        this.audioCtx = new AudioContextCtor();
                    }
                }

                if (this.audioCtx.state === "suspended" && typeof this.audioCtx.resume === "function") {
                    try {
                        await this.audioCtx.resume();
                    } catch {
                        // ignore
                    }
                }

                const source = this.audioCtx.createMediaStreamSource(stream);
                this.audioSourceNode = source;
                let captureInput = source;

                // Lightweight mic cleanup stage before PCM capture:
                // - High-pass removes low rumble/fan hum.
                // - Compressor smooths sudden peaks and lifts speech intelligibility.
                if (
                    typeof this.audioCtx.createBiquadFilter === "function" &&
                    typeof this.audioCtx.createDynamicsCompressor === "function"
                ) {
                    try {
                        const highpass = this.audioCtx.createBiquadFilter();
                        highpass.type = "highpass";
                        highpass.frequency.value = 120;
                        highpass.Q.value = 0.707;

                        const compressor = this.audioCtx.createDynamicsCompressor();
                        compressor.threshold.value = -45;
                        compressor.knee.value = 30;
                        compressor.ratio.value = 3;
                        compressor.attack.value = 0.003;
                        compressor.release.value = 0.25;

                        source.connect(highpass);
                        highpass.connect(compressor);
                        captureInput = compressor;
                        this.audioNoiseHighpass = highpass;
                        this.audioNoiseCompressor = compressor;
                    } catch (filterErr) {
                        this.logWebAudioFailure("telephone-noise-filter", filterErr);
                    }
                }
                const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
                const url = `${wsProtocol}//${window.location.host}/ws/telephone/audio`;

                const sendMicPcmToWs = (arrayBuffer) => {
                    if (!this.audioWs || this.audioWs.readyState !== WebSocket.OPEN) {
                        return;
                    }
                    if (arrayBuffer && arrayBuffer.byteLength > 0) {
                        this.audioWs.send(arrayBuffer);
                    }
                };

                const floatChannelToInt16PcmBuffer = (ch0) => {
                    const pcm = new Int16Array(ch0.length);
                    for (let i = 0; i < ch0.length; i += 1) {
                        const s = ch0[i];
                        pcm[i] = Math.max(-1, Math.min(1, s)) * 0x7fff;
                    }
                    return pcm.buffer;
                };

                let micTapNode = null;

                if (
                    globalThis.isSecureContext !== false &&
                    this.audioCtx.audioWorklet &&
                    typeof this.audioCtx.audioWorklet.addModule === "function"
                ) {
                    try {
                        await this.audioCtx.audioWorklet.addModule(telephonePcmCaptureWorkletUrl);
                        const processor = new AudioWorkletNode(this.audioCtx, "telephone-pcm-capture", {
                            numberOfInputs: 1,
                            numberOfOutputs: 1,
                            channelCount: 1,
                        });
                        processor.port.onmessage = (event) => {
                            const pcmBuffer = event.data;
                            sendMicPcmToWs(pcmBuffer);
                            const samples = this.extractInt16Samples(pcmBuffer);
                            if (samples && samples.length > 0) {
                                const level = this.computeSignalLevel(samples, 0x7fff);
                                this.localAudioTarget = Math.max(this.localAudioTarget, level);
                                this.localAudioLevel = Math.max(this.localAudioLevel, this.localAudioTarget);
                            }
                        };
                        captureInput.connect(processor);
                        this.audioWorkletNode = processor;
                        micTapNode = processor;
                    } catch (workletErr) {
                        this.logWebAudioFailure("telephone-worklet-add", workletErr);
                    }
                }

                if (!micTapNode) {
                    if (typeof this.audioCtx.createScriptProcessor !== "function") {
                        await this.disableWebAudioBridgeWithError(
                            "call.web_audio_not_available",
                            new Error("AudioWorklet and ScriptProcessor capture are unavailable"),
                            "start-preflight-audio-capture"
                        );
                        return;
                    }
                    try {
                        const scriptNode = this.audioCtx.createScriptProcessor(4096, 1, 1);
                        scriptNode.onaudioprocess = (e) => {
                            const ch0 = e.inputBuffer.getChannelData(0);
                            if (!ch0 || ch0.length === 0) {
                                return;
                            }
                            const level = this.computeSignalLevel(ch0, 1);
                            this.localAudioTarget = Math.max(this.localAudioTarget, level);
                            this.localAudioLevel = Math.max(this.localAudioLevel, this.localAudioTarget);
                            sendMicPcmToWs(floatChannelToInt16PcmBuffer(ch0));
                        };
                        captureInput.connect(scriptNode);
                        this.audioProcessor = scriptNode;
                        micTapNode = scriptNode;
                    } catch (scriptErr) {
                        await this.disableWebAudioBridgeWithError(
                            "call.web_audio_not_available",
                            scriptErr,
                            "start-preflight-script-processor"
                        );
                        return;
                    }
                }

                const silentGain = this.audioCtx.createGain();
                silentGain.gain.value = 0;
                this.audioSilentGain = silentGain;
                micTapNode.connect(silentGain);
                silentGain.connect(this.audioCtx.destination);

                const ws = new WebSocket(url);
                ws.binaryType = "arraybuffer";
                ws.onopen = () => {
                    ws.send(JSON.stringify({ type: "attach" }));
                };
                ws.onmessage = (event) => {
                    if (typeof event.data === "string") {
                        try {
                            const msg = JSON.parse(event.data);
                            if (msg.type === "error") {
                                const errMsg = typeof msg.message === "string" ? msg.message : "";
                                if (errMsg.includes("Web audio is disabled in config")) {
                                    if (!this.webAudioBridgeRequired && this.config) {
                                        this.config.telephone_web_audio_enabled = false;
                                    }
                                    this.stopWebAudio();
                                    return;
                                }
                                this.logWebAudioFailure("ws-server-error", new Error(msg.message || "unknown"));
                                if (
                                    this.activeCall &&
                                    typeof msg.message === "string" &&
                                    msg.message.includes("No active call")
                                ) {
                                    window.setTimeout(() => {
                                        try {
                                            if (this.audioWs && this.audioWs.readyState === WebSocket.OPEN) {
                                                this.audioWs.send(JSON.stringify({ type: "attach" }));
                                            }
                                        } catch {
                                            // ignore
                                        }
                                    }, 150);
                                }
                            }
                        } catch {
                            // ignore non-json
                        }
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
                this.webAudioStartBlocked = true;
                const permissionState = await queryMicrophonePermissionState();
                const errorKey = classifyGetUserMediaError(err, {
                    permissionState,
                    isBrave: isBraveBrowser(),
                });
                await this.disableWebAudioBridgeWithError(errorKey, err, "start-catch");
            } finally {
                this.webAudioStartInFlight = false;
            }
        },
        async onRefreshAudioDevices() {
            const permitted = await this.requestAudioPermission();
            if (!permitted || !this.activeCall || !this.webAudioBridgeEnabled) {
                return;
            }
            await this.restartWebAudio();
        },
        async requestAudioPermission() {
            try {
                if (this.isMeshChatXAndroid()) {
                    const tel = window.MeshChatXAndroid?.isTelephoneNativeAudioAvailable;
                    if (typeof tel === "function" && tel()) {
                        this.webAudioMicReady = true;
                        this.webAudioStartBlocked = false;
                        return true;
                    }
                    if (window.MeshChatXAndroid?.isNativePcmAudioAvailable?.()) {
                        this.webAudioMicReady = true;
                        this.webAudioStartBlocked = false;
                        return true;
                    }
                }
                if (typeof window !== "undefined" && window.isSecureContext === false) {
                    ToastUtils.error(this.$t("call.microphone_insecure_context"), 5000, WEB_AUDIO_MIC_TOAST_KEY);
                    return false;
                }
                const mediaDevices = this.getMediaDevicesApi();
                if (!mediaDevices) {
                    throw new Error("navigator.mediaDevices is unavailable");
                }
                // Wide-open { audio: true } is what opens the permission dialog.
                // Do not follow a failed probe with processing constraints.
                this.selectedAudioInputId = "__meshchat_default_in__";
                await promptMicrophoneAccess(mediaDevices);
                this.webAudioMicReady = true;
                this.webAudioStartBlocked = false;
                await this.refreshAudioDevices();
                return true;
            } catch (e) {
                this.logWebAudioFailure("request-permission", e);
                this.webAudioStartBlocked = true;
                const errorKey = await this.resolveMissingMicErrorKey(e);
                ToastUtils.error(this.$t(errorKey), 5000, WEB_AUDIO_MIC_TOAST_KEY);
                return false;
            }
        },
        async resolveMissingMicErrorKey(error) {
            const permissionState = await queryMicrophonePermissionState();
            if (error) {
                return classifyGetUserMediaError(error, {
                    permissionState,
                    isBrave: isBraveBrowser(),
                });
            }
            if (permissionState === "denied") {
                return "call.microphone_permission_denied";
            }
            if (permissionState === "prompt") {
                return isBraveBrowser() ? "call.microphone_prompt_blocked" : "call.microphone_permission_needed";
            }
            return isBraveBrowser() ? "call.microphone_prompt_blocked" : "call.no_audio_input_found";
        },
        async refreshAudioDevices() {
            const defaultIn = {
                deviceId: "__meshchat_default_in__",
                kind: "audioinput",
                label: "Default",
                groupId: "",
            };
            const defaultOut = {
                deviceId: "__meshchat_default_out__",
                kind: "audiooutput",
                label: "Default",
                groupId: "",
            };
            try {
                const mediaDevices = this.getMediaDevicesApi();
                if (!mediaDevices) {
                    this.audioInputDevices = [defaultIn];
                    this.audioOutputDevices = [defaultOut];
                    return;
                }
                if (!this.hasEnumerateDevicesApi(mediaDevices)) {
                    this.audioInputDevices = [defaultIn];
                    this.audioOutputDevices = [defaultOut];
                    return;
                }
                const devices = await mediaDevices.enumerateDevices();
                let inputs = devices.filter((d) => d.kind === "audioinput");
                let outputs = devices.filter((d) => d.kind === "audiooutput");
                // Pre-permission lists often have blank deviceId and blank labels.
                // Keep the Default placeholder so we do not lock onto phantom IDs.
                const inputsUsable = inputs.some((d) => d.deviceId && String(d.deviceId).trim() !== "" && d.label);
                if (!inputsUsable) {
                    inputs = [defaultIn];
                }
                const outputsUsable = outputs.some((d) => d.deviceId && String(d.deviceId).trim() !== "" && d.label);
                if (!outputsUsable) {
                    outputs = [defaultOut];
                }
                this.audioInputDevices = inputs;
                this.audioOutputDevices = outputs;
                const selectedInStillValid = this.audioInputDevices.some(
                    (d) => d.deviceId === this.selectedAudioInputId
                );
                if (!selectedInStillValid) {
                    this.selectedAudioInputId = this.audioInputDevices[0]?.deviceId || defaultIn.deviceId;
                }
                const selectedOutStillValid = this.audioOutputDevices.some(
                    (d) => d.deviceId === this.selectedAudioOutputId
                );
                if (!selectedOutStillValid) {
                    this.selectedAudioOutputId = this.audioOutputDevices[0]?.deviceId || defaultOut.deviceId;
                }
            } catch (e) {
                this.logWebAudioFailure("refresh-devices", e);
                this.audioInputDevices = [defaultIn];
                this.audioOutputDevices = [defaultOut];
            }
        },
        playRemotePcm(arrayBuffer) {
            if (!this.audioCtx || !arrayBuffer) {
                return;
            }
            const pcm = this.extractInt16Samples(arrayBuffer);
            if (!pcm) return;
            if (pcm.length === 0) return;
            const remoteLevel = this.computeSignalLevel(pcm, 0x7fff);
            this.remoteAudioTarget = Math.max(this.remoteAudioTarget, remoteLevel);
            this.remoteAudioLevel = Math.max(this.remoteAudioLevel, this.remoteAudioTarget);
            const floatBuf = new Float32Array(pcm.length);
            for (let i = 0; i < pcm.length; i += 1) {
                floatBuf[i] = pcm[i] / 0x7fff;
            }
            const audioBuffer = this.audioCtx.createBuffer(1, floatBuf.length, 48000);
            audioBuffer.copyToChannel(floatBuf, 0);
            const bufferSource = this.audioCtx.createBufferSource();
            bufferSource.buffer = audioBuffer;
            const sinkId = this.selectedAudioOutputId;
            const useSetSinkId =
                sinkId && sinkId !== "__meshchat_default_out__" && "setSinkId" in HTMLMediaElement.prototype;
            if (useSetSinkId) {
                if (!this.remoteAudioEl) {
                    this.remoteAudioEl = new Audio();
                    this.remoteAudioEl.autoplay = true;
                }
                const dest = this.audioCtx.createMediaStreamDestination();
                bufferSource.connect(dest);
                bufferSource.start();
                this.remoteAudioEl.srcObject = dest.stream;
                this.remoteAudioEl.setSinkId(sinkId).catch((err) => console.warn("setSinkId failed", err));
            } else {
                bufferSource.connect(this.audioCtx.destination);
                bufferSource.start();
            }
        },
        _bindAndroidNativeTelephone() {
            this._unbindAndroidNativeTelephone();
            this.androidNativeTelephoneListener = (ev) => {
                const d = ev && ev.detail;
                if (d && d.kind === "levels") {
                    this.localAudioTarget = Math.max(this.localAudioTarget, this.normalizeAudioLevel(d.tx_level));
                    this.remoteAudioTarget = Math.max(this.remoteAudioTarget, this.normalizeAudioLevel(d.rx_level));
                    this.localAudioLevel = Math.max(this.localAudioLevel, this.localAudioTarget);
                    this.remoteAudioLevel = Math.max(this.remoteAudioLevel, this.remoteAudioTarget);
                    return;
                }
                if (d && d.kind === "error" && d.detail) {
                    this.logWebAudioFailure("android-native", new Error(String(d.sub || d.detail || "error")));
                }
            };
            window.addEventListener("meshchatx-native-telephone-audio", this.androidNativeTelephoneListener);
        },
        _unbindAndroidNativeTelephone() {
            if (this.androidNativeTelephoneListener) {
                window.removeEventListener("meshchatx-native-telephone-audio", this.androidNativeTelephoneListener);
                this.androidNativeTelephoneListener = null;
            }
        },
        stopWebAudio() {
            if (this.useAndroidNativeTelephone) {
                this._unbindAndroidNativeTelephone();
                this.useAndroidNativeTelephone = false;
                try {
                    if (window.MeshChatXAndroid?.stopTelephoneNativeAudio) {
                        window.MeshChatXAndroid.stopTelephoneNativeAudio();
                    }
                } catch (e) {
                    this.logWebAudioFailure("android-native-stop", e);
                }
            }
            const ws = this.audioWs;
            this.audioWs = null;
            if (ws) {
                try {
                    ws.onopen = null;
                    ws.onmessage = null;
                    ws.onerror = null;
                    ws.onclose = null;
                    ws.close();
                } catch {
                    // ignore
                }
            }
            if (this.audioSourceNode) {
                try {
                    this.audioSourceNode.disconnect();
                } catch {
                    // ignore
                }
                this.audioSourceNode = null;
            }
            if (this.audioNoiseHighpass) {
                try {
                    this.audioNoiseHighpass.disconnect();
                } catch {
                    // ignore
                }
                this.audioNoiseHighpass = null;
            }
            if (this.audioNoiseCompressor) {
                try {
                    this.audioNoiseCompressor.disconnect();
                } catch {
                    // ignore
                }
                this.audioNoiseCompressor = null;
            }
            if (this.audioProcessor) {
                try {
                    this.audioProcessor.disconnect();
                } catch {
                    // ignore
                }
                this.audioProcessor = null;
            }
            if (this.audioWorkletNode) {
                try {
                    this.audioWorkletNode.port.onmessage = null;
                } catch {
                    // ignore
                }
                try {
                    this.audioWorkletNode.disconnect();
                } catch {
                    // ignore
                }
                this.audioWorkletNode = null;
            }
            if (this.audioStream) {
                this.audioStream.getTracks().forEach((t) => t.stop());
                this.audioStream = null;
            }
            if (this.remoteAudioEl) {
                this.remoteAudioEl.srcObject = null;
                this.remoteAudioEl = null;
            }
            if (this.audioSilentGain) {
                try {
                    this.audioSilentGain.disconnect();
                } catch {
                    // ignore
                }
                this.audioSilentGain = null;
            }
            if (
                this.audioCtx &&
                this.audioCtx.state !== "closed" &&
                typeof this.audioCtx.close === "function"
            ) {
                this.audioCtx.close().catch(() => {
                    // ignore
                });
            }
            this.audioCtx = null;
        },
        async getConfig() {
            try {
                const response = await window.api.get("/api/v1/config");
                this.config = response.data.config;
            } catch (e) {
                console.log(e);
            }
        },
        async updateConfig(config) {
            try {
                const response = await window.api.patch("/api/v1/config", config);
                if (response.data?.config) {
                    this.config = response.data.config;
                }
                ToastUtils.success(this.$t("call.settings_saved"));
            } catch {
                ToastUtils.error(this.$t("call.failed_to_save_settings"));
            }
        },
        async getAudioProfiles() {
            try {
                const response = await window.api.get("/api/v1/telephone/audio-profiles");
                const profiles = Array.isArray(response.data.audio_profiles) ? response.data.audio_profiles : [];
                this.audioProfiles = profiles.filter((p) => p && p.available !== false);
                this.selectedAudioProfileId = response.data.default_audio_profile_id;
                if (response.data.codec2_available === false) {
                    const hadCodec2 = profiles.some((p) => p && p.unavailable_reason === "codec2");
                    if (hadCodec2) {
                        ToastUtils.warning(this.$t("call.codec2_unavailable"));
                    }
                }
            } catch (e) {
                console.log(e);
            }
        },
        async getCallModes() {
            try {
                const response = await window.api.get("/api/v1/telephone/call-modes");
                const modes = Array.isArray(response.data.call_modes) ? response.data.call_modes : [];
                this.callModes = modes;
                if (response.data.default_call_mode_id != null) {
                    this.selectedCallModeId = response.data.default_call_mode_id;
                }
            } catch (e) {
                console.log(e);
            }
        },
        async getStatus() {
            try {
                const response = await window.api.get("/api/v1/telephone/status");
                const oldCall = this.activeCall;
                const newCall = response.data.active_call;

                // Sync local mute / PTT / mode state from backend
                if (newCall) {
                    if (!oldCall || newCall.hash !== oldCall.hash) {
                        this.localMicMuted = Boolean(newCall.is_mic_muted);
                        this.localSpeakerMuted = Boolean(newCall.is_speaker_muted);
                        this.localPttActive = Boolean(newCall.is_ptt_active);
                    } else if (!this.isMicMuting) {
                        this.localMicMuted = Boolean(
                            newCall.is_mic_muted ?? response.data.is_mic_muted ?? this.localMicMuted
                        );
                        this.localSpeakerMuted = Boolean(
                            newCall.is_speaker_muted ?? response.data.is_speaker_muted ?? this.localSpeakerMuted
                        );
                        if (!this.pttKeyHeld) {
                            this.localPttActive = Boolean(newCall.is_ptt_active);
                        }
                    }
                    if (newCall.call_mode_id != null) {
                        this.selectedCallModeId = newCall.call_mode_id;
                    }
                } else {
                    this.localPttActive = false;
                    this.pttKeyHeld = false;
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

                this.hydrateContactVisuals();

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
                remote_identity_hash: entry.remote_identity_hash || "",
                lxmf_address: entry.remote_destination_hash || "",
                lxst_address: entry.remote_telephony_hash || "",
                preferred_ringtone_id: null,
            };
            this.isContactModalOpen = true;
        },
        openMessageFromHistory(entry) {
            const hash = entry.remote_destination_hash || entry.remote_identity_hash;
            if (!hash) return;
            this.$router.push({ name: "messages", params: { destinationHash: hash } });
        },
        async getHistory(loadMore = false) {
            try {
                if (!loadMore) {
                    this.callHistoryOffset = 0;
                }

                const response = await window.api.get(
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
                this.hydrateContactVisuals();
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

                const response = await window.api.get("/api/v1/announces", {
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
                await window.api.patch("/api/v1/config", {
                    do_not_disturb_enabled: value,
                });
                if (this.config) {
                    this.config.do_not_disturb_enabled = value;
                }
                ToastUtils.success(value ? "Do Not Disturb enabled" : "Do Not Disturb disabled");
            } catch {
                ToastUtils.error(this.$t("call.failed_to_update_dnd"));
            }
        },
        async toggleAllowCallsFromContactsOnly(value) {
            try {
                await window.api.patch("/api/v1/config", {
                    telephone_allow_calls_from_contacts_only: value,
                });
                if (this.config) {
                    this.config.telephone_allow_calls_from_contacts_only = value;
                }
                ToastUtils.success(value ? "Calls limited to contacts" : "Calls allowed from everyone");
            } catch {
                ToastUtils.error(this.$t("call.failed_to_update_call_settings"));
            }
        },
        async toggleTelephoneAnnounceEnabled(value) {
            try {
                await window.api.patch("/api/v1/config", {
                    telephone_announce_enabled: value,
                });
                if (this.config) {
                    this.config.telephone_announce_enabled = value;
                }
                ToastUtils.success(value ? "Telephone announces enabled" : "Telephone announces disabled");
            } catch {
                ToastUtils.error(this.$t("call.failed_to_update_call_settings"));
            }
        },
        async toggleCallRecording(value) {
            try {
                await window.api.patch("/api/v1/config", {
                    call_recording_enabled: value,
                });
                if (this.config) {
                    this.config.call_recording_enabled = value;
                }
                ToastUtils.success(value ? this.$t("call.recording_enabled") : this.$t("call.recording_disabled"));
            } catch {
                ToastUtils.error(this.$t("call.failed_to_update_recording_status"));
            }
        },
        async clearHistory() {
            if (!(await DialogUtils.confirm(this.$t("common.delete_confirm")))) return;
            try {
                await window.api.delete("/api/v1/telephone/history");
                this.callHistory = [];
                await this.markMissedCallsViewed();
                ToastUtils.success(this.$t("call.call_history_cleared"));
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("call.failed_to_clear_call_history"));
            }
        },
        async markMissedCallsViewed() {
            try {
                await window.api.post("/api/v1/telephone/missed-calls/mark-viewed");
                GlobalState.missedCallsCount = 0;
            } catch (e) {
                console.error(e);
            }
        },
        async blockIdentity(hash) {
            if (!(await DialogUtils.confirm(this.$t("call.banish_identity_confirm")))) return;
            try {
                await window.api.post("/api/v1/blocked-destinations", {
                    destination_hash: hash,
                });
                ToastUtils.success(this.$t("call.identity_banished"));
                this.getHistory();
            } catch {
                ToastUtils.error(this.$t("call.failed_to_banish_identity"));
            }
        },
        async getVoicemailStatus() {
            try {
                const response = await window.api.get("/api/v1/telephone/voicemail/status");
                this.voicemailStatus = response.data;
            } catch (e) {
                console.log(e);
            }
        },
        async getRingtoneStatus() {
            try {
                const response = await window.api.get("/api/v1/telephone/ringtones/status");
                this.ringtoneStatus = response.data;
            } catch (e) {
                console.log(e);
            }
        },
        async getRingtones() {
            try {
                const response = await window.api.get("/api/v1/telephone/ringtones");
                this.ringtones = response.data;
            } catch (e) {
                console.error("Failed to get ringtones:", e);
            }
        },
        async deleteRingtone(ringtone) {
            if (!(await DialogUtils.confirm(this.$t("common.delete_confirm")))) return;
            try {
                await window.api.delete(`/api/v1/telephone/ringtones/${ringtone.id}`);
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
                await window.api.patch(`/api/v1/telephone/ringtones/${ringtone.id}`, {
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
                await window.api.patch(`/api/v1/telephone/ringtones/${this.editingRingtoneId}`, {
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
                await window.api.post("/api/v1/telephone/ringtones/upload", formData, {
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
        onPhonebookCall(destinationHash) {
            this.destinationHash = destinationHash;
            this.activeTab = "phone";
            this.$nextTick(() => this.call(destinationHash));
        },
        onRingtoneSaved() {
            this.getRingtones();
            this.getRingtoneStatus();
        },
        async getVoicemails() {
            try {
                const response = await window.api.get("/api/v1/telephone/voicemails", {
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
        onVoicemailPatchConfig(patch) {
            if (!this.config || !patch) return;
            Object.assign(this.config, patch);
        },
        onVoicemailUpdateConfig(patch) {
            if (!this.config || !patch) return;
            Object.assign(this.config, patch);
            this.updateConfig(patch);
        },
        onVoicemailSaveAndGenerate() {
            if (!this.config) return;
            this.updateConfig({ voicemail_greeting: this.config.voicemail_greeting });
            this.generateGreeting();
        },
        getContactByHash(hash) {
            if (!hash) return null;
            return this.contacts.find((c) => c.remote_identity_hash === hash);
        },
        async getContacts() {
            try {
                const response = await window.api.get("/api/v1/telephone/contacts", {
                    params: { search: this.contactsSearch },
                });
                this.contacts = response.data.contacts || (Array.isArray(response.data) ? response.data : []);
                this.hydrateContactVisuals();
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
        hydrateContactVisuals() {
            const map = {};
            this.contacts.forEach((c) => {
                if (!c) return;
                const image = c.custom_image;
                const keys = [c.remote_identity_hash, c.lxmf_address, c.lxst_address].filter(Boolean);
                keys.forEach((k) => {
                    map[k] = image;
                });
            });

            const applyImage = (target) => {
                if (!target) return;
                const key =
                    target.remote_identity_hash || target.remote_destination_hash || target.remote_telephony_hash;
                if (key && map[key]) {
                    target.custom_image = map[key];
                }
            };

            applyImage(this.activeCall);
            applyImage(this.lastCall);

            if (Array.isArray(this.callHistory) && this.callHistory.length > 0) {
                this.callHistory = this.callHistory.map((entry) => {
                    const key =
                        entry.remote_identity_hash || entry.remote_destination_hash || entry.remote_telephony_hash;
                    if (key && map[key]) {
                        return { ...entry, contact_image: map[key] };
                    }
                    return entry;
                });
            }
        },
        openAddContactModal() {
            this.editingContact = null;
            this.contactForm = {
                name: "",
                remote_identity_hash: "",
                lxmf_address: "",
                lxst_address: "",
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
                lxmf_address: contact.lxmf_address || "",
                lxst_address: contact.lxst_address || "",
                preferred_ringtone_id: contact.preferred_ringtone_id,
                custom_image: contact.custom_image,
            };
            this.isContactModalOpen = true;
        },
        async saveContact(contact) {
            if (!contact.name || !contact.remote_identity_hash) {
                ToastUtils.error(this.$t("call.name_and_hash_required"));
                return;
            }
            try {
                if (contact.id) {
                    // if editing and image was cleared, let backend know
                    if (this.editingContact && this.editingContact.custom_image && !contact.custom_image) {
                        contact.clear_image = true;
                    }
                    await window.api.patch(`/api/v1/telephone/contacts/${contact.id}`, contact);
                    ToastUtils.success(this.$t("call.contact_updated"));
                } else {
                    await window.api.post("/api/v1/telephone/contacts", contact);
                    ToastUtils.success(this.$t("call.contact_added"));
                }
                this.isContactModalOpen = false;
                this.getContacts();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("call.failed_to_save_contact"));
            }
        },
        async deleteContact(contactId) {
            if (!(await DialogUtils.confirm(this.$t("call.delete_contact_confirm")))) return;
            try {
                await window.api.delete(`/api/v1/telephone/contacts/${contactId}`);
                ToastUtils.success(this.$t("call.contact_deleted"));
                this.getContacts();
            } catch {
                ToastUtils.error(this.$t("call.failed_to_delete_contact"));
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
                ToastUtils.success(this.$t("call.hash_copied"));
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("call.failed_to_copy_hash"));
            }
        },
        async generateGreeting() {
            this.isGeneratingGreeting = true;
            try {
                await window.api.post("/api/v1/telephone/voicemail/generate-greeting");
                ToastUtils.success(this.$t("call.greeting_generated_successfully"));
                await this.getVoicemailStatus();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("call.failed_to_generate_greeting"));
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
                await window.api.post("/api/v1/telephone/voicemail/greeting/upload", formData, {
                    headers: {
                        "Content-Type": "multipart/form-data",
                    },
                });
                ToastUtils.success(this.$t("call.greeting_uploaded_successfully"));
                await this.getVoicemailStatus();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("call.failed_to_upload_greeting"));
            } finally {
                this.isUploadingGreeting = false;
                event.target.value = "";
            }
        },
        async deleteGreeting() {
            if (!(await DialogUtils.confirm(this.$t("call.delete_greeting_confirm")))) return;

            try {
                await window.api.delete("/api/v1/telephone/voicemail/greeting");
                ToastUtils.success(this.$t("call.greeting_deleted"));
                await this.getVoicemailStatus();
            } catch {
                ToastUtils.error(this.$t("call.failed_to_delete_greeting"));
            }
        },
        async startRecordingGreetingMic() {
            try {
                await window.api.post("/api/v1/telephone/voicemail/greeting/record/start");
                await this.getVoicemailStatus();
            } catch {
                ToastUtils.error(this.$t("call.failed_to_start_recording_greeting"));
            }
        },
        async stopRecordingGreetingMic() {
            try {
                await window.api.post("/api/v1/telephone/voicemail/greeting/record/stop");
                await this.getVoicemailStatus();
                ToastUtils.success(this.$t("call.greeting_recorded_from_mic"));
            } catch {
                ToastUtils.error(this.$t("call.failed_to_stop_recording_greeting"));
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

            this.markVoicemailAsRead(voicemail);
        },
        async markVoicemailAsRead(voicemail) {
            if (!voicemail.is_read) {
                try {
                    await window.api.post(`/api/v1/telephone/voicemails/${voicemail.id}/read`);
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
                await window.api.delete(`/api/v1/telephone/voicemails/${voicemailId}`);
                this.getVoicemails();
                ToastUtils.success(this.$t("call.voicemail_deleted"));
            } catch {
                ToastUtils.error(this.$t("call.failed_to_delete_voicemail"));
            }
        },
        async getRecordings() {
            try {
                const response = await window.api.get("/api/v1/telephone/recordings", {
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
                ToastUtils.error(this.$t("call.failed_to_load_recording"));
                this.playingRecordingId = null;
                this.playingSide = null;
            }
        },
        async deleteRecording(recordingId) {
            if (!(await DialogUtils.confirm(this.$t("call.delete_recording_confirm")))) return;
            try {
                await window.api.delete(`/api/v1/telephone/recordings/${recordingId}`);
                this.getRecordings();
                ToastUtils.success(this.$t("call.recording_deleted"));
            } catch {
                ToastUtils.error(this.$t("call.failed_to_delete_recording"));
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
                ToastUtils.error(this.$t("call.enter_identity_hash_to_call_error"));
                return;
            }

            let hashToCall = identityHash.trim();
            // Accept lxmf:// URIs or pasted text, and RNS truncated hashes are 32 hex chars
            const hexMatch = hashToCall.match(/[0-9a-fA-F]{32,64}/);
            if (hexMatch) {
                hashToCall = hexMatch[0].slice(0, 32);
            }
            hashToCall = hashToCall.toLowerCase();

            // Try to resolve name from contacts
            const contact = this.contacts.find((c) => c.name.toLowerCase() === hashToCall.toLowerCase());
            if (contact) {
                hashToCall =
                    contact.remote_identity_hash ||
                    contact.remote_telephony_hash ||
                    contact.lxst_address ||
                    contact.lxmf_address;
            }

            // Provide immediate feedback
            this.destinationHash = hashToCall;
            const targetContact = this.contacts.find(
                (c) =>
                    c.remote_identity_hash === hashToCall ||
                    c.lxmf_address === hashToCall ||
                    c.lxst_address === hashToCall ||
                    c.remote_telephony_hash === hashToCall
            );
            this.initiationTargetHash = hashToCall;
            this.initiationTargetName = targetContact ? targetContact.name : null;
            this.activeTab = "phone";
            this.initiationStatus = "Initiating...";
            this.isCallEnded = false;
            this.wasDeclined = false;

            try {
                if (this.webAudioBridgeEnabled) {
                    await this.requestAudioPermission();
                }
                await window.api.post(`/api/v1/telephone/call/${hashToCall}`);
            } catch (e) {
                this.initiationStatus = null;
                ToastUtils.error(e.response?.data?.message || this.$t("call.failed_to_initiate_call"));
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
                if (this.webAudioBridgeEnabled) {
                    await this.requestAudioPermission();
                }
                await window.api.post("/api/v1/telephone/answer");
            } catch {
                ToastUtils.error(this.$t("call.failed_to_answer_call"));
            }
        },
        async hangupCall() {
            try {
                if (this.activeCall && this.activeCall.is_incoming && this.activeCall.status === 4) {
                    this.wasDeclined = true;
                }
                await window.api.post("/api/v1/telephone/hangup");
            } catch {
                ToastUtils.error(this.$t("call.failed_to_hangup_call"));
            }
        },
        async sendToVoicemail() {
            try {
                await window.api.post("/api/v1/telephone/send-to-voicemail");
                ToastUtils.success(this.$t("call.call_sent_to_voicemail"));
            } catch {
                ToastUtils.error(this.$t("call.failed_to_send_to_voicemail"));
            }
        },
        async switchAudioProfile(audioProfileId) {
            try {
                const response = await window.api.post(`/api/v1/telephone/switch-audio-profile/${audioProfileId}`);
                const resolved = response.data?.profile_id;
                if (resolved != null) {
                    this.selectedAudioProfileId = resolved;
                }
                if (response.data?.remapped) {
                    ToastUtils.warning(this.$t("call.codec2_profile_remapped"));
                }
            } catch {
                ToastUtils.error(this.$t("call.failed_to_switch_audio_profile"));
            }
        },
        async switchCallMode(modeId) {
            try {
                const response = await window.api.post(`/api/v1/telephone/switch-call-mode/${modeId}`);
                const resolved = response.data?.mode_id;
                if (resolved != null) {
                    this.selectedCallModeId = resolved;
                }
                this.localPttActive = Boolean(response.data?.is_ptt_active);
                if (this.activeCall) {
                    this.activeCall.call_mode_id = resolved;
                    this.activeCall.is_half_duplex = Boolean(response.data?.is_half_duplex);
                    this.activeCall.is_ptt_active = this.localPttActive;
                }
                if (this.config) {
                    this.config.telephone_call_mode_id = resolved;
                }
            } catch {
                ToastUtils.error(this.$t("call.failed_to_switch_call_mode"));
            }
        },
        isEditableEventTarget(target) {
            if (!target || !(target instanceof Element)) return false;
            const tag = (target.tagName || "").toLowerCase();
            if (tag === "input" || tag === "textarea" || tag === "select") return true;
            return Boolean(target.isContentEditable);
        },
        onPttKeyDown(event) {
            if (event.code !== "Space" && event.key !== " ") return;
            if (event.repeat) return;
            if (this.isEditableEventTarget(event.target)) return;
            if (!this.isHalfDuplexCall) return;
            event.preventDefault();
            this.pttKeyHeld = true;
            this.setPttActive(true);
        },
        onPttKeyUp(event) {
            if (event.code !== "Space" && event.key !== " ") return;
            if (!this.pttKeyHeld && !this.localPttActive) return;
            event.preventDefault();
            this.pttKeyHeld = false;
            this.setPttActive(false);
        },
        onPttWindowBlur() {
            this.pttKeyHeld = false;
            if (this.localPttActive) {
                this.setPttActive(false);
            }
        },
        async setPttActive(active) {
            if (!this.isHalfDuplexCall && active) {
                return;
            }
            const wantActive = Boolean(active);
            if (this.localPttActive === wantActive) {
                return;
            }
            this.localPttActive = wantActive;
            if (this.activeCall) {
                this.activeCall.is_ptt_active = wantActive;
            }
            try {
                await window.api.post("/api/v1/telephone/ptt", { active: wantActive });
            } catch {
                this.localPttActive = !wantActive;
                if (this.activeCall) {
                    this.activeCall.is_ptt_active = !wantActive;
                }
                if (wantActive) {
                    ToastUtils.error(this.$t("call.failed_to_set_ptt"));
                }
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
                await window.api.post(endpoint);
                setTimeout(() => {
                    this.isMicMuting = false;
                }, 500);
            } catch {
                // Revert on error
                this.localMicMuted = !this.localMicMuted;
                ToastUtils.error(this.$t("call.failed_to_toggle_microphone"));
                this.isMicMuting = false;
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
                await window.api.post(endpoint);
                setTimeout(() => {
                    this.isSpeakerMuting = false;
                }, 500);
            } catch {
                // Revert on error
                this.localSpeakerMuted = !this.localSpeakerMuted;
                ToastUtils.error(this.$t("call.failed_to_toggle_speaker"));
                this.isSpeakerMuting = false;
            }
        },
    },
};
</script>
