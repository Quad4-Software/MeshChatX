// SPDX-License-Identifier: 0BSD

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import DialogUtils from "@/js/DialogUtils";
import { editContactNameWithDuplicates } from "@/features/contacts/lib/contactsActions.ts";
import {
    mergePeerFromAnnounce,
    mergePeerFromConversation,
    preferKnownDisplayName,
    shouldUpdatePanePeerDisplayName,
} from "@/features/messages/lib/peerAnnounce.ts";
import { registerTranslator } from "@/js/i18n.js";

vi.mock("@/js/DialogUtils", () => ({
    default: {
        prompt: vi.fn(),
        alert: vi.fn(),
        confirm: vi.fn(() => Promise.resolve(true)),
    },
}));

describe("Messages display name protection", () => {
    it("does not replace a known name with Anonymous Peer", () => {
        expect(preferKnownDisplayName("Anonymous Peer", "Real Name")).toBe("Real Name");
        expect(
            mergePeerFromAnnounce(
                { destination_hash: "a".repeat(32), display_name: "Real Name" },
                { destination_hash: "a".repeat(32), display_name: "Anonymous Peer" }
            ).display_name
        ).toBe("Real Name");
    });

    it("accepts a real announce over an anonymous or older name", () => {
        expect(
            mergePeerFromAnnounce(
                { destination_hash: "b".repeat(32), display_name: "Anonymous Peer" },
                { destination_hash: "b".repeat(32), display_name: "Newly Announced" }
            ).display_name
        ).toBe("Newly Announced");
        expect(
            mergePeerFromAnnounce(
                { destination_hash: "b".repeat(32), display_name: "Old Name" },
                { destination_hash: "b".repeat(32), display_name: "New Name" }
            ).display_name
        ).toBe("New Name");
    });

    it("protects known names when applying conversation rows", () => {
        const existing = {
            destination_hash: "c".repeat(32),
            display_name: "Known Peer",
            custom_display_name: "My Custom Name",
        };
        const merged = mergePeerFromConversation(existing, {
            destination_hash: "c".repeat(32),
            display_name: "Anonymous Peer",
        });

        expect(merged.display_name).toBe("Known Peer");
        expect(merged.custom_display_name).toBe("My Custom Name");
    });

    it("updates pane names only for a new non-anonymous name", () => {
        expect(shouldUpdatePanePeerDisplayName("Resolved Name", "Anonymous Peer")).toBe(true);
        expect(shouldUpdatePanePeerDisplayName("Anonymous Peer", "Known Name")).toBe(false);
        expect(shouldUpdatePanePeerDisplayName("Known Name", "Known Name")).toBe(false);
    });
});

describe("ContactsPage edit contact name", () => {
    let api;

    beforeEach(() => {
        vi.clearAllMocks();
        registerTranslator((key) => key);
        api = {
            get: vi.fn(),
            post: vi.fn().mockResolvedValue({ data: { message: "OK" } }),
            patch: vi.fn().mockResolvedValue({ data: { message: "Contact updated" } }),
            delete: vi.fn(),
        };
        window.api = api;
    });

    afterEach(() => {
        delete window.api;
        registerTranslator(null);
    });

    it("updates both contact and custom display name", async () => {
        DialogUtils.prompt.mockResolvedValue("Renamed Alice");
        const contact = {
            id: 42,
            name: "Alice",
            remote_identity_hash: "a".repeat(32),
            lxmf_address: "a".repeat(32),
            remote_destination_hash: "a".repeat(32),
        };

        await editContactNameWithDuplicates(contact, [contact], async () => {});

        expect(api.patch).toHaveBeenCalledWith("/api/v1/telephone/contacts/42", {
            name: "Renamed Alice",
        });
        expect(api.post).toHaveBeenCalledWith(
            `/api/v1/destination/${"a".repeat(32)}/custom-display-name/update`,
            { display_name: "Renamed Alice" }
        );
    });

    it("does nothing when the prompt is cancelled or unchanged", async () => {
        DialogUtils.prompt.mockResolvedValueOnce(null).mockResolvedValueOnce("Alice");
        await editContactNameWithDuplicates({ id: 1, name: "Alice" }, [], async () => {});
        await editContactNameWithDuplicates({ id: 1, name: "Alice" }, [], async () => {});
        expect(api.patch).not.toHaveBeenCalled();
        expect(api.post).not.toHaveBeenCalled();
    });

    it("uses the LXMF destination when no remote destination hash exists", async () => {
        DialogUtils.prompt.mockResolvedValue("Updated");
        const contact = {
            id: 10,
            name: "Old",
            remote_identity_hash: "i".repeat(32),
            lxmf_address: "l".repeat(32),
        };

        await editContactNameWithDuplicates(contact, [contact], async () => {});

        expect(api.post).toHaveBeenCalledWith(
            `/api/v1/destination/${"l".repeat(32)}/custom-display-name/update`,
            { display_name: "Updated" }
        );
    });
});
