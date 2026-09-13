<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../../js/i18n.js";

    interface Props {
        visible?: boolean;
    }

    let { visible = true }: Props = $props();

    let selfTestRunning = $state(false);
    let selfTestResults = $state<Record<string, { status: string; reason?: string }> | null>(null);
    let selfTestExpandedReasons = $state<Record<string, boolean>>({});

    const CHECK_KEYS: Array<{ key: string; labelKey: string }> = [
        { key: "stack_up", labelKey: "selftest.stack_up" },
        { key: "config_good", labelKey: "selftest.config_good" },
        { key: "db_good", labelKey: "selftest.db_good" },
        { key: "read_write_good", labelKey: "selftest.read_write" },
        { key: "identity_good", labelKey: "selftest.identity_good" },
        { key: "imports_good", labelKey: "selftest.imports_good" },
        { key: "storage_lock_good", labelKey: "selftest.storage_lock_good" },
        { key: "temp_fs_good", labelKey: "selftest.temp_fs_good" },
        { key: "public_assets_good", labelKey: "selftest.public_assets_good" },
        { key: "lxmf_router_good", labelKey: "selftest.lxmf_router_good" },
        { key: "subprocess_good", labelKey: "selftest.subprocess_good" },
        { key: "run_module_good", labelKey: "selftest.run_module_good" },
        { key: "sqlite_roundtrip", labelKey: "selftest.sqlite_roundtrip" },
        { key: "identity_roundtrip", labelKey: "selftest.identity_roundtrip" },
        { key: "loopback_tcp", labelKey: "selftest.loopback_tcp" },
        { key: "unicode_path_good", labelKey: "selftest.unicode_path_good" },
        { key: "rnode_support_good", labelKey: "selftest.rnode_support_good" },
        { key: "bot_launcher_good", labelKey: "selftest.bot_launcher_good" },
        { key: "http_status_good", labelKey: "selftest.http_status_good" },
        { key: "http_app_info_good", labelKey: "selftest.http_app_info_good" },
        { key: "http_config_good", labelKey: "selftest.http_config_good" },
        { key: "http_db_health_good", labelKey: "selftest.http_db_health_good" },
        { key: "http_auth_csrf_good", labelKey: "selftest.http_auth_csrf_good" },
        { key: "http_bots_status_good", labelKey: "selftest.http_bots_status_good" },
        { key: "http_security_good", labelKey: "selftest.http_security_good" },
        { key: "http_interfaces_good", labelKey: "selftest.http_interfaces_good" },
        { key: "http_reticulum_instance_good", labelKey: "selftest.http_reticulum_instance_good" },
        { key: "http_identities_good", labelKey: "selftest.http_identities_good" },
        { key: "http_favourites_good", labelKey: "selftest.http_favourites_good" },
        { key: "http_telephone_good", labelKey: "selftest.http_telephone_good" },
        { key: "http_plugins_good", labelKey: "selftest.http_plugins_good" },
        { key: "http_plugins_trust_good", labelKey: "selftest.http_plugins_trust_good" },
        { key: "http_sideband_plugins_good", labelKey: "selftest.http_sideband_plugins_good" },
        { key: "http_sideband_config_good", labelKey: "selftest.http_sideband_config_good" },
        { key: "http_rrc_hubs_good", labelKey: "selftest.http_rrc_hubs_good" },
        { key: "http_rrc_servers_good", labelKey: "selftest.http_rrc_servers_good" },
        { key: "plugins_runtime_good", labelKey: "selftest.plugins_runtime_good" },
        { key: "websocket_good", labelKey: "selftest.websocket_good" },
        { key: "websocket_rns_link_good", labelKey: "selftest.websocket_rns_link_good" },
        { key: "bots_lifecycle", labelKey: "selftest.bots_lifecycle" },
    ];

    const selfTestChecks = $derived.by(() => {
        if (!selfTestResults) return [];
        const r = selfTestResults;
        return CHECK_KEYS.map(({ key, labelKey }) => ({
            key,
            label: t(labelKey),
            passed: r[key]?.status === "ok",
            reason: r[key]?.reason || "",
        }));
    });

    const allSelfTestChecksPassed = $derived(
        selfTestChecks.length > 0 && selfTestChecks.every((check) => check.passed)
    );

    function isSelfTestReasonExpanded(key: string): boolean {
        return Boolean(selfTestExpandedReasons[key]);
    }

    function toggleSelfTestReason(key: string) {
        selfTestExpandedReasons = {
            ...selfTestExpandedReasons,
            [key]: !selfTestExpandedReasons[key],
        };
    }

    async function runSelfTest() {
        if (selfTestRunning) return;
        selfTestRunning = true;
        selfTestResults = null;
        selfTestExpandedReasons = {};
        try {
            const response = await window.api.get("/api/v1/self-test");
            selfTestResults = response.data;
        } catch (e: any) {
            console.error("Failed to run system self-test", e);
            const failed = { status: "failed", reason: e?.message || String(e) };
            const fallback: Record<string, { status: string; reason: string }> = {};
            for (const { key } of CHECK_KEYS) {
                fallback[key] = { ...failed };
            }
            selfTestResults = fallback;
        } finally {
            selfTestRunning = false;
        }
    }
