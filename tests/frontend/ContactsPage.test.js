import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, waitFor, screen } from "@testing-library/svelte";
import ContactsPage from "@/features/contacts/ContactsPage.svelte";
import { parseLxmaUri, extractDestinationHash } from "@/features/contacts/lib/contactUri.js";
import { mergeContactsByName } from "@/features/contacts/lib/mergeContacts.js";
import {
    addContactFromInput,
    exportContactsFile,
    importContactsList,
} from "@/features/contacts/lib/contactsActions.js";
import WebSocketConnection from "@/js/WebSocketConnection";
import ToastUtils from "@/js/ToastUtils";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";

vi.mock("@/js/WebSocketConnection", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
        send: vi.fn(),
    },
}));

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
        loading: vi.fn(),
        dismiss: vi.fn(),
    },
}));

vi.mock("qrcode", () => ({
    default: {
        toDataURL: vi.fn().mockResolvedValue("data:image/png;base64,test"),
    },
}));

describe("contactUri / mergeContacts", () => {
    it("parses lxma URI correctly", () => {
        const result = parseLxmaUri(`lxma://${"c".repeat(32)}:${"d".repeat(128)}`);
        expect(result.destinationHash).toBe("c".repeat(32));
        expect(result.publicKeyHex).toBe("d".repeat(128));
        expect(extractDestinationHash("e".repeat(32))).toBe("e".repeat(32));
    });

    it("merges contacts that share a name", () => {
        const merged = mergeContactsByName([
            { id: 1, name: "A", lxmf_address: "a".repeat(32) },
            { id: 2, name: "A", remote_telephony_hash: "b".repeat(32) },
        ]);
        expect(merged).toHaveLength(1);
        expect(merged[0].lxmf_address).toBe("a".repeat(32));
        expect(merged[0].remote_telephony_hash).toBe("b".repeat(32));
    });
});

describe("ContactsPage.svelte", () => {
    let axiosMock;

    beforeEach(() => {
        vi.clearAllMocks();
        registerTranslator(null);
        registerFallbackMessages({
            contacts: {
                title: "contacts.title",
                description: "desc",
                share_my_identity: "share",
                export_contacts: "contacts.export_contacts",
                import_contacts: "contacts.import_contacts",
                add_contact: "contacts.add_contact",
                search_placeholder: "Search",
                loading: "loading",
                no_contacts: "none",
                load_more: "more",
                failed_load_contacts: "contacts.failed_load_contacts",
            },
            common: { cancel: "Cancel", copy: "Copy" },
        });
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
            delete: vi.fn(),
            patch: vi.fn(),
        };
        window.api = axiosMock;

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/config") {
                return Promise.resolve({
                    data: {
                        config: {
                            lxmf_address_hash: "a".repeat(32),
                            identity_public_key: "b".repeat(128),
                        },
                    },
                });
            }
            if (url === "/api/v1/telephone/contacts/export") {
                return Promise.resolve({ data: { contacts: [] } });
            }
            if (url.startsWith("/api/v1/telephone/contacts/check/")) {
                return Promise.resolve({ data: { is_contact: false, contact: null } });
            }
            if (
                url === "/api/v1/telephone/contacts" ||
                (typeof url === "string" && url.startsWith("/api/v1/telephone/contacts?"))
            ) {
                return Promise.resolve({ data: { contacts: [], total_count: 0 } });
            }
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        cleanup();
        delete window.api;
    });

    it("adds contact using manual destination hash", async () => {
        await addContactFromInput("e".repeat(32), "Test Contact", {
            setPendingLxma: vi.fn(),
            onAdded: vi.fn(async () => {}),
        });
        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/telephone/contacts", {
            name: "Test Contact",
            lxmf_address: "e".repeat(32),
        });
    });

    it("uses websocket ingest for lxma URI input", async () => {
        await addContactFromInput(`lxma://${"f".repeat(32)}:${"1".repeat(128)}`, "", {
            setPendingLxma: vi.fn(),
            onAdded: vi.fn(async () => {}),
        });
        expect(WebSocketConnection.send).toHaveBeenCalledWith(
            JSON.stringify({
                type: "lxm.ingest_uri",
                uri: `lxma://${"f".repeat(32)}:${"1".repeat(128)}`,
            })
        );
        expect(axiosMock.post).not.toHaveBeenCalled();
    });

    it("exports contacts via GET /api/v1/telephone/contacts/export", async () => {
        vi.stubGlobal(
            "Blob",
            class {
                constructor() {}
            }
        );
        const DownloadUtils = await import("@/js/DownloadUtils");
        vi.spyOn(DownloadUtils.default, "downloadFile").mockResolvedValue(undefined);
        await exportContactsFile();
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/telephone/contacts/export");
        vi.unstubAllGlobals();
    });

    it("imports contacts via POST /api/v1/telephone/contacts/import", async () => {
        axiosMock.post.mockResolvedValue({ data: { added: 2, skipped: 0 } });
        await importContactsList(
            [
                { name: "A", remote_identity_hash: "a".repeat(32) },
                { name: "B", remote_identity_hash: "b".repeat(32) },
            ],
            async () => {}
        );
        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/telephone/contacts/import", {
            contacts: [
                { name: "A", remote_identity_hash: "a".repeat(32) },
                { name: "B", remote_identity_hash: "b".repeat(32) },
            ],
        });
    });

    it("mounts within 500ms", () => {
        const start = performance.now();
        render(ContactsPage);
        const elapsed = performance.now() - start;
        expect(screen.getByText("contacts.title")).toBeTruthy();
        expect(elapsed).toBeLessThan(500);
    });

    it("export and import buttons are present", async () => {
        render(ContactsPage);
        expect(await screen.findByTitle("contacts.export_contacts")).toBeTruthy();
        expect(screen.getByTitle("contacts.import_contacts")).toBeTruthy();
    });

    it("renders floating add-contact action for mobile layout", async () => {
        render(ContactsPage);
        expect(await screen.findByTitle("contacts.add_contact")).toBeTruthy();
    });

    it("getContacts maps total_count from telephone contacts API", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/config") {
                return Promise.resolve({
                    data: {
                        config: {
                            lxmf_address_hash: "a".repeat(32),
                            identity_public_key: "b".repeat(128),
                        },
                    },
                });
            }
            if (
                url === "/api/v1/telephone/contacts" ||
                (typeof url === "string" && url.startsWith("/api/v1/telephone/contacts?"))
            ) {
                return Promise.resolve({
                    data: {
                        contacts: [{ id: 1, name: "One", remote_identity_hash: "c".repeat(32) }],
                        total_count: 42,
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });
        render(ContactsPage);
        expect(await screen.findByText("One")).toBeTruthy();
    });

    it("toasts failed_load_contacts when contacts GET fails", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/config") {
                return Promise.resolve({
                    data: {
                        config: {
                            lxmf_address_hash: "a".repeat(32),
                            identity_public_key: "b".repeat(128),
                        },
                    },
                });
            }
            if (
                url === "/api/v1/telephone/contacts" ||
                (typeof url === "string" && url.startsWith("/api/v1/telephone/contacts?"))
            ) {
                return Promise.reject(
                    Object.assign(new Error("HTTP 500"), {
                        response: { status: 500, data: { error: "boom" } },
                    })
                );
            }
            return Promise.resolve({ data: {} });
        });

        render(ContactsPage);
        await waitFor(() => expect(ToastUtils.error).toHaveBeenCalledWith("contacts.failed_load_contacts"));
    });
});
