<template>
    <div
        v-if="config"
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-gradient-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div class="flex-1 overflow-y-auto w-full px-4 md:px-8 py-6">
            <div class="space-y-4 w-full max-w-6xl mx-auto">
                <!-- hero card -->
                <div
                    class="bg-white/90 dark:bg-zinc-900/80 backdrop-blur border border-gray-200 dark:border-zinc-800 rounded-3xl shadow-xl p-5 md:p-6"
                >
                    <div class="flex flex-col md:flex-row md:items-center gap-4">
                        <div class="flex-1 space-y-1">
                            <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                                {{ $t("app.profile") }}
                            </div>
                            <div class="flex flex-col sm:flex-row sm:items-center gap-2">
                                <div class="flex-1 min-w-0">
                                    <input
                                        v-model="config.display_name"
                                        type="text"
                                        :placeholder="$t('app.display_name_placeholder')"
                                        class="w-full rounded-xl border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 px-3 py-2 text-base font-semibold text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500/60 focus:border-blue-500 outline-none transition"
                                        @input="onDisplayNameChange"
                                    />
                                </div>
                                <div class="text-sm text-gray-600 dark:text-gray-300 whitespace-nowrap">
                                    {{ $t("app.manage_identity") }}
                                </div>
                            </div>
                        </div>
                    </div>
                    <transition name="fade">
                        <div
                            v-if="copyToast"
                            class="mt-3 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200 px-3 py-1 text-xs inline-flex items-center gap-2"
                        >
                            {{ copyToast }}
                            <span class="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
                        </div>
                    </transition>
                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-4 text-sm text-gray-600 dark:text-gray-300">
                        <div
                            class="rounded-2xl border border-gray-200 dark:border-zinc-800 p-3 bg-white/70 dark:bg-zinc-900/70"
                        >
                            <div class="text-xs uppercase tracking-wide">{{ $t("app.theme") }}</div>
                            <div class="font-semibold text-gray-900 dark:text-white capitalize">
                                {{ $t("app.theme_mode", { mode: config.theme }) }}
                            </div>
                        </div>
                        <div
                            class="rounded-2xl border border-gray-200 dark:border-zinc-800 p-3 bg-white/70 dark:bg-zinc-900/70"
                        >
                            <div class="text-xs uppercase tracking-wide">{{ $t("app.transport") }}</div>
                            <div class="font-semibold text-gray-900 dark:text-white">
                                {{ config.is_transport_enabled ? $t("app.enabled") : $t("app.disabled") }}
                            </div>
                        </div>
                        <div
                            class="rounded-2xl border border-gray-200 dark:border-zinc-800 p-3 bg-white/70 dark:bg-zinc-900/70"
                        >
                            <div class="text-xs uppercase tracking-wide">{{ $t("app.propagation") }}</div>
                            <div class="font-semibold text-gray-900 dark:text-white">
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
                <div class="sticky top-0 z-10 py-4">
                    <div class="relative max-w-6xl mx-auto">
                        <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                            <MaterialDesignIcon icon-name="magnify" class="size-5 text-gray-400" />
                        </div>
                        <input
                            v-model="searchQuery"
                            type="text"
                            class="w-full bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 rounded-2xl py-3 pl-12 pr-4 text-sm focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none transition-all shadow-sm"
                            :placeholder="$t('app.search_settings') || 'Search settings...'"
                        />
                        <button
                            v-if="searchQuery"
                            class="absolute inset-y-0 right-0 pr-4 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                            @click="searchQuery = ''"
                        >
                            <MaterialDesignIcon icon-name="close-circle" class="size-5" />
                        </button>
                    </div>
                </div>

                <!-- no results -->
                <div
                    v-if="searchQuery && !hasSearchResults"
                    class="flex flex-col items-center justify-center py-12 text-center"
                >
                    <div
                        class="p-4 bg-white/50 dark:bg-zinc-800/50 rounded-full mb-4 border border-gray-100 dark:border-zinc-800"
                    >
                        <MaterialDesignIcon icon-name="magnify-close" class="size-8 text-gray-400" />
                    </div>
                    <h3 class="text-lg font-semibold text-gray-900 dark:text-white">No results found</h3>
                    <p class="text-gray-500 dark:text-gray-400">No settings match "{{ searchQuery }}"</p>
                    <button
                        class="mt-4 px-4 py-2 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition font-semibold text-sm"
                        @click="searchQuery = ''"
                    >
                        Clear search
                    </button>
                </div>

                <!-- settings grid -->
                <div v-show="hasSearchResults" class="columns-1 lg:columns-2 gap-4 space-y-4">
                    <!-- Banishment -->
                    <section
                        v-show="matchesSearch('stranger', 'attachments', 'trust', 'block')"
                        class="glass-card break-inside-avoid"
                    >
                        <header class="glass-card__header">
                            <div>
                                <div class="glass-card__eyebrow">Security</div>
                                <h2>{{ $t("app.stranger_protection") }}</h2>
                                <p>{{ $t("app.stranger_protection_description") }}</p>
                            </div>
                        </header>
                        <div class="glass-card__body space-y-4">
                            <label class="setting-toggle">
                                <Toggle
                                    id="block-attachments-from-strangers"
                                    v-model="config.block_attachments_from_strangers"
                                    @update:model-value="onStrangerAttachmentBlockChange"
                                />
                                <span class="setting-toggle__label">
                                    <span class="setting-toggle__title">{{
                                        $t("app.block_stranger_attachments")
                                    }}</span>
                                    <span class="setting-toggle__description">{{
                                        $t("app.block_stranger_attachments_description")
                                    }}</span>
                                </span>
                            </label>
                            <label class="setting-toggle">
                                <Toggle
                                    id="block-all-from-strangers"
                                    v-model="config.block_all_from_strangers"
                                    @update:model-value="onBlockAllFromStrangersChange"
                                />
                                <span class="setting-toggle__label">
                                    <span class="setting-toggle__title">{{ $t("app.block_all_from_strangers") }}</span>
                                    <span class="setting-toggle__description">{{
                                        $t("app.block_all_from_strangers_description")
                                    }}</span>
                                </span>
                            </label>
                        </div>
                    </section>

                    <section
                        v-show="matchesSearch(...sectionKeywords.banishment)"
                        class="glass-card break-inside-avoid"
                    >
                        <header class="glass-card__header">
                            <div>
                                <div class="glass-card__eyebrow">Visuals</div>
                                <h2>{{ $t("app.banishment") }}</h2>
                                <p>{{ $t("app.banishment_description") }}</p>
                            </div>
                        </header>
                        <div class="glass-card__body space-y-4">
                            <label class="setting-toggle">
                                <Toggle
                                    id="banished-effect-enabled"
                                    v-model="config.banished_effect_enabled"
                                    @update:model-value="onBanishedEffectEnabledChange"
                                />
                                <span class="setting-toggle__label">
                                    <span class="setting-toggle__title">{{ $t("app.banished_effect_enabled") }}</span>
                                    <span class="setting-toggle__description">{{
                                        $t("app.banished_effect_description")
                                    }}</span>
                                </span>
                            </label>

                            <div v-if="config.banished_effect_enabled" class="space-y-4">
                                <div class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        {{ $t("app.banished_text_label") }}
                                    </div>
                                    <input
                                        v-model="config.banished_text"
                                        type="text"
                                        class="input-field"
                                        @input="onBanishedConfigChange"
                                    />
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        {{ $t("app.banished_text_description") }}
                                    </div>
                                </div>

                                <div class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        {{ $t("app.banished_color_label") }}
                                    </div>
                                    <div class="flex gap-2">
                                        <input
                                            v-model="config.banished_color"
                                            type="color"
                                            class="w-12 h-10 rounded-xl border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 cursor-pointer"
                                            @input="onBanishedConfigChange"
                                        />
                                        <input
                                            v-model="config.banished_color"
                                            type="text"
                                            class="input-field monospace-field"
                                            @input="onBanishedConfigChange"
                                        />
                                    </div>
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        {{ $t("app.banished_color_description") }}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </section>

                    <!-- Maintenance & Data -->
                    <section
                        v-show="matchesSearch(...sectionKeywords.maintenance)"
                        class="glass-card break-inside-avoid"
                    >
                        <header class="glass-card__header">
                            <div>
                                <div class="glass-card__eyebrow">Maintenance</div>
                                <h2>{{ $t("maintenance.title") }}</h2>
                                <p>{{ $t("maintenance.description") }}</p>
                            </div>
                        </header>
                        <div class="glass-card__body space-y-4">
                            <div class="grid grid-cols-1 gap-3">
                                <button
                                    type="button"
                                    class="btn-maintenance border-red-200 dark:border-red-900/30 text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-900/10 hover:bg-red-100 dark:hover:bg-red-900/20"
                                    @click="clearMessages"
                                >
                                    <div class="flex flex-col items-start text-left">
                                        <div class="font-bold flex items-center gap-2">
                                            <MaterialDesignIcon icon-name="message-remove" class="size-4" />
                                            {{ $t("maintenance.clear_messages") }}
                                        </div>
                                        <div class="text-xs opacity-80">
                                            {{ $t("maintenance.clear_messages_desc") }}
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
                            </div>

                            <div class="space-y-2 pt-2 border-t border-gray-100 dark:border-zinc-800">
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
                                </button>
                                <input
                                    ref="importFile"
                                    type="file"
                                    accept=".json"
                                    class="hidden"
                                    @change="importMessages"
                                />
                            </div>

                            <div class="grid grid-cols-2 gap-3 mt-2 pt-4 border-t border-gray-100 dark:border-zinc-800">
                                <button
                                    type="button"
                                    class="flex flex-col items-center justify-center gap-2 p-4 rounded-2xl border border-purple-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-800/50 hover:border-purple-500 transition group"
                                    @click="exportFolders"
                                >
                                    <MaterialDesignIcon
                                        icon-name="folder-export-outline"
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
                                        icon-name="folder-import-outline"
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
                        </div>
                    </section>

                    <!-- Desktop / Electron Settings -->
                    <section
                        v-if="ElectronUtils.isElectron()"
                        v-show="matchesSearch(...sectionKeywords.desktop)"
                        class="glass-card break-inside-avoid"
                    >
                        <header class="glass-card__header">
                            <div>
                                <div class="glass-card__eyebrow">Desktop</div>
                                <h2>App Behaviour</h2>
                                <p>Control how MeshChat behaves on your desktop.</p>
                            </div>
                        </header>
                        <div class="glass-card__body space-y-4">
                            <label class="setting-toggle opacity-50 cursor-not-allowed">
                                <Toggle
                                    id="desktop-open-calls-in-separate-window"
                                    :model-value="false"
                                    :disabled="true"
                                />
                                <span class="setting-toggle__label">
                                    <span class="setting-toggle__title">{{
                                        $t("app.desktop_open_calls_in_separate_window")
                                    }}</span>
                                    <span class="setting-toggle__description">
                                        {{ $t("app.desktop_open_calls_in_separate_window_description") }}
                                        <span class="text-blue-500 font-bold block mt-1">(Phased out for now)</span>
                                    </span>
                                </span>
                            </label>

                            <label class="setting-toggle">
                                <Toggle
                                    id="desktop-hardware-acceleration-enabled"
                                    v-model="config.desktop_hardware_acceleration_enabled"
                                    @update:model-value="onDesktopHardwareAccelerationEnabledChange"
                                />
                                <span class="setting-toggle__label">
                                    <span class="setting-toggle__title">{{
                                        $t("app.desktop_hardware_acceleration_enabled")
                                    }}</span>
                                    <span class="setting-toggle__description">{{
                                        $t("app.desktop_hardware_acceleration_enabled_description")
                                    }}</span>
                                    <span class="setting-toggle__hint">{{ $t("app.requires_restart") }}</span>
                                </span>
                            </label>
                        </div>
                    </section>

                    <!-- Page Archiver -->
                    <section v-show="matchesSearch(...sectionKeywords.archiver)" class="glass-card break-inside-avoid">
                        <header class="glass-card__header">
                            <div>
                                <div class="glass-card__eyebrow">Browsing</div>
                                <h2>Page Archiver</h2>
                                <p>Automatically save copies of visited NomadNetwork pages.</p>
                            </div>
                        </header>
                        <div class="glass-card__body space-y-3">
                            <label class="setting-toggle">
                                <Toggle
                                    id="page-archiver-enabled"
                                    v-model="config.page_archiver_enabled"
                                    @update:model-value="onPageArchiverEnabledChangeWrapper"
                                />
                                <span class="setting-toggle__label">
                                    <span class="setting-toggle__title">Enable Archiver</span>
                                    <span class="setting-toggle__description"
                                        >Automatically archive pages for offline viewing and fallback.</span
                                    >
                                </span>
                            </label>
                            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        Max Versions per Page
                                    </div>
                                    <input
                                        v-model.number="config.page_archiver_max_versions"
                                        type="number"
                                        min="1"
                                        max="50"
                                        class="input-field"
                                        @input="onPageArchiverConfigChange"
                                    />
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        How many versions of each page to keep.
                                    </div>
                                </div>
                                <div class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        Max Total Storage (GB)
                                    </div>
                                    <input
                                        v-model.number="config.archives_max_storage_gb"
                                        type="number"
                                        min="1"
                                        class="input-field"
                                        @input="onPageArchiverConfigChange"
                                    />
                                    <div class="text-xs text-gray-600 dark:text-gray-400">
                                        Total storage for all archived pages.
                                    </div>
                                </div>
                            </div>
                            <button
                                type="button"
                                class="w-full flex items-center justify-center gap-2 rounded-xl border border-red-200 dark:border-red-900/30 bg-red-50 dark:bg-red-900/20 px-4 py-2 text-sm font-semibold text-red-700 dark:text-red-300 hover:bg-red-100 dark:hover:bg-red-900/40 transition"
                                @click="flushArchivedPages"
                            >
                                <MaterialDesignIcon icon-name="delete-sweep" class="w-4 h-4" />
                                Flush All Archived Pages
                            </button>
                        </div>
                    </section>

                    <!-- Smart Crawler -->
                    <section v-show="matchesSearch(...sectionKeywords.crawler)" class="glass-card break-inside-avoid">
                        <header class="glass-card__header">
                            <div>
                                <div class="glass-card__eyebrow">Discovery</div>
                                <h2>Smart Crawler</h2>
                                <p>Automatically archive node homepages when announced.</p>
                            </div>
                        </header>
                        <div class="glass-card__body space-y-4">
                            <label class="setting-toggle">
                                <Toggle
                                    id="crawler-enabled"
                                    v-model="config.crawler_enabled"
                                    @update:model-value="onCrawlerEnabledChange"
                                />
                                <span class="setting-toggle__label">
                                    <span class="setting-toggle__title">Enable Crawler</span>
                                    <span class="setting-toggle__description"
                                        >Archive index pages for every node discovered on the mesh.</span
                                    >
                                </span>
                            </label>

                            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">Max Retries</div>
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
                                    max="5"
                                    class="input-field"
                                    @input="onCrawlerConfigChange"
                                />
                                <div class="text-xs text-gray-600 dark:text-gray-400">
                                    Limits background bandwidth usage.
                                </div>
                            </div>
                        </div>
                    </section>

                    <!-- Appearance -->
                    <section
                        v-show="matchesSearch(...sectionKeywords.appearance)"
                        class="glass-card break-inside-avoid"
                    >
                        <header class="glass-card__header">
                            <div>
                                <div class="glass-card__eyebrow">Personalise</div>
                                <h2>{{ $t("app.appearance") }}</h2>
                                <p>{{ $t("app.appearance_description") }}</p>
                            </div>
                        </header>
                        <div class="glass-card__body space-y-4">
                            <div class="space-y-2">
                                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                    {{ $t("app.theme") }}
                                </div>
                                <select v-model="config.theme" class="input-field" @change="onThemeChange">
                                    <option value="light">{{ $t("app.light_theme") }}</option>
                                    <option value="dark">{{ $t("app.dark_theme") }}</option>
                                </select>
                            </div>

                            <div class="space-y-2">
                                <div class="flex items-center justify-between">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        Message Font Size
                                    </div>
                                    <div class="text-xs font-mono text-blue-500 dark:text-blue-400">
                                        {{ config.message_font_size || 14 }}px
                                    </div>
                                </div>
                                <div class="flex items-center gap-3">
                                    <span class="text-xs text-gray-400">A</span>
                                    <input
                                        v-model.number="config.message_font_size"
                                        type="range"
                                        min="10"
                                        max="32"
                                        step="1"
                                        class="flex-1 h-1.5 bg-gray-200 dark:bg-zinc-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                                        @input="onMessageFontSizeChange"
                                    />
                                    <span class="text-lg text-gray-400">A</span>
                                </div>
                            </div>

                            <div class="space-y-2">
                                <div class="flex items-center justify-between">
                                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">Icon Size</div>
                                    <div class="text-xs font-mono text-blue-500 dark:text-blue-400">
                                        {{ config.message_icon_size || 28 }}px
                                    </div>
                                </div>
                                <div class="flex items-center gap-3">
                                    <MaterialDesignIcon icon-name="account-outline" class="text-gray-400" />
                                    <input
                                        v-model.number="config.message_icon_size"
                                        type="range"
                                        min="16"
                                        max="64"
                                        step="1"
                                        class="flex-1 h-1.5 bg-gray-200 dark:bg-zinc-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                                        @input="onMessageIconSizeChange"
                                    />
                                    <MaterialDesignIcon icon-name="account" class="text-gray-500 dark:text-gray-300" />
                                </div>
                            </div>

                            <div
                                class="flex items-center gap-3 text-sm text-gray-600 dark:text-gray-300 border border-dashed border-gray-200 dark:border-zinc-800 rounded-2xl px-3 py-2"
                            >
                                <div
                                    :style="messageIconPreviewStyle"
                                    class="flex items-center justify-center shrink-0 rounded-full bg-gray-100 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700"
                                >
                                    <LxmfUserIcon
                                        :key="config.message_icon_size"
                                        icon-name="account"
                                        icon-class="w-full h-full"
                                        icon-foreground-colour="#374151"
                                        icon-background-colour="#e5e7eb"
                                    />
                                </div>
                                <div class="flex-1 min-w-0 space-y-0.5">
                                    <div
                                        class="font-semibold text-gray-900 dark:text-gray-100"
                                        :style="previewTextStyle"
                                    >
                                        Preview Name
                                    </div>
                                    <div class="text-gray-600 dark:text-gray-400 truncate" :style="previewTextStyle">
                                        Hey there, this is how text and icons will look.
                                    </div>
                                </div>
                                <span
                                    class="inline-flex items-center gap-1 text-blue-500 dark:text-blue-300 text-xs font-semibold uppercase"
                                >
                                    <span class="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                                    {{ $t("app.live_preview") }}
                                </span>
                            </div>

                            <div class="space-y-4 pt-2">
                                <div
                                    class="text-sm font-bold text-gray-400 dark:text-zinc-500 uppercase tracking-wider"
                                >
                                    Message Bubbles
                                </div>

                                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                    <div class="space-y-2">
                                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                            Outbound Color
                                        </div>
                                        <div class="flex gap-2">
                                            <input
                                                v-model="config.message_outbound_bubble_color"
                                                type="color"
                                                class="w-12 h-10 rounded-xl border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 cursor-pointer"
                                                @input="onMessageBubbleColorChange('outbound')"
                                            />
                                            <input
                                                v-model="config.message_outbound_bubble_color"
                                                type="text"
                                                class="input-field monospace-field flex-1"
                                                @input="onMessageBubbleColorChange('outbound')"
                                            />
                                        </div>
                                    </div>

                                    <div class="space-y-2">
                                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                            Failed Color
                                        </div>
                                        <div class="flex gap-2">
                                            <input
                                                v-model="config.message_failed_bubble_color"
                                                type="color"
                                                class="w-12 h-10 rounded-xl border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 cursor-pointer"
                                                @input="onMessageBubbleColorChange('failed')"
                                            />
                                            <input
                                                v-model="config.message_failed_bubble_color"
                                                type="text"
                                                class="input-field monospace-field flex-1"
                                                @input="onMessageBubbleColorChange('failed')"
                                            />
                                        </div>
                                    </div>
                                </div>

                                <div class="space-y-2">
                                    <div class="flex items-center justify-between">
                                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                            Inbound Color (Optional)
                                        </div>
                                        <button
                                            v-if="config.message_inbound_bubble_color"
                                            type="button"
                                            class="text-[10px] text-red-500 font-bold uppercase hover:underline"
                                            @click="
                                                config.message_inbound_bubble_color = null;
                                                onMessageBubbleColorChange('inbound');
                                            "
                                        >
                                            Reset to default
                                        </button>
                                    </div>
                                    <div class="flex gap-2">
                                        <input
                                            v-model="config.message_inbound_bubble_color"
                                            type="color"
                                            class="w-12 h-10 rounded-xl border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 cursor-pointer"
                                            :disabled="!config.message_inbound_bubble_color"
                                            @input="onMessageBubbleColorChange('inbound')"
                                        />
                                        <div
                                            v-if="!config.message_inbound_bubble_color"
                                            class="flex-1 flex items-center px-3 text-xs text-gray-400 bg-gray-50 dark:bg-zinc-900 rounded-xl border border-dashed border-gray-200 dark:border-zinc-800 italic"
                                        >
                                            Using theme default. Click to customize ->
                                            <button
                                                class="ml-2 px-2 py-1 bg-blue-500 text-white rounded-lg not-italic font-bold"
                                                @click="
                                                    config.message_inbound_bubble_color = '#ffffff';
                                                    onMessageBubbleColorChange('inbound');
                                                "
                                            >
                                                Customize
                                            </button>
                                        </div>
                                        <input
                                            v-else
                                            v-model="config.message_inbound_bubble_color"
                                            type="text"
                                            class="input-field monospace-field flex-1"
                                            @input="onMessageBubbleColorChange('inbound')"
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                    </section>

                    <!-- Location -->
                    <section v-show="matchesSearch(...sectionKeywords.location)" class="glass-card break-inside-avoid">
                        <header class="glass-card__header">
                            <div>
                                <div class="glass-card__eyebrow">Privacy</div>
                                <h2>Location</h2>
                                <p>Manage how your location is shared.</p>
                            </div>
                        </header>
                        <div class="glass-card__body space-y-4">
                            <div class="space-y-2">
                                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">Location Source</div>
                                <select
                                    v-model="config.location_source"
                                    class="input-field"
                                    @change="
                                        updateConfig({ location_source: config.location_source }, 'location_source')
                                    "
                                >
                                    <option value="browser">Automatic (Browser)</option>
                                    <option value="manual">Manual</option>
                                </select>
                                <div
                                    v-if="config.location_source === 'browser'"
                                    class="text-xs text-gray-600 dark:text-gray-400"
                                >
                                    Uses your browser's geolocation API. Note: In the desktop app, this can use Google
                                    services, which is blocked by CORS so you would need to specifically allow it.
                                </div>
                                <div
                                    v-if="config.location_source === 'manual'"
                                    class="text-xs text-gray-600 dark:text-gray-400"
                                >
                                    Use manually entered coordinates for maximum privacy.
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

                            <div class="pt-4 border-t border-gray-100 dark:border-zinc-800 space-y-4">
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
                            </div>

                            <div
                                v-if="config.telemetry_enabled"
                                class="pt-4 border-t border-gray-100 dark:border-zinc-800 space-y-4"
                            >
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
                                                class="size-8 rounded-full bg-blue-50 dark:bg-blue-900/20 text-blue-500 flex items-center justify-center"
                                            >
                                                <MaterialDesignIcon icon-name="account" class="size-5" />
                                            </div>
                                            <div class="min-w-0">
                                                <div class="text-sm font-bold text-gray-900 dark:text-white truncate">
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
                    </section>

                    <!-- Language -->
                    <section
                        v-show="
                            matchesSearch(
                                'i18n',
                                'app.language',
                                'app.select_language',
                                'English',
                                'Deutsch',
                                'Русский'
                            )
                        "
                        class="glass-card break-inside-avoid"
                    >
                        <header class="glass-card__header">
                            <div>
                                <div class="glass-card__eyebrow">i18n</div>
                                <h2>{{ $t("app.language") }}</h2>
                                <p>{{ $t("app.select_language") }}</p>
                            </div>
                        </header>
                        <div class="glass-card__body space-y-3">
                            <select v-model="config.language" class="input-field" @change="onLanguageChange">
                                <option value="en">English</option>
                                <option value="de">Deutsch</option>
                                <option value="ru">Русский</option>
                                <option value="it">Italiano</option>
                            </select>
                        </div>
                    </section>

                    <!-- Network Security -->
                    <section
                        v-show="
                            matchesSearch(
                                'RNS Security',
                                'Network Security',
                                'app.blackhole_integration_enabled',
                                'app.blackhole_integration_description',
                                'app.announce_limits'
                            )
                        "
                        class="glass-card break-inside-avoid"
                    >
                        <header class="glass-card__header">
                            <div>
                                <div class="glass-card__eyebrow">RNS Security</div>
                                <h2>Network Security</h2>
                                <p>Manage mesh-level security features.</p>
                            </div>
                        </header>
                        <div class="glass-card__body space-y-4">
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
                                <div class="text-xs font-semibold text-gray-700 dark:text-zinc-300 uppercase tracking-wide">
                                    {{ $t("app.announce_max_stored_heading") }}
                                </div>
                                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                    <div class="space-y-1">
                                        <label class="text-xs font-medium">{{ $t("app.announce_limit_lxmf") }}</label>
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
                                        <label class="text-xs font-medium">{{ $t("app.announce_limit_prop") }}</label>
                                        <input
                                            v-model.number="config.announce_max_stored_lxmf_propagation"
                                            type="number"
                                            min="1"
                                            class="input-field"
                                            @change="onAnnounceLimitsChange"
                                        />
                                    </div>
                                </div>
                                <div class="text-xs font-semibold text-gray-700 dark:text-zinc-300 uppercase tracking-wide">
                                    {{ $t("app.announce_fetch_limit_heading") }}
                                </div>
                                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                    <div class="space-y-1">
                                        <label class="text-xs font-medium">{{ $t("app.announce_limit_lxmf") }}</label>
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
                                        <label class="text-xs font-medium">{{ $t("app.announce_limit_prop") }}</label>
                                        <input
                                            v-model.number="config.announce_fetch_limit_lxmf_propagation"
                                            type="number"
                                            min="1"
                                            class="input-field"
                                            @change="onAnnounceLimitsChange"
                                        />
                                    </div>
                                </div>
                                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div class="space-y-1">
                                        <label class="text-xs font-medium">{{ $t("app.announce_search_max_fetch") }}</label>
                                        <input
                                            v-model.number="config.announce_search_max_fetch"
                                            type="number"
                                            min="100"
                                            class="input-field"
                                            @change="onAnnounceLimitsChange"
                                        />
                                        <p class="text-[10px] text-gray-500 dark:text-zinc-500">
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
                                        <p class="text-[10px] text-gray-500 dark:text-zinc-500">
                                            {{ $t("app.discovered_interfaces_max_return_hint") }}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </section>

                    <!-- Transport -->
                    <section v-show="matchesSearch(...sectionKeywords.transport)" class="glass-card break-inside-avoid">
                        <header class="glass-card__header">
                            <div>
                                <div class="glass-card__eyebrow">Reticulum</div>
                                <h2>{{ $t("app.transport_mode") }}</h2>
                                <p>{{ $t("app.transport_description") }}</p>
                            </div>
                        </header>
                        <div class="glass-card__body space-y-3">
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
                                    <span class="setting-toggle__hint">{{ $t("app.requires_restart") }}</span>
                                </span>
                            </label>
                        </div>
                    </section>

                    <!-- Interfaces -->
                    <section
                        v-show="matchesSearch(...sectionKeywords.interfaces)"
                        class="glass-card break-inside-avoid"
                    >
                        <header class="glass-card__header">
                            <div>
                                <div class="glass-card__eyebrow">Adapters</div>
                                <h2>{{ $t("app.interfaces") }}</h2>
                                <p>Show curated community configs inside the interface wizard.</p>
                            </div>
                        </header>
                        <div class="glass-card__body space-y-3">
                            <label class="setting-toggle">
                                <Toggle
                                    id="show-community-interfaces"
                                    v-model="config.show_suggested_community_interfaces"
                                    @update:model-value="onShowSuggestedCommunityInterfacesChangeWrapper"
                                />
                                <span class="setting-toggle__label">
                                    <span class="setting-toggle__title">{{ $t("app.show_community_interfaces") }}</span>
                                    <span class="setting-toggle__description">{{
                                        $t("app.community_interfaces_description")
                                    }}</span>
                                </span>
                            </label>
                        </div>
                    </section>

                    <!-- Blocked -->
                    <section
                        v-show="matchesSearch('Privacy', 'Banished', 'Manage Banished users and nodes')"
                        class="glass-card break-inside-avoid"
                    >
                        <header class="glass-card__header">
                            <div>
                                <div class="glass-card__eyebrow">Privacy</div>
                                <h2>Banished</h2>
                                <p>Manage Banished users and nodes</p>
                            </div>
                            <RouterLink :to="{ name: 'blocked' }" class="primary-chip"> Manage Banished </RouterLink>
                        </header>
                        <div class="glass-card__body">
                            <p class="text-sm text-gray-600 dark:text-gray-400">
                                Banished users and nodes will not be able to send you messages, and their announces will
                                be ignored.
                            </p>
                        </div>
                    </section>

                    <!-- Authentication -->
                    <section v-show="matchesSearch(...sectionKeywords.auth)" class="glass-card break-inside-avoid">
                        <header class="glass-card__header">
                            <div>
                                <div class="glass-card__eyebrow">Security</div>
                                <h2>Authentication</h2>
                                <p>Require a password to access the web interface.</p>
                            </div>
                        </header>
                        <div class="glass-card__body space-y-3">
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

                    <!-- Translator -->
                    <section
                        v-show="matchesSearch(...sectionKeywords.translator)"
                        class="glass-card break-inside-avoid"
                    >
                        <header class="glass-card__header">
                            <div>
                                <div class="glass-card__eyebrow">i18n</div>
                                <h2>{{ $t("app.translator") }}</h2>
                                <p>{{ $t("translator.description") }}</p>
                            </div>
                        </header>
                        <div class="glass-card__body space-y-4">
                            <label class="setting-toggle">
                                <Toggle
                                    id="translator-enabled"
                                    v-model="config.translator_enabled"
                                    @update:model-value="onTranslatorEnabledChange"
                                />
                                <span class="setting-toggle__label">
                                    <span class="setting-toggle__title">{{ $t("app.translator_enabled") }}</span>
                                    <span class="setting-toggle__description">{{
                                        $t("app.translator_description")
                                    }}</span>
                                </span>
                            </label>

                            <div v-if="config.translator_enabled" class="space-y-2">
                                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                    {{ $t("app.libretranslate_url") }}
                                </div>
                                <input
                                    v-model="config.libretranslate_url"
                                    type="text"
                                    placeholder="http://localhost:5000"
                                    class="input-field"
                                    @input="onTranslatorConfigChange"
                                />
                                <div class="text-xs text-gray-600 dark:text-gray-400">
                                    {{ $t("app.libretranslate_url_description") }}
                                </div>
                            </div>
                        </div>
                    </section>

                    <!-- Sources & Infrastructure -->
                    <section
                        v-show="matchesSearch(...sectionKeywords.infrastructure)"
                        class="glass-card break-inside-avoid"
                    >
                        <header class="glass-card__header">
                            <div>
                                <div class="glass-card__eyebrow">Infrastructure</div>
                                <h2>Sources & Mirroring</h2>
                                <p>Customize URLs for documentation and external resources.</p>
                            </div>
                        </header>
                        <div class="glass-card__body space-y-4">
                            <div class="space-y-2">
                                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">Gitea Base URL</div>
                                <input
                                    v-model="config.gitea_base_url"
                                    type="text"
                                    placeholder="https://git.quad4.io"
                                    class="input-field"
                                    @input="onGiteaConfigChange"
                                />
                                <div class="text-xs text-gray-600 dark:text-gray-400">
                                    The base URL for your preferred Gitea instance.
                                </div>
                            </div>

                            <div class="space-y-2">
                                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                    Documentation Download URLs
                                </div>
                                <textarea
                                    v-model="config.docs_download_urls"
                                    placeholder="Enter one URL per line (or comma-separated)"
                                    class="input-field min-h-[100px] text-xs font-mono"
                                    @input="onGiteaConfigChange"
                                ></textarea>
                                <div class="text-xs text-gray-600 dark:text-gray-400">
                                    List of ZIP URLs to try when downloading documentation. One URL per line.
                                </div>
                            </div>
                        </div>
                    </section>

                    <!-- Content Security Policy (CSP) -->
                    <section v-show="matchesSearch(...sectionKeywords.csp)" class="glass-card break-inside-avoid">
                        <header class="glass-card__header">
                            <div>
                                <div class="glass-card__eyebrow">Security</div>
                                <h2>{{ $t("app.csp_settings") }}</h2>
                                <p>{{ $t("app.csp_description") }}</p>
                            </div>
                        </header>
                        <div class="glass-card__body space-y-4">
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

                    <!-- Messages -->
                    <section v-show="matchesSearch(...sectionKeywords.messages)" class="glass-card break-inside-avoid">
                        <header class="glass-card__header">
                            <div>
                                <div class="glass-card__eyebrow">{{ $t("app.reliability") }}</div>
                                <h2>{{ $t("app.messages") }}</h2>
                                <p>{{ $t("app.messages_description") }}</p>
                            </div>
                        </header>
                        <div class="glass-card__body space-y-3">
                            <label class="setting-toggle">
                                <Toggle
                                    id="auto-resend-failed"
                                    v-model="config.auto_resend_failed_messages_when_announce_received"
                                    @update:model-value="onAutoResendFailedMessagesWhenAnnounceReceivedChangeWrapper"
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
                                    @update:model-value="onAllowAutoResendingFailedMessagesWithAttachmentsChangeWrapper"
                                />
                                <span class="setting-toggle__label">
                                    <span class="setting-toggle__title">{{ $t("app.retry_attachments_title") }}</span>
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
                        </div>
                    </section>

                    <!-- Propagation nodes -->
                    <section
                        v-show="matchesSearch(...sectionKeywords.propagation)"
                        class="glass-card break-inside-avoid"
                    >
                        <header class="glass-card__header">
                            <div>
                                <div class="glass-card__eyebrow">LXMF</div>
                                <h2>{{ $t("app.propagation_nodes") }}</h2>
                                <p>{{ $t("app.propagation_nodes_description") }}</p>
                            </div>
                            <RouterLink :to="{ name: 'propagation-nodes' }" class="primary-chip">
                                {{ $t("app.browse_nodes") }}
                            </RouterLink>
                        </header>
                        <div class="glass-card__body space-y-5">
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
                                        config.lxmf_local_propagation_node_address_hash || "—"
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
                                </span>
                            </label>
                            <div class="space-y-2">
                                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                                    {{ $t("app.preferred_propagation_node") }}
                                </div>
                                <input
                                    v-model="config.lxmf_preferred_propagation_node_destination_hash"
                                    type="text"
                                    :placeholder="$t('app.preferred_node_placeholder')"
                                    class="input-field monospace-field"
                                    @input="onLxmfPreferredPropagationNodeDestinationHashChange"
                                />
                                <div class="text-xs text-gray-600 dark:text-gray-400">
                                    {{ $t("app.fallback_node_description") }}
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
                                            time: formatSecondsAgo(
                                                config.lxmf_preferred_propagation_node_last_synced_at
                                            ),
                                        })
                                    }}</span>
                                    <span v-else>{{ $t("app.last_synced_never") }}</span>
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
                        </div>
                    </section>

                    <!-- System / RNS Reload -->
                    <!--
                    <section class="glass-card break-inside-avoid">
                        <header class="glass-card__header">
                            <div>
                                <div class="glass-card__eyebrow">{{ $t("app.system") }}</div>
                                <h2>{{ $t("app.reticulum_stack") }}</h2>
                                <p>{{ $t("app.reticulum_stack_description") }}</p>
                            </div>
                        </header>
                        <div class="glass-card__body space-y-4">
                            <div class="flex flex-col gap-3">
                                <button
                                    class="btn btn--secondary w-full justify-center gap-2 py-3"
                                    :disabled="reloadingRns"
                                    @click="reloadRns"
                                >
                                    <MaterialDesignIcon
                                        :icon-name="reloadingRns ? 'refresh' : 'restart'"
                                        class="w-5 h-5"
                                        :class="{ 'animate-spin-reverse': reloadingRns }"
                                    />
                                    <span>{{ reloadingRns ? $t("app.reloading_rns") : $t("app.reload_rns") }}</span>
                                </button>
                                <p class="text-xs text-gray-500 dark:text-gray-400">
                                    {{ $t("app.reload_rns_description") }}
                                </p>
                            </div>
                        </div>
                    </section>
                    -->
                </div>

                <!-- Keyboard Shortcuts (Full width at bottom) -->
                <div v-show="matchesSearch(...sectionKeywords.shortcuts)" class="mt-4">
                    <section class="glass-card">
                        <div class="glass-card__header">
                            <div class="flex items-center gap-3">
                                <div
                                    class="p-2 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-xl"
                                >
                                    <MaterialDesignIcon icon-name="keyboard-outline" class="size-6" />
                                </div>
                                <div>
                                    <h2>Keyboard Shortcuts</h2>
                                    <p>Customize your workflow with quick keyboard actions</p>
                                </div>
                            </div>
                        </div>
                        <div class="glass-card__body">
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div
                                    v-for="shortcut in KeyboardShortcuts.getDefaultShortcuts()"
                                    :key="shortcut.action"
                                    class="bg-gray-50/50 dark:bg-zinc-800/30 rounded-2xl p-5 border border-gray-100 dark:border-zinc-800"
                                >
                                    <div class="flex items-center justify-between mb-3">
                                        <span
                                            class="text-sm font-bold text-gray-900 dark:text-zinc-100 uppercase tracking-wide"
                                        >
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
</template>

