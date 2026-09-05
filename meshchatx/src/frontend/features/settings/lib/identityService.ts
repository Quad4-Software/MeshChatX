// SPDX-License-Identifier: 0BSD

import ToastUtils from "../../../js/ToastUtils.js";
import DialogUtils from "../../../js/DialogUtils.js";
import DownloadUtils from "../../../js/DownloadUtils.js";
import GlobalEmitter from "../../../js/GlobalEmitter.js";
import { t } from "../../../js/i18n.js";

export interface IdentityItem {
    hash: string;
    display_name: string;
    is_current: boolean;
    lxmf_address?: string;
    lxst_address?: string;
    message_count?: number;
    icon_name?: string;
    icon_foreground_colour?: string;
    icon_background_colour?: string;
}

export function normalizeBase32(value: string): string {
    return String(value || "").replace(/\s+/g, "");
}

export async function copyToClipboard(value?: string): Promise<boolean> {
    if (!value) return false;
    try {
        await navigator.clipboard.writeText(value);
        ToastUtils.success(t("common.copied"));
        return true;
    } catch {
        ToastUtils.error(t("identities.identity_copy_failed"));
        return false;
    }
}

export async function fetchIdentities(api: any): Promise<IdentityItem[]> {
    try {
        const response = await api.get("/api/v1/identities");
        return response.data?.identities ?? [];
    } catch (e) {
        console.error(e);
        ToastUtils.error(t("identities.failed_load"));
        return [];
    }
}

export async function downloadIdentityBackup(api: any): Promise<void> {
    try {
        const response = await api.post(
            "/api/v1/identity/backup/download",
            {},
            {
                responseType: "arraybuffer",
            }
        );
        await DownloadUtils.downloadFromApiResponse(response, "identity.bin");
        ToastUtils.success(t("identities.identity_exported"));
    } catch {
        ToastUtils.error(t("identities.identity_export_failed"));
    }
}

export async function copyIdentityBase32(api: any): Promise<void> {
    try {
        const response = await api.post("/api/v1/identity/backup/base32");
        const base32 = response.data?.identity_base32 ?? "";
        if (!base32) {
            ToastUtils.error(t("identities.no_identity_available"));
            return;
        }
        await navigator.clipboard.writeText(base32);
        ToastUtils.success(t("identities.identity_copied"));
    } catch {
        ToastUtils.error(t("identities.identity_copy_failed"));
    }
}

export async function downloadAllIdentitiesZip(api: any): Promise<void> {
    try {
        const response = await api.post(
            "/api/v1/identities/export-all",
            {},
            {
                responseType: "arraybuffer",
            }
        );
        await DownloadUtils.downloadFromApiResponse(response, "identities_export.zip");
        ToastUtils.success(t("identities.export_all_success"));
    } catch (e: any) {
        const msg = e?.response?.data?.message || t("identities.export_all_failed");
        ToastUtils.error(msg);
    }
}

export async function switchIdentityWorkflow(
    api: any,
    identity: IdentityItem,
    onBusyChange: (busy: boolean) => void
): Promise<void> {
    if (identity.is_current) return;

    if (!(await DialogUtils.confirm(t("identities.switch_confirm", { name: identity.display_name })))) {
        return;
    }

    try {
        onBusyChange(true);
        GlobalEmitter.emit("identity-switching-start");

        const response = await api.post("/api/v1/identities/switch", {
            identity_hash: identity.hash,
        });

        if (response.data.hotswapped) {
            GlobalEmitter.emit("identity-switched-apply", {
                identity_hash: response.data.identity_hash ?? identity.hash,
                display_name: response.data.display_name ?? identity.display_name ?? "",
                requires_reauth: Boolean(response.data.requires_reauth),
            });
        } else {
            ToastUtils.info(t("identities.switch_scheduled"));
            onBusyChange(false);
            GlobalEmitter.emit("identity-switching-abort");
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        }
    } catch (e: any) {
        console.error(e);
        const errorMsg = e.response?.data?.message || t("identities.failed_switch") || "Failed to switch identity";
        ToastUtils.error(errorMsg);
        onBusyChange(false);
        GlobalEmitter.emit("identity-switching-abort");
    }
}
