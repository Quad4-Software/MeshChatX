<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <section v-show="visible" class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">{{ $t("app.appearance") }}</div>
                <h2>{{ $t("app.appearance") }}</h2>
                <p>{{ $t("app.appearance_description") }}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <div class="space-y-2">
                <div class="text-sm font-medium text-sem-fg">
                    {{ $t("app.theme") }}
                </div>
                <SegmentedControl :model-value="config.theme" :options="themeModes" @change="onThemeModeSelect" />
            </div>

            <div class="space-y-2">
                <div class="text-sm font-medium text-sem-fg">
                    {{ $t("app.theme_preset") }}
                </div>
                <ThemePresetPicker :value="themePresetValue" :config="config" @change="onThemePresetPickerChange" />
                <p class="text-xs text-sem-fg-muted">
                    {{ $t("app.theme_preset_description") }}
                </p>
            </div>

            <div class="space-y-2">
                <div class="flex items-center justify-between gap-2">
                    <div class="text-sm font-medium text-sem-fg">
                        {{ $t("app.accent_color") }}
                    </div>
                    <button
                        v-if="config.accent_color"
                        type="button"
                        class="text-[10px] font-bold uppercase text-sem-accent hover:underline"
                        @click="onAccentColorReset"
                    >
                        {{ $t("app.accent_color_reset") }}
                    </button>
                </div>
                <div class="flex gap-2">
                    <input
                        :value="accentColorInput"
                        type="color"
                        class="color-fill-input w-12 h-10 rounded-xl border border-sem-border cursor-pointer"
                        @input="onAccentColorInput"
                    />
                    <input
                        :value="config.accent_color || ''"
                        type="text"
                        class="input-field monospace-field flex-1"
                        :placeholder="$t('app.accent_color_placeholder')"
                        @input="onAccentColorInput"
                    />
                </div>
                <p class="text-xs text-sem-fg-muted">
                    {{ $t("app.accent_color_description") }}
                </p>
            </div>

            <div v-if="themePresetValue === 'custom'" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div class="space-y-2">
                    <div class="text-sm font-medium text-sem-fg">
                        {{ $t("app.custom_canvas_color") }}
                    </div>
                    <div class="flex gap-2">
                        <input
                            :value="customCanvasInput"
                            type="color"
                            class="color-fill-input w-12 h-10 rounded-xl border border-sem-border cursor-pointer"
                            @input="onCustomCanvasInput"
                        />
                        <input
                            :value="config.custom_canvas_color || ''"
                            type="text"
                            class="input-field monospace-field flex-1"
                            @input="onCustomCanvasInput"
                        />
                    </div>
                </div>
                <div class="space-y-2">
                    <div class="text-sm font-medium text-sem-fg">
                        {{ $t("app.custom_surface_color") }}
                    </div>
                    <div class="flex gap-2">
                        <input
                            :value="customSurfaceInput"
                            type="color"
                            class="color-fill-input w-12 h-10 rounded-xl border border-sem-border cursor-pointer"
                            @input="onCustomSurfaceInput"
                        />
                        <input
                            :value="config.custom_surface_color || ''"
                            type="text"
                            class="input-field monospace-field flex-1"
                            @input="onCustomSurfaceInput"
                        />
                    </div>
                </div>
                <p class="text-xs text-sem-fg-muted sm:col-span-2">
                    {{ $t("app.custom_colors_description") }}
                </p>
            </div>

            <div class="space-y-2">
                <div class="text-sm font-medium text-sem-fg">
                    {{ $t("app.messages_sidebar_position") }}
                </div>
                <SegmentedControl
                    :model-value="config.messages_sidebar_position"
                    :options="sidebarPositionOptions"
                    @change="onMessagesSidebarPositionSelect"
                />
            </div>

            <div class="space-y-2">
                <div class="text-sm font-medium text-sem-fg">
                    {{ $t("app.app_sidebar_layout") }}
                </div>
                <SegmentedControl
                    :model-value="sidebarLayoutValue"
                    :options="sidebarLayoutOptions"
                    @change="onAppSidebarLayoutSelect"
                />
                <p class="text-xs text-sem-fg-muted">
                    {{ $t("app.app_sidebar_layout_description") }}
                </p>
            </div>

            <div class="space-y-2">
                <div class="flex items-center justify-between gap-2">
                    <div class="text-sm font-medium text-sem-fg">
                        {{ $t("app.top_nav_buttons") }}
                    </div>
                    <button
                        type="button"
                        class="text-xs font-semibold text-sem-accent hover:underline"
                        @click="resetTopNav"
                    >
                        {{ $t("app.top_nav_reset") }}
                    </button>
                </div>
                <p class="text-xs text-sem-fg-muted">
                    {{ $t("app.top_nav_description") }}
                </p>
                <ul class="divide-y divide-sem-border rounded-xl border border-sem-border overflow-hidden">
                    <li
                        v-for="row in topNavEditorRows"
                        :key="row.item.id"
                        class="flex items-center gap-2 px-3 py-2"
                        :class="row.pinned ? 'bg-sem-surface' : 'bg-sem-surface-muted/40 opacity-60'"
                        :data-testid="`topnav-row-${row.item.id}`"
                    >
                        <input
                            type="checkbox"
                            class="size-4 shrink-0 accent-sem-accent"
                            :checked="row.pinned"
                            :aria-label="$t(row.item.labelKey)"
                            @change="toggleTopNavItem(row.item.id)"
                        />
                        <MaterialDesignIcon :icon-name="row.item.icon" class="size-4 shrink-0 text-sem-fg-muted" />
                        <span class="flex-1 min-w-0 truncate text-sm text-sem-fg">{{ $t(row.item.labelKey) }}</span>
                        <button
                            v-if="row.pinned"
                            type="button"
                            class="p-1 rounded-md text-sem-fg-muted hover:bg-sem-surface-muted disabled:opacity-30"
                            :disabled="row.pinnedIndex === 0"
                            :title="$t('app.nav_move_up')"
                            :aria-label="$t('app.nav_move_up')"
                            @click="moveTopNavItem(row.item.id, -1)"
                        >
                            <MaterialDesignIcon icon-name="chevron-up" class="size-4" />
                        </button>
                        <button
                            v-if="row.pinned"
                            type="button"
                            class="p-1 rounded-md text-sem-fg-muted hover:bg-sem-surface-muted disabled:opacity-30"
                            :disabled="row.pinnedIndex === topNavPinnedCount - 1"
                            :title="$t('app.nav_move_down')"
                            :aria-label="$t('app.nav_move_down')"
                            @click="moveTopNavItem(row.item.id, 1)"
                        >
                            <MaterialDesignIcon icon-name="chevron-down" class="size-4" />
                        </button>
                    </li>
                </ul>
            </div>

            <div class="space-y-2">
                <div class="flex items-center justify-between">
                    <div class="text-sm font-medium text-sem-fg">
                        {{ $t("app.message_font_size") }}
                    </div>
                    <div class="text-xs font-mono text-sem-accent">{{ config.message_font_size || 14 }}px</div>
                </div>
                <div class="flex items-center gap-3">
                    <span class="text-xs text-sem-fg-muted">A</span>
                    <input
                        :value="config.message_font_size"
                        type="range"
                        min="10"
                        max="32"
                        step="1"
                        class="range-input flex-1"
                        @input="onMessageFontSizeInput"
                    />
                    <span class="text-lg text-sem-fg-muted">A</span>
                </div>
            </div>

            <div class="space-y-2">
                <div class="flex items-center justify-between">
                    <div class="text-sm font-medium text-sem-fg">
                        {{ $t("app.message_icon_size") }}
                    </div>
                    <div class="text-xs font-mono text-sem-accent">{{ config.message_icon_size || 28 }}px</div>
                </div>
                <div class="flex items-center gap-3">
                    <MaterialDesignIcon
                        icon-name="account-outline"
                        class="shrink-0 text-sem-fg-muted"
                        :style="{ width: '16px', height: '16px' }"
                    />
                    <input
                        :value="config.message_icon_size"
                        type="range"
                        min="16"
                        max="64"
                        step="1"
                        class="range-input flex-1"
                        @input="onMessageIconSizeInput"
                    />
                    <MaterialDesignIcon
                        icon-name="account"
                        class="shrink-0 text-sem-fg-muted"
                        :style="messageIconPreviewStyle"
                    />
                </div>
            </div>

            <div class="space-y-2">
                <div class="flex items-center justify-between">
                    <div class="text-sm font-medium text-sem-fg">
                        {{ $t("app.ui_transparency") }}
                    </div>
                    <div class="text-xs font-mono text-sem-accent">
                        {{ Math.max(0, Math.min(100, Number(config.ui_transparency) || 0)) }}%
                    </div>
                </div>
                <div class="flex items-center gap-3">
                    <span class="text-xs text-gray-400">0</span>
                    <input
                        :value="config.ui_transparency"
                        type="range"
                        min="0"
                        max="100"
                        step="1"
                        class="range-input flex-1"
                        @input="onUiTransparencyInput"
                    />
                    <span class="text-xs text-gray-400">100</span>
                </div>
                <div class="text-xs text-sem-fg-muted">
                    {{ $t("app.ui_transparency_description") }}
                </div>
            </div>

            <label class="setting-toggle">
                <Toggle
                    id="ui-glass-enabled"
                    :model-value="config.ui_glass_enabled"
                    @update:model-value="onUiGlassEnabledToggle"
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{{ $t("app.ui_glass_enabled") }}</span>
                    <span class="setting-toggle__description">{{ $t("app.ui_glass_enabled_description") }}</span>
                </span>
            </label>

            <div class="settings-field">
                <label class="block text-sm font-medium text-sem-fg mb-1" for="ui-font-family">
                    {{ $t("app.ui_font_family") }}
                </label>
                <div class="flex items-center gap-3">
                    <select
                        id="ui-font-family"
                        :value="config.ui_font_family || 'system'"
                        class="input-field flex-1"
                        @change="onFontFamilyChange"
                    >
                        <option value="system">{{ $t("app.ui_font_system") }}</option>
                        <option value="noto-sans">{{ $t("app.ui_font_noto_sans") }}</option>
                        <option value="inter">{{ $t("app.ui_font_inter") }}</option>
                        <option value="jetbrains-mono">{{ $t("app.ui_font_jetbrains_mono") }}</option>
                        <option value="ibm-plex-sans">{{ $t("app.ui_font_ibm_plex_sans") }}</option>
                        <option value="space-grotesk">{{ $t("app.ui_font_space_grotesk") }}</option>
                        <option value="roboto-mono-nerd">{{ $t("app.ui_font_roboto_mono_nerd") }}</option>
                        <option v-if="config.ui_custom_font_name" value="custom">
                            {{ config.ui_custom_font_name }}
                        </option>
                    </select>
                    <label
                        class="cursor-pointer rounded-lg border border-sem-border px-3 py-2 text-xs font-medium text-sem-fg-muted hover:border-sem-accent hover:text-sem-accent transition-colors"
                        :title="$t('app.ui_font_upload_tooltip')"
                    >
                        <input
                            type="file"
                            accept=".woff2,.ttf,.otf"
                            class="hidden"
                            @change="onFontFileUpload"
                        />
                        {{ $t("app.ui_font_upload") }}
                    </label>
                </div>
                <div
                    class="mt-2 rounded-lg border border-sem-border bg-sem-surface-muted p-3 text-sm"
                    :style="fontPreviewStyle"
                >
                    {{ $t("app.ui_font_preview_text") }}
                </div>
                <div class="mt-1 text-[11px] text-sem-fg-muted">
                    {{ $t("app.ui_font_preview_hint") }}
                </div>
            </div>

            <label class="setting-toggle">
                <Toggle
                    id="messages-multi-pane-enabled"
                    :model-value="config.messages_multi_pane_enabled"
                    @update:model-value="onMessagesMultiPaneEnabledToggle"
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{{ $t("app.messages_multi_pane_enabled") }}</span>
                    <span class="setting-toggle__description">{{
                        $t("app.messages_multi_pane_enabled_description")
                    }}</span>
                </span>
            </label>

            <label class="setting-toggle">
                <Toggle
                    id="nomad-tabs-enabled"
                    :model-value="config.nomad_tabs_enabled"
                    @update:model-value="onNomadTabsEnabledToggle"
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{{ $t("app.nomad_tabs_enabled") }}</span>
                    <span class="setting-toggle__description">{{ $t("app.nomad_tabs_enabled_description") }}</span>
                </span>
            </label>

            <label v-if="config.nomad_tabs_enabled" class="setting-toggle">
                <Toggle
                    id="nomad-private-tabs-enabled"
                    :model-value="config.nomad_private_tabs_enabled"
                    @update:model-value="onNomadPrivateTabsEnabledToggle"
                />
                <MaterialDesignIcon icon-name="incognito" class="size-5 text-sem-fg-muted shrink-0" />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{{ $t("app.nomad_private_tabs_enabled") }}</span>
                    <span class="setting-toggle__description">{{
                        $t("app.nomad_private_tabs_enabled_description")
                    }}</span>
                </span>
            </label>

            <label v-if="config.nomad_tabs_enabled" class="setting-toggle">
                <Toggle
                    id="nomad-history-enabled"
                    :model-value="config.nomad_history_enabled"
                    @update:model-value="onNomadHistoryEnabledToggle"
                />
                <MaterialDesignIcon icon-name="history" class="size-5 text-sem-fg-muted shrink-0" />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{{ $t("app.nomad_history_enabled") }}</span>
                    <span class="setting-toggle__description">{{ $t("app.nomad_history_enabled_description") }}</span>
                </span>
            </label>

            <label class="setting-toggle">
                <Toggle id="rrc-enabled" :model-value="config.rrc_enabled" @update:model-value="onRrcEnabledToggle" />
                <MaterialDesignIcon icon-name="forum-outline" class="size-5 text-sem-fg-muted shrink-0" />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{{ $t("app.rrc_enabled") }}</span>
                    <span class="setting-toggle__description">{{ $t("app.rrc_enabled_description") }}</span>
                </span>
            </label>

            <label v-if="config.rrc_enabled" class="setting-toggle">
                <Toggle
                    id="rrc-unread-badges"
                    :model-value="config.rrc_unread_badges_enabled"
                    @update:model-value="onRrcUnreadBadgesEnabledToggle"
                />
                <MaterialDesignIcon icon-name="bell-badge-outline" class="size-5 text-sem-fg-muted shrink-0" />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{{ $t("app.rrc_unread_badges_enabled") }}</span>
                    <span class="setting-toggle__description">{{
                        $t("app.rrc_unread_badges_enabled_description")
                    }}</span>
                </span>
            </label>

            <div class="pt-1">
                <button
                    type="button"
                    class="p-0 border-0 bg-transparent text-sm font-medium text-sem-accent hover:underline cursor-pointer"
                    @click="$emit('reset-appearance-defaults')"
                >
                    {{ $t("app.reset_appearance_defaults") }}
                </button>
            </div>

            <div class="space-y-4 pt-2">
                <div class="text-sm font-bold text-sem-fg-muted uppercase tracking-wider">Message Bubbles</div>

                <div class="flex items-start gap-3 rounded-xl border border-sem-border px-3 py-2.5">
                    <input
                        id="detailed-outbound-send-status"
                        type="checkbox"
                        class="mt-1 rounded-sm border-gray-300 dark:border-zinc-600"
                        :checked="detailedOutboundSendStatus"
                        @change="$emit('detailed-outbound-send-status-change', $event)"
                    />
                    <label for="detailed-outbound-send-status" class="min-w-0 cursor-pointer">
                        <div class="text-sm font-medium text-sem-fg">
                            {{ $t("app.detailed_outbound_send_status") }}
                        </div>
                        <div class="text-xs text-sem-fg-muted mt-0.5">
                            {{ $t("app.detailed_outbound_send_status_description") }}
                        </div>
                    </label>
                </div>

                <div class="flex items-start gap-3 rounded-xl border border-sem-border px-3 py-2.5">
                    <input
                        id="outbound-transfer-progress-enabled"
                        type="checkbox"
                        class="mt-1 rounded-sm border-gray-300 dark:border-zinc-600"
                        :checked="outboundTransferProgressEnabled"
                        @change="$emit('outbound-transfer-progress-enabled-change', $event)"
                    />
                    <label for="outbound-transfer-progress-enabled" class="min-w-0 cursor-pointer">
                        <div class="text-sm font-medium text-sem-fg">
                            {{ $t("app.outbound_transfer_progress_enabled") }}
                        </div>
                        <div class="text-xs text-sem-fg-muted mt-0.5">
                            {{ $t("app.outbound_transfer_progress_enabled_description") }}
                        </div>
                    </label>
                </div>

                <div class="flex items-start gap-3 rounded-xl border border-sem-border px-3 py-2.5">
                    <input
                        id="message-timestamp-grouping"
                        type="checkbox"
                        class="mt-1 rounded-sm border-gray-300 dark:border-zinc-600"
                        :checked="messageTimestampGroupingEnabled"
                        @change="$emit('message-timestamp-grouping-change', $event)"
                    />
                    <label for="message-timestamp-grouping" class="min-w-0 cursor-pointer">
                        <div class="text-sm font-medium text-sem-fg">
                            {{ $t("app.message_timestamp_grouping") }}
                        </div>
                        <div class="text-xs text-sem-fg-muted mt-0.5">
                            {{ $t("app.message_timestamp_grouping_description") }}
                        </div>
                    </label>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div class="space-y-2">
                        <div class="text-sm font-medium text-sem-fg">
                            {{ $t("settings.outbound_bubble_color") }}
                        </div>
                        <div class="flex gap-2">
                            <input
                                :value="bubbleColorInputValue('outbound')"
                                type="color"
                                class="color-fill-input w-12 h-10 rounded-xl border border-sem-border cursor-pointer"
                                @input="onBubbleColorInput('outbound', $event)"
                            />
                            <input
                                :value="bubbleColorInputValue('outbound')"
                                type="text"
                                class="input-field monospace-field flex-1"
                                @input="onBubbleColorInput('outbound', $event)"
                            />
                        </div>
                        <p v-if="isThemeBubbleColor('outbound')" class="text-[11px] text-sem-fg-muted">
                            {{ $t("settings.inbound_bubble_default_hint") }}
                        </p>
                    </div>

                    <div class="space-y-2">
                        <div class="text-sm font-medium text-sem-fg">
                            {{ $t("settings.failed_bubble_color") }}
                        </div>
                        <div class="flex gap-2">
                            <input
                                :value="bubbleColorInputValue('failed')"
                                type="color"
                                class="color-fill-input w-12 h-10 rounded-xl border border-sem-border cursor-pointer"
                                @input="onBubbleColorInput('failed', $event)"
                            />
                            <input
                                :value="bubbleColorInputValue('failed')"
                                type="text"
                                class="input-field monospace-field flex-1"
                                @input="onBubbleColorInput('failed', $event)"
                            />
                        </div>
                        <p v-if="isThemeBubbleColor('failed')" class="text-[11px] text-sem-fg-muted">
                            {{ $t("settings.inbound_bubble_default_hint") }}
                        </p>
                    </div>

                    <div class="space-y-2">
                        <div class="text-sm font-medium text-sem-fg">
                            {{ $t("settings.waiting_bubble_color") }}
                        </div>
                        <div class="flex gap-2">
                            <input
                                :value="bubbleColorInputValue('waiting')"
                                type="color"
                                class="color-fill-input w-12 h-10 rounded-xl border border-sem-border cursor-pointer"
                                @input="onBubbleColorInput('waiting', $event)"
                            />
                            <input
                                :value="bubbleColorInputValue('waiting')"
                                type="text"
                                class="input-field monospace-field flex-1"
                                @input="onBubbleColorInput('waiting', $event)"
                            />
                        </div>
                        <p v-if="isThemeBubbleColor('waiting')" class="text-[11px] text-sem-fg-muted">
                            {{ $t("settings.inbound_bubble_default_hint") }}
                        </p>
                    </div>
                </div>

                <div class="space-y-2">
                    <div class="flex items-center justify-between">
                        <div class="text-sm font-medium text-sem-fg">
                            {{ $t("settings.inbound_bubble_color") }}
                        </div>
                        <button
                            v-if="config.message_inbound_bubble_color"
                            type="button"
                            class="text-[10px] text-red-500 font-bold uppercase hover:underline"
                            @click="onInboundBubbleReset"
                        >
                            {{ $t("settings.inbound_bubble_reset") }}
                        </button>
                    </div>
                    <div class="flex gap-2">
                        <input
                            v-if="config.message_inbound_bubble_color"
                            :value="config.message_inbound_bubble_color"
                            type="color"
                            class="color-fill-input w-12 h-10 rounded-xl border border-sem-border cursor-pointer"
                            @input="onBubbleColorInput('inbound', $event)"
                        />
                        <div
                            v-if="!config.message_inbound_bubble_color"
                            class="flex-1 flex items-center px-3 text-xs text-gray-400 bg-sem-surface-muted rounded-xl border border-dashed border-sem-border italic"
                        >
                            {{ $t("settings.inbound_bubble_default_hint") }}
                            <button
                                type="button"
                                class="ml-2 px-2 py-1 bg-sem-action-primary text-sem-action-primary-text rounded-lg not-italic font-bold"
                                @click="onInboundBubbleCustomize"
                            >
                                {{ $t("settings.inbound_bubble_customize") }}
                            </button>
                        </div>
                        <input
                            v-else
                            :value="config.message_inbound_bubble_color"
                            type="text"
                            class="input-field monospace-field flex-1"
                            @input="onBubbleColorInput('inbound', $event)"
                        />
                    </div>
                </div>
            </div>
        </div>
    </section>
