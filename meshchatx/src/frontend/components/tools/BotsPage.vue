<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
        <ToolsPageHeader
            icon="robot"
            :title="$t('tools.bots.title')"
            :description="$t('tools.bots.description')"
            accent="blue"
        />
        <div
            class="flex-1 overflow-y-auto w-full px-3 sm:px-4 md:px-5 lg:px-8 py-4 sm:py-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]"
        >
            <div class="space-y-8 w-full max-w-4xl mx-auto">
                <div class="space-y-6">
                    <div class="space-y-4">
                        <h3 class="text-lg font-semibold text-sem-fg">
                            {{ $t("bots.create_new_bot") }}
                        </h3>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                            <div
                                v-for="template in templates"
                                :key="template.id"
                                class="relative rounded-lg border border-sem-border bg-sem-surface p-4 hover:border-blue-400 dark:hover:border-blue-600 transition cursor-pointer flex flex-col justify-between min-h-[140px] pr-12"
                                @click="openSetup(template)"
                            >
                                <div class="flex items-start gap-3 min-w-0">
                                    <LxmfUserIcon
                                        v-if="template.default_icon"
                                        :icon-name="template.default_icon"
                                        icon-class="size-9 shrink-0"
                                    />
                                    <div class="min-w-0">
                                        <div class="font-bold text-sem-fg">{{ template.name }}</div>
                                        <div class="text-sm text-gray-600 dark:text-gray-400 mt-1">
                                            {{ template.description }}
                                        </div>
                                    </div>
                                </div>
                                <div
                                    class="absolute bottom-3 right-3 p-2 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors pointer-events-none"
                                >
                                    <MaterialDesignIcon icon-name="chevron-right" class="size-6" />
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="space-y-4">
                        <h3 class="text-lg font-semibold text-sem-fg">
                            {{ $t("bots.saved_bots") }}
                        </h3>
                        <div v-if="bots.length === 0" class="text-sm text-gray-500 italic">
                            {{ $t("bots.no_bots_running") }}
                        </div>
                        <div v-else class="space-y-2 sm:space-y-3">
                            <div
                                v-for="bot in bots"
                                :key="bot.id"
                                :class="[
                                    'relative rounded-lg border border-sem-border bg-sem-surface p-3 sm:p-4',
                                    editingBotId === bot.id ? 'pr-28 sm:pr-40' : 'pr-10 sm:pr-12',
                                ]"
                            >
                                <div
                                    class="absolute top-2 right-2 flex flex-wrap items-center justify-end gap-0.5 z-10 max-w-[min(100%,calc(100%-2rem))]"
                                >
                                    <button
                                        v-if="lxmfAddressFor(bot)"
                                        type="button"
                                        class="p-2 rounded-lg text-sem-fg-muted hover:text-blue-600 dark:hover:text-blue-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors"
                                        :title="$t('bots.chat_with_bot')"
                                        @click="openChatWithBot(bot)"
                                    >
                                        <MaterialDesignIcon icon-name="message-text" class="size-5" />
                                    </button>
                                    <button
                                        v-if="bot.running"
                                        type="button"
                                        class="p-2 rounded-lg text-sem-fg-muted hover:text-amber-600 dark:hover:text-amber-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors"
                                        :title="$t('bots.force_announce')"
                                        @click="forceAnnounce(bot)"
                                    >
                                        <MaterialDesignIcon icon-name="bullhorn" class="size-5" />
                                    </button>
                                    <button
                                        v-if="bot.running"
                                        type="button"
                                        class="p-2 rounded-lg text-sem-fg-muted hover:text-blue-600 dark:hover:text-blue-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors"
                                        :title="$t('bots.restart_bot')"
                                        @click="restartExisting(bot)"
                                    >
                                        <MaterialDesignIcon icon-name="refresh" class="size-5" />
                                    </button>
                                    <button
                                        v-if="bot.running"
                                        type="button"
                                        class="p-2 rounded-lg text-sem-fg-muted hover:text-red-600 dark:hover:text-red-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors"
                                        :title="$t('bots.stop_bot')"
                                        @click="stopBot(bot.id)"
                                    >
                                        <MaterialDesignIcon icon-name="stop" class="size-5" />
                                    </button>
                                    <button
                                        v-if="!bot.running"
                                        type="button"
                                        class="p-2 rounded-lg text-sem-fg-muted hover:text-emerald-600 dark:hover:text-emerald-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors"
                                        :title="$t('bots.start_bot')"
                                        @click="startExisting(bot)"
                                    >
                                        <MaterialDesignIcon icon-name="play" class="size-5" />
                                    </button>
                                    <button
                                        type="button"
                                        class="p-2 rounded-lg text-sem-fg-muted hover:text-violet-600 dark:hover:text-violet-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors"
                                        :title="$t('bots.view_process_log')"
                                        @click="openProcessLog(bot)"
                                    >
                                        <MaterialDesignIcon icon-name="bug-outline" class="size-5" />
                                    </button>
                                    <button
                                        type="button"
                                        class="p-2 rounded-lg text-sem-fg-muted hover:text-fuchsia-600 dark:hover:text-fuchsia-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors"
                                        :title="$t('bots.edit_icon')"
                                        @click="openIconEditor(bot)"
                                    >
                                        <MaterialDesignIcon icon-name="palette" class="size-5" />
                                    </button>
                                    <button
                                        v-if="(bot.template_id || bot.template) === 'custom'"
                                        type="button"
                                        class="p-2 rounded-lg text-sem-fg-muted hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors"
                                        :title="$t('bots.edit_custom_commands')"
                                        @click="openCustomEditor(bot)"
                                    >
                                        <MaterialDesignIcon icon-name="format-list-bulleted" class="size-5" />
                                    </button>
                                    <button
                                        v-if="(bot.template_id || bot.template) === 'rrc'"
                                        type="button"
                                        class="p-2 rounded-lg text-sem-fg-muted hover:text-teal-600 dark:hover:text-teal-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors"
                                        :title="$t('bots.edit_rrc')"
                                        @click="openRrcEditor(bot)"
                                    >
                                        <MaterialDesignIcon icon-name="access-point" class="size-5" />
                                    </button>
                                    <button
                                        type="button"
                                        class="p-2 rounded-lg text-sem-fg-muted hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors"
                                        :title="$t('bots.edit_lxmf_config')"
                                        @click="openLxmfConfig(bot)"
                                    >
                                        <MaterialDesignIcon icon-name="cog" class="size-5" />
                                    </button>
                                    <button
                                        type="button"
                                        class="p-2 rounded-lg text-sem-fg-muted hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors"
                                        :title="$t('bots.export_identity')"
                                        @click="exportIdentity(bot.id)"
                                    >
                                        <MaterialDesignIcon icon-name="export" class="size-5" />
                                    </button>
                                    <button
                                        type="button"
                                        class="p-2 rounded-lg text-sem-fg-muted hover:text-red-600 dark:hover:text-red-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 transition-colors"
                                        :title="$t('bots.delete_bot')"
                                        @click="deleteBot(bot.id)"
                                    >
                                        <MaterialDesignIcon icon-name="delete" class="size-5" />
                                    </button>
                                </div>

                                <div class="flex items-start gap-3 min-w-0">
                                    <LxmfUserIcon
                                        v-if="bot.icon && bot.icon.icon_name"
                                        :icon-name="bot.icon.icon_name"
                                        :icon-foreground-colour="bot.icon.fg_color"
                                        :icon-background-colour="bot.icon.bg_color"
                                        icon-class="size-10"
                                    />
                                    <div v-else class="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg shrink-0">
                                        <MaterialDesignIcon icon-name="robot" class="size-6 text-sem-accent" />
                                    </div>
                                    <div class="min-w-0 flex-1 space-y-1.5 sm:pr-2">
                                        <div
                                            class="flex items-center gap-1 min-w-0"
                                            :class="
                                                editingBotId === bot.id
                                                    ? 'max-w-[min(100%,14rem)] sm:max-w-[16rem]'
                                                    : ''
                                            "
                                        >
                                            <template v-if="editingBotId === bot.id">
                                                <input
                                                    v-model="editingNameDraft"
                                                    type="text"
                                                    class="input-field text-xs py-1 h-8 px-2 min-w-0 flex-1 max-w-40 sm:max-w-48"
                                                    maxlength="256"
                                                    @keydown.enter.prevent="saveBotName(bot)"
                                                    @keydown.escape="cancelEditName"
                                                />
                                                <button
                                                    type="button"
                                                    class="p-1 rounded-lg text-gray-500 hover:text-emerald-600 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 shrink-0"
                                                    :title="$t('common.save')"
                                                    @click="saveBotName(bot)"
                                                >
                                                    <MaterialDesignIcon icon-name="check" class="size-4" />
                                                </button>
                                                <button
                                                    type="button"
                                                    class="p-1 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 shrink-0"
                                                    :title="$t('common.cancel')"
                                                    @click="cancelEditName"
                                                >
                                                    <MaterialDesignIcon icon-name="close" class="size-4" />
                                                </button>
                                            </template>
                                            <template v-else>
                                                <span class="font-bold text-sem-fg truncate">{{ bot.name }}</span>
                                                <button
                                                    type="button"
                                                    class="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 shrink-0"
                                                    :title="$t('bots.edit_name')"
                                                    @click="startEditName(bot)"
                                                >
                                                    <MaterialDesignIcon icon-name="pencil" class="size-4" />
                                                </button>
                                            </template>
                                        </div>
                                        <div class="flex items-center gap-2 text-[11px] text-sem-fg-muted">
                                            <span
                                                class="inline-block size-2 rounded-full shrink-0"
                                                :class="bot.running ? 'bg-emerald-500' : 'bg-gray-400 dark:bg-gray-500'"
                                            ></span>
                                            <span>{{
                                                bot.running ? $t("bots.status_running") : $t("bots.status_stopped")
                                            }}</span>
                                            <span v-if="bot.running && bot.uptime_seconds != null"
                                                >&middot; {{ $t("bots.uptime") }}
                                                {{ formatUptime(bot.uptime_seconds) }}</span
                                            >
                                        </div>
                                        <div
                                            v-if="bot.rrc && bot.rrc.hub"
                                            class="text-[11px] text-sem-fg-muted min-w-0"
                                        >
                                            <span class="font-mono break-all"
                                                >{{ $t("bots.rrc_hub") }}: {{ bot.rrc.hub }}</span
                                            >
                                            <span v-if="bot.rrc.rooms && bot.rrc.rooms.length">
                                                &middot;
                                                {{ bot.rrc.rooms.map((r) => "#" + r).join(", ") }}</span
                                            >
                                        </div>
                                        <div
                                            v-if="bot.custom && bot.custom.commands && bot.custom.commands.length"
                                            class="text-[11px] text-sem-fg-muted"
                                        >
                                            {{
                                                $t("bots.custom_command_count", {
                                                    count: bot.custom.commands.length,
                                                })
                                            }}
                                        </div>
                                        <dl class="space-y-2.5 text-[11px] text-sem-fg-muted min-w-0">
                                            <div class="min-w-0">
                                                <dt
                                                    class="text-[10px] font-semibold uppercase tracking-wide text-sem-fg-muted mb-1"
                                                >
                                                    {{ $t("bots.lxmf_address") }}
                                                </dt>
                                                <dd class="m-0 min-w-0">
                                                    <button
                                                        v-if="lxmfAddressFor(bot)"
                                                        type="button"
                                                        class="font-mono text-[11px] break-all text-left w-full max-w-full text-gray-800 dark:text-gray-200 hover:underline leading-snug"
                                                        @click="copyLxmfAddress(bot)"
                                                    >
                                                        {{ lxmfAddressFor(bot) }}
                                                    </button>
                                                    <span v-else class="text-sem-fg-muted">{{
                                                        $t("bots.address_pending")
                                                    }}</span>
                                                </dd>
                                            </div>
                                            <div class="min-w-0">
                                                <dt
                                                    class="text-[10px] font-semibold uppercase tracking-wide text-sem-fg-muted mb-1"
                                                >
                                                    {{ $t("bots.last_announce") }}
                                                </dt>
                                                <dd class="m-0 text-gray-700 dark:text-gray-200 leading-snug">
                                                    <span v-if="bot.last_announce_at">{{
                                                        formatRelativeSince(bot.last_announce_at)
                                                    }}</span>
                                                    <span v-else-if="lxmfAddressFor(bot)">{{
                                                        $t("bots.never_announced")
                                                    }}</span>
                                                    <span v-else>-</span>
                                                </dd>
                                            </div>
                                        </dl>
                                        <div
                                            v-if="botLastError(bot)"
                                            class="rounded-lg border border-red-200/90 dark:border-red-900/70 bg-red-50/90 dark:bg-red-950/50 px-2.5 py-2 text-[11px] text-red-900 dark:text-red-100"
                                        >
                                            <div class="font-semibold flex items-center gap-1.5">
                                                <MaterialDesignIcon
                                                    icon-name="alert-circle-outline"
                                                    class="size-4 shrink-0 opacity-90"
                                                />
                                                {{ $t("bots.last_error_heading") }}
                                            </div>
                                            <pre
                                                class="mt-1.5 m-0 whitespace-pre-wrap wrap-break-word font-mono text-[10px] leading-relaxed text-red-800/95 dark:text-red-100/90"
                                                >{{ botLastError(bot) }}</pre>
                                        </div>
                                        <div class="text-[10px] text-gray-400 pt-0.5">
                                            {{ bot.template_id || bot.template }}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div
            v-if="processLogModalBot"
            class="fixed inset-0 z-100 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/50"
            @click.self="closeProcessLog"
        >
            <div
                class="w-full sm:max-w-3xl flex flex-col max-sm:h-[92dvh] max-sm:max-h-[92dvh] sm:max-h-[90vh] rounded-t-2xl sm:rounded-lg border border-sem-border bg-sem-surface shadow-xl touch-pan-y min-h-0"
            >
                <div class="flex justify-between items-start gap-2 p-3 sm:p-5 border-b border-sem-border shrink-0">
                    <div class="min-w-0 pr-2">
                        <h3 class="text-lg sm:text-xl font-bold text-sem-fg">
                            {{ $t("bots.process_log_title") }}
                        </h3>
                        <p class="text-sm text-gray-600 dark:text-gray-400 mt-0.5 truncate">
                            {{ processLogModalBot.name }}
                        </p>
                        <p v-if="processLogTruncated" class="text-xs text-amber-700 dark:text-amber-400 mt-1">
                            {{ $t("bots.process_log_truncated") }}
                        </p>
                    </div>
                    <div class="flex items-center gap-1 shrink-0">
                        <button
                            type="button"
                            class="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80"
                            :title="$t('bots.copy_process_log')"
                            :disabled="!processLogText"
                            @click="copyProcessLog"
                        >
                            <MaterialDesignIcon icon-name="content-copy" class="size-5" />
                        </button>
                        <button
                            type="button"
                            class="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80"
                            @click="closeProcessLog"
                        >
                            <MaterialDesignIcon icon-name="close" class="size-5" />
                        </button>
                    </div>
                </div>
                <div class="flex-1 min-h-0 flex flex-col p-2 sm:p-5 pt-2 sm:pt-2">
                    <div
                        v-if="processLogLoading"
                        class="flex items-center justify-center py-16 text-sem-fg-muted text-sm"
                    >
                        {{ $t("bots.process_log_loading") }}
                    </div>
                    <div
                        v-else
                        class="flex-1 min-h-0 max-sm:min-h-[55dvh] sm:min-h-[12rem] overflow-auto rounded-lg border border-sem-border bg-sem-surface-muted touch-pan-x"
                    >
                        <pre
                            class="bots-process-log-text m-0 min-h-full w-max min-w-full p-2 sm:p-3 font-mono text-gray-800 dark:text-gray-200 whitespace-pre select-text"
                            >{{ processLogDisplayText }}</pre>
                    </div>
                </div>
            </div>
        </div>

        <div
            v-if="iconModalBot"
            class="fixed inset-0 z-100 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/50"
            @click.self="closeIconEditor"
        >
            <div
                class="w-full sm:max-w-lg rounded-t-2xl sm:rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-6 space-y-4 max-h-[90vh] overflow-y-auto"
            >
                <div class="flex justify-between items-start gap-2">
                    <div class="min-w-0 pr-2">
                        <h3 class="text-lg sm:text-xl font-bold text-sem-fg">
                            {{ $t("bots.icon_modal_title") }}
                        </h3>
                        <p class="text-sm text-gray-600 dark:text-gray-400 mt-0.5 truncate">
                            {{ iconModalBot.name }}
                        </p>
                    </div>
                    <button
                        type="button"
                        class="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80"
                        @click="closeIconEditor"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-5" />
                    </button>
                </div>

                <LxmfIconEditor v-model="iconDraft" />

                <p v-if="iconModalBot.running" class="text-xs text-amber-700 dark:text-amber-400">
                    {{ $t("bots.restart_hint_generic") }}
                </p>

                <div class="flex justify-end gap-2 pt-2">
                    <button
                        type="button"
                        class="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80"
                        @click="closeIconEditor"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-6" />
                    </button>
                    <button
                        type="button"
                        class="p-2 rounded-lg text-gray-500 hover:text-emerald-600 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 disabled:opacity-40"
                        :disabled="iconSaving"
                        @click="saveIcon"
                    >
                        <span
                            v-if="iconSaving"
                            class="inline-block w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin"
                        ></span>
                        <MaterialDesignIcon v-else icon-name="check" class="size-6" />
                    </button>
                </div>
            </div>
        </div>

        <div
            v-if="customModalBot"
            class="fixed inset-0 z-100 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/50"
            @click.self="closeCustomEditor"
        >
            <div
                class="w-full sm:max-w-lg rounded-t-2xl sm:rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-6 space-y-4 max-h-[90vh] overflow-y-auto"
            >
                <div class="flex justify-between items-start gap-2">
                    <div class="min-w-0 pr-2">
                        <h3 class="text-lg sm:text-xl font-bold text-sem-fg">
                            {{ $t("bots.custom_modal_title") }}
                        </h3>
                        <p class="text-sm text-gray-600 dark:text-gray-400 mt-0.5 truncate">
                            {{ customModalBot.name }}
                        </p>
                    </div>
                    <button
                        type="button"
                        class="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80"
                        @click="closeCustomEditor"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-5" />
                    </button>
                </div>

                <BotCustomCommandsEditor v-model="customDraft" />

                <p v-if="customModalBot.running" class="text-xs text-amber-700 dark:text-amber-400">
                    {{ $t("bots.restart_hint_generic") }}
                </p>

                <div class="flex justify-end gap-2 pt-2">
                    <button
                        type="button"
                        class="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80"
                        @click="closeCustomEditor"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-6" />
                    </button>
                    <button
                        type="button"
                        class="p-2 rounded-lg text-gray-500 hover:text-emerald-600 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 disabled:opacity-40"
                        :disabled="customSaving"
                        @click="saveCustom"
                    >
                        <span
                            v-if="customSaving"
                            class="inline-block w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin"
                        ></span>
                        <MaterialDesignIcon v-else icon-name="check" class="size-6" />
                    </button>
                </div>
            </div>
        </div>

        <div
            v-if="rrcModalBot"
            class="fixed inset-0 z-100 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/50"
            @click.self="closeRrcEditor"
        >
            <div
                class="w-full sm:max-w-lg rounded-t-2xl sm:rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-6 space-y-4 max-h-[90vh] overflow-y-auto"
            >
                <div class="flex justify-between items-start gap-2">
                    <div class="min-w-0 pr-2">
                        <h3 class="text-lg sm:text-xl font-bold text-sem-fg">
                            {{ $t("bots.rrc_modal_title") }}
                        </h3>
                        <p class="text-sm text-gray-600 dark:text-gray-400 mt-0.5 truncate">
                            {{ rrcModalBot.name }}
                        </p>
                    </div>
                    <button
                        type="button"
                        class="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80"
                        @click="closeRrcEditor"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-5" />
                    </button>
                </div>

                <BotRrcFields v-model="rrcDraft" />

                <p v-if="rrcModalBot.running" class="text-xs text-amber-700 dark:text-amber-400">
                    {{ $t("bots.restart_hint_generic") }}
                </p>

                <div class="flex justify-end gap-2 pt-2">
                    <button
                        type="button"
                        class="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80"
                        @click="closeRrcEditor"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-6" />
                    </button>
                    <button
                        type="button"
                        class="p-2 rounded-lg text-gray-500 hover:text-emerald-600 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 disabled:opacity-40"
                        :disabled="rrcSaving"
                        @click="saveRrc"
                    >
                        <span
                            v-if="rrcSaving"
                            class="inline-block w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin"
                        ></span>
                        <MaterialDesignIcon v-else icon-name="check" class="size-6" />
                    </button>
                </div>
            </div>
        </div>

        <div
            v-if="lxmfConfigModalBot"
            class="fixed inset-0 z-100 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/50"
            @click.self="closeLxmfConfig"
        >
            <div
                class="w-full sm:max-w-lg rounded-t-2xl sm:rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-6 space-y-4 max-h-[90vh] overflow-y-auto"
            >
                <div class="flex justify-between items-start gap-2">
                    <div class="min-w-0 pr-2">
                        <h3 class="text-lg sm:text-xl font-bold text-sem-fg">
                            {{ $t("bots.lxmf_config_title") }}
                        </h3>
                        <p class="text-sm text-gray-600 dark:text-gray-400 mt-0.5 truncate">
                            {{ lxmfConfigModalBot.name }}
                        </p>
                    </div>
                    <button
                        type="button"
                        class="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80"
                        @click="closeLxmfConfig"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-5" />
                    </button>
                </div>

                <LxmfConfigFields v-model="lxmfConfigDraft" />

                <div
                    v-if="lxmfConfigModalBot.effective_lxmf_config"
                    class="rounded-lg border border-sem-border bg-sem-surface-muted p-3 text-[11px] text-gray-700 dark:text-gray-300"
                >
                    <div class="font-semibold mb-1">{{ $t("bots.effective_settings_heading") }}</div>
                    <pre class="m-0 whitespace-pre-wrap wrap-break-word font-mono">{{
                        formatEffectiveLxmfConfig(lxmfConfigModalBot.effective_lxmf_config)
                    }}</pre>
                </div>

                <p v-if="lxmfConfigModalBot.running" class="text-xs text-amber-700 dark:text-amber-400">
                    {{ $t("bots.lxmf_config_restart_hint") }}
                </p>

                <div class="flex justify-end gap-2 pt-2">
                    <button
                        type="button"
                        class="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80"
                        @click="closeLxmfConfig"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-6" />
                    </button>
                    <button
                        type="button"
                        class="p-2 rounded-lg text-gray-500 hover:text-emerald-600 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 disabled:opacity-40"
                        :disabled="lxmfConfigSaving"
                        @click="saveLxmfConfig"
                    >
                        <span
                            v-if="lxmfConfigSaving"
                            class="inline-block w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin"
                        ></span>
                        <MaterialDesignIcon v-else icon-name="check" class="size-6" />
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import ToastUtils from "../../js/ToastUtils";
import DialogUtils from "../../js/DialogUtils";
import DownloadUtils from "../../js/DownloadUtils";
import GlobalEmitter from "../../js/GlobalEmitter";
import GlobalState from "../../js/GlobalState";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToolsPageHeader from "./ToolsPageHeader.vue";
import LxmfUserIcon from "../LxmfUserIcon.vue";
import LxmfIconEditor from "../LxmfIconEditor.vue";
import LxmfConfigFields from "./internal/BotLxmfConfigFields.vue";
import BotCustomCommandsEditor, {
    buildCustomPayload,
    defaultCustomDraft,
    draftFromBotCustom,
} from "./internal/BotCustomCommandsEditor.vue";
import BotRrcFields, { buildRrcPayload, defaultRrcDraft, draftFromBotRrc } from "./internal/BotRrcFields.vue";
import { buildLxmfConfigPatch, defaultLxmfConfigDraft, draftFromBotLxmfConfig } from "./internal/botLxmfConfigForm.js";

