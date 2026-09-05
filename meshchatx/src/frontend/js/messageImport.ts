/**
 * Parse and import LXMF message export JSON (v1 messages-only or v2 bundle).
 */

export interface MessageImportApiResponse {
    imported?: number;
    skipped?: number;
    contacts_added?: number;
    contacts_skipped?: number;
    display_names_imported?: number;
    read_state_imported?: number;
    message?: string;
    errors?: Array<{ error: string }>;
}

export interface MessageImportResult {
    payload?: { messages?: unknown[] };
    imported: number;
    skipped: number;
    contacts_added: number;
    display_names_imported: number;
    read_state_imported: number;
}

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
    const data = response.data as MessageImportApiResponse | undefined;
    return {
        payload,
        imported: data?.imported ?? payload.messages?.length ?? 0,
        skipped: data?.skipped ?? 0,
        contacts_added: data?.contacts_added ?? 0,
        display_names_imported: data?.display_names_imported ?? 0,
        read_state_imported: data?.read_state_imported ?? 0,
    };
}

export async function importMessagesFromFile(file) {
    const form = new FormData();
    form.append("file", file);
    const response = await window.api.post("/api/v1/maintenance/messages/import-file", form);
    const data = response.data as MessageImportApiResponse | undefined;
    return {
        imported: data?.imported ?? 0,
        skipped: data?.skipped ?? 0,
        contacts_added: data?.contacts_added ?? 0,
        display_names_imported: data?.display_names_imported ?? 0,
        read_state_imported: data?.read_state_imported ?? 0,
    };
}