</script>

{#if visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">Maintenance</div>
                <h2>{t("selftest.title")}</h2>
                <p>{t("selftest.description")}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <div class="flex items-center gap-3">
                <button
                    type="button"
                    class="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl transition flex items-center gap-2 cursor-pointer"
                    disabled={selfTestRunning}
                    onclick={runSelfTest}
                >
                    {#if selfTestRunning}
                        <MaterialDesignIcon iconName="loading" class="animate-spin size-4" />
                    {:else}
                        <MaterialDesignIcon iconName="play-circle-outline" class="size-4" />
                    {/if}
                    {selfTestRunning ? t("selftest.running") : t("selftest.run_test_btn")}
                </button>
            </div>

            {#if selfTestResults}
                <div class="space-y-3 mt-4 border-t border-sem-border pt-4">
                    {#each selfTestChecks as check (check.key)}
                        <div
                            class="flex flex-col p-3 rounded-xl border bg-sem-surface {check.passed
                                ? 'border-emerald-200/60 dark:border-emerald-900/30'
                                : 'border-red-200/60 dark:border-red-900/30'}"
                        >
                            <div class="flex items-center justify-between gap-2">
                                <div class="flex items-center gap-2 font-semibold text-sm min-w-0">
                                    <MaterialDesignIcon
                                        iconName={check.passed ? "check-circle-outline" : "alert-circle-outline"}
                                        class="size-4 shrink-0 {check.passed ? 'text-emerald-500' : 'text-red-500'}"
                                    />
                                    <span class="truncate">{check.label}</span>
                                </div>
                                <div class="flex items-center gap-1.5 shrink-0">
                                    {#if !check.passed && check.reason}
                                        <button
                                            type="button"
                                            class="inline-flex items-center justify-center rounded-lg p-1 text-red-600 hover:bg-red-50 dark:text-red-300 dark:hover:bg-red-950/40 cursor-pointer"
                                            aria-expanded={isSelfTestReasonExpanded(check.key)}
                                            aria-label={isSelfTestReasonExpanded(check.key)
                                                ? t("selftest.collapse_reason")
                                                : t("selftest.expand_reason")}
                                            title={isSelfTestReasonExpanded(check.key)
                                                ? t("selftest.collapse_reason")
                                                : t("selftest.expand_reason")}
                                            onclick={() => toggleSelfTestReason(check.key)}
                                        >
                                            <MaterialDesignIcon
                                                iconName={isSelfTestReasonExpanded(check.key)
                                                    ? "chevron-up"
                                                    : "chevron-down"}
                                                class="size-4"
                                            />
                                        </button>
                                    {/if}
                                    <span
                                        class="px-2 py-0.5 text-xs font-bold rounded-md {check.passed
                                            ? 'bg-emerald-50 dark:bg-emerald-950/20 text-emerald-700 dark:text-emerald-300'
                                            : 'bg-red-50 dark:bg-red-950/20 text-red-700 dark:text-red-300'}"
                                    >
                                        {check.passed ? t("selftest.passed") : t("selftest.failed")}
                                    </span>
                                </div>
                            </div>
                            {#if !check.passed && check.reason && isSelfTestReasonExpanded(check.key)}
                                <div
                                    class="text-xs text-red-600 dark:text-red-400 mt-2 pl-6 whitespace-pre-wrap wrap-break-word"
                                >
                                    <span class="font-semibold">{t("selftest.reason_label")}:</span>
                                    {check.reason}
                                </div>
                            {/if}
                        </div>
                    {/each}

                    {#if allSelfTestChecksPassed}
                        <div
                            class="text-xs text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-2 pl-2"
                        >
                            <MaterialDesignIcon iconName="check" class="size-4" />
                            {t("selftest.checks_completed")}
                        </div>
                    {/if}
                </div>
            {/if}
        </div>
    </section>
{/if}