</template>

<script>
import Toggle from "../../forms/Toggle.vue";
import SegmentedControl from "../../forms/SegmentedControl.vue";
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";
import ThemePresetPicker from "../ThemePresetPicker.vue";
import {
    THEME_PRESET_CATALOG,
    buildThemeVariableOverrides,
    normalizeThemePreset,
    resolveEffectiveTheme,
    systemPrefersDark,
} from "../../../theme/themeEngine.js";
import { MESHCHAT_THEME_VARIABLES_DARK, MESHCHAT_THEME_VARIABLES_LIGHT } from "../../../theme/designTokens.js";
import { listNavItems } from "../../../js/registries/navRegistry";
import {
    resolveTopNavItemIds,
    resetTopNavItemIds,
    saveTopNavItemIds,
    topNavLayoutState,
} from "../../../js/appTopNavLayout";

export default {
    name: "AppearanceSettingsSection",
    components: {
        Toggle,
        SegmentedControl,
        MaterialDesignIcon,
        ThemePresetPicker,
    },
    props: {
        visible: {
            type: Boolean,
            default: true,
        },
        config: {
            type: Object,
            required: true,
        },
        detailedOutboundSendStatus: {
            type: Boolean,
            default: false,
        },
        outboundTransferProgressEnabled: {
            type: Boolean,
            default: false,
        },
        messageTimestampGroupingEnabled: {
            type: Boolean,
            default: false,
        },
        messageIconPreviewStyle: {
            type: Object,
            default: () => ({}),
        },
    },
    emits: [
        "update-field",
        "theme-change",
        "theme-preset-change",
        "accent-color-change",
        "custom-canvas-color-change",
        "custom-surface-color-change",
        "messages-sidebar-position-change",
        "app-sidebar-layout-change",
        "message-font-size-change",
        "message-icon-size-change",
        "ui-transparency-change",
        "ui-glass-enabled-change",
        "messages-multi-pane-enabled-change",
        "nomad-tabs-enabled-change",
        "nomad-private-tabs-enabled-change",
        "nomad-history-enabled-change",
        "ui-font-family-change",
        "ui-custom-font-change",
        "rrc-enabled-change",
        "rrc-unread-badges-enabled-change",
        "reset-appearance-defaults",
        "detailed-outbound-send-status-change",
        "outbound-transfer-progress-enabled-change",
        "message-timestamp-grouping-change",
        "bubble-color-change",
    ],
    computed: {
        themePresetCatalog() {
            return THEME_PRESET_CATALOG;
        },
        themeModes() {
            return [
                { value: "light", icon: "weather-sunny", label: "app.light_theme" },
                { value: "dark", icon: "weather-night", label: "app.dark_theme" },
                { value: "system", icon: "monitor", label: "app.system_theme" },
            ];
        },
        fontPreviewStyle() {
            const key = this.config?.ui_font_family || "system";
            if (key === "custom" && this.config?.ui_custom_font_name) {
                const name = String(this.config.ui_custom_font_name).replace(/["\\]/g, "");
                return { fontFamily: `"${name}", ui-sans-serif, system-ui, sans-serif` };
            }
            const stacks = {
                "noto-sans": '"Noto Sans", ui-sans-serif, system-ui, sans-serif',
                "inter": '"Inter", ui-sans-serif, system-ui, sans-serif',
                "jetbrains-mono": '"JetBrains Mono", ui-monospace, monospace',
                "ibm-plex-sans": '"IBM Plex Sans", ui-sans-serif, system-ui, sans-serif',
                "space-grotesk": '"Space Grotesk", ui-sans-serif, system-ui, sans-serif',
                "roboto-mono-nerd": '"Roboto Mono Nerd Font", ui-monospace, monospace',
            };
            return stacks[key] ? { fontFamily: stacks[key] } : {};
        },
        sidebarPositionOptions() {
            return [
                { value: "left", icon: "format-horizontal-align-left", label: "app.messages_sidebar_position_left" },
                {
                    value: "right",
                    icon: "format-horizontal-align-right",
                    label: "app.messages_sidebar_position_right",
                },
            ];
        },
        sidebarLayoutOptions() {
            return [
                { value: "grouped", icon: "view-grid-outline", label: "app.app_sidebar_layout_grouped" },
                { value: "classic", icon: "view-list-outline", label: "app.app_sidebar_layout_classic" },
            ];
        },
        sidebarLayoutValue() {
            const layout = this.config?.app_sidebar_layout;
            return layout === "classic" ? "classic" : "grouped";
        },
        themePresetValue() {
            return normalizeThemePreset(this.config?.theme_preset);
        },
        accentColorInput() {
            return this.config?.accent_color || "#2563eb";
        },
        customCanvasInput() {
            return this.config?.custom_canvas_color || "#f8fafc";
        },
        customSurfaceInput() {
            return this.config?.custom_surface_color || "#ffffff";
        },
        topNavIds() {
            return resolveTopNavItemIds(topNavLayoutState.itemIds);
        },
        topNavEditorRows() {
            const pinnedIds = this.topNavIds;
            const allItems = listNavItems();
            const byId = new Map(allItems.map((item) => [item.id, item]));
            const rows = [];
            for (const id of pinnedIds) {
                const item = byId.get(id);
                if (item) {
                    rows.push({ item, pinned: true, pinnedIndex: rows.length });
                }
            }
            for (const item of allItems) {
                if (!pinnedIds.includes(item.id)) {
                    rows.push({ item, pinned: false, pinnedIndex: -1 });
                }
            }
            return rows;
        },
        topNavPinnedCount() {
            return this.topNavEditorRows.filter((row) => row.pinned).length;
        },
        resolvedBubbleColors() {
            const mode = resolveEffectiveTheme(this.config?.theme, systemPrefersDark());
            const base = mode === "dark" ? MESHCHAT_THEME_VARIABLES_DARK : MESHCHAT_THEME_VARIABLES_LIGHT;
            const resolved = { ...base, ...buildThemeVariableOverrides(this.config, mode) };
            return {
                outbound: resolved["--mc-bubble-outbound"],
                failed: resolved["--mc-bubble-failed"],
                waiting: resolved["--mc-bubble-waiting"],
            };
        },
    },
    methods: {
        emitField(key, value, eventName, eventArg) {
            this.$emit("update-field", { key, value });
            if (eventName) {
                if (eventArg !== undefined) {
                    this.$emit(eventName, eventArg);
                } else {
                    this.$emit(eventName);
                }
            }
        },
        onThemeModeSelect(value) {
            this.emitField("theme", value, "theme-change");
        },
        onThemePresetSelect(event) {
            this.emitField("theme_preset", event.target.value, "theme-preset-change");
        },
        onThemePresetPickerChange(presetId) {
            this.emitField("theme_preset", presetId, "theme-preset-change");
        },
        onAccentColorInput(event) {
            const value = event.target.value || null;
            this.emitField("accent_color", value, "accent-color-change");
        },
        onAccentColorReset() {
            this.emitField("accent_color", null, "accent-color-change");
        },
        onCustomCanvasInput(event) {
            this.emitField("custom_canvas_color", event.target.value || null, "custom-canvas-color-change");
        },
        onCustomSurfaceInput(event) {
            this.emitField("custom_surface_color", event.target.value || null, "custom-surface-color-change");
        },
        onMessagesSidebarPositionSelect(value) {
            this.emitField("messages_sidebar_position", value, "messages-sidebar-position-change");
        },
        onAppSidebarLayoutSelect(value) {
            const next = value === "classic" ? "classic" : "grouped";
            this.emitField("app_sidebar_layout", next, "app-sidebar-layout-change");
        },
        onMessageFontSizeInput(event) {
            this.emitField("message_font_size", Number(event.target.value), "message-font-size-change");
        },
        onMessageIconSizeInput(event) {
            this.emitField("message_icon_size", Number(event.target.value), "message-icon-size-change");
        },
        onUiTransparencyInput(event) {
            this.emitField("ui_transparency", Number(event.target.value), "ui-transparency-change");
        },
        onUiGlassEnabledToggle(value) {
            this.emitField("ui_glass_enabled", value, "ui-glass-enabled-change");
        },
        onFontFamilyChange(event) {
            const value = event.target.value;
            this.emitField("ui_font_family", value, "ui-font-family-change");
        },
        async onFontFileUpload(event) {
            const file = event.target.files?.[0];
            if (!file) return;
            const name = file.name.replace(/\.(woff2|ttf|otf)$/i, "").replace(/["\\]/g, "") || "Custom Font";
            const reader = new FileReader();
            reader.onload = () => {
                const base64 = btoa(
                    new Uint8Array(reader.result).reduce((s, b) => s + String.fromCharCode(b), "")
                );
                this.$emit("ui-custom-font-change", {
                    ui_font_family: "custom",
                    ui_custom_font_name: name,
                    ui_custom_font_data: base64,
                });
            };
            reader.readAsArrayBuffer(file);
            event.target.value = "";
        },
        onMessagesMultiPaneEnabledToggle(value) {
            this.emitField("messages_multi_pane_enabled", value, "messages-multi-pane-enabled-change");
        },
        onNomadTabsEnabledToggle(value) {
            this.emitField("nomad_tabs_enabled", value, "nomad-tabs-enabled-change");
        },
        onNomadPrivateTabsEnabledToggle(value) {
            this.emitField("nomad_private_tabs_enabled", value, "nomad-private-tabs-enabled-change");
        },
        onNomadHistoryEnabledToggle(value) {
            this.emitField("nomad_history_enabled", value, "nomad-history-enabled-change");
        },
        onRrcEnabledToggle(value) {
            this.emitField("rrc_enabled", value, "rrc-enabled-change");
        },
        onRrcUnreadBadgesEnabledToggle(value) {
            this.emitField("rrc_unread_badges_enabled", value, "rrc-unread-badges-enabled-change");
        },
        onBubbleColorInput(type, event) {
            this.emitField(`message_${type}_bubble_color`, event.target.value, "bubble-color-change", type);
        },
        isThemeBubbleColor(type) {
            const raw = this.config?.[`message_${type}_bubble_color`];
            const hex = String(raw ?? "")
                .trim()
                .toLowerCase();
            if (hex === "") {
                return true;
            }
            if (type === "outbound") {
                return hex === "#4f46e5";
            }
            if (type === "failed") {
                return hex === "#ef4444" || hex === "#dc2626";
            }
            if (type === "waiting") {
                return hex === "#e5e7eb" || hex === "#3f3f46";
            }
            return false;
        },
        bubbleColorInputValue(type) {
            if (this.isThemeBubbleColor(type)) {
                return this.resolvedBubbleColors[type] || "#000000";
            }
            return String(this.config?.[`message_${type}_bubble_color`] ?? "").trim();
        },
        onInboundBubbleReset() {
            this.emitField("message_inbound_bubble_color", null, "bubble-color-change", "inbound");
        },
        onInboundBubbleCustomize() {
            this.emitField("message_inbound_bubble_color", "#ffffff", "bubble-color-change", "inbound");
        },
        toggleTopNavItem(id) {
            const ids = [...this.topNavIds];
            const index = ids.indexOf(id);
            if (index >= 0) {
                ids.splice(index, 1);
            } else {
                ids.push(id);
            }
            saveTopNavItemIds(ids);
        },
        moveTopNavItem(id, delta) {
            const ids = [...this.topNavIds];
            const index = ids.indexOf(id);
            const target = index + delta;
            if (index < 0 || target < 0 || target >= ids.length) {
                return;
            }
            ids.splice(index, 1);
            ids.splice(target, 0, id);
            saveTopNavItemIds(ids);
        },
        resetTopNav() {
            resetTopNavItemIds();
        },
    },
};
</script>
