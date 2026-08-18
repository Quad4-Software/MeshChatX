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
                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {{ $t("app.theme") }}
                </div>
                <select :value="config.theme" class="input-field" @change="onThemeSelect">
                    <option value="light">{{ $t("app.light_theme") }}</option>
                    <option value="dark">{{ $t("app.dark_theme") }}</option>
                </select>
            </div>

            <div class="space-y-2">
                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {{ $t("app.messages_sidebar_position") }}
                </div>
                <select
                    :value="config.messages_sidebar_position"
                    class="input-field"
                    @change="onMessagesSidebarPositionSelect"
                >
                    <option value="left">{{ $t("app.messages_sidebar_position_left") }}</option>
                    <option value="right">{{ $t("app.messages_sidebar_position_right") }}</option>
                </select>
            </div>

            <div class="space-y-2">
                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {{ $t("app.app_sidebar_layout") }}
                </div>
                <select :value="sidebarLayoutValue" class="input-field" @change="onAppSidebarLayoutSelect">
                    <option value="grouped">{{ $t("app.app_sidebar_layout_grouped") }}</option>
                    <option value="classic">{{ $t("app.app_sidebar_layout_classic") }}</option>
                </select>
                <p class="text-xs text-gray-600 dark:text-gray-400">
                    {{ $t("app.app_sidebar_layout_description") }}
                </p>
            </div>

            <div class="space-y-2">
                <div class="flex items-center justify-between">
                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {{ $t("app.message_font_size") }}
                    </div>
                    <div class="text-xs font-mono text-blue-500 dark:text-blue-400">
                        {{ config.message_font_size || 14 }}px
                    </div>
                </div>
                <div class="flex items-center gap-3">
                    <span class="text-xs text-gray-400">A</span>
                    <input
                        :value="config.message_font_size"
                        type="range"
                        min="10"
                        max="32"
                        step="1"
                        class="flex-1 h-1.5 bg-gray-200 dark:bg-zinc-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                        @input="onMessageFontSizeInput"
                    />
                    <span class="text-lg text-gray-400">A</span>
                </div>
            </div>

            <div class="space-y-2">
                <div class="flex items-center justify-between">
                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {{ $t("app.message_icon_size") }}
                    </div>
                    <div class="text-xs font-mono text-blue-500 dark:text-blue-400">
                        {{ config.message_icon_size || 28 }}px
                    </div>
                </div>
                <div class="flex items-center gap-3">
                    <MaterialDesignIcon
                        icon-name="account-outline"
                        class="shrink-0 text-gray-400"
                        :style="{ width: '16px', height: '16px' }"
                    />
                    <input
                        :value="config.message_icon_size"
                        type="range"
                        min="16"
                        max="64"
                        step="1"
                        class="flex-1 h-1.5 bg-gray-200 dark:bg-zinc-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                        @input="onMessageIconSizeInput"
                    />
                    <MaterialDesignIcon
                        icon-name="account"
                        class="shrink-0 text-gray-500 dark:text-gray-300"
                        :style="messageIconPreviewStyle"
                    />
                </div>
            </div>

            <div class="space-y-2">
                <div class="flex items-center justify-between">
                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {{ $t("app.ui_transparency") }}
                    </div>
                    <div class="text-xs font-mono text-blue-500 dark:text-blue-400">
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
                        class="flex-1 h-1.5 bg-gray-200 dark:bg-zinc-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                        @input="onUiTransparencyInput"
                    />
                    <span class="text-xs text-gray-400">100</span>
                </div>
                <div class="text-xs text-gray-600 dark:text-gray-400">
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

            <label class="setting-toggle">
                <Toggle id="rrc-enabled" :model-value="config.rrc_enabled" @update:model-value="onRrcEnabledToggle" />
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
                    class="p-0 border-0 bg-transparent text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline cursor-pointer"
                    @click="$emit('reset-appearance-defaults')"
                >
                    {{ $t("app.reset_appearance_defaults") }}
                </button>
            </div>

            <div class="space-y-4 pt-2">
                <div class="text-sm font-bold text-gray-400 dark:text-zinc-500 uppercase tracking-wider">
                    Message Bubbles
                </div>

                <div class="flex items-start gap-3 rounded-xl border border-gray-200 dark:border-zinc-700 px-3 py-2.5">
                    <input
                        id="detailed-outbound-send-status"
                        type="checkbox"
                        class="mt-1 rounded-sm border-gray-300 dark:border-zinc-600"
                        :checked="detailedOutboundSendStatus"
                        @change="$emit('detailed-outbound-send-status-change', $event)"
                    />
                    <label for="detailed-outbound-send-status" class="min-w-0 cursor-pointer">
                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                            {{ $t("app.detailed_outbound_send_status") }}
                        </div>
                        <div class="text-xs text-gray-500 dark:text-zinc-400 mt-0.5">
                            {{ $t("app.detailed_outbound_send_status_description") }}
                        </div>
                    </label>
                </div>

                <div class="flex items-start gap-3 rounded-xl border border-gray-200 dark:border-zinc-700 px-3 py-2.5">
                    <input
                        id="outbound-transfer-progress-enabled"
                        type="checkbox"
                        class="mt-1 rounded-sm border-gray-300 dark:border-zinc-600"
                        :checked="outboundTransferProgressEnabled"
                        @change="$emit('outbound-transfer-progress-enabled-change', $event)"
                    />
                    <label for="outbound-transfer-progress-enabled" class="min-w-0 cursor-pointer">
                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                            {{ $t("app.outbound_transfer_progress_enabled") }}
                        </div>
                        <div class="text-xs text-gray-500 dark:text-zinc-400 mt-0.5">
                            {{ $t("app.outbound_transfer_progress_enabled_description") }}
                        </div>
                    </label>
                </div>

                <div class="flex items-start gap-3 rounded-xl border border-gray-200 dark:border-zinc-700 px-3 py-2.5">
                    <input
                        id="message-timestamp-grouping"
                        type="checkbox"
                        class="mt-1 rounded-sm border-gray-300 dark:border-zinc-600"
                        :checked="messageTimestampGroupingEnabled"
                        @change="$emit('message-timestamp-grouping-change', $event)"
                    />
                    <label for="message-timestamp-grouping" class="min-w-0 cursor-pointer">
                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                            {{ $t("app.message_timestamp_grouping") }}
                        </div>
                        <div class="text-xs text-gray-500 dark:text-zinc-400 mt-0.5">
                            {{ $t("app.message_timestamp_grouping_description") }}
                        </div>
                    </label>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div class="space-y-2">
                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                            {{ $t("settings.outbound_bubble_color") }}
                        </div>
                        <div class="flex gap-2">
                            <input
                                :value="config.message_outbound_bubble_color"
                                type="color"
                                class="color-fill-input w-12 h-10 rounded-xl border border-gray-200 dark:border-zinc-700 cursor-pointer"
                                @input="onBubbleColorInput('outbound', $event)"
                            />
                            <input
                                :value="config.message_outbound_bubble_color"
                                type="text"
                                class="input-field monospace-field flex-1"
                                @input="onBubbleColorInput('outbound', $event)"
                            />
                        </div>
                    </div>

                    <div class="space-y-2">
                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                            {{ $t("settings.failed_bubble_color") }}
                        </div>
                        <div class="flex gap-2">
                            <input
                                :value="config.message_failed_bubble_color"
                                type="color"
                                class="color-fill-input w-12 h-10 rounded-xl border border-gray-200 dark:border-zinc-700 cursor-pointer"
                                @input="onBubbleColorInput('failed', $event)"
                            />
                            <input
                                :value="config.message_failed_bubble_color"
                                type="text"
                                class="input-field monospace-field flex-1"
                                @input="onBubbleColorInput('failed', $event)"
                            />
                        </div>
                    </div>

                    <div class="space-y-2">
                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                            {{ $t("settings.waiting_bubble_color") }}
                        </div>
                        <div class="flex gap-2">
                            <input
                                :value="config.message_waiting_bubble_color"
                                type="color"
                                class="color-fill-input w-12 h-10 rounded-xl border border-gray-200 dark:border-zinc-700 cursor-pointer"
                                @input="onBubbleColorInput('waiting', $event)"
                            />
                            <input
                                :value="config.message_waiting_bubble_color"
                                type="text"
                                class="input-field monospace-field flex-1"
                                @input="onBubbleColorInput('waiting', $event)"
                            />
                        </div>
                    </div>
                </div>

                <div class="space-y-2">
                    <div class="flex items-center justify-between">
                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
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
                            class="color-fill-input w-12 h-10 rounded-xl border border-gray-200 dark:border-zinc-700 cursor-pointer"
                            @input="onBubbleColorInput('inbound', $event)"
                        />
                        <div
                            v-if="!config.message_inbound_bubble_color"
                            class="flex-1 flex items-center px-3 text-xs text-gray-400 bg-gray-50 dark:bg-zinc-900 rounded-xl border border-dashed border-gray-200 dark:border-zinc-800 italic"
                        >
                            {{ $t("settings.inbound_bubble_default_hint") }}
                            <button
                                type="button"
                                class="ml-2 px-2 py-1 bg-blue-500 text-white rounded-lg not-italic font-bold"
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
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";

