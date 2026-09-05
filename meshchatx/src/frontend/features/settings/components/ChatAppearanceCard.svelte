<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "./Toggle.svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        config: Record<string, any>;
        detailedOutboundSendStatus?: boolean;
        outboundTransferProgressEnabled?: boolean;
        messageTimestampGroupingEnabled?: boolean;
        onupdatefield?: (data: { key: string; value: any }) => void;
        onmessagessidebarpositionchange?: () => void;
        onappsidebarlayoutchange?: () => void;
        onmessagefontsizechange?: () => void;
        onmessageiconsizechange?: () => void;
        onuitransparencychange?: () => void;
        onuiglassenabledchange?: () => void;
        onmessagesmultipaneenabledchange?: () => void;
        onnomadtabsenabledchange?: () => void;
        onrrcenabledchange?: () => void;
        onrrcunreadbadgesenabledchange?: () => void;
        onresetappearancedefaults?: () => void;
        ondetailedoutboundsendstatuschange?: (event: Event) => void;
        onoutboundtransferprogressenabledchange?: (event: Event) => void;
        onmessagetimestampgroupingchange?: (event: Event) => void;
    }

    let {
        config,
        detailedOutboundSendStatus = false,
        outboundTransferProgressEnabled = false,
        messageTimestampGroupingEnabled = false,
        onupdatefield,
        onmessagessidebarpositionchange,
        onappsidebarlayoutchange,
        onmessagefontsizechange,
        onmessageiconsizechange,
        onuitransparencychange,
        onuiglassenabledchange,
        onmessagesmultipaneenabledchange,
        onnomadtabsenabledchange,
        onrrcenabledchange,
        onrrcunreadbadgesenabledchange,
        onresetappearancedefaults,
        ondetailedoutboundsendstatuschange,
        onoutboundtransferprogressenabledchange,
        onmessagetimestampgroupingchange,
    }: Props = $props();

    const sidebarLayoutValue = $derived(config?.app_sidebar_layout === "classic" ? "classic" : "grouped");

    function emitField(key: string, value: any, callback?: () => void) {
        onupdatefield?.({ key, value });
        callback?.();
    }
</script>

