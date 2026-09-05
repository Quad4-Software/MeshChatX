/**
 * Parse and import LXMF message export JSON (v1 messages-only or v2 bundle).
 */

export function parseMessagesImportJson(text) {
    const data = JSON.parse(text);
    if (Array.isArray(data)) {
        return { messages: data };
    }
    if (data && typeof data === "object" && Array.isArray(data.messages)) {
        return data;
    }
    throw new Error("Invalid file format");
}

export async function importMessagesFromText(text) {
    const payload = parseMessagesImportJson(text);
    const response = await window.api.post("/api/v1/maintenance/messages/import", payload);
    return {
        payload,
        imported: response.data?.imported ?? payload.messages?.length ?? 0,
        skipped: response.data?.skipped ?? 0,
        contacts_added: response.data?.contacts_added ?? 0,
        display_names_imported: response.data?.display_names_imported ?? 0,
        read_state_imported: response.data?.read_state_imported ?? 0,
    };
}

export async function importMessagesFromFile(file) {
    const form = new FormData();
    form.append("file", file);
    const response = await window.api.post("/api/v1/maintenance/messages/import-file", form);
    return {
        imported: response.data?.imported ?? 0,
        skipped: response.data?.skipped ?? 0,
        contacts_added: response.data?.contacts_added ?? 0,
        display_names_imported: response.data?.display_names_imported ?? 0,
        read_state_imported: response.data?.read_state_imported ?? 0,
    };
}