export default {
    name: "AppearanceSettingsSection",
    components: {
        Toggle,
        MaterialDesignIcon,
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
        "messages-sidebar-position-change",
        "app-sidebar-layout-change",
        "message-font-size-change",
        "message-icon-size-change",
        "ui-transparency-change",
        "ui-glass-enabled-change",
        "messages-multi-pane-enabled-change",
        "nomad-tabs-enabled-change",
        "rrc-enabled-change",
        "rrc-unread-badges-enabled-change",
        "reset-appearance-defaults",
        "detailed-outbound-send-status-change",
        "outbound-transfer-progress-enabled-change",
        "message-timestamp-grouping-change",
        "bubble-color-change",
    ],
    computed: {
        sidebarLayoutValue() {
            const layout = this.config?.app_sidebar_layout;
            return layout === "classic" ? "classic" : "grouped";
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
        onThemeSelect(event) {
            this.emitField("theme", event.target.value, "theme-change");
        },
        onMessagesSidebarPositionSelect(event) {
            this.emitField("messages_sidebar_position", event.target.value, "messages-sidebar-position-change");
        },
        onAppSidebarLayoutSelect(event) {
            const value = event.target.value === "classic" ? "classic" : "grouped";
            this.emitField("app_sidebar_layout", value, "app-sidebar-layout-change");
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
        onMessagesMultiPaneEnabledToggle(value) {
            this.emitField("messages_multi_pane_enabled", value, "messages-multi-pane-enabled-change");
        },
        onNomadTabsEnabledToggle(value) {
            this.emitField("nomad_tabs_enabled", value, "nomad-tabs-enabled-change");
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
        onInboundBubbleReset() {
            this.emitField("message_inbound_bubble_color", null, "bubble-color-change", "inbound");
        },
        onInboundBubbleCustomize() {
            this.emitField("message_inbound_bubble_color", "#ffffff", "bubble-color-change", "inbound");
        },
    },
};
</script>
