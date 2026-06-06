/**
 * Parse and import LXMF message export JSON.
 */

export function parseMessagesImportJson(text) {
    const data = JSON.parse(text);
    const messages = Array.isArray(data) ? data : data?.messages;
    if (!Array.isArray(messages)) {
        throw new Error("Invalid file format");
    }
    return messages;
}

export async function importMessagesFromText(text) {
    const messages = parseMessagesImportJson(text);
    const response = await window.api.post("/api/v1/maintenance/messages/import", {
        messages,
    });
    return {
        messages,
        imported: response.data?.imported ?? messages.length,
        skipped: response.data?.skipped ?? 0,
    };
}

export async function importMessagesFromFile(file) {
    const form = new FormData();
    form.append("file", file);
    const response = await window.api.post("/api/v1/maintenance/messages/import-file", form);
    return {
        imported: response.data?.imported ?? 0,
        skipped: response.data?.skipped ?? 0,
    };
}
