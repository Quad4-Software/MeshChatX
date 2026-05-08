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
            class="flex min-h-0 flex-1 flex-col bg-white dark:bg-zinc-950 border-0 overflow-hidden relative h-full max-h-dvh"
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
                        currentStep === step ? 'flex-2' : 'flex-1',
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
                        <div
                            v-if="migrationOffer && migrationOffer.show_choice"
                            class="w-full max-w-xl mx-auto p-4 rounded-2xl border border-amber-200 dark:border-amber-900/50 bg-amber-50/90 dark:bg-amber-950/40 text-left space-y-3"
                        >
                            <div class="font-semibold text-amber-950 dark:text-amber-100">
                                {{ $t("tutorial.migration_title") }}
                            </div>
                            <p class="text-sm text-amber-950/90 dark:text-amber-100/90">
                                {{ $t("tutorial.migration_desc") }}
                            </p>
                            <div class="flex flex-col sm:flex-row gap-2 justify-stretch sm:justify-end">
                                <button
                                    type="button"
                                    class="tutorial-action-btn tutorial-action-btn-primary"
                                    :disabled="migrationBusy"
                                    @click="migrationMigrate"
                                >
                                    {{ $t("tutorial.migration_migrate") }}
                                </button>
                                <button
                                    type="button"
                                    class="tutorial-action-btn tutorial-action-btn-secondary"
                                    :disabled="migrationBusy"
                                    @click="migrationFresh"
                                >
                                    {{ $t("tutorial.migration_fresh") }}
                                </button>
                            </div>
                            <p v-if="migrationBusy" class="text-xs text-center text-gray-600 dark:text-zinc-400">
                                {{ $t("tutorial.migration_working") }}
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

                    <!-- Step 2: Identity Setup -->
                    <div v-else-if="currentStep === 2" key="step2-identity" class="space-y-6">
                        <div class="text-center space-y-2">
                            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">
                                {{ $t("tutorial.identity_title") }}
                            </h2>
                            <p class="text-gray-600 dark:text-zinc-400 text-base">
                                {{ $t("tutorial.identity_desc") }}
                            </p>
                        </div>
                        <input
                            ref="identityImportFileInput"
                            type="file"
                            accept=".identity,.bin,.key"
                            class="hidden"
                            @change="onIdentityImportFileChange"
                        />
                        <div class="grid grid-cols-1 gap-3">
                            <button
                                type="button"
                                class="text-left flex items-start gap-4 p-5 rounded-2xl border-2 transition-all"
                                :class="
                                    identityMode === 'new'
                                        ? 'border-blue-500 bg-blue-500/5'
                                        : 'border-gray-200 dark:border-zinc-700 hover:border-blue-400'
                                "
                                @click="identityMode = 'new'"
                            >
                                <v-icon icon="mdi-account-plus-outline" color="blue" size="34"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">
                                        {{ $t("tutorial.identity_new") }}
                                    </div>
                                    <div class="text-sm text-gray-600 dark:text-zinc-400">
                                        {{ $t("tutorial.identity_new_desc") }}
                                    </div>
                                </div>
                            </button>
                            <button
                                type="button"
                                class="text-left flex items-start gap-4 p-5 rounded-2xl border-2 transition-all"
                                :class="
                                    identityMode === 'import'
                                        ? 'border-blue-500 bg-blue-500/5'
                                        : 'border-gray-200 dark:border-zinc-700 hover:border-blue-400'
                                "
                                @click="identityMode = 'import'"
                            >
                                <v-icon icon="mdi-file-import-outline" color="indigo" size="34"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">
                                        {{ $t("tutorial.identity_import") }}
                                    </div>
                                    <div class="text-sm text-gray-600 dark:text-zinc-400">
                                        {{ $t("tutorial.identity_import_desc") }}
                                    </div>
                                </div>
                            </button>
                        </div>
                        <div class="rounded-2xl border border-gray-200 dark:border-zinc-700 p-4 space-y-3">
                            <label class="block text-sm font-semibold text-gray-700 dark:text-zinc-200">
                                {{ $t("tutorial.identity_set_name") }}
                            </label>
                            <input
                                v-model="identityName"
                                type="text"
                                :placeholder="defaultUsername"
                                class="w-full rounded-xl border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm text-gray-900 dark:text-zinc-100"
                            />
                            <div
                                v-if="identityMode === 'import'"
                                class="space-y-3 pt-2 border-t border-gray-200 dark:border-zinc-800"
                            >
                                <button
                                    type="button"
                                    class="tutorial-action-btn tutorial-action-btn-secondary w-full justify-center"
                                    @click="$refs.identityImportFileInput?.click()"
                                >
                                    {{
                                        identityImportFile
                                            ? identityImportFile.name
                                            : $t("tutorial.identity_upload_file")
                                    }}
                                </button>
                                <textarea
                                    v-model="identityImportBase32"
                                    rows="3"
                                    class="w-full rounded-xl border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-xs font-mono text-gray-900 dark:text-zinc-100"
                                    :placeholder="$t('tutorial.identity_base32_placeholder')"
                                />
                            </div>
                            <p v-if="identityImportError" class="text-sm text-red-600 dark:text-red-400">
                                {{ identityImportError }}
                            </p>
                        </div>
                    </div>

                    <!-- Step 3: Choose Connection Mode -->
                    <div v-else-if="currentStep === 3" key="step3-mode" class="space-y-6">
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

                    <!-- Step 4: Bootstrap Selection -->
                    <div v-else-if="currentStep === 4" key="step4-bootstrap" class="space-y-6">
                        <div class="text-center space-y-2">
                            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">
                                {{ $t("tutorial.bootstrap_title") }}
                            </h2>
                            <p class="text-gray-600 dark:text-zinc-400 text-sm">
                                {{ $t("tutorial.bootstrap_desc") }}
                            </p>
                            <div class="flex flex-col items-center gap-2 pt-1">
                                <button
                                    type="button"
                                    class="inline-flex items-center gap-2 rounded-xl border border-blue-500/30 bg-blue-500/10 px-4 py-2 text-xs font-semibold text-blue-700 transition-colors hover:bg-blue-500/15 dark:text-blue-300 dark:hover:bg-blue-500/20 disabled:opacity-60"
                                    :disabled="loadingInterfaces || loadingDiscovered || pickingRandomBootstraps"
                                    @click="pickRandomTcpBootstraps"
                                >
                                    <v-progress-circular
                                        v-if="pickingRandomBootstraps"
                                        indeterminate
                                        size="16"
                                        width="2"
                                    />
                                    <v-icon v-else icon="mdi-shuffle-variant" size="18" />
                                    {{ $t("tutorial.bootstrap_pick_random_tcp") }}
                                </button>
                                <div
                                    v-if="bootstrapSelectedLabels.length > 0"
                                    class="w-full max-w-md rounded-xl border border-gray-200/90 bg-gray-50/80 px-3 py-2 text-left dark:border-zinc-700 dark:bg-zinc-900/50"
                                >
                                    <div
                                        class="text-[10px] font-bold uppercase tracking-wide text-gray-500 dark:text-zinc-400"
                                    >
                                        {{ $t("tutorial.bootstrap_selected_nodes_heading") }}
                                    </div>
                                    <ul class="mt-1 space-y-0.5 text-xs text-gray-800 dark:text-zinc-200">
                                        <li
                                            v-for="(label, idx) in bootstrapSelectedLabels"
                                            :key="selectedBootstrapKeys[idx]"
                                        >
                                            {{ label }}
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </div>

                        <div
                            class="flex items-start gap-3 sm:gap-4 rounded-2xl border border-gray-200 dark:border-zinc-700 bg-white/80 dark:bg-zinc-900/60 p-3.5 sm:p-4"
                        >
                            <div class="shrink-0 pr-0.5 pt-0.5 sm:pt-1 sm:pr-1 flex items-start">
                                <Toggle
                                    v-model="defaultBootstrapOnly"
                                    @update:model-value="persistDefaultBootstrapOnly"
                                />
                            </div>
                            <div class="min-w-0 flex-1 pl-0.5 sm:pl-0 sm:pt-0.5">
                                <div class="text-sm font-semibold text-gray-900 dark:text-white leading-snug">
                                    {{ $t("tutorial.bootstrap_only_label") }}
                                </div>
                                <p class="text-xs text-gray-500 dark:text-zinc-400 mt-1.5 leading-relaxed">
                                    {{ $t("tutorial.bootstrap_only_hint") }}
                                </p>
                            </div>
                        </div>

                        <div class="space-y-4">
                            <div
                                v-if="hasAnyBootstrapsToShow"
                                class="w-full max-w-6xl mx-auto flex items-center gap-2 border-0 border-b border-gray-200/90 dark:border-zinc-600/90 py-1.5"
                            >
                                <v-icon icon="mdi-magnify" size="20" class="shrink-0 text-gray-400" />
                                <input
                                    v-model="bootstrapListSearch"
                                    type="search"
                                    autocomplete="off"
                                    :placeholder="$t('tutorial.bootstrap_search_placeholder')"
                                    class="min-w-0 flex-1 border-0 bg-transparent p-0 text-sm text-gray-900 shadow-none ring-0 outline-hidden focus:ring-0 dark:text-zinc-100 placeholder:text-gray-400 dark:placeholder:text-zinc-500"
                                />
                                <button
                                    v-if="bootstrapListSearch"
                                    type="button"
                                    class="shrink-0 rounded p-1 text-gray-400 transition-colors hover:text-gray-700 dark:hover:text-zinc-200"
                                    :title="$t('tutorial.bootstrap_search_clear')"
                                    :aria-label="$t('tutorial.bootstrap_search_clear')"
                                    @click="bootstrapListSearch = ''"
                                >
                                    <v-icon icon="mdi-close" size="18" />
                                </button>
                            </div>

                            <div
                                v-if="sortedDiscoveredInterfaces.length > 0"
                                class="h-fit min-w-0 bg-emerald-500/5 dark:bg-emerald-500/10 rounded-3xl border border-emerald-500/20"
                            >
                                <button
                                    type="button"
                                    class="flex w-full items-center justify-between gap-2 p-4 text-left sm:px-4"
                                    :aria-expanded="bootstrapDiscoveredSectionOpen"
                                    @click="bootstrapDiscoveredSectionOpen = !bootstrapDiscoveredSectionOpen"
                                >
                                    <div class="flex min-w-0 items-center gap-2 text-sm">
                                        <MaterialDesignIcon
                                            :icon-name="bootstrapDiscoveredSectionOpen ? 'chevron-up' : 'chevron-down'"
                                            class="size-4 shrink-0 text-gray-500"
                                        />
                                        <v-icon icon="mdi-radar" color="emerald"></v-icon>
                                        <span class="font-bold text-gray-900 dark:text-white">{{
                                            $t("tutorial.bootstrap_discovered")
                                        }}</span>
                                    </div>
                                </button>
                                <div v-show="bootstrapDiscoveredSectionOpen" class="px-4 pb-4">
                                    <p
                                        v-if="
                                            bootstrapListSearch &&
                                            sortedDiscoveredInterfaces.length > 0 &&
                                            filteredDiscoveredForBootstrap.length === 0
                                        "
                                        class="text-xs text-gray-500 dark:text-zinc-400"
                                    >
                                        {{ $t("tutorial.bootstrap_search_no_match") }}
                                    </p>
                                    <div
                                        v-else
                                        class="space-y-2 max-h-[260px] overflow-y-auto pr-2 pt-1 custom-scrollbar"
                                    >
                                        <label
                                            v-for="iface in filteredDiscoveredForBootstrap"
                                            :key="iface.discovery_hash || iface.name"
                                            class="flex cursor-pointer items-center gap-3 rounded-xl border bg-white p-3 transition-all dark:bg-zinc-800"
                                            :class="[
                                                isBootstrapSelected(`disc:${iface.discovery_hash || iface.name}`)
                                                    ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20'
                                                    : 'border-gray-100 dark:border-zinc-700 hover:border-emerald-400',
                                            ]"
                                        >
                                            <input
                                                type="checkbox"
                                                class="h-4 w-4 accent-emerald-500"
                                                :checked="
                                                    isBootstrapSelected(`disc:${iface.discovery_hash || iface.name}`)
                                                "
                                                @change="toggleBootstrap(`disc:${iface.discovery_hash || iface.name}`)"
                                            />
                                            <MaterialDesignIcon
                                                :icon-name="getDiscoveryIcon(iface)"
                                                class="h-5 w-5 shrink-0 text-emerald-500"
                                            />
                                            <div class="min-w-0 flex-1">
                                                <div class="truncate text-sm font-bold text-gray-900 dark:text-white">
                                                    {{ iface.name }}
                                                </div>
                                                <div
                                                    class="truncate font-mono text-[10px] text-gray-500 dark:text-zinc-400"
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
                            </div>

                            <div
                                class="h-fit min-w-0 rounded-3xl border border-gray-100 bg-gray-50 p-0 dark:border-zinc-800 dark:bg-zinc-900"
                            >
                                <div class="flex items-center justify-between gap-2 p-4 pr-2 sm:px-4">
                                    <button
                                        type="button"
                                        class="flex min-w-0 flex-1 items-center gap-2 text-left text-sm"
                                        :aria-expanded="bootstrapCommunitySectionOpen"
                                        @click="bootstrapCommunitySectionOpen = !bootstrapCommunitySectionOpen"
                                    >
                                        <MaterialDesignIcon
                                            :icon-name="bootstrapCommunitySectionOpen ? 'chevron-up' : 'chevron-down'"
                                            class="size-4 shrink-0 text-gray-500"
                                        />
                                        <v-icon icon="mdi-web" color="blue"></v-icon>
                                        <span class="font-bold text-gray-900 dark:text-white">{{
                                            $t("tutorial.bootstrap_community")
                                        }}</span>
                                    </button>
                                    <button
                                        type="button"
                                        class="shrink-0 rounded-lg p-1.5 text-gray-500 transition-colors hover:bg-gray-100 hover:text-blue-600 disabled:opacity-50 dark:hover:bg-zinc-800 dark:hover:text-blue-400"
                                        :disabled="refreshingCommunityPresets"
                                        :title="$t('interfaces.community_presets_refresh')"
                                        :aria-label="$t('interfaces.community_presets_refresh')"
                                        @click.stop="refreshCommunityPresets"
                                    >
                                        <v-icon
                                            icon="mdi-refresh"
                                            size="20"
                                            :class="{ 'animate-spin': refreshingCommunityPresets }"
                                        />
                                    </button>
                                </div>
                                <div v-show="bootstrapCommunitySectionOpen" class="px-4 pb-4">
                                    <p
                                        v-if="
                                            bootstrapListSearch &&
                                            communityInterfaces.length > 0 &&
                                            filteredCommunityForBootstrap.length === 0
                                        "
                                        class="text-xs text-gray-500 dark:text-zinc-400"
                                    >
                                        {{ $t("tutorial.bootstrap_search_no_match") }}
                                    </p>
                                    <div
                                        v-else
                                        class="space-y-2 max-h-[260px] overflow-y-auto pr-2 pt-1 custom-scrollbar"
                                    >
                                        <label
                                            v-for="iface in filteredCommunityForBootstrap"
                                            :key="iface.name"
                                            class="flex cursor-pointer items-center gap-3 rounded-xl border border-gray-100 bg-white p-3 transition-all dark:border-zinc-700 dark:bg-zinc-800"
                                            :class="[
                                                isBootstrapSelected(`comm:${iface.name}`)
                                                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                                                    : 'hover:border-blue-400',
                                            ]"
                                        >
                                            <input
                                                type="checkbox"
                                                class="h-4 w-4 accent-blue-500"
                                                :checked="isBootstrapSelected(`comm:${iface.name}`)"
                                                @change="toggleBootstrap(`comm:${iface.name}`)"
                                            />
                                            <v-icon icon="mdi-server-network" color="blue" size="20"></v-icon>
                                            <div class="min-w-0 flex-1">
                                                <div class="truncate text-sm font-bold text-gray-900 dark:text-white">
                                                    {{ iface.name }}
                                                </div>
                                                <div
                                                    class="truncate font-mono text-[10px] text-gray-500 dark:text-zinc-400"
                                                >
                                                    {{ iface.target_host
                                                    }}<span v-if="iface.target_port">:{{ iface.target_port }}</span>
                                                </div>
                                            </div>
                                            <span
                                                v-if="iface.online"
                                                class="shrink-0 text-[9px] font-bold uppercase tracking-widest text-green-500"
                                                >{{ $t("tutorial.online") }}</span
                                            >
                                        </label>
                                        <div v-if="loadingInterfaces" class="flex justify-center py-3">
                                            <v-progress-circular
                                                indeterminate
                                                color="blue"
                                                size="24"
                                            ></v-progress-circular>
                                        </div>
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
                                        class="tutorial-action-btn tutorial-action-btn-secondary"
                                        @click="skipBootstraps"
                                    >
                                        {{ $t("tutorial.bootstrap_skip") }}
                                    </button>
                                    <button
                                        type="button"
                                        class="tutorial-action-btn tutorial-action-btn-success"
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

                    <!-- Step 5: Propagation Mode -->
                    <div v-else-if="currentStep === 5" key="step5-prop" class="space-y-6">
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
                                class="bg-blue-500/10 dark:bg-blue-500/20 p-6 rounded-4xl text-center space-y-4 border border-blue-500/20 max-w-md"
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
                                        class="tutorial-action-btn tutorial-action-btn-primary w-full"
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
                                        class="tutorial-action-btn tutorial-action-btn-secondary w-full"
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

                    <!-- Step 6: Learn & Create -->
                    <div v-else-if="currentStep === 6" key="step6-tools" class="space-y-6">
                        <div class="text-center space-y-2">
                            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">
                                {{ $t("tutorial.learn_create") }}
                            </h2>
                            <p class="text-gray-600 dark:text-zinc-400">
                                {{ $t("tutorial.learn_create_desc") }}
                            </p>
                        </div>

                        <div class="space-y-6">
                            <div class="flex w-full flex-col gap-4 max-w-xl mx-auto">
                                <div
                                    class="flex w-full items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 touch-manipulation"
                                >
                                    <v-icon icon="mdi-book-open-variant" color="blue" size="32"></v-icon>
                                    <div class="min-w-0 flex-1">
                                        <div class="font-bold text-gray-900 dark:text-white">
                                            {{ $t("tutorial.documentation") }}
                                        </div>
                                        <div class="text-sm text-gray-900 dark:text-white mb-2">
                                            {{ $t("tutorial.documentation_desc") }}
                                        </div>
                                        <div class="flex flex-wrap gap-2">
                                            <a
                                                href="/meshchatx-docs/index.html"
                                                target="_blank"
                                                class="px-3 py-1 text-[10px] rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold shadow-xs transition-all inline-block"
                                            >
                                                {{ $t("tutorial.meshchatx_docs") }}
                                            </a>
                                            <a
                                                :href="reticulumBundledDocsUrl"
                                                target="_blank"
                                                class="px-3 py-1 text-[10px] rounded-xl border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 font-semibold shadow-xs transition-all hover:bg-gray-50 dark:hover:bg-zinc-700 hover:border-blue-400 dark:hover:border-blue-500 inline-block"
                                            >
                                                {{ $t("tutorial.reticulum_docs") }}
                                            </a>
                                        </div>
                                    </div>
                                </div>

                                <div
                                    class="flex w-full items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 touch-manipulation"
                                >
                                    <v-icon icon="mdi-file-document-edit-outline" color="orange" size="32"></v-icon>
                                    <div class="min-w-0 flex-1">
                                        <div class="font-bold text-gray-900 dark:text-white">
                                            {{ $t("tutorial.micron_editor") }}
                                        </div>
                                        <div class="text-sm text-gray-900 dark:text-white mb-2">
                                            {{ $t("tutorial.micron_editor_desc") }}
                                        </div>
                                        <div class="flex flex-wrap gap-2">
                                            <button
                                                type="button"
                                                class="px-3 py-1 text-[10px] rounded-xl border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 font-semibold shadow-xs transition-all hover:bg-gray-50 dark:hover:bg-zinc-700 hover:border-blue-400 dark:hover:border-blue-500"
                                                @click="gotoRoute('micron-editor')"
                                            >
                                                {{ $t("tutorial.open_micron_editor") }}
                                            </button>
                                            <button
                                                type="button"
                                                class="px-3 py-1 text-[10px] rounded-xl border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 font-semibold shadow-xs transition-all hover:bg-gray-50 dark:hover:bg-zinc-700 hover:border-blue-400 dark:hover:border-blue-500"
                                                @click="gotoRoute('mesh-server')"
                                            >
                                                {{ $t("tutorial.open_mesh_server") }}
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                <div
                                    class="flex w-full cursor-pointer items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-colors hover:border-indigo-500 touch-manipulation min-h-[4.5rem]"
                                    role="button"
                                    tabindex="0"
                                    @click="gotoRoute('identities')"
                                    @keydown.enter="gotoRoute('identities')"
                                >
                                    <v-icon icon="mdi-account-multiple-outline" color="indigo" size="32"></v-icon>
                                    <div class="min-w-0 flex-1">
                                        <div class="font-bold text-gray-900 dark:text-white">
                                            {{ $t("tutorial.identities_card_title") }}
                                        </div>
                                        <div class="text-sm text-gray-600 dark:text-zinc-400">
                                            {{ $t("tutorial.identities_card_desc") }}
                                        </div>
                                    </div>
                                </div>

                                <div
                                    class="flex w-full cursor-pointer items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-colors hover:border-teal-500 touch-manipulation min-h-[4.5rem]"
                                    role="button"
                                    tabindex="0"
                                    @click="gotoRoute('archives')"
                                    @keydown.enter="gotoRoute('archives')"
                                >
                                    <v-icon icon="mdi-archive-outline" color="teal" size="32"></v-icon>
                                    <div>
                                        <div class="font-bold text-gray-900 dark:text-white">
                                            {{ $t("tutorial.archiver") }}
                                        </div>
                                        <div class="text-sm text-gray-900 dark:text-white">
                                            {{ $t("tutorial.archiver_desc") }}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <p
                                class="text-center text-[11px] font-semibold tracking-wide text-gray-600 dark:text-zinc-400 px-2"
                            >
                                {{ $t("tutorial.learn_create_more") }}
                            </p>

                            <div class="grid grid-cols-2 gap-2 max-w-xl mx-auto">
                                <div
                                    class="flex flex-col gap-1.5 rounded-xl border border-gray-100 bg-gray-50 p-2.5 dark:border-zinc-800 dark:bg-zinc-900 cursor-pointer hover:border-blue-500 transition-colors touch-manipulation min-h-[5.5rem]"
                                    role="button"
                                    tabindex="0"
                                    @click="gotoRoute('nomadnetwork')"
                                    @keydown.enter="gotoRoute('nomadnetwork')"
                                >
                                    <v-icon icon="mdi-earth" color="purple" size="22" class="shrink-0"></v-icon>
                                    <div class="min-w-0">
                                        <div class="font-bold text-gray-900 dark:text-white text-[11px] leading-tight">
                                            {{ $t("tutorial.paper_messages") }}
                                        </div>
                                        <div
                                            class="text-[9px] text-gray-600 dark:text-zinc-400 leading-snug line-clamp-3"
                                        >
                                            {{ $t("tutorial.paper_messages_desc") }}
                                        </div>
                                    </div>
                                </div>

                                <div
                                    class="flex flex-col gap-1.5 rounded-xl border border-gray-100 bg-gray-50 p-2.5 dark:border-zinc-800 dark:bg-zinc-900 cursor-pointer hover:border-blue-500 transition-colors touch-manipulation min-h-[5.5rem]"
                                    role="button"
                                    tabindex="0"
                                    @click="gotoRoute('messages')"
                                    @keydown.enter="gotoRoute('messages')"
                                >
                                    <v-icon
                                        icon="mdi-message-text-outline"
                                        color="green"
                                        size="22"
                                        class="shrink-0"
                                    ></v-icon>
                                    <div class="min-w-0">
                                        <div class="font-bold text-gray-900 dark:text-white text-[11px] leading-tight">
                                            {{ $t("tutorial.send_messages") }}
                                        </div>
                                        <div
                                            class="text-[9px] text-gray-600 dark:text-zinc-400 leading-snug line-clamp-3"
                                        >
                                            {{ $t("tutorial.send_messages_desc") }}
                                        </div>
                                    </div>
                                </div>

                                <div
                                    class="flex flex-col gap-1.5 rounded-xl border border-gray-100 bg-gray-50 p-2.5 dark:border-zinc-800 dark:bg-zinc-900 cursor-pointer hover:border-blue-500 transition-colors touch-manipulation min-h-[5.5rem]"
                                    role="button"
                                    tabindex="0"
                                    @click="gotoRoute('network-visualiser')"
                                    @keydown.enter="gotoRoute('network-visualiser')"
                                >
                                    <v-icon icon="mdi-hub" color="teal" size="22" class="shrink-0"></v-icon>
                                    <div class="min-w-0">
                                        <div class="font-bold text-gray-900 dark:text-white text-[11px] leading-tight">
                                            {{ $t("tutorial.explore_nodes") }}
                                        </div>
                                        <div
                                            class="text-[9px] text-gray-600 dark:text-zinc-400 leading-snug line-clamp-3"
                                        >
                                            {{ $t("tutorial.explore_nodes_desc") }}
                                        </div>
                                    </div>
                                </div>

                                <div
                                    class="flex flex-col gap-1.5 rounded-xl border border-gray-100 bg-gray-50 p-2.5 dark:border-zinc-800 dark:bg-zinc-900 cursor-pointer hover:border-blue-500 transition-colors touch-manipulation min-h-[5.5rem]"
                                    role="button"
                                    tabindex="0"
                                    @click="gotoRoute('call')"
                                    @keydown.enter="gotoRoute('call')"
                                >
                                    <v-icon
                                        icon="mdi-phone-in-talk-outline"
                                        color="red"
                                        size="22"
                                        class="shrink-0"
                                    ></v-icon>
                                    <div class="min-w-0">
                                        <div class="font-bold text-gray-900 dark:text-white text-[11px] leading-tight">
                                            {{ $t("tutorial.voice_calls") }}
                                        </div>
                                        <div
                                            class="text-[9px] text-gray-600 dark:text-zinc-400 leading-snug line-clamp-3"
                                        >
                                            {{ $t("tutorial.voice_calls_desc") }}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Step 7: Finish -->
                    <div
                        v-else-if="currentStep === 7"
                        key="step7-finish"
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
                    class="tutorial-action-btn tutorial-action-btn-secondary"
                    @click="previousStep"
                >
                    {{ $t("tutorial.back") }}
                </button>
                <div v-else></div>

                <div class="flex gap-3">
                    <button
                        v-if="currentStep < totalSteps"
                        type="button"
                        class="tutorial-action-btn tutorial-action-btn-secondary"
                        @click="skipTutorial"
                    >
                        {{ $t("tutorial.skip") }}
                    </button>

                    <button
                        v-if="currentStep < totalSteps"
                        type="button"
                        class="tutorial-action-btn tutorial-action-btn-primary"
                        :disabled="currentStep === 2 && identityImportInProgress"
                        @click="handlePrimaryAction"
                    >
                        {{ $t("tutorial.next") }}
                    </button>

                    <button
                        v-else
                        type="button"
                        class="tutorial-action-btn tutorial-action-btn-success"
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
                    currentStep === step ? 'flex-2' : 'flex-1',
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
                        <div
                            v-if="migrationOffer && migrationOffer.show_choice"
                            class="w-full max-w-2xl mx-auto p-5 rounded-2xl border border-amber-200 dark:border-amber-900/50 bg-amber-50/90 dark:bg-amber-950/40 text-left space-y-3"
                        >
                            <div class="font-semibold text-amber-950 dark:text-amber-100">
                                {{ $t("tutorial.migration_title") }}
                            </div>
                            <p class="text-sm text-amber-950/90 dark:text-amber-100/90">
                                {{ $t("tutorial.migration_desc") }}
                            </p>
                            <div class="flex flex-col sm:flex-row gap-2 justify-stretch sm:justify-end">
                                <button
                                    type="button"
                                    class="tutorial-action-btn tutorial-action-btn-primary"
                                    :disabled="migrationBusy"
                                    @click="migrationMigrate"
                                >
                                    {{ $t("tutorial.migration_migrate") }}
                                </button>
                                <button
                                    type="button"
                                    class="tutorial-action-btn tutorial-action-btn-secondary"
                                    :disabled="migrationBusy"
                                    @click="migrationFresh"
                                >
                                    {{ $t("tutorial.migration_fresh") }}
                                </button>
                            </div>
                            <p v-if="migrationBusy" class="text-xs text-center text-gray-600 dark:text-zinc-400">
                                {{ $t("tutorial.migration_working") }}
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

                    <!-- Step 2: Identity Setup -->
                    <div v-else-if="currentStep === 2" key="page-step2-identity" class="space-y-8 py-8">
                        <div class="text-center space-y-3">
                            <h2 class="text-3xl font-black text-gray-900 dark:text-white">
                                {{ $t("tutorial.identity_title") }}
                            </h2>
                            <p class="text-lg text-gray-600 dark:text-zinc-400 max-w-3xl mx-auto">
                                {{ $t("tutorial.identity_desc_page") }}
                            </p>
                        </div>
                        <input
                            ref="identityImportFileInput"
                            type="file"
                            accept=".identity,.bin,.key"
                            class="hidden"
                            @change="onIdentityImportFileChange"
                        />
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-5xl mx-auto">
                            <button
                                type="button"
                                class="text-left flex items-start gap-5 p-7 rounded-3xl border-2 transition-all"
                                :class="
                                    identityMode === 'new'
                                        ? 'border-blue-500 bg-blue-500/5'
                                        : 'border-gray-200 dark:border-zinc-700 hover:border-blue-400'
                                "
                                @click="identityMode = 'new'"
                            >
                                <v-icon icon="mdi-account-plus-outline" color="blue" size="52"></v-icon>
                                <div>
                                    <div class="text-xl font-bold text-gray-900 dark:text-white">
                                        {{ $t("tutorial.identity_new") }}
                                    </div>
                                    <div class="text-sm text-gray-600 dark:text-zinc-400 mt-1">
                                        {{ $t("tutorial.identity_new_desc") }}
                                    </div>
                                </div>
                            </button>
                            <button
                                type="button"
                                class="text-left flex items-start gap-5 p-7 rounded-3xl border-2 transition-all"
                                :class="
                                    identityMode === 'import'
                                        ? 'border-blue-500 bg-blue-500/5'
                                        : 'border-gray-200 dark:border-zinc-700 hover:border-blue-400'
                                "
                                @click="identityMode = 'import'"
                            >
                                <v-icon icon="mdi-file-import-outline" color="indigo" size="52"></v-icon>
                                <div>
                                    <div class="text-xl font-bold text-gray-900 dark:text-white">
                                        {{ $t("tutorial.identity_import") }}
                                    </div>
                                    <div class="text-sm text-gray-600 dark:text-zinc-400 mt-1">
                                        {{ $t("tutorial.identity_import_desc") }}
                                    </div>
                                </div>
                            </button>
                        </div>
                        <div
                            class="max-w-4xl mx-auto rounded-3xl border border-gray-200 dark:border-zinc-700 p-6 space-y-4"
                        >
                            <label class="block text-base font-semibold text-gray-800 dark:text-zinc-100">
                                {{ $t("tutorial.identity_set_name") }}
                            </label>
                            <input
                                v-model="identityName"
                                type="text"
                                :placeholder="defaultUsername"
                                class="w-full rounded-xl border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-4 py-3 text-base text-gray-900 dark:text-zinc-100"
                            />
                            <div
                                v-if="identityMode === 'import'"
                                class="space-y-4 pt-3 border-t border-gray-200 dark:border-zinc-800"
                            >
                                <button
                                    type="button"
                                    class="tutorial-action-btn tutorial-action-btn-secondary w-full justify-center"
                                    @click="$refs.identityImportFileInput?.click()"
                                >
                                    {{
                                        identityImportFile
                                            ? identityImportFile.name
                                            : $t("tutorial.identity_upload_file")
                                    }}
                                </button>
                                <textarea
                                    v-model="identityImportBase32"
                                    rows="4"
                                    class="w-full rounded-xl border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-4 py-3 text-sm font-mono text-gray-900 dark:text-zinc-100"
                                    :placeholder="$t('tutorial.identity_base32_placeholder')"
                                />
                            </div>
                            <p v-if="identityImportError" class="text-sm text-red-600 dark:text-red-400">
                                {{ identityImportError }}
                            </p>
                        </div>
                    </div>

                    <!-- Step 3: Choose Connection Mode -->
                    <div v-else-if="currentStep === 3" key="page-step3-mode" class="space-y-8 py-8">
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

                    <!-- Step 4: Bootstrap Selection -->
                    <div v-else-if="currentStep === 4" key="page-step4-bootstrap" class="space-y-6 py-8">
                        <div class="text-center space-y-2">
                            <h2 class="text-3xl font-black text-gray-900 dark:text-white">
                                {{ $t("tutorial.bootstrap_title") }}
                            </h2>
                            <p class="text-lg text-gray-600 dark:text-zinc-400 max-w-3xl mx-auto">
                                {{ $t("tutorial.bootstrap_desc_page") }}
                            </p>
                            <div class="flex flex-col items-center gap-3 pt-2">
                                <button
                                    type="button"
                                    class="inline-flex items-center gap-2 rounded-xl border-2 border-blue-500/30 bg-blue-500/10 px-5 py-2.5 text-sm font-semibold text-blue-700 transition-colors hover:bg-blue-500/15 dark:text-blue-300 dark:hover:bg-blue-500/20 disabled:opacity-60"
                                    :disabled="loadingInterfaces || loadingDiscovered || pickingRandomBootstraps"
                                    @click="pickRandomTcpBootstraps"
                                >
                                    <v-progress-circular
                                        v-if="pickingRandomBootstraps"
                                        indeterminate
                                        size="18"
                                        width="2"
                                    />
                                    <v-icon v-else icon="mdi-shuffle-variant" size="20" />
                                    {{ $t("tutorial.bootstrap_pick_random_tcp") }}
                                </button>
                                <div
                                    v-if="bootstrapSelectedLabels.length > 0"
                                    class="w-full max-w-xl rounded-xl border border-gray-200/90 bg-gray-50/80 px-4 py-3 text-left dark:border-zinc-700 dark:bg-zinc-900/50"
                                >
                                    <div
                                        class="text-xs font-bold uppercase tracking-wide text-gray-500 dark:text-zinc-400"
                                    >
                                        {{ $t("tutorial.bootstrap_selected_nodes_heading") }}
                                    </div>
                                    <ul class="mt-1.5 space-y-1 text-sm text-gray-800 dark:text-zinc-200">
                                        <li
                                            v-for="(label, idx) in bootstrapSelectedLabels"
                                            :key="selectedBootstrapKeys[idx]"
                                        >
                                            {{ label }}
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </div>

                        <div
                            class="flex items-start gap-3 sm:gap-5 max-w-3xl mx-auto rounded-2xl border border-gray-200 dark:border-zinc-700 bg-white/80 dark:bg-zinc-900/60 p-3.5 sm:p-5"
                        >
                            <div class="shrink-0 pr-0.5 pt-0.5 sm:pt-1.5 sm:pr-1 flex items-start">
                                <Toggle
                                    v-model="defaultBootstrapOnly"
                                    @update:model-value="persistDefaultBootstrapOnly"
                                />
                            </div>
                            <div class="min-w-0 flex-1 pl-0.5 sm:pl-0 sm:pt-0.5">
                                <div
                                    class="text-sm sm:text-base font-semibold text-gray-900 dark:text-white leading-snug"
                                >
                                    {{ $t("tutorial.bootstrap_only_label") }}
                                </div>
                                <p
                                    class="text-xs sm:text-sm text-gray-500 dark:text-zinc-400 mt-1.5 sm:mt-2 leading-relaxed"
                                >
                                    {{ $t("tutorial.bootstrap_only_hint") }}
                                </p>
                            </div>
                        </div>

                        <div
                            v-if="hasAnyBootstrapsToShow"
                            class="flex w-full max-w-6xl mx-auto items-center gap-2 border-0 border-b border-gray-200/90 dark:border-zinc-600/90 py-1.5"
                        >
                            <v-icon icon="mdi-magnify" size="22" class="shrink-0 text-gray-400" />
                            <input
                                v-model="bootstrapListSearch"
                                type="search"
                                autocomplete="off"
                                :placeholder="$t('tutorial.bootstrap_search_placeholder')"
                                class="min-w-0 flex-1 border-0 bg-transparent p-0 text-base text-gray-900 shadow-none ring-0 outline-hidden focus:ring-0 dark:text-zinc-100 placeholder:text-gray-400 dark:placeholder:text-zinc-500"
                            />
                            <button
                                v-if="bootstrapListSearch"
                                type="button"
                                class="shrink-0 rounded p-1.5 text-gray-400 transition-colors hover:text-gray-700 dark:hover:text-zinc-200"
                                :title="$t('tutorial.bootstrap_search_clear')"
                                :aria-label="$t('tutorial.bootstrap_search_clear')"
                                @click="bootstrapListSearch = ''"
                            >
                                <v-icon icon="mdi-close" size="20" />
                            </button>
                        </div>

                        <div class="grid max-w-6xl mx-auto grid-cols-1 items-start gap-6 lg:grid-cols-2">
                            <div
                                v-if="sortedDiscoveredInterfaces.length > 0"
                                class="h-fit min-w-0 bg-emerald-500/5 dark:bg-emerald-500/10 rounded-3xl border border-emerald-500/20"
                            >
                                <button
                                    type="button"
                                    class="flex w-full items-center justify-between gap-2 p-4 text-left sm:px-5"
                                    :aria-expanded="bootstrapDiscoveredSectionOpen"
                                    @click="bootstrapDiscoveredSectionOpen = !bootstrapDiscoveredSectionOpen"
                                >
                                    <div class="flex min-w-0 items-center gap-2.5 text-base">
                                        <MaterialDesignIcon
                                            :icon-name="bootstrapDiscoveredSectionOpen ? 'chevron-up' : 'chevron-down'"
                                            class="size-4 shrink-0 text-gray-500"
                                        />
                                        <v-icon icon="mdi-radar" color="emerald" size="22"></v-icon>
                                        <span class="font-bold text-gray-900 dark:text-white">{{
                                            $t("tutorial.bootstrap_discovered")
                                        }}</span>
                                    </div>
                                </button>
                                <div v-show="bootstrapDiscoveredSectionOpen" class="px-4 pb-5 sm:px-5">
                                    <p
                                        v-if="
                                            bootstrapListSearch &&
                                            sortedDiscoveredInterfaces.length > 0 &&
                                            filteredDiscoveredForBootstrap.length === 0
                                        "
                                        class="text-sm text-gray-500 dark:text-zinc-400"
                                    >
                                        {{ $t("tutorial.bootstrap_search_no_match") }}
                                    </p>
                                    <div
                                        v-else
                                        class="max-h-[480px] space-y-2 overflow-y-auto pr-2 pt-1 custom-scrollbar"
                                    >
                                        <label
                                            v-for="iface in filteredDiscoveredForBootstrap"
                                            :key="iface.discovery_hash || iface.name"
                                            class="flex cursor-pointer items-center gap-3 rounded-xl border border-gray-100 bg-white p-3 transition-all dark:border-zinc-700 dark:bg-zinc-800"
                                            :class="[
                                                isBootstrapSelected(`disc:${iface.discovery_hash || iface.name}`)
                                                    ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20'
                                                    : 'hover:border-emerald-400',
                                            ]"
                                        >
                                            <input
                                                type="checkbox"
                                                class="h-4 w-4 accent-emerald-500"
                                                :checked="
                                                    isBootstrapSelected(`disc:${iface.discovery_hash || iface.name}`)
                                                "
                                                @change="toggleBootstrap(`disc:${iface.discovery_hash || iface.name}`)"
                                            />
                                            <MaterialDesignIcon
                                                :icon-name="getDiscoveryIcon(iface)"
                                                class="h-5 w-5 shrink-0 text-emerald-500"
                                            />
                                            <div class="min-w-0 flex-1">
                                                <div class="truncate text-sm font-bold text-gray-900 dark:text-white">
                                                    {{ iface.name }}
                                                </div>
                                                <div
                                                    class="truncate font-mono text-[10px] text-gray-500 dark:text-zinc-400"
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
                            </div>

                            <div
                                class="h-fit min-w-0 rounded-3xl border border-gray-100 bg-gray-50 p-0 dark:border-zinc-800 dark:bg-zinc-900"
                                :class="[sortedDiscoveredInterfaces.length === 0 ? 'lg:col-span-2' : '']"
                            >
                                <div class="flex items-center justify-between gap-2 p-4 pr-2 sm:px-5">
                                    <button
                                        type="button"
                                        class="flex min-w-0 flex-1 items-center gap-2.5 text-left text-base"
                                        :aria-expanded="bootstrapCommunitySectionOpen"
                                        @click="bootstrapCommunitySectionOpen = !bootstrapCommunitySectionOpen"
                                    >
                                        <MaterialDesignIcon
                                            :icon-name="bootstrapCommunitySectionOpen ? 'chevron-up' : 'chevron-down'"
                                            class="size-4 shrink-0 text-gray-500"
                                        />
                                        <v-icon icon="mdi-web" color="blue" size="22"></v-icon>
                                        <span class="font-bold text-gray-900 dark:text-white">{{
                                            $t("tutorial.bootstrap_community")
                                        }}</span>
                                    </button>
                                    <button
                                        type="button"
                                        class="shrink-0 rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-100 hover:text-blue-600 disabled:opacity-50 dark:hover:bg-zinc-800 dark:hover:text-blue-400"
                                        :disabled="refreshingCommunityPresets"
                                        :title="$t('interfaces.community_presets_refresh')"
                                        :aria-label="$t('interfaces.community_presets_refresh')"
                                        @click.stop="refreshCommunityPresets"
                                    >
                                        <v-icon
                                            icon="mdi-refresh"
                                            size="22"
                                            :class="{ 'animate-spin': refreshingCommunityPresets }"
                                        />
                                    </button>
                                </div>
                                <div v-show="bootstrapCommunitySectionOpen" class="px-4 pb-5 sm:px-5">
                                    <p
                                        v-if="
                                            bootstrapListSearch &&
                                            communityInterfaces.length > 0 &&
                                            filteredCommunityForBootstrap.length === 0
                                        "
                                        class="text-sm text-gray-500 dark:text-zinc-400"
                                    >
                                        {{ $t("tutorial.bootstrap_search_no_match") }}
                                    </p>
                                    <div
                                        v-else
                                        class="max-h-[480px] space-y-2 overflow-y-auto pr-2 pt-1 custom-scrollbar"
                                    >
                                        <label
                                            v-for="iface in filteredCommunityForBootstrap"
                                            :key="iface.name"
                                            class="flex cursor-pointer items-center gap-3 rounded-xl border border-gray-100 bg-white p-3 transition-all dark:border-zinc-700 dark:bg-zinc-800"
                                            :class="[
                                                isBootstrapSelected(`comm:${iface.name}`)
                                                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                                                    : 'hover:border-blue-400',
                                            ]"
                                        >
                                            <input
                                                type="checkbox"
                                                class="h-4 w-4 accent-blue-500"
                                                :checked="isBootstrapSelected(`comm:${iface.name}`)"
                                                @change="toggleBootstrap(`comm:${iface.name}`)"
                                            />
                                            <v-icon icon="mdi-server-network" color="blue" size="22"></v-icon>
                                            <div class="min-w-0 flex-1">
                                                <div class="truncate text-sm font-bold text-gray-900 dark:text-white">
                                                    {{ iface.name }}
                                                </div>
                                                <div
                                                    class="truncate font-mono text-[10px] text-gray-500 dark:text-zinc-400"
                                                >
                                                    {{ iface.target_host
                                                    }}<span v-if="iface.target_port">:{{ iface.target_port }}</span>
                                                </div>
                                            </div>
                                            <span
                                                v-if="iface.online"
                                                class="shrink-0 text-[9px] font-bold uppercase tracking-widest text-green-500"
                                                >{{ $t("tutorial.online") }}</span
                                            >
                                        </label>
                                        <div v-if="loadingInterfaces" class="flex justify-center py-3">
                                            <v-progress-circular
                                                indeterminate
                                                color="blue"
                                                size="24"
                                            ></v-progress-circular>
                                        </div>
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
                                    class="tutorial-action-btn tutorial-action-btn-secondary"
                                    @click="skipBootstraps"
                                >
                                    {{ $t("tutorial.bootstrap_skip") }}
                                </button>
                                <button
                                    type="button"
                                    class="tutorial-action-btn tutorial-action-btn-success"
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

                    <!-- Step 5: Propagation Mode -->
                    <div v-else-if="currentStep === 5" key="page-step5-prop" class="space-y-8 py-12">
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
                                        class="tutorial-action-btn tutorial-action-btn-primary"
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
                                        class="tutorial-action-btn tutorial-action-btn-secondary"
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

                    <!-- Step 6: Learn & Create -->
                    <div v-else-if="currentStep === 6" key="page-step6-tools" class="space-y-8 py-10">
                        <div class="text-center space-y-4">
                            <h2 class="text-4xl font-black text-gray-900 dark:text-white">
                                {{ $t("tutorial.learn_create") }}
                            </h2>
                            <p class="text-xl text-gray-600 dark:text-zinc-400 max-w-2xl mx-auto">
                                {{ $t("tutorial.learn_create_desc_page") }}
                            </p>
                        </div>

                        <div class="space-y-8 px-2 sm:px-0">
                            <div class="flex w-full flex-col gap-5 max-w-2xl mx-auto">
                                <div
                                    class="flex w-full flex-col gap-4 rounded-3xl border border-gray-100 bg-gray-50 p-6 dark:border-zinc-800 dark:bg-zinc-900 sm:p-8 sm:rounded-[2rem] touch-manipulation"
                                >
                                    <div class="flex gap-4 sm:gap-5">
                                        <v-icon
                                            icon="mdi-book-open-variant"
                                            color="blue"
                                            size="56"
                                            class="shrink-0"
                                        ></v-icon>
                                        <div class="min-w-0 flex-1 text-left">
                                            <div
                                                class="text-xl font-bold text-gray-900 dark:text-white sm:text-2xl mb-2"
                                            >
                                                {{ $t("tutorial.documentation") }}
                                            </div>
                                            <p class="text-gray-700 dark:text-zinc-300 mb-6 text-base">
                                                {{ $t("tutorial.documentation_desc_page") }}
                                            </p>
                                            <div class="flex flex-col gap-3">
                                                <a
                                                    href="/meshchatx-docs/index.html"
                                                    target="_blank"
                                                    class="flex min-h-12 items-center justify-center rounded-xl bg-blue-600 px-4 py-3 text-base font-semibold text-white shadow-xs transition-all hover:bg-blue-500"
                                                >
                                                    {{ $t("tutorial.read_meshchatx_docs") }}
                                                </a>
                                                <a
                                                    :href="reticulumBundledDocsUrl"
                                                    target="_blank"
                                                    class="flex min-h-12 items-center justify-center rounded-xl border border-gray-300 bg-white px-4 py-3 text-base font-semibold text-gray-700 shadow-xs transition-all hover:border-blue-400 hover:bg-gray-50 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:border-blue-500 dark:hover:bg-zinc-700"
                                                >
                                                    {{ $t("tutorial.reticulum_manual") }}
                                                </a>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div
                                    class="flex w-full flex-col gap-4 rounded-3xl border border-gray-100 bg-gray-50 p-6 dark:border-zinc-800 dark:bg-zinc-900 sm:p-8 sm:rounded-[2rem] touch-manipulation"
                                >
                                    <div class="flex gap-4 sm:gap-5">
                                        <v-icon
                                            icon="mdi-file-document-edit-outline"
                                            color="orange"
                                            size="56"
                                            class="shrink-0"
                                        ></v-icon>
                                        <div class="min-w-0 flex-1 text-left">
                                            <div
                                                class="text-xl font-bold text-gray-900 dark:text-white sm:text-2xl mb-2"
                                            >
                                                {{ $t("tutorial.micron_editor") }}
                                            </div>
                                            <p class="text-gray-700 dark:text-zinc-300 mb-6 text-base">
                                                {{ $t("tutorial.micron_editor_desc_page") }}
                                            </p>
                                            <div class="flex flex-col gap-3">
                                                <div class="flex flex-col gap-3 sm:flex-row">
                                                    <button
                                                        type="button"
                                                        class="flex min-h-12 flex-1 items-center justify-center rounded-xl bg-orange-600 px-4 py-3 text-base font-semibold text-white transition-all hover:bg-orange-500"
                                                        @click="gotoRoute('micron-editor')"
                                                    >
                                                        {{ $t("tutorial.open_micron_editor") }}
                                                    </button>
                                                    <button
                                                        type="button"
                                                        class="flex min-h-12 flex-1 items-center justify-center rounded-xl border border-gray-300 bg-white px-4 py-3 text-base font-semibold text-gray-700 transition-all hover:bg-gray-50 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700"
                                                        @click="gotoRoute('mesh-server')"
                                                    >
                                                        {{ $t("tutorial.open_mesh_server") }}
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div
                                    class="flex w-full cursor-pointer flex-col gap-4 rounded-3xl border border-gray-100 bg-gray-50 p-6 transition-colors hover:border-indigo-500 dark:border-zinc-800 dark:bg-zinc-900 sm:p-8 sm:rounded-[2rem] touch-manipulation"
                                    role="button"
                                    tabindex="0"
                                    @click="gotoRoute('identities')"
                                    @keydown.enter="gotoRoute('identities')"
                                >
                                    <div class="flex gap-4 sm:gap-5">
                                        <v-icon
                                            icon="mdi-account-multiple-outline"
                                            color="indigo"
                                            size="56"
                                            class="shrink-0"
                                        ></v-icon>
                                        <div class="min-w-0 flex-1 text-left">
                                            <div
                                                class="text-xl font-bold text-gray-900 dark:text-white sm:text-2xl mb-2"
                                            >
                                                {{ $t("tutorial.identities_card_title") }}
                                            </div>
                                            <p class="text-gray-700 dark:text-zinc-300 text-base">
                                                {{ $t("tutorial.identities_card_desc_page") }}
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                <div
                                    class="flex w-full cursor-pointer flex-col gap-4 rounded-3xl border border-gray-100 bg-gray-50 p-6 transition-colors hover:border-teal-500 dark:border-zinc-800 dark:bg-zinc-900 sm:p-8 sm:rounded-[2rem] touch-manipulation min-h-[5rem]"
                                    role="button"
                                    tabindex="0"
                                    @click="gotoRoute('archives')"
                                    @keydown.enter="gotoRoute('archives')"
                                >
                                    <div class="flex gap-4 sm:gap-5">
                                        <v-icon
                                            icon="mdi-archive-outline"
                                            color="teal"
                                            size="56"
                                            class="shrink-0"
                                        ></v-icon>
                                        <div class="min-w-0 flex-1 text-left">
                                            <div
                                                class="text-xl font-bold text-gray-900 dark:text-white sm:text-2xl mb-2"
                                            >
                                                {{ $t("tutorial.archiver") }}
                                            </div>
                                            <p class="text-gray-700 dark:text-zinc-300 text-base">
                                                {{ $t("tutorial.archiver_desc_page") }}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <p class="text-center text-sm font-semibold text-gray-600 dark:text-zinc-400 px-2">
                                {{ $t("tutorial.learn_create_more") }}
                            </p>

                            <div class="grid grid-cols-2 gap-3 max-w-2xl mx-auto px-1 sm:px-0">
                                <div
                                    class="flex cursor-pointer flex-col gap-2 rounded-2xl border border-gray-100 bg-gray-50 p-3 dark:border-zinc-800 dark:bg-zinc-900 transition-colors hover:border-blue-500 touch-manipulation min-h-[6.5rem]"
                                    role="button"
                                    tabindex="0"
                                    @click="gotoRoute('nomadnetwork')"
                                    @keydown.enter="gotoRoute('nomadnetwork')"
                                >
                                    <v-icon icon="mdi-earth" color="purple" size="28" class="shrink-0"></v-icon>
                                    <div class="min-w-0">
                                        <div
                                            class="font-bold text-gray-900 dark:text-white text-xs sm:text-sm leading-tight"
                                        >
                                            {{ $t("tutorial.paper_messages") }}
                                        </div>
                                        <div
                                            class="text-[10px] sm:text-xs text-gray-600 dark:text-zinc-400 mt-1 leading-snug line-clamp-4"
                                        >
                                            {{ $t("tutorial.paper_messages_desc") }}
                                        </div>
                                    </div>
                                </div>

                                <div
                                    class="flex cursor-pointer flex-col gap-2 rounded-2xl border border-gray-100 bg-gray-50 p-3 dark:border-zinc-800 dark:bg-zinc-900 transition-colors hover:border-blue-500 touch-manipulation min-h-[6.5rem]"
                                    role="button"
                                    tabindex="0"
                                    @click="gotoRoute('messages')"
                                    @keydown.enter="gotoRoute('messages')"
                                >
                                    <v-icon
                                        icon="mdi-message-text-outline"
                                        color="green"
                                        size="28"
                                        class="shrink-0"
                                    ></v-icon>
                                    <div class="min-w-0">
                                        <div
                                            class="font-bold text-gray-900 dark:text-white text-xs sm:text-sm leading-tight"
                                        >
                                            {{ $t("tutorial.send_messages") }}
                                        </div>
                                        <div
                                            class="text-[10px] sm:text-xs text-gray-600 dark:text-zinc-400 mt-1 leading-snug line-clamp-4"
                                        >
                                            {{ $t("tutorial.send_messages_desc") }}
                                        </div>
                                    </div>
                                </div>

                                <div
                                    class="flex cursor-pointer flex-col gap-2 rounded-2xl border border-gray-100 bg-gray-50 p-3 dark:border-zinc-800 dark:bg-zinc-900 transition-colors hover:border-blue-500 touch-manipulation min-h-[6.5rem]"
                                    role="button"
                                    tabindex="0"
                                    @click="gotoRoute('network-visualiser')"
                                    @keydown.enter="gotoRoute('network-visualiser')"
                                >
                                    <v-icon icon="mdi-hub" color="teal" size="28" class="shrink-0"></v-icon>
                                    <div class="min-w-0">
                                        <div
                                            class="font-bold text-gray-900 dark:text-white text-xs sm:text-sm leading-tight"
                                        >
                                            {{ $t("tutorial.explore_nodes") }}
                                        </div>
                                        <div
                                            class="text-[10px] sm:text-xs text-gray-600 dark:text-zinc-400 mt-1 leading-snug line-clamp-4"
                                        >
                                            {{ $t("tutorial.explore_nodes_desc") }}
                                        </div>
                                    </div>
                                </div>

                                <div
                                    class="flex cursor-pointer flex-col gap-2 rounded-2xl border border-gray-100 bg-gray-50 p-3 dark:border-zinc-800 dark:bg-zinc-900 transition-colors hover:border-blue-500 touch-manipulation min-h-[6.5rem]"
                                    role="button"
                                    tabindex="0"
                                    @click="gotoRoute('call')"
                                    @keydown.enter="gotoRoute('call')"
                                >
                                    <v-icon
                                        icon="mdi-phone-in-talk-outline"
                                        color="red"
                                        size="28"
                                        class="shrink-0"
                                    ></v-icon>
                                    <div class="min-w-0">
                                        <div
                                            class="font-bold text-gray-900 dark:text-white text-xs sm:text-sm leading-tight"
                                        >
                                            {{ $t("tutorial.voice_calls") }}
                                        </div>
                                        <div
                                            class="text-[10px] sm:text-xs text-gray-600 dark:text-zinc-400 mt-1 leading-snug line-clamp-4"
                                        >
                                            {{ $t("tutorial.voice_calls_desc") }}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Step 7: Finish -->
                    <div
                        v-else-if="currentStep === 7"
                        key="page-step7-finish"
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
                        class="tutorial-action-btn tutorial-action-btn-secondary"
                        @click="previousStep"
                    >
                        {{ $t("tutorial.back") }}
                    </button>
                    <div v-else></div>

                    <div class="flex gap-4">
                        <button
                            v-if="currentStep < totalSteps"
                            type="button"
                            class="tutorial-action-btn tutorial-action-btn-secondary"
                            @click="skipTutorial"
                        >
                            {{ $t("tutorial.skip_setup") }}
                        </button>

                        <button
                            v-if="currentStep < totalSteps"
                            type="button"
                            class="tutorial-action-btn tutorial-action-btn-primary"
                            :disabled="currentStep === 2 && identityImportInProgress"
                            @click="handlePrimaryAction"
                        >
                            {{ $t("tutorial.continue") }}
                        </button>

                        <button
                            v-else
                            type="button"
                            class="tutorial-action-btn tutorial-action-btn-success"
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
import { bundledReticulumDocsUrl } from "../js/reticulumDocsEntryUrl.js";
import LanguageSelector from "./LanguageSelector.vue";
import MaterialDesignIcon from "./MaterialDesignIcon.vue";
import Toggle from "./forms/Toggle.vue";

