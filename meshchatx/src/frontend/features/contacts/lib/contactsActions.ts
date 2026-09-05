// SPDX-License-Identifier: 0BSD


import ToastUtils from "../../../js/ToastUtils.js";
import DownloadUtils from "../../../js/DownloadUtils.js";
import DialogUtils from "../../../js/DialogUtils.js";
import WebSocketConnection from "../../../js/WebSocketConnection.js";
import { t } from "../../../js/i18n.js";
import { buildContactUri, extractDestinationHash, parseLxmaUri, publicKeyFromAnnounce } from "./contactUri.js";

type ApiResponse = { data?: any; response?: { data?: { message?: string } } };
type ApiError = { response?: { data?: { message?: string } } };

type WindowApi = {
    get: (url: string, config?: { params?: Record<string, unknown> }) => Promise<ApiResponse>;
    post: (url: string, body?: unknown) => Promise<ApiResponse>;
    patch: (url: string, body?: unknown) => Promise<ApiResponse>;
    delete: (url: string) => Promise<ApiResponse>;
};

function api(): WindowApi {
    return (window as unknown as { api: WindowApi }).api;
}

export type ContactActionRecord = Record<string, unknown> & {
    id?: string | number;
    name?: string;
    lxmf_address?: string;
    remote_identity_hash?: string;
    remote_destination_hash?: string;
    remote_telephony_hash?: string;
};

export type AddContactHooks = {
    setPendingLxma: (v: boolean) => void;
    onAdded: () => Promise<void>;
};

export async function copyToClipboard(value: string, successMessage?: string): Promise<void> {
    try {
        await navigator.clipboard.writeText(value);
        ToastUtils.success(successMessage || t("common.copied"));
    } catch {
        ToastUtils.error(t("common.failed_to_copy"));
    }
}

export async function shareUri(uri: string): Promise<void> {
    try {
        if (navigator.share) {
            await navigator.share({ title: t("contacts.share"), text: uri });
            return;
        }
    } catch {
        // fall through
    }
    await copyToClipboard(uri, t("contacts.contact_uri_copied"));
}

export async function fetchContactLxmaUri(contact: ContactActionRecord): Promise<string | null> {
    const destinationHash = String(contact?.lxmf_address || contact?.remote_identity_hash || "").toLowerCase();
    if (!/^[0-9a-f]{32}$/.test(destinationHash)) return null;
    try {
        const response = await api().get("/api/v1/announces", {
            params: { destination_hash: destinationHash, limit: 1 },
        });
        const publicKeyHex = publicKeyFromAnnounce(response.data?.announces?.[0]?.identity_public_key);
        return buildContactUri(contact, publicKeyHex);
    } catch {
        return null;
    }
}

export async function addContactFromInput(
    input: string,
    name: string,
    hooks: AddContactHooks
): Promise<{ pending: boolean; added?: boolean }> {
    const lxmaData = parseLxmaUri(input);
    if (lxmaData) {
        hooks.setPendingLxma(true);
        WebSocketConnection.send(JSON.stringify({ type: "lxm.ingest_uri", uri: lxmaData.normalizedUri }));
        ToastUtils.info(t("contacts.importing_lxma"));
        return { pending: true };
    }
    const destinationHash = extractDestinationHash(input);
    if (!destinationHash) {
        ToastUtils.error(t("contacts.invalid_contact_input"));
        return { pending: false };
    }
    const existing = await api().get(`/api/v1/telephone/contacts/check/${destinationHash}`);
    if (existing.data?.id) {
        ToastUtils.info(t("contacts.contact_already_exists"));
        return { pending: false };
    }
    await api().post("/api/v1/telephone/contacts", {
        name: name?.trim() || `Contact ${destinationHash.slice(0, 8)}`,
        lxmf_address: destinationHash,
    });
    ToastUtils.success(t("contacts.contact_added"));
    await hooks.onAdded();
    return { pending: false, added: true };
}

export async function removeContactWithDuplicates(
    contact: ContactActionRecord,
    contacts: ContactActionRecord[],
    onDone: () => Promise<void>
): Promise<void> {
    if (!contact?.id) return;
    const duplicates = contacts.filter((c) => c.name === contact.name && c.id !== contact.id);
    const confirmMsg =
        duplicates.length > 0
            ? t("contacts.remove_duplicates_confirm", { count: duplicates.length, name: contact.name })
            : t("contacts.remove_contact_confirm");
    if (!(await DialogUtils.confirm(confirmMsg))) return;
    try {
        for (const id of [contact.id, ...duplicates.map((c) => c.id)]) {
            await api().delete(`/api/v1/telephone/contacts/${id}`);
        }
        ToastUtils.success(t("contacts.contact_removed"));
        await onDone();
    } catch {
        ToastUtils.error(t("contacts.failed_remove_contact"));
    }
}

export async function editContactNameWithDuplicates(
    contact: ContactActionRecord,
    contacts: ContactActionRecord[],
    onDone: () => Promise<void>
): Promise<void> {
    if (!contact?.id) return;
    const name = await DialogUtils.prompt(t("contacts.enter_contact_name"), String(contact.name || ""));
    if (name == null || name === contact.name) return;
    try {
        const duplicates = contacts.filter((c) => c.name === contact.name && c.id !== contact.id);
        for (const c of [contact, ...duplicates]) {
            await api().patch(`/api/v1/telephone/contacts/${c.id}`, { name });
            const destHash = c.remote_destination_hash || c.lxmf_address || c.remote_identity_hash;
            if (destHash && name.length > 0) {
                await api().post(`/api/v1/destination/${destHash}/custom-display-name/update`, {
                    display_name: name,
                });
            }
        }
        ToastUtils.success(t("contacts.contact_updated"));
        await onDone();
    } catch {
        ToastUtils.error(t("contacts.failed_update_contact"));
    }
}

export async function exportContactsFile(): Promise<void> {
    try {
        const response = await api().get("/api/v1/telephone/contacts/export");
        const blob = new Blob([JSON.stringify({ contacts: response.data?.contacts ?? [] }, null, 2)], {
            type: "application/json",
        });
        await DownloadUtils.downloadFile("contacts_export.json", blob);
        ToastUtils.success(t("contacts.export_success"));
    } catch (e) {
        const err = e as ApiError;
        ToastUtils.error(err?.response?.data?.message || t("contacts.export_failed"));
    }
}

export async function importContactsList(list: unknown[], onDone: () => Promise<void>): Promise<string | null> {
    try {
        const response = await api().post("/api/v1/telephone/contacts/import", { contacts: list });
        ToastUtils.success(t("contacts.import_success", { added: response.data?.added ?? 0 }));
        await onDone();
        return null;
    } catch (err) {
        const e = err as ApiError;
        return e?.response?.data?.message || t("contacts.import_failed");
    }
}

export function messagesHashHref(contact: ContactActionRecord): string {
    const hash = String(contact.remote_destination_hash || contact.lxmf_address || contact.remote_identity_hash || "");
    return hash ? `#/messages/${hash}` : "";
}

export function callHashHref(contact: ContactActionRecord): string {
    const hash = String(
        contact.remote_telephony_hash || contact.remote_destination_hash || contact.remote_identity_hash || ""
    );
    return hash ? `#/call?destination_hash=${encodeURIComponent(hash)}&tab=phone` : "";
}
