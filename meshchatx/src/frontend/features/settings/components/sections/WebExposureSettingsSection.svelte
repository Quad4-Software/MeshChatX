<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../../js/i18n.js";

    interface Props {
        visible?: boolean;
        serverSecurity?: {
            listen_host?: string;
            listen_port?: number;
            https_enabled?: boolean;
            landlock_requested?: boolean;
            landlock_active?: boolean;
            landlock_auto_enabled?: boolean;
            landlock_kernel_supported?: boolean;
            landlock_disabled_by_env?: boolean;
            appcontainer_requested?: boolean;
            appcontainer_active?: boolean;
            appcontainer_auto_enabled?: boolean;
            appcontainer_supported?: boolean;
            appcontainer_disabled_by_env?: boolean;
            seccomp_requested?: boolean;
            seccomp_active?: boolean;
            seccomp_auto_enabled?: boolean;
            seccomp_kernel_supported?: boolean;
            seccomp_disabled_by_env?: boolean;
            is_loopback_bind?: boolean;
            auth_enabled?: boolean;
            web_ui_ip_allowlist?: string;
            [k: string]: any;
        };
        exposureAckFirewall?: boolean;
        exposureAckVpn?: boolean;
        onackfirewallchange?: (val: boolean) => void;
        onackvpnchange?: (val: boolean) => void;
        onallowlistchange?: (val: string) => void;
    }

    let {
        visible = true,
        serverSecurity = {},
        exposureAckFirewall = false,
        exposureAckVpn = false,
        onackfirewallchange,
        onackvpnchange,
        onallowlistchange,
    }: Props = $props();
</script>

{#if visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">Security</div>
                <h2>{t("app.web_exposure_title")}</h2>
                <p>{t("app.web_exposure_description")}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                <div>
                    <div class="text-sem-fg-muted">
                        {t("app.web_listen_address")}
                    </div>
                    <div class="font-mono text-sem-fg">
                        {serverSecurity.listen_host || "-"}:{serverSecurity.listen_port ?? "-"}
                    </div>
                </div>
                <div>
                    <div class="text-sem-fg-muted">
                        {t("app.web_listen_https")}
                    </div>
                    <div class="text-sem-fg">
                        {serverSecurity.https_enabled ? t("app.enabled") : t("app.disabled")}
                    </div>
                </div>
            </div>

            {#if serverSecurity.landlock_requested !== undefined}
                <div class="text-xs text-sem-fg-muted">
                    {t("app.landlock_status")}:
                    {serverSecurity.landlock_active
                        ? serverSecurity.landlock_auto_enabled
                            ? t("app.landlock_auto_enabled")
                            : t("app.landlock_active")
                        : serverSecurity.landlock_kernel_supported === false
                          ? t("app.landlock_kernel_unsupported")
                          : serverSecurity.landlock_disabled_by_env
                            ? t("app.landlock_disabled_by_env")
                            : t("app.landlock_inactive")}
                </div>
            {/if}

            {#if serverSecurity.appcontainer_requested !== undefined}
                <div class="text-xs text-sem-fg-muted">
                    {t("app.appcontainer_status")}:
                    {serverSecurity.appcontainer_active
                        ? serverSecurity.appcontainer_auto_enabled
                            ? t("app.appcontainer_auto_enabled")
                            : t("app.appcontainer_active")
                        : serverSecurity.appcontainer_supported === false
                          ? t("app.appcontainer_unsupported")
                          : serverSecurity.appcontainer_disabled_by_env
                            ? t("app.appcontainer_disabled_by_env")
                            : t("app.appcontainer_inactive")}
                </div>
            {/if}

            {#if serverSecurity.seccomp_requested !== undefined}
                <div class="text-xs text-sem-fg-muted">
                    {t("app.seccomp_status")}:
                    {serverSecurity.seccomp_active
                        ? serverSecurity.seccomp_auto_enabled
                            ? t("app.seccomp_auto_enabled")
                            : t("app.seccomp_active")
                        : serverSecurity.seccomp_kernel_supported === false
                          ? t("app.seccomp_kernel_unsupported")
                          : serverSecurity.seccomp_disabled_by_env
                            ? t("app.seccomp_disabled_by_env")
                            : t("app.seccomp_inactive")}
                </div>
            {/if}

            {#if serverSecurity.is_loopback_bind === false}
                <div class="rounded-md border border-amber-500/40 bg-amber-500/10 p-4 space-y-3">
                    <div class="text-sm font-semibold text-amber-900 dark:text-amber-200">
                        {t("app.web_exposure_warning_title")}
                    </div>
                    <p class="text-sm text-amber-950/90 dark:text-amber-100/90">
                        {t("app.web_exposure_warning_body")}
                    </p>
                    <ul class="space-y-2 text-sm">
                        <li class="flex items-start gap-2">
                            <MaterialDesignIcon
                                iconName={serverSecurity.auth_enabled ? "check-circle" : "alert-circle"}
                                class="size-4 mt-0.5 shrink-0 {serverSecurity.auth_enabled
                                    ? 'text-green-600'
                                    : 'text-amber-600'}"
                            />
                            <span>
                                {serverSecurity.auth_enabled
                                    ? t("app.web_exposure_check_auth")
                                    : t("app.web_exposure_check_auth_off")}
                            </span>
                        </li>
                        <li>
                            <label class="flex items-start gap-2 cursor-pointer">
                                <input
                                    checked={exposureAckFirewall}
                                    type="checkbox"
                                    class="rounded-sm mt-1"
                                    onchange={(e) => onackfirewallchange?.((e.target as HTMLInputElement).checked)}
                                />
                                <span>{t("app.web_exposure_check_firewall")}</span>
                            </label>
                        </li>
                        <li>
                            <label class="flex items-start gap-2 cursor-pointer">
                                <input
                                    checked={exposureAckVpn}
                                    type="checkbox"
                                    class="rounded-sm mt-1"
                                    onchange={(e) => onackvpnchange?.((e.target as HTMLInputElement).checked)}
                                />
                                <span>{t("app.web_exposure_check_vpn")}</span>
                            </label>
                        </li>
                    </ul>
                </div>
            {/if}

            <div class="space-y-2">
                <label for="web-ui-ip-allowlist-input" class="text-sm font-medium text-sem-fg block">
                    {t("app.web_ui_ip_allowlist")}
                </label>
                <input
                    id="web-ui-ip-allowlist-input"
                    value={serverSecurity.web_ui_ip_allowlist || ""}
                    type="text"
                    class="input-field font-mono text-xs"
                    placeholder={t("app.web_ui_ip_allowlist_placeholder")}
                    oninput={(e) => onallowlistchange?.((e.target as HTMLInputElement).value)}
                />
                <div class="text-xs text-sem-fg-muted">
                    {t("app.web_ui_ip_allowlist_description")}
                </div>
            </div>
        </div>
    </section>
{/if}
