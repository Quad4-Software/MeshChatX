<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import SettingsSectionBlock from "../SettingsSectionBlock.svelte";
    import Toggle from "../Toggle.svelte";
    import MaterialDesignIcon from "../../../../ui/svelte/MaterialDesignIcon.svelte";
    import DialogUtils from "../../../../js/DialogUtils.js";
    import ToastUtils from "../../../../js/ToastUtils.js";
    import { t } from "../../../../js/i18n.js";

    interface Props {
        visible?: boolean;
        config?: Record<string, any>;
        reticulumInstance?: Record<string, any>;
        reticulumInstanceSaving?: boolean;
        showWindowsScreenSecurity?: boolean;
        screenSecurityEnabled?: boolean;
        screenSecuritySaving?: boolean;
        trustedTelemetryPeers?: Array<{ id: string | number; name: string; remote_identity_hash: string }>;
        onupdatefield?: (data: { key: string; value: any }) => void;
        onupdatereticuluminstance?: (patch: Record<string, any>) => void;
        onscreensecuritychange?: (val: boolean) => void;
        onrevoketelemetrypeer?: (peer: any) => void;
    }

    let {
        visible = true,
        config = {},
        reticulumInstance = {},
        reticulumInstanceSaving = false,
        showWindowsScreenSecurity = false,
        screenSecurityEnabled = $bindable(false),
        screenSecuritySaving = false,
        trustedTelemetryPeers = [],
        onupdatefield,
        onupdatereticuluminstance,
        onscreensecuritychange,
        onrevoketelemetrypeer,
    }: Props = $props();

    function emitToggle(key: string, value: boolean) {
        onupdatefield?.({ key, value });
    }

    function emitValue(key: string, value: any) {
        onupdatefield?.({ key, value });
    }
</script>

<SettingsSectionBlock
    show={visible}
    eyebrow={t("app.privacy_eyebrow")}
    title={t("app.privacy_data_title")}
    description={t("app.privacy_data_description")}
    bodyClass="space-y-4"
