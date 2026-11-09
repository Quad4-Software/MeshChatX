<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <AppModal
        v-if="!isPage"
        v-model="visible"
        :fullscreen="dialogFullscreen"
        :max-width="800"
        persistent
        :show-close="false"
        panel-class="border-0 bg-sem-surface overflow-hidden relative"
        body-class="flex min-h-0 flex-1 flex-col overflow-hidden p-0"
    >
        <!-- Progress segments -->
        <div class="shrink-0 px-4 pb-1 pt-3 sm:px-6">
            <div class="flex h-1.5 w-full gap-1" aria-hidden="true">
                <div
                    v-for="step in totalSteps"
                    :key="step"
                    class="h-full flex-1 rounded-full transition-colors duration-300 ease-out"
                    :class="currentStep >= step ? 'bg-sem-accent' : 'bg-sem-border'"
                ></div>
            </div>
        </div>

        <!-- Step counter + language/theme -->
        <div class="tutorial-topbar">
            <span class="tutorial-step-count">
                <span class="font-bold text-sem-accent">{{ currentStep }}</span>
                <span class="text-sem-fg-muted"> / {{ totalSteps }}</span>
            </span>
            <div class="flex items-center gap-0.5">
                <LanguageSelector @language-change="onLanguageChange" />
                <button
                    type="button"
                    class="tutorial-icon-btn"
                    :title="config?.theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
                    :aria-label="config?.theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
                    @click="toggleTheme"
                >
                    <MaterialDesignIcon
                        :icon-name="config?.theme === 'dark' ? 'brightness-6' : 'brightness-4'"
                        class="size-5"
                    />
                </button>
            </div>
        </div>

        <!-- Reticulum stack rebuild in flight (triggered here or elsewhere) -->
        <div
            v-if="reticulumBusy"
            class="flex shrink-0 items-center justify-center gap-2 border-b border-sem-border bg-sem-surface-muted/60 px-4 py-1.5 text-xs font-semibold text-sem-fg-muted sm:px-6"
            role="status"
        >
            <MaterialDesignIcon icon-name="loading" class="size-3.5 animate-spin text-sem-accent" />
            {{ $t("app.reloading_rns") }}
        </div>

        <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-4 sm:px-6 sm:py-6 md:px-10 md:py-8">
            <div class="flex min-h-full w-full flex-col justify-center">
                <transition name="fade-slide" mode="out-in">
                    <!-- Step 1: Welcome -->
                    <div v-if="currentStep === 1" key="step1" class="tutorial-step max-w-2xl items-center text-center">
                        <div class="relative">
                            <div
                                class="absolute -inset-1.5 rotate-6 rounded-[1.6rem] bg-sem-accent/15 sm:-inset-2 sm:rounded-[2rem]"
                            ></div>
                            <div
                                class="relative flex size-28 items-center justify-center rounded-[1.75rem] border border-sem-border bg-sem-surface p-3 shadow-sm sm:size-32 sm:rounded-[2rem] sm:p-4"
                            >
                                <img :src="logoUrl" alt="" class="size-full object-contain" />
                            </div>
                        </div>
                        <div class="space-y-2">
                            <h1 class="text-4xl font-black leading-tight tracking-tight text-sem-fg sm:text-5xl">
                                {{ $t("tutorial.welcome") }} <span class="text-sem-accent">MeshChatX</span>
                            </h1>
                            <p class="mx-auto max-w-xl text-base text-sem-fg-muted sm:text-lg">
                                {{ $t("tutorial.welcome_desc") }}
                            </p>
                        </div>
                        <div
                            v-if="migrationOffer && migrationOffer.show_choice"
                            class="tutorial-notice tutorial-notice--warning"
                        >
                            <div class="flex items-start gap-3">
                                <MaterialDesignIcon
                                    icon-name="alert-outline"
                                    class="mt-0.5 size-5 shrink-0 text-sem-warning"
                                />
                                <div class="min-w-0 flex-1 space-y-1.5">
                                    <div class="text-sm font-bold text-sem-fg">
                                        {{ $t("tutorial.migration_title") }}
                                    </div>
                                    <p class="text-sm text-sem-fg-muted">
                                        {{ $t("tutorial.migration_desc") }}
                                    </p>
                                    <div class="flex flex-col gap-2 pt-2 sm:flex-row sm:justify-end">
                                        <button
                                            type="button"
                                            class="tutorial-action-btn tutorial-action-btn-primary w-full sm:w-auto"
                                            :disabled="migrationBusy"
                                            @click="migrationMigrate"
                                        >
                                            {{ $t("tutorial.migration_migrate") }}
                                        </button>
                                        <button
                                            type="button"
                                            class="tutorial-action-btn tutorial-action-btn-secondary w-full sm:w-auto"
                                            :disabled="migrationBusy"
                                            @click="migrationFresh"
                                        >
                                            {{ $t("tutorial.migration_fresh") }}
                                        </button>
                                    </div>
                                    <p v-if="migrationBusy" class="text-xs text-sem-fg-muted">
                                        {{ $t("tutorial.migration_working") }}
                                    </p>
                                </div>
                            </div>
                        </div>
                        <div
                            v-if="androidStorageSetup && androidStorageSetup.needs_setup_choice"
                            class="tutorial-notice tutorial-notice--info"
                        >
                            <div class="flex items-start gap-3">
                                <MaterialDesignIcon
                                    icon-name="folder-open-outline"
                                    class="mt-0.5 size-5 shrink-0 text-sem-info"
                                />
                                <div class="min-w-0 flex-1 space-y-3">
                                    <div>
                                        <div class="text-sm font-bold text-sem-fg">
                                            {{ $t("android_storage.setup_title") }}
                                        </div>
                                        <p class="mt-0.5 text-sm text-sem-fg-muted">
                                            {{ $t("android_storage.setup_desc") }}
                                        </p>
                                    </div>
                                    <div class="space-y-2">
                                        <label
                                            class="flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition-colors"
                                            :class="
                                                androidStorageSetupChoice === 'external'
                                                    ? 'border-sem-accent bg-sem-accent/5'
                                                    : 'border-sem-border bg-sem-surface hover:border-sem-accent/60'
                                            "
                                        >
                                            <input
                                                v-model="androidStorageSetupChoice"
                                                type="radio"
                                                class="mt-0.5 size-4 shrink-0 accent-sem-accent"
                                                value="external"
                                                :disabled="androidStorageBusy"
                                            />
                                            <span class="min-w-0">
                                                <span class="block text-sm font-semibold text-sem-fg">
                                                    {{ $t("android_storage.setup_external_title") }}
                                                </span>
                                                <span class="mt-0.5 block text-xs text-sem-fg-muted">
                                                    {{ $t("android_storage.setup_external_desc") }}
                                                </span>
                                            </span>
                                        </label>
                                        <label
                                            class="flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition-colors"
                                            :class="
                                                androidStorageSetupChoice === 'internal'
                                                    ? 'border-sem-accent bg-sem-accent/5'
                                                    : 'border-sem-border bg-sem-surface hover:border-sem-accent/60'
                                            "
                                        >
                                            <input
                                                v-model="androidStorageSetupChoice"
                                                type="radio"
                                                class="mt-0.5 size-4 shrink-0 accent-sem-accent"
                                                value="internal"
                                                :disabled="androidStorageBusy"
                                            />
                                            <span class="min-w-0">
                                                <span class="block text-sm font-semibold text-sem-fg">
                                                    {{ $t("android_storage.setup_internal_title") }}
                                                </span>
                                                <span class="mt-0.5 block text-xs text-sem-fg-muted">
                                                    {{ $t("android_storage.setup_internal_desc") }}
                                                </span>
                                            </span>
                                        </label>
                                    </div>
                                    <div class="flex flex-col gap-2 pt-1 sm:flex-row sm:justify-end">
                                        <button
                                            type="button"
                                            class="tutorial-action-btn tutorial-action-btn-primary w-full sm:w-auto"
                                            :disabled="androidStorageBusy || !androidStorageSetupChoice"
                                            @click="applyAndroidStorageSetup"
                                        >
                                            {{ $t("android_storage.setup_continue") }}
                                        </button>
                                    </div>
                                    <p v-if="androidStorageBusy" class="text-xs text-sem-fg-muted">
                                        {{ $t("android_storage.working") }}
                                    </p>
                                </div>
                            </div>
                        </div>
                        <div class="tutorial-feature-grid">
                            <div class="tutorial-feature-card">
                                <MaterialDesignIcon icon-name="shield-lock" class="tutorial-feature-icon" />
                                <div class="min-w-0">
                                    <div class="tutorial-feature-title">{{ $t("tutorial.security") }}</div>
                                    <div class="tutorial-feature-desc">{{ $t("tutorial.security_desc") }}</div>
                                </div>
                            </div>
                            <div class="tutorial-feature-card">
                                <MaterialDesignIcon icon-name="map-marker-path" class="tutorial-feature-icon" />
                                <div class="min-w-0">
                                    <div class="tutorial-feature-title">{{ $t("tutorial.maps") }}</div>
                                    <div class="tutorial-feature-desc">{{ $t("tutorial.maps_desc") }}</div>
                                </div>
                            </div>
                            <div class="tutorial-feature-card">
                                <MaterialDesignIcon icon-name="phone" class="tutorial-feature-icon" />
                                <div class="min-w-0">
                                    <div class="tutorial-feature-title">{{ $t("tutorial.voice") }}</div>
                                    <div class="tutorial-feature-desc">{{ $t("tutorial.voice_desc") }}</div>
                                </div>
                            </div>
                            <div class="tutorial-feature-card">
                                <MaterialDesignIcon icon-name="tools" class="tutorial-feature-icon" />
                                <div class="min-w-0">
                                    <div class="tutorial-feature-title">{{ $t("tutorial.tools") }}</div>
                                    <div class="tutorial-feature-desc">{{ $t("tutorial.tools_desc") }}</div>
                                </div>
                            </div>
                            <div class="tutorial-feature-card">
                                <MaterialDesignIcon icon-name="database-search" class="tutorial-feature-icon" />
                                <div class="min-w-0">
                                    <div class="tutorial-feature-title">{{ $t("tutorial.archiver") }}</div>
                                    <div class="tutorial-feature-desc">{{ $t("tutorial.archiver_desc") }}</div>
                                </div>
                            </div>
                            <div class="tutorial-feature-card">
                                <MaterialDesignIcon icon-name="account-cancel" class="tutorial-feature-icon" />
                                <div class="min-w-0">
                                    <div class="tutorial-feature-title">{{ $t("tutorial.banishment") }}</div>
                                    <div class="tutorial-feature-desc">{{ $t("tutorial.banishment_desc") }}</div>
                                </div>
                            </div>
                            <div class="tutorial-feature-card">
                                <MaterialDesignIcon icon-name="keyboard-outline" class="tutorial-feature-icon" />
                                <div class="min-w-0">
                                    <div class="tutorial-feature-title">{{ $t("tutorial.palette") }}</div>
                                    <div class="tutorial-feature-desc">{{ $t("tutorial.palette_desc") }}</div>
                                </div>
                            </div>
                            <div class="tutorial-feature-card">
                                <MaterialDesignIcon icon-name="translate" class="tutorial-feature-icon" />
                                <div class="min-w-0">
                                    <div class="tutorial-feature-title">{{ $t("tutorial.i18n") }}</div>
                                    <div class="tutorial-feature-desc">{{ $t("tutorial.i18n_desc") }}</div>
                                </div>
                            </div>
                        </div>
                        <p class="text-xs text-sem-fg-muted">{{ $t("tutorial.more_features") }}</p>
                    </div>

                    <!-- Step 2: Identity Setup -->
                    <div v-else-if="currentStep === 2" key="step2-identity" class="tutorial-step max-w-3xl">
                        <header class="tutorial-step-header">
                            <div class="tutorial-step-icon">
                                <MaterialDesignIcon icon-name="account-key" class="size-6" />
                            </div>
                            <div class="min-w-0">
                                <h2 class="tutorial-step-title">{{ $t("tutorial.identity_title") }}</h2>
                                <p class="tutorial-step-desc">{{ $t("tutorial.identity_desc") }}</p>
                            </div>
                        </header>

                        <div v-if="originalIdentityHash" class="tutorial-card">
                            <div class="text-xs font-bold uppercase tracking-wide text-sem-fg-muted">
                                {{ $t("app.identity_hash") }}
                            </div>
                            <div class="mt-1.5 break-all font-mono text-xs text-sem-fg-muted select-all">
                                {{ formatIdentityHash(originalIdentityHash) }}
                            </div>
                            <p class="mt-2 text-xs text-sem-fg-muted">{{ $t("tutorial.identity_new_desc") }}</p>
                        </div>

                        <input
                            ref="identityImportFileInput"
                            type="file"
                            accept=".bin,.key,.identity,application/octet-stream,*/*"
                            class="hidden"
                            @change="onIdentityImportFileChange"
                        />
                        <div
                            class="grid grid-cols-1 gap-3 sm:grid-cols-2"
                            :class="{ 'pointer-events-none opacity-70': tutorialNavBusy }"
                            :aria-busy="tutorialNavBusy"
                        >
                            <button
                                type="button"
                                class="tutorial-choice"
                                :class="identityMode === 'new' ? 'tutorial-choice--selected' : ''"
                                :disabled="tutorialNavBusy"
                                @click="setIdentityMode('new')"
                            >
                                <span class="tutorial-icon-tile bg-sem-accent/10 text-sem-accent">
                                    <MaterialDesignIcon icon-name="account-plus-outline" class="size-5" />
                                </span>
                                <span class="min-w-0 flex-1">
                                    <span class="block font-bold text-sem-fg">
                                        {{ $t("tutorial.identity_new") }}
                                    </span>
                                    <span class="mt-0.5 block text-sm text-sem-fg-muted">
                                        {{ $t("tutorial.identity_new_desc") }}
                                    </span>
                                </span>
                                <span v-if="identityMode === 'new'" class="tutorial-choice__check">
                                    <MaterialDesignIcon icon-name="check" class="size-3.5" />
                                </span>
                            </button>
                            <button
                                type="button"
                                class="tutorial-choice"
                                :class="identityMode === 'import' ? 'tutorial-choice--selected' : ''"
                                :disabled="tutorialNavBusy"
                                @click="setIdentityMode('import')"
                            >
                                <span class="tutorial-icon-tile bg-sem-info/10 text-sem-info">
                                    <MaterialDesignIcon icon-name="file-import-outline" class="size-5" />
                                </span>
                                <span class="min-w-0 flex-1">
                                    <span class="block font-bold text-sem-fg">
                                        {{ $t("tutorial.identity_import") }}
                                    </span>
                                    <span class="mt-0.5 block text-sm text-sem-fg-muted">
                                        {{ $t("tutorial.identity_import_desc") }}
                                    </span>
                                </span>
                                <span v-if="identityMode === 'import'" class="tutorial-choice__check">
                                    <MaterialDesignIcon icon-name="check" class="size-3.5" />
                                </span>
                            </button>
                        </div>
                        <div class="tutorial-card space-y-3">
                            <label class="block text-sm font-semibold text-sem-fg">
                                {{ $t("tutorial.identity_set_name") }}
                            </label>
                            <input
                                v-model="identityName"
                                type="text"
                                :placeholder="defaultUsername"
                                class="input-field"
                                :disabled="tutorialNavBusy"
                            />
                            <div v-if="identityMode === 'import'" class="space-y-3 border-t border-sem-border pt-3">
                                <p class="text-xs text-sem-fg-muted">
                                    {{ $t("tutorial.identity_import_key_only_hint") }}
                                </p>
                                <button
                                    type="button"
                                    class="tutorial-action-btn tutorial-action-btn-secondary w-full justify-center"
                                    :disabled="tutorialNavBusy"
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
                                    class="input-field font-mono"
                                    :placeholder="$t('tutorial.identity_base32_placeholder')"
                                    :disabled="Boolean(identityImportFile) || tutorialNavBusy"
                                    @input="onIdentityImportBase32Input"
                                />
                                <p
                                    v-if="identityImportFile && identityImportBase32.trim()"
                                    class="text-xs text-sem-warning"
                                >
                                    {{ $t("tutorial.identity_file_overrides_base32") }}
                                </p>
                            </div>
                            <p v-if="identityImportError" role="alert" class="text-sm text-sem-danger">
                                {{ identityImportError }}
                            </p>
                        </div>
                    </div>

                    <!-- Step 3: Choose Connection Mode -->
                    <div v-else-if="currentStep === 3" key="step3-mode" class="tutorial-step max-w-3xl">
                        <header class="tutorial-step-header">
                            <div class="tutorial-step-icon tutorial-step-icon--info">
                                <MaterialDesignIcon icon-name="access-point-network" class="size-6" />
                            </div>
                            <div class="min-w-0">
                                <h2 class="tutorial-step-title">{{ $t("tutorial.connect") }}</h2>
                                <p class="tutorial-step-desc">{{ $t("tutorial.connect_desc") }}</p>
                            </div>
                        </header>

                        <div
                            class="grid grid-cols-1 gap-3 sm:grid-cols-2"
                            :class="{ 'pointer-events-none opacity-70': connectionSetupBusy }"
                            :aria-busy="connectionSetupBusy"
                        >
                            <button
                                type="button"
                                class="tutorial-choice"
                                :class="connectionMode === 'recommended' ? 'tutorial-choice--selected' : ''"
                                :disabled="connectionSetupBusy"
                                @click="useRecommendedMode"
                            >
                                <span class="tutorial-icon-tile bg-sem-info/10 text-sem-info">
                                    <MaterialDesignIcon icon-name="access-point-network" class="size-5" />
                                </span>
                                <span class="min-w-0 flex-1">
                                    <span class="block font-bold text-sem-fg">
                                        {{ $t("tutorial.mode_recommended_title") }}
                                    </span>
                                    <span class="mt-0.5 block text-sm text-sem-fg-muted">
                                        {{ $t("tutorial.mode_recommended_desc") }}
                                    </span>
                                </span>
                                <MaterialDesignIcon
                                    v-if="connectionSetupBusy"
                                    icon-name="loading"
                                    class="size-5 shrink-0 animate-spin self-start text-sem-accent"
                                />
                                <span v-else-if="connectionMode === 'recommended'" class="tutorial-choice__check">
                                    <MaterialDesignIcon icon-name="check" class="size-3.5" />
                                </span>
                            </button>

                            <button
                                type="button"
                                class="tutorial-choice"
                                :class="connectionMode === 'discovery' ? 'tutorial-choice--selected' : ''"
                                :disabled="connectionSetupBusy"
                                @click="useDiscoveryMode"
                            >
                                <span class="tutorial-icon-tile bg-sem-accent/10 text-sem-accent">
                                    <MaterialDesignIcon icon-name="radar" class="size-5" />
                                </span>
                                <span class="min-w-0 flex-1">
                                    <span class="block font-bold text-sem-fg">
                                        {{ $t("tutorial.mode_discovery_title") }}
                                    </span>
                                    <span class="mt-0.5 block text-sm text-sem-fg-muted">
                                        {{ $t("tutorial.mode_discovery_desc") }}
                                    </span>
                                </span>
                                <MaterialDesignIcon
                                    v-if="connectionSetupBusy"
                                    icon-name="loading"
                                    class="size-5 shrink-0 animate-spin self-start text-sem-accent"
                                />
                                <span v-else-if="connectionMode === 'discovery'" class="tutorial-choice__check">
                                    <MaterialDesignIcon icon-name="check" class="size-3.5" />
                                </span>
                            </button>

                            <button
                                type="button"
                                class="tutorial-choice"
                                :class="connectionMode === 'local' ? 'tutorial-choice--selected' : ''"
                                :disabled="connectionSetupBusy"
                                @click="useLocalMode"
                            >
                                <span class="tutorial-icon-tile bg-sem-success/10 text-sem-success">
                                    <MaterialDesignIcon icon-name="lan" class="size-5" />
                                </span>
                                <span class="min-w-0 flex-1">
                                    <span class="block font-bold text-sem-fg">
                                        {{ $t("tutorial.mode_local_title") }}
                                    </span>
                                    <span class="mt-0.5 block text-sm text-sem-fg-muted">
                                        {{ $t("tutorial.mode_local_desc") }}
                                    </span>
                                </span>
                                <MaterialDesignIcon
                                    v-if="connectionSetupBusy"
                                    icon-name="loading"
                                    class="size-5 shrink-0 animate-spin self-start text-sem-accent"
                                />
                                <span v-else-if="connectionMode === 'local'" class="tutorial-choice__check">
                                    <MaterialDesignIcon icon-name="check" class="size-3.5" />
                                </span>
                            </button>

                            <button
                                type="button"
                                class="tutorial-choice"
                                :class="connectionMode === 'manual' ? 'tutorial-choice--selected' : ''"
                                :disabled="connectionSetupBusy"
                                @click="useManualMode"
                            >
                                <span class="tutorial-icon-tile bg-sem-surface-muted text-sem-fg-muted">
                                    <MaterialDesignIcon icon-name="cog-outline" class="size-5" />
                                </span>
                                <span class="min-w-0 flex-1">
                                    <span class="block font-bold text-sem-fg">
                                        {{ $t("tutorial.mode_manual_title") }}
                                    </span>
                                    <span class="mt-0.5 block text-sm text-sem-fg-muted">
                                        {{ $t("tutorial.mode_manual_desc") }}
                                    </span>
                                </span>
                                <span v-if="connectionMode === 'manual'" class="tutorial-choice__check">
                                    <MaterialDesignIcon icon-name="check" class="size-3.5" />
                                </span>
                            </button>
                        </div>

                        <p class="text-xs text-center text-sem-fg-muted">{{ $t("tutorial.mode_change_later") }}</p>
                    </div>

                    <!-- Step 4: Bootstrap Selection -->
                    <div v-else-if="currentStep === 4" key="step4-bootstrap" class="tutorial-step max-w-4xl">
                        <header class="tutorial-step-header">
                            <div class="tutorial-step-icon">
                                <MaterialDesignIcon icon-name="server-network" class="size-6" />
                            </div>
                            <div class="min-w-0">
                                <h2 class="tutorial-step-title">{{ $t("tutorial.bootstrap_title") }}</h2>
                                <p class="tutorial-step-desc">{{ $t("tutorial.bootstrap_desc") }}</p>
                            </div>
                        </header>

                        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                            <button
                                type="button"
                                class="tutorial-action-btn tutorial-action-btn-secondary"
                                :disabled="bootstrapPickBusy"
                                @click="pickRandomTcpBootstraps"
                            >
                                <MaterialDesignIcon
                                    v-if="bootstrapPickBusy"
                                    icon-name="loading"
                                    class="size-4 animate-spin text-sem-accent"
                                />
                                <MaterialDesignIcon v-else icon-name="shuffle-variant" class="size-4" />
                                {{ $t("tutorial.bootstrap_pick_random_tcp") }}
                            </button>
                            <div
                                v-if="bootstrapSelectedLabels.length > 0"
                                class="w-full rounded-xl border border-sem-border bg-sem-surface-muted/60 px-3 py-2 sm:max-w-xs"
                            >
                                <div class="text-[11px] font-bold uppercase tracking-wide text-sem-fg-muted">
                                    {{ $t("tutorial.bootstrap_selected_nodes_heading") }}
                                </div>
                                <ul
                                    class="mt-1 max-h-24 space-y-0.5 overflow-y-auto text-xs text-sem-fg custom-scrollbar"
                                >
                                    <li
                                        v-for="(label, idx) in bootstrapSelectedLabels"
                                        :key="selectedBootstrapKeys[idx]"
                                    >
                                        {{ label }}
                                    </li>
                                </ul>
                            </div>
                        </div>

                        <div class="tutorial-card flex items-start gap-3">
                            <div class="flex shrink-0 items-start pt-0.5">
                                <Toggle
                                    v-model="defaultBootstrapOnly"
                                    :disabled="bootstrapActionBusy"
                                    @update:model-value="persistDefaultBootstrapOnly"
                                />
                            </div>
                            <div class="min-w-0 flex-1">
                                <div class="text-sm font-semibold text-sem-fg">
                                    {{ $t("tutorial.bootstrap_only_label") }}
                                </div>
                                <p class="mt-1 text-xs leading-relaxed text-sem-fg-muted">
                                    {{ $t("tutorial.bootstrap_only_hint") }}
                                </p>
                            </div>
                        </div>

                        <div class="tutorial-notice tutorial-notice--info">
                            <div class="flex items-start gap-3">
                                <MaterialDesignIcon
                                    icon-name="lan-connect"
                                    class="mt-0.5 size-5 shrink-0 text-sem-info"
                                />
                                <div class="min-w-0 flex-1 space-y-3">
                                    <div>
                                        <div class="text-sm font-bold text-sem-fg">
                                            {{ $t("tutorial.custom_interfaces") }}
                                        </div>
                                        <p class="mt-0.5 text-sm text-sem-fg-muted">
                                            {{
                                                isPage
                                                    ? $t("tutorial.custom_interfaces_desc_page")
                                                    : $t("tutorial.custom_interfaces_desc")
                                            }}
                                        </p>
                                    </div>
                                    <button
                                        type="button"
                                        class="tutorial-mini-btn tutorial-mini-btn--secondary"
                                        :disabled="tutorialNavBusy"
                                        @click="gotoAddInterface()"
                                    >
                                        {{ $t("tutorial.open_interfaces") }}
                                        <MaterialDesignIcon icon-name="arrow-right" class="size-4" />
                                    </button>
                                </div>
                            </div>
                        </div>

                        <template v-if="hasAnyBootstrapsToShow">
                            <div class="relative">
                                <MaterialDesignIcon
                                    icon-name="magnify"
                                    class="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-sem-fg-muted"
                                />
                                <input
                                    v-model="bootstrapListSearch"
                                    type="search"
                                    autocomplete="off"
                                    :placeholder="$t('tutorial.bootstrap_search_placeholder')"
                                    class="search-input"
                                />
                                <button
                                    v-if="bootstrapListSearch"
                                    type="button"
                                    class="absolute right-1.5 top-1/2 flex size-8 -translate-y-1/2 items-center justify-center rounded-full text-sem-fg-muted transition-colors hover:bg-sem-surface-muted hover:text-sem-fg"
                                    :title="$t('tutorial.bootstrap_search_clear')"
                                    :aria-label="$t('tutorial.bootstrap_search_clear')"
                                    @click="bootstrapListSearch = ''"
                                >
                                    <MaterialDesignIcon icon-name="close" class="size-4" />
                                </button>
                            </div>

                            <div
                                class="grid grid-cols-1 items-start gap-4 lg:grid-cols-2"
                                :aria-busy="bootstrapActionBusy"
                            >
                                <div
                                    v-if="sortedDiscoveredInterfaces.length > 0"
                                    class="tutorial-section tutorial-section--discovered"
                                >
                                    <button
                                        type="button"
                                        class="tutorial-section__head"
                                        :aria-expanded="bootstrapDiscoveredSectionOpen"
                                        @click="bootstrapDiscoveredSectionOpen = !bootstrapDiscoveredSectionOpen"
                                    >
                                        <span
                                            class="flex size-8 shrink-0 items-center justify-center rounded-lg bg-sem-success/10 text-sem-success"
                                        >
                                            <MaterialDesignIcon icon-name="radar" class="size-4" />
                                        </span>
                                        <span class="text-sm font-bold text-sem-fg">{{
                                            $t("tutorial.bootstrap_discovered")
                                        }}</span>
                                        <span class="tutorial-count-chip">{{ sortedDiscoveredInterfaces.length }}</span>
                                        <MaterialDesignIcon
                                            :icon-name="bootstrapDiscoveredSectionOpen ? 'chevron-up' : 'chevron-down'"
                                            class="ml-auto size-5 shrink-0 text-sem-fg-muted"
                                        />
                                    </button>
                                    <div v-show="bootstrapDiscoveredSectionOpen" class="px-4 pb-4">
                                        <p
                                            v-if="
                                                bootstrapListSearch &&
                                                sortedDiscoveredInterfaces.length > 0 &&
                                                filteredDiscoveredForBootstrap.length === 0
                                            "
                                            class="text-xs text-sem-fg-muted"
                                        >
                                            {{ $t("tutorial.bootstrap_search_no_match") }}
                                        </p>
                                        <div
                                            v-else
                                            class="max-h-72 space-y-2 overflow-y-auto pt-1 custom-scrollbar"
                                            :class="{ 'pointer-events-none opacity-60': bootstrapActionBusy }"
                                        >
                                            <label
                                                v-for="iface in filteredDiscoveredForBootstrap"
                                                :key="iface.discovery_hash || iface.name"
                                                class="tutorial-bootstrap-row"
                                                :class="
                                                    isBootstrapSelected(`disc:${iface.discovery_hash || iface.name}`)
                                                        ? 'tutorial-bootstrap-row--selected'
                                                        : ''
                                                "
                                            >
                                                <input
                                                    type="checkbox"
                                                    class="size-4 shrink-0 accent-sem-accent"
                                                    :disabled="bootstrapActionBusy"
                                                    :checked="
                                                        isBootstrapSelected(
                                                            `disc:${iface.discovery_hash || iface.name}`
                                                        )
                                                    "
                                                    @change="
                                                        toggleBootstrap(`disc:${iface.discovery_hash || iface.name}`)
                                                    "
                                                />
                                                <MaterialDesignIcon
                                                    :icon-name="getDiscoveryIcon(iface)"
                                                    class="size-5 shrink-0 text-sem-success"
                                                />
                                                <span class="min-w-0 flex-1">
                                                    <span class="block truncate text-sm font-semibold text-sem-fg">
                                                        {{ iface.name }}
                                                    </span>
                                                    <span
                                                        class="mt-0.5 block truncate font-mono text-[11px] text-sem-fg-muted"
                                                    >
                                                        <span v-if="iface.reachable_on"
                                                            >{{ iface.reachable_on
                                                            }}<span v-if="iface.port">:{{ iface.port }}</span></span
                                                        >
                                                        <span v-else>{{ iface.type }}</span>
                                                        <span class="ml-2 capitalize">{{ iface.status }}</span>
                                                    </span>
                                                </span>
                                            </label>
                                        </div>
                                    </div>
                                </div>

                                <div
                                    class="tutorial-section tutorial-section--community"
                                    :class="[sortedDiscoveredInterfaces.length === 0 ? 'lg:col-span-2' : '']"
                                >
                                    <button
                                        type="button"
                                        class="tutorial-section__head"
                                        :aria-expanded="bootstrapCommunitySectionOpen"
                                        @click="bootstrapCommunitySectionOpen = !bootstrapCommunitySectionOpen"
                                    >
                                        <span
                                            class="flex size-8 shrink-0 items-center justify-center rounded-lg bg-sem-accent/10 text-sem-accent"
                                        >
                                            <MaterialDesignIcon icon-name="web" class="size-4" />
                                        </span>
                                        <span class="text-sm font-bold text-sem-fg">{{
                                            $t("tutorial.bootstrap_community")
                                        }}</span>
                                        <span class="tutorial-count-chip">{{ communityInterfaces.length }}</span>
                                        <MaterialDesignIcon
                                            :icon-name="bootstrapCommunitySectionOpen ? 'chevron-up' : 'chevron-down'"
                                            class="ml-auto size-5 shrink-0 text-sem-fg-muted"
                                        />
                                    </button>
                                    <div v-show="bootstrapCommunitySectionOpen" class="px-4 pb-4">
                                        <p
                                            v-if="
                                                bootstrapListSearch &&
                                                communityInterfaces.length > 0 &&
                                                filteredCommunityForBootstrap.length === 0
                                            "
                                            class="text-xs text-sem-fg-muted"
                                        >
                                            {{ $t("tutorial.bootstrap_search_no_match") }}
                                        </p>
                                        <div
                                            v-else
                                            class="max-h-72 space-y-2 overflow-y-auto pt-1 custom-scrollbar"
                                            :class="{ 'pointer-events-none opacity-60': bootstrapActionBusy }"
                                        >
                                            <label
                                                v-for="iface in filteredCommunityForBootstrap"
                                                :key="iface.name"
                                                class="tutorial-bootstrap-row"
                                                :class="
                                                    isBootstrapSelected(`comm:${iface.name}`)
                                                        ? 'tutorial-bootstrap-row--selected'
                                                        : ''
                                                "
                                            >
                                                <input
                                                    type="checkbox"
                                                    class="size-4 shrink-0 accent-sem-accent"
                                                    :disabled="bootstrapActionBusy"
                                                    :checked="isBootstrapSelected(`comm:${iface.name}`)"
                                                    @change="toggleBootstrap(`comm:${iface.name}`)"
                                                />
                                                <MaterialDesignIcon
                                                    icon-name="server-network"
                                                    class="size-5 shrink-0 text-sem-accent"
                                                />
                                                <span class="min-w-0 flex-1">
                                                    <span class="block truncate text-sm font-semibold text-sem-fg">
                                                        {{ iface.name }}
                                                    </span>
                                                    <span
                                                        class="block truncate font-mono text-[11px] text-sem-fg-muted"
                                                    >
                                                        {{ iface.target_host
                                                        }}<span v-if="iface.target_port">:{{ iface.target_port }}</span>
                                                    </span>
                                                </span>
                                                <span v-if="iface.online" class="tutorial-online-badge">{{
                                                    $t("tutorial.online")
                                                }}</span>
                                            </label>
                                            <div v-if="loadingInterfaces" class="flex justify-center py-3">
                                                <MaterialDesignIcon
                                                    icon-name="loading"
                                                    class="size-6 animate-spin text-sem-accent"
                                                />
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </template>
                        <div v-else class="tutorial-notice tutorial-notice--info">
                            <div class="flex items-start gap-3">
                                <MaterialDesignIcon icon-name="radar" class="mt-0.5 size-5 shrink-0 text-sem-info" />
                                <div class="min-w-0 flex-1">
                                    <div class="text-sm font-bold text-sem-fg">
                                        {{ $t("tutorial.bootstrap_empty_title") }}
                                    </div>
                                    <p class="mt-0.5 text-sm text-sem-fg-muted">
                                        {{ $t("tutorial.bootstrap_empty") }}
                                    </p>
                                </div>
                            </div>
                        </div>

                        <div
                            class="sticky bottom-0 -mx-4 border-t border-sem-border bg-sem-surface px-4 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3 sm:-mx-6 sm:px-6 md:-mx-10 md:px-10"
                            :aria-busy="bootstrapActionBusy"
                        >
                            <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                                <p class="text-xs text-sem-fg-muted">
                                    {{
                                        $t("tutorial.bootstrap_selected", {
                                            count: selectedBootstrapCount,
                                        })
                                    }}
                                </p>
                                <div class="flex flex-col gap-2 sm:flex-row">
                                    <button
                                        type="button"
                                        class="tutorial-action-btn tutorial-action-btn-secondary w-full sm:w-auto"
                                        :disabled="bootstrapActionBusy"
                                        @click="skipBootstraps"
                                    >
                                        {{ $t("tutorial.bootstrap_skip") }}
                                    </button>
                                    <button
                                        type="button"
                                        class="tutorial-action-btn tutorial-action-btn-success w-full sm:w-auto"
                                        :disabled="bootstrapActionBusy || selectedBootstrapCount === 0"
                                        @click="confirmBootstraps"
                                    >
                                        <MaterialDesignIcon
                                            v-if="bootstrapActionBusy"
                                            icon-name="loading"
                                            class="size-4 animate-spin"
                                        />
                                        {{ $t("tutorial.bootstrap_confirm") }}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Step 5: Propagation Mode -->
                    <div v-else-if="currentStep === 5" key="step5-prop" class="tutorial-step max-w-3xl">
                        <header class="tutorial-step-header">
                            <div class="tutorial-step-icon">
                                <MaterialDesignIcon icon-name="bullseye" class="size-6" />
                            </div>
                            <div class="min-w-0">
                                <h2 class="tutorial-step-title">{{ $t("tutorial.propagation") }}</h2>
                                <p class="tutorial-step-desc">{{ $t("tutorial.propagation_desc") }}</p>
                            </div>
                        </header>

                        <div class="tutorial-card mx-auto w-full max-w-xl text-center">
                            <div
                                class="mx-auto mb-4 flex size-12 items-center justify-center rounded-2xl bg-sem-accent/10 text-sem-accent"
                            >
                                <MaterialDesignIcon icon-name="server-network" class="size-6" />
                            </div>
                            <div class="text-base font-bold text-sem-fg">
                                {{ $t("tutorial.propagation_question") }}
                            </div>
                            <p class="mt-1.5 text-sm text-sem-fg-muted">{{ $t("tutorial.propagation_auto") }}</p>
                            <div class="mt-5 flex flex-col gap-2.5 sm:flex-row sm:justify-center">
                                <button
                                    type="button"
                                    class="tutorial-action-btn tutorial-action-btn-primary w-full sm:w-auto"
                                    :disabled="tutorialNavBusy"
                                    @click="enableAutoPropagation"
                                >
                                    <MaterialDesignIcon
                                        v-if="savingPropagation"
                                        icon-name="loading"
                                        class="size-4 animate-spin"
                                    />
                                    {{ $t("tutorial.propagation_enable_auto") }}
                                </button>
                                <button
                                    type="button"
                                    class="tutorial-action-btn tutorial-action-btn-secondary w-full sm:w-auto"
                                    :disabled="tutorialNavBusy"
                                    @click="nextStep"
                                >
                                    {{ $t("tutorial.propagation_skip_auto") }}
                                </button>
                            </div>
                            <div class="mt-5 border-t border-sem-border pt-4 text-left">
                                <div class="text-sm font-bold text-sem-fg">
                                    {{ $t("tutorial.propagation_manual") }}
                                </div>
                                <p class="mt-1 text-xs leading-relaxed text-sem-fg-muted">
                                    {{ $t("tutorial.propagation_manual_desc") }}
                                </p>
                            </div>
                        </div>
                    </div>

                    <!-- Step 6: Learn & Create -->
                    <div v-else-if="currentStep === 6" key="step6-tools" class="tutorial-step max-w-3xl">
                        <header class="tutorial-step-header">
                            <div class="tutorial-step-icon tutorial-step-icon--info">
                                <MaterialDesignIcon icon-name="lightbulb-on" class="size-6" />
                            </div>
                            <div class="min-w-0">
                                <h2 class="tutorial-step-title">{{ $t("tutorial.learn_create") }}</h2>
                                <p class="tutorial-step-desc">{{ $t("tutorial.learn_create_desc") }}</p>
                            </div>
                        </header>

                        <div class="mx-auto flex w-full max-w-2xl flex-col gap-4">
                            <div class="tutorial-card">
                                <div class="flex items-start gap-4">
                                    <span class="tutorial-icon-tile bg-sem-accent/10 text-sem-accent">
                                        <MaterialDesignIcon icon-name="book-open-variant" class="size-5" />
                                    </span>
                                    <div class="min-w-0 flex-1">
                                        <div class="font-bold text-sem-fg">{{ $t("tutorial.documentation") }}</div>
                                        <p class="mt-0.5 text-sm text-sem-fg-muted">
                                            {{ $t("tutorial.documentation_desc") }}
                                        </p>
                                        <div class="mt-3 flex flex-wrap gap-2">
                                            <a
                                                href="/meshchatx-docs/index.html"
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                class="tutorial-mini-btn tutorial-mini-btn--primary"
                                            >
                                                {{ $t("tutorial.meshchatx_docs") }}
                                            </a>
                                            <a
                                                :href="reticulumBundledDocsUrl"
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                class="tutorial-mini-btn tutorial-mini-btn--secondary"
                                            >
                                                {{ $t("tutorial.reticulum_docs") }}
                                            </a>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="tutorial-card">
                                <div class="flex items-start gap-4">
                                    <span class="tutorial-icon-tile bg-sem-warning/10 text-sem-warning">
                                        <MaterialDesignIcon icon-name="file-document-edit-outline" class="size-5" />
                                    </span>
                                    <div class="min-w-0 flex-1">
                                        <div class="font-bold text-sem-fg">{{ $t("tutorial.micron_editor") }}</div>
                                        <p class="mt-0.5 text-sm text-sem-fg-muted">
                                            {{ $t("tutorial.micron_editor_desc") }}
                                        </p>
                                        <div class="mt-3 flex flex-wrap gap-2">
                                            <button
                                                type="button"
                                                class="tutorial-mini-btn tutorial-mini-btn--primary"
                                                @click="gotoRoute('micron-editor')"
                                            >
                                                {{ $t("tutorial.open_micron_editor") }}
                                            </button>
                                            <button
                                                type="button"
                                                class="tutorial-mini-btn tutorial-mini-btn--secondary"
                                                @click="gotoRoute('mesh-server')"
                                            >
                                                {{ $t("tutorial.open_mesh_server") }}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div
                                class="tutorial-link-card"
                                role="button"
                                tabindex="0"
                                @click="gotoRoute('identities')"
                                @keydown.enter="gotoRoute('identities')"
                            >
                                <span class="tutorial-icon-tile bg-sem-info/10 text-sem-info">
                                    <MaterialDesignIcon icon-name="account-multiple-outline" class="size-5" />
                                </span>
                                <span class="min-w-0 flex-1">
                                    <span class="block font-bold text-sem-fg">
                                        {{ $t("tutorial.identities_card_title") }}
                                    </span>
                                    <span class="mt-0.5 block text-sm text-sem-fg-muted">
                                        {{ $t("tutorial.identities_card_desc") }}
                                    </span>
                                </span>
                                <MaterialDesignIcon
                                    icon-name="chevron-right"
                                    class="mt-1 size-5 shrink-0 text-sem-fg-muted"
                                />
                            </div>

                            <div
                                class="tutorial-link-card"
                                role="button"
                                tabindex="0"
                                @click="gotoRoute('archives')"
                                @keydown.enter="gotoRoute('archives')"
                            >
                                <span class="tutorial-icon-tile bg-sem-success/10 text-sem-success">
                                    <MaterialDesignIcon icon-name="archive-outline" class="size-5" />
                                </span>
                                <span class="min-w-0 flex-1">
                                    <span class="block font-bold text-sem-fg">{{ $t("tutorial.archiver") }}</span>
                                    <span class="mt-0.5 block text-sm text-sem-fg-muted">
                                        {{ $t("tutorial.archiver_desc") }}
                                    </span>
                                </span>
                                <MaterialDesignIcon
                                    icon-name="chevron-right"
                                    class="mt-1 size-5 shrink-0 text-sem-fg-muted"
                                />
                            </div>
                        </div>

                        <div class="mx-auto w-full max-w-2xl">
                            <p class="mb-3 text-center text-xs font-semibold text-sem-fg-muted">
                                {{ $t("tutorial.learn_create_more") }}
                            </p>
                            <div class="grid grid-cols-2 gap-2.5">
                                <div
                                    class="tutorial-mini-card"
                                    role="button"
                                    tabindex="0"
                                    @click="gotoRoute('nomadnetwork')"
                                    @keydown.enter="gotoRoute('nomadnetwork')"
                                >
                                    <MaterialDesignIcon icon-name="earth" class="size-5 shrink-0 text-sem-info" />
                                    <span class="min-w-0">
                                        <span class="block text-xs font-bold leading-tight text-sem-fg">
                                            {{ $t("tutorial.paper_messages") }}
                                        </span>
                                        <span
                                            class="mt-0.5 block text-[11px] leading-snug text-sem-fg-muted line-clamp-3"
                                        >
                                            {{ $t("tutorial.paper_messages_desc") }}
                                        </span>
                                    </span>
                                </div>

                                <div
                                    class="tutorial-mini-card"
                                    role="button"
                                    tabindex="0"
                                    @click="gotoRoute('messages')"
                                    @keydown.enter="gotoRoute('messages')"
                                >
                                    <MaterialDesignIcon
                                        icon-name="message-text-outline"
                                        class="size-5 shrink-0 text-sem-success"
                                    />
                                    <span class="min-w-0">
                                        <span class="block text-xs font-bold leading-tight text-sem-fg">
                                            {{ $t("tutorial.send_messages") }}
                                        </span>
                                        <span
                                            class="mt-0.5 block text-[11px] leading-snug text-sem-fg-muted line-clamp-3"
                                        >
                                            {{ $t("tutorial.send_messages_desc") }}
                                        </span>
                                    </span>
                                </div>

                                <div
                                    class="tutorial-mini-card"
                                    role="button"
                                    tabindex="0"
                                    @click="gotoRoute('network-visualiser')"
                                    @keydown.enter="gotoRoute('network-visualiser')"
                                >
                                    <MaterialDesignIcon icon-name="hub" class="size-5 shrink-0 text-sem-success" />
                                    <span class="min-w-0">
                                        <span class="block text-xs font-bold leading-tight text-sem-fg">
                                            {{ $t("tutorial.explore_nodes") }}
                                        </span>
                                        <span
                                            class="mt-0.5 block text-[11px] leading-snug text-sem-fg-muted line-clamp-3"
                                        >
                                            {{ $t("tutorial.explore_nodes_desc") }}
                                        </span>
                                    </span>
                                </div>

                                <div
                                    class="tutorial-mini-card"
                                    role="button"
                                    tabindex="0"
                                    @click="gotoRoute('call')"
                                    @keydown.enter="gotoRoute('call')"
                                >
                                    <MaterialDesignIcon
                                        icon-name="phone-in-talk-outline"
                                        class="size-5 shrink-0 text-sem-danger"
                                    />
                                    <span class="min-w-0">
                                        <span class="block text-xs font-bold leading-tight text-sem-fg">
                                            {{ $t("tutorial.voice_calls") }}
                                        </span>
                                        <span
                                            class="mt-0.5 block text-[11px] leading-snug text-sem-fg-muted line-clamp-3"
                                        >
                                            {{ $t("tutorial.voice_calls_desc") }}
                                        </span>
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Step 7: Privacy -->
                    <div v-else-if="currentStep === 7" key="step7-privacy" class="tutorial-step max-w-3xl">
                        <TutorialPrivacyStep />
                    </div>

                    <!-- Step 8: Finish -->
                    <div
                        v-else-if="currentStep === 8"
                        key="step8-finish"
                        class="tutorial-step max-w-2xl items-center text-center"
                    >
                        <div
                            class="flex size-24 items-center justify-center rounded-full bg-sem-success/10 text-sem-success"
                        >
                            <MaterialDesignIcon icon-name="check-decagram" class="size-12" />
                        </div>
                        <div class="space-y-2">
                            <h2 class="text-3xl font-black tracking-tight text-sem-fg sm:text-4xl">
                                {{ $t("tutorial.ready") }}
                            </h2>
                            <p class="mx-auto max-w-md text-base text-sem-fg-muted sm:text-lg">
                                {{ $t("tutorial.ready_desc") }}
                            </p>
                        </div>
                        <div v-if="interfaceAddedViaTutorial" class="tutorial-notice tutorial-notice--warning">
                            <div class="flex items-start gap-3">
                                <MaterialDesignIcon
                                    icon-name="information-outline"
                                    class="mt-0.5 size-5 shrink-0 text-sem-warning"
                                />
                                <p class="min-w-0 flex-1 text-sm text-sem-fg">{{ $t("tutorial.docker_note") }}</p>
                            </div>
                        </div>
                        <RouterLink
                            :to="{ name: 'documentation' }"
                            class="tutorial-mini-btn tutorial-mini-btn--secondary"
                        >
                            {{ $t("tutorial.learn_more_docs") }}
                            <MaterialDesignIcon icon-name="arrow-right" class="size-4" />
                        </RouterLink>
                    </div>
                </transition>
            </div>
        </div>

        <!-- Footer navigation (pinned below the scroll area) -->
        <div
            class="shrink-0 border-t border-sem-border bg-sem-surface px-4 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3 sm:px-6"
        >
            <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
                <button
                    v-if="currentStep > 1 && currentStep < totalSteps"
                    type="button"
                    class="tutorial-action-btn tutorial-action-btn-secondary"
                    :disabled="tutorialNavBusy"
                    @click="previousStep"
                >
                    <MaterialDesignIcon icon-name="arrow-left" class="size-4" />
                    {{ $t("tutorial.back") }}
                </button>
                <div v-else></div>

                <div class="flex items-center gap-2">
                    <button
                        v-if="currentStep < totalSteps"
                        type="button"
                        class="tutorial-action-btn tutorial-action-btn-ghost"
                        :disabled="tutorialNavBusy"
                        @click="skipTutorial"
                    >
                        {{ $t("tutorial.skip") }}
                    </button>

                    <button
                        v-if="showFooterContinue"
                        type="button"
                        class="tutorial-action-btn tutorial-action-btn-primary"
                        :disabled="
                            tutorialNavBusy ||
                            (currentStep === 2 && identityMode === 'import' && !hasIdentityImportInput)
                        "
                        @click="handlePrimaryAction"
                    >
                        {{ $t("tutorial.next") }}
                        <MaterialDesignIcon icon-name="arrow-right" class="size-4" />
                    </button>

                    <button
                        v-else-if="currentStep === totalSteps"
                        type="button"
                        class="tutorial-action-btn tutorial-action-btn-success"
                        :disabled="finishingTutorial || tutorialNavBusy"
                        @click="finishTutorial"
                    >
                        {{ $t("tutorial.finish_setup") }}
                    </button>
                </div>
            </div>
        </div>
    </AppModal>

    <div v-else class="flex h-full flex-col overflow-hidden bg-sem-surface relative">
        <!-- Progress segments -->
        <div class="shrink-0 px-4 pb-1 pt-3 sm:px-6">
            <div class="flex h-1.5 w-full gap-1" aria-hidden="true">
                <div
                    v-for="step in totalSteps"
                    :key="step"
                    class="h-full flex-1 rounded-full transition-colors duration-300 ease-out"
                    :class="currentStep >= step ? 'bg-sem-accent' : 'bg-sem-border'"
                ></div>
            </div>
        </div>

        <!-- Step counter + language/theme -->
        <div class="tutorial-topbar">
            <span class="tutorial-step-count">
                <span class="font-bold text-sem-accent">{{ currentStep }}</span>
                <span class="text-sem-fg-muted"> / {{ totalSteps }}</span>
            </span>
            <div class="flex items-center gap-0.5">
                <LanguageSelector @language-change="onLanguageChange" />
                <button
                    type="button"
                    class="tutorial-icon-btn"
                    :title="config?.theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
                    :aria-label="config?.theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
                    @click="toggleTheme"
                >
                    <MaterialDesignIcon
                        :icon-name="config?.theme === 'dark' ? 'brightness-6' : 'brightness-4'"
                        class="size-5"
                    />
                </button>
            </div>
        </div>

        <!-- Reticulum stack rebuild in flight (triggered here or elsewhere) -->
        <div
            v-if="reticulumBusy"
            class="flex shrink-0 items-center justify-center gap-2 border-b border-sem-border bg-sem-surface-muted/60 px-4 py-1.5 text-xs font-semibold text-sem-fg-muted sm:px-6"
            role="status"
        >
            <MaterialDesignIcon icon-name="loading" class="size-3.5 animate-spin text-sem-accent" />
            {{ $t("app.reloading_rns") }}
        </div>

        <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-4 sm:px-6 sm:py-6 md:px-10 md:py-8">
            <div class="flex min-h-full w-full flex-col justify-center">
                <transition name="fade-slide" mode="out-in">
                    <!-- Step 1: Welcome -->
                    <div
                        v-if="currentStep === 1"
                        key="page-step1"
                        class="tutorial-step max-w-2xl items-center text-center"
                    >
                        <div class="relative">
                            <div
                                class="absolute -inset-1.5 rotate-6 rounded-[1.6rem] bg-sem-accent/15 sm:-inset-2 sm:rounded-[2rem]"
                            ></div>
                            <div
                                class="relative flex size-24 items-center justify-center rounded-[1.75rem] border border-sem-border bg-sem-surface p-3 shadow-sm sm:size-28 sm:rounded-[2rem] sm:p-4"
                            >
                                <img :src="logoUrl" alt="" class="size-full object-contain" />
                            </div>
                        </div>
                        <div class="space-y-2">
                            <h1 class="text-3xl font-black leading-tight tracking-tight text-sem-fg sm:text-4xl">
                                {{ $t("tutorial.welcome") }} <span class="text-sem-accent">MeshChatX</span>
                            </h1>
                            <p class="mx-auto max-w-xl text-base text-sem-fg-muted sm:text-lg">
                                {{ $t("tutorial.welcome_desc") }}
                            </p>
                        </div>
                        <div
                            v-if="migrationOffer && migrationOffer.show_choice"
                            class="tutorial-notice tutorial-notice--warning"
                        >
                            <div class="flex items-start gap-3">
                                <MaterialDesignIcon
                                    icon-name="alert-outline"
                                    class="mt-0.5 size-5 shrink-0 text-sem-warning"
                                />
                                <div class="min-w-0 flex-1 space-y-1.5">
                                    <div class="text-sm font-bold text-sem-fg">
                                        {{ $t("tutorial.migration_title") }}
                                    </div>
                                    <p class="text-sm text-sem-fg-muted">
                                        {{ $t("tutorial.migration_desc") }}
                                    </p>
                                    <div class="flex flex-col gap-2 pt-2 sm:flex-row sm:justify-end">
                                        <button
                                            type="button"
                                            class="tutorial-action-btn tutorial-action-btn-primary w-full sm:w-auto"
                                            :disabled="migrationBusy"
                                            @click="migrationMigrate"
                                        >
                                            {{ $t("tutorial.migration_migrate") }}
                                        </button>
                                        <button
                                            type="button"
                                            class="tutorial-action-btn tutorial-action-btn-secondary w-full sm:w-auto"
                                            :disabled="migrationBusy"
                                            @click="migrationFresh"
                                        >
                                            {{ $t("tutorial.migration_fresh") }}
                                        </button>
                                    </div>
                                    <p v-if="migrationBusy" class="text-xs text-sem-fg-muted">
                                        {{ $t("tutorial.migration_working") }}
                                    </p>
                                </div>
                            </div>
                        </div>
                        <div
                            v-if="androidStorageSetup && androidStorageSetup.needs_setup_choice"
                            class="tutorial-notice tutorial-notice--info"
                        >
                            <div class="flex items-start gap-3">
                                <MaterialDesignIcon
                                    icon-name="folder-open-outline"
                                    class="mt-0.5 size-5 shrink-0 text-sem-info"
                                />
                                <div class="min-w-0 flex-1 space-y-3">
                                    <div>
                                        <div class="text-sm font-bold text-sem-fg">
                                            {{ $t("android_storage.setup_title") }}
                                        </div>
                                        <p class="mt-0.5 text-sm text-sem-fg-muted">
                                            {{ $t("android_storage.setup_desc") }}
                                        </p>
                                    </div>
                                    <div class="space-y-2">
                                        <label
                                            class="flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition-colors"
                                            :class="
                                                androidStorageSetupChoice === 'external'
                                                    ? 'border-sem-accent bg-sem-accent/5'
                                                    : 'border-sem-border bg-sem-surface hover:border-sem-accent/60'
                                            "
                                        >
                                            <input
                                                v-model="androidStorageSetupChoice"
                                                type="radio"
                                                class="mt-0.5 size-4 shrink-0 accent-sem-accent"
                                                value="external"
                                                :disabled="androidStorageBusy"
                                            />
                                            <span class="min-w-0">
                                                <span class="block text-sm font-semibold text-sem-fg">
                                                    {{ $t("android_storage.setup_external_title") }}
                                                </span>
                                                <span class="mt-0.5 block text-xs text-sem-fg-muted">
                                                    {{ $t("android_storage.setup_external_desc") }}
                                                </span>
                                            </span>
                                        </label>
                                        <label
                                            class="flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition-colors"
                                            :class="
                                                androidStorageSetupChoice === 'internal'
                                                    ? 'border-sem-accent bg-sem-accent/5'
                                                    : 'border-sem-border bg-sem-surface hover:border-sem-accent/60'
                                            "
                                        >
                                            <input
                                                v-model="androidStorageSetupChoice"
                                                type="radio"
                                                class="mt-0.5 size-4 shrink-0 accent-sem-accent"
                                                value="internal"
                                                :disabled="androidStorageBusy"
                                            />
                                            <span class="min-w-0">
                                                <span class="block text-sm font-semibold text-sem-fg">
                                                    {{ $t("android_storage.setup_internal_title") }}
                                                </span>
                                                <span class="mt-0.5 block text-xs text-sem-fg-muted">
                                                    {{ $t("android_storage.setup_internal_desc") }}
                                                </span>
                                            </span>
                                        </label>
                                    </div>
                                    <div class="flex flex-col gap-2 pt-1 sm:flex-row sm:justify-end">
                                        <button
                                            type="button"
                                            class="tutorial-action-btn tutorial-action-btn-primary w-full sm:w-auto"
                                            :disabled="androidStorageBusy || !androidStorageSetupChoice"
                                            @click="applyAndroidStorageSetup"
                                        >
                                            {{ $t("android_storage.setup_continue") }}
                                        </button>
                                    </div>
                                    <p v-if="androidStorageBusy" class="text-xs text-sem-fg-muted">
                                        {{ $t("android_storage.working") }}
                                    </p>
                                </div>
                            </div>
                        </div>
                        <div class="tutorial-feature-grid">
                            <div class="tutorial-feature-card">
                                <MaterialDesignIcon icon-name="shield-lock" class="tutorial-feature-icon" />
                                <div class="min-w-0">
                                    <div class="tutorial-feature-title">{{ $t("tutorial.security") }}</div>
                                    <div class="tutorial-feature-desc">
                                        {{ $t("tutorial.security_desc_page") }}
                                    </div>
                                </div>
                            </div>
                            <div class="tutorial-feature-card">
                                <MaterialDesignIcon icon-name="map-marker-path" class="tutorial-feature-icon" />
                                <div class="min-w-0">
                                    <div class="tutorial-feature-title">{{ $t("tutorial.maps") }}</div>
                                    <div class="tutorial-feature-desc">{{ $t("tutorial.maps_desc_page") }}</div>
                                </div>
                            </div>
                            <div class="tutorial-feature-card">
                                <MaterialDesignIcon icon-name="phone" class="tutorial-feature-icon" />
                                <div class="min-w-0">
                                    <div class="tutorial-feature-title">{{ $t("tutorial.voice") }}</div>
                                    <div class="tutorial-feature-desc">{{ $t("tutorial.voice_desc_page") }}</div>
                                </div>
                            </div>
                            <div class="tutorial-feature-card">
                                <MaterialDesignIcon icon-name="tools" class="tutorial-feature-icon" />
                                <div class="min-w-0">
                                    <div class="tutorial-feature-title">{{ $t("tutorial.tools") }}</div>
                                    <div class="tutorial-feature-desc">{{ $t("tutorial.tools_desc_page") }}</div>
                                </div>
                            </div>
                            <div class="tutorial-feature-card">
                                <MaterialDesignIcon icon-name="database-search" class="tutorial-feature-icon" />
                                <div class="min-w-0">
                                    <div class="tutorial-feature-title">{{ $t("tutorial.archiver") }}</div>
                                    <div class="tutorial-feature-desc">
                                        {{ $t("tutorial.archiver_desc_page") }}
                                    </div>
                                </div>
                            </div>
                            <div class="tutorial-feature-card">
                                <MaterialDesignIcon icon-name="account-cancel" class="tutorial-feature-icon" />
                                <div class="min-w-0">
                                    <div class="tutorial-feature-title">{{ $t("tutorial.banishment") }}</div>
                                    <div class="tutorial-feature-desc">{{ $t("tutorial.banishment_desc") }}</div>
                                </div>
                            </div>
                            <div class="tutorial-feature-card">
                                <MaterialDesignIcon icon-name="keyboard-outline" class="tutorial-feature-icon" />
                                <div class="min-w-0">
                                    <div class="tutorial-feature-title">{{ $t("tutorial.palette") }}</div>
                                    <div class="tutorial-feature-desc">
                                        {{ $t("tutorial.palette_desc_page") }}
                                    </div>
                                </div>
                            </div>
                            <div class="tutorial-feature-card">
                                <MaterialDesignIcon icon-name="translate" class="tutorial-feature-icon" />
                                <div class="min-w-0">
                                    <div class="tutorial-feature-title">{{ $t("tutorial.i18n") }}</div>
                                    <div class="tutorial-feature-desc">{{ $t("tutorial.i18n_desc_page") }}</div>
                                </div>
                            </div>
                        </div>
                        <p class="text-xs text-sem-fg-muted">{{ $t("tutorial.more_features") }}</p>
                    </div>

                    <!-- Step 2: Identity Setup -->
                    <div v-else-if="currentStep === 2" key="page-step2-identity" class="tutorial-step max-w-3xl">
                        <header class="tutorial-step-header">
                            <div class="tutorial-step-icon">
                                <MaterialDesignIcon icon-name="account-key" class="size-6" />
                            </div>
                            <div class="min-w-0">
                                <h2 class="tutorial-step-title">{{ $t("tutorial.identity_title") }}</h2>
                                <p class="tutorial-step-desc">{{ $t("tutorial.identity_desc_page") }}</p>
                            </div>
                        </header>

                        <div v-if="originalIdentityHash" class="tutorial-card">
                            <div class="text-xs font-bold uppercase tracking-wide text-sem-fg-muted">
                                {{ $t("app.identity_hash") }}
                            </div>
                            <div class="mt-1.5 break-all font-mono text-xs text-sem-fg-muted select-all">
                                {{ formatIdentityHash(originalIdentityHash) }}
                            </div>
                            <p class="mt-2 text-xs text-sem-fg-muted">{{ $t("tutorial.identity_new_desc") }}</p>
                        </div>

                        <input
                            ref="identityImportFileInput"
                            type="file"
                            accept=".bin,.key,.identity,application/octet-stream,*/*"
                            class="hidden"
                            @change="onIdentityImportFileChange"
                        />
                        <div
                            class="grid grid-cols-1 gap-3 sm:grid-cols-2"
                            :class="{ 'pointer-events-none opacity-70': tutorialNavBusy }"
                            :aria-busy="tutorialNavBusy"
                        >
                            <button
                                type="button"
                                class="tutorial-choice"
                                :class="identityMode === 'new' ? 'tutorial-choice--selected' : ''"
                                :disabled="tutorialNavBusy"
                                @click="setIdentityMode('new')"
                            >
                                <span class="tutorial-icon-tile bg-sem-accent/10 text-sem-accent">
                                    <MaterialDesignIcon icon-name="account-plus-outline" class="size-5" />
                                </span>
                                <span class="min-w-0 flex-1">
                                    <span class="block font-bold text-sem-fg">
                                        {{ $t("tutorial.identity_new") }}
                                    </span>
                                    <span class="mt-0.5 block text-sm text-sem-fg-muted">
                                        {{ $t("tutorial.identity_new_desc") }}
                                    </span>
                                </span>
                                <span v-if="identityMode === 'new'" class="tutorial-choice__check">
                                    <MaterialDesignIcon icon-name="check" class="size-3.5" />
                                </span>
                            </button>
                            <button
                                type="button"
                                class="tutorial-choice"
                                :class="identityMode === 'import' ? 'tutorial-choice--selected' : ''"
                                :disabled="tutorialNavBusy"
                                @click="setIdentityMode('import')"
                            >
                                <span class="tutorial-icon-tile bg-sem-info/10 text-sem-info">
                                    <MaterialDesignIcon icon-name="file-import-outline" class="size-5" />
                                </span>
                                <span class="min-w-0 flex-1">
                                    <span class="block font-bold text-sem-fg">
                                        {{ $t("tutorial.identity_import") }}
                                    </span>
                                    <span class="mt-0.5 block text-sm text-sem-fg-muted">
                                        {{ $t("tutorial.identity_import_desc") }}
                                    </span>
                                </span>
                                <span v-if="identityMode === 'import'" class="tutorial-choice__check">
                                    <MaterialDesignIcon icon-name="check" class="size-3.5" />
                                </span>
                            </button>
                        </div>
                        <div class="tutorial-card space-y-3">
                            <label class="block text-sm font-semibold text-sem-fg">
                                {{ $t("tutorial.identity_set_name") }}
                            </label>
                            <input
                                v-model="identityName"
                                type="text"
                                :placeholder="defaultUsername"
                                class="input-field"
                                :disabled="tutorialNavBusy"
                            />
                            <div v-if="identityMode === 'import'" class="space-y-3 border-t border-sem-border pt-3">
                                <p class="text-xs text-sem-fg-muted">
                                    {{ $t("tutorial.identity_import_key_only_hint") }}
                                </p>
                                <button
                                    type="button"
                                    class="tutorial-action-btn tutorial-action-btn-secondary w-full justify-center"
                                    :disabled="tutorialNavBusy"
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
                                    class="input-field font-mono"
                                    :placeholder="$t('tutorial.identity_base32_placeholder')"
                                    :disabled="Boolean(identityImportFile) || tutorialNavBusy"
                                    @input="onIdentityImportBase32Input"
                                />
                                <p
                                    v-if="identityImportFile && identityImportBase32.trim()"
                                    class="text-xs text-sem-warning"
                                >
                                    {{ $t("tutorial.identity_file_overrides_base32") }}
                                </p>
                            </div>
                            <p v-if="identityImportError" role="alert" class="text-sm text-sem-danger">
                                {{ identityImportError }}
                            </p>
                        </div>
                    </div>

                    <!-- Step 3: Choose Connection Mode -->
                    <div v-else-if="currentStep === 3" key="page-step3-mode" class="tutorial-step max-w-3xl">
                        <header class="tutorial-step-header">
                            <div class="tutorial-step-icon tutorial-step-icon--info">
                                <MaterialDesignIcon icon-name="access-point-network" class="size-6" />
                            </div>
                            <div class="min-w-0">
                                <h2 class="tutorial-step-title">{{ $t("tutorial.connect") }}</h2>
                                <p class="tutorial-step-desc">{{ $t("tutorial.connect_desc_page") }}</p>
                            </div>
                        </header>

                        <div
                            class="grid grid-cols-1 gap-3 sm:grid-cols-2"
                            :class="{ 'pointer-events-none opacity-70': connectionSetupBusy }"
                            :aria-busy="connectionSetupBusy"
                        >
                            <button
                                type="button"
                                class="tutorial-choice"
                                :class="connectionMode === 'recommended' ? 'tutorial-choice--selected' : ''"
                                :disabled="connectionSetupBusy"
                                @click="useRecommendedMode"
                            >
                                <span class="tutorial-icon-tile bg-sem-info/10 text-sem-info">
                                    <MaterialDesignIcon icon-name="access-point-network" class="size-5" />
                                </span>
                                <span class="min-w-0 flex-1">
                                    <span class="block font-bold text-sem-fg">
                                        {{ $t("tutorial.mode_recommended_title") }}
                                    </span>
                                    <span class="mt-0.5 block text-sm text-sem-fg-muted">
                                        {{ $t("tutorial.mode_recommended_desc") }}
                                    </span>
                                </span>
                                <MaterialDesignIcon
                                    v-if="connectionSetupBusy"
                                    icon-name="loading"
                                    class="size-5 shrink-0 animate-spin self-start text-sem-accent"
                                />
                                <span v-else-if="connectionMode === 'recommended'" class="tutorial-choice__check">
                                    <MaterialDesignIcon icon-name="check" class="size-3.5" />
                                </span>
                            </button>

                            <button
                                type="button"
                                class="tutorial-choice"
                                :class="connectionMode === 'discovery' ? 'tutorial-choice--selected' : ''"
                                :disabled="connectionSetupBusy"
                                @click="useDiscoveryMode"
                            >
                                <span class="tutorial-icon-tile bg-sem-accent/10 text-sem-accent">
                                    <MaterialDesignIcon icon-name="radar" class="size-5" />
                                </span>
                                <span class="min-w-0 flex-1">
                                    <span class="block font-bold text-sem-fg">
                                        {{ $t("tutorial.mode_discovery_title") }}
                                    </span>
                                    <span class="mt-0.5 block text-sm text-sem-fg-muted">
                                        {{ $t("tutorial.mode_discovery_desc") }}
                                    </span>
                                </span>
                                <MaterialDesignIcon
                                    v-if="connectionSetupBusy"
                                    icon-name="loading"
                                    class="size-5 shrink-0 animate-spin self-start text-sem-accent"
                                />
                                <span v-else-if="connectionMode === 'discovery'" class="tutorial-choice__check">
                                    <MaterialDesignIcon icon-name="check" class="size-3.5" />
                                </span>
                            </button>

                            <button
                                type="button"
                                class="tutorial-choice"
                                :class="connectionMode === 'local' ? 'tutorial-choice--selected' : ''"
                                :disabled="connectionSetupBusy"
                                @click="useLocalMode"
                            >
                                <span class="tutorial-icon-tile bg-sem-success/10 text-sem-success">
                                    <MaterialDesignIcon icon-name="lan" class="size-5" />
                                </span>
                                <span class="min-w-0 flex-1">
                                    <span class="block font-bold text-sem-fg">
                                        {{ $t("tutorial.mode_local_title") }}
                                    </span>
                                    <span class="mt-0.5 block text-sm text-sem-fg-muted">
                                        {{ $t("tutorial.mode_local_desc") }}
                                    </span>
                                </span>
                                <MaterialDesignIcon
                                    v-if="connectionSetupBusy"
                                    icon-name="loading"
                                    class="size-5 shrink-0 animate-spin self-start text-sem-accent"
                                />
                                <span v-else-if="connectionMode === 'local'" class="tutorial-choice__check">
                                    <MaterialDesignIcon icon-name="check" class="size-3.5" />
                                </span>
                            </button>

                            <button
                                type="button"
                                class="tutorial-choice"
                                :class="connectionMode === 'manual' ? 'tutorial-choice--selected' : ''"
                                :disabled="connectionSetupBusy"
                                @click="useManualMode"
                            >
                                <span class="tutorial-icon-tile bg-sem-surface-muted text-sem-fg-muted">
                                    <MaterialDesignIcon icon-name="cog-outline" class="size-5" />
                                </span>
                                <span class="min-w-0 flex-1">
                                    <span class="block font-bold text-sem-fg">
                                        {{ $t("tutorial.mode_manual_title") }}
                                    </span>
                                    <span class="mt-0.5 block text-sm text-sem-fg-muted">
                                        {{ $t("tutorial.mode_manual_desc") }}
                                    </span>
                                </span>
                                <span v-if="connectionMode === 'manual'" class="tutorial-choice__check">
                                    <MaterialDesignIcon icon-name="check" class="size-3.5" />
                                </span>
                            </button>
                        </div>

                        <p class="text-xs text-center text-sem-fg-muted">{{ $t("tutorial.mode_change_later") }}</p>
                    </div>

                    <!-- Step 4: Bootstrap Selection -->
                    <div v-else-if="currentStep === 4" key="page-step4-bootstrap" class="tutorial-step max-w-4xl">
                        <header class="tutorial-step-header">
                            <div class="tutorial-step-icon">
                                <MaterialDesignIcon icon-name="server-network" class="size-6" />
                            </div>
                            <div class="min-w-0">
                                <h2 class="tutorial-step-title">{{ $t("tutorial.bootstrap_title") }}</h2>
                                <p class="tutorial-step-desc">{{ $t("tutorial.bootstrap_desc_page") }}</p>
                            </div>
                        </header>

                        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                            <button
                                type="button"
                                class="tutorial-action-btn tutorial-action-btn-secondary"
                                :disabled="bootstrapPickBusy"
                                @click="pickRandomTcpBootstraps"
                            >
                                <MaterialDesignIcon
                                    v-if="bootstrapPickBusy"
                                    icon-name="loading"
                                    class="size-4 animate-spin text-sem-accent"
                                />
                                <MaterialDesignIcon v-else icon-name="shuffle-variant" class="size-4" />
                                {{ $t("tutorial.bootstrap_pick_random_tcp") }}
                            </button>
                            <div
                                v-if="bootstrapSelectedLabels.length > 0"
                                class="w-full rounded-xl border border-sem-border bg-sem-surface-muted/60 px-3 py-2 sm:max-w-xs"
                            >
                                <div class="text-[11px] font-bold uppercase tracking-wide text-sem-fg-muted">
                                    {{ $t("tutorial.bootstrap_selected_nodes_heading") }}
                                </div>
                                <ul
                                    class="mt-1 max-h-24 space-y-0.5 overflow-y-auto text-xs text-sem-fg custom-scrollbar"
                                >
                                    <li
                                        v-for="(label, idx) in bootstrapSelectedLabels"
                                        :key="selectedBootstrapKeys[idx]"
                                    >
                                        {{ label }}
                                    </li>
                                </ul>
                            </div>
                        </div>

                        <div class="tutorial-card flex items-start gap-3">
                            <div class="flex shrink-0 items-start pt-0.5">
                                <Toggle
                                    v-model="defaultBootstrapOnly"
                                    :disabled="bootstrapActionBusy"
                                    @update:model-value="persistDefaultBootstrapOnly"
                                />
                            </div>
                            <div class="min-w-0 flex-1">
                                <div class="text-sm font-semibold text-sem-fg">
                                    {{ $t("tutorial.bootstrap_only_label") }}
                                </div>
                                <p class="mt-1 text-xs leading-relaxed text-sem-fg-muted">
                                    {{ $t("tutorial.bootstrap_only_hint") }}
                                </p>
                            </div>
                        </div>

                        <div class="tutorial-notice tutorial-notice--info">
                            <div class="flex items-start gap-3">
                                <MaterialDesignIcon
                                    icon-name="lan-connect"
                                    class="mt-0.5 size-5 shrink-0 text-sem-info"
                                />
                                <div class="min-w-0 flex-1 space-y-3">
                                    <div>
                                        <div class="text-sm font-bold text-sem-fg">
                                            {{ $t("tutorial.custom_interfaces") }}
                                        </div>
                                        <p class="mt-0.5 text-sm text-sem-fg-muted">
                                            {{
                                                isPage
                                                    ? $t("tutorial.custom_interfaces_desc_page")
                                                    : $t("tutorial.custom_interfaces_desc")
                                            }}
                                        </p>
                                    </div>
                                    <button
                                        type="button"
                                        class="tutorial-mini-btn tutorial-mini-btn--secondary"
                                        :disabled="tutorialNavBusy"
                                        @click="gotoAddInterface()"
                                    >
                                        {{ $t("tutorial.open_interfaces") }}
                                        <MaterialDesignIcon icon-name="arrow-right" class="size-4" />
                                    </button>
                                </div>
                            </div>
                        </div>

                        <template v-if="hasAnyBootstrapsToShow">
                            <div class="relative">
                                <MaterialDesignIcon
                                    icon-name="magnify"
                                    class="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-sem-fg-muted"
                                />
                                <input
                                    v-model="bootstrapListSearch"
                                    type="search"
                                    autocomplete="off"
                                    :placeholder="$t('tutorial.bootstrap_search_placeholder')"
                                    class="search-input"
                                />
                                <button
                                    v-if="bootstrapListSearch"
                                    type="button"
                                    class="absolute right-1.5 top-1/2 flex size-8 -translate-y-1/2 items-center justify-center rounded-full text-sem-fg-muted transition-colors hover:bg-sem-surface-muted hover:text-sem-fg"
                                    :title="$t('tutorial.bootstrap_search_clear')"
                                    :aria-label="$t('tutorial.bootstrap_search_clear')"
                                    @click="bootstrapListSearch = ''"
                                >
                                    <MaterialDesignIcon icon-name="close" class="size-4" />
                                </button>
                            </div>

                            <div
                                class="grid grid-cols-1 items-start gap-4 lg:grid-cols-2"
                                :aria-busy="bootstrapActionBusy"
                            >
                                <div
                                    v-if="sortedDiscoveredInterfaces.length > 0"
                                    class="tutorial-section tutorial-section--discovered"
                                >
                                    <button
                                        type="button"
                                        class="tutorial-section__head"
                                        :aria-expanded="bootstrapDiscoveredSectionOpen"
                                        @click="bootstrapDiscoveredSectionOpen = !bootstrapDiscoveredSectionOpen"
                                    >
                                        <span
                                            class="flex size-8 shrink-0 items-center justify-center rounded-lg bg-sem-success/10 text-sem-success"
                                        >
                                            <MaterialDesignIcon icon-name="radar" class="size-4" />
                                        </span>
                                        <span class="text-sm font-bold text-sem-fg">{{
                                            $t("tutorial.bootstrap_discovered")
                                        }}</span>
                                        <span class="tutorial-count-chip">{{ sortedDiscoveredInterfaces.length }}</span>
                                        <MaterialDesignIcon
                                            :icon-name="bootstrapDiscoveredSectionOpen ? 'chevron-up' : 'chevron-down'"
                                            class="ml-auto size-5 shrink-0 text-sem-fg-muted"
                                        />
                                    </button>
                                    <div v-show="bootstrapDiscoveredSectionOpen" class="px-4 pb-4">
                                        <p
                                            v-if="
                                                bootstrapListSearch &&
                                                sortedDiscoveredInterfaces.length > 0 &&
                                                filteredDiscoveredForBootstrap.length === 0
                                            "
                                            class="text-xs text-sem-fg-muted"
                                        >
                                            {{ $t("tutorial.bootstrap_search_no_match") }}
                                        </p>
                                        <div
                                            v-else
                                            class="max-h-72 space-y-2 overflow-y-auto pt-1 custom-scrollbar"
                                            :class="{ 'pointer-events-none opacity-60': bootstrapActionBusy }"
                                        >
                                            <label
                                                v-for="iface in filteredDiscoveredForBootstrap"
                                                :key="iface.discovery_hash || iface.name"
                                                class="tutorial-bootstrap-row"
                                                :class="
                                                    isBootstrapSelected(`disc:${iface.discovery_hash || iface.name}`)
                                                        ? 'tutorial-bootstrap-row--selected'
                                                        : ''
                                                "
                                            >
                                                <input
                                                    type="checkbox"
                                                    class="size-4 shrink-0 accent-sem-accent"
                                                    :disabled="bootstrapActionBusy"
                                                    :checked="
                                                        isBootstrapSelected(
                                                            `disc:${iface.discovery_hash || iface.name}`
                                                        )
                                                    "
                                                    @change="
                                                        toggleBootstrap(`disc:${iface.discovery_hash || iface.name}`)
                                                    "
                                                />
                                                <MaterialDesignIcon
                                                    :icon-name="getDiscoveryIcon(iface)"
                                                    class="size-5 shrink-0 text-sem-success"
                                                />
                                                <span class="min-w-0 flex-1">
                                                    <span class="block truncate text-sm font-semibold text-sem-fg">
                                                        {{ iface.name }}
                                                    </span>
                                                    <span
                                                        class="mt-0.5 block truncate font-mono text-[11px] text-sem-fg-muted"
                                                    >
                                                        <span v-if="iface.reachable_on"
                                                            >{{ iface.reachable_on
                                                            }}<span v-if="iface.port">:{{ iface.port }}</span></span
                                                        >
                                                        <span v-else>{{ iface.type }}</span>
                                                        <span class="ml-2 capitalize">{{ iface.status }}</span>
                                                    </span>
                                                </span>
                                            </label>
                                        </div>
                                    </div>
                                </div>

                                <div
                                    class="tutorial-section tutorial-section--community"
                                    :class="[sortedDiscoveredInterfaces.length === 0 ? 'lg:col-span-2' : '']"
                                >
                                    <button
                                        type="button"
                                        class="tutorial-section__head"
                                        :aria-expanded="bootstrapCommunitySectionOpen"
                                        @click="bootstrapCommunitySectionOpen = !bootstrapCommunitySectionOpen"
                                    >
                                        <span
                                            class="flex size-8 shrink-0 items-center justify-center rounded-lg bg-sem-accent/10 text-sem-accent"
                                        >
                                            <MaterialDesignIcon icon-name="web" class="size-4" />
                                        </span>
                                        <span class="text-sm font-bold text-sem-fg">{{
                                            $t("tutorial.bootstrap_community")
                                        }}</span>
                                        <span class="tutorial-count-chip">{{ communityInterfaces.length }}</span>
                                        <MaterialDesignIcon
                                            :icon-name="bootstrapCommunitySectionOpen ? 'chevron-up' : 'chevron-down'"
                                            class="ml-auto size-5 shrink-0 text-sem-fg-muted"
                                        />
                                    </button>
                                    <div v-show="bootstrapCommunitySectionOpen" class="px-4 pb-4">
                                        <p
                                            v-if="
                                                bootstrapListSearch &&
                                                communityInterfaces.length > 0 &&
                                                filteredCommunityForBootstrap.length === 0
                                            "
                                            class="text-xs text-sem-fg-muted"
                                        >
                                            {{ $t("tutorial.bootstrap_search_no_match") }}
                                        </p>
                                        <div
                                            v-else
                                            class="max-h-72 space-y-2 overflow-y-auto pt-1 custom-scrollbar"
                                            :class="{ 'pointer-events-none opacity-60': bootstrapActionBusy }"
                                        >
                                            <label
                                                v-for="iface in filteredCommunityForBootstrap"
                                                :key="iface.name"
                                                class="tutorial-bootstrap-row"
                                                :class="
                                                    isBootstrapSelected(`comm:${iface.name}`)
                                                        ? 'tutorial-bootstrap-row--selected'
                                                        : ''
                                                "
                                            >
                                                <input
                                                    type="checkbox"
                                                    class="size-4 shrink-0 accent-sem-accent"
                                                    :disabled="bootstrapActionBusy"
                                                    :checked="isBootstrapSelected(`comm:${iface.name}`)"
                                                    @change="toggleBootstrap(`comm:${iface.name}`)"
                                                />
                                                <MaterialDesignIcon
                                                    icon-name="server-network"
                                                    class="size-5 shrink-0 text-sem-accent"
                                                />
                                                <span class="min-w-0 flex-1">
                                                    <span class="block truncate text-sm font-semibold text-sem-fg">
                                                        {{ iface.name }}
                                                    </span>
                                                    <span
                                                        class="block truncate font-mono text-[11px] text-sem-fg-muted"
                                                    >
                                                        {{ iface.target_host
                                                        }}<span v-if="iface.target_port">:{{ iface.target_port }}</span>
                                                    </span>
                                                </span>
                                                <span v-if="iface.online" class="tutorial-online-badge">{{
                                                    $t("tutorial.online")
                                                }}</span>
                                            </label>
                                            <div v-if="loadingInterfaces" class="flex justify-center py-3">
                                                <MaterialDesignIcon
                                                    icon-name="loading"
                                                    class="size-6 animate-spin text-sem-accent"
                                                />
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </template>
                        <div v-else class="tutorial-notice tutorial-notice--info">
                            <div class="flex items-start gap-3">
                                <MaterialDesignIcon icon-name="radar" class="mt-0.5 size-5 shrink-0 text-sem-info" />
                                <div class="min-w-0 flex-1">
                                    <div class="text-sm font-bold text-sem-fg">
                                        {{ $t("tutorial.bootstrap_empty_title") }}
                                    </div>
                                    <p class="mt-0.5 text-sm text-sem-fg-muted">
                                        {{ $t("tutorial.bootstrap_empty") }}
                                    </p>
                                </div>
                            </div>
                        </div>

                        <div
                            class="sticky bottom-0 -mx-4 border-t border-sem-border bg-sem-surface px-4 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3 sm:-mx-6 sm:px-6 md:-mx-10 md:px-10"
                            :aria-busy="bootstrapActionBusy"
                        >
                            <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                                <p class="text-xs text-sem-fg-muted">
                                    {{
                                        $t("tutorial.bootstrap_selected", {
                                            count: selectedBootstrapCount,
                                        })
                                    }}
                                </p>
                                <div class="flex flex-col gap-2 sm:flex-row">
                                    <button
                                        type="button"
                                        class="tutorial-action-btn tutorial-action-btn-secondary w-full sm:w-auto"
                                        :disabled="bootstrapActionBusy"
                                        @click="skipBootstraps"
                                    >
                                        {{ $t("tutorial.bootstrap_skip") }}
                                    </button>
                                    <button
                                        type="button"
                                        class="tutorial-action-btn tutorial-action-btn-success w-full sm:w-auto"
                                        :disabled="bootstrapActionBusy || selectedBootstrapCount === 0"
                                        @click="confirmBootstraps"
                                    >
                                        <MaterialDesignIcon
                                            v-if="bootstrapActionBusy"
                                            icon-name="loading"
                                            class="size-4 animate-spin"
                                        />
                                        {{ $t("tutorial.bootstrap_confirm") }}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Step 5: Propagation Mode -->
                    <div v-else-if="currentStep === 5" key="page-step5-prop" class="tutorial-step max-w-3xl">
                        <header class="tutorial-step-header">
                            <div class="tutorial-step-icon">
                                <MaterialDesignIcon icon-name="bullseye" class="size-6" />
                            </div>
                            <div class="min-w-0">
                                <h2 class="tutorial-step-title">{{ $t("tutorial.propagation") }}</h2>
                                <p class="tutorial-step-desc">{{ $t("tutorial.propagation_desc") }}</p>
                            </div>
                        </header>

                        <div class="tutorial-card mx-auto w-full max-w-xl text-center">
                            <div
                                class="mx-auto mb-4 flex size-12 items-center justify-center rounded-2xl bg-sem-accent/10 text-sem-accent"
                            >
                                <MaterialDesignIcon icon-name="server-network" class="size-6" />
                            </div>
                            <div class="text-base font-bold text-sem-fg">
                                {{ $t("tutorial.propagation_question") }}
                            </div>
                            <p class="mt-1.5 text-sm text-sem-fg-muted">{{ $t("tutorial.propagation_auto") }}</p>
                            <div class="mt-5 flex flex-col gap-2.5 sm:flex-row sm:justify-center">
                                <button
                                    type="button"
                                    class="tutorial-action-btn tutorial-action-btn-primary w-full sm:w-auto"
                                    :disabled="tutorialNavBusy"
                                    @click="enableAutoPropagation"
                                >
                                    <MaterialDesignIcon
                                        v-if="savingPropagation"
                                        icon-name="loading"
                                        class="size-4 animate-spin"
                                    />
                                    {{ $t("tutorial.propagation_enable_auto") }}
                                </button>
                                <button
                                    type="button"
                                    class="tutorial-action-btn tutorial-action-btn-secondary w-full sm:w-auto"
                                    :disabled="tutorialNavBusy"
                                    @click="nextStep"
                                >
                                    {{ $t("tutorial.propagation_skip_auto") }}
                                </button>
                            </div>
                            <div class="mt-5 border-t border-sem-border pt-4 text-left">
                                <div class="text-sm font-bold text-sem-fg">
                                    {{ $t("tutorial.propagation_manual") }}
                                </div>
                                <p class="mt-1 text-xs leading-relaxed text-sem-fg-muted">
                                    {{ $t("tutorial.propagation_manual_desc") }}
                                </p>
                            </div>
                        </div>
                    </div>

                    <!-- Step 6: Learn & Create -->
                    <div v-else-if="currentStep === 6" key="page-step6-tools" class="tutorial-step max-w-3xl">
                        <header class="tutorial-step-header">
                            <div class="tutorial-step-icon tutorial-step-icon--info">
                                <MaterialDesignIcon icon-name="lightbulb-on" class="size-6" />
                            </div>
                            <div class="min-w-0">
                                <h2 class="tutorial-step-title">{{ $t("tutorial.learn_create") }}</h2>
                                <p class="tutorial-step-desc">{{ $t("tutorial.learn_create_desc_page") }}</p>
                            </div>
                        </header>

                        <div class="mx-auto flex w-full max-w-2xl flex-col gap-4">
                            <div class="tutorial-card">
                                <div class="flex items-start gap-4">
                                    <span class="tutorial-icon-tile bg-sem-accent/10 text-sem-accent">
                                        <MaterialDesignIcon icon-name="book-open-variant" class="size-5" />
                                    </span>
                                    <div class="min-w-0 flex-1">
                                        <div class="font-bold text-sem-fg">{{ $t("tutorial.documentation") }}</div>
                                        <p class="mt-0.5 text-sm text-sem-fg-muted">
                                            {{ $t("tutorial.documentation_desc_page") }}
                                        </p>
                                        <div class="mt-3 flex flex-wrap gap-2">
                                            <a
                                                href="/meshchatx-docs/index.html"
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                class="tutorial-mini-btn tutorial-mini-btn--primary"
                                            >
                                                {{ $t("tutorial.read_meshchatx_docs") }}
                                            </a>
                                            <a
                                                :href="reticulumBundledDocsUrl"
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                class="tutorial-mini-btn tutorial-mini-btn--secondary"
                                            >
                                                {{ $t("tutorial.reticulum_manual") }}
                                            </a>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="tutorial-card">
                                <div class="flex items-start gap-4">
                                    <span class="tutorial-icon-tile bg-sem-warning/10 text-sem-warning">
                                        <MaterialDesignIcon icon-name="file-document-edit-outline" class="size-5" />
                                    </span>
                                    <div class="min-w-0 flex-1">
                                        <div class="font-bold text-sem-fg">{{ $t("tutorial.micron_editor") }}</div>
                                        <p class="mt-0.5 text-sm text-sem-fg-muted">
                                            {{ $t("tutorial.micron_editor_desc_page") }}
                                        </p>
                                        <div class="mt-3 flex flex-wrap gap-2">
                                            <button
                                                type="button"
                                                class="tutorial-mini-btn tutorial-mini-btn--primary"
                                                @click="gotoRoute('micron-editor')"
                                            >
                                                {{ $t("tutorial.open_micron_editor") }}
                                            </button>
                                            <button
                                                type="button"
                                                class="tutorial-mini-btn tutorial-mini-btn--secondary"
                                                @click="gotoRoute('mesh-server')"
                                            >
                                                {{ $t("tutorial.open_mesh_server") }}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div
                                class="tutorial-link-card"
                                role="button"
                                tabindex="0"
                                @click="gotoRoute('identities')"
                                @keydown.enter="gotoRoute('identities')"
                            >
                                <span class="tutorial-icon-tile bg-sem-info/10 text-sem-info">
                                    <MaterialDesignIcon icon-name="account-multiple-outline" class="size-5" />
                                </span>
                                <span class="min-w-0 flex-1">
                                    <span class="block font-bold text-sem-fg">
                                        {{ $t("tutorial.identities_card_title") }}
                                    </span>
                                    <span class="mt-0.5 block text-sm text-sem-fg-muted">
                                        {{ $t("tutorial.identities_card_desc_page") }}
                                    </span>
                                </span>
                                <MaterialDesignIcon
                                    icon-name="chevron-right"
                                    class="mt-1 size-5 shrink-0 text-sem-fg-muted"
                                />
                            </div>

                            <div
                                class="tutorial-link-card"
                                role="button"
                                tabindex="0"
                                @click="gotoRoute('archives')"
                                @keydown.enter="gotoRoute('archives')"
                            >
                                <span class="tutorial-icon-tile bg-sem-success/10 text-sem-success">
                                    <MaterialDesignIcon icon-name="archive-outline" class="size-5" />
                                </span>
                                <span class="min-w-0 flex-1">
                                    <span class="block font-bold text-sem-fg">{{ $t("tutorial.archiver") }}</span>
                                    <span class="mt-0.5 block text-sm text-sem-fg-muted">
                                        {{ $t("tutorial.archiver_desc_page") }}
                                    </span>
                                </span>
                                <MaterialDesignIcon
                                    icon-name="chevron-right"
                                    class="mt-1 size-5 shrink-0 text-sem-fg-muted"
                                />
                            </div>
                        </div>

                        <div class="mx-auto w-full max-w-2xl">
                            <p class="mb-3 text-center text-xs font-semibold text-sem-fg-muted">
                                {{ $t("tutorial.learn_create_more") }}
                            </p>
                            <div class="grid grid-cols-2 gap-2.5">
                                <div
                                    class="tutorial-mini-card"
                                    role="button"
                                    tabindex="0"
                                    @click="gotoRoute('nomadnetwork')"
                                    @keydown.enter="gotoRoute('nomadnetwork')"
                                >
                                    <MaterialDesignIcon icon-name="earth" class="size-5 shrink-0 text-sem-info" />
                                    <span class="min-w-0">
                                        <span class="block text-xs font-bold leading-tight text-sem-fg">
                                            {{ $t("tutorial.paper_messages") }}
                                        </span>
                                        <span
                                            class="mt-0.5 block text-[11px] leading-snug text-sem-fg-muted line-clamp-3"
                                        >
                                            {{ $t("tutorial.paper_messages_desc") }}
                                        </span>
                                    </span>
                                </div>

                                <div
                                    class="tutorial-mini-card"
                                    role="button"
                                    tabindex="0"
                                    @click="gotoRoute('messages')"
                                    @keydown.enter="gotoRoute('messages')"
                                >
                                    <MaterialDesignIcon
                                        icon-name="message-text-outline"
                                        class="size-5 shrink-0 text-sem-success"
                                    />
                                    <span class="min-w-0">
                                        <span class="block text-xs font-bold leading-tight text-sem-fg">
                                            {{ $t("tutorial.send_messages") }}
                                        </span>
                                        <span
                                            class="mt-0.5 block text-[11px] leading-snug text-sem-fg-muted line-clamp-3"
                                        >
                                            {{ $t("tutorial.send_messages_desc") }}
                                        </span>
                                    </span>
                                </div>

                                <div
                                    class="tutorial-mini-card"
                                    role="button"
                                    tabindex="0"
                                    @click="gotoRoute('network-visualiser')"
                                    @keydown.enter="gotoRoute('network-visualiser')"
                                >
                                    <MaterialDesignIcon icon-name="hub" class="size-5 shrink-0 text-sem-success" />
                                    <span class="min-w-0">
                                        <span class="block text-xs font-bold leading-tight text-sem-fg">
                                            {{ $t("tutorial.explore_nodes") }}
                                        </span>
                                        <span
                                            class="mt-0.5 block text-[11px] leading-snug text-sem-fg-muted line-clamp-3"
                                        >
                                            {{ $t("tutorial.explore_nodes_desc") }}
                                        </span>
                                    </span>
                                </div>

                                <div
                                    class="tutorial-mini-card"
                                    role="button"
                                    tabindex="0"
                                    @click="gotoRoute('call')"
                                    @keydown.enter="gotoRoute('call')"
                                >
                                    <MaterialDesignIcon
                                        icon-name="phone-in-talk-outline"
                                        class="size-5 shrink-0 text-sem-danger"
                                    />
                                    <span class="min-w-0">
                                        <span class="block text-xs font-bold leading-tight text-sem-fg">
                                            {{ $t("tutorial.voice_calls") }}
                                        </span>
                                        <span
                                            class="mt-0.5 block text-[11px] leading-snug text-sem-fg-muted line-clamp-3"
                                        >
                                            {{ $t("tutorial.voice_calls_desc") }}
                                        </span>
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Step 7: Privacy -->
                    <div v-else-if="currentStep === 7" key="page-step7-privacy" class="tutorial-step max-w-3xl">
                        <TutorialPrivacyStep />
                    </div>

                    <!-- Step 8: Finish -->
                    <div
                        v-else-if="currentStep === 8"
                        key="page-step8-finish"
                        class="tutorial-step max-w-2xl items-center text-center"
                    >
                        <div
                            class="flex size-24 items-center justify-center rounded-full bg-sem-success/10 text-sem-success"
                        >
                            <MaterialDesignIcon icon-name="check-decagram" class="size-12" />
                        </div>
                        <div class="space-y-2">
                            <h2 class="text-3xl font-black tracking-tight text-sem-fg sm:text-4xl">
                                {{ $t("tutorial.ready") }}
                            </h2>
                            <p class="mx-auto max-w-md text-base text-sem-fg-muted sm:text-lg">
                                {{ $t("tutorial.ready_desc_page") }}
                            </p>
                        </div>
                        <div class="tutorial-notice tutorial-notice--warning">
                            <div class="flex items-start gap-3">
                                <MaterialDesignIcon
                                    icon-name="information-outline"
                                    class="mt-0.5 size-5 shrink-0 text-sem-warning"
                                />
                                <div class="min-w-0 flex-1 space-y-1">
                                    <div class="text-sm font-bold text-sem-fg">
                                        {{ $t("tutorial.restart_required") }}
                                    </div>
                                    <p class="text-sm text-sem-fg-muted">{{ $t("tutorial.restart_desc_page") }}</p>
                                </div>
                            </div>
                        </div>
                        <RouterLink
                            :to="{ name: 'documentation' }"
                            class="tutorial-mini-btn tutorial-mini-btn--secondary"
                        >
                            {{ $t("tutorial.learn_more_docs") }}
                            <MaterialDesignIcon icon-name="arrow-right" class="size-4" />
                        </RouterLink>
                    </div>
                </transition>
            </div>
        </div>

        <!-- Footer navigation (pinned below the scroll area) -->
        <div
            class="shrink-0 border-t border-sem-border bg-sem-surface px-4 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3 sm:px-6"
        >
            <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
                <button
                    v-if="currentStep > 1 && currentStep < totalSteps"
                    type="button"
                    class="tutorial-action-btn tutorial-action-btn-secondary"
                    :disabled="tutorialNavBusy"
                    @click="previousStep"
                >
                    <MaterialDesignIcon icon-name="arrow-left" class="size-4" />
                    {{ $t("tutorial.back") }}
                </button>
                <div v-else></div>

                <div class="flex items-center gap-2">
                    <button
                        v-if="currentStep < totalSteps"
                        type="button"
                        class="tutorial-action-btn tutorial-action-btn-ghost"
                        :disabled="tutorialNavBusy"
                        @click="skipTutorial"
                    >
                        {{ $t("tutorial.skip_setup") }}
                    </button>

                    <button
                        v-if="showFooterContinue"
                        type="button"
                        class="tutorial-action-btn tutorial-action-btn-primary"
                        :disabled="
                            tutorialNavBusy ||
                            (currentStep === 2 && identityMode === 'import' && !hasIdentityImportInput)
                        "
                        @click="handlePrimaryAction"
                    >
                        {{ $t("tutorial.continue") }}
                        <MaterialDesignIcon icon-name="arrow-right" class="size-4" />
                    </button>

                    <button
                        v-else-if="currentStep === totalSteps"
                        type="button"
                        class="tutorial-action-btn tutorial-action-btn-success"
                        :disabled="finishingTutorial || tutorialNavBusy"
                        @click="finishTutorial"
                    >
                        {{ $t("tutorial.finish_setup") }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { getCurrentInstance } from "vue";
import { useConfigStore } from "../js/stores/configStore";
import { useInterfaceChangesStore } from "../js/stores/interfaceChangesStore.js";
import logoUrl from "../assets/images/logo.png";
import AndroidStorageBridge from "../js/AndroidStorageBridge.js";
import ToastUtils from "../js/ToastUtils";
import DialogUtils from "../js/DialogUtils";
import GlobalEmitter from "../js/GlobalEmitter";
import { apiPath, EMITTER_EVENTS, WS_EVENTS } from "../js/constants";
import { onWsEvent, offWsEvent } from "../js/registries/wsEventRegistry.js";
import { bundledReticulumDocsUrl } from "../js/reticulumDocsEntryUrl.js";
import { useTutorialIdentity } from "../js/tutorial/useTutorialIdentity.js";
import AppModal from "./AppModal.vue";
import LanguageSelector from "./LanguageSelector.vue";
import { normalizeUiLocaleCode, setLocale } from "../js/localeLoader.js";
import MaterialDesignIcon from "./MaterialDesignIcon.vue";
import Toggle from "./forms/Toggle.vue";
import TutorialPrivacyStep from "./TutorialPrivacyStep.vue";

// Bootstrap adds run sequentially and each one churns the Reticulum stack;
// cap how many onboarding can pick so a huge discovery list cannot
// soft-lock the tutorial.
const MAX_BOOTSTRAP_SELECTIONS = 10;

export default {
    name: "TutorialModal",
    components: {
        AppModal,
        LanguageSelector,
        MaterialDesignIcon,
        Toggle,
        TutorialPrivacyStep,
    },
    setup() {
        const inst = getCurrentInstance();
        return {
            ...useTutorialIdentity({
                t: (key, params) => inst?.proxy.$t(key, params),
                goToStep: (step) => {
                    if (inst?.proxy) {
                        inst.proxy.currentStep = step;
                    }
                },
            }),
        };
    },
    data() {
        return {
            visible: false,
            currentStep: 1,
            totalSteps: 8,
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
            reticulumReloading: false,
            identityActionBusy: false,
            discoveredInterfaces: [],
            discoveredActive: [],
            loadingDiscovered: false,
            savingDiscovery: false,
            savingPropagation: false,
            discoveryInterval: null,
            markingSeen: false,
            windowWidth: typeof window !== "undefined" ? window.innerWidth : 1024,
            defaultBootstrapOnly: false,
            bootstrapListSearch: "",
            bootstrapDiscoveredSectionOpen: true,
            bootstrapCommunitySectionOpen: true,
            bootstrapAutoPickDone: false,
            pickingRandomBootstraps: false,
            addingRecommended: false,
            migrationOffer: null,
            migrationBusy: false,
            androidStorageSetup: null,
            androidStorageSetupChoice: "external",
            androidStorageBusy: false,
            androidStorageBridge: null,
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
            return useConfigStore().config;
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
        bootstrapSelectedLabels() {
            return this.selectedBootstrapKeys.map((k) => this.bootstrapDisplayLabelForKey(k)).filter(Boolean);
        },
        showFooterContinue() {
            if (this.currentStep === 3 || this.currentStep === 4) {
                return false;
            }
            return this.currentStep < this.totalSteps;
        },
        reticulumBusy() {
            // Local reload call in flight, or the backend broadcast a
            // reticulum_reload_status with in_progress for a reload triggered
            // anywhere else (settings, interfaces page, discovery PATCH).
            return this.reloadingReticulum || this.reticulumReloading;
        },
        connectionSetupBusy() {
            return this.addingRecommended || this.savingDiscovery || this.addingLocal || this.reticulumBusy;
        },
        bootstrapPickBusy() {
            return (
                this.pickingRandomBootstraps || this.loadingInterfaces || this.loadingDiscovered || this.reticulumBusy
            );
        },
        bootstrapActionBusy() {
            return this.pickingRandomBootstraps || this.addingBootstraps || this.reticulumBusy;
        },
        tutorialNavBusy() {
            return (
                this.connectionSetupBusy ||
                this.bootstrapActionBusy ||
                this.savingPropagation ||
                this.finishingTutorial ||
                this.identityImportInProgress ||
                this.identityActionBusy ||
                this.migrationBusy ||
                this.androidStorageBusy
            );
        },
    },
    watch: {
        visible(value) {
            if (!value) {
                this.onVisibleUpdate(false);
            }
        },
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
        offWsEvent(WS_EVENTS.RETICULUM_RELOAD_STATUS, this.onReticulumReloadStatus);
        GlobalEmitter.off(EMITTER_EVENTS.WEBSOCKET_RECONNECTED, this.onWebsocketReconnected);
    },
    mounted() {
        this.onWindowResize = () => {
            this.windowWidth = window.innerWidth;
        };
        window.addEventListener("resize", this.onWindowResize, { passive: true });
        // The backend broadcasts reticulum_reload_status for every stack
        // reload, including ones this wizard did not trigger. Track it so
        // mutating controls lock while the stack is being rebuilt.
        onWsEvent(WS_EVENTS.RETICULUM_RELOAD_STATUS, this.onReticulumReloadStatus);
        GlobalEmitter.on(EMITTER_EVENTS.WEBSOCKET_RECONNECTED, this.onWebsocketReconnected);
        if (this.isPage) {
            this.loadIdentitySetupDefaults();
            this.loadDiscoveryBootstrapDefaults();
            this.loadCommunityInterfaces();
            this.loadDiscoveredInterfaces();
            this.refreshMigrationOffer();
            this.refreshAndroidStorageSetup();
            this.discoveryInterval = setInterval(() => {
                this.loadDiscoveredInterfaces();
            }, 5000);
        }
    },
    methods: {
        async toggleTheme() {
            const newTheme = this.config.theme === "dark" ? "light" : "dark";
            try {
                await window.api.patch(apiPath("/config"), {
                    theme: newTheme,
                });
                useConfigStore().config.theme = newTheme;
            } catch (e) {
                console.error("Failed to update theme:", e);
            }
        },
        async onLanguageChange(langCode) {
            const code = normalizeUiLocaleCode(langCode);
            try {
                await setLocale(this.$i18n, code);
                await window.api.patch(apiPath("/config"), {
                    language: code,
                });
                useConfigStore().config.language = code;
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
            await this.refreshAndroidStorageSetup();
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
                const response = await window.api.get(apiPath("/community-interfaces"));
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
                const response = await window.api.get(apiPath("/reticulum/discovered-interfaces"));
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
                const response = await window.api.get(apiPath("/app/info"));
                const m = response.data?.app_info?.migration;
                if (m && m.show_choice) {
                    this.migrationOffer = m;
                }
            } catch (e) {
                console.error("Failed to load migration status:", e);
            }
        },
        ensureAndroidStorageBridge() {
            if (!this.androidStorageBridge) {
                this.androidStorageBridge = new AndroidStorageBridge();
            }
            return this.androidStorageBridge;
        },
        refreshAndroidStorageSetup() {
            this.androidStorageSetup = null;
            const bridge = this.ensureAndroidStorageBridge();
            if (!bridge.isAndroidHost()) {
                return;
            }
            const status = bridge.getStatus();
            if (status?.needs_setup_choice) {
                this.androidStorageSetup = status;
                this.androidStorageSetupChoice = status.active_mode === "internal" ? "internal" : "external";
            }
        },
        async applyAndroidStorageSetup() {
            if (this.androidStorageBusy || !this.androidStorageSetup) {
                return;
            }
            const bridge = this.ensureAndroidStorageBridge();
            const mode = this.androidStorageSetupChoice || "external";
            this.androidStorageBusy = true;
            try {
                const result = bridge.applySetupChoice(mode, this.androidStorageSetup);
                if (result.restarted) {
                    ToastUtils.success(this.$t("android_storage.restart_to_apply"));
                } else {
                    this.androidStorageSetup = null;
                }
            } catch (e) {
                ToastUtils.error(this.$t("android_storage.failed"));
                console.error(e);
            } finally {
                this.androidStorageBusy = false;
            }
        },
        async migrationMigrate() {
            if (this.migrationBusy || !this.migrationOffer) return;
            this.migrationBusy = true;
            try {
                await window.api.post(apiPath("/setup/storage-migration"), { action: "migrate" });
                ToastUtils.success(this.$t("tutorial.migration_done_restart"));
                if (window.desktop && typeof window.desktop.relaunch === "function") {
                    await window.desktop.relaunch();
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
                await window.api.post(apiPath("/setup/storage-migration"), { action: "fresh" });
                ToastUtils.success(this.$t("tutorial.migration_done_restart"));
                if (window.desktop && typeof window.desktop.relaunch === "function") {
                    await window.desktop.relaunch();
                }
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("tutorial.migration_failed"));
                console.error(e);
            } finally {
                this.migrationBusy = false;
            }
        },
        onReticulumReloadStatus(json) {
            this.reticulumReloading = Boolean(json && typeof json === "object" && json.in_progress !== false);
        },
        onWebsocketReconnected() {
            // A reload "done" broadcast can be lost while the socket is down;
            // resync the busy flag instead of leaving the wizard locked.
            this.reticulumReloading = false;
        },
        clearPendingInterfaceChanges() {
            const store = useInterfaceChangesStore();
            store.hasPendingInterfaceChanges = false;
            if (store.modifiedInterfaceNames && store.modifiedInterfaceNames.clear) {
                store.modifiedInterfaceNames.clear();
            }
        },
        noteDiscoveryPatchResult(response) {
            // PATCH /reticulum/discovery applies most options live. When it
            // reports reloaded=true the stack restart already applied every
            // pending interface edit, so finishTutorial must not reload again.
            if (response?.data?.discovery?.reloaded === true) {
                this.clearPendingInterfaceChanges();
            }
        },
        async reloadReticulum() {
            this.reloadingReticulum = true;
            try {
                await window.api.post(apiPath("/reticulum/reload"));
                this.clearPendingInterfaceChanges();
                return true;
            } catch (e) {
                console.error("Failed to reload Reticulum:", e);
                ToastUtils.error(this.$t("tutorial.failed_reload_rns"));
                return false;
            } finally {
                this.reloadingReticulum = false;
            }
        },
        async useRecommendedMode() {
            if (this.connectionSetupBusy) {
                return;
            }
            this.addingRecommended = true;
            try {
                await window.api.post(apiPath("/reticulum/interfaces/add"), {
                    name: "Local Network",
                    type: "AutoInterface",
                    enabled: true,
                });
                useInterfaceChangesStore().hasPendingInterfaceChanges = true;
                useInterfaceChangesStore().modifiedInterfaceNames.add("Local Network");

                const payload = {
                    discover_interfaces: true,
                    autoconnect_discovered_interfaces: 3,
                    default_bootstrap_only: false,
                };
                const discoveryResponse = await window.api.patch(apiPath("/reticulum/discovery"), payload);
                this.noteDiscoveryPatchResult(discoveryResponse);
                this.defaultBootstrapOnly = false;

                ToastUtils.success(this.$t("tutorial.mode_recommended_added"));
                this.connectionMode = "recommended";
                this.currentStep = 4;
                this.bootstrapListSearch = "";
                this.bootstrapDiscoveredSectionOpen = true;
                this.bootstrapCommunitySectionOpen = true;
                this.bootstrapAutoPickDone = false;
                await this.loadCommunityInterfaces();
                await this.loadDiscoveredInterfaces();
                await this.pickRandomTcpBootstraps({ silent: true, auto: true, count: 3 });
                this.bootstrapAutoPickDone = true;
                this.interfaceAddedViaTutorial = true;
            } catch (e) {
                console.error("Failed to apply recommended connection mode:", e);
                ToastUtils.error(
                    e.response?.data?.message ||
                        this.$t("tutorial.failed_add_local") ||
                        this.$t("tutorial.failed_enable_discovery")
                );
            } finally {
                this.addingRecommended = false;
            }
        },
        async useDiscoveryMode() {
            if (this.connectionSetupBusy) {
                return;
            }
            this.savingDiscovery = true;
            try {
                const payload = {
                    discover_interfaces: true,
                    autoconnect_discovered_interfaces: 3,
                    default_bootstrap_only: false,
                };
                const discoveryResponse = await window.api.patch(apiPath("/reticulum/discovery"), payload);
                this.noteDiscoveryPatchResult(discoveryResponse);
                this.defaultBootstrapOnly = false;
                ToastUtils.success(this.$t("tutorial.discovery_enabled"));
                this.connectionMode = "discovery";
                this.currentStep = 4;
                this.bootstrapListSearch = "";
                this.bootstrapDiscoveredSectionOpen = true;
                this.bootstrapCommunitySectionOpen = true;
                this.bootstrapAutoPickDone = false;
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
            if (this.connectionSetupBusy) {
                return;
            }
            this.addingLocal = true;
            try {
                await window.api.post(apiPath("/reticulum/interfaces/add"), {
                    name: "Local Network",
                    type: "AutoInterface",
                    enabled: true,
                });
                this.interfaceAddedViaTutorial = true;
                useInterfaceChangesStore().hasPendingInterfaceChanges = true;
                useInterfaceChangesStore().modifiedInterfaceNames.add("Local Network");
                ToastUtils.success(this.$t("tutorial.local_added"));
                const reloaded = await this.reloadReticulum();
                if (!reloaded) {
                    return;
                }
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
            if (this.connectionSetupBusy) {
                return;
            }
            this.connectionMode = "manual";
            this.currentStep = 5;
        },
        isBootstrapSelected(key) {
            return this.selectedBootstrapKeys.includes(key);
        },
        toggleBootstrap(key) {
            if (this.bootstrapActionBusy) {
                return;
            }
            const idx = this.selectedBootstrapKeys.indexOf(key);
            if (idx >= 0) {
                this.selectedBootstrapKeys.splice(idx, 1);
            } else {
                if (this.selectedBootstrapKeys.length >= MAX_BOOTSTRAP_SELECTIONS) {
                    ToastUtils.warning(
                        this.$t("tutorial.bootstrap_selection_limit", { count: MAX_BOOTSTRAP_SELECTIONS })
                    );
                    return;
                }
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
            // bootstrapActionBusy covers an in-flight pick, bootstrap adds,
            // and any Reticulum reload so selection cannot churn mid-reload.
            if (this.bootstrapActionBusy) {
                return;
            }
            this.pickingRandomBootstraps = true;
            // Yield once so the busy spinner can paint before selection work.
            await Promise.resolve();
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
                const wanted = Number.isFinite(options.count) ? Number(options.count) : 3;
                const take = Math.min(Math.max(1, wanted), entries.length);
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
                this.pickingRandomBootstraps = false;
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
            if (this.pickingRandomBootstraps) {
                return;
            }
            const entries = this.dedupeBootstrapEntries(this.pickEligibleCommunityTcpBootstrapForRandom());
            if (entries.length === 0) {
                return;
            }
            await this.pickRandomTcpBootstraps({ silent: true, auto: true });
            if (this.selectedBootstrapKeys.length > 0) {
                this.bootstrapAutoPickDone = true;
            }
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
                const response = await window.api.get(apiPath("/reticulum/discovery"));
                const d = response.data?.discovery ?? {};
                this.defaultBootstrapOnly = this.parseDiscoveryBool(d.default_bootstrap_only);
            } catch (e) {
                console.error(e);
                this.defaultBootstrapOnly = false;
            }
        },
        async persistDefaultBootstrapOnly(value) {
            if (this.bootstrapActionBusy) {
                return;
            }
            try {
                const response = await window.api.patch(apiPath("/reticulum/discovery"), {
                    default_bootstrap_only: value === true,
                });
                this.noteDiscoveryPatchResult(response);
                this.defaultBootstrapOnly = value === true;
            } catch (e) {
                console.error("Failed to save default_bootstrap_only:", e);
                ToastUtils.error(this.$t("tutorial.failed_save_bootstrap_only"));
                this.defaultBootstrapOnly = !value;
            }
        },
        async confirmBootstraps() {
            if (this.bootstrapActionBusy) {
                return;
            }
            if (this.selectedBootstrapKeys.length === 0) {
                ToastUtils.warning(this.$t("tutorial.bootstrap_pick_at_least_one"));
                return;
            }
            this.addingBootstraps = true;
            // Adding interfaces is sequential and each add churns the
            // Reticulum stack. A huge selection would soft-lock onboarding.
            const selectedKeys = this.selectedBootstrapKeys.slice(0, MAX_BOOTSTRAP_SELECTIONS);
            const items = [];
            for (const key of selectedKeys) {
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
                    await window.api.post(apiPath("/reticulum/interfaces/add"), payload);
                    this.addedBootstrapKeys.push(item.key);
                    useInterfaceChangesStore().hasPendingInterfaceChanges = true;
                    useInterfaceChangesStore().modifiedInterfaceNames.add(payload.name);
                    added += 1;
                } catch (e) {
                    console.error("Failed to add bootstrap interface:", e);
                    ToastUtils.error(e.response?.data?.message || this.$t("tutorial.failed_add_bootstrap"));
                }
            }
            if (added === 0) {
                ToastUtils.warning(this.$t("tutorial.failed_add_bootstrap_none"));
                this.addingBootstraps = false;
                return;
            }
            this.interfaceAddedViaTutorial = true;
            ToastUtils.success(this.$t("tutorial.bootstrap_added", { count: added }));
            const reloaded = await this.reloadReticulum();
            this.addingBootstraps = false;
            if (reloaded) {
                this.currentStep = 5;
            }
        },
        skipBootstraps() {
            if (this.bootstrapActionBusy) {
                return;
            }
            this.currentStep = 5;
        },
        async enableAutoPropagation() {
            this.savingPropagation = true;
            try {
                await window.api.patch(apiPath("/config"), {
                    lxmf_preferred_propagation_node_auto_select: true,
                });
                if (useConfigStore().config) {
                    useConfigStore().config.lxmf_preferred_propagation_node_auto_select = true;
                }
                ToastUtils.success(this.$t("tutorial.auto_propagation_enabled"));
                this.nextStep();
            } catch (e) {
                console.error("Failed to enable auto-propagation:", e);
                ToastUtils.error(e.response?.data?.message || this.$t("tutorial.failed_enable_propagation"));
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
        gotoAddInterface() {
            void this.closeWithPendingImportGuard().then((closed) => {
                if (!closed) {
                    return;
                }
                if (this.$router) {
                    this.$router.push({ path: "/interfaces/add" });
                }
            });
        },
        gotoRoute(routeName) {
            void this.closeWithPendingImportGuard().then((closed) => {
                if (!closed) {
                    return;
                }
                if (this.$router) {
                    this.$router.push({ name: routeName });
                }
            });
        },
        async closeWithPendingImportGuard() {
            if (this.identityImportedHash && this.identityImportedHash !== this.originalIdentityHash) {
                const activate = await DialogUtils.confirm(this.$t("tutorial.identity_import_pending_activate"));
                if (activate) {
                    const activated = await this.activateImportedIdentity();
                    if (!activated) {
                        return false;
                    }
                } else {
                    ToastUtils.warning(this.$t("tutorial.identity_import_pending_kept"));
                }
            }
            if (!this.isPage) {
                this.visible = false;
            }
            return true;
        },
        async handlePrimaryAction() {
            if (this.currentStep === 2) {
                if (this.identityActionBusy) {
                    return;
                }
                this.identityActionBusy = true;
                try {
                    await this.handleIdentityContinue();
                } finally {
                    this.identityActionBusy = false;
                }
                return;
            }
            this.nextStep();
        },
        nextStep() {
            if (this.currentStep >= this.totalSteps) return;
            if (this.currentStep === 3) {
                if (!this.connectionMode) {
                    ToastUtils.warning(this.$t("tutorial.connect_mode_required"));
                    return;
                }
                if (this.connectionMode !== "discovery" && this.connectionMode !== "recommended") {
                    this.currentStep = 5;
                    return;
                }
            }
            if (this.currentStep === 4) {
                ToastUtils.warning(this.$t("tutorial.bootstrap_pick_at_least_one"));
                return;
            }
            this.currentStep++;
            if (this.currentStep === 6 || this.currentStep === 7) {
                this.currentStep = 8;
            }
            if (this.currentStep === 4) {
                this.bootstrapListSearch = "";
                this.bootstrapDiscoveredSectionOpen = true;
                this.bootstrapCommunitySectionOpen = true;
            }
        },
        previousStep() {
            if (this.tutorialNavBusy) {
                return;
            }
            if (this.currentStep <= 1) return;
            if (this.currentStep === 8) {
                this.currentStep = 5;
                return;
            }
            if (
                this.currentStep === 5 &&
                this.connectionMode !== "discovery" &&
                this.connectionMode !== "recommended"
            ) {
                this.currentStep = 3;
                return;
            }
            this.currentStep--;
        },
        async skipTutorial() {
            if (this.tutorialNavBusy) {
                return;
            }
            if (!(await DialogUtils.confirm(this.$t("tutorial.skip_confirm")))) {
                return;
            }
            if (this.identityImportedHash && this.identityImportedHash !== this.originalIdentityHash) {
                const activate = await DialogUtils.confirm(this.$t("tutorial.identity_import_pending_activate"));
                if (activate) {
                    const activated = await this.activateImportedIdentity();
                    if (!activated) {
                        return;
                    }
                } else {
                    ToastUtils.warning(this.$t("tutorial.identity_import_pending_kept"));
                }
            }
            this.visible = false;
            this.markSeen();
        },
        async markSeen() {
            if (this.markingSeen) return;
            this.markingSeen = true;
            try {
                await window.api.post(apiPath("/app/tutorial/seen"));
            } catch (e) {
                console.error("Failed to mark tutorial as seen:", e);
            } finally {
                this.markingSeen = false;
            }
        },
        async finishTutorial() {
            if (this.finishingTutorial || this.tutorialNavBusy) {
                return;
            }
            this.finishingTutorial = true;
            try {
                if (useInterfaceChangesStore().hasPendingInterfaceChanges) {
                    const reloaded = await this.reloadReticulum();
                    if (!reloaded) {
                        return;
                    }
                }
                if (this.identityImportedHash && this.identityImportedHash !== this.originalIdentityHash) {
                    const activated = await this.activateImportedIdentity();
                    if (!activated) {
                        return;
                    }
                }
                await this.markSeen();
                this.visible = false;
                GlobalEmitter.emit(EMITTER_EVENTS.TUTORIAL_FINISHED);
                if (this.interfaceAddedViaTutorial) {
                    ToastUtils.success(this.$t("tutorial.ready_finished"));
                }
            } finally {
                this.finishingTutorial = false;
            }
        },
        async onVisibleUpdate(val) {
            if (!val) {
                // Closing without finish still marks seen, but warn if import was pending.
                if (this.identityImportedHash && this.identityImportedHash !== this.originalIdentityHash) {
                    ToastUtils.warning(this.$t("tutorial.identity_import_pending_kept"));
                }
                this.markSeen();
            }
        },
    },
};
</script>

<style scoped>
@reference "../style.css";

/* ---------- chrome ---------- */

.tutorial-topbar {
    @apply flex shrink-0 items-center justify-between gap-2 px-4 py-2 sm:px-6;
}

.tutorial-step-count {
    @apply text-xs font-semibold;
}

.tutorial-icon-btn {
    @apply inline-flex size-11 items-center justify-center rounded-full text-sem-fg-muted transition-colors hover:bg-sem-surface-muted hover:text-sem-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sem-focus sm:size-10;
}

/* LanguageSelector renders its own button; match the theme toggle's size/ring. */
.tutorial-topbar :deep(button) {
    @apply inline-flex size-11 items-center justify-center rounded-full text-sem-fg-muted transition-colors hover:bg-sem-surface-muted hover:text-sem-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sem-focus sm:size-10;
}

/* ---------- steps ---------- */

.tutorial-step {
    @apply mx-auto flex w-full flex-col gap-5 sm:gap-6;
}

.tutorial-step-header {
    @apply flex items-center gap-3 sm:gap-4;
}

.tutorial-step-icon {
    @apply flex size-11 shrink-0 items-center justify-center rounded-2xl bg-sem-accent/10 text-sem-accent;
}

.tutorial-step-icon--info {
    @apply bg-sem-info/10 text-sem-info;
}

.tutorial-step-title {
    @apply text-xl font-bold tracking-tight text-sem-fg sm:text-2xl;
}

.tutorial-step-desc {
    @apply mt-1 text-sm text-sem-fg-muted;
}

/* ---------- cards ---------- */

.tutorial-card {
    @apply rounded-2xl border border-sem-border bg-sem-surface-muted p-4 sm:p-5;
}

.tutorial-notice {
    @apply w-full rounded-2xl border p-4 sm:p-5;
}

.tutorial-notice--warning {
    @apply border-sem-warning/40 bg-sem-warning/10;
}

.tutorial-notice--info {
    @apply border-sem-info/40 bg-sem-info/10;
}

.tutorial-icon-tile {
    @apply flex size-11 shrink-0 items-center justify-center rounded-xl;
}

/* Selectable option cards (identity mode, connection mode). */
.tutorial-choice {
    @apply relative flex w-full cursor-pointer items-start gap-4 rounded-2xl border-2 border-sem-border bg-sem-surface p-4 text-left transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sem-focus disabled:cursor-not-allowed disabled:opacity-60 sm:p-5;
}

.tutorial-choice:not(.tutorial-choice--selected):hover:not(:disabled) {
    @apply border-sem-accent/60;
}

.tutorial-choice--selected {
    @apply border-sem-accent bg-sem-accent/5;
}

.tutorial-choice--selected:hover:not(:disabled) {
    @apply bg-sem-accent/10;
}

.tutorial-choice__check {
    @apply flex size-6 shrink-0 items-center justify-center self-start rounded-full bg-sem-accent text-sem-action-primary-text;
}

/* Whole-card navigation targets (learn & create). */
.tutorial-link-card {
    @apply flex w-full cursor-pointer items-start gap-4 rounded-2xl border border-sem-border bg-sem-surface-muted p-4 text-left transition-colors hover:border-sem-accent/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sem-focus sm:p-5;
}

.tutorial-mini-card {
    @apply flex cursor-pointer items-start gap-2.5 rounded-xl border border-sem-border bg-sem-surface-muted p-3 text-left transition-colors hover:border-sem-accent/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sem-focus;
}

/* ---------- welcome feature grid ---------- */

.tutorial-feature-grid {
    @apply grid w-full grid-cols-2 gap-2.5 sm:gap-3;
}

.tutorial-feature-card {
    @apply flex items-start gap-2.5 rounded-xl border border-sem-border bg-sem-surface p-2.5 text-left transition-colors hover:border-sem-accent/60 hover:bg-sem-surface-muted sm:gap-3 sm:p-3;
}

.tutorial-feature-icon {
    @apply mt-0.5 size-4 shrink-0 text-sem-fg-muted sm:size-5;
}

.tutorial-feature-title {
    @apply text-[11px] font-bold leading-tight text-sem-fg sm:text-xs;
}

.tutorial-feature-desc {
    @apply mt-0.5 text-[10px] leading-snug text-sem-fg-muted sm:text-[11px];
}

/* ---------- bootstrap sections ---------- */

.tutorial-section {
    @apply h-fit min-w-0 overflow-hidden rounded-2xl border bg-sem-surface;
}

.tutorial-section--discovered {
    @apply border-sem-success/40 bg-sem-success/5;
}

.tutorial-section--community {
    @apply border-sem-border;
}

.tutorial-section__head {
    @apply flex w-full items-center gap-2.5 px-4 py-3.5 text-left transition-colors hover:bg-sem-surface-muted/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sem-focus;
}

.tutorial-count-chip {
    @apply shrink-0 rounded-full bg-sem-surface-muted px-2 py-0.5 text-[11px] font-bold tabular-nums text-sem-fg-muted;
}

.tutorial-bootstrap-row {
    @apply flex w-full cursor-pointer items-center gap-3 rounded-xl border border-sem-border bg-sem-surface p-3 transition-colors focus-within:ring-2 focus-within:ring-inset focus-within:ring-sem-focus;
}

.tutorial-bootstrap-row:not(.tutorial-bootstrap-row--selected):hover {
    @apply border-sem-accent/60;
}

.tutorial-bootstrap-row--selected {
    @apply border-sem-accent bg-sem-accent/5;
}

.tutorial-bootstrap-row--selected:hover {
    @apply bg-sem-accent/10;
}

.tutorial-online-badge {
    @apply shrink-0 rounded-full bg-sem-success/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-sem-success;
}

/* ---------- small buttons ---------- */

.tutorial-mini-btn {
    @apply inline-flex min-h-9 items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sem-focus;
}

.tutorial-mini-btn--primary {
    @apply bg-sem-action-primary text-sem-action-primary-text;
}

.tutorial-mini-btn--primary:hover:not(:disabled) {
    @apply bg-sem-action-primary-hover;
}

.tutorial-mini-btn--secondary {
    @apply border border-sem-border bg-sem-surface text-sem-fg-muted;
}

.tutorial-mini-btn--secondary:hover:not(:disabled) {
    @apply border-sem-accent bg-sem-surface-muted text-sem-fg;
}

/* ---------- footer actions ---------- */

.tutorial-action-btn {
    @apply inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sem-focus focus-visible:ring-offset-2 focus-visible:ring-offset-sem-surface;
}

.tutorial-action-btn:disabled {
    @apply cursor-not-allowed opacity-60;
}

.tutorial-action-btn-primary {
    @apply bg-sem-action-primary text-sem-action-primary-text;
}

.tutorial-action-btn-primary:hover:not(:disabled) {
    @apply bg-sem-action-primary-hover;
}

.tutorial-action-btn-secondary {
    @apply border border-sem-border bg-sem-surface text-sem-fg;
}

.tutorial-action-btn-secondary:hover:not(:disabled) {
    @apply bg-sem-surface-muted;
}

.tutorial-action-btn-success {
    @apply bg-sem-action-success text-sem-action-success-text;
}

.tutorial-action-btn-success:hover:not(:disabled) {
    @apply bg-sem-action-success-hover;
}

.tutorial-action-btn-ghost {
    @apply text-sem-fg-muted;
}

.tutorial-action-btn-ghost:hover:not(:disabled) {
    @apply bg-sem-surface-muted text-sem-fg;
}

/* ---------- step transition ---------- */

.fade-slide-enter-active,
.fade-slide-leave-active {
    transition:
        opacity 0.22s ease-out,
        transform 0.22s ease-out;
}

.fade-slide-enter-from {
    opacity: 0;
    transform: translateX(24px);
}

.fade-slide-leave-to {
    opacity: 0;
    transform: translateX(-24px);
}
</style>
