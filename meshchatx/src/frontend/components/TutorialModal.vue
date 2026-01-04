<template>
    <v-dialog
        v-if="!isPage"
        v-model="visible"
        :fullscreen="isMobile"
        max-width="800"
        transition="dialog-bottom-transition"
        class="tutorial-dialog"
        persistent
        @update:model-value="onVisibleUpdate"
    >
        <v-card class="flex flex-col h-full bg-white dark:bg-zinc-950 border-0 overflow-hidden relative">
            <!-- Settings Controls -->
            <div class="absolute top-4 left-4 z-50 flex items-center gap-1">
                <LanguageSelector @language-change="onLanguageChange" />
                <button
                    type="button"
                    class="rounded-full p-1.5 sm:p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-zinc-800 transition-colors"
                    :title="config?.theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
                    @click="toggleTheme"
                >
                    <MaterialDesignIcon
                        :icon-name="config?.theme === 'dark' ? 'brightness-6' : 'brightness-4'"
                        class="w-5 h-5 sm:w-6 sm:h-6"
                    />
                </button>
            </div>

            <!-- Progress Bar -->
            <div class="w-full h-1.5 bg-gray-100 dark:bg-zinc-900 overflow-hidden flex">
                <div
                    v-for="step in totalSteps"
                    :key="step"
                    class="h-full transition-all duration-500 ease-out"
                    :class="[
                        currentStep >= step ? 'bg-blue-500' : 'bg-transparent',
                        currentStep === step ? 'flex-[2]' : 'flex-1',
                    ]"
                    :style="{ borderRight: step < totalSteps ? '1px solid rgba(0,0,0,0.05)' : 'none' }"
                ></div>
            </div>

            <!-- Content Area -->
            <v-card-text class="flex-1 overflow-y-auto px-6 md:px-12 py-10 relative">
                <transition name="fade-slide" mode="out-in">
                    <!-- Step 1: Welcome -->
                    <div v-if="currentStep === 1" key="step1" class="flex flex-col items-center text-center space-y-6">
                        <div class="relative">
                            <div class="w-24 h-24 bg-blue-500/10 rounded-3xl rotate-12 absolute -inset-2"></div>
                            <img :src="logoUrl" class="w-24 h-24 relative z-10 p-2" />
                        </div>
                        <div class="space-y-2">
                            <h1 class="text-4xl font-black tracking-tight text-gray-900 dark:text-white">
                                {{ $t("tutorial.welcome") }} <span class="text-blue-500">MeshChatX</span>
                            </h1>
                            <p class="text-lg text-gray-600 dark:text-zinc-400 max-w-md mx-auto">
                                {{ $t("tutorial.welcome_desc") }}
                            </p>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 w-full mt-8">
                            <div
                                class="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-all hover:scale-[1.03] hover:shadow-xl hover:z-10"
                            >
                                <v-icon icon="mdi-shield-lock" color="blue" size="32"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">
                                        {{ $t("tutorial.security") }}
                                    </div>
                                    <div class="text-sm text-gray-900 dark:text-white">
                                        {{ $t("tutorial.security_desc") }}
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-all hover:scale-[1.03] hover:shadow-xl hover:z-10"
                            >
                                <v-icon icon="mdi-map-marker-path" color="purple" size="32"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">{{ $t("tutorial.maps") }}</div>
                                    <div class="text-sm text-gray-900 dark:text-white">
                                        {{ $t("tutorial.maps_desc") }}
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-all hover:scale-[1.03] hover:shadow-xl hover:z-10"
                            >
                                <v-icon icon="mdi-phone" color="green" size="32"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">
                                        {{ $t("tutorial.voice") }}
                                    </div>
                                    <div class="text-sm text-gray-900 dark:text-white">
                                        {{ $t("tutorial.voice_desc") }}
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-all hover:scale-[1.03] hover:shadow-xl hover:z-10"
                            >
                                <v-icon icon="mdi-tools" color="orange" size="32"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">
                                        {{ $t("tutorial.tools") }}
                                    </div>
                                    <div class="text-sm text-gray-900 dark:text-white">
                                        {{ $t("tutorial.tools_desc") }}
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-all hover:scale-[1.03] hover:shadow-xl hover:z-10"
                            >
                                <v-icon icon="mdi-database-search" color="teal" size="32"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">
                                        {{ $t("tutorial.archiver") }}
                                    </div>
                                    <div class="text-sm text-gray-900 dark:text-white">
                                        {{ $t("tutorial.archiver_desc") }}
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-all hover:scale-[1.03] hover:shadow-xl hover:z-10"
                            >
                                <v-icon icon="mdi-account-cancel" color="amber" size="32"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">
                                        {{ $t("tutorial.banishment") }}
                                    </div>
                                    <div class="text-sm text-gray-900 dark:text-white">
                                        {{ $t("tutorial.banishment_desc") }}
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-all hover:scale-[1.03] hover:shadow-xl hover:z-10"
                            >
                                <v-icon icon="mdi-keyboard-outline" color="red" size="32"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">
                                        {{ $t("tutorial.palette") }}
                                    </div>
                                    <div class="text-sm text-gray-900 dark:text-white">
                                        {{ $t("tutorial.palette_desc") }}
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-all hover:scale-[1.03] hover:shadow-xl hover:z-10"
                            >
                                <v-icon icon="mdi-translate" color="cyan" size="32"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">{{ $t("tutorial.i18n") }}</div>
                                    <div class="text-sm text-gray-900 dark:text-white">
                                        {{ $t("tutorial.i18n_desc") }}
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div
                            class="w-full flex justify-end items-center gap-2 mt-4 px-4 text-gray-400 dark:text-zinc-500"
                        >
                            <v-icon icon="mdi-plus" size="16"></v-icon>
                            <span class="text-xs font-bold uppercase tracking-widest">{{
                                $t("tutorial.more_features")
                            }}</span>
                        </div>
                    </div>

                    <!-- Step 2: Add Interface -->
                    <div v-else-if="currentStep === 2" key="step2" class="space-y-6">
                        <div class="text-center space-y-2">
                            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">
                                {{ $t("tutorial.connect") }}
                            </h2>
                            <p class="text-gray-600 dark:text-zinc-400 text-base">
                                {{ $t("tutorial.connect_desc") }}
                            </p>
                        </div>

                        <div class="space-y-4">
                            <!-- Community Interfaces -->
                            <div
                                class="bg-gray-50 dark:bg-zinc-900 rounded-3xl p-3 border border-gray-100 dark:border-zinc-800"
                            >
                                <div class="flex items-center gap-2 mb-3 px-2 text-sm">
                                    <v-icon icon="mdi-web" color="blue"></v-icon>
                                    <span class="font-bold text-gray-900 dark:text-white">{{
                                        $t("tutorial.suggested_networks")
                                    }}</span>
                                </div>
                                <div class="space-y-2 max-h-[260px] overflow-y-auto pr-2">
                                    <div
                                        v-for="iface in communityInterfaces"
                                        :key="iface.name"
                                        class="flex items-center justify-between p-3 bg-white dark:bg-zinc-800 rounded-xl border border-gray-100 dark:border-zinc-700 hover:border-blue-400 transition-colors cursor-pointer"
                                        @click="selectCommunityInterface(iface)"
                                    >
                                        <div class="flex flex-col">
                                            <span class="font-bold text-gray-900 dark:text-white text-sm">{{
                                                iface.name
                                            }}</span>
                                            <span class="text-[11px] text-gray-500 dark:text-zinc-400"
                                                >{{ iface.target_host }}:{{ iface.target_port }}</span
                                            >
                                        </div>
                                        <div class="flex items-center gap-2">
                                            <span
                                                v-if="iface.online"
                                                class="flex items-center gap-1 text-[9px] font-bold text-green-500 uppercase tracking-[0.2em]"
                                            >
                                                <span
                                                    class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"
                                                ></span>
                                                {{ $t("tutorial.online") }}
                                            </span>
                                            <button
                                                type="button"
                                                class="px-3 py-1 text-[11px] rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold shadow-sm transition-all"
                                                @click.stop="selectCommunityInterface(iface)"
                                            >
                                                {{ $t("tutorial.use") }}
                                            </button>
                                        </div>
                                    </div>
                                    <div v-if="loadingInterfaces" class="flex justify-center py-3">
                                        <v-progress-circular indeterminate color="blue" size="24"></v-progress-circular>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="flex flex-col items-center gap-3 text-sm text-gray-900 dark:text-white">
                            <p class="max-w-sm text-center">
                                {{ $t("tutorial.custom_interfaces_desc") }}
                            </p>
                            <button
                                type="button"
                                class="px-5 py-2 text-[11px] rounded-xl border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 font-semibold shadow-sm transition-all hover:bg-gray-50 dark:hover:bg-zinc-700 hover:border-blue-400 dark:hover:border-blue-500"
                                @click="gotoAddInterface"
                            >
                                {{ $t("tutorial.open_interfaces") }}
                            </button>
                        </div>
                    </div>

                    <!-- Step 3: Documentation & Tools -->
                    <div v-else-if="currentStep === 3" key="step3" class="space-y-6">
                        <div class="text-center space-y-2">
                            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">
                                {{ $t("tutorial.learn_create") }}
                            </h2>
                            <p class="text-gray-600 dark:text-zinc-400">
                                {{ $t("tutorial.learn_create_desc") }}
                            </p>
                        </div>

                        <div class="grid grid-cols-1 gap-4">
                            <div
                                class="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800"
                            >
                                <v-icon icon="mdi-book-open-variant" color="blue" size="32"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">
                                        {{ $t("tutorial.documentation") }}
                                    </div>
                                    <div class="text-sm text-gray-900 dark:text-white mb-2">
                                        {{ $t("tutorial.documentation_desc") }}
                                    </div>
                                    <div class="flex gap-2">
                                        <a
                                            href="/meshchatx-docs/index.html"
                                            target="_blank"
                                            class="px-3 py-1 text-[10px] rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold shadow-sm transition-all inline-block"
                                        >
                                            {{ $t("tutorial.meshchatx_docs") }}
                                        </a>
                                        <a
                                            href="/reticulum-docs/index.html"
                                            target="_blank"
                                            class="px-3 py-1 text-[10px] rounded-xl border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 font-semibold shadow-sm transition-all hover:bg-gray-50 dark:hover:bg-zinc-700 hover:border-blue-400 dark:hover:border-blue-500 inline-block"
                                        >
                                            {{ $t("tutorial.reticulum_docs") }}
                                        </a>
                                    </div>
                                </div>
                            </div>

                            <div
                                class="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800"
                            >
                                <v-icon icon="mdi-file-document-edit-outline" color="orange" size="32"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">
                                        {{ $t("tutorial.micron_editor") }}
                                    </div>
                                    <div class="text-sm text-gray-900 dark:text-white mb-2">
                                        {{ $t("tutorial.micron_editor_desc") }}
                                    </div>
                                    <button
                                        type="button"
                                        class="px-3 py-1 text-[10px] rounded-xl border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 font-semibold shadow-sm transition-all hover:bg-gray-50 dark:hover:bg-zinc-700 hover:border-blue-400 dark:hover:border-blue-500"
                                        @click="gotoRoute('micron-editor')"
                                    >
                                        {{ $t("tutorial.open_micron_editor") }}
                                    </button>
                                </div>
                            </div>

                            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div
                                    class="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 cursor-pointer hover:border-blue-500 transition-colors"
                                    @click="gotoRoute('nomadnetwork')"
                                >
                                    <v-icon icon="mdi-earth" color="purple" size="24"></v-icon>
                                    <div>
                                        <div class="font-bold text-gray-900 dark:text-white text-xs">
                                            {{ $t("tutorial.paper_messages") }}
                                        </div>
                                        <div class="text-[10px] text-gray-900 dark:text-white">
                                            {{ $t("tutorial.paper_messages_desc") }}
                                        </div>
                                    </div>
                                </div>

                                <div
                                    class="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 cursor-pointer hover:border-blue-500 transition-colors"
                                    @click="gotoRoute('messages')"
                                >
                                    <v-icon icon="mdi-message-text-outline" color="green" size="24"></v-icon>
                                    <div>
                                        <div class="font-bold text-gray-900 dark:text-white text-xs">
                                            {{ $t("tutorial.send_messages") }}
                                        </div>
                                        <div class="text-[10px] text-gray-900 dark:text-white">
                                            {{ $t("tutorial.send_messages_desc") }}
                                        </div>
                                    </div>
                                </div>

                                <div
                                    class="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 cursor-pointer hover:border-blue-500 transition-colors"
                                    @click="gotoRoute('network-visualiser')"
                                >
                                    <v-icon icon="mdi-hub" color="teal" size="24"></v-icon>
                                    <div>
                                        <div class="font-bold text-gray-900 dark:text-white text-xs">
                                            {{ $t("tutorial.explore_nodes") }}
                                        </div>
                                        <div class="text-[10px] text-gray-900 dark:text-white">
                                            {{ $t("tutorial.explore_nodes_desc") }}
                                        </div>
                                    </div>
                                </div>

                                <div
                                    class="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 cursor-pointer hover:border-blue-500 transition-colors"
                                    @click="gotoRoute('call')"
                                >
                                    <v-icon icon="mdi-phone-in-talk-outline" color="red" size="24"></v-icon>
                                    <div>
                                        <div class="font-bold text-gray-900 dark:text-white text-xs">
                                            {{ $t("tutorial.voice_calls") }}
                                        </div>
                                        <div class="text-[10px] text-gray-900 dark:text-white">
                                            {{ $t("tutorial.voice_calls_desc") }}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Step 4: Finish -->
                    <div
                        v-else-if="currentStep === 4"
                        key="step4"
                        class="flex flex-col items-center text-center space-y-8 py-10"
                    >
                        <div class="w-32 h-32 bg-green-500/10 rounded-full flex items-center justify-center relative">
                            <v-icon icon="mdi-check-decagram" color="green" size="80"></v-icon>
                            <div class="absolute inset-0 bg-green-500/20 rounded-full animate-ping opacity-20"></div>
                        </div>
                        <div class="space-y-3">
                            <h2 class="text-3xl font-black text-gray-900 dark:text-white">
                                {{ $t("tutorial.ready") }}
                            </h2>
                            <p class="text-lg text-gray-600 dark:text-zinc-400 max-w-md mx-auto">
                                {{ $t("tutorial.ready_desc") }}
                            </p>
                        </div>
                        <div
                            v-if="interfaceAddedViaTutorial"
                            class="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-2xl border border-amber-100 dark:border-amber-900/30 text-amber-700 dark:text-amber-400 text-sm flex gap-3 max-w-md text-left"
                        >
                            <v-icon icon="mdi-information-outline" class="shrink-0"></v-icon>
                            <span>{{ $t("tutorial.docker_note") }}</span>
                        </div>
                    </div>
                </transition>
            </v-card-text>

            <!-- Footer -->
            <v-divider class="dark:border-zinc-900"></v-divider>
            <v-card-actions class="px-6 py-6 bg-gray-50 dark:bg-zinc-950/50 flex justify-between">
                <button
                    v-if="currentStep > 1 && currentStep < totalSteps"
                    type="button"
                    class="px-6 py-2.5 rounded-xl border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 font-semibold text-sm shadow-sm transition-all hover:bg-gray-50 dark:hover:bg-zinc-700 hover:border-blue-400 dark:hover:border-blue-500"
                    @click="currentStep--"
                >
                    {{ $t("tutorial.back") }}
                </button>
                <div v-else></div>

                <div class="flex gap-3">
                    <button
                        v-if="currentStep < totalSteps"
                        type="button"
                        class="px-6 py-2.5 rounded-xl border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 font-semibold text-sm shadow-sm transition-all opacity-50 hover:opacity-100 hover:bg-gray-50 dark:hover:bg-zinc-700"
                        @click="skipTutorial"
                    >
                        {{ $t("tutorial.skip") }}
                    </button>

                    <button
                        v-if="currentStep < totalSteps"
                        type="button"
                        class="px-8 h-12 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm shadow-sm transition-all"
                        @click="nextStep"
                    >
                        {{ $t("tutorial.next") }}
                    </button>

                    <button
                        v-else
                        type="button"
                        class="px-8 h-12 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm shadow-sm transition-all"
                        @click="finishAndRestart"
                    >
                        {{ $t("tutorial.restart_start") }}
                    </button>
                </div>
            </v-card-actions>
        </v-card>
    </v-dialog>

    <div v-else class="flex flex-col h-full bg-white dark:bg-zinc-950 overflow-hidden relative">
        <!-- Settings Controls -->
        <div class="absolute top-4 left-4 z-50 flex items-center gap-1">
            <LanguageSelector @language-change="onLanguageChange" />
            <button
                type="button"
                class="rounded-full p-1.5 sm:p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-zinc-800 transition-colors"
                :title="config?.theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
                @click="toggleTheme"
            >
                <MaterialDesignIcon
                    :icon-name="config?.theme === 'dark' ? 'brightness-6' : 'brightness-4'"
                    class="w-5 h-5 sm:w-6 sm:h-6"
                />
            </button>
        </div>

        <!-- Progress Bar -->
        <div class="w-full h-1.5 bg-gray-100 dark:bg-zinc-900 overflow-hidden flex">
            <div
                v-for="step in totalSteps"
                :key="step"
                class="h-full transition-all duration-500 ease-out"
                :class="[
                    currentStep >= step ? 'bg-blue-500' : 'bg-transparent',
                    currentStep === step ? 'flex-[2]' : 'flex-1',
                ]"
                :style="{ borderRight: step < totalSteps ? '1px solid rgba(0,0,0,0.05)' : 'none' }"
            ></div>
        </div>

        <div class="flex-1 overflow-y-auto px-6 md:px-12 py-10">
            <div class="max-w-4xl mx-auto h-full flex flex-col justify-between">
                <transition name="fade-slide" mode="out-in">
                    <!-- Step 1: Welcome -->
                    <div
                        v-if="currentStep === 1"
                        key="step1"
                        class="flex flex-col items-center text-center space-y-8 py-10"
                    >
                        <div class="relative">
                            <div class="w-32 h-32 bg-blue-500/10 rounded-3xl rotate-12 absolute -inset-2"></div>
                            <img :src="logoUrl" class="w-32 h-32 relative z-10 p-2" />
                        </div>
                        <div class="space-y-4">
                            <h1 class="text-5xl font-black tracking-tight text-gray-900 dark:text-white">
                                {{ $t("tutorial.welcome") }} <span class="text-blue-500">MeshChatX</span>
                            </h1>
                            <p class="text-xl text-gray-600 dark:text-zinc-400 max-w-2xl mx-auto">
                                {{ $t("tutorial.welcome_desc") }}
                            </p>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 w-full mt-12">
                            <div
                                class="flex items-start gap-6 p-6 rounded-3xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-all hover:scale-[1.03] hover:shadow-2xl hover:z-10"
                            >
                                <v-icon icon="mdi-shield-lock" color="blue" size="40"></v-icon>
                                <div>
                                    <div class="font-bold text-xl text-gray-900 dark:text-white">
                                        {{ $t("tutorial.security") }}
                                    </div>
                                    <div class="text-gray-900 dark:text-white">
                                        {{ $t("tutorial.security_desc_page") }}
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-6 p-6 rounded-3xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-all hover:scale-[1.03] hover:shadow-2xl hover:z-10"
                            >
                                <v-icon icon="mdi-map-marker-path" color="purple" size="40"></v-icon>
                                <div>
                                    <div class="font-bold text-xl text-gray-900 dark:text-white">
                                        {{ $t("tutorial.maps") }}
                                    </div>
                                    <div class="text-gray-900 dark:text-white">
                                        {{ $t("tutorial.maps_desc_page") }}
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-6 p-6 rounded-3xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-all hover:scale-[1.03] hover:shadow-2xl hover:z-10"
                            >
                                <v-icon icon="mdi-phone" color="green" size="40"></v-icon>
                                <div>
                                    <div class="font-bold text-xl text-gray-900 dark:text-white">
                                        {{ $t("tutorial.voice") }}
                                    </div>
                                    <div class="text-gray-900 dark:text-white">
                                        {{ $t("tutorial.voice_desc_page") }}
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-6 p-6 rounded-3xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-all hover:scale-[1.03] hover:shadow-2xl hover:z-10"
                            >
                                <v-icon icon="mdi-tools" color="orange" size="40"></v-icon>
                                <div>
                                    <div class="font-bold text-xl text-gray-900 dark:text-white">
                                        {{ $t("tutorial.tools") }}
                                    </div>
                                    <div class="text-gray-900 dark:text-white">
                                        {{ $t("tutorial.tools_desc_page") }}
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-6 p-6 rounded-3xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-all hover:scale-[1.03] hover:shadow-2xl hover:z-10"
                            >
                                <v-icon icon="mdi-database-search" color="teal" size="40"></v-icon>
                                <div>
                                    <div class="font-bold text-xl text-gray-900 dark:text-white">
                                        {{ $t("tutorial.archiver") }}
                                    </div>
                                    <div class="text-gray-900 dark:text-white">
                                        {{ $t("tutorial.archiver_desc_page") }}
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-6 p-6 rounded-3xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-all hover:scale-[1.03] hover:shadow-2xl hover:z-10"
                            >
                                <v-icon icon="mdi-account-cancel" color="amber" size="40"></v-icon>
                                <div>
                                    <div class="font-bold text-xl text-gray-900 dark:text-white">
                                        {{ $t("tutorial.banishment") }}
                                    </div>
                                    <div class="text-gray-900 dark:text-white">
                                        {{ $t("tutorial.banishment_desc") }}
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-6 p-6 rounded-3xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-all hover:scale-[1.03] hover:shadow-2xl hover:z-10"
                            >
                                <v-icon icon="mdi-keyboard-outline" color="red" size="40"></v-icon>
                                <div>
                                    <div class="font-bold text-xl text-gray-900 dark:text-white">
                                        {{ $t("tutorial.palette") }}
                                    </div>
                                    <div class="text-gray-900 dark:text-white">
                                        {{ $t("tutorial.palette_desc_page") }}
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-6 p-6 rounded-3xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-all hover:scale-[1.03] hover:shadow-2xl hover:z-10"
                            >
                                <v-icon icon="mdi-translate" color="cyan" size="40"></v-icon>
                                <div>
                                    <div class="font-bold text-xl text-gray-900 dark:text-white">
                                        {{ $t("tutorial.i18n") }}
                                    </div>
                                    <div class="text-gray-900 dark:text-white">
                                        {{ $t("tutorial.i18n_desc_page") }}
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div
                            class="w-full flex justify-end items-center gap-2 mt-8 px-6 text-gray-400 dark:text-zinc-500"
                        >
                            <v-icon icon="mdi-plus" size="24"></v-icon>
                            <span class="text-base font-bold uppercase tracking-widest">{{
                                $t("tutorial.more_features")
                            }}</span>
                        </div>
                    </div>

                    <!-- Step 2: Add Interface -->
                    <div v-else-if="currentStep === 2" key="step2" class="space-y-6 py-8">
                        <div class="text-center space-y-2">
                            <h2 class="text-3xl font-black text-gray-900 dark:text-white">
                                {{ $t("tutorial.connect") }}
                            </h2>
                            <p class="text-lg text-gray-600 dark:text-zinc-400 max-w-2xl mx-auto">
                                {{ $t("tutorial.connect_desc_page") }}
                            </p>
                        </div>

                        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <!-- Community Interfaces -->
                            <div
                                class="bg-gray-50 dark:bg-zinc-900 rounded-[1.5rem] p-5 border border-gray-100 dark:border-zinc-800"
                            >
                                <div class="flex items-center gap-2 mb-5">
                                    <v-icon icon="mdi-web" color="blue" size="26"></v-icon>
                                    <span class="text-lg font-bold text-gray-900 dark:text-white">{{
                                        $t("tutorial.suggested_relays")
                                    }}</span>
                                </div>
                                <div class="space-y-3 max-h-[320px] overflow-y-auto pr-3 custom-scrollbar">
                                    <div
                                        v-for="iface in communityInterfaces"
                                        :key="iface.name"
                                        class="flex items-center justify-between p-3 bg-white dark:bg-zinc-800 rounded-xl border border-gray-100 dark:border-zinc-700 hover:border-blue-400 transition-all cursor-pointer"
                                        @click="selectCommunityInterface(iface)"
                                    >
                                        <div class="flex flex-col">
                                            <span class="font-bold text-gray-900 dark:text-white text-base">
                                                {{ iface.name }}
                                            </span>
                                            <span class="text-xs text-gray-500 font-mono"
                                                >{{ iface.target_host }}:{{ iface.target_port }}</span
                                            >
                                        </div>
                                        <div class="flex items-center gap-2">
                                            <span
                                                v-if="iface.online"
                                                class="flex items-center gap-1.5 text-[9px] font-bold text-green-500 uppercase tracking-[0.2em]"
                                            >
                                                <span class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                                                {{ $t("tutorial.online") }}
                                            </span>
                                            <button
                                                type="button"
                                                class="px-4 py-1 text-[11px] rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold shadow-sm transition-all"
                                                @click.stop="selectCommunityInterface(iface)"
                                            >
                                                {{ $t("tutorial.use") }}
                                            </button>
                                        </div>
                                    </div>
                                    <div v-if="loadingInterfaces" class="flex justify-center py-4">
                                        <v-progress-circular indeterminate color="blue" size="32"></v-progress-circular>
                                    </div>
                                </div>
                            </div>

                            <div
                                class="flex flex-col justify-center gap-4 text-sm text-gray-900 dark:text-white bg-gray-50 dark:bg-zinc-900 rounded-[1.5rem] p-5 border border-gray-100 dark:border-zinc-800"
                            >
                                <div class="text-center">
                                    <p class="text-base font-bold text-gray-900 dark:text-white">
                                        {{ $t("tutorial.custom_interfaces") }}
                                    </p>
                                    <p class="mt-2">
                                        {{ $t("tutorial.custom_interfaces_desc_page") }}
                                    </p>
                                </div>
                                <button
                                    type="button"
                                    class="px-4 py-2 text-[11px] rounded-xl border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 font-semibold shadow-sm transition-all hover:bg-gray-50 dark:hover:bg-zinc-700 hover:border-blue-400 dark:hover:border-blue-500"
                                    @click="gotoAddInterface"
                                >
                                    {{ $t("tutorial.open_interfaces") }}
                                </button>
                            </div>
                        </div>
                    </div>
                    <!-- Step 3: Documentation & Tools -->
                    <div v-else-if="currentStep === 3" key="step3" class="space-y-8 py-10">
                        <div class="text-center space-y-4">
                            <h2 class="text-4xl font-black text-gray-900 dark:text-white">
                                {{ $t("tutorial.learn_create") }}
                            </h2>
                            <p class="text-xl text-gray-600 dark:text-zinc-400 max-w-2xl mx-auto">
                                {{ $t("tutorial.learn_create_desc_page") }}
                            </p>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                            <div
                                class="flex flex-col items-center gap-6 p-8 rounded-[2rem] bg-gray-50 dark:bg-zinc-900 text-center border border-gray-100 dark:border-zinc-800"
                            >
                                <v-icon icon="mdi-book-open-variant" color="blue" size="64"></v-icon>
                                <div>
                                    <div class="font-bold text-2xl text-gray-900 dark:text-white mb-2">
                                        {{ $t("tutorial.documentation") }}
                                    </div>
                                    <p class="text-gray-900 dark:text-white mb-6">
                                        {{ $t("tutorial.documentation_desc_page") }}
                                    </p>
                                    <div class="flex flex-col gap-3">
                                        <a
                                            href="/meshchatx-docs/index.html"
                                            target="_blank"
                                            class="h-12 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold shadow-sm transition-all inline-flex items-center justify-center px-6"
                                        >
                                            {{ $t("tutorial.read_meshchatx_docs") }}
                                        </a>
                                        <a
                                            href="/reticulum-docs/index.html"
                                            target="_blank"
                                            class="h-12 rounded-xl border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 font-semibold shadow-sm transition-all hover:bg-gray-50 dark:hover:bg-zinc-700 hover:border-blue-400 dark:hover:border-blue-500 inline-flex items-center justify-center px-6"
                                        >
                                            {{ $t("tutorial.reticulum_manual") }}
                                        </a>
                                    </div>
                                </div>
                            </div>

                            <div
                                class="flex flex-col items-center gap-6 p-8 rounded-[2rem] bg-gray-50 dark:bg-zinc-900 text-center border border-gray-100 dark:border-zinc-800"
                            >
                                <v-icon icon="mdi-file-document-edit-outline" color="orange" size="64"></v-icon>
                                <div>
                                    <div class="font-bold text-2xl text-gray-900 dark:text-white mb-2">
                                        {{ $t("tutorial.micron_editor") }}
                                    </div>
                                    <p class="text-gray-900 dark:text-white mb-6">
                                        {{ $t("tutorial.micron_editor_desc_page") }}
                                    </p>
                                    <button
                                        type="button"
                                        class="w-full h-12 rounded-xl bg-orange-600 hover:bg-orange-500 text-white font-semibold shadow-sm transition-all"
                                        @click="gotoRoute('micron-editor')"
                                    >
                                        {{ $t("tutorial.open_micron_editor") }}
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                            <div
                                class="flex flex-col items-center gap-4 p-6 rounded-3xl bg-gray-50 dark:bg-zinc-900 text-center border border-gray-100 dark:border-zinc-800 cursor-pointer hover:border-blue-500 transition-all hover:scale-[1.02]"
                                @click="gotoRoute('nomadnetwork')"
                            >
                                <v-icon icon="mdi-earth" color="purple" size="40"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">
                                        {{ $t("tutorial.paper_messages") }}
                                    </div>
                                    <div class="text-sm text-gray-900 dark:text-white mt-1">
                                        {{ $t("tutorial.paper_messages_desc") }}
                                    </div>
                                </div>
                            </div>

                            <div
                                class="flex flex-col items-center gap-4 p-6 rounded-3xl bg-gray-50 dark:bg-zinc-900 text-center border border-gray-100 dark:border-zinc-800 cursor-pointer hover:border-blue-500 transition-all hover:scale-[1.02]"
                                @click="gotoRoute('messages')"
                            >
                                <v-icon icon="mdi-message-text-outline" color="green" size="40"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">
                                        {{ $t("tutorial.send_messages") }}
                                    </div>
                                    <div class="text-sm text-gray-900 dark:text-white mt-1">
                                        {{ $t("tutorial.send_messages_desc") }}
                                    </div>
                                </div>
                            </div>

                            <div
                                class="flex flex-col items-center gap-4 p-6 rounded-3xl bg-gray-50 dark:bg-zinc-900 text-center border border-gray-100 dark:border-zinc-800 cursor-pointer hover:border-blue-500 transition-all hover:scale-[1.02]"
                                @click="gotoRoute('network-visualiser')"
                            >
                                <v-icon icon="mdi-hub" color="teal" size="40"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">
                                        {{ $t("tutorial.explore_nodes") }}
                                    </div>
                                    <div class="text-sm text-gray-900 dark:text-white mt-1">
                                        {{ $t("tutorial.explore_nodes_desc") }}
                                    </div>
                                </div>
                            </div>

                            <div
                                class="flex flex-col items-center gap-4 p-6 rounded-3xl bg-gray-50 dark:bg-zinc-900 text-center border border-gray-100 dark:border-zinc-800 cursor-pointer hover:border-blue-500 transition-all hover:scale-[1.02]"
                                @click="gotoRoute('call')"
                            >
                                <v-icon icon="mdi-phone-in-talk-outline" color="red" size="40"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">
                                        {{ $t("tutorial.voice_calls") }}
                                    </div>
                                    <div class="text-sm text-gray-900 dark:text-white mt-1">
                                        {{ $t("tutorial.voice_calls_desc") }}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Step 4: Finish -->
                    <div
                        v-else-if="currentStep === 4"
                        key="step4"
                        class="flex flex-col items-center text-center space-y-10 py-20"
                    >
                        <div class="w-48 h-48 bg-green-500/10 rounded-full flex items-center justify-center relative">
                            <v-icon icon="mdi-check-decagram" color="green" size="120"></v-icon>
                            <div class="absolute inset-0 bg-green-500/20 rounded-full animate-ping opacity-20"></div>
                        </div>
                        <div class="space-y-4">
                            <h2 class="text-5xl font-black text-gray-900 dark:text-white">
                                {{ $t("tutorial.ready") }}
                            </h2>
                            <p class="text-xl text-gray-600 dark:text-zinc-400 max-w-2xl mx-auto">
                                {{ $t("tutorial.ready_desc_page") }}
                            </p>
                        </div>
                        <div
                            class="p-6 bg-amber-50 dark:bg-amber-900/20 rounded-3xl border border-amber-100 dark:border-amber-900/30 text-amber-700 dark:text-amber-400 flex gap-4 max-w-xl text-left"
                        >
                            <v-icon icon="mdi-information-outline" size="32" class="shrink-0"></v-icon>
                            <div class="space-y-1">
                                <div class="font-bold text-lg">{{ $t("tutorial.restart_required") }}</div>
                                <div class="opacity-90">
                                    {{ $t("tutorial.restart_desc_page") }}
                                </div>
                            </div>
                        </div>
                    </div>
                </transition>

                <!-- Navigation Buttons (Page Mode) -->
                <div class="flex justify-between items-center mt-12 border-t dark:border-zinc-900 pt-8">
                    <button
                        v-if="currentStep > 1 && currentStep < totalSteps"
                        type="button"
                        class="px-8 h-12 rounded-xl border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 font-semibold text-sm shadow-sm transition-all hover:bg-gray-50 dark:hover:bg-zinc-700 hover:border-blue-400 dark:hover:border-blue-500"
                        @click="currentStep--"
                    >
                        {{ $t("tutorial.back") }}
                    </button>
                    <div v-else></div>

                    <div class="flex gap-4">
                        <button
                            v-if="currentStep < totalSteps"
                            type="button"
                            class="px-8 h-12 rounded-xl border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 font-semibold text-sm shadow-sm transition-all opacity-50 hover:opacity-100 hover:bg-gray-50 dark:hover:bg-zinc-700"
                            @click="skipTutorial"
                        >
                            {{ $t("tutorial.skip_setup") }}
                        </button>

                        <button
                            v-if="currentStep < totalSteps"
                            type="button"
                            class="px-12 h-14 text-lg rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold shadow-sm transition-all"
                            @click="nextStep"
                        >
                            {{ $t("tutorial.continue") }}
                        </button>

                        <button
                            v-else
                            type="button"
                            class="px-12 h-14 text-lg rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold shadow-sm transition-all"
                            @click="finishAndRestart"
                        >
                            {{ $t("tutorial.restart_start") }}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import logoUrl from "../assets/images/logo.png";
