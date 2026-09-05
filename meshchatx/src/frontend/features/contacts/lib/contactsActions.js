// SPDX-License-Identifier: 0BSD

import ToastUtils from "../../../js/ToastUtils.js";
import DownloadUtils from "../../../js/DownloadUtils.js";
import DialogUtils from "../../../js/DialogUtils.js";
import WebSocketConnection from "../../../js/WebSocketConnection.js";
import { t } from "../../../js/i18n.js";
import { buildContactUri, extractDestinationHash, parseLxmaUri, publicKeyFromAnnounce } from "./contactUri.js";

/**
 * @param {string} value
 * @param {string} [successMessage]
 */
export async function copyToClipboard(value, successMessage) {
    try {
        await navigator.clipboard.writeText(value);
        ToastUtils.success(successMessage || t("common.copied"));
    } catch {
        ToastUtils.error(t("common.failed_to_copy"));
    }
}

/**
 * @param {string} uri
 */
export async function shareUri(uri) {
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

/**
 * @param {Record<string, unknown>} contact
 * @returns {Promise<string | null>}
 */
export async function fetchContactLxmaUri(contact) {
    const destinationHash = String(contact?.lxmf_address || contact?.remote_identity_hash || "").toLowerCase();
    if (!/^[0-9a-f]{32}$/.test(destinationHash)) return null;
    try {
        const response = await window.api.get("/api/v1/announces", {
            params: { destination_hash: destinationHash, limit: 1 },
        });
        const publicKeyHex = publicKeyFromAnnounce(response.data?.announces?.[0]?.identity_public_key);
        return buildContactUri(contact, publicKeyHex);
    } catch {
        return null;
    }
}

/**
 * @param {string} input
 * @param {string} name
 * @param {{
 *   setPendingLxma: (v: boolean) => void,
 *   onAdded: () => Promise<void>,
 * }} hooks
 */
export async function addContactFromInput(input, name, hooks) {
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
    const existing = await window.api.get(`/api/v1/telephone/contacts/check/${destinationHash}`);
    if (existing.data?.id) {
        ToastUtils.info(t("contacts.contact_already_exists"));
        return { pending: false };
    }
    await window.api.post("/api/v1/telephone/contacts", {
        name: name?.trim() || `Contact ${destinationHash.slice(0, 8)}`,
        lxmf_address: destinationHash,
    });
    ToastUtils.success(t("contacts.contact_added"));
    await hooks.onAdded();
    return { pending: false, added: true };
}

/**
 * @param {Record<string, unknown>} contact
 * @param {Array<Record<string, unknown>>} contacts
 * @param {() => Promise<void>} onDone
 */
export async function removeContactWithDuplicates(contact, contacts, onDone) {
    if (!contact?.id) return;
    const duplicates = contacts.filter((c) => c.name === contact.name && c.id !== contact.id);
    const confirmMsg =
        duplicates.length > 0
            ? t("contacts.remove_duplicates_confirm", { count: duplicates.length, name: contact.name })
            : t("contacts.remove_contact_confirm");
    if (!(await DialogUtils.confirm(confirmMsg))) return;
    try {
        for (const id of [contact.id, ...duplicates.map((c) => c.id)]) {
            await window.api.delete(`/api/v1/telephone/contacts/${id}`);
        }
        ToastUtils.success(t("contacts.contact_removed"));
        await onDone();
    } catch {
        ToastUtils.error(t("contacts.failed_remove_contact"));
    }
}

/**
 * @param {Record<string, unknown>} contact
 * @param {Array<Record<string, unknown>>} contacts
 * @param {() => Promise<void>} onDone
 */
export async function editContactNameWithDuplicates(contact, contacts, onDone) {
    if (!contact?.id) return;
    const name = await DialogUtils.prompt(t("contacts.enter_contact_name"), String(contact.name || ""));
    if (name == null || name === contact.name) return;
    try {
        const duplicates = contacts.filter((c) => c.name === contact.name && c.id !== contact.id);
        for (const c of [contact, ...duplicates]) {
            await window.api.patch(`/api/v1/telephone/contacts/${c.id}`, { name });
            const destHash = c.remote_destination_hash || c.lxmf_address || c.remote_identity_hash;
            if (destHash && name.length > 0) {
                await window.api.post(`/api/v1/destination/${destHash}/custom-display-name/update`, {
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

export async function exportContactsFile() {
    try {
        const response = await window.api.get("/api/v1/telephone/contacts/export");
        const blob = new Blob([JSON.stringify({ contacts: response.data?.contacts ?? [] }, null, 2)], {
            type: "application/json",
        });
        await DownloadUtils.downloadFile("contacts_export.json", blob);
        ToastUtils.success(t("contacts.export_success"));
    } catch (e) {
        ToastUtils.error(e?.response?.data?.message || t("contacts.export_failed"));
    }
}

/**
 * @param {unknown[]} list
 * @param {() => Promise<void>} onDone
 * @returns {Promise<string | null>} error message or null
 */
export async function importContactsList(list, onDone) {
    try {
        const response = await window.api.post("/api/v1/telephone/contacts/import", { contacts: list });
        ToastUtils.success(t("contacts.import_success", { added: response.data?.added ?? 0 }));
        await onDone();
        return null;
    } catch (err) {
        return err?.response?.data?.message || t("contacts.import_failed");
    }
}

/**
 * @param {Record<string, unknown>} contact
 */
export function messagesHashHref(contact) {
    const hash = String(contact.remote_destination_hash || contact.lxmf_address || contact.remote_identity_hash || "");
    return hash ? `#/messages/${hash}` : "";
}

/**
 * @param {Record<string, unknown>} contact
 */
export function callHashHref(contact) {
    const hash = String(
        contact.remote_telephony_hash || contact.remote_destination_hash || contact.remote_identity_hash || ""
    );
    return hash ? `#/call?destination_hash=${encodeURIComponent(hash)}&tab=phone` : "";
}
