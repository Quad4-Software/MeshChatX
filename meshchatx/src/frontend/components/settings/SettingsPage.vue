<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div
        v-if="config"
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-linear-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div
            class="flex-1 overflow-y-auto overflow-x-hidden w-full min-w-0 px-3 sm:px-5 md:px-5 lg:px-8 py-4 sm:py-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]"
        >
            <div class="space-y-0 w-full max-w-6xl xl:max-w-7xl 2xl:max-w-360 mx-auto min-w-0">
                <div class="settings-section settings-section--hero">
                    <div class="flex flex-col lg:flex-row lg:items-center gap-4">
                        <div class="flex-1 space-y-1">
                            <div class="text-xs uppercase tracking-wide text-sem-fg-muted">
                                {{ $t("app.profile") }}
                            </div>
                            <div class="flex flex-col sm:flex-row sm:items-center gap-2">
                                <div class="flex-1 min-w-0">
                                    <input
                                        v-model="config.display_name"
                                        type="text"
                                        :placeholder="$t('app.display_name_placeholder')"
                                        class="w-full rounded-xl border border-sem-border bg-white dark:bg-zinc-800 px-3 py-2 text-base font-semibold text-sem-fg focus:ring-2 focus:ring-blue-500/60 focus:border-blue-500 outline-hidden transition"
                                        @input="onDisplayNameChange"
                                    />
                                </div>
                                <div class="text-sm text-sem-fg-muted whitespace-nowrap">
                                    {{ $t("app.manage_identity") }}
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-3 mt-4 text-sm text-sem-fg-muted">
                        <div
                            class="border border-gray-200/70 dark:border-zinc-800/80 py-3 px-3 sm:rounded-xl sm:bg-black/2 dark:sm:bg-white/2"
                        >
                            <div class="text-xs uppercase tracking-wide">{{ $t("app.theme") }}</div>
                            <div class="font-semibold text-sem-fg capitalize">
                                {{ $t("app.theme_mode", { mode: config.theme }) }}
                            </div>
                        </div>
                        <div
                            class="border border-gray-200/70 dark:border-zinc-800/80 py-3 px-3 sm:rounded-xl sm:bg-black/2 dark:sm:bg-white/2"
                        >
                            <div class="text-xs uppercase tracking-wide">{{ $t("app.transport") }}</div>
                            <div class="font-semibold text-sem-fg">
                                {{ config.is_transport_enabled ? $t("app.enabled") : $t("app.disabled") }}
                            </div>
                        </div>
                        <div
                            class="border border-gray-200/70 dark:border-zinc-800/80 py-3 px-3 sm:rounded-xl sm:bg-black/2 dark:sm:bg-white/2"
                        >
                            <div class="text-xs uppercase tracking-wide">{{ $t("app.propagation") }}</div>
                            <div class="font-semibold text-sem-fg">
                                {{
                                    config.lxmf_local_propagation_node_enabled
                                        ? $t("app.local_node_running")
                                        : $t("app.client_only")
                                }}
                            </div>
                        </div>
                    </div>
                    <div class="grid gap-3 mt-4 text-sm text-gray-700 dark:text-gray-200 sm:grid-cols-2">
                        <div class="address-card">
                            <div class="address-card__label">{{ $t("app.identity_hash") }}</div>
                            <div class="address-card__value monospace-field">{{ config.identity_hash }}</div>
                            <button
                                type="button"
                                class="address-card__action"
                                @click="copyValue(config.identity_hash, $t('app.identity_hash'))"
                            >
                                <MaterialDesignIcon icon-name="content-copy" class="w-4 h-4" />
                                {{ $t("app.copy") }}
                            </button>
                        </div>
                        <div class="address-card">
                            <div class="address-card__label">{{ $t("app.lxmf_address") }}</div>
                            <div class="address-card__value monospace-field">{{ config.lxmf_address_hash }}</div>
                            <button
                                type="button"
                                class="address-card__action"
                                @click="copyValue(config.lxmf_address_hash, $t('app.lxmf_address'))"
                            >
                                <MaterialDesignIcon icon-name="content-copy" class="w-4 h-4" />
                                {{ $t("app.copy") }}
                            </button>
                        </div>
                    </div>
                </div>

                <!-- search bar -->
                <div
                    class="sticky top-0 z-10 py-3 sm:py-4 mb-2 border-b border-gray-200/50 dark:border-zinc-800/50 bg-transparent min-w-0"
                >
                    <div class="relative w-full max-w-6xl xl:max-w-7xl 2xl:max-w-360 mx-auto min-w-0 px-0">
                        <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                            <MaterialDesignIcon icon-name="magnify" class="size-5 text-gray-400" />
                        </div>
                        <input
                            ref="settingsSearchInput"
                            :value="searchQuery"
                            type="search"
                            inputmode="search"
                            enterkeyhint="search"
                            autocomplete="off"
                            autocorrect="off"
                            autocapitalize="none"
                            spellcheck="false"
                            :aria-label="$t('settings.search_label')"
                            :class="[
                                'w-full bg-sem-surface border border-sem-border rounded-2xl py-3 pl-12 text-sm focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-hidden transition-all shadow-xs',
                                settingsSearchActive ? 'pr-12' : 'pr-4',
                            ]"
                            :placeholder="$t('app.search_settings')"
                            @input="onSettingsSearchInput"
                            @change="onSettingsSearchInput"
                            @compositionend="onSettingsSearchCompositionEnd"
                            @keydown.esc.prevent="clearSettingsSearch"
                        />
                        <button
                            v-if="settingsSearchActive"
                            type="button"
                            class="absolute inset-y-0 right-0 pr-4 flex items-center text-sem-fg-muted hover:text-sem-fg"
                            :aria-label="$t('settings.search_clear')"
                            @click="clearSettingsSearch"
                        >
                            <MaterialDesignIcon icon-name="close-circle" class="size-5" />
                        </button>
                    </div>
                    <p
                        v-if="settingsSearchActive && hasSearchResults"
                        class="w-full max-w-6xl xl:max-w-7xl 2xl:max-w-360 mx-auto mt-2 px-1 text-xs text-sem-fg-muted"
                    >
                        {{ $t("settings.search_match_count", { n: settingsSearchMatchTotal }) }}
                    </p>
                </div>

                <!-- no results -->
                <div
                    v-if="settingsSearchActive && !hasSearchResults"
                    class="flex flex-col items-center justify-center py-12 text-center"
                >
                    <div class="p-4 bg-white/50 dark:bg-zinc-800/50 rounded-full mb-4 border border-sem-border">
                        <MaterialDesignIcon icon-name="magnify-close" class="size-8 text-gray-400" />
                    </div>
                    <h3 class="text-lg font-semibold text-sem-fg">
                        {{ $t("settings.search_no_results") }}
                    </h3>
                    <p class="text-sem-fg-muted">
                        {{ $t("settings.search_no_match", { query: settingsSearchDisplay }) }}
                    </p>
                    <button
                        type="button"
                        class="mt-4 px-4 py-2 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition font-semibold text-sm"
                        @click="clearSettingsSearch"
                    >
                        {{ $t("settings.search_clear") }}
                    </button>
                </div>

                <!-- settings panel -->
                <div v-show="hasSearchResults" class="settings-panel">
                    <SettingsNav
                        :active-tab="settingsNavActiveTab"
                        :match-counts="settingsSearchActive ? settingsSearchMatchCounts : null"
                        @select="onSettingsNavSelect"
                    />
                    <div class="settings-panel__content">
                        <StrangerProtectionSettingsSection
                            :visible="showSection('strangerProtection')"
                            :config="config"
                            @block-attachments-change="onStrangerAttachmentBlockChange"
                            @block-all-change="onBlockAllFromStrangersChange"
                            @unknown-banner-change="onShowUnknownContactBannerChange"
                            @warn-links-change="onWarnOnStrangerLinksChange"
                        />

                        <BanishmentSettingsSection
                            :visible="showSection('banishment')"
                            :config="config"
                            @enabled-change="onBanishedEffectEnabledChange"
                            @text-change="onBanishedTextChange"
                            @color-change="onBanishedColorChange"
                        />

                        <StickersSettingsSection
                            v-model:replace-duplicates="stickerImportReplaceDuplicates"
                            :visible="showSection('stickers')"
                            :sticker-count="stickerCount"
                            @export="exportStickers"
                            @import="importStickers"
                        />

                        <GifsSettingsSection
                            v-model:replace-duplicates="gifImportReplaceDuplicates"
                            :visible="showSection('gifs')"
                            :gif-count="gifCount"
                            @export="exportGifs"
                            @import="importGifs"
                        />

                        <!-- Maintenance & Data -->
                        <section v-show="showSection('maintenance')" class="settings-section break-inside-avoid">
                            <header class="settings-section__header">
                                <div>
                                    <div class="settings-section__eyebrow">Maintenance</div>
                                    <h2>{{ $t("maintenance.title") }}</h2>
                                    <p>{{ $t("maintenance.description") }}</p>
                                </div>
                            </header>
                            <div class="settings-section__body space-y-4">
                                <div
                                    class="rounded-2xl border border-amber-200 dark:border-amber-900/40 bg-amber-50/60 dark:bg-amber-950/20 p-4 space-y-3"
                                >
                                    <div>
                                        <div class="text-sm font-bold text-gray-900 dark:text-gray-100">
                                            {{ $t("maintenance.purge_old_title") }}
                                        </div>
                                        <div class="text-xs text-sem-fg-muted mt-1">
                                            {{ $t("maintenance.purge_old_desc") }}
                                        </div>
                                    </div>
                                    <div class="flex flex-wrap gap-2">
                                        <button
                                            type="button"
                                            class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition"
                                            :class="
                                                messageAgePurgeMode === 'days'
                                                    ? 'border-amber-500 bg-amber-100 dark:bg-amber-900/40 text-amber-900 dark:text-amber-100'
                                                    : 'border-sem-border text-sem-fg-muted'
                                            "
                                            @click="messageAgePurgeMode = 'days'"
                                        >
                                            {{ $t("maintenance.purge_mode_days") }}
                                        </button>
                                        <button
                                            type="button"
                                            class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition"
                                            :class="
                                                messageAgePurgeMode === 'date'
                                                    ? 'border-amber-500 bg-amber-100 dark:bg-amber-900/40 text-amber-900 dark:text-amber-100'
                                                    : 'border-sem-border text-sem-fg-muted'
                                            "
                                            @click="messageAgePurgeMode = 'date'"
                                        >
                                            {{ $t("maintenance.purge_mode_date") }}
                                        </button>
                                    </div>
                                    <div
                                        v-if="messageAgePurgeMode === 'days'"
                                        class="flex flex-wrap items-center gap-2"
                                    >
                                        <label class="text-sm text-sem-fg" for="purge-older-days">
                                            {{ $t("maintenance.purge_older_than_days") }}
                                        </label>
                                        <input
                                            id="purge-older-days"
                                            v-model.number="messageAgePurgeDays"
                                            type="number"
                                            min="1"
                                            max="10000"
                                            class="input-field w-24"
                                            :aria-label="$t('maintenance.purge_older_than_days')"
                                            @change="refreshMessageAgePurgePreview"
                                        />
                                    </div>
                                    <div v-else class="flex flex-wrap items-center gap-2">
                                        <label class="text-sm text-sem-fg" for="purge-before-date">
                                            {{ $t("maintenance.purge_before_date") }}
                                        </label>
                                        <input
                                            id="purge-before-date"
                                            v-model="messageAgePurgeBeforeDate"
                                            type="date"
                                            class="input-field"
                                            :aria-label="$t('maintenance.purge_before_date')"
                                            @change="refreshMessageAgePurgePreview"
                                        />
                                    </div>
                                    <div class="text-xs text-sem-fg-muted">
                                        <span v-if="messageAgePurgePreviewLoading">{{
                                            $t("maintenance.purge_preview_loading")
                                        }}</span>
                                        <span v-else-if="messageAgePurgePreviewCount != null">{{
                                            $t("maintenance.purge_preview_count", {
                                                count: messageAgePurgePreviewCount,
                                            })
                                        }}</span>
                                        <span v-else>{{ $t("maintenance.purge_preview_hint") }}</span>
                                    </div>
                                    <div class="flex flex-wrap gap-2">
                                        <button
                                            type="button"
                                            class="px-3 py-2 rounded-xl text-sm font-semibold border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-800 hover:bg-gray-50 hover:bg-sem-surface-muted disabled:opacity-60"
                                            :disabled="messageAgePurgeBusy"
                                            @click="refreshMessageAgePurgePreview"
                                        >
                                            {{ $t("maintenance.purge_preview") }}
                                        </button>
                                        <button
                                            type="button"
                                            class="px-3 py-2 rounded-xl text-sm font-semibold border border-blue-300 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/40 text-blue-800 dark:text-blue-200 hover:bg-blue-100 dark:hover:bg-blue-900/40 disabled:opacity-60"
                                            :disabled="messageAgePurgeBusy"
                                            @click="exportOldMessagesArchive"
                                        >
                                            {{ $t("maintenance.export_old_archive") }}
                                        </button>
                                        <button
                                            type="button"
                                            class="px-3 py-2 rounded-xl text-sm font-semibold border border-red-300 dark:border-red-800 bg-red-600 text-white hover:bg-red-700 disabled:opacity-60"
                                            :disabled="messageAgePurgeBusy"
                                            @click="purgeOldMessages"
                                        >
                                            {{ $t("maintenance.purge_old_confirm_btn") }}
                                        </button>
                                    </div>
                                </div>

                                <div class="grid grid-cols-1 gap-3">
                                    <button
                                        type="button"
                                        class="btn-maintenance border-red-200 dark:border-red-900/30 text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-900/10 hover:bg-red-100 dark:hover:bg-red-900/20"
                                        @click="clearMessages"
                                    >
                                        <div class="flex flex-col items-start text-left">
                                            <div class="font-bold flex items-center gap-2">
                                                <MaterialDesignIcon icon-name="forum-remove-outline" class="size-4" />
                                                {{ $t("maintenance.clear_messages") }}
                                            </div>
                                            <div class="text-xs opacity-80">
                                                {{ $t("maintenance.clear_messages_desc") }}
                                            </div>
                                        </div>
                                    </button>

                                    <button
                                        type="button"
                                        class="btn-maintenance border-violet-200 dark:border-violet-900/30 text-violet-800 dark:text-violet-200 bg-violet-50 dark:bg-violet-900/10 hover:bg-violet-100 dark:hover:bg-violet-900/20"
                                        @click="clearDuplicateMessages"
                                    >
                                        <div class="flex flex-col items-start text-left">
                                            <div class="font-bold flex items-center gap-2">
                                                <MaterialDesignIcon icon-name="content-duplicate" class="size-4" />
                                                {{ $t("maintenance.clear_duplicates") }}
                                            </div>
                                            <div class="text-xs opacity-80">
                                                {{ $t("maintenance.clear_duplicates_desc") }}
                                            </div>
                                        </div>
                                    </button>

                                    <button
                                        type="button"
                                        class="btn-maintenance border-orange-200 dark:border-orange-900/30 text-orange-700 dark:text-orange-300 bg-orange-50 dark:bg-orange-900/10 hover:bg-orange-100 dark:hover:bg-orange-900/20"
                                        @click="clearAnnounces"
                                    >
                                        <div class="flex flex-col items-start text-left">
                                            <div class="font-bold flex items-center gap-2">
                                                <MaterialDesignIcon icon-name="broadcast-off" class="size-4" />
                                                {{ $t("maintenance.clear_announces") }}
                                            </div>
                                            <div class="text-xs opacity-80">
                                                {{ $t("maintenance.clear_announces_desc") }}
                                            </div>
                                        </div>
                                    </button>

                                    <button
                                        type="button"
                                        class="btn-maintenance border-indigo-200 dark:border-indigo-900/30 text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-900/10 hover:bg-indigo-100 dark:hover:bg-indigo-900/20"
                                        @click="clearNomadnetFavorites"
                                    >
                                        <div class="flex flex-col items-start text-left">
                                            <div class="font-bold flex items-center gap-2">
                                                <MaterialDesignIcon icon-name="bookmark-remove" class="size-4" />
                                                {{ $t("maintenance.clear_nomadnet_favs") }}
                                            </div>
                                            <div class="text-xs opacity-80">
                                                {{ $t("maintenance.clear_nomadnet_favs_desc") }}
                                            </div>
                                        </div>
                                    </button>

                                    <button
                                        type="button"
                                        class="btn-maintenance border-emerald-200 dark:border-emerald-900/30 text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-900/10 hover:bg-emerald-100 dark:hover:bg-emerald-900/20"
                                        @click="clearLxmfIcons"
                                    >
                                        <div class="flex flex-col items-start text-left">
                                            <div class="font-bold flex items-center gap-2">
                                                <MaterialDesignIcon icon-name="account-off" class="size-4" />
                                                {{ $t("maintenance.clear_lxmf_icons") }}
                                            </div>
                                            <div class="text-xs opacity-80">
                                                {{ $t("maintenance.clear_lxmf_icons_desc") }}
                                            </div>
                                        </div>
                                    </button>

                                    <button
                                        type="button"
                                        class="btn-maintenance border-amber-200 dark:border-amber-900/30 text-amber-800 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/10 hover:bg-amber-100 dark:hover:bg-amber-900/20"
                                        @click="clearStickers"
                                    >
                                        <div class="flex flex-col items-start text-left">
                                            <div class="font-bold flex items-center gap-2">
                                                <MaterialDesignIcon icon-name="emoticon-outline" class="size-4" />
                                                {{ $t("maintenance.clear_stickers") }}
                                            </div>
                                            <div class="text-xs opacity-80">
                                                {{ $t("maintenance.clear_stickers_desc") }}
                                            </div>
                                        </div>
                                    </button>

                                    <button
                                        type="button"
                                        class="btn-maintenance border-pink-200 dark:border-pink-900/30 text-pink-700 dark:text-pink-300 bg-pink-50 dark:bg-pink-900/10 hover:bg-pink-100 dark:hover:bg-pink-900/20"
                                        @click="clearGifs"
                                    >
                                        <div class="flex flex-col items-start text-left">
                                            <div class="font-bold flex items-center gap-2">
                                                <MaterialDesignIcon icon-name="file-gif-box" class="size-4" />
                                                {{ $t("maintenance.clear_gifs") }}
                                            </div>
                                            <div class="text-xs opacity-80">
                                                {{ $t("maintenance.clear_gifs_desc") }}
                                            </div>
                                        </div>
                                    </button>

                                    <button
                                        type="button"
                                        class="btn-maintenance border-blue-200 dark:border-blue-900/30 text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/10 hover:bg-blue-100 dark:hover:bg-blue-900/20"
                                        @click="clearArchives"
                                    >
                                        <div class="flex flex-col items-start text-left">
                                            <div class="font-bold flex items-center gap-2">
                                                <MaterialDesignIcon icon-name="delete-sweep" class="size-4" />
                                                {{ $t("maintenance.clear_archives") }}
                                            </div>
                                            <div class="text-xs opacity-80">
                                                {{ $t("maintenance.clear_archives_desc") }}
                                            </div>
                                        </div>
                                    </button>

                                    <button
                                        type="button"
                                        class="btn-maintenance border-orange-200 dark:border-orange-900/30 text-orange-700 dark:text-orange-300 bg-orange-50 dark:bg-orange-900/10 hover:bg-orange-100 dark:hover:bg-orange-900/20"
                                        @click="clearReticulumDocs"
                                    >
                                        <div class="flex flex-col items-start text-left">
                                            <div class="font-bold flex items-center gap-2">
                                                <MaterialDesignIcon icon-name="book-remove" class="size-4" />
                                                {{ $t("maintenance.clear_reticulum_docs") }}
                                            </div>
                                            <div class="text-xs opacity-80">
                                                {{ $t("maintenance.clear_reticulum_docs_desc") }}
                                            </div>
                                        </div>
                                    </button>

                                    <button
                                        type="button"
                                        class="btn-maintenance border-teal-200 dark:border-teal-900/30 text-teal-800 dark:text-teal-300 bg-teal-50 dark:bg-teal-900/10 hover:bg-teal-100 dark:hover:bg-teal-900/20"
                                        @click="clearPathTable"
                                    >
                                        <div class="flex flex-col items-start text-left">
                                            <div class="font-bold flex items-center gap-2">
                                                <MaterialDesignIcon icon-name="map-marker-remove" class="size-4" />
                                                {{ $t("maintenance.clear_path_table") }}
                                            </div>
                                            <div class="text-xs opacity-80">
                                                {{ $t("maintenance.clear_path_table_desc") }}
                                            </div>
                                        </div>
                                    </button>
                                </div>

                                <div class="space-y-2 pt-2 border-t border-sem-border">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        Automatic Backup Limit
                                    </div>
                                    <input
                                        v-model.number="config.backup_max_count"
                                        type="number"
                                        min="1"
                                        max="50"
                                        class="input-field"
                                        @input="onBackupConfigChange"
                                    />
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        Number of automatic backups to keep.
                                    </div>
                                </div>

                                <div class="grid grid-cols-2 gap-3 mt-4">
                                    <button
                                        type="button"
                                        class="flex flex-col items-center justify-center gap-2 p-4 rounded-2xl border border-blue-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-800/50 hover:border-blue-500 transition group"
                                        @click="exportMessages"
                                    >
                                        <MaterialDesignIcon
                                            icon-name="export"
                                            class="size-6 text-blue-500 group-hover:scale-110 transition"
                                        />
                                        <div class="text-sm font-bold">{{ $t("maintenance.export_messages") }}</div>
                                        <div class="text-xs opacity-70 text-center px-1">
                                            {{ $t("maintenance.export_messages_desc") }}
                                        </div>
                                    </button>

                                    <button
                                        type="button"
                                        class="flex flex-col items-center justify-center gap-2 p-4 rounded-2xl border border-emerald-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-800/50 hover:border-emerald-500 transition group"
                                        @click="triggerImport"
                                    >
                                        <MaterialDesignIcon
                                            icon-name="import"
                                            class="size-6 text-emerald-500 group-hover:scale-110 transition"
                                        />
                                        <div class="text-sm font-bold">{{ $t("maintenance.import_messages") }}</div>
                                        <div class="text-xs opacity-70 text-center px-1">
                                            {{ $t("maintenance.import_messages_desc") }}
                                        </div>
                                    </button>
                                    <input
                                        ref="importFile"
                                        type="file"
                                        accept=".json"
                                        class="hidden"
                                        @change="importMessages"
                                    />
                                </div>

                                <div class="grid grid-cols-2 gap-3 mt-2 pt-4 border-t border-sem-border">
                                    <button
                                        type="button"
                                        class="flex flex-col items-center justify-center gap-2 p-4 rounded-2xl border border-purple-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-800/50 hover:border-purple-500 transition group"
                                        @click="exportFolders"
                                    >
                                        <MaterialDesignIcon
                                            icon-name="folder-download-outline"
                                            class="size-6 text-purple-500 group-hover:scale-110 transition"
                                        />
                                        <div class="text-sm font-bold">Export Folders</div>
                                    </button>

                                    <button
                                        type="button"
                                        class="flex flex-col items-center justify-center gap-2 p-4 rounded-2xl border border-indigo-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-800/50 hover:border-indigo-500 transition group"
                                        @click="triggerFolderImport"
                                    >
                                        <MaterialDesignIcon
                                            icon-name="folder-upload-outline"
                                            class="size-6 text-indigo-500 group-hover:scale-110 transition"
                                        />
                                        <div class="text-sm font-bold">Import Folders</div>
                                    </button>
                                    <input
                                        ref="importFolderFile"
                                        type="file"
                                        accept=".json"
                                        class="hidden"
                                        @change="importFolders"
                                    />
                                </div>

                                <div class="grid grid-cols-2 gap-3 mt-2 pt-4 border-t border-sem-border">
                                    <button
                                        type="button"
                                        class="flex flex-col items-center justify-center gap-2 p-4 rounded-2xl border border-teal-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-800/50 hover:border-teal-500 transition group"
                                        @click="exportNomadnetFavouritesLayout"
                                    >
                                        <MaterialDesignIcon
                                            icon-name="file-export"
                                            class="size-6 text-teal-500 group-hover:scale-110 transition"
                                        />
                                        <div class="text-sm font-bold">
                                            {{ $t("maintenance.export_nomadnet_favourites") }}
                                        </div>
                                    </button>

                                    <button
                                        type="button"
                                        class="flex flex-col items-center justify-center gap-2 p-4 rounded-2xl border border-cyan-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-800/50 hover:border-cyan-500 transition group"
                                        @click="triggerNomadnetFavouritesImport"
                                    >
                                        <MaterialDesignIcon
                                            icon-name="import"
                                            class="size-6 text-cyan-500 group-hover:scale-110 transition"
                                        />
                                        <div class="text-sm font-bold">
                                            {{ $t("maintenance.import_nomadnet_favourites") }}
                                        </div>
                                    </button>
                                    <input
                                        ref="nomadnetFavouritesImportFile"
                                        type="file"
                                        accept=".json"
                                        class="hidden"
                                        @change="importNomadnetFavouritesLayoutFile"
                                    />
                                </div>
                            </div>
                        </section>

                        <section v-show="showSection('selftest')" class="settings-section break-inside-avoid">
                            <header class="settings-section__header">
                                <div>
                                    <div class="settings-section__eyebrow">Maintenance</div>
                                    <h2>{{ $t("selftest.title") }}</h2>
                                    <p>{{ $t("selftest.description") }}</p>
                                </div>
                            </header>
                            <div class="settings-section__body space-y-4">
                                <div class="flex items-center gap-3">
                                    <button
                                        type="button"
                                        class="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl transition flex items-center gap-2"
                                        :disabled="selfTestRunning"
                                        @click="runSelfTest"
                                    >
                                        <MaterialDesignIcon
                                            v-if="selfTestRunning"
                                            icon-name="loading"
                                            class="animate-spin size-4"
                                        />
                                        <MaterialDesignIcon v-else icon-name="play-circle-outline" class="size-4" />
                                        {{ selfTestRunning ? $t("selftest.running") : $t("selftest.run_test_btn") }}
                                    </button>
                                </div>

                                <div v-if="selfTestResults" class="space-y-3 mt-4 border-t border-sem-border pt-4">
                                    <div
                                        v-for="check in selfTestChecks"
                                        :key="check.key"
                                        class="flex flex-col p-3 rounded-xl border bg-sem-surface"
                                        :class="
                                            check.passed
                                                ? 'border-emerald-200/60 dark:border-emerald-900/30'
                                                : 'border-red-200/60 dark:border-red-900/30'
                                        "
                                    >
                                        <div class="flex items-center justify-between gap-2">
                                            <div class="flex items-center gap-2 font-semibold text-sm min-w-0">
                                                <MaterialDesignIcon
                                                    :icon-name="
                                                        check.passed ? 'check-circle-outline' : 'alert-circle-outline'
                                                    "
                                                    :class="check.passed ? 'text-emerald-500' : 'text-red-500'"
                                                    class="size-4 shrink-0"
                                                />
                                                <span class="truncate">{{ check.label }}</span>
                                            </div>
                                            <div class="flex items-center gap-1.5 shrink-0">
                                                <button
                                                    v-if="!check.passed && check.reason"
                                                    type="button"
                                                    class="inline-flex items-center justify-center rounded-lg p-1 text-red-600 hover:bg-red-50 dark:text-red-300 dark:hover:bg-red-950/40"
                                                    :aria-expanded="isSelfTestReasonExpanded(check.key)"
                                                    :aria-label="
                                                        isSelfTestReasonExpanded(check.key)
                                                            ? $t('selftest.collapse_reason')
                                                            : $t('selftest.expand_reason')
                                                    "
                                                    :title="
                                                        isSelfTestReasonExpanded(check.key)
                                                            ? $t('selftest.collapse_reason')
                                                            : $t('selftest.expand_reason')
                                                    "
                                                    @click="toggleSelfTestReason(check.key)"
                                                >
                                                    <MaterialDesignIcon
                                                        :icon-name="
                                                            isSelfTestReasonExpanded(check.key)
                                                                ? 'chevron-up'
                                                                : 'chevron-down'
                                                        "
                                                        class="size-4"
                                                    />
                                                </button>
                                                <span
                                                    class="px-2 py-0.5 text-xs font-bold rounded-md"
                                                    :class="
                                                        check.passed
                                                            ? 'bg-emerald-50 dark:bg-emerald-950/20 text-emerald-700 dark:text-emerald-300'
                                                            : 'bg-red-50 dark:bg-red-950/20 text-red-700 dark:text-red-300'
                                                    "
                                                >
                                                    {{ check.passed ? $t("selftest.passed") : $t("selftest.failed") }}
                                                </span>
                                            </div>
                                        </div>
                                        <div
                                            v-if="!check.passed && check.reason && isSelfTestReasonExpanded(check.key)"
                                            class="text-xs text-red-600 dark:text-red-400 mt-2 pl-6 whitespace-pre-wrap wrap-break-word"
                                        >
                                            <span class="font-semibold">{{ $t("selftest.reason_label") }}:</span>
                                            {{ check.reason }}
                                        </div>
                                    </div>

                                    <div
                                        v-if="allSelfTestChecksPassed"
                                        class="text-xs text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-2 pl-2"
                                    >
                                        <MaterialDesignIcon icon-name="check" class="size-4" />
                                        {{ $t("selftest.checks_completed") }}
                                    </div>
                                </div>
                            </div>
                        </section>

                        <PluginsSettingsSection :visible="showSection('plugins')" />

                        <TelephonySettingsSection
                            :visible="showSection('telephony')"
                            :config="config"
                            @enabled-change="onTelephoneEnabledChange"
                        />

                        <DesktopSettingsSection
                            :visible="showSection('desktop')"
                            :config="config"
                            :desktop-close-settings="desktopCloseSettings"
                            @hardware-acceleration-change="onDesktopHardwareAccelerationEnabledChange"
                            @tray-enabled-change="onDesktopTrayEnabledChange"
                            @close-behavior-change="onDesktopCloseBehaviorChange"
                        />

                        <AndroidSettingsSection
                            v-if="isMeshChatXAndroid"
                            :visible="showSection('android')"
                            :android-shell-privacy="androidShellPrivacy"
                            :remote-backend-url="androidRemoteBackendUrl"
                            :effective-backend-url="androidEffectiveBackendUrl"
                            :remote-backend-active="androidRemoteBackendActive"
                            @update:block-screenshots="
                                (v) => {
                                    androidShellPrivacy.blockScreenshots = v;
                                    saveAndroidBlockScreenshots();
                                }
                            "
                            @update:clear-clipboard-on-background="
                                (v) => {
                                    androidShellPrivacy.clearClipboardOnBackground = v;
                                    saveAndroidClearClipboardOnBackground();
                                }
                            "
                            @update:remote-backend-url="(v) => (androidRemoteBackendUrl = v)"
                            @apply-remote-backend="applyAndroidRemoteBackend"
                            @clear-remote-backend="clearAndroidRemoteBackend"
                            @share-apk="shareAndroidApk"
                        />

                        <ArchiverSettingsSection
                            :visible="showSection('archiver')"
                            :config="config"
                            @enabled-change="onPageArchiverEnabledChangeWrapper"
                            @config-change="
                                (patch) => {
                                    Object.assign(config, patch);
                                    onPageArchiverConfigChange();
                                }
                            "
                            @flush="flushArchivedPages"
                        />

                        <!-- NomadNet browser renderer -->
                        <section v-show="showSection('nomadRenderer')" class="settings-section break-inside-avoid">
                            <header class="settings-section__header">
                                <div>
                                    <div class="settings-section__eyebrow">Browsing</div>
                                    <h2>NomadNet browser renderer</h2>
                                    <p>
                                        Control how Micron, Markdown, HTML, and plain text pages are rendered in the
                                        Nomad browser and archives. Set the default page path when opening a node
                                        without a path.
                                    </p>
                                </div>
                            </header>
                            <div class="settings-section__body space-y-3">
                                <label class="setting-toggle">
                                    <Toggle
                                        id="nomad-render-markdown"
                                        v-model="config.nomad_render_markdown_enabled"
                                        @update:model-value="onNomadRendererMarkdownToggle"
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">Render Markdown (.md) pages</span>
                                        <span class="setting-toggle__description"
                                            >When off, .md files are shown as escaped text instead of formatted
                                            Markdown.</span
                                        >
                                    </span>
                                </label>
                                <label class="setting-toggle">
                                    <Toggle
                                        id="nomad-render-html"
                                        v-model="config.nomad_render_html_enabled"
                                        @update:model-value="onNomadRendererHtmlToggle"
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">Render HTML (.html) pages</span>
                                        <span class="setting-toggle__description"
                                            >When off, .html files are shown as escaped text instead of sanitized
                                            HTML.</span
                                        >
                                    </span>
                                </label>
                                <label class="setting-toggle">
                                    <Toggle
                                        id="nomad-render-plaintext"
                                        v-model="config.nomad_render_plaintext_enabled"
                                        @update:model-value="onNomadRendererPlaintextToggle"
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">Render plain text (.txt) pages</span>
                                        <span class="setting-toggle__description"
                                            >When off, .txt files use a simpler escaped layout.</span
                                        >
                                    </span>
                                </label>
                                <label v-if="micronWasmBundledInBuild" class="setting-toggle">
                                    <Toggle
                                        id="nomad-micron-wasm"
                                        v-model="config.nomad_micron_wasm_enabled"
                                        @update:model-value="onNomadMicronWasmToggle"
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">{{
                                            $t("settings.nomad_micron_wasm_title")
                                        }}</span>
                                        <span class="setting-toggle__description">
                                            {{ $t("settings.nomad_micron_wasm_desc_before_link") }}
                                            <a
                                                class="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 underline underline-offset-2"
                                                href="https://github.com/Quad4-Software/micron-parser-go"
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                >{{ $t("settings.nomad_micron_wasm_link_label") }}</a
                                            >{{ $t("settings.nomad_micron_wasm_desc_after_link") }}
                                        </span>
                                    </span>
                                </label>
                                <div
                                    v-if="micronWasmBundledInBuild && config.nomad_micron_wasm_enabled"
                                    class="space-y-2 rounded-lg border border-gray-200 bg-gray-50/80 p-3 dark:border-zinc-700 dark:bg-zinc-900/50"
                                >
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        {{ $t("settings.nomad_micron_default_engine_title") }}
                                    </div>
                                    <p class="text-xs text-gray-600 dark:text-gray-400">
                                        {{ $t("settings.nomad_micron_default_engine_desc") }}
                                    </p>
                                    <select
                                        :value="config.nomad_micron_default_engine === 'wasm' ? 'wasm' : 'js'"
                                        class="input-field max-w-xl"
                                        @change="onNomadMicronDefaultEngineSelect($event)"
                                    >
                                        <option value="js">
                                            {{ $t("settings.nomad_micron_default_engine_option_js") }}
                                        </option>
                                        <option value="wasm">
                                            {{ $t("settings.nomad_micron_default_engine_option_wasm") }}
                                        </option>
                                    </select>
                                </div>
                                <div v-if="micronWasmBundledInBuild" class="mt-2">
                                    <button
                                        type="button"
                                        class="primary-chip text-sm"
                                        @click="micronWasmUpdateModalOpen = true"
                                    >
                                        {{ $t("settings.micron_wasm_update_open_btn") }}
                                    </button>
                                </div>
                                <div class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        Default page path (no URL path)
                                    </div>
                                    <select
                                        v-model="config.nomad_default_page_path"
                                        class="input-field max-w-xl"
                                        @change="onNomadDefaultPagePathChange"
                                    >
                                        <option value="/page/index.mu">/page/index.mu (Micron)</option>
                                        <option value="/page/index.html">/page/index.html (HTML)</option>
                                        <option value="/page/index.md">/page/index.md (Markdown)</option>
                                        <option value="/page/index.txt">/page/index.txt (plain text)</option>
                                    </select>
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        Used when opening a Nomad node without a path, for hash-only links, and for the
                                        Smart Crawler homepage fetch.
                                    </div>
                                </div>
                            </div>
                        </section>

                        <!-- Smart Crawler -->
                        <section v-show="showSection('crawler')" class="settings-section break-inside-avoid">
                            <header class="settings-section__header">
                                <div>
                                    <div class="settings-section__eyebrow">Discovery</div>
                                    <h2>Smart Crawler</h2>
                                    <p>
                                        Opt-in NomadNet indexer. Listens for announces, prefers nearby low-hop nodes,
                                        fetches at most one page per node per day, stays within a small hop and RTT
                                        budget, and only walks a couple of levels from the front page (hard cap 20 pages
                                        per node). Nodes can opt out forever with a
                                        <code class="text-xs"># nocrawl</code> line on their index page, or from the
                                        Archives viewer.
                                    </p>
                                </div>
                            </header>
                            <div class="settings-section__body space-y-4">
                                <label class="setting-toggle">
                                    <Toggle
                                        id="crawler-enabled"
                                        v-model="config.crawler_enabled"
                                        @update:model-value="onCrawlerEnabledChange"
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">Enable Crawler</span>
                                        <span class="setting-toggle__description"
                                            >Off by default. When on, archives announced Nomad nodes under the limits
                                            below.</span
                                        >
                                    </span>
                                </label>

                                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                    <div class="space-y-2">
                                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">Max hops</div>
                                        <input
                                            v-model.number="config.crawler_max_hops"
                                            type="number"
                                            min="1"
                                            max="16"
                                            class="input-field"
                                            @input="onCrawlerConfigChange"
                                        />
                                        <div class="text-xs text-gray-600 dark:text-gray-400">
                                            Skip nodes farther than this path length (default 4).
                                        </div>
                                    </div>
                                    <div class="space-y-2">
                                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                            Max link RTT (ms)
                                        </div>
                                        <input
                                            v-model.number="config.crawler_max_rtt_ms"
                                            type="number"
                                            min="100"
                                            max="60000"
                                            class="input-field"
                                            @input="onCrawlerConfigChange"
                                        />
                                        <div class="text-xs text-gray-600 dark:text-gray-400">
                                            Do not index nodes whose link RTT is above this (default 2500).
                                        </div>
                                    </div>
                                    <div class="space-y-2">
                                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                            Max depth
                                        </div>
                                        <input
                                            v-model.number="config.crawler_max_depth"
                                            type="number"
                                            min="0"
                                            max="2"
                                            class="input-field"
                                            @input="onCrawlerConfigChange"
                                        />
                                        <div class="text-xs text-gray-600 dark:text-gray-400">
                                            0 is front page only. 2 is front page plus two levels down.
                                        </div>
                                    </div>
                                    <div class="space-y-2">
                                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                            Max pages per node
                                        </div>
                                        <input
                                            v-model.number="config.crawler_max_pages_per_node"
                                            type="number"
                                            min="1"
                                            max="20"
                                            class="input-field"
                                            @input="onCrawlerConfigChange"
                                        />
                                        <div class="text-xs text-gray-600 dark:text-gray-400">
                                            Hard cap on indexed paths per destination (default 20).
                                        </div>
                                    </div>
                                    <div class="space-y-2">
                                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                            Requests per day per node
                                        </div>
                                        <input
                                            v-model.number="config.crawler_requests_per_day_per_node"
                                            type="number"
                                            min="1"
                                            max="3"
                                            class="input-field"
                                            @input="onCrawlerConfigChange"
                                        />
                                        <div class="text-xs text-gray-600 dark:text-gray-400">
                                            Default 1. Keeps scrape load trivial on constrained links.
                                        </div>
                                    </div>
                                    <div class="space-y-2">
                                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                            Homepage refresh (days)
                                        </div>
                                        <input
                                            v-model.number="config.crawler_refresh_days"
                                            type="number"
                                            min="1"
                                            max="365"
                                            class="input-field"
                                            @input="onCrawlerConfigChange"
                                        />
                                        <div class="text-xs text-gray-600 dark:text-gray-400">
                                            Re-queue a completed homepage after this many days (default 30).
                                        </div>
                                    </div>
                                    <div class="space-y-2">
                                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                            Max Retries
                                        </div>
                                        <input
                                            v-model.number="config.crawler_max_retries"
                                            type="number"
                                            min="1"
                                            max="10"
                                            class="input-field"
                                            @input="onCrawlerConfigChange"
                                        />
                                        <div class="text-xs text-gray-600 dark:text-gray-400">
                                            Attempts before giving up.
                                        </div>
                                    </div>
                                    <div class="space-y-2">
                                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                            Retry Delay (seconds)
                                        </div>
                                        <input
                                            v-model.number="config.crawler_retry_delay_seconds"
                                            type="number"
                                            min="60"
                                            class="input-field"
                                            @input="onCrawlerConfigChange"
                                        />
                                        <div class="text-xs text-gray-600 dark:text-gray-400">
                                            Wait time between attempts.
                                        </div>
                                    </div>
                                </div>

                                <div class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        Max Concurrent Crawls
                                    </div>
                                    <input
                                        v-model.number="config.crawler_max_concurrent"
                                        type="number"
                                        min="1"
                                        max="2"
                                        class="input-field"
                                        @input="onCrawlerConfigChange"
                                    />
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        Capped at 2. Prefer 1 on LoRa-class links.
                                    </div>
                                </div>
                            </div>
                        </section>

                        <!-- Appearance -->
                        <AppearanceSettingsSection
                            :visible="showSection('appearance')"
                            :config="config"
                            :detailed-outbound-send-status="GlobalState.detailedOutboundSendStatus"
                            :outbound-transfer-progress-enabled="GlobalState.outboundTransferProgressEnabled"
                            :message-timestamp-grouping-enabled="GlobalState.messageTimestampGroupingEnabled"
                            :message-icon-preview-style="messageIconPreviewStyle"
                            @update-field="
                                (p) => {
                                    config[p.key] = p.value;
                                }
                            "
                            @theme-change="onThemeChange"
                            @theme-preset-change="onThemePresetChange"
                            @accent-color-change="onAccentColorChange"
                            @custom-canvas-color-change="onCustomCanvasColorChange"
                            @custom-surface-color-change="onCustomSurfaceColorChange"
                            @messages-sidebar-position-change="onMessagesSidebarPositionChange"
                            @app-sidebar-layout-change="onAppSidebarLayoutChange"
                            @message-font-size-change="onMessageFontSizeChange"
                            @message-icon-size-change="onMessageIconSizeChange"
                            @ui-transparency-change="onUiTransparencyChange"
                            @ui-glass-enabled-change="onUiGlassEnabledChange"
                            @messages-multi-pane-enabled-change="onMessagesMultiPaneEnabledChange"
                            @nomad-tabs-enabled-change="onNomadTabsEnabledChange"
                            @rrc-enabled-change="onRrcEnabledChange"
                            @rrc-unread-badges-enabled-change="onRrcUnreadBadgesEnabledChange"
                            @reset-appearance-defaults="resetAppearanceDefaults"
                            @detailed-outbound-send-status-change="onDetailedOutboundSendStatusChange"
                            @outbound-transfer-progress-enabled-change="onOutboundTransferProgressEnabledChange"
                            @message-timestamp-grouping-change="onMessageTimestampGroupingChange"
                            @bubble-color-change="onMessageBubbleColorChange"
                        />

                        <!-- Battery saver -->
                        <BatterySettingsSection
                            :visible="showSection('battery')"
                            :battery-saver="batterySaver"
                            :battery-interface-rows="batteryInterfaceRows"
                            :battery-bitrate-busy="batteryBitrateBusy"
                            @enabled-change="onBatterySaverEnabledChange"
                            @patch="patchBatterySaver"
                            @apply-bitrates="applyBatteryBitrateLimitsNow"
                            @restore-bitrates="restoreBatteryBitrateLimitsNow"
                        />

                        <VisualiserSettingsSection
                            :visible="showSection('visualiser')"
                            :renderer="visualiserRenderer"
                            :view-mode="visualiserViewMode"
                            :show-disabled-interfaces="visualiserShowDisabledInterfaces"
                            :show-discovered-interfaces="visualiserShowDiscoveredInterfaces"
                            @renderer-change="
                                (v) => {
                                    visualiserRenderer = v;
                                    onVisualiserRendererChange();
                                }
                            "
                            @view-mode-change="
                                (v) => {
                                    visualiserViewMode = v;
                                    onVisualiserViewModeChange();
                                }
                            "
                            @show-disabled-change="onVisualiserShowDisabledChange"
                            @show-discovered-change="onVisualiserShowDiscoveredChange"
                        />

                        <!-- Location (map & coordinates) -->
                        <section v-show="showSection('location')" class="settings-section break-inside-avoid">
                            <header class="settings-section__header">
                                <div>
                                    <div class="settings-section__eyebrow">{{ $t("app.settings_map_eyebrow") }}</div>
                                    <h2>{{ $t("app.map_settings_title") }}</h2>
                                    <p>{{ $t("app.map_settings_desc") }}</p>
                                </div>
                            </header>
                            <div class="settings-section__body space-y-4">
                                <div class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        {{ $t("app.location_source") }}
                                    </div>
                                    <select
                                        v-model="config.location_source"
                                        class="input-field"
                                        @change="
                                            updateConfig({ location_source: config.location_source }, 'location_source')
                                        "
                                    >
                                        <option value="disabled">{{ $t("app.location_source_disabled") }}</option>
                                        <option value="browser">{{ $t("app.location_source_browser") }}</option>
                                        <option value="manual">{{ $t("app.location_source_manual") }}</option>
                                    </select>
                                    <div
                                        v-if="config.location_source === 'disabled'"
                                        class="text-xs text-gray-600 dark:text-gray-400"
                                    >
                                        {{ $t("app.location_source_disabled_desc") }}
                                    </div>
                                    <div
                                        v-if="config.location_source === 'browser'"
                                        class="text-xs text-gray-600 dark:text-gray-400"
                                    >
                                        {{ $t("app.location_source_browser_desc") }}
                                    </div>
                                    <div
                                        v-if="config.location_source === 'manual'"
                                        class="text-xs text-gray-600 dark:text-gray-400"
                                    >
                                        {{ $t("app.location_source_manual_desc") }}
                                    </div>
                                </div>

                                <div
                                    v-if="config.location_source === 'manual'"
                                    class="grid grid-cols-1 sm:grid-cols-3 gap-4"
                                >
                                    <div class="space-y-2">
                                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                            {{ $t("app.location_manual_lat") }}
                                        </div>
                                        <input
                                            v-model="config.location_manual_lat"
                                            type="text"
                                            class="input-field"
                                            placeholder="0.0"
                                            @input="
                                                updateConfig(
                                                    { location_manual_lat: config.location_manual_lat },
                                                    'location_manual_lat'
                                                )
                                            "
                                        />
                                    </div>
                                    <div class="space-y-2">
                                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                            {{ $t("app.location_manual_lon") }}
                                        </div>
                                        <input
                                            v-model="config.location_manual_lon"
                                            type="text"
                                            class="input-field"
                                            placeholder="0.0"
                                            @input="
                                                updateConfig(
                                                    { location_manual_lon: config.location_manual_lon },
                                                    'location_manual_lon'
                                                )
                                            "
                                        />
                                    </div>
                                    <div class="space-y-2">
                                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                            {{ $t("app.location_manual_alt") }}
                                        </div>
                                        <input
                                            v-model="config.location_manual_alt"
                                            type="text"
                                            class="input-field"
                                            placeholder="0.0"
                                            @input="
                                                updateConfig(
                                                    { location_manual_alt: config.location_manual_alt },
                                                    'location_manual_alt'
                                                )
                                            "
                                        />
                                    </div>
                                </div>

                                <div class="space-y-2 border-t border-sem-border pt-4">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        {{ $t("app.map_defaults_heading") }}
                                    </div>
                                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                                        <div class="space-y-2">
                                            <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                                {{ $t("app.map_default_lat") }}
                                            </div>
                                            <input
                                                v-model="config.map_default_lat"
                                                type="text"
                                                class="input-field"
                                                @input="
                                                    updateConfig(
                                                        { map_default_lat: config.map_default_lat },
                                                        'map_default_lat'
                                                    )
                                                "
                                            />
                                        </div>
                                        <div class="space-y-2">
                                            <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                                {{ $t("app.map_default_lon") }}
                                            </div>
                                            <input
                                                v-model="config.map_default_lon"
                                                type="text"
                                                class="input-field"
                                                @input="
                                                    updateConfig(
                                                        { map_default_lon: config.map_default_lon },
                                                        'map_default_lon'
                                                    )
                                                "
                                            />
                                        </div>
                                        <div class="space-y-2">
                                            <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                                {{ $t("app.map_default_zoom") }}
                                            </div>
                                            <input
                                                v-model.number="config.map_default_zoom"
                                                type="number"
                                                class="input-field"
                                                @input="
                                                    updateConfig(
                                                        { map_default_zoom: config.map_default_zoom },
                                                        'map_default_zoom'
                                                    )
                                                "
                                            />
                                        </div>
                                    </div>
                                </div>

                                <div class="space-y-2 border-t border-sem-border pt-4">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        {{ $t("app.map_tiles_heading") }}
                                    </div>
                                    <div class="space-y-2">
                                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                            {{ $t("app.map_tile_server_url") }}
                                        </div>
                                        <input
                                            v-model="config.map_tile_server_url"
                                            type="text"
                                            class="input-field"
                                            @input="
                                                updateConfig(
                                                    { map_tile_server_url: config.map_tile_server_url },
                                                    'map_tile_server_url'
                                                )
                                            "
                                        />
                                    </div>
                                    <div class="space-y-2">
                                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                            {{ $t("app.map_nominatim_api_url") }}
                                        </div>
                                        <input
                                            v-model="config.map_nominatim_api_url"
                                            type="text"
                                            class="input-field"
                                            @input="
                                                updateConfig(
                                                    { map_nominatim_api_url: config.map_nominatim_api_url },
                                                    'map_nominatim_api_url'
                                                )
                                            "
                                        />
                                    </div>
                                    <label class="setting-toggle">
                                        <Toggle
                                            v-model="config.map_offline_enabled"
                                            @update:model-value="
                                                updateConfig(
                                                    { map_offline_enabled: config.map_offline_enabled },
                                                    'map_offline_enabled'
                                                )
                                            "
                                        />
                                        <span class="setting-toggle__label">
                                            <span class="setting-toggle__title">{{
                                                $t("app.map_offline_enabled")
                                            }}</span>
                                        </span>
                                    </label>
                                    <label class="setting-toggle">
                                        <Toggle
                                            v-model="config.map_tile_cache_enabled"
                                            @update:model-value="
                                                updateConfig(
                                                    { map_tile_cache_enabled: config.map_tile_cache_enabled },
                                                    'map_tile_cache_enabled'
                                                )
                                            "
                                        />
                                        <span class="setting-toggle__label">
                                            <span class="setting-toggle__title">{{
                                                $t("app.map_tile_cache_enabled")
                                            }}</span>
                                        </span>
                                    </label>
                                </div>

                                <div class="space-y-3 border-t border-sem-border pt-4">
                                    <div>
                                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                            {{ $t("app.map_overlay_limits_heading") }}
                                        </div>
                                        <div class="text-xs text-gray-600 dark:text-gray-400">
                                            {{ $t("app.map_overlay_limits_desc") }}
                                        </div>
                                    </div>
                                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        <div v-for="field in mapOverlayLimitFields" :key="field.key" class="space-y-2">
                                            <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                                {{ $t(field.labelKey) }}
                                            </div>
                                            <input
                                                v-model.number="config[field.key]"
                                                type="number"
                                                class="input-field"
                                                :min="field.min"
                                                :max="field.max"
                                                @change="onMapOverlayLimitChange(field.key)"
                                            />
                                            <div class="text-[10px] text-gray-500">
                                                {{ field.min }} .. {{ field.max }}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </section>

                        <!-- Language -->
                        <LanguageSettingsSection
                            :visible="showSection('language')"
                            :language="config.language"
                            @change="onLanguageSectionChange"
                        />

                        <!-- Network Security -->
                        <section v-show="showSection('networkSecurity')" class="settings-section break-inside-avoid">
                            <header class="settings-section__header">
                                <div>
                                    <div class="settings-section__eyebrow">RNS Security</div>
                                    <h2>Network Security</h2>
                                    <p>Manage mesh-level security features.</p>
                                </div>
                            </header>
                            <div class="settings-section__body space-y-4">
                                <div class="setting-toggle">
                                    <div class="setting-toggle__label">
                                        <div class="setting-toggle__title">
                                            {{ $t("app.blackhole_integration_enabled") }}
                                        </div>
                                        <div class="setting-toggle__description text-xs text-gray-500">
                                            {{ $t("app.blackhole_integration_description") }}
                                        </div>
                                    </div>
                                    <Toggle
                                        v-model="config.blackhole_integration_enabled"
                                        @update:model-value="
                                            updateConfig(
                                                {
                                                    blackhole_integration_enabled: config.blackhole_integration_enabled,
                                                },
                                                'blackhole_integration_enabled'
                                            )
                                        "
                                    />
                                </div>
                                <div class="space-y-4">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        {{ $t("app.announce_limits") }}
                                    </div>
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        {{ $t("app.announce_limits_description") }}
                                    </div>
                                    <div class="text-xs font-medium text-gray-800 dark:text-gray-200">
                                        {{ $t("app.announce_store_heading") }}
                                    </div>
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        {{ $t("app.announce_store_description") }}
                                    </div>
                                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                        <label class="setting-toggle">
                                            <Toggle
                                                :model-value="config.announce_store_lxmf_delivery"
                                                @update:model-value="
                                                    (v) => onAnnounceStoreToggle('announce_store_lxmf_delivery', v)
                                                "
                                            />
                                            <span class="setting-toggle__label">
                                                <span class="setting-toggle__title">{{
                                                    $t("app.announce_store_lxmf")
                                                }}</span>
                                            </span>
                                        </label>
                                        <label class="setting-toggle">
                                            <Toggle
                                                :model-value="config.announce_store_lxst_telephony"
                                                @update:model-value="
                                                    (v) => onAnnounceStoreToggle('announce_store_lxst_telephony', v)
                                                "
                                            />
                                            <span class="setting-toggle__label">
                                                <span class="setting-toggle__title">{{
                                                    $t("app.announce_store_lxst")
                                                }}</span>
                                            </span>
                                        </label>
                                        <label class="setting-toggle">
                                            <Toggle
                                                :model-value="config.announce_store_nomadnetwork_node"
                                                @update:model-value="
                                                    (v) => onAnnounceStoreToggle('announce_store_nomadnetwork_node', v)
                                                "
                                            />
                                            <span class="setting-toggle__label">
                                                <span class="setting-toggle__title">{{
                                                    $t("app.announce_store_nomad")
                                                }}</span>
                                            </span>
                                        </label>
                                        <label class="setting-toggle">
                                            <Toggle
                                                :model-value="config.announce_store_lxmf_propagation"
                                                @update:model-value="
                                                    (v) => onAnnounceStoreToggle('announce_store_lxmf_propagation', v)
                                                "
                                            />
                                            <span class="setting-toggle__label">
                                                <span class="setting-toggle__title">{{
                                                    $t("app.announce_store_prop")
                                                }}</span>
                                            </span>
                                        </label>
                                        <label class="setting-toggle">
                                            <Toggle
                                                :model-value="config.announce_store_map_data"
                                                @update:model-value="
                                                    (v) => onAnnounceStoreToggle('announce_store_map_data', v)
                                                "
                                            />
                                            <span class="setting-toggle__label">
                                                <span class="setting-toggle__title">{{
                                                    $t("app.announce_store_map_data")
                                                }}</span>
                                            </span>
                                        </label>
                                    </div>
                                    <div class="text-xs font-semibold text-sem-fg-muted uppercase tracking-wide">
                                        {{ $t("app.announce_max_stored_heading") }}
                                    </div>
                                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                        <div class="space-y-1">
                                            <label class="text-xs font-medium">{{
                                                $t("app.announce_limit_lxmf")
                                            }}</label>
                                            <input
                                                v-model.number="config.announce_max_stored_lxmf_delivery"
                                                type="number"
                                                min="1"
                                                class="input-field"
                                                @change="onAnnounceLimitsChange"
                                            />
                                        </div>
                                        <div class="space-y-1">
                                            <label class="text-xs font-medium">{{
                                                $t("app.announce_limit_nomadnet")
                                            }}</label>
                                            <input
                                                v-model.number="config.announce_max_stored_nomadnetwork_node"
                                                type="number"
                                                min="1"
                                                class="input-field"
                                                @change="onAnnounceLimitsChange"
                                            />
                                        </div>
                                        <div class="space-y-1">
                                            <label class="text-xs font-medium">{{
                                                $t("app.announce_limit_prop")
                                            }}</label>
                                            <input
                                                v-model.number="config.announce_max_stored_lxmf_propagation"
                                                type="number"
                                                min="1"
                                                class="input-field"
                                                @change="onAnnounceLimitsChange"
                                            />
                                        </div>
                                        <div class="space-y-1">
                                            <label class="text-xs font-medium">{{
                                                $t("app.announce_limit_map_data")
                                            }}</label>
                                            <input
                                                v-model.number="config.announce_max_stored_map_data"
                                                type="number"
                                                min="1"
                                                class="input-field"
                                                @change="onAnnounceLimitsChange"
                                            />
                                        </div>
                                    </div>
                                    <div class="text-xs font-semibold text-sem-fg-muted uppercase tracking-wide">
                                        {{ $t("app.announce_fetch_limit_heading") }}
                                    </div>
                                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                        <div class="space-y-1">
                                            <label class="text-xs font-medium">{{
                                                $t("app.announce_limit_lxmf")
                                            }}</label>
                                            <input
                                                v-model.number="config.announce_fetch_limit_lxmf_delivery"
                                                type="number"
                                                min="1"
                                                class="input-field"
                                                @change="onAnnounceLimitsChange"
                                            />
                                        </div>
                                        <div class="space-y-1">
                                            <label class="text-xs font-medium">{{
                                                $t("app.announce_limit_nomadnet")
                                            }}</label>
                                            <input
                                                v-model.number="config.announce_fetch_limit_nomadnetwork_node"
                                                type="number"
                                                min="1"
                                                class="input-field"
                                                @change="onAnnounceLimitsChange"
                                            />
                                        </div>
                                        <div class="space-y-1">
                                            <label class="text-xs font-medium">{{
                                                $t("app.announce_limit_prop")
                                            }}</label>
                                            <input
                                                v-model.number="config.announce_fetch_limit_lxmf_propagation"
                                                type="number"
                                                min="1"
                                                class="input-field"
                                                @change="onAnnounceLimitsChange"
                                            />
                                        </div>
                                        <div class="space-y-1">
                                            <label class="text-xs font-medium">{{
                                                $t("app.announce_limit_map_data")
                                            }}</label>
                                            <input
                                                v-model.number="config.announce_fetch_limit_map_data"
                                                type="number"
                                                min="1"
                                                class="input-field"
                                                @change="onAnnounceLimitsChange"
                                            />
                                        </div>
                                    </div>
                                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                        <div class="space-y-1">
                                            <label class="text-xs font-medium">{{
                                                $t("app.announce_search_max_fetch")
                                            }}</label>
                                            <input
                                                v-model.number="config.announce_search_max_fetch"
                                                type="number"
                                                min="100"
                                                class="input-field"
                                                @change="onAnnounceLimitsChange"
                                            />
                                            <p class="text-[10px] text-sem-fg-muted">
                                                {{ $t("app.announce_search_max_fetch_hint") }}
                                            </p>
                                        </div>
                                        <div class="space-y-1">
                                            <label class="text-xs font-medium">{{
                                                $t("app.discovered_interfaces_max_return")
                                            }}</label>
                                            <input
                                                v-model.number="config.discovered_interfaces_max_return"
                                                type="number"
                                                min="1"
                                                class="input-field"
                                                @change="onAnnounceLimitsChange"
                                            />
                                            <p class="text-[10px] text-sem-fg-muted">
                                                {{ $t("app.discovered_interfaces_max_return_hint") }}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </section>

                        <!-- Transport / shared instance / hop obfuscation -->
                        <section v-show="showSection('transport')" class="settings-section break-inside-avoid">
                            <header class="settings-section__header">
                                <div>
                                    <div class="settings-section__eyebrow">Reticulum</div>
                                    <h2>{{ $t("app.transport_mode") }}</h2>
                                    <p>{{ $t("app.transport_description") }}</p>
                                </div>
                            </header>
                            <div class="settings-section__body space-y-3">
                                <label class="setting-toggle">
                                    <Toggle
                                        id="transport-enabled"
                                        v-model="config.is_transport_enabled"
                                        @update:model-value="onIsTransportEnabledChangeWrapper"
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">{{ $t("app.enable_transport_mode") }}</span>
                                        <span class="setting-toggle__description">{{
                                            $t("app.transport_toggle_description")
                                        }}</span>
                                    </span>
                                </label>

                                <label class="setting-toggle">
                                    <Toggle
                                        id="share-reticulum-instance"
                                        v-model="reticulumInstance.share_instance"
                                        :disabled="reticulumInstanceSaving"
                                        @update:model-value="onShareInstanceChange"
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">{{
                                            $t("app.share_reticulum_instance")
                                        }}</span>
                                        <span class="setting-toggle__description">{{
                                            $t("app.share_reticulum_instance_description")
                                        }}</span>
                                    </span>
                                </label>

                                <label class="setting-toggle">
                                    <Toggle
                                        id="respond-to-probes"
                                        v-model="reticulumInstance.respond_to_probes"
                                        :disabled="reticulumInstanceSaving"
                                        @update:model-value="onRespondToProbesChange"
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">{{ $t("app.respond_to_probes") }}</span>
                                        <span class="setting-toggle__description">{{
                                            $t("app.respond_to_probes_description")
                                        }}</span>
                                    </span>
                                </label>

                                <label class="setting-toggle">
                                    <Toggle
                                        id="enable-remote-management"
                                        v-model="reticulumInstance.enable_remote_management"
                                        :disabled="reticulumInstanceSaving"
                                        @update:model-value="onEnableRemoteManagementChange"
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">{{
                                            $t("app.enable_remote_management")
                                        }}</span>
                                        <span class="setting-toggle__description">{{
                                            $t("app.enable_remote_management_description")
                                        }}</span>
                                    </span>
                                </label>

                                <div
                                    v-if="reticulumInstance.enable_remote_management"
                                    class="space-y-2 rounded-xl border border-sem-border bg-black/2 dark:bg-white/2 p-3"
                                >
                                    <label class="block space-y-1">
                                        <span class="text-sm font-medium text-sem-fg">{{
                                            $t("app.remote_management_allowed")
                                        }}</span>
                                        <textarea
                                            v-model="remoteManagementAllowedText"
                                            rows="3"
                                            class="w-full rounded-xl border border-sem-border bg-white dark:bg-zinc-800 px-3 py-2 font-mono text-xs text-sem-fg"
                                            :disabled="reticulumInstanceSaving"
                                            :placeholder="$t('app.remote_management_allowed_placeholder')"
                                        ></textarea>
                                        <span class="text-xs text-sem-fg-muted">{{
                                            $t("app.remote_management_allowed_description")
                                        }}</span>
                                    </label>
                                    <div class="flex flex-wrap items-center gap-2">
                                        <button
                                            type="button"
                                            class="primary-chip px-3 py-1.5 text-xs"
                                            :disabled="reticulumInstanceSaving"
                                            @click="saveRemoteManagementAllowed"
                                        >
                                            {{ $t("app.remote_management_allowed_save") }}
                                        </button>
                                        <ManagementIdentityPicker
                                            v-model="settingsMgmtIdentityPath"
                                            class="min-w-[16rem] flex-1"
                                            default-name="mgmt"
                                            @update:identity-hash="onSettingsMgmtIdentityHash"
                                        />
                                    </div>
                                    <p v-if="settingsMgmtIdentityHash" class="text-xs text-sem-fg-muted">
                                        {{ $t("remote_mgmt.management_identity") }}:
                                        <span class="font-mono">{{ settingsMgmtIdentityHash }}</span>
                                    </p>
                                </div>

                                <div class="grid gap-3 sm:grid-cols-2">
                                    <label class="block space-y-1">
                                        <span class="text-sm font-medium text-sem-fg">{{
                                            $t("app.shared_instance_type")
                                        }}</span>
                                        <select
                                            v-model="reticulumInstance.shared_instance_type"
                                            class="w-full rounded-xl border border-sem-border bg-white dark:bg-zinc-800 px-3 py-2 text-sm text-sem-fg"
                                            :disabled="reticulumInstanceSaving"
                                            @change="onSharedInstanceTypeChange"
                                        >
                                            <option value="">{{ $t("app.shared_instance_type_default") }}</option>
                                            <option value="unix">unix</option>
                                            <option value="tcp">tcp</option>
                                        </select>
                                        <span class="text-xs text-sem-fg-muted">{{
                                            $t("app.shared_instance_type_description")
                                        }}</span>
                                    </label>
                                    <label class="block space-y-1">
                                        <span class="text-sm font-medium text-sem-fg">{{
                                            $t("app.instance_name")
                                        }}</span>
                                        <input
                                            v-model="reticulumInstance.instance_name"
                                            type="text"
                                            maxlength="64"
                                            class="w-full rounded-xl border border-sem-border bg-white dark:bg-zinc-800 px-3 py-2 text-sm text-sem-fg"
                                            :disabled="reticulumInstanceSaving"
                                            @change="onInstanceNameChange"
                                        />
                                        <span class="text-xs text-sem-fg-muted">{{
                                            $t("app.instance_name_description")
                                        }}</span>
                                    </label>
                                </div>

                                <div
                                    class="rounded-xl border border-sem-border bg-black/2 dark:bg-white/2 p-3 space-y-2"
                                >
                                    <div class="text-sm font-medium text-sem-fg">
                                        {{ $t("app.rpc_config") }}
                                    </div>
                                    <p class="text-xs text-sem-fg-muted">
                                        {{ $t("app.rpc_config_description") }}
                                    </p>
                                    <p
                                        v-if="reticulumInstance.is_connected_to_shared_instance"
                                        class="text-xs text-amber-700 dark:text-amber-300"
                                    >
                                        {{ $t("app.connected_to_shared_instance") }}
                                    </p>
                                    <div
                                        class="relative rounded-lg border border-gray-200/70 dark:border-zinc-800 bg-white/60 dark:bg-zinc-900/60"
                                    >
                                        <pre
                                            class="text-xs font-mono whitespace-pre-wrap break-all text-sem-fg p-2 pr-12"
                                            >{{ displayedRpcConfigSnippet }}</pre>
                                        <button
                                            v-if="reticulumInstance.rpc_config_snippet"
                                            type="button"
                                            class="absolute top-1.5 right-1.5 inline-flex items-center justify-center rounded-lg p-1.5 text-gray-500 hover:text-gray-800 hover:bg-gray-100 text-sem-fg-muted dark:hover:text-zinc-100 dark:hover:bg-zinc-800"
                                            :aria-label="
                                                rpcKeyVisible ? $t('app.rpc_key_hide') : $t('app.rpc_key_show')
                                            "
                                            :title="rpcKeyVisible ? $t('app.rpc_key_hide') : $t('app.rpc_key_show')"
                                            @click="rpcKeyVisible = !rpcKeyVisible"
                                        >
                                            <MaterialDesignIcon
                                                :icon-name="rpcKeyVisible ? 'eye-off-outline' : 'eye-outline'"
                                                class="w-4 h-4"
                                            />
                                        </button>
                                    </div>
                                    <button
                                        type="button"
                                        class="inline-flex items-center gap-2 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold px-3 py-2"
                                        :disabled="!reticulumInstance.rpc_config_snippet"
                                        @click="copyRpcConfigSnippet"
                                    >
                                        <MaterialDesignIcon icon-name="content-copy" class="w-4 h-4" />
                                        {{ $t("app.copy_rpc_config") }}
                                    </button>
                                </div>
                            </div>
                        </section>

                        <!-- Interfaces -->
                        <section v-show="showSection('interfaces')" class="settings-section break-inside-avoid">
                            <header class="settings-section__header">
                                <div>
                                    <div class="settings-section__eyebrow">Adapters</div>
                                    <h2>{{ $t("app.interfaces") }}</h2>
                                    <p>Show curated community configs inside the interface wizard.</p>
                                </div>
                            </header>
                            <div class="settings-section__body space-y-3">
                                <label class="setting-toggle">
                                    <Toggle
                                        id="show-community-interfaces"
                                        v-model="config.show_suggested_community_interfaces"
                                        @update:model-value="onShowSuggestedCommunityInterfacesChangeWrapper"
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">{{
                                            $t("app.show_community_interfaces")
                                        }}</span>
                                        <span class="setting-toggle__description">{{
                                            $t("app.community_interfaces_description")
                                        }}</span>
                                    </span>
                                </label>
                            </div>
                        </section>

                        <BlockedSettingsSection :visible="showSection('blocked')" />

                        <SettingsSectionBlock
                            v-show="showSection('privacyData')"
                            :eyebrow="$t('app.privacy_eyebrow')"
                            :title="$t('app.privacy_data_title')"
                            :description="$t('app.privacy_data_description')"
                            body-class="space-y-4"
                        >
                            <div class="space-y-3">
                                <div class="text-[11px] font-semibold uppercase tracking-wider text-sem-fg-muted">
                                    {{ $t("app.privacy_subsection_device") }}
                                </div>
                                <label class="setting-toggle">
                                    <Toggle
                                        id="local-message-auto-delete"
                                        v-model="config.local_message_auto_delete_enabled"
                                        @update:model-value="onLocalMessageAutoDeleteEnabledChange"
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">{{
                                            $t("app.local_message_auto_delete_title")
                                        }}</span>
                                        <span class="setting-toggle__description">{{
                                            $t("app.local_message_auto_delete_description")
                                        }}</span>
                                    </span>
                                </label>
                                <div
                                    v-if="config.local_message_auto_delete_enabled"
                                    class="grid grid-cols-1 sm:grid-cols-2 gap-3 pl-0 sm:pl-1"
                                >
                                    <div class="space-y-1">
                                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                            {{ $t("app.local_message_auto_delete_age") }}
                                        </div>
                                        <div class="flex flex-wrap items-center gap-2">
                                            <input
                                                v-model.number="config.local_message_auto_delete_value"
                                                type="number"
                                                min="1"
                                                :max="config.local_message_auto_delete_unit === 'months' ? 120 : 10000"
                                                class="input-field w-24"
                                                :aria-label="$t('app.local_message_auto_delete_age')"
                                                @input="onLocalMessageAutoDeleteParamsChange"
                                            />
                                            <select
                                                v-model="config.local_message_auto_delete_unit"
                                                class="input-field min-w-[7rem]"
                                                :aria-label="$t('app.local_message_auto_delete_unit_aria')"
                                                @change="onLocalMessageAutoDeleteParamsChange"
                                            >
                                                <option value="days">
                                                    {{ $t("app.local_message_auto_delete_unit_days") }}
                                                </option>
                                                <option value="months">
                                                    {{ $t("app.local_message_auto_delete_unit_months") }}
                                                </option>
                                            </select>
                                        </div>
                                        <div class="text-xs text-gray-600 dark:text-gray-400">
                                            {{ $t("app.local_message_auto_delete_month_note") }}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="border-t border-sem-border pt-4 space-y-3">
                                <div class="text-[11px] font-semibold uppercase tracking-wider text-sem-fg-muted">
                                    {{ $t("app.privacy_eyebrow") }}
                                </div>
                                <div
                                    v-if="showWindowsScreenSecurity"
                                    class="p-4 rounded-2xl border border-amber-200 dark:border-amber-900/40 bg-amber-50/80 dark:bg-amber-950/30 space-y-3"
                                >
                                    <div
                                        class="text-xs font-semibold uppercase tracking-wider text-amber-800 dark:text-amber-200"
                                    >
                                        {{ $t("app.screen_security_drm_eyebrow") }}
                                    </div>
                                    <label class="setting-toggle">
                                        <Toggle
                                            id="screen-security-enabled"
                                            v-model="screenSecurityEnabled"
                                            :disabled="screenSecuritySaving"
                                            @update:model-value="onScreenSecurityChange"
                                        />
                                        <span class="setting-toggle__label">
                                            <span class="setting-toggle__title">{{
                                                $t("app.screen_security_enabled")
                                            }}</span>
                                            <span class="setting-toggle__description">{{
                                                $t("app.screen_security_description")
                                            }}</span>
                                        </span>
                                    </label>
                                    <p class="text-xs text-amber-900/80 dark:text-amber-100/80">
                                        {{ $t("app.screen_security_drm_note") }}
                                    </p>
                                </div>
                                <label class="setting-toggle">
                                    <Toggle
                                        id="privacy-mode-enabled"
                                        v-model="config.privacy_mode_enabled"
                                        @update:model-value="onPrivacyModeChange"
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">{{ $t("app.privacy_mode_enabled") }}</span>
                                        <span class="setting-toggle__description">{{
                                            $t("app.privacy_mode_description")
                                        }}</span>
                                    </span>
                                </label>

                                <label class="setting-toggle">
                                    <Toggle
                                        id="multi-session-warning-enabled"
                                        v-model="config.multi_session_warning_enabled"
                                        @update:model-value="onMultiSessionWarningChange"
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">{{
                                            $t("app.multi_session_warning_enabled")
                                        }}</span>
                                        <span class="setting-toggle__description">{{
                                            $t("app.multi_session_warning_description")
                                        }}</span>
                                    </span>
                                </label>

                                <label class="setting-toggle">
                                    <Toggle
                                        id="obfuscate-hops"
                                        v-model="reticulumInstance.local_hops_delta"
                                        :disabled="reticulumInstanceSaving"
                                        @update:model-value="onLocalHopsDeltaChange"
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">{{ $t("app.obfuscate_hops") }}</span>
                                        <span class="setting-toggle__description">{{
                                            $t("app.obfuscate_hops_description")
                                        }}</span>
                                    </span>
                                </label>
                            </div>

                            <div class="border-t border-sem-border pt-4 space-y-4">
                                <div class="text-[11px] font-semibold uppercase tracking-wider text-sem-fg-muted">
                                    {{ $t("app.privacy_subsection_telemetry") }}
                                </div>
                                <label class="setting-toggle">
                                    <Toggle
                                        id="telemetry-enabled"
                                        v-model="config.telemetry_enabled"
                                        @update:model-value="
                                            updateConfig(
                                                { telemetry_enabled: config.telemetry_enabled },
                                                'telemetry_enabled'
                                            )
                                        "
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">{{ $t("app.telemetry_enabled") }}</span>
                                        <span class="setting-toggle__description">{{
                                            $t("app.telemetry_description")
                                        }}</span>
                                    </span>
                                </label>
                                <div v-if="config.telemetry_enabled" class="space-y-4">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        {{ $t("app.telemetry_trusted_peers") }}
                                    </div>
                                    <div v-if="trustedTelemetryPeers.length === 0" class="text-xs text-gray-500 italic">
                                        {{ $t("app.telemetry_no_trusted_peers") }}
                                    </div>
                                    <div v-else class="space-y-2">
                                        <div
                                            v-for="peer in trustedTelemetryPeers"
                                            :key="peer.id"
                                            class="flex items-center justify-between p-2 rounded-xl bg-gray-50 dark:bg-zinc-800 border border-gray-100 dark:border-zinc-700"
                                        >
                                            <div class="flex items-center gap-3">
                                                <div
                                                    class="size-8 rounded-full bg-sem-surface-muted text-blue-500 flex items-center justify-center"
                                                >
                                                    <MaterialDesignIcon icon-name="account" class="size-5" />
                                                </div>
                                                <div class="min-w-0">
                                                    <div class="text-sm font-bold text-sem-fg truncate">
                                                        {{ peer.name }}
                                                    </div>
                                                    <div class="text-[10px] text-gray-500 font-mono truncate">
                                                        {{ peer.remote_identity_hash }}
                                                    </div>
                                                </div>
                                            </div>
                                            <button
                                                class="p-2 text-gray-400 hover:text-red-500 transition-colors"
                                                :title="$t('app.telemetry_revoke_trust')"
                                                @click="revokeTelemetryTrust(peer)"
                                            >
                                                <MaterialDesignIcon icon-name="shield-off-outline" class="size-5" />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </SettingsSectionBlock>

                        <!-- Authentication -->
                        <section v-show="showSection('auth')" class="settings-section break-inside-avoid">
                            <header class="settings-section__header">
                                <div>
                                    <div class="settings-section__eyebrow">Security</div>
                                    <h2>Authentication</h2>
                                    <p>Require a password to access the web interface.</p>
                                </div>
                            </header>
                            <div class="settings-section__body space-y-3">
                                <label class="setting-toggle">
                                    <Toggle
                                        id="auth-enabled"
                                        v-model="config.auth_enabled"
                                        @update:model-value="onAuthEnabledChange"
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">Enable Authentication</span>
                                        <span class="setting-toggle__description"
                                            >Protect your instance with a password.</span
                                        >
                                    </span>
                                </label>
                                <div v-if="config.auth_enabled" class="info-callout">
                                    <p class="text-sm">
                                        Authentication is currently enabled. You will be asked for your password when
                                        accessing the web interface.
                                    </p>
                                </div>
                            </div>
                        </section>

                        <section v-show="showSection('webExposure')" class="settings-section break-inside-avoid">
                            <header class="settings-section__header">
                                <div>
                                    <div class="settings-section__eyebrow">Security</div>
                                    <h2>{{ $t("app.web_exposure_title") }}</h2>
                                    <p>{{ $t("app.web_exposure_description") }}</p>
                                </div>
                            </header>
                            <div class="settings-section__body space-y-4">
                                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                                    <div>
                                        <div class="text-sem-fg-muted">
                                            {{ $t("app.web_listen_address") }}
                                        </div>
                                        <div class="font-mono text-gray-900 dark:text-gray-100">
                                            {{ serverSecurity.listen_host || "-" }}:{{
                                                serverSecurity.listen_port ?? "-"
                                            }}
                                        </div>
                                    </div>
                                    <div>
                                        <div class="text-sem-fg-muted">
                                            {{ $t("app.web_listen_https") }}
                                        </div>
                                        <div class="text-gray-900 dark:text-gray-100">
                                            {{ serverSecurity.https_enabled ? $t("app.enabled") : $t("app.disabled") }}
                                        </div>
                                    </div>
                                </div>
                                <div
                                    v-if="serverSecurity.landlock_requested !== undefined"
                                    class="text-xs text-gray-600 dark:text-gray-400"
                                >
                                    {{ $t("app.landlock_status") }}:
                                    {{
                                        serverSecurity.landlock_active
                                            ? serverSecurity.landlock_auto_enabled
                                                ? $t("app.landlock_auto_enabled")
                                                : $t("app.landlock_active")
                                            : serverSecurity.landlock_kernel_supported === false
                                              ? $t("app.landlock_kernel_unsupported")
                                              : serverSecurity.landlock_disabled_by_env
                                                ? $t("app.landlock_disabled_by_env")
                                                : $t("app.landlock_inactive")
                                    }}
                                </div>
                                <div
                                    v-if="serverSecurity.appcontainer_requested !== undefined"
                                    class="text-xs text-gray-600 dark:text-gray-400"
                                >
                                    {{ $t("app.appcontainer_status") }}:
                                    {{
                                        serverSecurity.appcontainer_active
                                            ? serverSecurity.appcontainer_auto_enabled
                                                ? $t("app.appcontainer_auto_enabled")
                                                : $t("app.appcontainer_active")
                                            : serverSecurity.appcontainer_supported === false
                                              ? $t("app.appcontainer_unsupported")
                                              : serverSecurity.appcontainer_disabled_by_env
                                                ? $t("app.appcontainer_disabled_by_env")
                                                : $t("app.appcontainer_inactive")
                                    }}
                                </div>
                                <div
                                    v-if="serverSecurity.seccomp_requested !== undefined"
                                    class="text-xs text-gray-600 dark:text-gray-400"
                                >
                                    {{ $t("app.seccomp_status") }}:
                                    {{
                                        serverSecurity.seccomp_active
                                            ? serverSecurity.seccomp_auto_enabled
                                                ? $t("app.seccomp_auto_enabled")
                                                : $t("app.seccomp_active")
                                            : serverSecurity.seccomp_kernel_supported === false
                                              ? $t("app.seccomp_kernel_unsupported")
                                              : serverSecurity.seccomp_disabled_by_env
                                                ? $t("app.seccomp_disabled_by_env")
                                                : $t("app.seccomp_inactive")
                                    }}
                                </div>
                                <div
                                    v-if="serverSecurity.is_loopback_bind === false"
                                    class="rounded-md border border-amber-500/40 bg-amber-500/10 p-4 space-y-3"
                                >
                                    <div class="text-sm font-semibold text-amber-900 dark:text-amber-200">
                                        {{ $t("app.web_exposure_warning_title") }}
                                    </div>
                                    <p class="text-sm text-amber-950/90 dark:text-amber-100/90">
                                        {{ $t("app.web_exposure_warning_body") }}
                                    </p>
                                    <ul class="space-y-2 text-sm">
                                        <li class="flex items-start gap-2">
                                            <MaterialDesignIcon
                                                :icon-name="
                                                    serverSecurity.auth_enabled ? 'check-circle' : 'alert-circle'
                                                "
                                                class="size-4 mt-0.5 shrink-0"
                                                :class="
                                                    serverSecurity.auth_enabled ? 'text-green-600' : 'text-amber-600'
                                                "
                                            />
                                            <span>{{
                                                serverSecurity.auth_enabled
                                                    ? $t("app.web_exposure_check_auth")
                                                    : $t("app.web_exposure_check_auth_off")
                                            }}</span>
                                        </li>
                                        <li>
                                            <label class="flex items-start gap-2 cursor-pointer">
                                                <input
                                                    v-model="exposureAckFirewall"
                                                    type="checkbox"
                                                    class="rounded-sm mt-1"
                                                    @change="persistExposureAcknowledgements"
                                                />
                                                <span>{{ $t("app.web_exposure_check_firewall") }}</span>
                                            </label>
                                        </li>
                                        <li>
                                            <label class="flex items-start gap-2 cursor-pointer">
                                                <input
                                                    v-model="exposureAckVpn"
                                                    type="checkbox"
                                                    class="rounded-sm mt-1"
                                                    @change="persistExposureAcknowledgements"
                                                />
                                                <span>{{ $t("app.web_exposure_check_vpn") }}</span>
                                            </label>
                                        </li>
                                    </ul>
                                </div>
                                <div class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        {{ $t("app.web_ui_ip_allowlist") }}
                                    </div>
                                    <input
                                        v-model="serverSecurity.web_ui_ip_allowlist"
                                        type="text"
                                        class="input-field font-mono text-xs"
                                        :placeholder="$t('app.web_ui_ip_allowlist_placeholder')"
                                        @input="onWebUiAllowlistChange"
                                    />
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        {{ $t("app.web_ui_ip_allowlist_description") }}
                                    </div>
                                </div>
                            </div>
                        </section>

                        <!-- Sources & Infrastructure -->
                        <section v-show="showSection('infrastructure')" class="settings-section break-inside-avoid">
                            <header class="settings-section__header">
                                <div>
                                    <div class="settings-section__eyebrow">Infrastructure</div>
                                    <h2>Sources & Mirroring</h2>
                                    <p>Customize URLs for documentation and external resources.</p>
                                </div>
                            </header>
                            <div class="settings-section__body space-y-4">
                                <div class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        Gitea Base URL
                                    </div>
                                    <input
                                        v-model="config.gitea_base_url"
                                        type="text"
                                        placeholder="https://github.com/example-org"
                                        class="input-field"
                                        @input="onGiteaConfigChange"
                                    />
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        The base URL for your preferred Gitea instance.
                                    </div>
                                </div>
                            </div>
                        </section>

                        <!-- Content Security Policy (CSP) -->
                        <section v-show="showSection('csp')" class="settings-section break-inside-avoid">
                            <header class="settings-section__header">
                                <div>
                                    <div class="settings-section__eyebrow">Security</div>
                                    <h2>{{ $t("app.csp_settings") }}</h2>
                                    <p>{{ $t("app.csp_description") }}</p>
                                </div>
                            </header>
                            <div class="settings-section__body space-y-4">
                                <div class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        {{ $t("app.csp_extra_connect_src") }}
                                    </div>
                                    <input
                                        v-model="config.csp_extra_connect_src"
                                        type="text"
                                        class="input-field font-mono text-xs"
                                        placeholder="https://api.example.com, wss://socket.example.com"
                                        @input="onCspConfigChange"
                                    />
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        {{ $t("app.csp_extra_connect_src_description") }}
                                    </div>
                                </div>

                                <div class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        {{ $t("app.csp_extra_img_src") }}
                                    </div>
                                    <input
                                        v-model="config.csp_extra_img_src"
                                        type="text"
                                        class="input-field font-mono text-xs"
                                        placeholder="https://tiles.example.com, https://cdn.example.com"
                                        @input="onCspConfigChange"
                                    />
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        {{ $t("app.csp_extra_img_src_description") }}
                                    </div>
                                </div>

                                <div class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        {{ $t("app.csp_extra_frame_src") }}
                                    </div>
                                    <input
                                        v-model="config.csp_extra_frame_src"
                                        type="text"
                                        class="input-field font-mono text-xs"
                                        placeholder="https://video.example.com"
                                        @input="onCspConfigChange"
                                    />
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        {{ $t("app.csp_extra_frame_src_description") }}
                                    </div>
                                </div>

                                <div class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        {{ $t("app.csp_extra_script_src") }}
                                    </div>
                                    <input
                                        v-model="config.csp_extra_script_src"
                                        type="text"
                                        class="input-field font-mono text-xs"
                                        placeholder="https://scripts.example.com"
                                        @input="onCspConfigChange"
                                    />
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        {{ $t("app.csp_extra_script_src_description") }}
                                    </div>
                                </div>

                                <div class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        {{ $t("app.csp_extra_style_src") }}
                                    </div>
                                    <input
                                        v-model="config.csp_extra_style_src"
                                        type="text"
                                        class="input-field font-mono text-xs"
                                        placeholder="https://fonts.example.com"
                                        @input="onCspConfigChange"
                                    />
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        {{ $t("app.csp_extra_style_src_description") }}
                                    </div>
                                </div>
                            </div>
                        </section>

                        <NotificationSoundSettings
                            v-show="showSection('notificationSounds')"
                            :config="config"
                            :show-section="showSection('notificationSounds')"
                            :update-config="updateConfig"
                        />

                        <!-- Messages (LXMF delivery, retries, inbound stamps) -->
                        <section v-show="showSection('messages')" class="settings-section break-inside-avoid">
                            <header class="settings-section__header">
                                <div>
                                    <div class="settings-section__eyebrow">{{ $t("app.lxmf_settings_eyebrow") }}</div>
                                    <h2>{{ $t("app.messages") }}</h2>
                                    <p>{{ $t("app.messages_description") }}</p>
                                </div>
                            </header>
                            <div class="settings-section__body space-y-3">
                                <label class="setting-toggle">
                                    <Toggle
                                        id="auto-resend-failed"
                                        v-model="config.auto_resend_failed_messages_when_announce_received"
                                        @update:model-value="
                                            onAutoResendFailedMessagesWhenAnnounceReceivedChangeWrapper
                                        "
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">{{ $t("app.auto_resend_title") }}</span>
                                        <span class="setting-toggle__description">{{
                                            $t("app.auto_resend_description")
                                        }}</span>
                                    </span>
                                </label>
                                <label class="setting-toggle">
                                    <Toggle
                                        id="allow-retries-attachments"
                                        v-model="config.allow_auto_resending_failed_messages_with_attachments"
                                        @update:model-value="
                                            onAllowAutoResendingFailedMessagesWithAttachmentsChangeWrapper
                                        "
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">{{
                                            $t("app.retry_attachments_title")
                                        }}</span>
                                        <span class="setting-toggle__description">{{
                                            $t("app.retry_attachments_description")
                                        }}</span>
                                    </span>
                                </label>
                                <label class="setting-toggle">
                                    <Toggle
                                        id="auto-fallback-propagation"
                                        v-model="config.auto_send_failed_messages_to_propagation_node"
                                        @update:model-value="onAutoSendFailedMessagesToPropagationNodeChangeWrapper"
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">{{ $t("app.auto_fallback_title") }}</span>
                                        <span class="setting-toggle__description">{{
                                            $t("app.auto_fallback_description")
                                        }}</span>
                                    </span>
                                </label>
                                <label class="setting-toggle">
                                    <Toggle
                                        id="inbound-stamps-required"
                                        :model-value="inboundStampsEnabled"
                                        @update:model-value="onInboundStampsEnabledChange"
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">{{
                                            $t("app.inbound_stamps_required_title")
                                        }}</span>
                                        <span class="setting-toggle__description">{{
                                            $t("app.inbound_stamps_required_description")
                                        }}</span>
                                    </span>
                                </label>
                                <div v-show="inboundStampsEnabled" class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        {{ $t("app.inbound_stamp_cost") }}
                                    </div>
                                    <input
                                        v-model.number="config.lxmf_inbound_stamp_cost"
                                        type="number"
                                        min="1"
                                        max="254"
                                        placeholder="8"
                                        class="input-field"
                                        @input="onLxmfInboundStampCostChange"
                                    />
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        {{ $t("app.inbound_stamp_description") }}
                                    </div>
                                </div>
                                <hr class="border-gray-200 dark:border-gray-700" />
                                <div>
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">
                                        {{ $t("app.flood_protection") }}
                                    </div>
                                    <div class="text-xs text-gray-600 dark:text-gray-400 mb-3">
                                        {{ $t("app.flood_protection_description") }}
                                    </div>
                                    <label class="setting-toggle">
                                        <Toggle
                                            id="lxmf-flood-protection"
                                            v-model="config.lxmf_flood_protection_enabled"
                                            @update:model-value="onLxmfFloodProtectionEnabledChange"
                                        />
                                        <span class="setting-toggle__label">
                                            <span class="setting-toggle__title">{{
                                                $t("app.flood_protection_enabled")
                                            }}</span>
                                        </span>
                                    </label>
                                    <div v-show="config.lxmf_flood_protection_enabled" class="space-y-3 mt-2">
                                        <div class="space-y-2">
                                            <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                                {{ $t("app.flood_threshold") }}
                                            </div>
                                            <input
                                                v-model.number="config.lxmf_flood_threshold_per_minute"
                                                type="number"
                                                min="1"
                                                max="1000"
                                                placeholder="30"
                                                class="input-field"
                                                @input="onLxmfFloodThresholdChange"
                                            />
                                        </div>
                                        <div class="space-y-2">
                                            <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                                {{ $t("app.flood_max_stamp_cost") }}
                                            </div>
                                            <input
                                                v-model.number="config.lxmf_flood_max_stamp_cost"
                                                type="number"
                                                min="1"
                                                max="254"
                                                placeholder="24"
                                                class="input-field"
                                                @input="onLxmfFloodMaxStampCostChange"
                                            />
                                        </div>
                                        <div class="space-y-2">
                                            <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                                {{ $t("app.flood_cooldown") }}
                                            </div>
                                            <input
                                                v-model.number="config.lxmf_flood_cooldown_seconds"
                                                type="number"
                                                min="30"
                                                max="3600"
                                                placeholder="300"
                                                class="input-field"
                                                @input="onLxmfFloodCooldownChange"
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </section>

                        <!-- Propagation nodes -->
                        <section v-show="showSection('propagation')" class="settings-section break-inside-avoid">
                            <header class="settings-section__header">
                                <div>
                                    <div class="settings-section__eyebrow">LXMF</div>
                                    <h2>{{ $t("app.propagation_nodes") }}</h2>
                                    <p>{{ $t("app.propagation_nodes_description") }}</p>
                                </div>
                                <RouterLink :to="{ name: 'propagation-nodes' }" class="primary-chip">
                                    {{ $t("app.browse_nodes") }}
                                </RouterLink>
                            </header>
                            <div class="settings-section__body space-y-5">
                                <div class="info-callout">
                                    <ul class="list-disc list-inside space-y-1 text-sm">
                                        <li>{{ $t("app.nodes_info_1") }}</li>
                                        <li>{{ $t("app.nodes_info_2") }}</li>
                                        <li>{{ $t("app.nodes_info_3") }}</li>
                                    </ul>
                                </div>
                                <label class="setting-toggle">
                                    <Toggle
                                        id="local-propagation-node"
                                        v-model="config.lxmf_local_propagation_node_enabled"
                                        @update:model-value="onLxmfLocalPropagationNodeEnabledChangeWrapper"
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">{{ $t("app.run_local_node") }}</span>
                                        <span class="setting-toggle__description">{{
                                            $t("app.run_local_node_description")
                                        }}</span>
                                        <span class="setting-toggle__hint monospace-field">{{
                                            config.lxmf_local_propagation_node_address_hash || "-"
                                        }}</span>
                                    </span>
                                </label>
                                <label class="setting-toggle">
                                    <Toggle
                                        id="auto-select-propagation-node"
                                        v-model="config.lxmf_preferred_propagation_node_auto_select"
                                        @update:model-value="onLxmfPreferredPropagationNodeAutoSelectChange"
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">{{ $t("app.auto_select_node") }}</span>
                                        <span class="setting-toggle__description">{{
                                            $t("app.auto_select_node_description")
                                        }}</span>
                                        <span
                                            v-if="config.lxmf_preferred_propagation_node_auto_select"
                                            class="setting-toggle__hint block mt-1 text-xs text-gray-600 dark:text-gray-400"
                                        >
                                            <template v-if="config.lxmf_preferred_propagation_node_destination_hash">
                                                <span class="block">{{ $t("app.auto_select_using_label") }}</span>
                                                <span class="monospace-field break-all block mt-0.5">{{
                                                    config.lxmf_preferred_propagation_node_destination_hash
                                                }}</span>
                                            </template>
                                            <template v-else>
                                                {{ $t("app.auto_select_pending") }}
                                            </template>
                                        </span>
                                    </span>
                                </label>
                                <div class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        {{ $t("app.preferred_propagation_node") }}
                                    </div>
                                    <div class="flex flex-col sm:flex-row gap-2">
                                        <input
                                            v-model="config.lxmf_preferred_propagation_node_destination_hash"
                                            type="text"
                                            spellcheck="false"
                                            autocomplete="off"
                                            :placeholder="$t('app.preferred_node_placeholder')"
                                            class="input-field monospace-field flex-1 min-w-0"
                                            @input="onLxmfPreferredPropagationNodeDestinationHashChange"
                                            @keydown.enter.prevent="savePreferredPropagationNodeHash(true)"
                                            @paste="onPreferredPropagationNodePaste"
                                        />
                                        <button
                                            type="button"
                                            class="secondary-chip shrink-0"
                                            @click="pastePreferredPropagationNodeHash"
                                        >
                                            {{ $t("tools.propagation_nodes.paste_hash") }}
                                        </button>
                                        <button
                                            type="button"
                                            class="primary-chip shrink-0"
                                            @click="savePreferredPropagationNodeHash(true)"
                                        >
                                            {{ $t("tools.propagation_nodes.set_preferred") }}
                                        </button>
                                        <button
                                            v-if="config.lxmf_preferred_propagation_node_destination_hash"
                                            type="button"
                                            class="secondary-chip shrink-0"
                                            @click="clearPreferredPropagationNodeHash"
                                        >
                                            {{ $t("tools.propagation_nodes.clear_preferred") }}
                                        </button>
                                    </div>
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        {{ $t("app.fallback_node_description") }}
                                    </div>
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        {{ $t("tools.propagation_nodes.manual_hint") }}
                                    </div>
                                </div>
                                <div class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        {{ $t("app.auto_sync_interval") }}
                                    </div>
                                    <select
                                        v-model="config.lxmf_preferred_propagation_node_auto_sync_interval_seconds"
                                        class="input-field"
                                        @change="onLxmfPreferredPropagationNodeAutoSyncIntervalSecondsChange"
                                    >
                                        <option value="0">{{ $t("app.disabled") }}</option>
                                        <option value="900">Every 15 Minutes</option>
                                        <option value="1800">Every 30 Minutes</option>
                                        <option value="3600">Every 1 Hour</option>
                                        <option value="10800">Every 3 Hours</option>
                                        <option value="21600">Every 6 Hours</option>
                                        <option value="43200">Every 12 Hours</option>
                                        <option value="86400">Every 24 Hours</option>
                                    </select>
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        <span v-if="config.lxmf_preferred_propagation_node_last_synced_at">{{
                                            $t("app.last_synced", {
                                                time: formatSecondsAgoForI18n(
                                                    config.lxmf_preferred_propagation_node_last_synced_at
                                                ),
                                            })
                                        }}</span>
                                        <span v-else>{{ $t("app.last_synced_never") }}</span>
                                    </div>
                                </div>
                                <div class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        {{ $t("app.incoming_message_size") }}
                                    </div>
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        {{ $t("app.incoming_message_size_description") }}
                                    </div>
                                    <select
                                        v-model="lxmfIncomingDeliveryPreset"
                                        class="input-field"
                                        @change="onLxmfIncomingDeliveryPresetChange"
                                    >
                                        <option value="1mb">{{ $t("app.incoming_message_size_1mb") }}</option>
                                        <option value="10mb">{{ $t("app.incoming_message_size_10mb") }}</option>
                                        <option value="25mb">{{ $t("app.incoming_message_size_25mb") }}</option>
                                        <option value="50mb">{{ $t("app.incoming_message_size_50mb") }}</option>
                                        <option value="1gb">{{ $t("app.incoming_message_size_1gb") }}</option>
                                        <option value="custom">{{ $t("app.incoming_message_size_custom") }}</option>
                                    </select>
                                    <div
                                        v-if="lxmfIncomingDeliveryPreset === 'custom'"
                                        class="flex flex-wrap items-center gap-2"
                                    >
                                        <input
                                            v-model.number="lxmfIncomingDeliveryCustomAmount"
                                            type="number"
                                            min="0.001"
                                            step="any"
                                            class="input-field max-w-40"
                                            @input="onLxmfIncomingDeliveryCustomChange"
                                        />
                                        <select
                                            v-model="lxmfIncomingDeliveryCustomUnit"
                                            class="input-field max-w-32"
                                            @change="onLxmfIncomingDeliveryCustomChange"
                                        >
                                            <option value="mb">{{ $t("app.incoming_message_size_unit_mb") }}</option>
                                            <option value="gb">{{ $t("app.incoming_message_size_unit_gb") }}</option>
                                        </select>
                                    </div>
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        {{ formatByteSize(config.lxmf_delivery_transfer_limit_in_bytes) }}
                                    </div>
                                </div>
                                <div class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        Propagation transfer limit (MB)
                                    </div>
                                    <input
                                        v-model.number="lxmfPropagationTransferLimitInputMb"
                                        type="number"
                                        min="0.001"
                                        step="0.01"
                                        class="input-field"
                                        @input="onLxmfPropagationTransferLimitChange"
                                    />
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        {{ formatByteSize(config.lxmf_propagation_transfer_limit_in_bytes) }}
                                    </div>
                                </div>
                                <div class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        Propagation sync limit (MB)
                                    </div>
                                    <input
                                        v-model.number="lxmfPropagationSyncLimitInputMb"
                                        type="number"
                                        min="0.001"
                                        step="0.01"
                                        class="input-field"
                                        @input="onLxmfPropagationSyncLimitChange"
                                    />
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        {{ formatByteSize(config.lxmf_propagation_sync_limit_in_bytes) }}
                                    </div>
                                </div>
                                <div v-if="config.lxmf_local_propagation_node_enabled" class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        {{ $t("app.propagation_stamp_cost") }}
                                    </div>
                                    <input
                                        v-model.number="config.lxmf_propagation_node_stamp_cost"
                                        type="number"
                                        min="13"
                                        max="254"
                                        placeholder="16"
                                        class="input-field"
                                        @input="onLxmfPropagationNodeStampCostChange"
                                    />
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        {{ $t("app.propagation_stamp_description") }}
                                    </div>
                                </div>
                                <label v-if="config.lxmf_local_propagation_node_enabled" class="setting-toggle">
                                    <Toggle
                                        id="propagation-sequential-validation"
                                        v-model="config.lxmf_propagation_sequential_validation"
                                        @update:model-value="onLxmfPropagationSequentialValidationChange"
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">{{
                                            $t("app.propagation_sequential_validation")
                                        }}</span>
                                        <span class="setting-toggle__description">{{
                                            $t("app.propagation_sequential_validation_description")
                                        }}</span>
                                    </span>
                                </label>
                                <label v-if="config.lxmf_local_propagation_node_enabled" class="setting-toggle">
                                    <Toggle
                                        id="propagation-static-peers-bypass-sequential"
                                        v-model="config.lxmf_propagation_static_peers_bypass_sequential"
                                        @update:model-value="onLxmfPropagationStaticPeersBypassChange"
                                    />
                                    <span class="setting-toggle__label">
                                        <span class="setting-toggle__title">{{
                                            $t("app.propagation_static_peers_bypass_sequential")
                                        }}</span>
                                        <span class="setting-toggle__description">{{
                                            $t("app.propagation_static_peers_bypass_sequential_description")
                                        }}</span>
                                    </span>
                                </label>
                                <div v-if="config.lxmf_local_propagation_node_enabled" class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        {{ $t("app.propagation_max_inbound_syncs") }}
                                    </div>
                                    <input
                                        v-model.number="config.lxmf_propagation_max_inbound_syncs"
                                        type="number"
                                        min="1"
                                        max="64"
                                        placeholder="3"
                                        class="input-field"
                                        @input="onLxmfPropagationMaxInboundSyncsChange"
                                    />
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        {{ $t("app.propagation_max_inbound_syncs_description") }}
                                    </div>
                                </div>
                            </div>
                        </section>

                        <section class="settings-section break-inside-avoid">
                            <header class="settings-section__header">
                                <div>
                                    <div class="settings-section__eyebrow">{{ $t("app.system") }}</div>
                                    <h2>{{ $t("app.reticulum_stack") }}</h2>
                                    <p>{{ $t("app.reticulum_stack_description") }}</p>
                                </div>
                            </header>
                            <div class="settings-section__body space-y-4">
                                <div class="grid grid-cols-1 gap-3">
                                    <button
                                        type="button"
                                        class="btn-maintenance border-violet-200 dark:border-violet-900/30 text-violet-800 dark:text-violet-200 bg-violet-50 dark:bg-violet-900/10 hover:bg-violet-100 dark:hover:bg-violet-900/20 disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:bg-violet-50 dark:disabled:hover:bg-violet-900/10"
                                        :disabled="reloadingRns"
                                        @click="reloadRns"
                                    >
                                        <div class="flex flex-col items-start text-left">
                                            <div class="font-bold flex items-center gap-2">
                                                <MaterialDesignIcon icon-name="restart" class="size-4" />
                                                {{ $t("app.reload_rns") }}
                                            </div>
                                        </div>
                                    </button>
                                    <p
                                        v-if="reloadRnsStatusMessage"
                                        class="text-xs"
                                        :class="reloadingRns ? 'text-sem-accent' : 'text-sem-fg-muted'"
                                    >
                                        {{ reloadRnsStatusMessage }}
                                    </p>
                                </div>
                            </div>
                        </section>

                        <!-- Keyboard Shortcuts -->
                        <div v-show="showSection('shortcuts')">
                            <section class="settings-section">
                                <button
                                    type="button"
                                    class="settings-section__header w-full text-left"
                                    :aria-expanded="shortcutsExpanded"
                                    @click="shortcutsExpanded = !shortcutsExpanded"
                                >
                                    <div class="flex items-center gap-3 w-full min-w-0">
                                        <div
                                            class="p-2 bg-blue-100 dark:bg-blue-900/30 text-sem-accent rounded-xl shrink-0"
                                        >
                                            <MaterialDesignIcon icon-name="keyboard-outline" class="size-6" />
                                        </div>
                                        <div class="min-w-0 flex-1">
                                            <h2>{{ $t("settings.keyboard_shortcuts_title") }}</h2>
                                            <p>{{ $t("settings.keyboard_shortcuts_description") }}</p>
                                        </div>
                                        <MaterialDesignIcon
                                            :icon-name="shortcutsExpanded ? 'chevron-up' : 'chevron-down'"
                                            class="size-6 shrink-0 text-sem-fg-muted"
                                        />
                                    </div>
                                </button>
                                <div v-show="shortcutsExpanded" class="settings-section__body">
                                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
                                        <div
                                            v-for="shortcut in KeyboardShortcuts.getDefaultShortcuts()"
                                            :key="shortcut.action"
                                            class="bg-gray-50/50 dark:bg-zinc-800/30 rounded-2xl p-4 sm:p-5 border border-sem-border"
                                        >
                                            <div class="flex items-center justify-between mb-3">
                                                <span class="text-sm font-bold text-sem-fg uppercase tracking-wide">
                                                    {{ shortcut.description }}
                                                </span>
                                            </div>
                                            <ShortcutRecorder
                                                :model-value="getShortcutKeys(shortcut.action)"
                                                :action="shortcut.action"
                                                @save="(keys) => saveShortcut(shortcut.action, keys)"
                                                @delete="() => deleteShortcut(shortcut.action)"
                                            />
                                        </div>
                                    </div>
                                </div>
                            </section>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <micron-wasm-update-modal v-model="micronWasmUpdateModalOpen" @saved="onMicronWasmOverrideSaved" />
    </div>
