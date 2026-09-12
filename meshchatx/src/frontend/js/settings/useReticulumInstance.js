// @ts-check

import { computed, ref } from "vue";

import ToastUtils from "../ToastUtils.js";
import { applyReticulumInstanceSettings, fetchReticulumInstanceSettings } from "./settingsReticulumInstanceService.js";

/**
 * Reticulum instance (shared-instance / RPC) settings for the transport
 * section of SettingsPage: instance state, saving flag, remote-management
 * allowlist text, and the redacted rpc_config snippet display.
 *
 * options.t is the host i18n function; options.getRpcKeyVisible reads the
 * host toggle that controls whether the rpc_key line is redacted.
 */
export function useReticulumInstance(options = {}) {
    const t = options.t || ((key) => key);
    const getRpcKeyVisible = options.getRpcKeyVisible || (() => false);

    const reticulumInstance = ref({
        share_instance: true,
        local_hops_delta: false,
        respond_to_probes: false,
        enable_remote_management: false,
        remote_management_allowed: [],
        shared_instance_type: "",
        instance_name: "default",
        rpc_key: null,
        rpc_config_snippet: null,
        is_connected_to_shared_instance: false,
        enable_transport: false,
    });
    const reticulumInstanceSaving = ref(false);
    const remoteManagementAllowedText = ref("");
    const settingsMgmtIdentityPath = ref("");
    const settingsMgmtIdentityHash = ref("");

    function mergeInstance(instance) {
        reticulumInstance.value = {
            ...reticulumInstance.value,
            ...instance,
            shared_instance_type: instance.shared_instance_type || "",
            instance_name: instance.instance_name || "default",
            remote_management_allowed: Array.isArray(instance.remote_management_allowed)
                ? instance.remote_management_allowed
                : [],
        };
    }

    const displayedRpcConfigSnippet = computed(() => {
        const snippet = reticulumInstance.value?.rpc_config_snippet;
        if (!snippet) {
            return t("app.rpc_config_unavailable");
        }
        if (getRpcKeyVisible()) {
            return snippet;
        }
        return snippet
            .split("\n")
            .map((line) => {
                const match = line.match(/^(\s*rpc_key\s*=\s*)(.*)$/i);
                if (!match) {
                    return line;
                }
                const value = match[2] || "";
                return `${match[1]}${"•".repeat(Math.max(8, Math.min(value.length, 48)))}`;
            })
            .join("\n");
    });

    async function loadReticulumInstanceSettings() {
        try {
            const instance = await fetchReticulumInstanceSettings(window.api);
            if (instance && typeof instance === "object") {
                mergeInstance(instance);
                remoteManagementAllowedText.value = (reticulumInstance.value.remote_management_allowed || []).join(
                    "\n"
                );
            }
        } catch (e) {
            console.log(e);
        }
    }

    async function patchReticulumInstance(patch) {
        if (reticulumInstanceSaving.value) return;
        reticulumInstanceSaving.value = true;
        try {
            const response = await applyReticulumInstanceSettings(patch, window.api);
            if (response?.data?.instance) {
                mergeInstance(response.data.instance);
                if ("remote_management_allowed" in (patch || {})) {
                    remoteManagementAllowedText.value = (reticulumInstance.value.remote_management_allowed || []).join(
                        "\n"
                    );
                }
            }
            if (response?.data?.message) {
                ToastUtils.success(response.data.message);
            }
        } catch {
            ToastUtils.error(t("settings.failed_update_reticulum_instance"));
            await loadReticulumInstanceSettings();
        } finally {
            reticulumInstanceSaving.value = false;
        }
    }

    function onShareInstanceChange(value) {
        patchReticulumInstance({ share_instance: !!value });
    }

    function onLocalHopsDeltaChange(value) {
        patchReticulumInstance({ local_hops_delta: !!value });
    }

    function onRespondToProbesChange(value) {
        patchReticulumInstance({ respond_to_probes: !!value });
    }

    function onEnableRemoteManagementChange(value) {
        patchReticulumInstance({ enable_remote_management: !!value });
    }

    function saveRemoteManagementAllowed() {
        const hashes = (remoteManagementAllowedText.value || "")
            .split(/[\s,]+/)
            .map((value) => value.trim().toLowerCase())
            .filter((value) => value.length > 0);
        patchReticulumInstance({ remote_management_allowed: hashes });
    }

    function onSettingsMgmtIdentityHash(hash) {
        settingsMgmtIdentityHash.value = hash || "";
    }

    function onSharedInstanceTypeChange() {
        const value = reticulumInstance.value.shared_instance_type || null;
        patchReticulumInstance({ shared_instance_type: value });
    }

    function onInstanceNameChange() {
        patchReticulumInstance({
            instance_name: reticulumInstance.value.instance_name || "default",
        });
    }

    async function copyRpcConfigSnippet() {
        const snippet = reticulumInstance.value.rpc_config_snippet;
        if (!snippet) return;
        try {
            await navigator.clipboard.writeText(snippet);
            ToastUtils.success(t("app.rpc_config_copied"));
        } catch {
            ToastUtils.error(t("app.copy_failed"));
        }
    }

    return {
        reticulumInstance,
        reticulumInstanceSaving,
        remoteManagementAllowedText,
        settingsMgmtIdentityPath,
        settingsMgmtIdentityHash,
        displayedRpcConfigSnippet,
        loadReticulumInstanceSettings,
        patchReticulumInstance,
        onShareInstanceChange,
        onLocalHopsDeltaChange,
        onRespondToProbesChange,
        onEnableRemoteManagementChange,
        saveRemoteManagementAllowed,
        onSettingsMgmtIdentityHash,
        onSharedInstanceTypeChange,
        onInstanceNameChange,
        copyRpcConfigSnippet,
    };
}
