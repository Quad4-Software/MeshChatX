<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "../Toggle.svelte";
    import { t } from "../../../../js/i18n.js";

    interface Props {
        visible?: boolean;
        config?: Record<string, any>;
        inboundStampsEnabled?: boolean;
        onupdatefield?: (data: { key: string; value: any }) => void;
        oninboundstampschange?: (val: boolean) => void;
    }

    let {
        visible = true,
        config = {},
        inboundStampsEnabled = false,
        onupdatefield,
        oninboundstampschange,
    }: Props = $props();

    function emitToggle(key: string, value: boolean) {
        onupdatefield?.({ key, value });
    }

    function emitNumber(key: string, value: string) {
        const num = Number(value);
        if (!Number.isNaN(num)) {
            onupdatefield?.({ key, value: num });
        }
    }
</script>

{#if visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">{t("app.lxmf_settings_eyebrow")}</div>
                <h2>{t("app.messages")}</h2>
                <p>{t("app.messages_description")}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-3">
            <label class="setting-toggle">
                <Toggle
                    id="delivery-helptips-enabled"
                    checked={Boolean(config.delivery_helptips_enabled)}
                    onchange={(val) => emitToggle("delivery_helptips_enabled", val)}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("app.delivery_helptips_enabled")}</span>
                    <span class="setting-toggle__description">
                        {t("app.delivery_helptips_enabled_description")}
                    </span>
                </span>
            </label>

            <label class="setting-toggle">
                <Toggle
                    id="auto-resend-failed"
                    checked={Boolean(config.auto_resend_failed_messages_when_announce_received)}
                    onchange={(val) => emitToggle("auto_resend_failed_messages_when_announce_received", val)}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("app.auto_resend_title")}</span>
                    <span class="setting-toggle__description">{t("app.auto_resend_description")}</span>
                </span>
            </label>

            <label class="setting-toggle">
                <Toggle
                    id="allow-retries-attachments"
                    checked={Boolean(config.allow_auto_resending_failed_messages_with_attachments)}
                    onchange={(val) => emitToggle("allow_auto_resending_failed_messages_with_attachments", val)}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("app.retry_attachments_title")}</span>
                    <span class="setting-toggle__description">{t("app.retry_attachments_description")}</span>
                </span>
            </label>

            <label class="setting-toggle">
                <Toggle
                    id="auto-fallback-propagation"
                    checked={Boolean(config.auto_send_failed_messages_to_propagation_node)}
                    onchange={(val) => emitToggle("auto_send_failed_messages_to_propagation_node", val)}
                />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("app.auto_fallback_title")}</span>
                    <span class="setting-toggle__description">{t("app.auto_fallback_description")}</span>
                </span>
            </label>

            <label class="setting-toggle">
                <Toggle id="inbound-stamps-required" checked={inboundStampsEnabled} onchange={oninboundstampschange} />
                <span class="setting-toggle__label">
                    <span class="setting-toggle__title">{t("app.inbound_stamps_required_title")}</span>
                    <span class="setting-toggle__description">{t("app.inbound_stamps_required_description")}</span>
                </span>
            </label>

            {#if inboundStampsEnabled}
                <div class="space-y-2">
                    <label for="lxmf-inbound-stamp-cost" class="text-sm font-medium text-sem-fg block">
                        {t("app.inbound_stamp_cost")}
                    </label>
                    <input
                        id="lxmf-inbound-stamp-cost"
                        value={config.lxmf_inbound_stamp_cost}
                        type="number"
                        min="1"
                        max="254"
                        placeholder="8"
                        class="input-field"
                        oninput={(e) => emitNumber("lxmf_inbound_stamp_cost", (e.target as HTMLInputElement).value)}
                    />
                    <div class="text-xs text-sem-fg-muted">
                        {t("app.inbound_stamp_description")}
                    </div>
                </div>
            {/if}

            <hr class="border-gray-200 dark:border-gray-700" />

            <div>
                <div class="text-sm font-medium text-sem-fg mb-1">
                    {t("app.flood_protection")}
                </div>
                <div class="text-xs text-sem-fg-muted mb-3">
                    {t("app.flood_protection_description")}
                </div>
                <label class="setting-toggle">
                    <Toggle
                        id="lxmf-flood-protection"
                        checked={Boolean(config.lxmf_flood_protection_enabled)}
                        onchange={(val) => emitToggle("lxmf_flood_protection_enabled", val)}
                    />
                    <span class="setting-toggle__label">
                        <span class="setting-toggle__title">{t("app.flood_protection_enabled")}</span>
                    </span>
                </label>
                {#if config.lxmf_flood_protection_enabled}
                    <div class="space-y-3 mt-2">
                        <div class="space-y-2">
                            <label for="lxmf-flood-threshold" class="text-sm font-medium text-sem-fg block">
                                {t("app.flood_threshold")}
                            </label>
                            <input
                                id="lxmf-flood-threshold"
                                value={config.lxmf_flood_threshold_per_minute}
                                type="number"
                                min="1"
                                max="1000"
                                placeholder="30"
                                class="input-field"
                                oninput={(e) =>
                                    emitNumber("lxmf_flood_threshold_per_minute", (e.target as HTMLInputElement).value)}
                            />
                        </div>
                        <div class="space-y-2">
                            <label for="lxmf-flood-max-stamp" class="text-sm font-medium text-sem-fg block">
                                {t("app.flood_max_stamp_cost")}
                            </label>
                            <input
                                id="lxmf-flood-max-stamp"
                                value={config.lxmf_flood_max_stamp_cost}
                                type="number"
                                min="1"
                                max="254"
                                placeholder="24"
                                class="input-field"
                                oninput={(e) =>
                                    emitNumber("lxmf_flood_max_stamp_cost", (e.target as HTMLInputElement).value)}
                            />
                        </div>
                        <div class="space-y-2">
                            <label for="lxmf-flood-cooldown" class="text-sm font-medium text-sem-fg block">
                                {t("app.flood_cooldown")}
                            </label>
                            <input
                                id="lxmf-flood-cooldown"
                                value={config.lxmf_flood_cooldown_seconds}
                                type="number"
                                min="30"
                                max="3600"
                                placeholder="300"
                                class="input-field"
                                oninput={(e) =>
                                    emitNumber("lxmf_flood_cooldown_seconds", (e.target as HTMLInputElement).value)}
                            />
                        </div>
                    </div>
                {/if}
            </div>
        </div>
    </section>
{/if}