</template>

<script>
import Utils from "../../js/Utils";
import WebSocketConnection from "../../js/WebSocketConnection";
import DialogUtils from "../../js/DialogUtils";
import ToastUtils from "../../js/ToastUtils";
import { onWsEvent, offWsEvent } from "../../js/registries/wsEventRegistry.js";
import { readTextFromClipboard } from "../../js/clipboardUtils.js";
import { importMessagesFromFile } from "../../js/messageImport";
import DownloadUtils from "../../js/DownloadUtils";
import GlobalEmitter from "../../js/GlobalEmitter";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import Toggle from "../forms/Toggle.vue";
import ManagementIdentityPicker from "../tools/ManagementIdentityPicker.vue";
import ShortcutRecorder from "./ShortcutRecorder.vue";
import SettingsSectionBlock from "./SettingsSectionBlock.vue";
import LanguageSettingsSection from "./sections/LanguageSettingsSection.vue";
import DesktopSettingsSection from "./sections/DesktopSettingsSection.vue";
import StrangerProtectionSettingsSection from "./sections/StrangerProtectionSettingsSection.vue";
import BanishmentSettingsSection from "./sections/BanishmentSettingsSection.vue";
import StickersSettingsSection from "./sections/StickersSettingsSection.vue";
import GifsSettingsSection from "./sections/GifsSettingsSection.vue";
import TelephonySettingsSection from "./sections/TelephonySettingsSection.vue";
import AppearanceSettingsSection from "./sections/AppearanceSettingsSection.vue";
import BatterySettingsSection from "./sections/BatterySettingsSection.vue";
import VisualiserSettingsSection from "./sections/VisualiserSettingsSection.vue";
import BlockedSettingsSection from "./sections/BlockedSettingsSection.vue";
import AndroidSettingsSection from "./sections/AndroidSettingsSection.vue";
import ArchiverSettingsSection from "./sections/ArchiverSettingsSection.vue";
import SettingsNav from "./SettingsNav.vue";
import KeyboardShortcuts from "../../js/KeyboardShortcuts";
import ElectronUtils from "../../js/ElectronUtils";
import AndroidBridge from "../../js/rnode/AndroidBridge";
import GlobalState from "../../js/GlobalState";
import {
    numOrNull,
    sanitizeColorConfigFields as normalizeConfigColors,
    fetchMergedConfig,
    patchServerConfig,
    publishPatchedConfig,
} from "../../js/settings/settingsConfigService";
import { applyAppearanceTheme } from "../../theme/themeEngine.js";
import { setLocale } from "../../js/localeLoader.js";
import {
    applyTransportMode,
    applyReticulumInstanceSettings,
    fetchReticulumInstanceSettings,
} from "../../js/settings/settingsTransportService";
import * as maintenanceClient from "../../js/settings/settingsMaintenanceClient";
import {
    loadVisualiserDisplayPrefs,
    persistVisualiserShowDisabled,
    persistVisualiserShowDiscovered,
    persistVisualiserRenderer,
    persistVisualiserViewMode,
} from "../../js/settings/settingsVisualiserPrefs";
import { loadBatterySaverPrefs, saveBatterySaverPrefs } from "../../js/settings/batterySaverPrefs.js";
import {
    applyBatterySaverBitrateLimits,
    restoreBatterySaverBitrateLimits,
} from "../../js/settings/batterySaverBitrateApply.js";
import {
    incomingDeliveryBytesFromCustom,
    incomingDeliveryBytesFromPresetKey,
    syncIncomingDeliveryFieldsFromBytes,
} from "../../js/settings/incomingDeliveryLimit";
import { normalizeRetentionValue } from "../../js/localMessageRetention";
import { matchesSettingSearch, normalizeSearchString } from "../../js/settingsSearchUtils";
import {
    ALL_SETTINGS_SECTIONS,
    DEFAULT_SETTINGS_TAB,
    normalizeSettingsTabId,
    SETTINGS_TABS,
    settingsSectionBelongsToTab,
    settingsSectionSearchExtras,
} from "../../js/settings/settingsTabs.js";
import { getAllSettingsSectionKeywords } from "../../js/registries/settingsSectionRegistry.js";
import { isMicronWasmBundled } from "../../js/MicronWasmLoader.js";
import MicronWasmUpdateModal from "./MicronWasmUpdateModal.vue";
import NotificationSoundSettings from "./NotificationSoundSettings.vue";
import PluginsSettingsSection from "./PluginsSettingsSection.vue";
import {
    loadNomadFavouritesLayout,
    normalizeNomadFavouritesLayout,
    saveNomadFavouritesLayout,
} from "../../js/nomadFavouritesLayoutStore.js";

