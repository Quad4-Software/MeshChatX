<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <v-dialog
        v-if="!isPage"
        v-model="visible"
        :fullscreen="dialogFullscreen"
        max-width="800"
        scrollable
        transition="dialog-bottom-transition"
        class="tutorial-dialog"
        persistent
        @update:model-value="onVisibleUpdate"
    >
        <v-card
            class="flex min-h-0 flex-1 flex-col bg-white dark:bg-zinc-950 border-0 overflow-hidden relative h-full max-h-[100dvh]"
        >
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
            <v-card-text
                class="relative min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-6 sm:px-6 md:px-12 md:py-10"
            >
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

                    <!-- Step 2: Choose Connection Mode -->
                    <div v-else-if="currentStep === 2" key="step2-mode" class="space-y-6">
                        <div class="text-center space-y-2">
                            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">
                                {{ $t("tutorial.connect") }}
                            </h2>
                            <p class="text-gray-600 dark:text-zinc-400 text-base">
                                {{ $t("tutorial.connect_desc") }}
                            </p>
                        </div>

                        <div class="grid grid-cols-1 gap-4">
                            <button
                                type="button"
                                class="text-left flex items-start gap-4 p-5 rounded-2xl bg-blue-500/5 dark:bg-blue-500/10 border-2 transition-all"
                                :class="[
                                    connectionMode === 'discovery'
                                        ? 'border-blue-500 ring-2 ring-blue-500/30'
                                        : 'border-blue-500/20 hover:border-blue-500',
                                ]"
                                :disabled="savingDiscovery"
                                @click="useDiscoveryMode"
                            >
                                <v-icon icon="mdi-radar" color="blue" size="40"></v-icon>
                                <div class="flex-1 min-w-0">
                                    <div class="font-bold text-lg text-gray-900 dark:text-white">
                                        {{ $t("tutorial.mode_discovery_title") }}
                                    </div>
                                    <div class="text-sm text-gray-600 dark:text-zinc-400 mt-1">
                                        {{ $t("tutorial.mode_discovery_desc") }}
                                    </div>
                                </div>
                                <v-progress-circular
                                    v-if="savingDiscovery"
                                    indeterminate
                                    size="20"
                                    width="2"
                                ></v-progress-circular>
                            </button>

                            <button
                                type="button"
                                class="text-left flex items-start gap-4 p-5 rounded-2xl bg-emerald-500/5 dark:bg-emerald-500/10 border-2 transition-all"
                                :class="[
                                    connectionMode === 'local'
                                        ? 'border-emerald-500 ring-2 ring-emerald-500/30'
                                        : 'border-emerald-500/20 hover:border-emerald-500',
                                ]"
                                :disabled="addingLocal || reloadingReticulum"
                                @click="useLocalMode"
                            >
                                <v-icon icon="mdi-lan" color="emerald" size="40"></v-icon>
                                <div class="flex-1 min-w-0">
                                    <div class="font-bold text-lg text-gray-900 dark:text-white">
                                        {{ $t("tutorial.mode_local_title") }}
                                    </div>
                                    <div class="text-sm text-gray-600 dark:text-zinc-400 mt-1">
                                        {{ $t("tutorial.mode_local_desc") }}
                                    </div>
                                </div>
                                <v-progress-circular
                                    v-if="addingLocal || reloadingReticulum"
                                    indeterminate
                                    size="20"
                                    width="2"
                                ></v-progress-circular>
                            </button>

                            <button
                                type="button"
                                class="text-left flex items-start gap-4 p-5 rounded-2xl bg-gray-100/50 dark:bg-zinc-800/40 border-2 transition-all"
                                :class="[
                                    connectionMode === 'manual'
                                        ? 'border-gray-500 ring-2 ring-gray-500/30'
                                        : 'border-gray-300 dark:border-zinc-700 hover:border-gray-500',
                                ]"
                                @click="useManualMode"
                            >
                                <v-icon icon="mdi-cog-outline" color="gray" size="40"></v-icon>
                                <div class="flex-1 min-w-0">
                                    <div class="font-bold text-lg text-gray-900 dark:text-white">
                                        {{ $t("tutorial.mode_manual_title") }}
                                    </div>
                                    <div class="text-sm text-gray-600 dark:text-zinc-400 mt-1">
                                        {{ $t("tutorial.mode_manual_desc") }}
                                    </div>
                                </div>
                            </button>
                        </div>

                        <p class="text-xs text-center text-gray-400 dark:text-zinc-500">
                            {{ $t("tutorial.mode_change_later") }}
                        </p>
                    </div>

                    <!-- Step 3: Bootstrap Selection -->
                    <div v-else-if="currentStep === 3" key="step3-bootstrap" class="space-y-6">
                        <div class="text-center space-y-2">
                            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">
                                {{ $t("tutorial.bootstrap_title") }}
                            </h2>
                            <p class="text-gray-600 dark:text-zinc-400 text-sm">
                                {{ $t("tutorial.bootstrap_desc") }}
                            </p>
                        </div>

                        <div class="space-y-4">
                            <div
                                v-if="sortedDiscoveredInterfaces.length > 0"
                                class="bg-emerald-500/5 dark:bg-emerald-500/10 rounded-3xl p-4 border border-emerald-500/20"
                            >
                                <div class="flex items-center gap-2 mb-3 px-1 text-sm">
                                    <v-icon icon="mdi-radar" color="emerald"></v-icon>
                                    <span class="font-bold text-gray-900 dark:text-white">{{
                                        $t("tutorial.bootstrap_discovered")
                                    }}</span>
                                </div>
                                <div class="space-y-2 max-h-[260px] overflow-y-auto pr-2 custom-scrollbar">
                                    <label
                                        v-for="iface in sortedDiscoveredInterfaces"
                                        :key="iface.discovery_hash || iface.name"
                                        class="flex items-center gap-3 p-3 bg-white dark:bg-zinc-800 rounded-xl border cursor-pointer transition-all"
                                        :class="[
                                            isBootstrapSelected(`disc:${iface.discovery_hash || iface.name}`)
                                                ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20'
                                                : 'border-gray-100 dark:border-zinc-700 hover:border-emerald-400',
                                        ]"
                                    >
                                        <input
                                            type="checkbox"
                                            class="w-4 h-4 accent-emerald-500"
                                            :checked="isBootstrapSelected(`disc:${iface.discovery_hash || iface.name}`)"
                                            @change="toggleBootstrap(`disc:${iface.discovery_hash || iface.name}`)"
                                        />
                                        <MaterialDesignIcon
                                            :icon-name="getDiscoveryIcon(iface)"
                                            class="w-5 h-5 text-emerald-500 shrink-0"
                                        />
                                        <div class="flex-1 min-w-0">
                                            <div class="text-sm font-bold text-gray-900 dark:text-white truncate">
                                                {{ iface.name }}
                                            </div>
                                            <div
                                                class="text-[10px] font-mono text-gray-500 dark:text-zinc-400 truncate"
                                            >
                                                <span v-if="iface.reachable_on"
                                                    >{{ iface.reachable_on
                                                    }}<span v-if="iface.port">:{{ iface.port }}</span></span
                                                >
                                                <span v-else>{{ iface.type }}</span>
                                                <span class="ml-2 capitalize">{{ iface.status }}</span>
                                            </div>
                                        </div>
                                    </label>
                                </div>
                            </div>

                            <div
                                class="bg-gray-50 dark:bg-zinc-900 rounded-3xl p-4 border border-gray-100 dark:border-zinc-800"
                            >
                                <div class="flex items-center gap-2 mb-3 px-1 text-sm">
                                    <v-icon icon="mdi-web" color="blue"></v-icon>
                                    <span class="font-bold text-gray-900 dark:text-white">{{
                                        $t("tutorial.bootstrap_community")
                                    }}</span>
                                </div>
                                <div class="space-y-2 max-h-[260px] overflow-y-auto pr-2 custom-scrollbar">
                                    <label
                                        v-for="iface in communityInterfaces"
                                        :key="iface.name"
                                        class="flex items-center gap-3 p-3 bg-white dark:bg-zinc-800 rounded-xl border cursor-pointer transition-all"
                                        :class="[
                                            isBootstrapSelected(`comm:${iface.name}`)
                                                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                                                : 'border-gray-100 dark:border-zinc-700 hover:border-blue-400',
                                        ]"
                                    >
                                        <input
                                            type="checkbox"
                                            class="w-4 h-4 accent-blue-500"
                                            :checked="isBootstrapSelected(`comm:${iface.name}`)"
                                            @change="toggleBootstrap(`comm:${iface.name}`)"
                                        />
                                        <v-icon icon="mdi-server-network" color="blue" size="20"></v-icon>
                                        <div class="flex-1 min-w-0">
                                            <div class="text-sm font-bold text-gray-900 dark:text-white truncate">
                                                {{ iface.name }}
                                            </div>
                                            <div
                                                class="text-[10px] font-mono text-gray-500 dark:text-zinc-400 truncate"
                                            >
                                                {{ iface.target_host
                                                }}<span v-if="iface.target_port">:{{ iface.target_port }}</span>
                                            </div>
                                        </div>
                                        <span
                                            v-if="iface.online"
                                            class="text-[9px] font-bold text-green-500 uppercase tracking-widest shrink-0"
                                            >{{ $t("tutorial.online") }}</span
                                        >
                                    </label>
                                    <div v-if="loadingInterfaces" class="flex justify-center py-3">
                                        <v-progress-circular indeterminate color="blue" size="24"></v-progress-circular>
                                    </div>
                                </div>
                            </div>

                            <div class="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
                                <p class="text-xs text-gray-500 dark:text-zinc-500">
                                    {{
                                        $t("tutorial.bootstrap_selected", {
                                            count: selectedBootstrapCount,
                                        })
                                    }}
                                </p>
                                <div class="flex gap-2">
                                    <button
                                        type="button"
                                        class="px-4 py-2 text-xs rounded-xl border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 font-semibold transition-all hover:bg-gray-50 dark:hover:bg-zinc-700"
                                        @click="skipBootstraps"
                                    >
                                        {{ $t("tutorial.bootstrap_skip") }}
                                    </button>
                                    <button
                                        type="button"
                                        class="px-5 py-2 text-xs rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold shadow transition-all"
                                        :disabled="
                                            addingBootstraps || reloadingReticulum || selectedBootstrapCount === 0
                                        "
                                        @click="confirmBootstraps"
                                    >
                                        <v-progress-circular
                                            v-if="addingBootstraps || reloadingReticulum"
                                            indeterminate
                                            size="14"
                                            width="2"
                                            class="mr-1"
                                        ></v-progress-circular>
                                        {{ $t("tutorial.bootstrap_confirm") }}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Step 4: Propagation Mode -->
                    <div v-else-if="currentStep === 4" key="step4-prop" class="space-y-6">
                        <div class="text-center space-y-2">
                            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">
                                {{ $t("tutorial.propagation") }}
                            </h2>
                            <p class="text-gray-600 dark:text-zinc-400 text-base">
                                {{ $t("tutorial.propagation_desc") }}
                            </p>
                        </div>

                        <div class="flex flex-col items-center gap-6 py-4">
                            <div
                                class="bg-blue-500/10 dark:bg-blue-500/20 p-6 rounded-[2rem] text-center space-y-4 border border-blue-500/20 max-w-md"
                            >
                                <v-icon icon="mdi-server-network" color="blue" size="48"></v-icon>
                                <div class="text-lg font-bold text-gray-900 dark:text-white">
                                    {{ $t("tutorial.propagation_question") }}
                                </div>
                                <p class="text-sm text-gray-600 dark:text-zinc-400">
                                    {{ $t("tutorial.propagation_auto") }}
                                </p>
                                <div class="flex flex-col gap-3 pt-2">
                                    <button
                                        type="button"
                                        class="w-full px-6 py-3 rounded-2xl bg-blue-600 hover:bg-blue-500 text-white font-bold shadow-lg transition-all transform hover:scale-[1.02]"
                                        :disabled="savingPropagation"
                                        @click="enableAutoPropagation"
                                    >
                                        <v-progress-circular
                                            v-if="savingPropagation"
                                            indeterminate
                                            size="20"
                                            width="2"
                                            class="mr-2"
                                        ></v-progress-circular>
                                        {{ $t("tutorial.propagation_enable_auto") }}
                                    </button>
                                    <button
                                        type="button"
                                        class="w-full px-6 py-3 rounded-2xl border-2 border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 font-bold shadow-sm transition-all transform hover:scale-[1.02]"
                                        @click="nextStep"
                                    >
                                        {{ $t("tutorial.propagation_skip_auto") }}
                                    </button>
                                </div>
                                <div class="mt-6 pt-6 border-t border-gray-200 dark:border-zinc-800">
                                    <div class="text-sm font-bold text-gray-900 dark:text-white mb-1">
                                        {{ $t("tutorial.propagation_manual") }}
                                    </div>
                                    <p class="text-xs text-gray-500 dark:text-zinc-500">
                                        {{ $t("tutorial.propagation_manual_desc") }}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Step 5: Documentation & Tools -->
                    <div v-else-if="currentStep === 5" key="step5-tools" class="space-y-6">
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

                    <!-- Step 6: Finish -->
                    <div
                        v-else-if="currentStep === 6"
                        key="step6-finish"
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
            <v-card-actions
                class="shrink-0 flex justify-between bg-gray-50 px-4 py-4 pb-[max(1rem,env(safe-area-inset-bottom))] dark:bg-zinc-950/50 sm:px-6 sm:py-6"
            >
                <button
                    v-if="currentStep > 1 && currentStep < totalSteps"
                    type="button"
                    class="px-6 py-2.5 rounded-xl border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 font-semibold text-sm shadow-sm transition-all hover:bg-gray-50 dark:hover:bg-zinc-700 hover:border-blue-400 dark:hover:border-blue-500"
                    @click="previousStep"
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
                        @click="finishTutorial"
                    >
                        {{ $t("tutorial.finish_setup") }}
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
            <div class="w-full h-full flex flex-col justify-between">
                <transition name="fade-slide" mode="out-in">
                    <!-- Step 1: Welcome -->
                    <div
                        v-if="currentStep === 1"
                        key="page-step1"
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

                    <!-- Step 2: Choose Connection Mode -->
                    <div v-else-if="currentStep === 2" key="page-step2-mode" class="space-y-8 py-8">
                        <div class="text-center space-y-2">
                            <h2 class="text-3xl font-black text-gray-900 dark:text-white">
                                {{ $t("tutorial.connect") }}
                            </h2>
                            <p class="text-lg text-gray-600 dark:text-zinc-400 max-w-2xl mx-auto">
                                {{ $t("tutorial.connect_desc_page") }}
                            </p>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-6xl mx-auto">
                            <button
                                type="button"
                                class="text-left flex flex-col gap-4 p-8 rounded-3xl bg-blue-500/5 dark:bg-blue-500/10 border-2 transition-all hover:scale-[1.02]"
                                :class="[
                                    connectionMode === 'discovery'
                                        ? 'border-blue-500 ring-2 ring-blue-500/30'
                                        : 'border-blue-500/20 hover:border-blue-500',
                                ]"
                                :disabled="savingDiscovery"
                                @click="useDiscoveryMode"
                            >
                                <v-icon icon="mdi-radar" color="blue" size="56"></v-icon>
                                <div class="font-bold text-xl text-gray-900 dark:text-white">
                                    {{ $t("tutorial.mode_discovery_title") }}
                                </div>
                                <div class="text-sm text-gray-600 dark:text-zinc-400">
                                    {{ $t("tutorial.mode_discovery_desc") }}
                                </div>
                                <v-progress-circular
                                    v-if="savingDiscovery"
                                    indeterminate
                                    size="20"
                                    width="2"
                                ></v-progress-circular>
                            </button>

                            <button
                                type="button"
                                class="text-left flex flex-col gap-4 p-8 rounded-3xl bg-emerald-500/5 dark:bg-emerald-500/10 border-2 transition-all hover:scale-[1.02]"
                                :class="[
                                    connectionMode === 'local'
                                        ? 'border-emerald-500 ring-2 ring-emerald-500/30'
                                        : 'border-emerald-500/20 hover:border-emerald-500',
                                ]"
                                :disabled="addingLocal || reloadingReticulum"
                                @click="useLocalMode"
                            >
                                <v-icon icon="mdi-lan" color="emerald" size="56"></v-icon>
                                <div class="font-bold text-xl text-gray-900 dark:text-white">
                                    {{ $t("tutorial.mode_local_title") }}
                                </div>
                                <div class="text-sm text-gray-600 dark:text-zinc-400">
                                    {{ $t("tutorial.mode_local_desc") }}
                                </div>
                                <v-progress-circular
                                    v-if="addingLocal || reloadingReticulum"
                                    indeterminate
                                    size="20"
                                    width="2"
                                ></v-progress-circular>
                            </button>

                            <button
                                type="button"
                                class="text-left flex flex-col gap-4 p-8 rounded-3xl bg-gray-100/50 dark:bg-zinc-800/40 border-2 transition-all hover:scale-[1.02]"
                                :class="[
                                    connectionMode === 'manual'
                                        ? 'border-gray-500 ring-2 ring-gray-500/30'
                                        : 'border-gray-300 dark:border-zinc-700 hover:border-gray-500',
                                ]"
                                @click="useManualMode"
                            >
                                <v-icon icon="mdi-cog-outline" color="gray" size="56"></v-icon>
                                <div class="font-bold text-xl text-gray-900 dark:text-white">
                                    {{ $t("tutorial.mode_manual_title") }}
                                </div>
                                <div class="text-sm text-gray-600 dark:text-zinc-400">
                                    {{ $t("tutorial.mode_manual_desc") }}
                                </div>
                            </button>
                        </div>

                        <p class="text-xs text-center text-gray-400 dark:text-zinc-500">
                            {{ $t("tutorial.mode_change_later") }}
                        </p>
                    </div>

                    <!-- Step 3: Bootstrap Selection -->
                    <div v-else-if="currentStep === 3" key="page-step3-bootstrap" class="space-y-6 py-8">
                        <div class="text-center space-y-2">
                            <h2 class="text-3xl font-black text-gray-900 dark:text-white">
                                {{ $t("tutorial.bootstrap_title") }}
                            </h2>
                            <p class="text-lg text-gray-600 dark:text-zinc-400 max-w-3xl mx-auto">
                                {{ $t("tutorial.bootstrap_desc_page") }}
                            </p>
                        </div>

                        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-6xl mx-auto">
                            <div
                                v-if="sortedDiscoveredInterfaces.length > 0"
                                class="bg-emerald-500/5 dark:bg-emerald-500/10 rounded-[1.5rem] p-5 border border-emerald-500/20"
                            >
                                <div class="flex items-center gap-2 mb-4">
                                    <v-icon icon="mdi-radar" color="emerald" size="22"></v-icon>
                                    <span class="text-base font-bold text-gray-900 dark:text-white">{{
                                        $t("tutorial.bootstrap_discovered")
                                    }}</span>
                                </div>
                                <div class="space-y-2 max-h-[480px] overflow-y-auto pr-2 custom-scrollbar">
                                    <label
                                        v-for="iface in sortedDiscoveredInterfaces"
                                        :key="iface.discovery_hash || iface.name"
                                        class="flex items-center gap-3 p-3 bg-white dark:bg-zinc-800 rounded-xl border cursor-pointer transition-all"
                                        :class="[
                                            isBootstrapSelected(`disc:${iface.discovery_hash || iface.name}`)
                                                ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20'
                                                : 'border-gray-100 dark:border-zinc-700 hover:border-emerald-400',
                                        ]"
                                    >
                                        <input
                                            type="checkbox"
                                            class="w-4 h-4 accent-emerald-500"
                                            :checked="isBootstrapSelected(`disc:${iface.discovery_hash || iface.name}`)"
                                            @change="toggleBootstrap(`disc:${iface.discovery_hash || iface.name}`)"
                                        />
                                        <MaterialDesignIcon
                                            :icon-name="getDiscoveryIcon(iface)"
                                            class="w-5 h-5 text-emerald-500 shrink-0"
                                        />
                                        <div class="flex-1 min-w-0">
                                            <div class="text-sm font-bold text-gray-900 dark:text-white truncate">
                                                {{ iface.name }}
                                            </div>
                                            <div
                                                class="text-[10px] font-mono text-gray-500 dark:text-zinc-400 truncate"
                                            >
                                                <span v-if="iface.reachable_on"
                                                    >{{ iface.reachable_on
                                                    }}<span v-if="iface.port">:{{ iface.port }}</span></span
                                                >
                                                <span v-else>{{ iface.type }}</span>
                                                <span class="ml-2 capitalize">{{ iface.status }}</span>
                                            </div>
                                        </div>
                                    </label>
                                </div>
                            </div>

                            <div
                                class="bg-gray-50 dark:bg-zinc-900 rounded-[1.5rem] p-5 border border-gray-100 dark:border-zinc-800"
                                :class="[sortedDiscoveredInterfaces.length === 0 ? 'lg:col-span-2' : '']"
                            >
                                <div class="flex items-center gap-2 mb-4">
                                    <v-icon icon="mdi-web" color="blue" size="22"></v-icon>
                                    <span class="text-base font-bold text-gray-900 dark:text-white">{{
                                        $t("tutorial.bootstrap_community")
                                    }}</span>
                                </div>
                                <div class="space-y-2 max-h-[480px] overflow-y-auto pr-2 custom-scrollbar">
                                    <label
                                        v-for="iface in communityInterfaces"
                                        :key="iface.name"
                                        class="flex items-center gap-3 p-3 bg-white dark:bg-zinc-800 rounded-xl border cursor-pointer transition-all"
                                        :class="[
                                            isBootstrapSelected(`comm:${iface.name}`)
                                                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                                                : 'border-gray-100 dark:border-zinc-700 hover:border-blue-400',
                                        ]"
                                    >
                                        <input
                                            type="checkbox"
                                            class="w-4 h-4 accent-blue-500"
                                            :checked="isBootstrapSelected(`comm:${iface.name}`)"
                                            @change="toggleBootstrap(`comm:${iface.name}`)"
                                        />
                                        <v-icon icon="mdi-server-network" color="blue" size="22"></v-icon>
                                        <div class="flex-1 min-w-0">
                                            <div class="text-sm font-bold text-gray-900 dark:text-white truncate">
                                                {{ iface.name }}
                                            </div>
                                            <div
                                                class="text-[10px] font-mono text-gray-500 dark:text-zinc-400 truncate"
                                            >
                                                {{ iface.target_host
                                                }}<span v-if="iface.target_port">:{{ iface.target_port }}</span>
                                            </div>
                                        </div>
                                        <span
                                            v-if="iface.online"
                                            class="text-[9px] font-bold text-green-500 uppercase tracking-widest shrink-0"
                                            >{{ $t("tutorial.online") }}</span
                                        >
                                    </label>
                                    <div v-if="loadingInterfaces" class="flex justify-center py-3">
                                        <v-progress-circular indeterminate color="blue" size="24"></v-progress-circular>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div
                            class="flex flex-col sm:flex-row items-center justify-between gap-4 max-w-6xl mx-auto pt-4"
                        >
                            <p class="text-sm text-gray-500 dark:text-zinc-500">
                                {{
                                    $t("tutorial.bootstrap_selected", {
                                        count: selectedBootstrapCount,
                                    })
                                }}
                            </p>
                            <div class="flex gap-3">
                                <button
                                    type="button"
                                    class="px-6 py-3 text-sm rounded-xl border-2 border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 font-bold transition-all hover:bg-gray-50 dark:hover:bg-zinc-700"
                                    @click="skipBootstraps"
                                >
                                    {{ $t("tutorial.bootstrap_skip") }}
                                </button>
                                <button
                                    type="button"
                                    class="px-8 py-3 text-sm rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold shadow-lg transition-all"
                                    :disabled="addingBootstraps || reloadingReticulum || selectedBootstrapCount === 0"
                                    @click="confirmBootstraps"
                                >
                                    <v-progress-circular
                                        v-if="addingBootstraps || reloadingReticulum"
                                        indeterminate
                                        size="16"
                                        width="2"
                                        class="mr-2"
                                    ></v-progress-circular>
                                    {{ $t("tutorial.bootstrap_confirm") }}
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Step 4: Propagation Mode -->
                    <div v-else-if="currentStep === 4" key="page-step4-prop" class="space-y-8 py-12">
                        <div class="text-center space-y-4">
                            <h2 class="text-4xl font-black text-gray-900 dark:text-white">
                                {{ $t("tutorial.propagation") }}
                            </h2>
                            <p class="text-xl text-gray-600 dark:text-zinc-400 max-w-2xl mx-auto">
                                {{ $t("tutorial.propagation_desc") }}
                            </p>
                        </div>

                        <div class="flex flex-col items-center gap-10 py-12">
                            <div
                                class="bg-blue-500/10 dark:bg-blue-500/20 p-12 rounded-[3rem] text-center space-y-8 border border-blue-500/20 max-w-2xl shadow-2xl"
                            >
                                <v-icon icon="mdi-server-network" color="blue" size="80"></v-icon>
                                <div class="text-3xl font-black text-gray-900 dark:text-white">
                                    {{ $t("tutorial.propagation_question") }}
                                </div>
                                <p class="text-xl text-gray-600 dark:text-zinc-400">
                                    {{ $t("tutorial.propagation_auto") }}
                                </p>
                                <div class="flex flex-col gap-4 pt-4">
                                    <button
                                        type="button"
                                        class="px-10 py-4 text-xl rounded-2xl bg-blue-600 hover:bg-blue-500 text-white font-black shadow-xl transition-all transform hover:scale-105"
                                        :disabled="savingPropagation"
                                        @click="enableAutoPropagation"
                                    >
                                        <v-progress-circular
                                            v-if="savingPropagation"
                                            indeterminate
                                            size="24"
                                            width="3"
                                            class="mr-3"
                                        ></v-progress-circular>
                                        {{ $t("tutorial.propagation_enable_auto") }}
                                    </button>
                                    <button
                                        type="button"
                                        class="px-10 py-4 text-xl rounded-2xl border-2 border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 font-black shadow-lg transition-all transform hover:scale-105"
                                        @click="nextStep"
                                    >
                                        {{ $t("tutorial.propagation_skip_auto") }}
                                    </button>
                                </div>
                                <div class="mt-8 pt-8 border-t-2 border-gray-200 dark:border-zinc-800">
                                    <div class="text-xl font-bold text-gray-900 dark:text-white mb-2">
                                        {{ $t("tutorial.propagation_manual") }}
                                    </div>
                                    <p class="text-base text-gray-500 dark:text-zinc-500">
                                        {{ $t("tutorial.propagation_manual_desc") }}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Step 5: Documentation & Tools -->
                    <div v-else-if="currentStep === 5" key="page-step5-tools" class="space-y-8 py-10">
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

                    <!-- Step 6: Finish -->
                    <div
                        v-else-if="currentStep === 6"
                        key="page-step6-finish"
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
                        @click="previousStep"
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
                            @click="finishTutorial"
                        >
                            {{ $t("tutorial.finish_setup") }}
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
            totalSteps: 6,
            logoUrl,
            communityInterfaces: [],
            loadingInterfaces: false,
            interfaceAddedViaTutorial: false,
            connectionMode: null,
            selectedBootstrapKeys: [],
            addedBootstrapKeys: [],
            addingBootstraps: false,
            addingLocal: false,
            reloadingReticulum: false,
            discoveredInterfaces: [],
            discoveredActive: [],
            loadingDiscovered: false,
            savingDiscovery: false,
            savingPropagation: false,
            discoveryInterval: null,
            markingSeen: false,
            windowWidth: typeof window !== "undefined" ? window.innerWidth : 1024,
        };
    },
    computed: {
        isPage() {
            return this.$route?.meta?.isPage === true;
        },
        dialogFullscreen() {
            return this.windowWidth < 768;
        },
        config() {
            return GlobalState.config;
        },
        sortedDiscoveredInterfaces() {
            return [...this.discoveredInterfaces].sort((a, b) => (b.last_heard || 0) - (a.last_heard || 0));
        },
        interfacesWithLocation() {
            return this.discoveredInterfaces.filter((iface) => iface.latitude != null && iface.longitude != null);
        },
        bootstrapCommunityKey() {
            return (iface) => `comm:${iface.name}`;
        },
        bootstrapDiscoveredKey() {
            return (iface) => `disc:${iface.discovery_hash || iface.name}`;
        },
        hasAnyBootstrapsToShow() {
            return this.communityInterfaces.length > 0 || this.sortedDiscoveredInterfaces.length > 0;
        },
        selectedBootstrapCount() {
            return this.selectedBootstrapKeys.length;
        },
    },
    beforeUnmount() {
        if (this.onWindowResize) {
            window.removeEventListener("resize", this.onWindowResize);
        }
        if (this.discoveryInterval) {
            clearInterval(this.discoveryInterval);
        }
    },
    mounted() {
        this.onWindowResize = () => {
            this.windowWidth = window.innerWidth;
        };
        window.addEventListener("resize", this.onWindowResize, { passive: true });
        if (this.isPage) {
            this.loadCommunityInterfaces();
            this.loadDiscoveredInterfaces();
            this.discoveryInterval = setInterval(() => {
                this.loadDiscoveredInterfaces();
            }, 5000);
        }
    },
    methods: {
        async toggleTheme() {
            const newTheme = this.config.theme === "dark" ? "light" : "dark";
            try {
                await window.api.patch("/api/v1/config", {
                    theme: newTheme,
                });
                GlobalState.config.theme = newTheme;
            } catch (e) {
                console.error("Failed to update theme:", e);
            }
        },
        async onLanguageChange(langCode) {
            try {
                await window.api.patch("/api/v1/config", {
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
            this.connectionMode = null;
            this.selectedBootstrapKeys = [];
            this.addedBootstrapKeys = [];
            await this.loadCommunityInterfaces();
            await this.loadDiscoveredInterfaces();

            if (this.discoveryInterval) {
                clearInterval(this.discoveryInterval);
            }
            this.discoveryInterval = setInterval(() => {
                this.loadDiscoveredInterfaces();
            }, 5000);
        },
        async loadCommunityInterfaces() {
            this.loadingInterfaces = true;
            try {
                const response = await window.api.get("/api/v1/community-interfaces");
                this.communityInterfaces = response.data.interfaces;
            } catch (e) {
                console.error("Failed to load community interfaces:", e);
            } finally {
                this.loadingInterfaces = false;
            }
        },
        async loadDiscoveredInterfaces() {
            this.loadingDiscovered = true;
            try {
                const response = await window.api.get(`/api/v1/reticulum/discovered-interfaces`);
                this.discoveredInterfaces = response.data?.interfaces ?? [];
                this.discoveredActive = response.data?.active ?? [];
            } catch (e) {
                console.error("Failed to load discovered interfaces:", e);
            } finally {
                this.loadingDiscovered = false;
            }
        },
        async reloadReticulum() {
            this.reloadingReticulum = true;
            try {
                await window.api.post("/api/v1/reticulum/reload");
                GlobalState.hasPendingInterfaceChanges = false;
                if (GlobalState.modifiedInterfaceNames && GlobalState.modifiedInterfaceNames.clear) {
                    GlobalState.modifiedInterfaceNames.clear();
                }
                return true;
            } catch (e) {
                console.error("Failed to reload Reticulum:", e);
                ToastUtils.error(this.$t("tutorial.failed_reload_rns"));
                return false;
            } finally {
                this.reloadingReticulum = false;
            }
        },
        async useDiscoveryMode() {
            this.savingDiscovery = true;
            try {
                const payload = {
                    discover_interfaces: true,
                    autoconnect_discovered_interfaces: 3,
                };
                await window.api.patch(`/api/v1/reticulum/discovery`, payload);
                ToastUtils.success(this.$t("tutorial.discovery_enabled"));
                this.connectionMode = "discovery";
                this.currentStep = 3;
            } catch (e) {
                console.error("Failed to enable discovery:", e);
                ToastUtils.error(this.$t("tutorial.failed_enable_discovery"));
            } finally {
                this.savingDiscovery = false;
            }
        },
        async useLocalMode() {
            if (this.addingLocal) return;
            this.addingLocal = true;
            try {
                await window.api.post("/api/v1/reticulum/interfaces/add", {
                    name: "Local Network",
                    type: "AutoInterface",
                    enabled: true,
                });
                this.interfaceAddedViaTutorial = true;
                GlobalState.hasPendingInterfaceChanges = true;
                GlobalState.modifiedInterfaceNames.add("Local Network");
                ToastUtils.success(this.$t("tutorial.local_added"));
                await this.reloadReticulum();
                this.connectionMode = "local";
                this.currentStep = 4;
            } catch (e) {
                console.error("Failed to add AutoInterface:", e);
                ToastUtils.error(e.response?.data?.message || this.$t("tutorial.failed_add_local"));
            } finally {
                this.addingLocal = false;
            }
        },
        useManualMode() {
            this.connectionMode = "manual";
            this.currentStep = 4;
        },
        isBootstrapSelected(key) {
            return this.selectedBootstrapKeys.includes(key);
        },
        toggleBootstrap(key) {
            const idx = this.selectedBootstrapKeys.indexOf(key);
            if (idx >= 0) {
                this.selectedBootstrapKeys.splice(idx, 1);
            } else {
                this.selectedBootstrapKeys.push(key);
            }
        },
        buildBootstrapPayload(item) {
            if (item.kind === "discovered") {
                const iface = item.iface;
                const payload = {
                    name: iface.name || `Discovered ${iface.discovery_hash || ""}`.trim(),
                    type: iface.type === "BackboneInterface" ? "TCPClientInterface" : iface.type,
                    enabled: true,
                };
                if (iface.reachable_on) {
                    payload.target_host = iface.reachable_on;
                }
                if (iface.port) {
                    payload.target_port = iface.port;
                }
                return payload;
            }
            const iface = item.iface;
            return {
                name: iface.name,
                type: iface.type,
                target_host: iface.target_host,
                target_port: iface.target_port,
                enabled: true,
            };
        },
        async confirmBootstraps() {
            if (this.addingBootstraps) return;
            if (this.selectedBootstrapKeys.length === 0) {
                ToastUtils.warning(this.$t("tutorial.bootstrap_pick_at_least_one"));
                return;
            }
            this.addingBootstraps = true;
            const items = [];
            for (const key of this.selectedBootstrapKeys) {
                if (this.addedBootstrapKeys.includes(key)) continue;
                if (key.startsWith("comm:")) {
                    const iface = this.communityInterfaces.find((c) => `comm:${c.name}` === key);
                    if (iface) items.push({ key, kind: "community", iface });
                } else if (key.startsWith("disc:")) {
                    const iface = this.discoveredInterfaces.find((d) => `disc:${d.discovery_hash || d.name}` === key);
                    if (iface) items.push({ key, kind: "discovered", iface });
                }
            }
            let added = 0;
            for (const item of items) {
                try {
                    const payload = this.buildBootstrapPayload(item);
                    if (!payload.target_host) continue;
                    await window.api.post("/api/v1/reticulum/interfaces/add", payload);
                    this.addedBootstrapKeys.push(item.key);
                    GlobalState.hasPendingInterfaceChanges = true;
                    GlobalState.modifiedInterfaceNames.add(payload.name);
                    added += 1;
                } catch (e) {
                    console.error("Failed to add bootstrap interface:", e);
                    ToastUtils.error(e.response?.data?.message || this.$t("tutorial.failed_add_bootstrap"));
                }
            }
            if (added > 0) {
                this.interfaceAddedViaTutorial = true;
                ToastUtils.success(this.$t("tutorial.bootstrap_added", { count: added }));
                await this.reloadReticulum();
            }
            this.addingBootstraps = false;
            this.currentStep = 4;
        },
        skipBootstraps() {
            this.currentStep = 4;
        },
        async enableAutoPropagation() {
            this.savingPropagation = true;
            try {
                await window.api.patch("/api/v1/config", {
                    lxmf_preferred_propagation_node_auto_select: true,
                });
                ToastUtils.success("Auto-propagation enabled");
                this.nextStep();
            } catch (e) {
                console.error("Failed to enable auto-propagation:", e);
                ToastUtils.error("Failed to enable auto-propagation");
            } finally {
                this.savingPropagation = false;
            }
        },
        getDiscoveryIcon(iface) {
            switch (iface.type) {
                case "AutoInterface":
                    return "home-automation";
                case "RNodeInterface":
                    return iface.port && iface.port.toString().startsWith("tcp://") ? "lan-connect" : "radio-tower";
                case "RNodeMultiInterface":
                    return "access-point-network";
                case "TCPClientInterface":
                case "BackboneInterface":
                    return "lan-connect";
                case "TCPServerInterface":
                    return "lan";
                case "UDPInterface":
                    return "wan";
                case "SerialInterface":
                    return "usb-port";
                case "KISSInterface":
                case "AX25KISSInterface":
                    return "antenna";
                case "I2PInterface":
                    return "eye";
                case "PipeInterface":
                    return "pipe";
                default:
                    return "server-network";
            }
        },
        formatLastHeard(ts) {
            const seconds = Math.max(0, Math.floor(Date.now() / 1000 - ts));
            if (seconds < 60) return `${seconds}s ago`;
            if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
            if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
            return `${Math.floor(seconds / 86400)}d ago`;
        },
        copyToClipboard(text, label) {
            if (!text) return;
            navigator.clipboard.writeText(text);
            ToastUtils.success(`${label} copied to clipboard`);
        },
        mapAllDiscovered() {
            if (!this.isPage) {
                this.visible = false;
            }
            this.$router.push({
                name: "map",
                query: { view: "discovered" },
            });
        },
        async selectCommunityInterface(iface) {
            try {
                await window.api.post("/api/v1/reticulum/interfaces/add", {
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
            if (this.currentStep >= this.totalSteps) return;
            if (this.currentStep === 2 && this.connectionMode !== "discovery") {
                this.currentStep = 4;
                return;
            }
            this.currentStep++;
        },
        previousStep() {
            if (this.currentStep <= 1) return;
            if (this.currentStep === 4 && this.connectionMode !== "discovery") {
                this.currentStep = 2;
                return;
            }
            this.currentStep--;
        },
        async skipTutorial() {
            if (await DialogUtils.confirm(this.$t("tutorial.skip_confirm"))) {
                this.visible = false;
                this.markSeen();
            }
        },
        async markSeen() {
            if (this.markingSeen) return;
            this.markingSeen = true;
            try {
                await window.api.post("/api/v1/app/tutorial/seen");
            } catch (e) {
                console.error("Failed to mark tutorial as seen:", e);
            } finally {
                this.markingSeen = false;
            }
        },
        async finishTutorial() {
            if (GlobalState.hasPendingInterfaceChanges) {
                await this.reloadReticulum();
            }
            this.visible = false;
            this.markSeen();
            if (this.interfaceAddedViaTutorial) {
                ToastUtils.success(this.$t("tutorial.ready_finished"));
            }
        },
        async onVisibleUpdate(val) {
            if (!val) {
                // if closed by clicking away or programmatically, mark as seen
                this.markSeen();
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

@media (max-width: 767px) {
    .tutorial-dialog .v-overlay__content {
        border-radius: 0 !important;
        max-height: 100dvh !important;
        margin: 0 !important;
        width: 100% !important;
    }
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
