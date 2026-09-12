// @ts-check

import { computed, ref } from "vue";

import { apiPath } from "../constants.js";

const SELF_TEST_KEYS = [
    "stack_up",
    "config_good",
    "db_good",
    "read_write_good",
    "identity_good",
    "imports_good",
    "umsgpack_roundtrip",
    "storage_lock_good",
    "temp_fs_good",
    "public_assets_good",
    "lxmf_router_good",
    "lxst_telephony",
    "subprocess_good",
    "run_module_good",
    "audio_codec_roundtrip",
    "miniaudio_decode",
    "translation_pack_import",
    "sqlite_roundtrip",
    "identity_roundtrip",
    "loopback_tcp",
    "unicode_path_good",
    "rnode_support_good",
    "bot_launcher_good",
    "http_status_good",
    "http_app_info_good",
    "http_config_good",
    "http_db_health_good",
    "http_auth_csrf_good",
    "http_bots_status_good",
    "http_security_good",
    "http_interfaces_good",
    "http_reticulum_instance_good",
    "http_identities_good",
    "http_favourites_good",
    "http_telephone_good",
    "http_plugins_good",
    "http_plugins_trust_good",
    "http_sideband_plugins_good",
    "http_sideband_config_good",
    "http_rrc_hubs_good",
    "http_rrc_servers_good",
    "plugins_runtime_good",
    "websocket_good",
    "websocket_rns_link_good",
    "bots_lifecycle",
];

const SELF_TEST_LABEL_KEYS = {
    stack_up: "selftest.stack_up",
    config_good: "selftest.config_good",
    db_good: "selftest.db_good",
    read_write_good: "selftest.read_write",
    identity_good: "selftest.identity_good",
    imports_good: "selftest.imports_good",
    umsgpack_roundtrip: "selftest.umsgpack_roundtrip",
    storage_lock_good: "selftest.storage_lock_good",
    temp_fs_good: "selftest.temp_fs_good",
    public_assets_good: "selftest.public_assets_good",
    lxmf_router_good: "selftest.lxmf_router_good",
    lxst_telephony: "selftest.lxst_telephony",
    subprocess_good: "selftest.subprocess_good",
    run_module_good: "selftest.run_module_good",
    audio_codec_roundtrip: "selftest.audio_codec_roundtrip",
    miniaudio_decode: "selftest.miniaudio_decode",
    translation_pack_import: "selftest.translation_pack_import",
    sqlite_roundtrip: "selftest.sqlite_roundtrip",
    identity_roundtrip: "selftest.identity_roundtrip",
    loopback_tcp: "selftest.loopback_tcp",
    unicode_path_good: "selftest.unicode_path_good",
    rnode_support_good: "selftest.rnode_support_good",
    bot_launcher_good: "selftest.bot_launcher_good",
    http_status_good: "selftest.http_status_good",
    http_app_info_good: "selftest.http_app_info_good",
    http_config_good: "selftest.http_config_good",
    http_db_health_good: "selftest.http_db_health_good",
    http_auth_csrf_good: "selftest.http_auth_csrf_good",
    http_bots_status_good: "selftest.http_bots_status_good",
    http_security_good: "selftest.http_security_good",
    http_interfaces_good: "selftest.http_interfaces_good",
    http_reticulum_instance_good: "selftest.http_reticulum_instance_good",
    http_identities_good: "selftest.http_identities_good",
    http_favourites_good: "selftest.http_favourites_good",
    http_telephone_good: "selftest.http_telephone_good",
    http_plugins_good: "selftest.http_plugins_good",
    http_plugins_trust_good: "selftest.http_plugins_trust_good",
    http_sideband_plugins_good: "selftest.http_sideband_plugins_good",
    http_sideband_config_good: "selftest.http_sideband_config_good",
    http_rrc_hubs_good: "selftest.http_rrc_hubs_good",
    http_rrc_servers_good: "selftest.http_rrc_servers_good",
    plugins_runtime_good: "selftest.plugins_runtime_good",
    websocket_good: "selftest.websocket_good",
    websocket_rns_link_good: "selftest.websocket_rns_link_good",
    bots_lifecycle: "selftest.bots_lifecycle",
};

/**
 * System self-test state for the diagnostics section of SettingsPage:
 * run flag, results map, expanded failure reasons, and the derived
 * per-check list with translated labels.
 *
 * options.t is the host i18n function so check labels keep the locale.
 */
export function useSelfTest(options = {}) {
    const t = options.t || ((key) => key);

    const selfTestRunning = ref(false);
    const selfTestResults = ref(null);
    const selfTestExpandedReasons = ref({});

    const selfTestChecks = computed(() => {
        if (!selfTestResults.value) {
            return [];
        }
        const r = selfTestResults.value;
        const item = (key, labelKey) => ({
            key,
            label: t(labelKey),
            passed: r[key]?.status === "ok",
            reason: r[key]?.reason || "",
        });
        return SELF_TEST_KEYS.map((key) => item(key, SELF_TEST_LABEL_KEYS[key]));
    });

    const allSelfTestChecksPassed = computed(
        () => selfTestChecks.value.length > 0 && selfTestChecks.value.every((check) => check.passed)
    );

    function isSelfTestReasonExpanded(key) {
        return !!selfTestExpandedReasons.value?.[key];
    }

    function toggleSelfTestReason(key) {
        selfTestExpandedReasons.value = {
            ...selfTestExpandedReasons.value,
            [key]: !selfTestExpandedReasons.value?.[key],
        };
    }

    async function runSelfTest() {
        if (selfTestRunning.value) {
            return;
        }
        selfTestRunning.value = true;
        selfTestResults.value = null;
        selfTestExpandedReasons.value = {};
        try {
            const response = await window.api.get(apiPath("/self-test"));
            selfTestResults.value = response.data;
        } catch (e) {
            console.error("Failed to run system self-test", e);
            const failed = { status: "failed", reason: e.message || String(e) };
            const results = {};
            for (const key of SELF_TEST_KEYS) {
                results[key] = { ...failed };
            }
            selfTestResults.value = results;
        } finally {
            selfTestRunning.value = false;
        }
    }

    return {
        selfTestRunning,
        selfTestResults,
        selfTestExpandedReasons,
        selfTestChecks,
        allSelfTestChecksPassed,
        isSelfTestReasonExpanded,
        toggleSelfTestReason,
        runSelfTest,
    };
}