export default {
    name: "SettingsPage",
    components: {
        MaterialDesignIcon,
        Toggle,
        ManagementIdentityPicker,
        ShortcutRecorder,
        SettingsSectionBlock,
        SettingsNav,
        PluginsSettingsSection,
        LanguageSettingsSection,
        DesktopSettingsSection,
        StrangerProtectionSettingsSection,
        BanishmentSettingsSection,
        StickersSettingsSection,
        GifsSettingsSection,
        TelephonySettingsSection,
        AppearanceSettingsSection,
        BatterySettingsSection,
        VisualiserSettingsSection,
        BlockedSettingsSection,
        AndroidSettingsSection,
        ArchiverSettingsSection,
        MicronWasmUpdateModal,
        NotificationSoundSettings,
    },
    data() {
        return {
            GlobalState,
            ElectronUtils,
            KeyboardShortcuts,
            shortcutsExpanded: typeof window !== "undefined" ? window.innerWidth >= 1024 : true,
            config: {
                display_name: "",
                identity_hash: "",
                lxmf_address_hash: "",
                theme: "dark",
                theme_preset: "default",
                accent_color: null,
                custom_canvas_color: null,
                custom_surface_color: null,
                is_transport_enabled: false,
                auto_resend_failed_messages_when_announce_received: null,
                allow_auto_resending_failed_messages_with_attachments: null,
                auto_send_failed_messages_to_propagation_node: null,
                show_suggested_community_interfaces: null,
                lxmf_delivery_transfer_limit_in_bytes: 1000 * 1000 * 10,
                lxmf_propagation_transfer_limit_in_bytes: 1000 * 256,
                lxmf_propagation_sync_limit_in_bytes: 1000 * 10240,
                lxmf_local_propagation_node_enabled: null,
                lxmf_propagation_sequential_validation: true,
                lxmf_propagation_static_peers_bypass_sequential: true,
                lxmf_propagation_max_inbound_syncs: 3,
                lxmf_preferred_propagation_node_destination_hash: null,
                lxmf_preferred_propagation_node_auto_select: null,
                archives_max_storage_gb: 1,
                backup_max_count: 5,
                block_attachments_from_strangers: true,
                block_all_from_strangers: false,
                show_unknown_contact_banner: true,
                warn_on_stranger_links: true,
                banished_effect_enabled: true,
                banished_text: "BANISHED",
                banished_color: "#dc2626",
                blackhole_integration_enabled: true,
                announce_store_lxmf_delivery: true,
                announce_store_lxst_telephony: true,
                announce_store_nomadnetwork_node: true,
                announce_store_lxmf_propagation: true,
                announce_store_map_data: false,
                announce_max_stored_lxmf_delivery: 1000,
                announce_max_stored_nomadnetwork_node: 1000,
                announce_max_stored_lxmf_propagation: 1000,
                announce_max_stored_map_data: 1000,
                announce_fetch_limit_lxmf_delivery: 500,
                announce_fetch_limit_nomadnetwork_node: 500,
                announce_fetch_limit_lxmf_propagation: 500,
                announce_fetch_limit_map_data: 500,
                announce_search_max_fetch: 2000,
                discovered_interfaces_max_return: 500,
                message_font_size: 14,
                messages_sidebar_position: "left",
                messages_multi_pane_enabled: true,
                nomad_tabs_enabled: true,
                rrc_enabled: true,
                rrc_unread_badges_enabled: true,
                message_icon_size: 28,
                ui_transparency: 0,
                ui_glass_enabled: true,
                message_outbound_bubble_color: "#4f46e5",
                message_inbound_bubble_color: null,
                message_failed_bubble_color: "#ef4444",
                message_waiting_bubble_color: "#e5e7eb",
                telephone_tone_generator_enabled: true,
                telephone_tone_generator_volume: 50,
                location_source: "disabled",
                location_manual_lat: "0.0",
                location_manual_lon: "0.0",
                location_manual_alt: "0.0",
                map_default_lat: "0.0",
                map_default_lon: "0.0",
                map_default_zoom: 2,
                map_tile_server_url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                map_nominatim_api_url: "https://nominatim.openstreetmap.org",
                map_offline_enabled: false,
                map_tile_cache_enabled: true,
                map_overlay_max_bytes: 8 * 1024 * 1024,
                map_overlay_max_features: 50000,
                map_overlay_max_kmz_uncompressed_bytes: 16 * 1024 * 1024,
                map_overlay_max_sources: 64,
                map_overlay_max_concurrent_jobs: 2,
                map_overlay_path_timeout_seconds: 30,
                map_overlay_transfer_timeout_seconds: 120,
                map_overlay_job_timeout_seconds: 300,
                map_overlay_max_retries: 3,
                map_overlay_retry_delay_seconds: 2,
                telemetry_enabled: false,
                gitea_base_url: "",
                csp_extra_connect_src: "",
                csp_extra_img_src: "",
                csp_extra_frame_src: "",
                csp_extra_script_src: "",
                csp_extra_style_src: "",
                nomad_render_markdown_enabled: true,
                nomad_render_html_enabled: true,
                nomad_render_plaintext_enabled: true,
                nomad_micron_wasm_enabled: true,
                nomad_micron_default_engine: "js",
                nomad_default_page_path: "/page/index.mu",
                local_message_auto_delete_enabled: false,
                local_message_auto_delete_value: 30,
                local_message_auto_delete_unit: "days",
                privacy_mode_enabled: false,
                multi_session_warning_enabled: true,
            },
            serverSecurity: {
                listen_host: null,
                listen_port: null,
                https_enabled: true,
                is_loopback_bind: true,
                web_ui_ip_allowlist: "",
                auth_enabled: false,
                landlock_requested: false,
                landlock_active: false,
                landlock_kernel_supported: false,
                landlock_auto_enabled: false,
                landlock_disabled_by_env: false,
                appcontainer_requested: false,
                appcontainer_active: false,
                appcontainer_supported: false,
                appcontainer_auto_enabled: false,
                appcontainer_disabled_by_env: false,
                seccomp_requested: false,
                seccomp_active: false,
                seccomp_kernel_supported: false,
                seccomp_auto_enabled: false,
                seccomp_disabled_by_env: false,
            },
            exposureAckFirewall: false,
            exposureAckVpn: false,
            saveTimeouts: {},
            lxmfIncomingDeliveryPreset: "10mb",
            lxmfIncomingDeliveryCustomAmount: 10,
            lxmfIncomingDeliveryCustomUnit: "mb",
            lxmfPropagationTransferLimitInputMb: 0.256,
            lxmfPropagationSyncLimitInputMb: 10.24,
            lastRememberedInboundStampCost: 8,
            shortcuts: [],
            reloadingRns: false,
            reloadRnsStatusMessage: "",
            messageAgePurgeMode: "days",
            messageAgePurgeDays: 90,
            messageAgePurgeBeforeDate: "",
            messageAgePurgePreviewCount: null,
            messageAgePurgePreviewLoading: false,
            messageAgePurgeBusy: false,
            searchQuery: "",
            searchTabFilter: null,
            activeSettingsTab: DEFAULT_SETTINGS_TAB,
            micronWasmUpdateModalOpen: false,
            trustedTelemetryPeers: [],
            stickerCount: 0,
            stickerImportReplaceDuplicates: false,
            gifCount: 0,
            gifImportReplaceDuplicates: false,
            visualiserShowDisabledInterfaces: false,
            visualiserShowDiscoveredInterfaces: false,
            visualiserRenderer: "auto",
            visualiserViewMode: "flat",
            batterySaver: loadBatterySaverPrefs(),
            batteryInterfaceRows: [],
            batteryBitrateBusy: false,
            selfTestRunning: false,
            selfTestResults: null,
            selfTestExpandedReasons: {},
            rpcKeyVisible: false,
            desktopCloseSettings: {
                closeBehavior: "ask",
                trayEnabled: true,
            },
            screenSecurityEnabled: false,
            screenSecuritySaving: false,
            showWindowsScreenSecurity: false,
            androidShellPrivacy: {
                blockScreenshots: false,
                clearClipboardOnBackground: false,
            },
            androidRemoteBackendUrl: "",
            androidEffectiveBackendUrl: "",
            androidRemoteBackendActive: false,
            reticulumInstance: {
                share_instance: true,
                local_hops_delta: false,
                respond_to_probes: false,
                enable_remote_management: false,
                remote_management_allowed: [],
                shared_instance_type: "",
                instance_name: "default",
                rpc_key: null,
                rpc_config_snippet: null,
                is_connected_to_shared_instance: false,
                enable_transport: false,
            },
            reticulumInstanceSaving: false,
            remoteManagementAllowedText: "",
            settingsMgmtIdentityPath: "",
            settingsMgmtIdentityHash: "",
        };
    },
    computed: {
        sectionKeywords() {
            return getAllSettingsSectionKeywords();
        },
        micronWasmBundledInBuild() {
            return isMicronWasmBundled();
        },
        settingsSearchActive() {
            return normalizeSearchString(this.searchQuery).length > 0;
        },
        settingsSearchDisplay() {
            return normalizeSearchString(this.searchQuery) || this.searchQuery;
        },
        settingsNavActiveTab() {
            if (this.settingsSearchActive) {
                const filter = this.searchTabFilter;
                if (filter && this.settingsSearchMatchCounts[filter] > 0) {
                    return filter;
                }
                return "";
            }
            return this.activeSettingsTab;
        },
        settingsSearchMatchCounts() {
            /** @type {Record<string, number>} */
            const counts = {};
            for (const tab of SETTINGS_TABS) {
                counts[tab.id] = tab.sections.filter((sectionKey) => this.sectionMatchesQuery(sectionKey)).length;
            }
            return counts;
        },
        settingsSearchMatchTotal() {
            return ALL_SETTINGS_SECTIONS.filter((sectionKey) => this.sectionMatchesQuery(sectionKey)).length;
        },
        hasSearchResults() {
            if (!this.settingsSearchActive) return true;
            return this.settingsSearchMatchTotal > 0;
        },
        selfTestChecks() {
            if (!this.selfTestResults) {
                return [];
            }
            const r = this.selfTestResults;
            const item = (key, labelKey) => ({
                key,
                label: this.$t(labelKey),
                passed: r[key]?.status === "ok",
                reason: r[key]?.reason || "",
            });
            return [
                item("stack_up", "selftest.stack_up"),
                item("config_good", "selftest.config_good"),
                item("db_good", "selftest.db_good"),
                item("read_write_good", "selftest.read_write"),
                item("identity_good", "selftest.identity_good"),
                item("imports_good", "selftest.imports_good"),
                item("storage_lock_good", "selftest.storage_lock_good"),
                item("temp_fs_good", "selftest.temp_fs_good"),
                item("public_assets_good", "selftest.public_assets_good"),
                item("lxmf_router_good", "selftest.lxmf_router_good"),
                item("subprocess_good", "selftest.subprocess_good"),
                item("run_module_good", "selftest.run_module_good"),
                item("sqlite_roundtrip", "selftest.sqlite_roundtrip"),
                item("identity_roundtrip", "selftest.identity_roundtrip"),
                item("loopback_tcp", "selftest.loopback_tcp"),
                item("unicode_path_good", "selftest.unicode_path_good"),
                item("rnode_support_good", "selftest.rnode_support_good"),
                item("bot_launcher_good", "selftest.bot_launcher_good"),
                item("http_status_good", "selftest.http_status_good"),
                item("http_app_info_good", "selftest.http_app_info_good"),
                item("http_config_good", "selftest.http_config_good"),
                item("http_db_health_good", "selftest.http_db_health_good"),
                item("http_auth_csrf_good", "selftest.http_auth_csrf_good"),
                item("http_bots_status_good", "selftest.http_bots_status_good"),
                item("http_security_good", "selftest.http_security_good"),
                item("http_interfaces_good", "selftest.http_interfaces_good"),
                item("http_reticulum_instance_good", "selftest.http_reticulum_instance_good"),
                item("http_identities_good", "selftest.http_identities_good"),
                item("http_favourites_good", "selftest.http_favourites_good"),
                item("http_telephone_good", "selftest.http_telephone_good"),
                item("http_plugins_good", "selftest.http_plugins_good"),
                item("http_plugins_trust_good", "selftest.http_plugins_trust_good"),
                item("http_sideband_plugins_good", "selftest.http_sideband_plugins_good"),
                item("http_sideband_config_good", "selftest.http_sideband_config_good"),
                item("http_rrc_hubs_good", "selftest.http_rrc_hubs_good"),
                item("http_rrc_servers_good", "selftest.http_rrc_servers_good"),
                item("plugins_runtime_good", "selftest.plugins_runtime_good"),
                item("websocket_good", "selftest.websocket_good"),
                item("websocket_rns_link_good", "selftest.websocket_rns_link_good"),
                item("bots_lifecycle", "selftest.bots_lifecycle"),
            ];
        },
        allSelfTestChecksPassed() {
            return this.selfTestChecks.length > 0 && this.selfTestChecks.every((check) => check.passed);
        },
        displayedRpcConfigSnippet() {
            const snippet = this.reticulumInstance?.rpc_config_snippet;
            if (!snippet) {
                return this.$t("app.rpc_config_unavailable");
            }
            if (this.rpcKeyVisible) {
                return snippet;
            }
            return snippet
                .split("\n")
                .map((line) => {
                    const match = line.match(/^(\s*rpc_key\s*=\s*)(.*)$/i);
                    if (!match) {
                        return line;
                    }
                    const value = match[2] || "";
                    return `${match[1]}${"•".repeat(Math.max(8, Math.min(value.length, 48)))}`;
                })
                .join("\n");
        },
        safeConfig() {
            if (!this.config) {
                return {
                    display_name: "",
                    identity_hash: "",
                    lxmf_address_hash: "",
                    theme: "dark",
                    is_transport_enabled: false,
                    location_source: "disabled",
                    location_manual_lat: "0.0",
                    location_manual_lon: "0.0",
                    location_manual_alt: "0.0",
                };
            }
            return this.config;
        },
        previewTextStyle() {
            const size = this.config?.message_font_size || 14;
            return { "font-size": `${size}px` };
        },
        messageIconPreviewStyle() {
            const size = Number(this.config?.message_icon_size) || 28;
            return {
                width: `${size}px`,
                height: `${size}px`,
                minWidth: `${size}px`,
                minHeight: `${size}px`,
                transition: "width 120ms linear, height 120ms linear",
            };
        },
        inboundStampsEnabled() {
            const c = this.config?.lxmf_inbound_stamp_cost;
            return (typeof c === "number" ? c : Number(c) || 0) > 0;
        },
        mapOverlayLimitFields() {
            return [
                {
                    key: "map_overlay_max_bytes",
                    labelKey: "app.map_overlay_max_bytes",
                    min: 65536,
                    max: 67108864,
                },
                {
                    key: "map_overlay_max_features",
                    labelKey: "app.map_overlay_max_features",
                    min: 100,
                    max: 500000,
                },
                {
                    key: "map_overlay_max_kmz_uncompressed_bytes",
                    labelKey: "app.map_overlay_max_kmz_uncompressed_bytes",
                    min: 262144,
                    max: 134217728,
                },
                {
                    key: "map_overlay_max_sources",
                    labelKey: "app.map_overlay_max_sources",
                    min: 1,
                    max: 256,
                },
                {
                    key: "map_overlay_max_concurrent_jobs",
                    labelKey: "app.map_overlay_max_concurrent_jobs",
                    min: 1,
                    max: 8,
                },
                {
                    key: "map_overlay_path_timeout_seconds",
                    labelKey: "app.map_overlay_path_timeout_seconds",
                    min: 5,
                    max: 300,
                },
                {
                    key: "map_overlay_transfer_timeout_seconds",
                    labelKey: "app.map_overlay_transfer_timeout_seconds",
                    min: 15,
                    max: 600,
                },
                {
                    key: "map_overlay_job_timeout_seconds",
                    labelKey: "app.map_overlay_job_timeout_seconds",
                    min: 30,
                    max: 1800,
                },
                {
                    key: "map_overlay_max_retries",
                    labelKey: "app.map_overlay_max_retries",
                    min: 0,
                    max: 10,
                },
                {
                    key: "map_overlay_retry_delay_seconds",
                    labelKey: "app.map_overlay_retry_delay_seconds",
                    min: 1,
                    max: 120,
                },
            ];
        },
        isMeshChatXAndroid() {
            return (
                typeof window !== "undefined" &&
                window.MeshChatXAndroid &&
                typeof window.MeshChatXAndroid.getPlatform === "function" &&
                window.MeshChatXAndroid.getPlatform() === "android"
            );
        },
    },
    beforeUnmount() {
        // stop listening for websocket events
        offWsEvent("config", this.onConfigEvent);
        offWsEvent("keyboard_shortcuts", this.onKeyboardShortcutsEvent);
        offWsEvent("reticulum_reload_status", this.onReloadStatusEvent);
        GlobalEmitter.off("identity-switched", this.onIdentitySwitched);
        window.removeEventListener("keydown", this.onSettingsSearchHotkey);
    },
    mounted() {
        // listen for websocket events
        onWsEvent("config", this.onConfigEvent);
        onWsEvent("keyboard_shortcuts", this.onKeyboardShortcutsEvent);
        onWsEvent("reticulum_reload_status", this.onReloadStatusEvent);
        GlobalEmitter.on("identity-switched", this.onIdentitySwitched);
        window.addEventListener("keydown", this.onSettingsSearchHotkey);

        this.getConfig();
        this.getServerSecurity();
        this.loadExposureAcknowledgements();
        this.getTrustedTelemetryPeers();
        this.loadStickerCount();
        this.loadGifCount();
        this.loadVisualiserDisplayPrefsFromStorage();
        this.loadBatterySaverPrefsFromStorage();
        this.loadBatteryInterfaceRows();
        this.loadDesktopCloseSettings();
        this.loadScreenSecuritySettings();
        this.loadReticulumInstanceSettings();
        this.loadAndroidShellPrivacy();
    },
    methods: {
        onIdentitySwitched() {
            this.getConfig();
            this.getServerSecurity();
            this.getTrustedTelemetryPeers();
            this.loadStickerCount();
            this.loadGifCount();
            this.loadBatteryInterfaceRows();
            this.loadReticulumInstanceSettings();
            this.loadAndroidShellPrivacy();
        },
        loadBatterySaverPrefsFromStorage() {
            this.batterySaver = loadBatterySaverPrefs();
            if (!this.batterySaver.interfaceBitrateLimits) {
                this.batterySaver.interfaceBitrateLimits = {};
            }
        },
        async loadBatteryInterfaceRows() {
            try {
                const response = await window.api.get("/api/v1/reticulum/interfaces");
                const interfaces = response?.data?.interfaces || {};
                this.batteryInterfaceRows = Object.entries(interfaces)
                    .map(([name, iface]) => ({
                        name,
                        type: iface?.type || "",
                        bitrate: iface?.bitrate ?? null,
                    }))
                    .sort((a, b) => a.name.localeCompare(b.name));
                for (const row of this.batteryInterfaceRows) {
                    if (this.batterySaver.interfaceBitrateLimits[row.name] == null && row.bitrate != null) {
                        const n = Number(row.bitrate);
                        if (Number.isFinite(n) && n >= 0) {
                            // leave unset so empty means "no forced limit"
                        }
                    }
                }
            } catch {
                this.batteryInterfaceRows = [];
            }
        },
        patchBatterySaver(patch) {
            this.batterySaver = saveBatterySaverPrefs(patch);
            if (!this.batterySaver.interfaceBitrateLimits) {
                this.batterySaver.interfaceBitrateLimits = {};
            }
        },
        onBatterySaverEnabledChange(val) {
            const enabled = val === true;
            this.patchBatterySaver({ enabled });
            if (enabled && this.batterySaver.applyInterfaceBitrateLimits) {
                this.applyBatteryBitrateLimitsNow();
            } else if (!enabled && Object.keys(this.batterySaver.interfaceBitratePrevious || {}).length > 0) {
                this.restoreBatteryBitrateLimitsNow();
            }
        },
        onBatteryBitrateLimitChange(name) {
            const limits = { ...(this.batterySaver.interfaceBitrateLimits || {}) };
            const raw = limits[name];
            if (raw === "" || raw == null || Number.isNaN(Number(raw))) {
                delete limits[name];
            } else {
                limits[name] = Math.max(0, Math.round(Number(raw)));
            }
            this.patchBatterySaver({ interfaceBitrateLimits: limits });
        },
        async applyBatteryBitrateLimitsNow() {
            if (this.batteryBitrateBusy) return;
            this.batteryBitrateBusy = true;
            try {
                this.patchBatterySaver({
                    applyInterfaceBitrateLimits: true,
                    interfaceBitrateLimits: { ...(this.batterySaver.interfaceBitrateLimits || {}) },
                });
                const result = await applyBatterySaverBitrateLimits({ reload: true });
                this.loadBatterySaverPrefsFromStorage();
                if (result.updated.length === 0) {
                    ToastUtils.error(this.$t("settings.battery.bitrates_none_applied"));
                } else {
                    ToastUtils.success(this.$t("settings.battery.bitrates_applied", { count: result.updated.length }));
                }
                await this.loadBatteryInterfaceRows();
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("settings.battery.bitrates_apply_failed"));
            } finally {
                this.batteryBitrateBusy = false;
            }
        },
        async restoreBatteryBitrateLimitsNow() {
            if (this.batteryBitrateBusy) return;
            this.batteryBitrateBusy = true;
            try {
                const result = await restoreBatterySaverBitrateLimits({ reload: true });
                this.loadBatterySaverPrefsFromStorage();
                if (result.updated.length === 0) {
                    ToastUtils.error(this.$t("settings.battery.bitrates_none_restored"));
                } else {
                    ToastUtils.success(this.$t("settings.battery.bitrates_restored", { count: result.updated.length }));
                }
                await this.loadBatteryInterfaceRows();
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("settings.battery.bitrates_restore_failed"));
            } finally {
                this.batteryBitrateBusy = false;
            }
        },
        async loadReticulumInstanceSettings() {
            try {
                const instance = await fetchReticulumInstanceSettings(window.api);
                if (instance && typeof instance === "object") {
                    this.reticulumInstance = {
                        ...this.reticulumInstance,
                        ...instance,
                        shared_instance_type: instance.shared_instance_type || "",
                        instance_name: instance.instance_name || "default",
                        remote_management_allowed: Array.isArray(instance.remote_management_allowed)
                            ? instance.remote_management_allowed
                            : [],
                    };
                    this.remoteManagementAllowedText = (this.reticulumInstance.remote_management_allowed || []).join(
                        "\n"
                    );
                }
            } catch (e) {
                console.log(e);
            }
        },
        async patchReticulumInstance(patch) {
            if (this.reticulumInstanceSaving) return;
            this.reticulumInstanceSaving = true;
            try {
                const response = await applyReticulumInstanceSettings(patch, window.api);
                if (response?.data?.instance) {
                    const instance = response.data.instance;
                    this.reticulumInstance = {
                        ...this.reticulumInstance,
                        ...instance,
                        shared_instance_type: instance.shared_instance_type || "",
                        instance_name: instance.instance_name || "default",
                        remote_management_allowed: Array.isArray(instance.remote_management_allowed)
                            ? instance.remote_management_allowed
                            : [],
                    };
                    if ("remote_management_allowed" in (patch || {})) {
                        this.remoteManagementAllowedText = (
                            this.reticulumInstance.remote_management_allowed || []
                        ).join("\n");
                    }
                }
                if (response?.data?.message) {
                    ToastUtils.success(response.data.message);
                }
            } catch {
                ToastUtils.error(this.$t("settings.failed_update_reticulum_instance"));
                await this.loadReticulumInstanceSettings();
            } finally {
                this.reticulumInstanceSaving = false;
            }
        },
        onShareInstanceChange(value) {
            this.patchReticulumInstance({ share_instance: !!value });
        },
        onLocalHopsDeltaChange(value) {
            this.patchReticulumInstance({ local_hops_delta: !!value });
        },
        onRespondToProbesChange(value) {
            this.patchReticulumInstance({ respond_to_probes: !!value });
        },
        onEnableRemoteManagementChange(value) {
            this.patchReticulumInstance({ enable_remote_management: !!value });
        },
        saveRemoteManagementAllowed() {
            const hashes = (this.remoteManagementAllowedText || "")
                .split(/[\s,]+/)
                .map((value) => value.trim().toLowerCase())
                .filter((value) => value.length > 0);
            this.patchReticulumInstance({ remote_management_allowed: hashes });
        },
        onSettingsMgmtIdentityHash(hash) {
            this.settingsMgmtIdentityHash = hash || "";
        },
        onSharedInstanceTypeChange() {
            const value = this.reticulumInstance.shared_instance_type || null;
            this.patchReticulumInstance({ shared_instance_type: value });
        },
        onInstanceNameChange() {
            this.patchReticulumInstance({
                instance_name: this.reticulumInstance.instance_name || "default",
            });
        },
        async copyRpcConfigSnippet() {
            const snippet = this.reticulumInstance.rpc_config_snippet;
            if (!snippet) return;
            try {
                await navigator.clipboard.writeText(snippet);
                ToastUtils.success(this.$t("app.rpc_config_copied"));
            } catch {
                ToastUtils.error(this.$t("app.copy_failed"));
            }
        },
        isSelfTestReasonExpanded(key) {
            return !!this.selfTestExpandedReasons?.[key];
        },
        toggleSelfTestReason(key) {
            this.selfTestExpandedReasons = {
                ...this.selfTestExpandedReasons,
                [key]: !this.selfTestExpandedReasons?.[key],
            };
        },
        async loadDesktopCloseSettings() {
            if (!ElectronUtils.isElectron()) {
                return;
            }
            try {
                const settings = await ElectronUtils.getCloseSettings();
                if (settings && typeof settings === "object") {
                    this.desktopCloseSettings = {
                        closeBehavior: settings.closeBehavior || "ask",
                        trayEnabled: settings.trayEnabled !== false,
                    };
                }
            } catch (e) {
                console.log(e);
            }
        },
        async loadScreenSecuritySettings() {
            this.showWindowsScreenSecurity =
                typeof ElectronUtils.isWindowsElectron === "function" && ElectronUtils.isWindowsElectron();
            if (!this.showWindowsScreenSecurity) {
                return;
            }
            try {
                const settings = await ElectronUtils.getScreenSecuritySettings();
                this.screenSecurityEnabled = settings?.enabled === true;
            } catch (e) {
                console.log(e);
            }
        },
        async onScreenSecurityChange(value) {
            if (this.screenSecuritySaving) {
                return;
            }
            this.screenSecuritySaving = true;
            const enabled = value === true;
            try {
                if (!enabled) {
                    const confirmed = await DialogUtils.confirm(this.$t("app.screen_security_disable_confirm"));
                    if (!confirmed) {
                        this.screenSecurityEnabled = true;
                        return;
                    }
                }
                const settings = await ElectronUtils.setScreenSecurityEnabled(enabled);
                this.screenSecurityEnabled = settings?.enabled === true;
                ToastUtils.success(
                    this.screenSecurityEnabled
                        ? this.$t("app.screen_security_enabled_toast")
                        : this.$t("app.screen_security_disabled_toast")
                );
            } catch (e) {
                console.log(e);
                this.screenSecurityEnabled = !enabled;
                ToastUtils.error(this.$t("common.save_failed"));
            } finally {
                this.screenSecuritySaving = false;
            }
        },
        async onDesktopTrayEnabledChange(value) {
            this.desktopCloseSettings.trayEnabled = value === true;
            try {
                const settings = await ElectronUtils.setCloseSettings({
                    trayEnabled: this.desktopCloseSettings.trayEnabled,
                });
                if (settings && typeof settings === "object") {
                    this.desktopCloseSettings = {
                        closeBehavior: settings.closeBehavior || this.desktopCloseSettings.closeBehavior,
                        trayEnabled: settings.trayEnabled !== false,
                    };
                }
            } catch (e) {
                console.log(e);
                ToastUtils.error(this.$t("common.save_failed"));
            }
        },
        async onDesktopCloseBehaviorChange(value) {
            if (typeof value === "string" && value) {
                this.desktopCloseSettings.closeBehavior = value;
            }
            try {
                const settings = await ElectronUtils.setCloseSettings({
                    closeBehavior: this.desktopCloseSettings.closeBehavior,
                });
                if (settings && typeof settings === "object") {
                    this.desktopCloseSettings = {
                        closeBehavior: settings.closeBehavior || this.desktopCloseSettings.closeBehavior,
                        trayEnabled: settings.trayEnabled !== false,
                    };
                }
            } catch (e) {
                console.log(e);
                ToastUtils.error(this.$t("common.save_failed"));
            }
        },
        async runSelfTest() {
            if (this.selfTestRunning) {
                return;
            }
            this.selfTestRunning = true;
            this.selfTestResults = null;
            this.selfTestExpandedReasons = {};
            try {
                const response = await window.api.get("/api/v1/self-test");
                this.selfTestResults = response.data;
            } catch (e) {
                console.error("Failed to run system self-test", e);
                const failed = { status: "failed", reason: e.message || String(e) };
                this.selfTestResults = {
                    stack_up: { ...failed },
                    config_good: { ...failed },
                    db_good: { ...failed },
                    read_write_good: { ...failed },
                    identity_good: { ...failed },
                    imports_good: { ...failed },
                    storage_lock_good: { ...failed },
                    temp_fs_good: { ...failed },
                    public_assets_good: { ...failed },
                    lxmf_router_good: { ...failed },
                    subprocess_good: { ...failed },
                    run_module_good: { ...failed },
                    sqlite_roundtrip: { ...failed },
                    identity_roundtrip: { ...failed },
                    loopback_tcp: { ...failed },
                    unicode_path_good: { ...failed },
                    rnode_support_good: { ...failed },
                    bot_launcher_good: { ...failed },
                    http_status_good: { ...failed },
                    http_app_info_good: { ...failed },
                    http_config_good: { ...failed },
                    http_db_health_good: { ...failed },
                    http_auth_csrf_good: { ...failed },
                    http_bots_status_good: { ...failed },
                    http_security_good: { ...failed },
                    http_interfaces_good: { ...failed },
                    http_reticulum_instance_good: { ...failed },
                    http_identities_good: { ...failed },
                    http_favourites_good: { ...failed },
                    http_telephone_good: { ...failed },
                    http_plugins_good: { ...failed },
                    http_plugins_trust_good: { ...failed },
                    http_sideband_plugins_good: { ...failed },
                    http_sideband_config_good: { ...failed },
                    http_rrc_hubs_good: { ...failed },
                    http_rrc_servers_good: { ...failed },
                    plugins_runtime_good: { ...failed },
                    websocket_good: { ...failed },
                    websocket_rns_link_good: { ...failed },
                    bots_lifecycle: { ...failed },
                };
            } finally {
                this.selfTestRunning = false;
            }
        },
        loadVisualiserDisplayPrefsFromStorage() {
            const p = loadVisualiserDisplayPrefs();
            this.visualiserShowDisabledInterfaces = p.showDisabledInterfaces;
            this.visualiserShowDiscoveredInterfaces = p.showDiscoveredInterfaces;
            this.visualiserRenderer = p.renderer || "auto";
            this.visualiserViewMode = p.viewMode === "planet" ? "planet" : "flat";
        },
        onVisualiserShowDisabledChange(val) {
            this.visualiserShowDisabledInterfaces = val;
            persistVisualiserShowDisabled(val);
        },
        onVisualiserShowDiscoveredChange(val) {
            this.visualiserShowDiscoveredInterfaces = val;
            persistVisualiserShowDiscovered(val);
        },
        onVisualiserRendererChange() {
            persistVisualiserRenderer(this.visualiserRenderer);
        },
        onVisualiserViewModeChange() {
            persistVisualiserViewMode(this.visualiserViewMode);
        },
        async getTrustedTelemetryPeers() {
            try {
                const response = await window.api.get("/api/v1/telemetry/trusted-peers");
                this.trustedTelemetryPeers = response.data.trusted_peers;
            } catch (e) {
                console.error("Failed to fetch trusted telemetry peers", e);
            }
        },
        async revokeTelemetryTrust(peer) {
            try {
                await window.api.patch(`/api/v1/telephone/contacts/${peer.id}`, {
                    is_telemetry_trusted: false,
                });
                this.getTrustedTelemetryPeers();
                ToastUtils.success(this.$t("app.telemetry_trust_revoked", { name: peer.name }));
            } catch (e) {
                ToastUtils.error(this.$t("app.telemetry_trust_failed"));
                console.error(e);
            }
        },
        onSettingsSearchInput(e) {
            const el = e?.target;
            if (!el || el.tagName !== "INPUT") return;
            this.searchQuery = el.value;
            if (!normalizeSearchString(this.searchQuery)) {
                this.searchTabFilter = null;
            }
        },
        onSettingsSearchCompositionEnd(e) {
            const el = e?.target;
            if (!el || el.tagName !== "INPUT") return;
            this.searchQuery = el.value;
        },
        clearSettingsSearch() {
            this.searchQuery = "";
            this.searchTabFilter = null;
        },
        onSettingsSearchHotkey(e) {
            if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey) return;
            const active = document.activeElement;
            const inField =
                active && (["INPUT", "TEXTAREA", "SELECT"].includes(active.tagName) || active.isContentEditable);
            if (inField) return;
            e.preventDefault();
            const input = this.$refs.settingsSearchInput;
            if (input && typeof input.focus === "function") {
                input.focus();
                if (typeof input.select === "function") {
                    input.select();
                }
            }
        },
        onSettingsNavSelect(tabId) {
            if (this.settingsSearchActive) {
                this.searchTabFilter = this.searchTabFilter === tabId ? null : tabId;
                return;
            }
            this.selectSettingsTab(tabId);
        },
        sectionAvailable(sectionKey) {
            if (sectionKey === "plugins" && GlobalState.pluginsEnabled === false) {
                return false;
            }
            return true;
        },
        sectionSearchTexts(sectionKey) {
            const keywords = this.sectionKeywords[sectionKey] || [];
            return [...keywords, ...settingsSectionSearchExtras(sectionKey)];
        },
        sectionMatchesQuery(sectionKey) {
            if (!this.sectionAvailable(sectionKey)) return false;
            return matchesSettingSearch(this.sectionSearchTexts(sectionKey), (k) => this.$t(k), this.searchQuery);
        },
        shareAndroidApk() {
            const bridge = new AndroidBridge();
            if (!bridge.shareApk()) {
                ToastUtils.error(this.$t("settings.share_apk_failed"));
            }
        },
        loadAndroidShellPrivacy() {
            if (!this.isMeshChatXAndroid) {
                return;
            }
            const bridge = new AndroidBridge();
            this.androidShellPrivacy = {
                blockScreenshots: bridge.getBlockScreenshots(),
                clearClipboardOnBackground: bridge.getClearClipboardOnBackground(),
            };
            this.androidRemoteBackendUrl = bridge.getRemoteBackendUrl() || "";
            this.androidEffectiveBackendUrl = bridge.getEffectiveBackendUrl() || "";
            this.androidRemoteBackendActive = bridge.isRemoteBackend() === true;
        },
        applyAndroidRemoteBackend() {
            const bridge = new AndroidBridge();
            const draft = (this.androidRemoteBackendUrl || "").trim();
            const result = bridge.setRemoteBackendUrlAndRestart(draft);
            if (result === "invalid") {
                ToastUtils.error(this.$t("settings.android_remote_backend_invalid"));
                return;
            }
            if (result === "unsupported") {
                ToastUtils.error(this.$t("settings.android_privacy_save_failed"));
                return;
            }
            if (result === "unchanged") {
                ToastUtils.info(this.$t("settings.android_remote_backend_unchanged"));
                return;
            }
            ToastUtils.success(this.$t("settings.android_remote_backend_restarting"));
        },
        clearAndroidRemoteBackend() {
            this.androidRemoteBackendUrl = "";
            const bridge = new AndroidBridge();
            const result = bridge.setRemoteBackendUrlAndRestart("");
            if (result === "unsupported") {
                ToastUtils.error(this.$t("settings.android_privacy_save_failed"));
                return;
            }
            if (result === "unchanged") {
                ToastUtils.info(this.$t("settings.android_remote_backend_already_local"));
                return;
            }
            ToastUtils.success(this.$t("settings.android_remote_backend_restarting"));
        },
        saveAndroidBlockScreenshots() {
            const bridge = new AndroidBridge();
            const enabled = Boolean(this.androidShellPrivacy.blockScreenshots);
            if (!bridge.setBlockScreenshots(enabled)) {
                this.androidShellPrivacy.blockScreenshots = !enabled;
                ToastUtils.error(this.$t("settings.android_privacy_save_failed"));
                return;
            }
            ToastUtils.success(
                enabled
                    ? this.$t("settings.android_block_screenshots_on")
                    : this.$t("settings.android_block_screenshots_off")
            );
        },
        saveAndroidClearClipboardOnBackground() {
            const bridge = new AndroidBridge();
            const enabled = Boolean(this.androidShellPrivacy.clearClipboardOnBackground);
            if (!bridge.setClearClipboardOnBackground(enabled)) {
                this.androidShellPrivacy.clearClipboardOnBackground = !enabled;
                ToastUtils.error(this.$t("settings.android_privacy_save_failed"));
                return;
            }
            ToastUtils.success(
                enabled
                    ? this.$t("settings.android_clear_clipboard_on_background_on")
                    : this.$t("settings.android_clear_clipboard_on_background_off")
            );
        },
        matchesSearch(...texts) {
            return matchesSettingSearch(texts, (k) => this.$t(k), this.searchQuery);
        },
        showSection(sectionKey) {
            if (!this.sectionAvailable(sectionKey)) {
                return false;
            }
            if (this.settingsSearchActive) {
                if (!this.sectionMatchesQuery(sectionKey)) {
                    return false;
                }
                const filter = this.searchTabFilter;
                if (filter && this.settingsSearchMatchCounts[filter] > 0) {
                    return settingsSectionBelongsToTab(sectionKey, filter);
                }
                return true;
            }
            const tab = SETTINGS_TABS.find((entry) => entry.id === this.activeSettingsTab);
            return Boolean(tab && tab.sections.includes(sectionKey));
        },
        selectSettingsTab(tabId) {
            this.activeSettingsTab = normalizeSettingsTabId(tabId);
        },
        onConfigEvent(json) {
            if (json.config) {
                this.config = { ...this.config, ...json.config };
                this.sanitizeColorConfigFields();
                this.syncLxmfTransferLimitInputs();
            }
        },
        onKeyboardShortcutsEvent(json) {
            this.shortcuts = json.shortcuts;
        },
        onReloadStatusEvent(json) {
            const message = json.message || this.$t("app.reloading_rns");
            this.reloadRnsStatusMessage = message;
            this.reloadingRns = json.in_progress !== false;
            const toastKey = "settings-rns-reload";
            if (json.level === "error") {
                ToastUtils.dismiss(toastKey);
                ToastUtils.error(message, 7000);
            } else if (json.level === "success") {
                ToastUtils.dismiss(toastKey);
                ToastUtils.success(message, 5000);
            } else {
                ToastUtils.info(message, 2500, toastKey);
            }
        },
        onWebsocketMessage(message) {
            let json;
            try {
                if (
                    message &&
                    typeof message === "object" &&
                    typeof message.type === "string" &&
                    message.data === undefined
                ) {
                    json = message;
                } else {
                    const raw = typeof message === "string" ? message : message?.data;
                    json = typeof raw === "string" ? JSON.parse(raw) : message;
                }
            } catch {
                return;
            }
            if (!json || typeof json !== "object" || typeof json.type !== "string") {
                return;
            }
            switch (json.type) {
                case "config":
                    return this.onConfigEvent(json);
                case "keyboard_shortcuts":
                    return this.onKeyboardShortcutsEvent(json);
                case "reticulum_reload_status":
                    return this.onReloadStatusEvent(json);
                default:
                    break;
            }
        },
        async getConfig() {
            try {
                const merged = await fetchMergedConfig(window.api, this.config);
                if (merged) {
                    this.config = merged;
                    normalizeConfigColors(this.config);
                    this.syncLxmfTransferLimitInputs();
                    const inbound = Number(this.config.lxmf_inbound_stamp_cost);
                    if (inbound > 0) {
                        this.lastRememberedInboundStampCost = Math.min(254, inbound);
                    }
                }
                this.getKeyboardShortcuts();
            } catch (e) {
                console.log(e);
            }
        },
        loadExposureAcknowledgements() {
            try {
                this.exposureAckFirewall = localStorage.getItem("meshchatx_exposure_ack_firewall") === "1";
                this.exposureAckVpn = localStorage.getItem("meshchatx_exposure_ack_vpn") === "1";
            } catch {
                this.exposureAckFirewall = false;
                this.exposureAckVpn = false;
            }
        },
        persistExposureAcknowledgements() {
            try {
                localStorage.setItem("meshchatx_exposure_ack_firewall", this.exposureAckFirewall ? "1" : "0");
                localStorage.setItem("meshchatx_exposure_ack_vpn", this.exposureAckVpn ? "1" : "0");
            } catch {
                // ignore storage failures
            }
        },
        async getServerSecurity() {
            try {
                const response = await window.api.get("/api/v1/server/security");
                this.serverSecurity = { ...this.serverSecurity, ...response.data };
            } catch (e) {
                console.log(e);
            }
        },
        async onPrivacyModeChange(value) {
            await this.updateConfig({ privacy_mode_enabled: value }, "privacy_mode_enabled");
        },
        async onMultiSessionWarningChange(value) {
            await this.updateConfig({ multi_session_warning_enabled: value }, "multi_session_warning_enabled");
        },
        onWebUiAllowlistChange() {
            if (this.saveTimeouts.webUiAllowlist) clearTimeout(this.saveTimeouts.webUiAllowlist);
            this.saveTimeouts.webUiAllowlist = setTimeout(async () => {
                try {
                    const response = await window.api.patch("/api/v1/server/security", {
                        web_ui_ip_allowlist: this.serverSecurity.web_ui_ip_allowlist,
                    });
                    this.serverSecurity = { ...this.serverSecurity, ...response.data };
                    ToastUtils.success(
                        this.$t("app.setting_auto_saved", { label: this.$t("app.web_ui_ip_allowlist") })
                    );
                } catch (e) {
                    ToastUtils.error(this.$t("common.save_failed"));
                    console.log(e);
                }
            }, 800);
        },
        getKeyboardShortcuts() {
            WebSocketConnection.send(
                JSON.stringify({
                    type: "keyboard_shortcuts.get",
                })
            );
        },
        getShortcutKeys(action) {
            const shortcut = this.shortcuts.find((s) => s.action === action);
            if (shortcut) return shortcut.keys;

            // Fallback to default
            const def = KeyboardShortcuts.getDefaultShortcuts().find((s) => s.action === action);
            return def ? def.keys : [];
        },
        async saveShortcut(action, keys) {
            await KeyboardShortcuts.saveShortcut(action, keys);
            ToastUtils.success(this.$t("settings.shortcut_saved"));
        },
        async deleteShortcut(action) {
            await KeyboardShortcuts.deleteShortcut(action);
            ToastUtils.success(this.$t("settings.shortcut_deleted"));
        },
        async updateConfig(config, label = null) {
            try {
                const newConfig = await patchServerConfig(config, window.api);
                publishPatchedConfig(newConfig);
                this.config = newConfig;
                normalizeConfigColors(this.config);
                this.syncLxmfTransferLimitInputs();
                if (label) {
                    ToastUtils.success(this.$t("app.setting_auto_saved", { label: this.$t(`app.${label}`) }));
                }
            } catch (e) {
                ToastUtils.error(this.$t("common.save_failed"));
                console.log(e);
            }
        },
        async onMapOverlayLimitChange(key) {
            const field = this.mapOverlayLimitFields.find((f) => f.key === key);
            let value = Number(this.config[key]);
            if (!Number.isFinite(value)) {
                return;
            }
            if (field) {
                value = Math.max(field.min, Math.min(field.max, Math.trunc(value)));
                this.config[key] = value;
            }
            await this.updateConfig({ [key]: value }, key);
        },
        syncLxmfTransferLimitInputs() {
            const incoming = syncIncomingDeliveryFieldsFromBytes(this.config.lxmf_delivery_transfer_limit_in_bytes);
            this.lxmfIncomingDeliveryPreset = incoming.preset;
            this.lxmfIncomingDeliveryCustomAmount = incoming.customAmount;
            this.lxmfIncomingDeliveryCustomUnit = incoming.customUnit;
            this.lxmfPropagationTransferLimitInputMb = this.bytesToMb(
                this.config.lxmf_propagation_transfer_limit_in_bytes
            );
            this.lxmfPropagationSyncLimitInputMb = this.bytesToMb(this.config.lxmf_propagation_sync_limit_in_bytes);
        },
        bytesToMb(value) {
            const n = Number(value);
            if (!Number.isFinite(n) || n <= 0) {
                return 0;
            }
            return Math.max(0.001, Math.round((n / 1000000) * 1000) / 1000);
        },
        mbToBytes(value) {
            const n = Number(value);
            if (!Number.isFinite(n) || n <= 0) {
                return 1000;
            }
            return Math.max(1000, Math.round(n * 1000000));
        },
        formatByteSize(bytes) {
            const value = Number(bytes);
            if (!Number.isFinite(value) || value < 0) return "0 B";
            if (value < 1000) return `${Math.round(value)} B`;
            if (value < 1000 * 1000) return `${(value / 1000).toFixed(1)} KB`;
            if (value < 1000 * 1000 * 1000) return `${(value / (1000 * 1000)).toFixed(2)} MB`;
            return `${(value / (1000 * 1000 * 1000)).toFixed(2)} GB`;
        },
        sanitizeColorConfigFields() {
            if (!this.config) return;
            normalizeConfigColors(this.config);
        },
        async onAnnounceLimitsChange() {
            const c = this.config;
            await this.updateConfig(
                {
                    announce_max_stored_lxmf_delivery: numOrNull(c.announce_max_stored_lxmf_delivery),
                    announce_max_stored_nomadnetwork_node: numOrNull(c.announce_max_stored_nomadnetwork_node),
                    announce_max_stored_lxmf_propagation: numOrNull(c.announce_max_stored_lxmf_propagation),
                    announce_max_stored_map_data: numOrNull(c.announce_max_stored_map_data),
                    announce_fetch_limit_lxmf_delivery: numOrNull(c.announce_fetch_limit_lxmf_delivery),
                    announce_fetch_limit_nomadnetwork_node: numOrNull(c.announce_fetch_limit_nomadnetwork_node),
                    announce_fetch_limit_lxmf_propagation: numOrNull(c.announce_fetch_limit_lxmf_propagation),
                    announce_fetch_limit_map_data: numOrNull(c.announce_fetch_limit_map_data),
                    announce_search_max_fetch: numOrNull(c.announce_search_max_fetch),
                    discovered_interfaces_max_return: numOrNull(c.discovered_interfaces_max_return),
                },
                "announce_limits"
            );
        },
        async onAnnounceStoreToggle(key, value) {
            this.config[key] = value;
            await this.updateConfig({ [key]: value }, key);
        },
        async copyValue(value, label) {
            if (!value) {
                ToastUtils.warning(`Nothing to copy for ${label}`);
                return;
            }
            try {
                await navigator.clipboard.writeText(value);
                ToastUtils.success(`${label} copied to clipboard`);
            } catch {
                ToastUtils.info(`${label}: ${value}`);
            }
        },
        async onThemeChange() {
            applyAppearanceTheme(this.config);
            await this.updateConfig(
                {
                    theme: this.config.theme,
                },
                "theme"
            );
        },
        async onThemePresetChange() {
            applyAppearanceTheme(this.config);
            await this.updateConfig(
                {
                    theme_preset: this.config.theme_preset,
                },
                "theme_preset"
            );
        },
        onAccentColorChange() {
            if (this.saveTimeouts.accent_color) clearTimeout(this.saveTimeouts.accent_color);
            this.saveTimeouts.accent_color = setTimeout(async () => {
                applyAppearanceTheme(this.config);
                await this.updateConfig(
                    {
                        accent_color: this.config.accent_color,
                    },
                    "accent_color"
                );
            }, 600);
        },
        onCustomCanvasColorChange() {
            if (this.saveTimeouts.custom_canvas_color) clearTimeout(this.saveTimeouts.custom_canvas_color);
            this.saveTimeouts.custom_canvas_color = setTimeout(async () => {
                applyAppearanceTheme(this.config);
                await this.updateConfig(
                    {
                        custom_canvas_color: this.config.custom_canvas_color,
                    },
                    "custom_canvas_color"
                );
            }, 600);
        },
        onCustomSurfaceColorChange() {
            if (this.saveTimeouts.custom_surface_color) clearTimeout(this.saveTimeouts.custom_surface_color);
            this.saveTimeouts.custom_surface_color = setTimeout(async () => {
                applyAppearanceTheme(this.config);
                await this.updateConfig(
                    {
                        custom_surface_color: this.config.custom_surface_color,
                    },
                    "custom_surface_color"
                );
            }, 600);
        },
        async onMessagesSidebarPositionChange() {
            const v = this.config.messages_sidebar_position === "right" ? "right" : "left";
            this.config.messages_sidebar_position = v;
            await this.updateConfig(
                {
                    messages_sidebar_position: v,
                },
                "messages_sidebar_position"
            );
        },
        async onAppSidebarLayoutChange() {
            const v = this.config.app_sidebar_layout === "classic" ? "classic" : "grouped";
            this.config.app_sidebar_layout = v;
            await this.updateConfig(
                {
                    app_sidebar_layout: v,
                },
                "app_sidebar_layout"
            );
        },
        async onMessageFontSizeChange() {
            if (this.saveTimeouts.message_font_size) clearTimeout(this.saveTimeouts.message_font_size);
            this.saveTimeouts.message_font_size = setTimeout(async () => {
                await this.updateConfig(
                    {
                        message_font_size: this.config.message_font_size,
                    },
                    "message_font_size"
                );
            }, 1000);
        },
        async onDisplayNameChange() {
            if (this.saveTimeouts.display_name) clearTimeout(this.saveTimeouts.display_name);
            this.saveTimeouts.display_name = setTimeout(async () => {
                await this.updateConfig(
                    {
                        display_name: this.config.display_name,
                    },
                    "display_name"
                );
            }, 600);
        },
        async onMessageIconSizeChange() {
            if (this.saveTimeouts.message_icon_size) clearTimeout(this.saveTimeouts.message_icon_size);
            this.saveTimeouts.message_icon_size = setTimeout(async () => {
                await this.updateConfig(
                    {
                        message_icon_size: this.config.message_icon_size,
                    },
                    "message_icon_size"
                );
            }, 1000);
        },
        onUiTransparencyChange() {
            if (this.saveTimeouts.ui_transparency) clearTimeout(this.saveTimeouts.ui_transparency);
            this.saveTimeouts.ui_transparency = setTimeout(async () => {
                const n = Number(this.config.ui_transparency);
                const v = Number.isFinite(n) ? Math.max(0, Math.min(100, Math.round(n))) : 0;
                this.config.ui_transparency = v;
                await this.updateConfig(
                    {
                        ui_transparency: v,
                    },
                    "ui_transparency"
                );
            }, 400);
        },
        async onUiGlassEnabledChange() {
            await this.updateConfig(
                {
                    ui_glass_enabled: this.config.ui_glass_enabled,
                },
                "ui_glass_enabled"
            );
        },
        async onMessagesMultiPaneEnabledChange() {
            await this.updateConfig(
                {
                    messages_multi_pane_enabled: this.config.messages_multi_pane_enabled,
                },
                "messages_multi_pane_enabled"
            );
        },
        async onNomadTabsEnabledChange() {
            await this.updateConfig(
                {
                    nomad_tabs_enabled: this.config.nomad_tabs_enabled,
                },
                "nomad_tabs_enabled"
            );
        },
        async onRrcEnabledChange() {
            await this.updateConfig(
                {
                    rrc_enabled: this.config.rrc_enabled,
                },
                "rrc_enabled"
            );
        },
        async onRrcUnreadBadgesEnabledChange() {
            await this.updateConfig(
                {
                    rrc_unread_badges_enabled: this.config.rrc_unread_badges_enabled,
                },
                "rrc_unread_badges_enabled"
            );
        },
        async resetAppearanceDefaults() {
            this.config.theme = "light";
            this.config.theme_preset = "default";
            this.config.accent_color = null;
            this.config.custom_canvas_color = null;
            this.config.custom_surface_color = null;
            this.config.messages_sidebar_position = "left";
            this.config.app_sidebar_layout = "grouped";
            this.config.message_font_size = 14;
            this.config.message_icon_size = 28;
            this.config.ui_transparency = 0;
            this.config.ui_glass_enabled = true;
            this.config.message_outbound_bubble_color = "#4f46e5";
            this.config.message_inbound_bubble_color = null;
            this.config.message_failed_bubble_color = "#ef4444";
            this.config.message_waiting_bubble_color = "#e5e7eb";
            applyAppearanceTheme(this.config);
            await this.updateConfig(
                {
                    theme: "light",
                    theme_preset: "default",
                    accent_color: null,
                    custom_canvas_color: null,
                    custom_surface_color: null,
                    messages_sidebar_position: "left",
                    app_sidebar_layout: "grouped",
                    message_font_size: 14,
                    message_icon_size: 28,
                    ui_transparency: 0,
                    ui_glass_enabled: true,
                    message_outbound_bubble_color: "#4f46e5",
                    message_inbound_bubble_color: null,
                    message_failed_bubble_color: "#ef4444",
                    message_waiting_bubble_color: "#e5e7eb",
                },
                "appearance"
            );
        },
        async onMessageBubbleColorChange(type) {
            const timeoutKey = `message_${type}_bubble_color`;
            if (this.saveTimeouts[timeoutKey]) clearTimeout(this.saveTimeouts[timeoutKey]);
            this.saveTimeouts[timeoutKey] = setTimeout(async () => {
                const configKey = `message_${type}_bubble_color`;
                await this.updateConfig(
                    {
                        [configKey]: this.config[configKey],
                    },
                    configKey
                );
            }, 1000);
        },
        onDetailedOutboundSendStatusChange(event) {
            const checked = event.target.checked;
            GlobalState.detailedOutboundSendStatus = checked;
            try {
                localStorage.setItem("meshchatx_detailed_outbound_send_status", checked ? "true" : "false");
            } catch {
                // ignore
            }
        },
        onOutboundTransferProgressEnabledChange(event) {
            const checked = event.target.checked;
            GlobalState.outboundTransferProgressEnabled = checked;
            try {
                localStorage.setItem("meshchatx_outbound_transfer_progress_enabled", checked ? "true" : "false");
            } catch {
                // ignore
            }
        },
        onMessageTimestampGroupingChange(event) {
            const checked = event.target.checked;
            GlobalState.messageTimestampGroupingEnabled = checked;
            try {
                localStorage.setItem("meshchatx_message_timestamp_grouping_enabled", checked ? "true" : "false");
            } catch {
                // ignore
            }
        },
        async onLanguageSectionChange(language) {
            this.config.language = language;
            await this.onLanguageChange();
        },
        async onLanguageChange() {
            await setLocale(this.$i18n, this.config.language);
            await this.updateConfig(
                {
                    language: this.config.language,
                },
                "language"
            );
        },
        async onAutoResendFailedMessagesWhenAnnounceReceivedChangeWrapper(value) {
            this.config.auto_resend_failed_messages_when_announce_received = value;
            await this.onAutoResendFailedMessagesWhenAnnounceReceivedChange();
        },
        async onAutoResendFailedMessagesWhenAnnounceReceivedChange() {
            await this.updateConfig(
                {
                    auto_resend_failed_messages_when_announce_received:
                        this.config.auto_resend_failed_messages_when_announce_received,
                },
                "auto_resend"
            );
        },
        async onAllowAutoResendingFailedMessagesWithAttachmentsChangeWrapper(value) {
            this.config.allow_auto_resending_failed_messages_with_attachments = value;
            await this.onAllowAutoResendingFailedMessagesWithAttachmentsChange();
        },
        async onAllowAutoResendingFailedMessagesWithAttachmentsChange() {
            await this.updateConfig(
                {
                    allow_auto_resending_failed_messages_with_attachments:
                        this.config.allow_auto_resending_failed_messages_with_attachments,
                },
                "retry_attachments"
            );
        },
        async onAutoSendFailedMessagesToPropagationNodeChangeWrapper(value) {
            this.config.auto_send_failed_messages_to_propagation_node = value;
            await this.onAutoSendFailedMessagesToPropagationNodeChange();
        },
        async onAutoSendFailedMessagesToPropagationNodeChange() {
            await this.updateConfig(
                {
                    auto_send_failed_messages_to_propagation_node:
                        this.config.auto_send_failed_messages_to_propagation_node,
                },
                "auto_fallback"
            );
        },
        async onShowSuggestedCommunityInterfacesChangeWrapper(value) {
            this.config.show_suggested_community_interfaces = value;
            await this.onShowSuggestedCommunityInterfacesChange();
        },
        async onShowSuggestedCommunityInterfacesChange() {
            await this.updateConfig(
                {
                    show_suggested_community_interfaces: this.config.show_suggested_community_interfaces,
                },
                "community_interfaces"
            );
        },
        async onLxmfPreferredPropagationNodeDestinationHashChange() {
            if (this.saveTimeouts.preferred_node) clearTimeout(this.saveTimeouts.preferred_node);
            this.saveTimeouts.preferred_node = setTimeout(async () => {
                await this.savePreferredPropagationNodeHash(false);
            }, 1000);
        },
        onPreferredPropagationNodePaste(event) {
            const text = event.clipboardData?.getData("text") || "";
            const parsed = Utils.parseDestinationHash(text);
            if (!parsed) {
                return;
            }
            event.preventDefault();
            this.config.lxmf_preferred_propagation_node_destination_hash = parsed;
            this.savePreferredPropagationNodeHash(true);
        },
        async pastePreferredPropagationNodeHash() {
            const result = await readTextFromClipboard();
            if (!result.ok) {
                ToastUtils.error(this.$t("messages.failed_read_clipboard"));
                return;
            }
            const parsed = Utils.parseDestinationHash(result.text);
            if (!parsed) {
                ToastUtils.error(this.$t("tools.propagation_nodes.invalid_hash"));
                return;
            }
            this.config.lxmf_preferred_propagation_node_destination_hash = parsed;
            await this.savePreferredPropagationNodeHash(true);
        },
        async clearPreferredPropagationNodeHash() {
            this.config.lxmf_preferred_propagation_node_destination_hash = "";
            await this.savePreferredPropagationNodeHash(true);
        },
        async savePreferredPropagationNodeHash(showInvalidToast) {
            if (this.saveTimeouts.preferred_node) {
                clearTimeout(this.saveTimeouts.preferred_node);
                this.saveTimeouts.preferred_node = null;
            }
            const raw = this.config.lxmf_preferred_propagation_node_destination_hash;
            const trimmed = (raw || "").toString().trim();
            if (!trimmed) {
                await this.updateConfig(
                    {
                        lxmf_preferred_propagation_node_destination_hash: null,
                    },
                    "preferred_node"
                );
                return;
            }
            const parsed = Utils.parseDestinationHash(trimmed);
            if (!parsed) {
                if (showInvalidToast) {
                    ToastUtils.error(this.$t("tools.propagation_nodes.invalid_hash"));
                }
                return;
            }
            this.config.lxmf_preferred_propagation_node_destination_hash = parsed;
            const patch = {
                lxmf_preferred_propagation_node_destination_hash: parsed,
            };
            if (this.config.lxmf_preferred_propagation_node_auto_select) {
                patch.lxmf_preferred_propagation_node_auto_select = false;
                this.config.lxmf_preferred_propagation_node_auto_select = false;
            }
            await this.updateConfig(patch, "preferred_node");
        },
        async onLxmfPreferredPropagationNodeAutoSelectChange() {
            await this.updateConfig(
                {
                    lxmf_preferred_propagation_node_auto_select:
                        this.config.lxmf_preferred_propagation_node_auto_select,
                },
                "auto_select_node"
            );
        },
        async onLxmfLocalPropagationNodeEnabledChangeWrapper(value) {
            this.config.lxmf_local_propagation_node_enabled = value;
            await this.onLxmfLocalPropagationNodeEnabledChange();
        },
        async onLxmfLocalPropagationNodeEnabledChange() {
            await this.updateConfig(
                {
                    lxmf_local_propagation_node_enabled: this.config.lxmf_local_propagation_node_enabled,
                },
                "local_node"
            );
        },
        async onLxmfPreferredPropagationNodeAutoSyncIntervalSecondsChange() {
            await this.updateConfig(
                {
                    lxmf_preferred_propagation_node_auto_sync_interval_seconds:
                        this.config.lxmf_preferred_propagation_node_auto_sync_interval_seconds,
                },
                "auto_sync"
            );
        },
        async onLxmfIncomingDeliveryPresetChange() {
            if (this.lxmfIncomingDeliveryPreset === "custom") {
                const incoming = syncIncomingDeliveryFieldsFromBytes(this.config.lxmf_delivery_transfer_limit_in_bytes);
                this.lxmfIncomingDeliveryCustomAmount = incoming.customAmount;
                this.lxmfIncomingDeliveryCustomUnit = incoming.customUnit;
                return;
            }
            const bytes = incomingDeliveryBytesFromPresetKey(this.lxmfIncomingDeliveryPreset);
            if (bytes == null) {
                return;
            }
            await this.updateConfig(
                {
                    lxmf_delivery_transfer_limit_in_bytes: bytes,
                },
                "incoming_message_size"
            );
        },
        async onLxmfIncomingDeliveryCustomChange() {
            if (this.lxmfIncomingDeliveryPreset !== "custom") {
                return;
            }
            if (this.saveTimeouts.delivery_transfer_limit) {
                clearTimeout(this.saveTimeouts.delivery_transfer_limit);
            }
            this.saveTimeouts.delivery_transfer_limit = setTimeout(async () => {
                await this.updateConfig({
                    lxmf_delivery_transfer_limit_in_bytes: incomingDeliveryBytesFromCustom(
                        this.lxmfIncomingDeliveryCustomAmount,
                        this.lxmfIncomingDeliveryCustomUnit
                    ),
                });
            }, 1000);
        },
        async onLxmfPropagationTransferLimitChange() {
            if (this.saveTimeouts.propagation_transfer_limit) {
                clearTimeout(this.saveTimeouts.propagation_transfer_limit);
            }
            this.saveTimeouts.propagation_transfer_limit = setTimeout(async () => {
                await this.updateConfig({
                    lxmf_propagation_transfer_limit_in_bytes: this.mbToBytes(this.lxmfPropagationTransferLimitInputMb),
                });
            }, 1000);
        },
        async onLxmfPropagationSyncLimitChange() {
            if (this.saveTimeouts.propagation_sync_limit) {
                clearTimeout(this.saveTimeouts.propagation_sync_limit);
            }
            this.saveTimeouts.propagation_sync_limit = setTimeout(async () => {
                await this.updateConfig({
                    lxmf_propagation_sync_limit_in_bytes: this.mbToBytes(this.lxmfPropagationSyncLimitInputMb),
                });
            }, 1000);
        },
        async onInboundStampsEnabledChange(enabled) {
            if (!enabled) {
                const cur = Number(this.config.lxmf_inbound_stamp_cost);
                if (cur > 0) {
                    this.lastRememberedInboundStampCost = Math.min(254, cur);
                }
                this.config.lxmf_inbound_stamp_cost = 0;
                await this.updateConfig(
                    {
                        lxmf_inbound_stamp_cost: 0,
                    },
                    "inbound_stamp_cost_label"
                );
                return;
            }
            const restore = Math.min(254, Math.max(1, Number(this.lastRememberedInboundStampCost) || 8));
            this.config.lxmf_inbound_stamp_cost = restore;
            await this.updateConfig(
                {
                    lxmf_inbound_stamp_cost: restore,
                },
                "inbound_stamp_cost_label"
            );
        },
        async onLxmfInboundStampCostChange() {
            if (this.saveTimeouts.inbound_stamp) clearTimeout(this.saveTimeouts.inbound_stamp);
            this.saveTimeouts.inbound_stamp = setTimeout(async () => {
                let cost = Number(this.config.lxmf_inbound_stamp_cost);
                if (!cost || cost < 1) {
                    cost = 8;
                    this.config.lxmf_inbound_stamp_cost = cost;
                } else if (cost > 254) {
                    cost = 254;
                    this.config.lxmf_inbound_stamp_cost = cost;
                }
                this.lastRememberedInboundStampCost = cost;
                await this.updateConfig(
                    {
                        lxmf_inbound_stamp_cost: cost,
                    },
                    "inbound_stamp_cost_label"
                );
            }, 1000);
        },
        async onLxmfPropagationNodeStampCostChange() {
            if (this.saveTimeouts.propagation_stamp) clearTimeout(this.saveTimeouts.propagation_stamp);
            this.saveTimeouts.propagation_stamp = setTimeout(async () => {
                await this.updateConfig(
                    {
                        lxmf_propagation_node_stamp_cost: this.config.lxmf_propagation_node_stamp_cost,
                    },
                    "propagation_stamp_cost_label"
                );
            }, 1000);
        },
        async onLxmfPropagationSequentialValidationChange(value) {
            await this.updateConfig({
                lxmf_propagation_sequential_validation: value,
            });
        },
        async onLxmfPropagationStaticPeersBypassChange(value) {
            await this.updateConfig({
                lxmf_propagation_static_peers_bypass_sequential: value,
            });
        },
        async onLxmfPropagationMaxInboundSyncsChange() {
            if (this.saveTimeouts.propagation_max_inbound_syncs) {
                clearTimeout(this.saveTimeouts.propagation_max_inbound_syncs);
            }
            this.saveTimeouts.propagation_max_inbound_syncs = setTimeout(async () => {
                let v = Number(this.config.lxmf_propagation_max_inbound_syncs);
                if (!v || v < 1) v = 1;
                else if (v > 64) v = 64;
                this.config.lxmf_propagation_max_inbound_syncs = v;
                await this.updateConfig({
                    lxmf_propagation_max_inbound_syncs: v,
                });
            }, 1000);
        },
        async onLxmfFloodProtectionEnabledChange(value) {
            await this.updateConfig({
                lxmf_flood_protection_enabled: value,
            });
        },
        async onLxmfFloodThresholdChange() {
            if (this.saveTimeouts.flood_threshold) clearTimeout(this.saveTimeouts.flood_threshold);
            this.saveTimeouts.flood_threshold = setTimeout(async () => {
                let v = Number(this.config.lxmf_flood_threshold_per_minute);
                if (!v || v < 1) v = 30;
                else if (v > 1000) v = 1000;
                this.config.lxmf_flood_threshold_per_minute = v;
                await this.updateConfig({
                    lxmf_flood_threshold_per_minute: v,
                });
            }, 1000);
        },
        async onLxmfFloodMaxStampCostChange() {
            if (this.saveTimeouts.flood_max_cost) clearTimeout(this.saveTimeouts.flood_max_cost);
            this.saveTimeouts.flood_max_cost = setTimeout(async () => {
                let v = Number(this.config.lxmf_flood_max_stamp_cost);
                if (!v || v < 1) v = 24;
                else if (v > 254) v = 254;
                this.config.lxmf_flood_max_stamp_cost = v;
                await this.updateConfig({
                    lxmf_flood_max_stamp_cost: v,
                });
            }, 1000);
        },
        async onLxmfFloodCooldownChange() {
            if (this.saveTimeouts.flood_cooldown) clearTimeout(this.saveTimeouts.flood_cooldown);
            this.saveTimeouts.flood_cooldown = setTimeout(async () => {
                let v = Number(this.config.lxmf_flood_cooldown_seconds);
                if (!v || v < 30) v = 30;
                else if (v > 3600) v = 3600;
                this.config.lxmf_flood_cooldown_seconds = v;
                await this.updateConfig({
                    lxmf_flood_cooldown_seconds: v,
                });
            }, 1000);
        },
        async onPageArchiverEnabledChangeWrapper(value) {
            this.config.page_archiver_enabled = value;
            await this.updateConfig(
                {
                    page_archiver_enabled: this.config.page_archiver_enabled,
                },
                "page_archiver"
            );
        },
        async onPageArchiverConfigChange() {
            if (this.saveTimeouts.page_archiver) clearTimeout(this.saveTimeouts.page_archiver);
            this.saveTimeouts.page_archiver = setTimeout(async () => {
                await this.updateConfig(
                    {
                        page_archiver_max_versions: this.config.page_archiver_max_versions,
                        archives_max_storage_gb: this.config.archives_max_storage_gb,
                    },
                    "page_archiver"
                );
            }, 1000);
        },
        async onNomadRendererMarkdownToggle(value) {
            this.config.nomad_render_markdown_enabled = value;
            await this.updateConfig(
                {
                    nomad_render_markdown_enabled: this.config.nomad_render_markdown_enabled,
                },
                null
            );
        },
        async onNomadRendererHtmlToggle(value) {
            this.config.nomad_render_html_enabled = value;
            await this.updateConfig(
                {
                    nomad_render_html_enabled: this.config.nomad_render_html_enabled,
                },
                null
            );
        },
        async onNomadRendererPlaintextToggle(value) {
            this.config.nomad_render_plaintext_enabled = value;
            await this.updateConfig(
                {
                    nomad_render_plaintext_enabled: this.config.nomad_render_plaintext_enabled,
                },
                null
            );
        },
        async onNomadMicronWasmToggle(value) {
            const prev = this.config.nomad_micron_wasm_enabled;
            this.config.nomad_micron_wasm_enabled = value;
            try {
                const newConfig = await patchServerConfig({ nomad_micron_wasm_enabled: value }, window.api);
                this.config = newConfig;
                normalizeConfigColors(this.config);
                this.syncLxmfTransferLimitInputs();
            } catch (e) {
                this.config.nomad_micron_wasm_enabled = prev;
                ToastUtils.error(this.$t("common.save_failed"));
                console.log(e);
            }
        },
        async onNomadMicronDefaultEngineSelect(ev) {
            const v = ev.target.value === "wasm" ? "wasm" : "js";
            const prev = this.config.nomad_micron_default_engine === "wasm" ? "wasm" : "js";
            if (v === prev) {
                return;
            }
            try {
                const newConfig = await patchServerConfig({ nomad_micron_default_engine: v }, window.api);
                this.config = newConfig;
                normalizeConfigColors(this.config);
                this.syncLxmfTransferLimitInputs();
            } catch (e) {
                ev.target.value = prev;
                ToastUtils.error(this.$t("common.save_failed"));
                console.log(e);
            }
        },
        onMicronWasmOverrideSaved() {},
        async onNomadDefaultPagePathChange() {
            await this.updateConfig(
                {
                    nomad_default_page_path: this.config.nomad_default_page_path,
                },
                null
            );
        },
        async onStrangerAttachmentBlockChange(value) {
            if (!this.config) return;
            this.config.block_attachments_from_strangers = value;
            await this.updateConfig({ block_attachments_from_strangers: value }, "stranger_protection");
        },
        async onBlockAllFromStrangersChange(value) {
            if (!this.config) return;
            this.config.block_all_from_strangers = value;
            await this.updateConfig({ block_all_from_strangers: value }, "stranger_protection");
        },
        async onShowUnknownContactBannerChange(value) {
            if (!this.config) return;
            this.config.show_unknown_contact_banner = value;
            await this.updateConfig({ show_unknown_contact_banner: value }, "stranger_protection");
        },
        async onWarnOnStrangerLinksChange(value) {
            if (!this.config) return;
            this.config.warn_on_stranger_links = value;
            await this.updateConfig({ warn_on_stranger_links: value }, "stranger_protection");
        },
        async onLocalMessageAutoDeleteEnabledChange(value) {
            this.config.local_message_auto_delete_enabled = value;
            await this.updateConfig({ local_message_auto_delete_enabled: value }, "privacy_data");
        },
        onLocalMessageAutoDeleteParamsChange() {
            if (this.saveTimeouts.localMessageAutoDelete) {
                clearTimeout(this.saveTimeouts.localMessageAutoDelete);
            }
            this.saveTimeouts.localMessageAutoDelete = setTimeout(async () => {
                const { value: v, unit: u } = normalizeRetentionValue(
                    this.config.local_message_auto_delete_value,
                    this.config.local_message_auto_delete_unit
                );
                this.config.local_message_auto_delete_value = v;
                this.config.local_message_auto_delete_unit = u;
                await this.updateConfig(
                    {
                        local_message_auto_delete_value: v,
                        local_message_auto_delete_unit: u,
                    },
                    "privacy_data"
                );
            }, 400);
        },
        async onBanishedEffectEnabledChange(value) {
            this.config.banished_effect_enabled = value;
            await this.updateConfig(
                {
                    banished_effect_enabled: value,
                },
                "banishment"
            );
        },
        onBanishedTextChange(value) {
            this.config.banished_text = value;
            this.onBanishedConfigChange();
        },
        onBanishedColorChange(value) {
            this.config.banished_color = value;
            this.onBanishedConfigChange();
        },
        async onBanishedConfigChange() {
            if (this.saveTimeouts.banished) clearTimeout(this.saveTimeouts.banished);
            this.saveTimeouts.banished = setTimeout(async () => {
                await this.updateConfig(
                    {
                        banished_text: this.config.banished_text,
                        banished_color: this.config.banished_color,
                    },
                    "banishment"
                );
            }, 1000);
        },
        async onCrawlerEnabledChange(value) {
            await this.updateConfig(
                {
                    crawler_enabled: value,
                },
                "smart_crawler"
            );
        },
        async onCrawlerConfigChange() {
            if (this.saveTimeouts.crawler) clearTimeout(this.saveTimeouts.crawler);
            this.saveTimeouts.crawler = setTimeout(async () => {
                await this.updateConfig(
                    {
                        crawler_max_retries: this.config.crawler_max_retries,
                        crawler_retry_delay_seconds: this.config.crawler_retry_delay_seconds,
                        crawler_max_concurrent: this.config.crawler_max_concurrent,
                        crawler_max_hops: this.config.crawler_max_hops,
                        crawler_max_rtt_ms: this.config.crawler_max_rtt_ms,
                        crawler_max_depth: this.config.crawler_max_depth,
                        crawler_max_pages_per_node: this.config.crawler_max_pages_per_node,
                        crawler_requests_per_day_per_node: this.config.crawler_requests_per_day_per_node,
                        crawler_refresh_days: this.config.crawler_refresh_days,
                    },
                    "smart_crawler"
                );
            }, 1000);
        },
        async onTelephoneEnabledChange(value) {
            this.config.telephone_enabled = value;
            try {
                const newConfig = await patchServerConfig({ telephone_enabled: value }, window.api);
                this.config = newConfig;
                ToastUtils.success(value ? this.$t("call.telephony_enabled") : this.$t("call.telephony_disabled"));
            } catch {
                ToastUtils.error(this.$t("call.failed_to_update_call_settings"));
            }
        },
        async onDesktopOpenCallsInSeparateWindowChange(value) {
            this.config.desktop_open_calls_in_separate_window = value;
            await this.updateConfig(
                {
                    desktop_open_calls_in_separate_window: value,
                },
                "desktop_open_calls_in_separate_window"
            );
        },
        async onDesktopHardwareAccelerationEnabledChange(value) {
            this.config.desktop_hardware_acceleration_enabled = value;
            await this.updateConfig(
                {
                    desktop_hardware_acceleration_enabled: value,
                },
                "desktop_hardware_acceleration_enabled"
            );
        },
        async onAuthEnabledChange(value) {
            await this.updateConfig(
                {
                    auth_enabled: value,
                },
                "authentication"
            );
            this.serverSecurity.auth_enabled = !!value;

            if (value) {
                // if enabled, redirect to setup page if password not set
                // or just to auth page in general
                this.$router.push({ name: "auth" });
            }
        },
        async onGiteaConfigChange() {
            if (this.saveTimeouts.gitea) clearTimeout(this.saveTimeouts.gitea);
            this.saveTimeouts.gitea = setTimeout(async () => {
                await this.updateConfig(
                    {
                        gitea_base_url: this.config.gitea_base_url,
                    },
                    "Infrastructure"
                );
            }, 1000);
        },
        async onCspConfigChange() {
            if (this.saveTimeouts.csp) clearTimeout(this.saveTimeouts.csp);
            this.saveTimeouts.csp = setTimeout(async () => {
                await this.updateConfig(
                    {
                        csp_extra_connect_src: this.config.csp_extra_connect_src,
                        csp_extra_img_src: this.config.csp_extra_img_src,
                        csp_extra_frame_src: this.config.csp_extra_frame_src,
                        csp_extra_script_src: this.config.csp_extra_script_src,
                        csp_extra_style_src: this.config.csp_extra_style_src,
                    },
                    "csp_settings"
                );
            }, 1000);
        },
        async onBackupConfigChange() {
            if (this.saveTimeouts.backup) clearTimeout(this.saveTimeouts.backup);
            this.saveTimeouts.backup = setTimeout(async () => {
                await this.updateConfig(
                    {
                        backup_max_count: this.config.backup_max_count,
                    },
                    "backup_max_count"
                );
            }, 1000);
        },
        async flushArchivedPages() {
            if (!(await DialogUtils.confirm(this.$t("settings.flush_archived_pages_confirm")))) {
                return;
            }
            WebSocketConnection.send(
                JSON.stringify({
                    type: "nomadnet.page.archive.flush",
                })
            );
            ToastUtils.success(this.$t("settings.archived_pages_flushed"));
        },
        async onIsTransportEnabledChangeWrapper(value) {
            this.config.is_transport_enabled = value;
            await this.onIsTransportEnabledChange();
        },
        async onIsTransportEnabledChange() {
            try {
                const response = await applyTransportMode(this.config.is_transport_enabled, window.api);
                if (response?.data?.message) {
                    ToastUtils.success(response.data.message);
                }
            } catch {
                ToastUtils.error(
                    this.config.is_transport_enabled
                        ? this.$t("settings.failed_enable_transport")
                        : this.$t("settings.failed_disable_transport")
                );
            }
        },
        async reloadRns() {
            if (this.reloadingRns) return;

            try {
                this.reloadingRns = true;
                this.reloadRnsStatusMessage = this.$t("app.reloading_rns");
                ToastUtils.loading(this.$t("app.reloading_rns"), 0, "settings-rns-reload");
                const response = await maintenanceClient.reloadReticulum(window.api);
                if (response?.data?.message) {
                    this.reloadRnsStatusMessage = response.data.message;
                }
            } catch {
                ToastUtils.error(this.$t("settings.failed_reload_reticulum"));
            } finally {
                ToastUtils.dismiss("settings-rns-reload");
                this.reloadingRns = false;
            }
        },
        async clearMessages() {
            if (!(await DialogUtils.confirm(this.$t("maintenance.clear_confirm")))) return;
            try {
                await maintenanceClient.clearMessages(window.api);
                ToastUtils.success(this.$t("maintenance.messages_cleared"));
            } catch {
                ToastUtils.error(this.$t("common.error"));
            }
        },
        async clearDuplicateMessages() {
            if (!(await DialogUtils.confirm(this.$t("maintenance.clear_duplicates_confirm")))) return;
            try {
                const { deleted } = await maintenanceClient.clearDuplicateMessages(window.api);
                ToastUtils.success(this.$t("maintenance.clear_duplicates_done", { count: deleted }));
            } catch {
                ToastUtils.error(this.$t("common.error"));
            }
        },
        messageAgeFilterParams() {
            return maintenanceClient.buildMessageAgeFilterParams({
                mode: this.messageAgePurgeMode,
                days: this.messageAgePurgeDays,
                beforeDate: this.messageAgePurgeBeforeDate,
            });
        },
        async refreshMessageAgePurgePreview() {
            const params = this.messageAgeFilterParams();
            if (!params) {
                this.messageAgePurgePreviewCount = null;
                ToastUtils.warning(this.$t("maintenance.purge_filter_invalid"));
                return;
            }
            this.messageAgePurgePreviewLoading = true;
            try {
                const { count } = await maintenanceClient.previewMessageAgePurge(window.api, params);
                this.messageAgePurgePreviewCount = count;
            } catch {
                this.messageAgePurgePreviewCount = null;
                ToastUtils.error(this.$t("common.error"));
            } finally {
                this.messageAgePurgePreviewLoading = false;
            }
        },
        async exportOldMessagesArchive() {
            const params = this.messageAgeFilterParams();
            if (!params) {
                ToastUtils.warning(this.$t("maintenance.purge_filter_invalid"));
                return;
            }
            this.messageAgePurgeBusy = true;
            try {
                const bundle = await maintenanceClient.exportMessagesBundle(window.api, params);
                const dataStr = JSON.stringify(bundle, null, 2);
                const blob = new Blob([dataStr], { type: "application/json" });
                const stamp =
                    params.before || (params.older_than_days != null ? `${params.older_than_days}d` : "filtered");
                const exportFileDefaultName = `meshchat_messages_archive_${stamp}_${new Date().toISOString().slice(0, 10)}.json`;
                await DownloadUtils.downloadFile(exportFileDefaultName, blob);
                ToastUtils.success(this.$t("maintenance.export_old_archive_done"));
            } catch {
                ToastUtils.error(this.$t("common.error"));
            } finally {
                this.messageAgePurgeBusy = false;
            }
        },
        async purgeOldMessages() {
            const params = this.messageAgeFilterParams();
            if (!params) {
                ToastUtils.warning(this.$t("maintenance.purge_filter_invalid"));
                return;
            }
            if (!(await DialogUtils.confirm(this.$t("maintenance.purge_old_confirm")))) return;
            this.messageAgePurgeBusy = true;
            try {
                const { deleted } = await maintenanceClient.purgeMessagesByAge(window.api, params);
                this.messageAgePurgePreviewCount = 0;
                ToastUtils.success(this.$t("maintenance.purge_old_done", { count: deleted }));
            } catch {
                ToastUtils.error(this.$t("common.error"));
            } finally {
                this.messageAgePurgeBusy = false;
            }
        },
        async clearAnnounces() {
            if (!(await DialogUtils.confirm(this.$t("maintenance.clear_confirm")))) return;
            try {
                await maintenanceClient.clearAnnounces(window.api);
                ToastUtils.success(this.$t("maintenance.announces_cleared"));
            } catch {
                ToastUtils.error(this.$t("common.error"));
            }
        },
        async clearNomadnetFavorites() {
            if (!(await DialogUtils.confirm(this.$t("maintenance.clear_confirm")))) return;
            try {
                await maintenanceClient.clearNomadnetFavorites(window.api);
                ToastUtils.success(this.$t("maintenance.favourites_cleared"));
            } catch {
                ToastUtils.error(this.$t("common.error"));
            }
        },
        async clearLxmfIcons() {
            if (!(await DialogUtils.confirm(this.$t("maintenance.clear_confirm")))) return;
            try {
                await maintenanceClient.clearLxmfIcons(window.api);
                ToastUtils.success(this.$t("maintenance.lxmf_icons_cleared"));
            } catch {
                ToastUtils.error(this.$t("common.error"));
            }
        },
        async clearStickers() {
            if (!(await DialogUtils.confirm(this.$t("maintenance.clear_confirm")))) return;
            try {
                await maintenanceClient.clearStickers(window.api);
                ToastUtils.success(this.$t("maintenance.stickers_cleared"));
                await this.loadStickerCount();
            } catch {
                ToastUtils.error(this.$t("common.error"));
            }
        },
        async loadStickerCount() {
            this.stickerCount = await maintenanceClient.fetchStickerCount(window.api);
        },
        async exportStickers() {
            try {
                const response = await window.api.get("/api/v1/stickers/export");
                const dataStr = JSON.stringify(response.data, null, 2);
                const exportFileDefaultName = `meshchat_stickers_${new Date().toISOString().slice(0, 10)}.json`;
                await DownloadUtils.downloadFile(
                    exportFileDefaultName,
                    new Blob([dataStr], { type: "application/json" })
                );
                ToastUtils.success(this.$t("stickers.export_done"));
            } catch {
                ToastUtils.error(this.$t("stickers.import_failed"));
            }
        },
        async importStickers(event) {
            const file = event.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = async (e) => {
                try {
                    const data = JSON.parse(e.target.result);
                    const response = await window.api.post("/api/v1/stickers/import", {
                        ...data,
                        replace_duplicates: this.stickerImportReplaceDuplicates,
                    });
                    const r = response.data;
                    ToastUtils.success(
                        this.$t("stickers.import_success", {
                            imported: r.imported ?? 0,
                            skipped_duplicates: r.skipped_duplicates ?? 0,
                            skipped_invalid: r.skipped_invalid ?? 0,
                        })
                    );
                    await this.loadStickerCount();
                } catch {
                    ToastUtils.error(this.$t("stickers.import_failed"));
                }
            };
            reader.readAsText(file);
            event.target.value = "";
        },
        async clearGifs() {
            if (!(await DialogUtils.confirm(this.$t("maintenance.clear_confirm")))) return;
            try {
                await maintenanceClient.clearGifs(window.api);
                ToastUtils.success(this.$t("maintenance.gifs_cleared"));
                await this.loadGifCount();
            } catch {
                ToastUtils.error(this.$t("common.error"));
            }
        },
        async loadGifCount() {
            this.gifCount = await maintenanceClient.fetchGifCount(window.api);
        },
        async exportGifs() {
            try {
                const response = await window.api.get("/api/v1/gifs/export");
                const dataStr = JSON.stringify(response.data, null, 2);
                const exportFileDefaultName = `meshchat_gifs_${new Date().toISOString().slice(0, 10)}.json`;
                await DownloadUtils.downloadFile(
                    exportFileDefaultName,
                    new Blob([dataStr], { type: "application/json" })
                );
                ToastUtils.success(this.$t("gifs.export_done"));
            } catch {
                ToastUtils.error(this.$t("gifs.import_failed"));
            }
        },
        async importGifs(event) {
            const file = event.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = async (e) => {
                try {
                    const data = JSON.parse(e.target.result);
                    const response = await window.api.post("/api/v1/gifs/import", {
                        ...data,
                        replace_duplicates: this.gifImportReplaceDuplicates,
                    });
                    const r = response.data;
                    ToastUtils.success(
                        this.$t("gifs.import_success", {
                            imported: r.imported ?? 0,
                            skipped_duplicates: r.skipped_duplicates ?? 0,
                            skipped_invalid: r.skipped_invalid ?? 0,
                        })
                    );
                    await this.loadGifCount();
                } catch {
                    ToastUtils.error(this.$t("gifs.import_failed"));
                }
            };
            reader.readAsText(file);
            event.target.value = "";
        },
        async clearArchives() {
            if (!(await DialogUtils.confirm(this.$t("maintenance.clear_confirm")))) return;
            try {
                await maintenanceClient.clearArchives(window.api);
                ToastUtils.success(this.$t("maintenance.archives_cleared"));
            } catch {
                ToastUtils.error(this.$t("common.error"));
            }
        },
        async clearReticulumDocs() {
            if (!(await DialogUtils.confirm(this.$t("maintenance.clear_confirm")))) return;
            try {
                await maintenanceClient.clearReticulumDocs(window.api);
                ToastUtils.success(this.$t("maintenance.docs_cleared"));
            } catch {
                ToastUtils.error(this.$t("common.error"));
            }
        },
        async clearPathTable() {
            if (!(await DialogUtils.confirm(this.$t("maintenance.clear_confirm")))) return;
            try {
                await maintenanceClient.clearPathTable(window.api);
                ToastUtils.success(this.$t("maintenance.path_table_cleared"));
            } catch {
                ToastUtils.error(this.$t("common.error"));
            }
        },
        async exportMessages() {
            try {
                const bundle = await maintenanceClient.exportMessagesBundle(window.api);
                const dataStr = JSON.stringify(bundle, null, 2);
                const blob = new Blob([dataStr], { type: "application/json" });
                const exportFileDefaultName = `meshchat_messages_${new Date().toISOString().slice(0, 10)}.json`;
                await DownloadUtils.downloadFile(exportFileDefaultName, blob);
                ToastUtils.success(this.$t("maintenance.export_messages_done"));
            } catch {
                ToastUtils.error(this.$t("common.error"));
            }
        },
        triggerImport() {
            this.$refs.importFile.click();
        },
        async importMessages(event) {
            const file = event.target.files[0];
            if (!file) return;

            try {
                const { imported } = await importMessagesFromFile(file);
                ToastUtils.success(this.$t("maintenance.import_success", { count: imported }));
            } catch {
                ToastUtils.error(this.$t("maintenance.import_failed"));
            }
            event.target.value = "";
        },
        async exportFolders() {
            try {
                const response = await window.api.get("/api/v1/lxmf/folders/export");
                const dataStr = JSON.stringify(response.data, null, 2);
                const blob = new Blob([dataStr], { type: "application/json" });
                const exportFileDefaultName = `meshchat_folders_${new Date().toISOString().slice(0, 10)}.json`;
                await DownloadUtils.downloadFile(exportFileDefaultName, blob);
                ToastUtils.success(this.$t("settings.folders_exported"));
            } catch {
                ToastUtils.error(this.$t("settings.failed_export_folders"));
            }
        },
        triggerFolderImport() {
            this.$refs.importFolderFile.click();
        },
        async importFolders(event) {
            const file = event.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = async (e) => {
                try {
                    const data = JSON.parse(e.target.result);
                    if (!data.folders || !data.mappings) throw new Error("Invalid file format");

                    await window.api.post("/api/v1/lxmf/folders/import", data);
                    ToastUtils.success(this.$t("settings.folders_imported"));
                } catch {
                    ToastUtils.error(this.$t("settings.failed_import_folders"));
                }
            };
            reader.readAsText(file);
            // Reset input
            event.target.value = "";
        },
        normalizeNomadnetFavouritesLayoutShape(layout) {
            return normalizeNomadFavouritesLayout(layout);
        },
        parseNomadnetFavouritesImportData(data) {
            if (!data || typeof data !== "object") {
                return null;
            }
            if (data.format === "meshchatx/nomadnet_favourites/v1" && data.layout && typeof data.layout === "object") {
                const layout = this.normalizeNomadnetFavouritesLayoutShape(data.layout);
                return layout ? { kind: "full", layout } : null;
            }
            if (data.format === "meshchatx/nomadnet_favourites_section/v1") {
                const sec = data.section;
                if (!sec || typeof sec.id !== "string") {
                    return null;
                }
                return { kind: "section", payload: data };
            }
            const layout = this.normalizeNomadnetFavouritesLayoutShape(data);
            return layout ? { kind: "full", layout } : null;
        },
        async mergeNomadnetFavouritesSectionImport(payload) {
            const sec = payload.section;
            const hashes = Array.isArray(payload.destination_hashes)
                ? payload.destination_hashes.filter((h) => typeof h === "string")
                : [];
            const loaded = await loadNomadFavouritesLayout(window.api);
            let base = loaded || { sections: [], sectionOrder: [], favouritesBySection: {} };
            const sections = [...base.sections];
            const sectionOrder = [...base.sectionOrder];
            const favouritesBySection = { ...base.favouritesBySection };
            const idx = sections.findIndex((s) => s.id === sec.id);
            const sectionObj = {
                id: sec.id,
                name:
                    typeof sec.name === "string" && sec.name.trim() !== "" ? sec.name : this.$t("nomadnet.favourites"),
                collapsed: sec.collapsed === true,
            };
            if (idx === -1) {
                sections.push(sectionObj);
                if (!sectionOrder.includes(sec.id)) {
                    sectionOrder.push(sec.id);
                }
            } else {
                sections[idx] = { ...sections[idx], ...sectionObj };
            }
            favouritesBySection[sec.id] = hashes;
            const merged = this.normalizeNomadnetFavouritesLayoutShape({
                sections,
                sectionOrder,
                favouritesBySection,
            });
            if (!merged) {
                throw new Error("invalid layout");
            }
            await saveNomadFavouritesLayout(window.api, merged);
        },
        async exportNomadnetFavouritesLayout() {
            let layout = { sections: [], sectionOrder: [], favouritesBySection: {} };
            try {
                const loaded = await loadNomadFavouritesLayout(window.api);
                if (loaded) {
                    layout = loaded;
                }
            } catch {
                // keep empty layout
            }
            let favourites = [];
            try {
                const response = await window.api.get("/api/v1/favourites");
                favourites = response.data.favourites || [];
            } catch {
                // continue without favourite records
            }
            const body = {
                format: "meshchatx/nomadnet_favourites/v1",
                exported_at: new Date().toISOString(),
                favourites,
                layout,
            };
            const blob = new Blob([JSON.stringify(body, null, 2)], { type: "application/json" });
            try {
                await DownloadUtils.downloadFile(
                    `meshchat_nomadnet_favourites_${new Date().toISOString().slice(0, 10)}.json`,
                    blob
                );
                ToastUtils.success(this.$t("maintenance.nomadnet_favourites_exported"));
            } catch {
                ToastUtils.error(this.$t("maintenance.nomadnet_favourites_export_failed"));
            }
        },
        triggerNomadnetFavouritesImport() {
            this.$refs.nomadnetFavouritesImportFile.click();
        },
        importNomadnetFavouritesLayoutFile(event) {
            const file = event.target.files[0];
            if (!file) {
                return;
            }
            const reader = new FileReader();
            reader.onload = async (e) => {
                try {
                    const data = JSON.parse(e.target.result);
                    const parsed = this.parseNomadnetFavouritesImportData(data);
                    if (!parsed) {
                        throw new Error("invalid file");
                    }
                    if (Array.isArray(data.favourites) && data.favourites.length > 0) {
                        await window.api.post("/api/v1/favourites/import", {
                            favourites: data.favourites,
                        });
                    }
                    if (parsed.kind === "full") {
                        await saveNomadFavouritesLayout(window.api, parsed.layout);
                    } else if (parsed.kind === "section") {
                        await this.mergeNomadnetFavouritesSectionImport(parsed.payload);
                    } else {
                        throw new Error("invalid file");
                    }
                    GlobalEmitter.emit("nomadnet-favourites-layout-imported");
                    ToastUtils.success(this.$t("maintenance.nomadnet_favourites_imported"));
                } catch {
                    ToastUtils.error(this.$t("maintenance.nomadnet_favourites_import_failed"));
                }
            };
            reader.readAsText(file);
            event.target.value = "";
        },
        formatSecondsAgo: function (seconds) {
            return Utils.formatSecondsAgo(seconds);
        },
        formatSecondsAgoForI18n: function (seconds) {
            return Utils.formatSecondsAgoForI18n(seconds);
        },
    },
};
</script>