<script>
import Utils from "../../js/Utils";
import WebSocketConnection from "../../js/WebSocketConnection";
import DialogUtils from "../../js/DialogUtils";
import ToastUtils from "../../js/ToastUtils";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import Toggle from "../forms/Toggle.vue";
import ShortcutRecorder from "./ShortcutRecorder.vue";
import KeyboardShortcuts from "../../js/KeyboardShortcuts";
import ElectronUtils from "../../js/ElectronUtils";
import LxmfUserIcon from "../LxmfUserIcon.vue";

export default {
    name: "SettingsPage",
    components: {
        MaterialDesignIcon,
        Toggle,
        ShortcutRecorder,
        LxmfUserIcon,
    },
    data() {
        return {
            ElectronUtils,
            KeyboardShortcuts,
            config: {
                display_name: "",
                identity_hash: "",
                lxmf_address_hash: "",
                theme: "dark",
                is_transport_enabled: false,
                auto_resend_failed_messages_when_announce_received: null,
                allow_auto_resending_failed_messages_with_attachments: null,
                auto_send_failed_messages_to_propagation_node: null,
                show_suggested_community_interfaces: null,
                lxmf_local_propagation_node_enabled: null,
                lxmf_preferred_propagation_node_destination_hash: null,
                lxmf_preferred_propagation_node_auto_select: null,
                archives_max_storage_gb: 1,
                backup_max_count: 5,
                block_attachments_from_strangers: true,
                block_all_from_strangers: false,
                banished_effect_enabled: true,
                banished_text: "BANISHED",
                banished_color: "#dc2626",
                blackhole_integration_enabled: true,
                announce_max_stored_lxmf_delivery: 1000,
                announce_max_stored_nomadnetwork_node: 1000,
                announce_max_stored_lxmf_propagation: 1000,
                announce_fetch_limit_lxmf_delivery: 500,
                announce_fetch_limit_nomadnetwork_node: 500,
                announce_fetch_limit_lxmf_propagation: 500,
                announce_search_max_fetch: 2000,
                discovered_interfaces_max_return: 500,
                message_font_size: 14,
                message_icon_size: 28,
                message_outbound_bubble_color: "#4f46e5",
                message_inbound_bubble_color: null,
                message_failed_bubble_color: "#ef4444",
                telephone_tone_generator_enabled: true,
                telephone_tone_generator_volume: 50,
                location_source: "browser",
                location_manual_lat: "0.0",
                location_manual_lon: "0.0",
                location_manual_alt: "0.0",
                telemetry_enabled: false,
                gitea_base_url: "https://git.quad4.io",
                docs_download_urls: "",
                csp_extra_connect_src: "",
                csp_extra_img_src: "",
                csp_extra_frame_src: "",
                csp_extra_script_src: "",
                csp_extra_style_src: "",
            },
            saveTimeouts: {},
            lastRememberedInboundStampCost: 8,
            shortcuts: [],
            reloadingRns: false,
            searchQuery: "",
            trustedTelemetryPeers: [],
            sectionKeywords: {
                banishment: [
                    "Visuals",
                    "app.banishment",
                    "app.banishment_description",
                    "app.banished_effect_enabled",
                    "app.banished_effect_description",
                    "app.banished_text_label",
                    "app.banished_text_description",
                    "app.banished_color_label",
                    "app.banished_color_description",
                ],
                maintenance: [
                    "Maintenance",
                    "maintenance.title",
                    "maintenance.description",
                    "maintenance.clear_messages",
                    "maintenance.clear_messages_desc",
                    "maintenance.clear_announces",
                    "maintenance.clear_announces_desc",
                    "maintenance.clear_nomadnet_favs",
                    "maintenance.clear_nomadnet_favs_desc",
                    "maintenance.clear_archives",
                    "maintenance.clear_archives_desc",
                    "maintenance.export_messages",
                    "maintenance.export_messages_desc",
                    "maintenance.import_messages",
                    "maintenance.import_messages_desc",
                    "Automatic Backup Limit",
                    "Export Folders",
                    "Import Folders",
                ],
                desktop: [
                    "Desktop",
                    "App Behaviour",
                    "app.desktop_open_calls_in_separate_window",
                    "app.desktop_open_calls_in_separate_window_description",
                    "app.desktop_hardware_acceleration_enabled",
                    "app.desktop_hardware_acceleration_enabled_description",
                ],
                archiver: ["Browsing", "Page Archiver", "archiver", "archive", "versions", "storage", "flush"],
                crawler: ["Discovery", "Smart Crawler", "crawler", "crawl", "retries", "delay", "concurrent"],
                csp: [
                    "Security",
                    "app.csp_settings",
                    "app.csp_description",
                    "app.csp_extra_connect_src",
                    "app.csp_extra_img_src",
                    "app.csp_extra_frame_src",
                    "app.csp_extra_script_src",
                    "app.csp_extra_style_src",
                    "CSP",
                    "Content Security Policy",
                ],
                appearance: [
                    "Personalise",
                    "app.appearance",
                    "app.appearance_description",
                    "app.theme",
                    "app.light_theme",
                    "app.dark_theme",
                    "Message Font Size",
                    "Icon Size",
                    "app.live_preview",
                    "app.realtime",
                ],
                language: ["i18n", "app.language", "app.select_language", "English", "Deutsch", "Русский"],
                networkSecurity: [
                    "RNS Security",
                    "Network Security",
                    "app.blackhole_integration_enabled",
                    "app.blackhole_integration_description",
                    "app.announce_limits",
                    "app.announce_limit_lxmf",
                    "app.announce_limit_nomadnet",
                    "app.announce_limit_prop",
                    "app.announce_max_stored_heading",
                    "app.announce_fetch_limit_heading",
                    "app.announce_search_max_fetch",
                    "app.discovered_interfaces_max_return",
                ],
                transport: [
                    "Reticulum",
                    "app.transport_mode",
                    "app.transport_description",
                    "app.enable_transport_mode",
                    "app.transport_toggle_description",
                ],
                interfaces: [
                    "Adapters",
                    "app.interfaces",
                    "app.show_community_interfaces",
                    "app.community_interfaces_description",
                ],
                blocked: ["Privacy", "Banished", "Manage Banished users and nodes"],
                auth: ["Security", "Authentication", "password", "Protect your instance with a password"],
                translator: [
                    "i18n",
                    "app.translator",
                    "translator.description",
                    "app.translator_enabled",
                    "app.translator_description",
                    "app.libretranslate_url",
                    "app.libretranslate_url_description",
                ],
                infrastructure: ["Infrastructure", "Sources & Mirroring", "gitea", "documentation", "download", "urls"],
                messages: [
                    "reliability",
                    "app.messages",
                    "app.messages_description",
                    "app.auto_resend_title",
                    "app.auto_resend_description",
                    "app.retry_attachments_title",
                    "app.retry_attachments_description",
                    "app.auto_fallback_title",
                    "app.auto_fallback_description",
                    "app.inbound_stamp_cost",
                    "app.inbound_stamp_description",
                    "app.inbound_stamps_required_title",
                    "app.inbound_stamps_required_description",
                ],
                propagation: [
                    "LXMF",
                    "app.propagation_nodes",
                    "app.propagation_nodes_description",
                    "app.browse_nodes",
                    "app.run_local_node",
                    "app.run_local_node_description",
                    "app.preferred_propagation_node",
                    "app.auto_sync_interval",
                    "app.propagation_stamp_cost",
                    "app.propagation_stamp_description",
                ],
                location: [
                    "Location",
                    "GPS",
                    "Privacy",
                    "manual",
                    "latitude",
                    "longitude",
                    "altitude",
                    "telemetry",
                    "trusted peers",
                ],
                shortcuts: ["Keyboard Shortcuts", "actions", "workflow"],
            },
        };
    },
    computed: {
        hasSearchResults() {
            if (!this.searchQuery) return true;
            return Object.values(this.sectionKeywords).some((keywords) => this.matchesSearch(...keywords));
        },
        safeConfig() {
            if (!this.config) {
                return {
                    display_name: "",
                    identity_hash: "",
                    lxmf_address_hash: "",
                    theme: "dark",
                    is_transport_enabled: false,
                    location_source: "browser",
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
    },
    beforeUnmount() {
        // stop listening for websocket messages
        WebSocketConnection.off("message", this.onWebsocketMessage);
    },
    mounted() {
        // listen for websocket messages
        WebSocketConnection.on("message", this.onWebsocketMessage);

        this.getConfig();
        this.getTrustedTelemetryPeers();
    },
    methods: {
        async getTrustedTelemetryPeers() {
            try {
                const response = await window.axios.get("/api/v1/telemetry/trusted-peers");
                this.trustedTelemetryPeers = response.data.trusted_peers;
            } catch (e) {
                console.error("Failed to fetch trusted telemetry peers", e);
            }
        },
        async revokeTelemetryTrust(peer) {
            try {
                await window.axios.patch(`/api/v1/telephone/contacts/${peer.id}`, {
                    is_telemetry_trusted: false,
                });
                this.getTrustedTelemetryPeers();
                ToastUtils.success(this.$t("app.telemetry_trust_revoked", { name: peer.name }));
            } catch (e) {
                ToastUtils.error("Failed to revoke telemetry trust");
                console.error(e);
            }
        },
        matchesSearch(...texts) {
            if (!this.searchQuery) return true;
            const query = this.searchQuery.toLowerCase();
            return texts.some((text) => {
                if (!text) return false;
                // If it looks like a translation key, translate it
                const content = text.includes(".") ? this.$t(text) : text;
                return content.toLowerCase().includes(query);
            });
        },
        async onWebsocketMessage(message) {
            const json = JSON.parse(message.data);
            switch (json.type) {
                case "config": {
                    if (json.config) {
                        this.config = { ...this.config, ...json.config };
                    }
                    break;
                }
                case "keyboard_shortcuts": {
                    this.shortcuts = json.shortcuts;
                    break;
                }
            }
        },
        async getConfig() {
            try {
                const response = await window.axios.get("/api/v1/config");
                if (response?.data?.config) {
                    this.config = { ...this.config, ...response.data.config };
                    const inbound = Number(this.config.lxmf_inbound_stamp_cost);
                    if (inbound > 0) {
                        this.lastRememberedInboundStampCost = Math.min(254, inbound);
                    }
                }
                this.getKeyboardShortcuts();
            } catch (e) {
                // do nothing if failed to load config
                console.log(e);
            }
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
                const response = await window.axios.patch("/api/v1/config", config);
                this.config = response.data.config;
                if (label) {
                    ToastUtils.success(this.$t("app.setting_auto_saved", { label: this.$t(`app.${label}`) }));
                }
            } catch (e) {
                ToastUtils.error(this.$t("common.save_failed"));
                console.log(e);
            }
        },
        numOrNull(v) {
            if (v === null || v === undefined || v === "") {
                return null;
            }
            const n = Number(v);
            return Number.isFinite(n) ? n : null;
        },
        async onAnnounceLimitsChange() {
            const c = this.config;
            await this.updateConfig(
                {
                    announce_max_stored_lxmf_delivery: this.numOrNull(c.announce_max_stored_lxmf_delivery),
                    announce_max_stored_nomadnetwork_node: this.numOrNull(
                        c.announce_max_stored_nomadnetwork_node
                    ),
                    announce_max_stored_lxmf_propagation: this.numOrNull(
                        c.announce_max_stored_lxmf_propagation
                    ),
                    announce_fetch_limit_lxmf_delivery: this.numOrNull(c.announce_fetch_limit_lxmf_delivery),
                    announce_fetch_limit_nomadnetwork_node: this.numOrNull(
                        c.announce_fetch_limit_nomadnetwork_node
                    ),
                    announce_fetch_limit_lxmf_propagation: this.numOrNull(
                        c.announce_fetch_limit_lxmf_propagation
                    ),
                    announce_search_max_fetch: this.numOrNull(c.announce_search_max_fetch),
                    discovered_interfaces_max_return: this.numOrNull(c.discovered_interfaces_max_return),
                },
                "announce_limits"
            );
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
            await this.updateConfig(
                {
                    theme: this.config.theme,
                },
                "theme"
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
        async onLanguageChange() {
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
                await this.updateConfig(
                    {
                        lxmf_preferred_propagation_node_destination_hash:
                            this.config.lxmf_preferred_propagation_node_destination_hash,
                    },
                    "preferred_node"
                );
            }, 1000);
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
        async onStrangerAttachmentBlockChange(value) {
            this.config.block_attachments_from_strangers = value;
            await this.updateConfig({ block_attachments_from_strangers: value }, "stranger_protection");
        },
        async onBlockAllFromStrangersChange(value) {
            this.config.block_all_from_strangers = value;
            await this.updateConfig({ block_all_from_strangers: value }, "stranger_protection");
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
                    },
                    "smart_crawler"
                );
            }, 1000);
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

            if (value) {
                // if enabled, redirect to setup page if password not set
                // or just to auth page in general
                this.$router.push({ name: "auth" });
            }
        },
        async onTranslatorEnabledChange(value) {
            this.config.translator_enabled = value;
            await this.updateConfig(
                {
                    translator_enabled: value,
                },
                "translator"
            );
        },
        async onTranslatorConfigChange() {
            if (this.saveTimeouts.translator) clearTimeout(this.saveTimeouts.translator);
            this.saveTimeouts.translator = setTimeout(async () => {
                await this.updateConfig(
                    {
                        libretranslate_url: this.config.libretranslate_url,
                    },
                    "translator"
                );
            }, 1000);
        },
        async onGiteaConfigChange() {
            if (this.saveTimeouts.gitea) clearTimeout(this.saveTimeouts.gitea);
            this.saveTimeouts.gitea = setTimeout(async () => {
                await this.updateConfig(
                    {
                        gitea_base_url: this.config.gitea_base_url,
                        docs_download_urls: this.config.docs_download_urls,
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
            if (
                !(await DialogUtils.confirm(
                    "Are you sure you want to delete all archived pages? This cannot be undone."
                ))
            ) {
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
            if (this.config.is_transport_enabled) {
                try {
                    await window.axios.post("/api/v1/reticulum/enable-transport");
                } catch {
                    ToastUtils.error(this.$t("settings.failed_enable_transport"));
                }
            } else {
                try {
                    await window.axios.post("/api/v1/reticulum/disable-transport");
                } catch {
                    ToastUtils.error(this.$t("settings.failed_disable_transport"));
                }
            }
        },
        async reloadRns() {
            if (this.reloadingRns) return;

            try {
                this.reloadingRns = true;
                const response = await window.axios.post("/api/v1/reticulum/reload");
                ToastUtils.success(response.data.message);
            } catch {
                ToastUtils.error(this.$t("settings.failed_reload_reticulum"));
            } finally {
                this.reloadingRns = false;
            }
        },
        async clearMessages() {
            if (!(await DialogUtils.confirm(this.$t("maintenance.clear_confirm")))) return;
            try {
                await window.axios.delete("/api/v1/maintenance/messages");
                ToastUtils.success(this.$t("maintenance.messages_cleared"));
            } catch {
                ToastUtils.error(this.$t("common.error"));
            }
        },
        async clearAnnounces() {
            if (!(await DialogUtils.confirm(this.$t("maintenance.clear_confirm")))) return;
            try {
                await window.axios.delete("/api/v1/maintenance/announces");
                ToastUtils.success(this.$t("maintenance.announces_cleared"));
            } catch {
                ToastUtils.error(this.$t("common.error"));
            }
        },
        async clearNomadnetFavorites() {
            if (!(await DialogUtils.confirm(this.$t("maintenance.clear_confirm")))) return;
            try {
                await window.axios.delete("/api/v1/maintenance/favourites", {
                    params: { aspect: "nomadnetwork.node" },
                });
                ToastUtils.success(this.$t("maintenance.favourites_cleared"));
            } catch {
                ToastUtils.error(this.$t("common.error"));
            }
        },
        async clearLxmfIcons() {
            if (!(await DialogUtils.confirm(this.$t("maintenance.clear_confirm")))) return;
            try {
                await window.axios.delete("/api/v1/maintenance/lxmf-icons");
                ToastUtils.success(this.$t("maintenance.lxmf_icons_cleared"));
            } catch {
                ToastUtils.error(this.$t("common.error"));
            }
        },
        async clearArchives() {
            if (!(await DialogUtils.confirm(this.$t("maintenance.clear_confirm")))) return;
            try {
                await window.axios.delete("/api/v1/maintenance/archives");
                ToastUtils.success(this.$t("maintenance.archives_cleared"));
            } catch {
                ToastUtils.error(this.$t("common.error"));
            }
        },
        async clearReticulumDocs() {
            if (!(await DialogUtils.confirm(this.$t("maintenance.clear_confirm")))) return;
            try {
                await window.axios.delete("/api/v1/maintenance/docs/reticulum");
                ToastUtils.success(this.$t("maintenance.docs_cleared"));
            } catch {
                ToastUtils.error(this.$t("common.error"));
            }
        },
        async exportMessages() {
            try {
                const response = await window.axios.get("/api/v1/maintenance/messages/export");
                const messages = response.data.messages;
                const dataStr = JSON.stringify({ messages }, null, 2);
                const dataUri = "data:application/json;charset=utf-8," + encodeURIComponent(dataStr);

                const exportFileDefaultName = `meshchat_messages_${new Date().toISOString().slice(0, 10)}.json`;

                const linkElement = document.createElement("a");
                linkElement.setAttribute("href", dataUri);
                linkElement.setAttribute("download", exportFileDefaultName);
                linkElement.click();
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

            const reader = new FileReader();
            reader.onload = async (e) => {
                try {
                    const data = JSON.parse(e.target.result);
                    if (!data.messages) throw new Error("Invalid file format");

                    await window.axios.post("/api/v1/maintenance/messages/import", {
                        messages: data.messages,
                    });
                    ToastUtils.success(this.$t("maintenance.import_success", { count: data.messages.length }));
                } catch {
                    ToastUtils.error(this.$t("maintenance.import_failed"));
                }
            };
            reader.readAsText(file);
            // Reset input
            event.target.value = "";
        },
        async exportFolders() {
            try {
                const response = await window.axios.get("/api/v1/lxmf/folders/export");
                const dataStr = JSON.stringify(response.data, null, 2);
                const dataUri = "data:application/json;charset=utf-8," + encodeURIComponent(dataStr);
                const exportFileDefaultName = `meshchat_folders_${new Date().toISOString().slice(0, 10)}.json`;
                const linkElement = document.createElement("a");
                linkElement.setAttribute("href", dataUri);
                linkElement.setAttribute("download", exportFileDefaultName);
                linkElement.click();
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

                    await window.axios.post("/api/v1/lxmf/folders/import", data);
                    ToastUtils.success(this.$t("settings.folders_imported"));
                } catch {
                    ToastUtils.error(this.$t("settings.failed_import_folders"));
                }
            };
            reader.readAsText(file);
            // Reset input
            event.target.value = "";
        },
        formatSecondsAgo: function (seconds) {
            return Utils.formatSecondsAgo(seconds);
        },
    },
};
</script>

<style scoped>
.glass-card {
    @apply bg-white/90 dark:bg-zinc-900/80 backdrop-blur border border-gray-200 dark:border-zinc-800 rounded-3xl shadow-lg flex flex-col;
}
.glass-card__header {
    @apply flex items-center justify-between gap-3 px-4 py-4 border-b border-gray-100/70 dark:border-zinc-800/80;
}
.glass-card__header h2 {
    @apply text-lg font-semibold text-gray-900 dark:text-white;
}
.glass-card__header p {
    @apply text-sm text-gray-600 dark:text-gray-400;
}
.glass-card__eyebrow {
    @apply text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400;
}
.glass-card__body {
    @apply px-4 py-4 text-gray-900 dark:text-gray-100;
}
.input-field {
    @apply bg-gray-50/90 dark:bg-zinc-800/80 border border-gray-200 dark:border-zinc-700 text-sm rounded-2xl focus:ring-2 focus:ring-blue-400 focus:border-blue-400 dark:focus:ring-blue-500 dark:focus:border-blue-500 block w-full p-2.5 text-gray-900 dark:text-gray-100 transition;
}
.btn-maintenance {
    @apply w-full px-4 py-3 rounded-2xl border transition flex items-center justify-between;
}
.setting-toggle {
    @apply flex items-start gap-3 rounded-2xl border border-gray-200 dark:border-zinc-800 bg-white/70 dark:bg-zinc-900/70 px-3 py-3;
}
.setting-toggle :deep(.sr-only) {
    @apply absolute w-px h-px p-0 -m-px overflow-hidden whitespace-nowrap border-0;
}
.setting-toggle__label {
    @apply flex-1 flex flex-col gap-0.5;
}
.setting-toggle__title {
    @apply text-sm font-semibold text-gray-900 dark:text-white;
}
.setting-toggle__description {
    @apply text-sm text-gray-600 dark:text-gray-300;
}
.setting-toggle__hint {
    @apply text-xs text-gray-500 dark:text-gray-400;
}
.info-callout {
    @apply rounded-2xl border border-blue-100 dark:border-blue-900/40 bg-blue-50/60 dark:bg-blue-900/20 px-3 py-3 text-blue-900 dark:text-blue-100;
}
.monospace-field {
    font-family: "Roboto Mono", monospace;
}
.address-card {
    @apply relative border border-gray-200 dark:border-zinc-800 rounded-2xl bg-white/80 dark:bg-zinc-900/70 p-4 space-y-2;
}
.address-card__label {
    @apply text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400;
}
.address-card__value {
    @apply text-sm text-gray-900 dark:text-white break-words pr-16;
}
.address-card__action {
    @apply absolute top-3 right-3 inline-flex items-center gap-1 rounded-full border border-gray-200 dark:border-zinc-700 px-3 py-1 text-xs font-semibold text-gray-700 dark:text-gray-100 bg-white/70 dark:bg-zinc-900/60 hover:border-blue-400 dark:hover:border-blue-500 transition;
}
.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}
</style>