export default {
    name: "TutorialModal",
    components: {
        LanguageSelector,
        MaterialDesignIcon,
        Toggle,
    },
    data() {
        return {
            visible: false,
            currentStep: 1,
            totalSteps: 7,
            logoUrl,
            identityMode: "new",
            identityName: "",
            identityImportBase32: "",
            identityImportFile: null,
            identityImportInProgress: false,
            identityImportError: "",
            identityImportedHash: null,
            originalIdentityHash: null,
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
            defaultBootstrapOnly: false,
            refreshingCommunityPresets: false,
            bootstrapListSearch: "",
            bootstrapDiscoveredSectionOpen: true,
            bootstrapCommunitySectionOpen: true,
            bootstrapAutoPickDone: false,
            pickingRandomBootstraps: false,
            migrationOffer: null,
            migrationBusy: false,
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
        filteredDiscoveredForBootstrap() {
            const list = this.sortedDiscoveredInterfaces;
            const q = (this.bootstrapListSearch || "").trim().toLowerCase();
            if (!q) {
                return list;
            }
            return list.filter((iface) => {
                const parts = [
                    iface.name,
                    iface.type,
                    iface.reachable_on,
                    String(iface.port ?? ""),
                    iface.status,
                    iface.discovery_hash,
                ].filter(Boolean);
                return parts.join(" ").toLowerCase().includes(q);
            });
        },
        filteredCommunityForBootstrap() {
            const list = this.communityInterfaces;
            const q = (this.bootstrapListSearch || "").trim().toLowerCase();
            if (!q) {
                return list;
            }
            return list.filter((iface) => {
                const parts = [iface.name, iface.target_host, String(iface.target_port ?? ""), iface.type].filter(
                    Boolean
                );
                return parts.join(" ").toLowerCase().includes(q);
            });
        },
        selectedBootstrapCount() {
            return this.selectedBootstrapKeys.length;
        },
        reticulumBundledDocsUrl() {
            return bundledReticulumDocsUrl(this.$i18n.locale);
        },
        defaultUsername() {
            return "Anonymous Peer";
        },
        hasIdentityImportInput() {
            return Boolean(this.identityImportFile || this.identityImportBase32.trim());
        },
        bootstrapSelectedLabels() {
            return this.selectedBootstrapKeys.map((k) => this.bootstrapDisplayLabelForKey(k)).filter(Boolean);
        },
    },
    watch: {
        communityInterfaces() {
            this.$nextTick(() => void this.maybeAutoPickBootstrapTcp());
        },
        discoveredInterfaces() {
            this.$nextTick(() => void this.maybeAutoPickBootstrapTcp());
        },
        currentStep(val) {
            if (val === 4) {
                this.$nextTick(() => void this.maybeAutoPickBootstrapTcp());
            }
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
            this.loadIdentitySetupDefaults();
            this.loadDiscoveryBootstrapDefaults();
            this.loadCommunityInterfaces();
            this.loadDiscoveredInterfaces();
            this.refreshMigrationOffer();
            this.discoveryInterval = setInterval(() => {
                this.loadDiscoveredInterfaces();
            }, 5000);
        }
    },
    methods: {
        resetIdentitySetupState() {
            this.identityMode = "new";
            this.identityName = "";
            this.identityImportBase32 = "";
            this.identityImportFile = null;
            this.identityImportError = "";
            this.identityImportInProgress = false;
            this.identityImportedHash = null;
            this.originalIdentityHash = null;
        },
        async loadIdentitySetupDefaults() {
            try {
                const [identitiesRes, configRes] = await Promise.all([
                    window.api.get("/api/v1/identities"),
                    window.api.get("/api/v1/config"),
                ]);
                const identities = identitiesRes.data?.identities ?? [];
                const currentIdentity = identities.find((item) => item.is_current);
                this.originalIdentityHash = currentIdentity?.hash || null;
                this.identityName = configRes.data?.config?.display_name || this.defaultUsername;
            } catch (e) {
                console.error("Failed to load identity setup defaults:", e);
                this.identityName = this.defaultUsername;
            }
        },
        onIdentityImportFileChange(event) {
            const files = event?.target?.files;
            this.identityImportFile = files?.[0] || null;
            this.identityImportError = "";
            if (event?.target) {
                event.target.value = "";
            }
        },
        async importIdentityFromFile(file, displayName) {
            const formData = new FormData();
            formData.append("file", file);
            if (displayName) {
                formData.append("display_name", displayName);
            }
            const response = await window.api.post("/api/v1/identity/restore", formData, {
                headers: { "Content-Type": "multipart/form-data" },
            });
            return response.data?.identity?.hash || null;
        },
        async importIdentityFromBase32(base32, displayName) {
            const payload = { base32 };
            if (displayName) {
                payload.display_name = displayName;
            }
            const response = await window.api.post("/api/v1/identity/restore", payload);
            return response.data?.identity?.hash || null;
        },
        async handleIdentityContinue() {
            if (this.identityImportInProgress) {
                return;
            }
            const trimmedName = this.identityName.trim() || this.defaultUsername;
            this.identityImportError = "";
            if (this.identityMode === "new") {
                try {
                    await window.api.patch("/api/v1/config", {
                        display_name: trimmedName,
                    });
                    GlobalState.config.display_name = trimmedName;
                    this.identityImportedHash = null;
                    this.currentStep = 3;
                } catch (e) {
                    this.identityImportError =
                        e.response?.data?.message || this.$t("tutorial.identity_name_update_failed");
                }
                return;
            }
            if (!this.hasIdentityImportInput) {
                this.identityImportError = this.$t("tutorial.identity_import_required");
                return;
            }
            this.identityImportInProgress = true;
            try {
                let importedHash = null;
                if (this.identityImportFile) {
                    importedHash = await this.importIdentityFromFile(this.identityImportFile, trimmedName);
                    this.identityImportFile = null;
                } else {
                    importedHash = await this.importIdentityFromBase32(this.identityImportBase32.trim(), trimmedName);
                    this.identityImportBase32 = "";
                }
                if (!importedHash) {
                    throw new Error("Missing imported identity hash");
                }
                this.identityImportedHash = importedHash;
                this.currentStep = 3;
            } catch (e) {
                this.identityImportError = e.response?.data?.message || this.$t("tutorial.identity_import_failed");
            } finally {
                this.identityImportInProgress = false;
            }
        },
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
            this.resetIdentitySetupState();
            this.interfaceAddedViaTutorial = false;
            this.connectionMode = null;
            this.selectedBootstrapKeys = [];
            this.addedBootstrapKeys = [];
            this.bootstrapListSearch = "";
            this.bootstrapDiscoveredSectionOpen = true;
            this.bootstrapCommunitySectionOpen = true;
            this.bootstrapAutoPickDone = false;
            await this.refreshMigrationOffer();
            await this.loadIdentitySetupDefaults();
            await this.loadDiscoveryBootstrapDefaults();
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
        async refreshCommunityPresets() {
            if (this.refreshingCommunityPresets) return;
            this.refreshingCommunityPresets = true;
            try {
                const r = await window.api.post("/api/v1/community-interfaces/refresh", {});
                const n = r.data?.count ?? 0;
                ToastUtils.success(this.$t("interfaces.community_presets_refreshed", { count: n }));
                await this.loadCommunityInterfaces();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("interfaces.community_presets_refresh_failed"));
                console.error(e);
            } finally {
                this.refreshingCommunityPresets = false;
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
        async refreshMigrationOffer() {
            this.migrationOffer = null;
            try {
                const response = await window.api.get("/api/v1/app/info");
                const m = response.data?.app_info?.migration;
                if (m && m.show_choice) {
                    this.migrationOffer = m;
                }
            } catch (e) {
                console.error("Failed to load migration status:", e);
            }
        },
        async migrationMigrate() {
            if (this.migrationBusy || !this.migrationOffer) return;
            this.migrationBusy = true;
            try {
                await window.api.post("/api/v1/setup/storage-migration", { action: "migrate" });
                ToastUtils.success(this.$t("tutorial.migration_done_restart"));
                if (window.electron && typeof window.electron.relaunch === "function") {
                    await window.electron.relaunch();
                }
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("tutorial.migration_failed"));
                console.error(e);
            } finally {
                this.migrationBusy = false;
            }
        },
        async migrationFresh() {
            if (this.migrationBusy || !this.migrationOffer) return;
            this.migrationBusy = true;
            try {
                await window.api.post("/api/v1/setup/storage-migration", { action: "fresh" });
                ToastUtils.success(this.$t("tutorial.migration_done_restart"));
                if (window.electron && typeof window.electron.relaunch === "function") {
                    await window.electron.relaunch();
                }
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("tutorial.migration_failed"));
                console.error(e);
            } finally {
                this.migrationBusy = false;
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
                    default_bootstrap_only: true,
                };
                await window.api.patch(`/api/v1/reticulum/discovery`, payload);
                this.defaultBootstrapOnly = true;
                ToastUtils.success(this.$t("tutorial.discovery_enabled"));
                this.connectionMode = "discovery";
                this.currentStep = 4;
                this.bootstrapListSearch = "";
                this.bootstrapDiscoveredSectionOpen = true;
                this.bootstrapCommunitySectionOpen = true;
                await this.loadCommunityInterfaces();
                await this.loadDiscoveredInterfaces();
                await this.maybeAutoPickBootstrapTcp();
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
                this.currentStep = 5;
            } catch (e) {
                console.error("Failed to add AutoInterface:", e);
                ToastUtils.error(e.response?.data?.message || this.$t("tutorial.failed_add_local"));
            } finally {
                this.addingLocal = false;
            }
        },
        useManualMode() {
            this.connectionMode = "manual";
            this.currentStep = 5;
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
        bootstrapDisplayLabelForKey(key) {
            if (!key) {
                return "";
            }
            if (key.startsWith("comm:")) {
                const name = key.slice(5);
                const iface = this.communityInterfaces.find((c) => c.name === name);
                return iface?.name || name;
            }
            if (key.startsWith("disc:")) {
                const suffix = key.slice(5);
                const iface = this.discoveredInterfaces.find((d) => String(d.discovery_hash || d.name) === suffix);
                return iface?.name || suffix;
            }
            return key;
        },
        communityBootstrapExcludedFromRandom(iface) {
            const name = String(iface.name || "");
            const desc = String(iface.description || "");
            const host = String(iface.target_host || "").trim();
            const hay = `${name} ${desc}`.toLowerCase();
            if (hay.includes("yggdrasil")) {
                return true;
            }
            if (/\bygg\b/.test(hay) || hay.includes("-ygg") || hay.includes(" ygg") || hay.includes("(ygg")) {
                return true;
            }
            if (/^(200|201|202|203):[0-9a-f:]+$/i.test(host)) {
                return true;
            }
            return false;
        },
        pickEligibleCommunityTcpBootstrapForRandom() {
            const out = [];
            for (const iface of this.communityInterfaces) {
                const t = iface.type;
                if (t !== "TCPClientInterface" && t !== "BackboneInterface") {
                    continue;
                }
                const host = String(iface.target_host || "").trim();
                const port = iface.target_port;
                if (!host || port === undefined || port === null || port === "") {
                    continue;
                }
                if (this.communityBootstrapExcludedFromRandom(iface)) {
                    continue;
                }
                out.push({
                    key: `comm:${iface.name}`,
                    kind: "community",
                    iface,
                    dedupe: `${host.toLowerCase()}:${Number(port)}`,
                });
            }
            return out;
        },
        pickEligibleTcpBootstrapEntries() {
            const out = [];
            for (const iface of this.communityInterfaces) {
                const t = iface.type;
                if (t !== "TCPClientInterface" && t !== "BackboneInterface") {
                    continue;
                }
                const host = String(iface.target_host || "").trim();
                const port = iface.target_port;
                if (!host || port === undefined || port === null || port === "") {
                    continue;
                }
                out.push({
                    key: `comm:${iface.name}`,
                    kind: "community",
                    iface,
                    dedupe: `${host.toLowerCase()}:${Number(port)}`,
                });
            }
            for (const iface of this.discoveredInterfaces) {
                const host = String(iface.reachable_on || "").trim();
                const port = iface.port;
                if (!host || port === undefined || port === null || port === "") {
                    continue;
                }
                const typ = iface.type || "";
                if (typ && typ !== "BackboneInterface" && typ !== "TCPClientInterface") {
                    continue;
                }
                out.push({
                    key: `disc:${iface.discovery_hash || iface.name}`,
                    kind: "discovered",
                    iface,
                    dedupe: `${host.toLowerCase()}:${Number(port)}`,
                });
            }
            return out;
        },
        dedupeBootstrapEntries(entries) {
            const seen = new Set();
            const deduped = [];
            for (const e of entries) {
                if (seen.has(e.dedupe)) {
                    continue;
                }
                seen.add(e.dedupe);
                deduped.push(e);
            }
            return deduped;
        },
        shuffleArrayInPlace(arr) {
            for (let i = arr.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [arr[i], arr[j]] = [arr[j], arr[i]];
            }
        },
        async pickRandomTcpBootstraps(options = {}) {
            const silent = options.silent === true;
            const auto = options.auto === true;
            if (!silent && !auto) {
                this.pickingRandomBootstraps = true;
            }
            await Promise.resolve();
            await new Promise((resolve) => {
                if (typeof requestAnimationFrame !== "undefined") {
                    requestAnimationFrame(() => resolve());
                } else {
                    setTimeout(resolve, 0);
                }
            });
            try {
                let entries = this.pickEligibleCommunityTcpBootstrapForRandom();
                entries = this.dedupeBootstrapEntries(entries);
                if (entries.length === 0) {
                    if (!silent && !auto) {
                        ToastUtils.warning(this.$t("tutorial.bootstrap_pick_random_none"));
                    }
                    return;
                }
                this.shuffleArrayInPlace(entries);
                const take = Math.min(3, entries.length);
                this.selectedBootstrapKeys = entries.slice(0, take).map((e) => e.key);
                const labels = this.selectedBootstrapKeys.map((k) => this.bootstrapDisplayLabelForKey(k));
                if (!silent && !auto) {
                    ToastUtils.success(
                        this.$t("tutorial.bootstrap_pick_random_done", {
                            count: take,
                            names: labels.join(", "),
                        })
                    );
                }
            } finally {
                if (!silent && !auto) {
                    this.pickingRandomBootstraps = false;
                }
            }
        },
        async maybeAutoPickBootstrapTcp() {
            if (this.bootstrapAutoPickDone) {
                return;
            }
            if (this.currentStep !== 4 || this.connectionMode !== "discovery") {
                return;
            }
            if (this.selectedBootstrapKeys.length > 0) {
                return;
            }
            const entries = this.dedupeBootstrapEntries(this.pickEligibleCommunityTcpBootstrapForRandom());
            if (entries.length === 0) {
                return;
            }
            await this.pickRandomTcpBootstraps({ silent: true, auto: true });
            this.bootstrapAutoPickDone = true;
        },
        buildBootstrapPayload(item) {
            if (item.kind === "discovered") {
                const iface = item.iface;
                const payload = {
                    name: iface.name || `Discovered ${iface.discovery_hash || ""}`.trim(),
                    type: iface.type === "BackboneInterface" ? "TCPClientInterface" : iface.type,
                    enabled: true,
                    bootstrap_only: this.defaultBootstrapOnly === true,
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
                bootstrap_only: this.defaultBootstrapOnly === true,
            };
        },
        parseDiscoveryBool(value, defaultValue = false) {
            if (value === undefined || value === null || value === "") {
                return defaultValue;
            }
            if (typeof value === "string") {
                return ["true", "yes", "1", "y", "on"].includes(value.toLowerCase());
            }
            return Boolean(value);
        },
        async loadDiscoveryBootstrapDefaults() {
            try {
                const response = await window.api.get("/api/v1/reticulum/discovery");
                const d = response.data?.discovery ?? {};
                this.defaultBootstrapOnly = this.parseDiscoveryBool(d.default_bootstrap_only, false);
            } catch (e) {
                console.error(e);
                this.defaultBootstrapOnly = false;
            }
        },
        async persistDefaultBootstrapOnly(value) {
            try {
                await window.api.patch("/api/v1/reticulum/discovery", {
                    default_bootstrap_only: value === true,
                });
            } catch (e) {
                console.error("Failed to save default_bootstrap_only:", e);
            }
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
            this.currentStep = 5;
        },
        skipBootstraps() {
            this.currentStep = 5;
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
        async handlePrimaryAction() {
            if (this.currentStep === 2) {
                await this.handleIdentityContinue();
                return;
            }
            this.nextStep();
        },
        nextStep() {
            if (this.currentStep >= this.totalSteps) return;
            if (this.currentStep === 3 && this.connectionMode !== "discovery") {
                this.currentStep = 5;
                return;
            }
            this.currentStep++;
            if (this.currentStep === 4) {
                this.bootstrapListSearch = "";
                this.bootstrapDiscoveredSectionOpen = true;
                this.bootstrapCommunitySectionOpen = true;
            }
        },
        previousStep() {
            if (this.currentStep <= 1) return;
            if (this.currentStep === 5 && this.connectionMode !== "discovery") {
                this.currentStep = 3;
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
            if (this.identityImportedHash && this.identityImportedHash !== this.originalIdentityHash) {
                try {
                    await window.api.post("/api/v1/identities/switch", {
                        identity_hash: this.identityImportedHash,
                    });
                    if (this.originalIdentityHash) {
                        await window.api.delete(`/api/v1/identities/${this.originalIdentityHash}`);
                    }
                } catch (e) {
                    ToastUtils.error(e.response?.data?.message || this.$t("tutorial.identity_switch_failed"));
                    return;
                }
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

.tutorial-action-btn {
    min-height: 2.75rem;
    padding: 0.625rem 1rem;
    border-radius: 0.75rem;
    font-size: 0.875rem;
    font-weight: 700;
    line-height: 1.1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    transition: all 0.15s ease;
}

.tutorial-action-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.tutorial-action-btn-primary {
    background: rgb(37 99 235);
    color: white;
}

.tutorial-action-btn-primary:hover:not(:disabled) {
    background: rgb(59 130 246);
}

.tutorial-action-btn-secondary {
    border: 1px solid rgb(209 213 219);
    background: white;
    color: rgb(55 65 81);
}

.tutorial-action-btn-secondary:hover:not(:disabled) {
    background: rgb(249 250 251);
}

.tutorial-action-btn-success {
    background: rgb(5 150 105);
    color: white;
}

.tutorial-action-btn-success:hover:not(:disabled) {
    background: rgb(16 185 129);
}

.tutorial-dialog :deep(.dark) .tutorial-action-btn-secondary,
:deep(.dark) .tutorial-action-btn-secondary {
    border-color: rgb(63 63 70);
    background: rgb(39 39 42);
    color: rgb(212 212 216);
}

.tutorial-dialog :deep(.dark) .tutorial-action-btn-secondary:hover:not(:disabled),
:deep(.dark) .tutorial-action-btn-secondary:hover:not(:disabled) {
    background: rgb(63 63 70);
}
</style>