import ToastUtils from "../js/ToastUtils";
import DialogUtils from "../js/DialogUtils";
import ElectronUtils from "../js/ElectronUtils";
import GlobalState from "../js/GlobalState";
import LanguageSelector from "./LanguageSelector.vue";
import MaterialDesignIcon from "./MaterialDesignIcon.vue";

export default {
    name: "TutorialModal",
    components: {
        LanguageSelector,
        MaterialDesignIcon,
    },
    data() {
        return {
            visible: false,
            currentStep: 1,
            totalSteps: 4,
            logoUrl,
            communityInterfaces: [],
            loadingInterfaces: false,
            interfaceAddedViaTutorial: false,
        };
    },
    computed: {
        isPage() {
            return this.$route?.meta?.isPage === true;
        },
        isMobile() {
            return window.innerWidth < 640;
        },
        config() {
            return GlobalState.config;
        },
    },
    mounted() {
        if (this.isPage) {
            this.loadCommunityInterfaces();
        }
    },
    methods: {
        async toggleTheme() {
            const newTheme = this.config.theme === "dark" ? "light" : "dark";
            try {
                await window.axios.patch("/api/v1/config", {
                    theme: newTheme,
                });
                GlobalState.config.theme = newTheme;
            } catch (e) {
                console.error("Failed to update theme:", e);
            }
        },
        async onLanguageChange(langCode) {
            try {
                await window.axios.patch("/api/v1/config", {
                    language: langCode,
                });
                this.$i18n.locale = langCode;
                GlobalState.config.language = langCode;
            } catch (e) {
                console.error("Failed to update language:", e);
            }
        },
        async show() {
            this.visible = true;
            this.currentStep = 1;
            this.interfaceAddedViaTutorial = false;
            await this.loadCommunityInterfaces();
        },
        async loadCommunityInterfaces() {
            this.loadingInterfaces = true;
            try {
                const response = await window.axios.get("/api/v1/community-interfaces");
                this.communityInterfaces = response.data.interfaces;
            } catch (e) {
                console.error("Failed to load community interfaces:", e);
            } finally {
                this.loadingInterfaces = false;
            }
        },
        async selectCommunityInterface(iface) {
            try {
                await window.axios.post("/api/v1/reticulum/interfaces/add", {
                    name: iface.name,
                    type: iface.type,
                    target_host: iface.target_host,
                    target_port: iface.target_port,
                    enabled: true,
                });
                ToastUtils.success(`Added interface: ${iface.name}`);

                this.interfaceAddedViaTutorial = true;

                // track change
                GlobalState.hasPendingInterfaceChanges = true;
                GlobalState.modifiedInterfaceNames.add(iface.name);

                this.nextStep();
            } catch (e) {
                console.error(e);
                ToastUtils.error(e.response?.data?.message || "Failed to add interface");
            }
        },
        gotoAddInterface() {
            if (!this.isPage) {
                this.visible = false;
            }
            if (this.$router) {
                this.$router.push({ path: "/interfaces/add" });
            }
        },
        gotoRoute(routeName) {
            if (!this.isPage) {
                this.visible = false;
            }
            if (this.$router) {
                this.$router.push({ name: routeName });
            }
        },
        nextStep() {
            if (this.currentStep < this.totalSteps) {
                this.currentStep++;
            }
        },
        async skipTutorial() {
            if (await DialogUtils.confirm(this.$t("tutorial.skip_confirm"))) {
                await this.markSeen();
                this.visible = false;
            }
        },
        async markSeen() {
            try {
                await window.axios.post("/api/v1/app/tutorial/seen");
            } catch (e) {
                console.error("Failed to mark tutorial as seen:", e);
            }
        },
        async finishAndRestart() {
            await this.markSeen();
            if (ElectronUtils.isElectron()) {
                ElectronUtils.relaunch();
            } else {
                if (this.interfaceAddedViaTutorial) {
                    ToastUtils.info("Restart the application/container to apply changes.");
                }
                this.visible = false;
            }
        },
        async onVisibleUpdate(val) {
            if (!val) {
                // if closed by clicking away, mark as seen so it doesn't pop up again
                await this.markSeen();
            }
        },
    },
};
</script>