>
    <div class="space-y-3">
        <div class="text-[11px] font-semibold uppercase tracking-wider text-sem-fg-muted">
            {t("app.privacy_subsection_device")}
        </div>
        <label class="setting-toggle">
            <Toggle
                id="local-message-auto-delete"
                checked={Boolean(config.local_message_auto_delete_enabled)}
                onchange={(val) => emitToggle("local_message_auto_delete_enabled", val)}
            />
            <span class="setting-toggle__label">
                <span class="setting-toggle__title">
                    {t("app.local_message_auto_delete_title")}
                </span>
                <span class="setting-toggle__description">
                    {t("app.local_message_auto_delete_description")}
                </span>
            </span>
        </label>
        {#if config.local_message_auto_delete_enabled}
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pl-0 sm:pl-1">
                <div class="space-y-1">
                    <label for="local-msg-auto-delete-val" class="text-sm font-medium text-sem-fg block">
                        {t("app.local_message_auto_delete_age")}
                    </label>
                    <div class="flex flex-wrap items-center gap-2">
                        <input
                            id="local-msg-auto-delete-val"
                            value={config.local_message_auto_delete_value}
                            type="number"
                            min="1"
                            max={config.local_message_auto_delete_unit === "months" ? 120 : 10000}
                            class="input-field w-24"
                            aria-label={t("app.local_message_auto_delete_age")}
                            oninput={(e) =>
                                emitValue(
                                    "local_message_auto_delete_value",
                                    Number((e.target as HTMLInputElement).value)
                                )}
                        />
                        <select
                            value={config.local_message_auto_delete_unit}
                            class="input-field min-w-[7rem]"
                            aria-label={t("app.local_message_auto_delete_unit_aria")}
                            onchange={(e) =>
                                emitValue("local_message_auto_delete_unit", (e.target as HTMLSelectElement).value)}
                        >
                            <option value="days">
                                {t("app.local_message_auto_delete_unit_days")}
                            </option>
                            <option value="months">
                                {t("app.local_message_auto_delete_unit_months")}
                            </option>
                        </select>
                    </div>
                    <div class="text-xs text-sem-fg-muted">
                        {t("app.local_message_auto_delete_month_note")}
                    </div>
                </div>
            </div>
        {/if}
    </div>

    <div class="border-t border-sem-border pt-4 space-y-3">
        <div class="text-[11px] font-semibold uppercase tracking-wider text-sem-fg-muted">
            {t("app.privacy_eyebrow")}
        </div>
        {#if showWindowsScreenSecurity}
            <div
                class="p-4 rounded-2xl border border-amber-200 dark:border-amber-900/40 bg-amber-50/80 dark:bg-amber-950/30 space-y-3"
            >
                <div class="text-xs font-semibold uppercase tracking-wider text-amber-800 dark:text-amber-200">
                    {t("app.screen_security_drm_eyebrow")}
                </div>
                <label class="setting-toggle">
                    <Toggle
                        id="screen-security-enabled"
                        bind:checked={screenSecurityEnabled}
                        disabled={screenSecuritySaving}
                        onchange={onscreensecuritychange}
                    />
                    <span class="setting-toggle__label">
                        <span class="setting-toggle__title">
                            {t("app.screen_security_enabled")}
                        </span>
                        <span class="setting-toggle__description">
                            {t("app.screen_security_description")}
                        </span>
                    </span>
                </label>
                <p class="text-xs text-amber-900/80 dark:text-amber-100/80">
                    {t("app.screen_security_drm_note")}
                </p>
            </div>
        {/if}
        <label class="setting-toggle">
            <Toggle
                id="privacy-mode-enabled"
                checked={Boolean(config.privacy_mode_enabled)}
                onchange={(val) => emitToggle("privacy_mode_enabled", val)}
            />
            <span class="setting-toggle__label">
                <span class="setting-toggle__title">{t("app.privacy_mode_enabled")}</span>
                <span class="setting-toggle__description">{t("app.privacy_mode_description")}</span>
            </span>
        </label>

        <label class="setting-toggle">
            <Toggle
                id="multi-session-warning-enabled"
                checked={Boolean(config.multi_session_warning_enabled)}
                onchange={(val) => emitToggle("multi_session_warning_enabled", val)}
            />
            <span class="setting-toggle__label">
                <span class="setting-toggle__title">
                    {t("app.multi_session_warning_enabled")}
                </span>
                <span class="setting-toggle__description">
                    {t("app.multi_session_warning_description")}
                </span>
            </span>
        </label>

        <label class="setting-toggle">
            <Toggle
                id="obfuscate-hops"
                checked={Boolean(reticulumInstance.local_hops_delta)}
                disabled={reticulumInstanceSaving}
                onchange={(val) => onupdatereticuluminstance?.({ local_hops_delta: val })}
            />
            <span class="setting-toggle__label">
                <span class="setting-toggle__title">{t("app.obfuscate_hops")}</span>
                <span class="setting-toggle__description">{t("app.obfuscate_hops_description")}</span>
            </span>
        </label>
    </div>

    <div class="border-t border-sem-border pt-4 space-y-4">
        <div class="text-[11px] font-semibold uppercase tracking-wider text-sem-fg-muted">
            {t("app.privacy_subsection_telemetry")}
        </div>
        <label class="setting-toggle">
            <Toggle
                id="telemetry-enabled"
                checked={Boolean(config.telemetry_enabled)}
                onchange={(val) => emitToggle("telemetry_enabled", val)}
            />
            <span class="setting-toggle__label">
                <span class="setting-toggle__title">{t("app.telemetry_enabled")}</span>
                <span class="setting-toggle__description">{t("app.telemetry_description")}</span>
            </span>
        </label>
        {#if config.telemetry_enabled}
            <div class="space-y-4">
                <div class="text-sm font-medium text-sem-fg">
                    {t("app.telemetry_trusted_peers")}
                </div>
                {#if trustedTelemetryPeers.length === 0}
                    <div class="text-xs text-sem-fg-muted italic">
                        {t("app.telemetry_no_trusted_peers")}
                    </div>
                {:else}
                    <div class="space-y-2">
                        {#each trustedTelemetryPeers as peer (peer.id)}
                            <div
                                class="flex items-center justify-between p-2 rounded-xl bg-sem-surface-muted border border-sem-border"
                            >
                                <div class="flex items-center gap-3">
                                    <div
                                        class="size-8 rounded-full bg-sem-surface-muted text-blue-500 flex items-center justify-center"
                                    >
                                        <MaterialDesignIcon iconName="account" class="size-5" />
                                    </div>
                                    <div class="min-w-0">
                                        <div class="text-sm font-bold text-sem-fg truncate">
                                            {peer.name}
                                        </div>
                                        <div class="text-[10px] text-sem-fg-muted font-mono truncate">
                                            {peer.remote_identity_hash}
                                        </div>
                                    </div>
                                </div>
                                <button
                                    type="button"
                                    class="p-2 text-sem-fg-muted hover:text-red-500 transition-colors cursor-pointer"
                                    title={t("app.telemetry_revoke_trust")}
                                    onclick={() => onrevoketelemetrypeer?.(peer)}
                                >
                                    <MaterialDesignIcon iconName="shield-off-outline" class="size-5" />
                                </button>
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>
        {/if}
    </div>
</SettingsSectionBlock>
