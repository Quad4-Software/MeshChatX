<template>
    <div
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
                            <div class="text-2xl font-semibold text-gray-900 dark:text-white">
                                {{ config.display_name }}
                            </div>
                            <div class="text-sm text-gray-600 dark:text-gray-300">{{ $t("app.manage_identity") }}</div>
                        </div>
                        <div class="flex flex-col sm:flex-row gap-2">
                            <button
                                type="button"
                                class="inline-flex items-center justify-center gap-x-2 rounded-xl border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 px-4 py-2 text-sm font-semibold text-gray-900 dark:text-zinc-100 shadow-sm hover:border-blue-400 dark:hover:border-blue-400/70 transition"
                                @click="copyValue(config.identity_hash, $t('app.identity_hash'))"
                            >
                                <MaterialDesignIcon icon-name="content-copy" class="w-4 h-4" />
                                {{ $t("app.identity_hash") }}
                            </button>
                            <button
                                type="button"
                                class="inline-flex items-center justify-center gap-x-2 rounded-xl bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 px-4 py-2 text-sm font-semibold text-white shadow hover:shadow-md transition"
                                @click="copyValue(config.lxmf_address_hash, $t('app.lxmf_address'))"
                            >
                                <MaterialDesignIcon icon-name="account-plus" class="w-4 h-4" />
                                {{ $t("app.lxmf_address") }}
                            </button>
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

                <!-- settings grid -->
                <div class="columns-1 lg:columns-2 gap-4 space-y-4">
                    <!-- Page Archiver -->
                    <section class="glass-card break-inside-avoid">
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
                    <section class="glass-card break-inside-avoid">
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
                    <section class="glass-card break-inside-avoid">
                        <header class="glass-card__header">
                            <div>
                                <div class="glass-card__eyebrow">Personalise</div>
                                <h2>{{ $t("app.appearance") }}</h2>
                                <p>{{ $t("app.appearance_description") }}</p>
                            </div>
                        </header>
                        <div class="glass-card__body space-y-3">
                            <select v-model="config.theme" class="input-field" @change="onThemeChange">
                                <option value="light">{{ $t("app.light_theme") }}</option>
                                <option value="dark">{{ $t("app.dark_theme") }}</option>
                            </select>
                            <div
                                class="flex items-center justify-between text-sm text-gray-600 dark:text-gray-300 border border-dashed border-gray-200 dark:border-zinc-800 rounded-2xl px-3 py-2"
                            >
                                <div>{{ $t("app.live_preview") }}</div>
                                <span
                                    class="inline-flex items-center gap-1 text-blue-500 dark:text-blue-300 text-xs font-semibold uppercase"
                                >
                                    <span class="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                                    {{ $t("app.realtime") }}
                                </span>
                            </div>
                        </div>
                    </section>

                    <!-- Language -->
                    <section class="glass-card break-inside-avoid">
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
                            </select>
                        </div>
                    </section>

                    <!-- Transport -->
                    <section class="glass-card break-inside-avoid">
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
                    <section class="glass-card break-inside-avoid">
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
                    <section class="glass-card break-inside-avoid">
                        <header class="glass-card__header">
                            <div>
                                <div class="glass-card__eyebrow">Privacy</div>
                                <h2>Blocked</h2>
                                <p>Manage blocked users and nodes</p>
                            </div>
                            <RouterLink :to="{ name: 'blocked' }" class="primary-chip"> Manage Blocked </RouterLink>
                        </header>
                        <div class="glass-card__body">
                            <p class="text-sm text-gray-600 dark:text-gray-400">
                                Blocked users and nodes will not be able to send you messages, and their announces will
                                be ignored.
                            </p>
                        </div>
                    </section>

                    <!-- Authentication -->
                    <section class="glass-card break-inside-avoid">
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

                    <!-- Messages -->
                    <section class="glass-card break-inside-avoid">
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
                            <div class="space-y-2">
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
                    <section class="glass-card break-inside-avoid">
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
                                        :class="{ 'animate-spin': reloadingRns }"
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
                <div class="mt-4">
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

export default {
    name: "SettingsPage",
    components: {
        MaterialDesignIcon,
        Toggle,
        ShortcutRecorder,
    },
    data() {
        return {
            KeyboardShortcuts,
            config: {
                auto_resend_failed_messages_when_announce_received: null,
                allow_auto_resending_failed_messages_with_attachments: null,
                auto_send_failed_messages_to_propagation_node: null,
                show_suggested_community_interfaces: null,
                lxmf_local_propagation_node_enabled: null,
                lxmf_preferred_propagation_node_destination_hash: null,
                archives_max_storage_gb: 1,
            },
            saveTimeouts: {},
            shortcuts: [],
            reloadingRns: false,
        };
    },
    beforeUnmount() {
        // stop listening for websocket messages
        WebSocketConnection.off("message", this.onWebsocketMessage);
    },
    mounted() {
        // listen for websocket messages
        WebSocketConnection.on("message", this.onWebsocketMessage);

        this.getConfig();
    },
    methods: {
        async onWebsocketMessage(message) {
            const json = JSON.parse(message.data);
            switch (json.type) {
                case "config": {
                    this.config = json.config;
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
                this.config = response.data.config;
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
            ToastUtils.success("Shortcut saved");
        },
        async deleteShortcut(action) {
            await KeyboardShortcuts.deleteShortcut(action);
            ToastUtils.success("Shortcut deleted");
        },
        async updateConfig(config, label = null) {
            try {
                const response = await window.axios.patch("/api/v1/config", config);
                this.config = response.data.config;
                if (label) {
                    ToastUtils.success(this.$t("app.setting_auto_saved", { label: this.$t(`app.${label}`) }));
                }
            } catch (e) {
                ToastUtils.error("Failed to save config!");
                console.log(e);
            }
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
        async onLxmfInboundStampCostChange() {
            if (this.saveTimeouts.inbound_stamp) clearTimeout(this.saveTimeouts.inbound_stamp);
            this.saveTimeouts.inbound_stamp = setTimeout(async () => {
                await this.updateConfig(
                    {
                        lxmf_inbound_stamp_cost: this.config.lxmf_inbound_stamp_cost,
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
            ToastUtils.success("Archived pages flushed.");
        },
        async onIsTransportEnabledChangeWrapper(value) {
            this.config.is_transport_enabled = value;
            await this.onIsTransportEnabledChange();
        },
        async onIsTransportEnabledChange() {
            if (this.config.is_transport_enabled) {
                try {
                    const response = await window.axios.post("/api/v1/reticulum/enable-transport");
                    ToastUtils.success(response.data.message);
                } catch (e) {
                    ToastUtils.error("Failed to enable transport mode!");
                    console.log(e);
                }
            } else {
                try {
                    const response = await window.axios.post("/api/v1/reticulum/disable-transport");
                    ToastUtils.success(response.data.message);
                } catch (e) {
                    ToastUtils.error("Failed to disable transport mode!");
                    console.log(e);
                }
            }
        },
        async reloadRns() {
            if (this.reloadingRns) return;

            try {
                this.reloadingRns = true;
                const response = await window.axios.post("/api/v1/reticulum/reload");
                ToastUtils.success(response.data.message);
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || "Failed to reload Reticulum!");
                console.error(e);
            } finally {
                this.reloadingRns = false;
            }
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
.primary-chip {
    @apply inline-flex items-center gap-x-1 rounded-full bg-blue-600/90 px-4 py-1.5 text-xs font-semibold text-white shadow hover:bg-blue-500 transition;
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
