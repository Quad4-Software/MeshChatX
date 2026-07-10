import { describe, it, expect, vi, beforeEach } from "vitest";
import { parseMessagesImportJson, importMessagesFromText } from "../../meshchatx/src/frontend/js/messageImport.js";

describe("messageImport", () => {
    beforeEach(() => {
        window.api = {
            post: vi.fn().mockResolvedValue({
                data: {
                    imported: 2,
                    skipped: 0,
                    contacts_added: 1,
                    display_names_imported: 1,
                    read_state_imported: 2,
                },
            }),
        };
    });

    it("parses legacy messages-only JSON", () => {
        const payload = parseMessagesImportJson(JSON.stringify({ messages: [{ hash: "a" }] }));
        expect(payload.messages).toHaveLength(1);
    });

    it("parses bare message arrays", () => {
        const payload = parseMessagesImportJson(JSON.stringify([{ hash: "a" }]));
        expect(payload.messages).toHaveLength(1);
    });

    it("parses v2 bundles with contacts and read state", () => {
        const payload = parseMessagesImportJson(
            JSON.stringify({
                format: "meshchatx/messages/v2",
                messages: [{ hash: "a" }],
                contacts: [{ name: "Alice", remote_identity_hash: "aa" }],
                display_names: [{ destination_hash: "aa", display_name: "Alice" }],
                conversation_read_state: [{ destination_hash: "aa", last_read_at: "2026-01-01" }],
            })
        );
        expect(payload.contacts).toHaveLength(1);
        expect(payload.display_names).toHaveLength(1);
        expect(payload.conversation_read_state).toHaveLength(1);
    });

    it("posts full v2 payload on importMessagesFromText", async () => {
        const text = JSON.stringify({
            format: "meshchatx/messages/v2",
            messages: [{ hash: "a" }],
            contacts: [{ name: "Alice", remote_identity_hash: "aa" }],
        });
        const result = await importMessagesFromText(text);
        expect(window.api.post).toHaveBeenCalledWith("/api/v1/maintenance/messages/import", {
            format: "meshchatx/messages/v2",
            messages: [{ hash: "a" }],
            contacts: [{ name: "Alice", remote_identity_hash: "aa" }],
        });
        expect(result.imported).toBe(2);
        expect(result.contacts_added).toBe(1);
        expect(result.read_state_imported).toBe(2);
    });
});