<style scoped>
@reference "../../style.css";
/*
 * Shared settings chrome is used by extracted section components.
 * :deep is required so scoped styles still reach their markup.
 */
:deep(.settings-section) {
    @apply w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-6 sm:py-8 flex flex-col break-inside-avoid;
}
:deep(.settings-section--hero) {
    @apply border-b border-gray-200/60 dark:border-zinc-800/60 py-6 sm:py-8;
}
:deep(.settings-section__header) {
    @apply flex items-center justify-between gap-3 pb-4 border-b border-gray-100/60 dark:border-zinc-800/60;
}
:deep(.settings-section__header h2) {
    @apply text-lg font-semibold text-sem-fg;
}
:deep(.settings-section__header p) {
    @apply text-sm text-gray-600 dark:text-gray-400;
}
:deep(.settings-section__eyebrow) {
    @apply text-xs uppercase tracking-wide text-sem-fg-muted;
}
:deep(.settings-section__body) {
    @apply pt-4 text-gray-900 dark:text-gray-100;
}
:deep(.input-field) {
    @apply bg-gray-50/90 dark:bg-zinc-800/80 border border-sem-border text-sm rounded-2xl focus:ring-2 focus:ring-blue-400 focus:border-blue-400 dark:focus:ring-blue-500 dark:focus:border-blue-500 block w-full p-2.5 text-gray-900 dark:text-gray-100 transition;
}
:deep(.btn-maintenance) {
    @apply w-full px-4 py-3 rounded-2xl border transition flex items-center justify-between;
}
:deep(.setting-toggle) {
    @apply relative flex flex-row-reverse items-start gap-3 rounded-2xl border border-sem-border bg-white/70 dark:bg-zinc-900/70 px-3 py-3;
}
:deep(.setting-toggle > label) {
    @apply shrink-0 self-center;
}
:deep(.setting-toggle .sr-only) {
    @apply absolute w-px h-px p-0 -m-px overflow-hidden whitespace-nowrap border-0;
}
:deep(.setting-toggle__label) {
    @apply flex-1 min-w-0 flex flex-col gap-0.5;
}
:deep(.setting-toggle__title) {
    @apply text-sm font-semibold text-sem-fg wrap-break-word leading-snug;
}
:deep(.setting-toggle__description) {
    @apply text-xs sm:text-sm text-sem-fg-muted wrap-break-word leading-snug;
}
:deep(.setting-toggle__hint) {
    @apply text-xs text-sem-fg-muted wrap-break-word;
}
:deep(.info-callout) {
    @apply rounded-2xl border border-blue-100 dark:border-blue-900/40 bg-blue-50/60 dark:bg-blue-900/20 px-3 py-3 text-blue-900 dark:text-blue-100;
}
:deep(.monospace-field) {
    font-family: "Roboto Mono", monospace;
}
:deep(.address-card) {
    @apply relative border border-gray-200/70 dark:border-zinc-800/80 py-3 px-3 sm:rounded-xl sm:bg-black/2 dark:sm:bg-white/2 space-y-2;
}
:deep(.address-card__label) {
    @apply text-xs uppercase tracking-wide text-sem-fg-muted;
}
:deep(.address-card__value) {
    @apply text-sm text-sem-fg wrap-break-word pr-16;
}
:deep(.address-card__action) {
    @apply absolute top-3 right-3 inline-flex items-center gap-1 rounded-full border border-sem-border px-3 py-1 text-xs font-semibold text-gray-700 dark:text-gray-100 bg-white/70 dark:bg-zinc-900/60 hover:border-blue-400 dark:hover:border-blue-500 transition;
}
.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}
.settings-panel {
    @apply flex flex-col gap-4 lg:flex-row lg:items-start lg:gap-8;
}
.settings-panel__content {
    @apply flex-1 min-w-0 flex flex-col;
}
.settings-panel__content :deep(.settings-section) {
    @apply border-b border-gray-200/60 dark:border-zinc-800/60 py-6 sm:py-8 first:pt-0;
}
.settings-panel__content :deep(.settings-section:last-child) {
    @apply border-b-0;
}
</style>