export default {
    name: "BotsPage",
    components: {
        MaterialDesignIcon,
        ToolsPageHeader,
        LxmfUserIcon,
        LxmfIconEditor,
        LxmfConfigFields,
        BotCustomCommandsEditor,
        BotRrcFields,
    },
    data() {
        return {
            bots: [],
            templates: [],
            loading: true,
            refreshInterval: null,
            relativeTimerTick: 0,
            relativeTimerInterval: null,
            editingBotId: null,
            editingNameDraft: "",
            processLogModalBot: null,
            processLogText: "",
            processLogTruncated: false,
            processLogLoading: false,
            lxmfConfigModalBot: null,
            lxmfConfigDraft: defaultLxmfConfigDraft(),
            lxmfConfigSaving: false,
            iconModalBot: null,
            iconDraft: null,
            iconSaving: false,
            customModalBot: null,
            customDraft: defaultCustomDraft(),
            customSaving: false,
            rrcModalBot: null,
            rrcDraft: defaultRrcDraft(),
            rrcSaving: false,
        };
    },
    computed: {
        processLogDisplayText() {
            const t = (this.processLogText || "").trim();
            if (t) {
                return this.processLogText;
            }
            return this.processLogLoading ? "" : this.$t("bots.process_log_empty");
        },
    },
    mounted() {
        this.getStatus();
        this.startStatusPollInterval();
        GlobalEmitter.on("websocket-reconnected", this.onWebsocketReconnected);
        this._liveTransportReadyWatch = this.$watch(
            () => GlobalState.liveTransportReady,
            () => {
                this.startStatusPollInterval();
            }
        );
        this.relativeTimerInterval = setInterval(() => {
            this.relativeTimerTick += 1;
        }, 1000);
    },
    beforeUnmount() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        if (this.relativeTimerInterval) {
            clearInterval(this.relativeTimerInterval);
        }
        GlobalEmitter.off("websocket-reconnected", this.onWebsocketReconnected);
        if (typeof this._liveTransportReadyWatch === "function") {
            this._liveTransportReadyWatch();
            this._liveTransportReadyWatch = null;
        }
    },
    methods: {
        onWebsocketReconnected() {
            void this.getStatus();
        },
        startStatusPollInterval() {
            if (this.refreshInterval) {
                clearInterval(this.refreshInterval);
                this.refreshInterval = null;
            }
            const pollMs = GlobalState.liveTransportReady ? 30000 : 5000;
            this.refreshInterval = setInterval(this.getStatus, pollMs);
        },
        async getStatus() {
            try {
                const response = await window.api.get("/api/v1/bots/status");
                this.bots = response.data.status.bots || [];
                this.templates = response.data.templates;
                this.loading = false;
            } catch (e) {
                console.error("[BotsPage] getStatus failed", e?.response?.data || e?.message || e);
            }
        },
        openSetup(template) {
            this.$router.push({
                name: "bot-setup",
                query: { template: template.id },
            });
        },
        async stopBot(botId) {
            try {
                await window.api.post("/api/v1/bots/stop", { bot_id: botId });
                ToastUtils.success(this.$t("bots.bot_stopped"));
                this.getStatus();
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("bots.failed_to_stop"));
            }
        },
        async startExisting(bot) {
            try {
                const payload = {
                    bot_id: bot.id,
                    template_id: bot.template_id || bot.template,
                    name: bot.name,
                };
                if (payload.template_id === "rrc" && bot.rrc) {
                    payload.rrc = bot.rrc;
                }
                await window.api.post("/api/v1/bots/start", payload);
                ToastUtils.success(this.$t("bots.bot_started"));
                this.getStatus();
            } catch (e) {
                console.error(e);
                ToastUtils.error(e.response?.data?.message || this.$t("bots.failed_to_start"));
            }
        },
        async restartExisting(bot) {
            try {
                await window.api.post("/api/v1/bots/restart", { bot_id: bot.id });
                ToastUtils.success(this.$t("bots.bot_started"));
                this.getStatus();
            } catch (e) {
                console.error(e);
                ToastUtils.error(e.response?.data?.message || this.$t("bots.failed_to_start"));
            }
        },
        async deleteBot(botId) {
            if (!(await DialogUtils.confirm(this.$t("common.delete_confirm")))) return;
            try {
                await window.api.post("/api/v1/bots/delete", { bot_id: botId });
                ToastUtils.success(this.$t("bots.bot_deleted"));
                if (this.editingBotId === botId) {
                    this.cancelEditName();
                }
                this.getStatus();
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("bots.failed_to_delete"));
            }
        },
        async exportIdentity(botId) {
            try {
                const response = await window.api.post(
                    "/api/v1/bots/export",
                    { bot_id: botId },
                    { responseType: "arraybuffer" }
                );
                await DownloadUtils.downloadFromApiResponse(response, `bot_${botId}_identity`);
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("bots.export_failed"));
            }
        },
        startEditName(bot) {
            this.editingBotId = bot.id;
            this.editingNameDraft = bot.name || "";
        },
        cancelEditName() {
            this.editingBotId = null;
            this.editingNameDraft = "";
        },
        async saveBotName(bot) {
            if (this.editingBotId !== bot.id) {
                return;
            }
            const name = (this.editingNameDraft || "").trim();
            if (!name) {
                ToastUtils.error(this.$t("bots.name_required"));
                return;
            }
            try {
                await window.api.patch("/api/v1/bots/update", {
                    bot_id: bot.id,
                    name,
                });
                ToastUtils.success(this.$t("bots.bot_renamed"));
                this.cancelEditName();
                this.getStatus();
            } catch (e) {
                console.error(e);
                ToastUtils.error(e.response?.data?.message || this.$t("bots.rename_failed"));
            }
        },
        async forceAnnounce(bot) {
            try {
                await window.api.post("/api/v1/bots/announce", { bot_id: bot.id });
                ToastUtils.success(this.$t("bots.announce_triggered"));
                this.getStatus();
            } catch (e) {
                console.error(e);
                ToastUtils.error(e.response?.data?.message || this.$t("bots.announce_failed"));
            }
        },
        botLastError(bot) {
            const t = (bot?.last_error || "").trim();
            return t;
        },
        closeProcessLog() {
            this.processLogModalBot = null;
            this.processLogText = "";
            this.processLogTruncated = false;
            this.processLogLoading = false;
        },
        async openProcessLog(bot) {
            this.processLogModalBot = bot;
            this.processLogText = "";
            this.processLogTruncated = false;
            this.processLogLoading = true;
            try {
                const response = await window.api.get("/api/v1/bots/subprocess-log", {
                    params: { bot_id: bot.id },
                });
                this.processLogText =
                    response.data.log === null || response.data.log === undefined ? "" : String(response.data.log);
                this.processLogTruncated = Boolean(response.data.truncated);
            } catch (e) {
                console.error(e);
                ToastUtils.error(e.response?.data?.message || this.$t("bots.process_log_failed"));
                this.closeProcessLog();
            } finally {
                this.processLogLoading = false;
            }
        },
        copyProcessLog() {
            const t = (this.processLogText || "").trim();
            if (!t) {
                return;
            }
            navigator.clipboard.writeText(this.processLogText);
            ToastUtils.success(this.$t("bots.process_log_copied"));
        },
        lxmfAddressFor(bot) {
            const raw = bot.lxmf_address || bot.full_address;
            if (!raw || typeof raw !== "string") {
                return "";
            }
            const h = raw.trim().toLowerCase();
            return h.length === 32 && /^[0-9a-f]+$/.test(h) ? h : "";
        },
        openChatWithBot(bot) {
            const h = this.lxmfAddressFor(bot);
            if (!h) {
                return;
            }
            const routeName = this.$route?.meta?.isPopout ? "messages-popout" : "messages";
            this.$router.push({ name: routeName, params: { destinationHash: h } });
        },
        copyLxmfAddress(bot) {
            const h = this.lxmfAddressFor(bot);
            if (!h) {
                return;
            }
            navigator.clipboard.writeText(h);
            ToastUtils.success(this.$t("translator.copied_to_clipboard"));
        },
        formatRelativeSince(iso) {
            if (!iso) {
                return "";
            }
            let t;
            try {
                t = new Date(iso).getTime();
            } catch {
                return String(iso);
            }
            if (Number.isNaN(t)) {
                return String(iso);
            }
            const now = Date.now() + 0 * this.relativeTimerTick;
            let sec = Math.floor((now - t) / 1000);
            if (sec < 0) {
                sec = 0;
            }
            if (sec < 60) {
                return `${sec}s`;
            }
            const min = Math.floor(sec / 60);
            if (min < 60) {
                return min === 1 ? `${min}m` : `${min}m`;
            }
            const h = Math.floor(min / 60);
            if (h < 24) {
                return h === 1 ? `${h}h` : `${h}h`;
            }
            const d = Math.floor(h / 24);
            if (d < 30) {
                return d === 1 ? "1 day" : `${d} days`;
            }
            const mo = Math.floor(d / 30);
            if (d < 365) {
                return mo === 1 ? "1 month" : `${mo} months`;
            }
            const y = Math.floor(d / 365);
            return y === 1 ? "1 year" : `${y} years`;
        },
        openLxmfConfig(bot) {
            this.lxmfConfigModalBot = bot;
            this.lxmfConfigDraft = draftFromBotLxmfConfig(bot.lxmf_config);
        },
        closeLxmfConfig() {
            this.lxmfConfigModalBot = null;
            this.lxmfConfigDraft = defaultLxmfConfigDraft();
            this.lxmfConfigSaving = false;
        },
        formatEffectiveLxmfConfig(effective) {
            if (!effective || typeof effective !== "object") {
                return "";
            }
            return JSON.stringify(effective, null, 2);
        },
        async saveLxmfConfig() {
            if (!this.lxmfConfigModalBot || this.lxmfConfigSaving) {
                return;
            }
            if (this.lxmfConfigDraft.propagation_mode === "manual") {
                const node = (this.lxmfConfigDraft.propagation_node || "").trim().toLowerCase();
                if (!/^[0-9a-f]{32}$/.test(node)) {
                    ToastUtils.error(this.$t("bots.lxmf_config_manual_node_required"));
                    return;
                }
            }
            this.lxmfConfigSaving = true;
            try {
                const patch = buildLxmfConfigPatch(this.lxmfConfigDraft, { clearEmpty: true });
                await window.api.patch("/api/v1/bots/lxmf-config", {
                    bot_id: this.lxmfConfigModalBot.id,
                    lxmf_config: patch,
                });
                ToastUtils.success(this.$t("bots.lxmf_config_saved"));
                if (this.lxmfConfigModalBot.running) {
                    ToastUtils.info(this.$t("bots.lxmf_config_restart_hint"));
                }
                this.closeLxmfConfig();
                this.getStatus();
            } catch (e) {
                console.error(e);
                ToastUtils.error(e.response?.data?.message || this.$t("bots.lxmf_config_failed"));
            } finally {
                this.lxmfConfigSaving = false;
            }
        },
        openIconEditor(bot) {
            this.iconModalBot = bot;
            this.iconDraft = bot.icon && bot.icon.icon_name ? { ...bot.icon } : null;
        },
        closeIconEditor() {
            this.iconModalBot = null;
            this.iconDraft = null;
            this.iconSaving = false;
        },
        async saveIcon() {
            if (!this.iconModalBot || this.iconSaving) {
                return;
            }
            this.iconSaving = true;
            try {
                await window.api.patch("/api/v1/bots/update", {
                    bot_id: this.iconModalBot.id,
                    icon: this.iconDraft,
                });
                ToastUtils.success(this.$t("bots.icon_saved"));
                if (this.iconModalBot.running) {
                    ToastUtils.info(this.$t("bots.restart_hint_generic"));
                }
                this.closeIconEditor();
                this.getStatus();
            } catch (e) {
                console.error(e);
                ToastUtils.error(e.response?.data?.message || this.$t("bots.icon_save_failed"));
            } finally {
                this.iconSaving = false;
            }
        },
        openCustomEditor(bot) {
            this.customModalBot = bot;
            this.customDraft = draftFromBotCustom(bot.custom);
        },
        closeCustomEditor() {
            this.customModalBot = null;
            this.customDraft = defaultCustomDraft();
            this.customSaving = false;
        },
        async saveCustom() {
            if (!this.customModalBot || this.customSaving) {
                return;
            }
            const payload = buildCustomPayload(this.customDraft);
            if (payload.commands.length === 0) {
                ToastUtils.error(this.$t("bots.custom_requires_command"));
                return;
            }
            this.customSaving = true;
            try {
                await window.api.patch("/api/v1/bots/update", {
                    bot_id: this.customModalBot.id,
                    custom: payload,
                });
                ToastUtils.success(this.$t("bots.custom_saved"));
                if (this.customModalBot.running) {
                    ToastUtils.info(this.$t("bots.restart_hint_generic"));
                }
                this.closeCustomEditor();
                this.getStatus();
            } catch (e) {
                console.error(e);
                ToastUtils.error(e.response?.data?.message || this.$t("bots.custom_save_failed"));
            } finally {
                this.customSaving = false;
            }
        },
        openRrcEditor(bot) {
            this.rrcModalBot = bot;
            this.rrcDraft = draftFromBotRrc(bot.rrc);
        },
        closeRrcEditor() {
            this.rrcModalBot = null;
            this.rrcDraft = defaultRrcDraft();
            this.rrcSaving = false;
        },
        async saveRrc() {
            if (!this.rrcModalBot || this.rrcSaving) {
                return;
            }
            const payload = buildRrcPayload(this.rrcDraft);
            if (!/^[0-9a-f]{32}$/.test(payload.hub)) {
                ToastUtils.error(this.$t("bots.rrc_hub_required"));
                return;
            }
            this.rrcSaving = true;
            try {
                await window.api.patch("/api/v1/bots/update", {
                    bot_id: this.rrcModalBot.id,
                    rrc: payload,
                });
                ToastUtils.success(this.$t("bots.rrc_saved"));
                if (this.rrcModalBot.running) {
                    ToastUtils.info(this.$t("bots.restart_hint_generic"));
                }
                this.closeRrcEditor();
                this.getStatus();
            } catch (e) {
                console.error(e);
                ToastUtils.error(e.response?.data?.message || this.$t("bots.rrc_save_failed"));
            } finally {
                this.rrcSaving = false;
            }
        },
        formatUptime(seconds) {
            let s = Math.max(0, Number(seconds) || 0);
            const d = Math.floor(s / 86400);
            s -= d * 86400;
            const h = Math.floor(s / 3600);
            s -= h * 3600;
            const m = Math.floor(s / 60);
            s -= m * 60;
            if (d) {
                return `${d}d ${h}h`;
            }
            if (h) {
                return `${h}h ${m}m`;
            }
            if (m) {
                return `${m}m ${Math.floor(s)}s`;
            }
            return `${Math.floor(s)}s`;
        },
    },
};
</script>

<style scoped>
@reference "../../style.css";
.glass-label {
    @apply block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1;
}
.bots-process-log-text {
    font-size: 0.6875rem;
    line-height: 1.55;
    -webkit-text-size-adjust: 100%;
    text-size-adjust: 100%;
}
@media (max-width: 639px) {
    .bots-process-log-text {
        font-size: 0.5625rem;
        line-height: 1.28;
    }
}
</style>