<div class="space-y-4">
    <div class="space-y-2">
        <label for="messages-sidebar-position-select" class="text-sm font-medium text-sem-fg block">
            {t("app.messages_sidebar_position")}
        </label>
        <select
            id="messages-sidebar-position-select"
            value={config.messages_sidebar_position}
            class="input-field"
            onchange={(e) =>
                emitField(
                    "messages_sidebar_position",
                    (e.target as HTMLSelectElement).value,
                    onmessagessidebarpositionchange
                )}
        >
            <option value="left">{t("app.messages_sidebar_position_left")}</option>
            <option value="right">{t("app.messages_sidebar_position_right")}</option>
        </select>
    </div>

    <div class="space-y-2">
        <label for="app-sidebar-layout-select" class="text-sm font-medium text-sem-fg block">
            {t("app.app_sidebar_layout")}
        </label>
        <select
            id="app-sidebar-layout-select"
            value={sidebarLayoutValue}
            class="input-field"
            onchange={(e) =>
                emitField("app_sidebar_layout", (e.target as HTMLSelectElement).value, onappsidebarlayoutchange)}
        >
            <option value="grouped">{t("app.app_sidebar_layout_grouped")}</option>
            <option value="classic">{t("app.app_sidebar_layout_classic")}</option>
        </select>
        <p class="text-xs text-sem-fg-muted">{t("app.app_sidebar_layout_description")}</p>
    </div>

    <div class="space-y-2">
        <label for="message-font-size-input" class="text-sm font-medium text-sem-fg block">
            {t("app.message_font_size")} ({config.message_font_size || 14}px)
        </label>
        <div class="flex items-center gap-3">
            <span class="text-xs text-gray-400">10</span>
            <input
                id="message-font-size-input"
                value={config.message_font_size}
                type="range"
                min="10"
                max="24"
                step="1"
                class="flex-1"
                oninput={(e) =>
                    emitField(
                        "message_font_size",
                        Number((e.target as HTMLInputElement).value),
                        onmessagefontsizechange
                    )}
            />
            <span class="text-xs text-gray-400">24</span>
        </div>
        <div class="text-xs text-gray-600 dark:text-gray-400">{t("app.message_font_size_description")}</div>
    </div>

    <div class="space-y-2">
        <label for="message-icon-size-input" class="text-sm font-medium text-sem-fg block">
            {t("app.message_icon_size")} ({config.message_icon_size || 28}px)
        </label>
        <div class="flex items-center gap-3">
            <span class="text-xs text-gray-400">16</span>
            <input
                id="message-icon-size-input"
                value={config.message_icon_size}
                type="range"
                min="16"
                max="64"
                step="2"
                class="flex-1"
                oninput={(e) =>
                    emitField(
                        "message_icon_size",
                        Number((e.target as HTMLInputElement).value),
                        onmessageiconsizechange
                    )}
            />
            <span class="text-xs text-gray-400">64</span>
        </div>
        <div class="text-xs text-gray-600 dark:text-gray-400">{t("app.message_icon_size_description")}</div>
    </div>

    <div class="space-y-2">
        <label for="ui-transparency-input" class="text-sm font-medium text-sem-fg block">
            {t("app.ui_transparency")} ({config.ui_transparency || 0}%)
        </label>
        <div class="flex items-center gap-3">
            <span class="text-xs text-gray-400">0</span>
            <input
                id="ui-transparency-input"
                value={config.ui_transparency}
                type="range"
                min="0"
                max="100"
                step="5"
                class="flex-1"
                oninput={(e) =>
                    emitField("ui_transparency", Number((e.target as HTMLInputElement).value), onuitransparencychange)}
            />
            <span class="text-xs text-gray-400">100</span>
        </div>
        <div class="text-xs text-gray-600 dark:text-gray-400">{t("app.ui_transparency_description")}</div>
    </div>

    <label class="setting-toggle">
        <Toggle
            id="ui-glass-enabled"
            checked={Boolean(config.ui_glass_enabled)}
            onchange={(val) => emitField("ui_glass_enabled", val, onuiglassenabledchange)}
        />
        <span class="setting-toggle__label">
            <span class="setting-toggle__title">{t("app.ui_glass_enabled")}</span>
            <span class="setting-toggle__description">{t("app.ui_glass_enabled_description")}</span>
        </span>
    </label>

    <label class="setting-toggle">
        <Toggle
            id="messages-multi-pane-enabled"
            checked={Boolean(config.messages_multi_pane_enabled)}
            onchange={(val) => emitField("messages_multi_pane_enabled", val, onmessagesmultipaneenabledchange)}
        />
        <span class="setting-toggle__label">
            <span class="setting-toggle__title">{t("app.messages_multi_pane_enabled")}</span>
            <span class="setting-toggle__description">{t("app.messages_multi_pane_enabled_description")}</span>
        </span>
    </label>

    <label class="setting-toggle">
        <Toggle
            id="nomad-tabs-enabled"
            checked={Boolean(config.nomad_tabs_enabled)}
            onchange={(val) => emitField("nomad_tabs_enabled", val, onnomadtabsenabledchange)}
        />
        <span class="setting-toggle__label">
            <span class="setting-toggle__title">{t("app.nomad_tabs_enabled")}</span>
            <span class="setting-toggle__description">{t("app.nomad_tabs_enabled_description")}</span>
        </span>
    </label>

    <label class="setting-toggle">
        <Toggle
            id="rrc-enabled"
            checked={Boolean(config.rrc_enabled)}
            onchange={(val) => emitField("rrc_enabled", val, onrrcenabledchange)}
        />
        <span class="setting-toggle__label">
            <span class="setting-toggle__title">{t("app.rrc_enabled")}</span>
            <span class="setting-toggle__description">{t("app.rrc_enabled_description")}</span>
        </span>
    </label>

    {#if config.rrc_enabled}
        <label class="setting-toggle">
            <Toggle
                id="rrc-unread-badges"
                checked={Boolean(config.rrc_unread_badges_enabled)}
                onchange={(val) => emitField("rrc_unread_badges_enabled", val, onrrcunreadbadgesenabledchange)}
            />
            <span class="setting-toggle__label">
                <span class="setting-toggle__title">{t("app.rrc_unread_badges_enabled")}</span>
                <span class="setting-toggle__description">{t("app.rrc_unread_badges_enabled_description")}</span>
            </span>
        </label>
    {/if}

    <div class="pt-1">
        <button
            type="button"
            class="p-0 border-0 bg-transparent text-sm font-medium text-sem-accent hover:underline cursor-pointer"
            onclick={onresetappearancedefaults}
        >
            {t("app.reset_appearance_defaults")}
        </button>
    </div>

    <div class="space-y-4 pt-2">
        <div class="text-sm font-bold text-sem-fg-muted uppercase tracking-wider">Message Bubbles</div>

        <div class="flex items-start gap-3 rounded-xl border border-sem-border px-3 py-2.5">
            <input
                id="detailed-outbound-send-status"
                type="checkbox"
                class="mt-1 rounded-sm border-gray-300 dark:border-zinc-600"
                checked={detailedOutboundSendStatus}
                onchange={ondetailedoutboundsendstatuschange}
            />
            <label for="detailed-outbound-send-status" class="min-w-0 cursor-pointer">
                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {t("app.detailed_outbound_send_status")}
                </div>
                <div class="text-xs text-sem-fg-muted mt-0.5">
                    {t("app.detailed_outbound_send_status_description")}
                </div>
            </label>
        </div>

        <div class="flex items-start gap-3 rounded-xl border border-sem-border px-3 py-2.5">
            <input
                id="outbound-transfer-progress-enabled"
                type="checkbox"
                class="mt-1 rounded-sm border-gray-300 dark:border-zinc-600"
                checked={outboundTransferProgressEnabled}
                onchange={onoutboundtransferprogressenabledchange}
            />
            <label for="outbound-transfer-progress-enabled" class="min-w-0 cursor-pointer">
                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {t("app.outbound_transfer_progress_enabled")}
                </div>
                <div class="text-xs text-sem-fg-muted mt-0.5">
                    {t("app.outbound_transfer_progress_enabled_description")}
                </div>
            </label>
        </div>

        <div class="flex items-start gap-3 rounded-xl border border-sem-border px-3 py-2.5">
            <input
                id="message-timestamp-grouping-enabled"
                type="checkbox"
                class="mt-1 rounded-sm border-gray-300 dark:border-zinc-600"
                checked={messageTimestampGroupingEnabled}
                onchange={onmessagetimestampgroupingchange}
            />
            <label for="message-timestamp-grouping-enabled" class="min-w-0 cursor-pointer">
                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {t("app.message_timestamp_grouping_enabled")}
                </div>
                <div class="text-xs text-sem-fg-muted mt-0.5">
                    {t("app.message_timestamp_grouping_enabled_description")}
                </div>
            </label>
        </div>
    </div>
</div>