<style scoped>
.tutorial-dialog :deep(.v-field) {
    border-radius: 1rem !important;
}

.tutorial-dialog :deep(.v-field--variant-outlined .v-field__outline) {
    --v-field-border-opacity: 0.15;
}

.tutorial-dialog :deep(.v-field--focused .v-field__outline) {
    --v-field-border-opacity: 1;
}

.tutorial-dialog :deep(.v-field__input) {
    padding-top: 24px !important;
    padding-bottom: 8px !important;
}

.tutorial-dialog :deep(.v-label.v-field-label--floating) {
    transform: translateY(-8px) scale(0.75) !important;
    font-weight: 800 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

.tutorial-dialog :deep(.v-select .v-theme--light),
.tutorial-dialog :deep(.v-list),
.tutorial-dialog :deep(.v-list-item) {
    background-color: white !important;
    color: #111827 !important;
}

.tutorial-dialog :deep(.v-list-item-title),
.tutorial-dialog :deep(.v-list-item-subtitle) {
    color: inherit !important;
}

.tutorial-dialog :deep(.dark .v-list),
.tutorial-dialog :deep(.dark .v-list-item) {
    background-color: #18181b !important;
    color: white !important;
}

.tutorial-dialog :deep(.v-field__input) {
    color: inherit !important;
}

.tutorial-dialog :deep(.v-label.v-field-label) {
    color: #6b7280 !important;
}

.tutorial-dialog :deep(.dark .v-label.v-field-label) {
    color: #a1a1aa !important;
}

.tutorial-dialog .v-overlay__content {
    border-radius: 2rem !important;
    overflow: hidden;
}

.fade-slide-enter-active,
.fade-slide-leave-active {
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-slide-enter-from {
    opacity: 0;
    transform: translateX(30px);
}

.fade-slide-leave-to {
    opacity: 0;
    transform: translateX(-30px);
}
</style>
