// @ts-check

import { computed, ref } from "vue";

import * as identityApi from "../api/identity.js";
import { apiPath, EMITTER_EVENTS } from "../constants.js";
import GlobalEmitter from "../GlobalEmitter.js";
import { useConfigStore } from "../stores/configStore.js";
import ToastUtils from "../ToastUtils.js";
import Utils from "../Utils.js";

/**
 * Identity onboarding state for TutorialModal: new-identity display
 * name, file/base32 import mode, and pending-import activation.
 *
 * options.t is the host instance $t so translated strings keep working.
 * options.goToStep advances the host wizard when identity setup
 * completes (handleIdentityContinue moves the wizard to step 3).
 */
export function useTutorialIdentity(options = {}) {
    const t = options.t || ((key) => key);
    const goToStep = options.goToStep;

    const identityMode = ref("new");
    const identityName = ref("");
    const identityImportBase32 = ref("");
    const identityImportFile = ref(null);
    const identityImportInProgress = ref(false);
    const identityImportError = ref("");
    const identityImportedHash = ref(null);
    const originalIdentityHash = ref(null);
    const finishingTutorial = ref(false);

    const defaultUsername = computed(() => "Anonymous Peer");

    const hasIdentityImportInput = computed(() =>
        Boolean(identityImportFile.value || normalizeBase32(identityImportBase32.value))
    );

    function resetIdentitySetupState() {
        identityMode.value = "new";
        identityName.value = "";
        identityImportBase32.value = "";
        identityImportFile.value = null;
        identityImportError.value = "";
        identityImportInProgress.value = false;
        identityImportedHash.value = null;
        originalIdentityHash.value = null;
        finishingTutorial.value = false;
    }

    function setIdentityMode(mode) {
        identityMode.value = mode;
        identityImportError.value = "";
        if (mode === "new") {
            identityImportFile.value = null;
            identityImportBase32.value = "";
            identityImportedHash.value = null;
        }
    }

    function normalizeBase32(value) {
        return String(value || "").replace(/\s+/g, "");
    }

    function formatIdentityHash(hash) {
        return Utils.formatDestinationHash(hash);
    }

    function onIdentityImportBase32Input() {
        identityImportedHash.value = null;
        identityImportError.value = "";
    }

    async function loadIdentitySetupDefaults() {
        try {
            const [identitiesRes, configRes] = await Promise.all([
                window.api.get(apiPath("/identities")),
                window.api.get(apiPath("/config")),
            ]);
            const identities = identitiesRes.data?.identities ?? [];
            const currentIdentity = identities.find((item) => item.is_current);
            originalIdentityHash.value = currentIdentity?.hash || null;
            identityName.value = configRes.data?.config?.display_name || defaultUsername.value;
        } catch (e) {
            console.error("Failed to load identity setup defaults:", e);
            identityName.value = defaultUsername.value;
        }
    }

    function onIdentityImportFileChange(event) {
        const files = event?.target?.files;
        const file = files?.[0] || null;
        identityImportedHash.value = null;
        identityImportError.value = "";
        if (file && file.size === 0) {
            identityImportFile.value = null;
            identityImportError.value = t("tutorial.identity_import_empty_file");
        } else if (file && file.size > 65536) {
            identityImportFile.value = null;
            identityImportError.value = t("tutorial.identity_import_file_too_large");
        } else {
            identityImportFile.value = file;
        }
        if (event?.target) {
            event.target.value = "";
        }
    }

    async function importIdentityFromFile(file, displayName) {
        const formData = new FormData();
        formData.append("file", file);
        if (displayName) {
            formData.append("display_name", displayName);
        }
        const response = await identityApi.restoreIdentity(formData, {
            headers: { "Content-Type": "multipart/form-data" },
        });
        return response.data?.identity?.hash || null;
    }

    async function importIdentityFromBase32(base32, displayName) {
        const payload = { base32: normalizeBase32(base32) };
        if (displayName) {
            payload.display_name = displayName;
        }
        const response = await window.api.post(apiPath("/identity/restore"), payload);
        return response.data?.identity?.hash || null;
    }

    async function handleIdentityContinue() {
        if (identityImportInProgress.value) {
            return;
        }
        const trimmedName = identityName.value.trim() || defaultUsername.value;
        identityImportError.value = "";
        if (identityMode.value === "new") {
            try {
                await window.api.patch(apiPath("/config"), {
                    display_name: trimmedName,
                });
                useConfigStore().config.display_name = trimmedName;
                identityImportedHash.value = null;
                goToStep?.(3);
            } catch (e) {
                identityImportError.value = e.response?.data?.message || t("tutorial.identity_name_update_failed");
            }
            return;
        }
        if (!hasIdentityImportInput.value) {
            identityImportError.value = t("tutorial.identity_import_required");
            return;
        }
        identityImportInProgress.value = true;
        try {
            let importedHash = null;
            if (identityImportFile.value) {
                importedHash = await importIdentityFromFile(identityImportFile.value, trimmedName);
                identityImportFile.value = null;
            } else {
                importedHash = await importIdentityFromBase32(identityImportBase32.value, trimmedName);
                identityImportBase32.value = "";
            }
            if (!importedHash) {
                throw new Error("Missing imported identity hash");
            }
            identityImportedHash.value = importedHash;
            goToStep?.(3);
        } catch (e) {
            identityImportError.value = e.response?.data?.message || t("tutorial.identity_import_failed");
        } finally {
            identityImportInProgress.value = false;
        }
    }

    async function activateImportedIdentity() {
        if (!identityImportedHash.value) {
            return true;
        }
        if (identityImportedHash.value === originalIdentityHash.value) {
            return true;
        }
        try {
            GlobalEmitter.emit(EMITTER_EVENTS.IDENTITY_SWITCHING_START);
            const response = await window.api.post(apiPath("/identities/switch"), {
                identity_hash: identityImportedHash.value,
            });
            if (originalIdentityHash.value) {
                try {
                    await window.api.delete(apiPath(`/identities/${originalIdentityHash.value}`));
                } catch (deleteError) {
                    console.error("Failed to delete default identity after import:", deleteError);
                    ToastUtils.warning(t("tutorial.identity_default_delete_failed"));
                }
            }
            if (response?.data?.hotswapped) {
                GlobalEmitter.emit(EMITTER_EVENTS.IDENTITY_SWITCHED_APPLY, {
                    identity_hash: response.data.identity_hash ?? identityImportedHash.value,
                    display_name: response.data.display_name ?? "",
                    requires_reauth: Boolean(response.data.requires_reauth),
                });
            } else if (response?.data?.hotswapped === false) {
                ToastUtils.info(t("identities.switch_scheduled"));
                GlobalEmitter.emit(EMITTER_EVENTS.IDENTITY_SWITCHING_ABORT);
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            }
            identityImportedHash.value = null;
            return true;
        } catch (e) {
            ToastUtils.error(e.response?.data?.message || t("tutorial.identity_switch_failed"));
            GlobalEmitter.emit(EMITTER_EVENTS.IDENTITY_SWITCHING_ABORT);
            return false;
        }
    }

    return {
        identityMode,
        identityName,
        identityImportBase32,
        identityImportFile,
        identityImportInProgress,
        identityImportError,
        identityImportedHash,
        originalIdentityHash,
        finishingTutorial,
        defaultUsername,
        hasIdentityImportInput,
        resetIdentitySetupState,
        setIdentityMode,
        normalizeBase32,
        formatIdentityHash,
        onIdentityImportBase32Input,
        loadIdentitySetupDefaults,
        onIdentityImportFileChange,
        importIdentityFromFile,
        importIdentityFromBase32,
        handleIdentityContinue,
        activateImportedIdentity,
    };
}
