// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, fireEvent, waitFor, screen } from "@testing-library/svelte";
import MessageBlocklistPage from "@/features/message-blocklist/MessageBlocklistPage.svelte";
import ToastUtils from "@/js/ToastUtils.js";
import DialogUtils from "@/js/DialogUtils.js";
import DownloadUtils from "@/js/DownloadUtils.js";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import {
    createNewBlocklistEntry,
    createDefaultBlocklistConfig,
    mapBlocklistFromApi,
    newEntryId,
    normalizeBlocklistForSave,
    sanitizeBlocklistMatchMode,
    sanitizeBlocklistScope,
} from "@/features/message-blocklist/lib/blocklistRules.ts";
import { API_MESSAGE_BLOCKLIST, API_MESSAGE_BLOCKLIST_EXPORT } from "@/features/message-blocklist/lib/constants.ts";
import { registerMessageBlocklistFeature } from "@/features/message-blocklist/index.ts";
import { clearRoutes, listRoutes } from "@/js/registries/routeRegistry.js";
import { clearFeatureIds, listFeatureIds } from "@/js/registries/featureRegistry.js";

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

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(() => Promise.resolve(false)),
        alert: vi.fn(),
    },
}));

vi.mock("@/js/DownloadUtils", () => ({
    default: {
        downloadFile: vi.fn(() => Promise.resolve()),
    },
}));

describe("message-blocklist lib helpers", () => {
    it("generates random entry id and new blank entry", () => {
        const id = newEntryId();
        expect(typeof id).toBe("string");
        expect(id.length).toBeGreaterThan(0);

        const entry = createNewBlocklistEntry();
        expect(entry.enabled).toBe(true);
        expect(entry.text).toBe("");
        expect(entry.match_mode).toBe("substring");
        expect(typeof entry.id).toBe("string");
    });

    it("sanitizes scope and match mode values", () => {
        expect(sanitizeBlocklistScope("contacts")).toBe("contacts");
        expect(sanitizeBlocklistScope("non_contacts")).toBe("non_contacts");
        expect(sanitizeBlocklistScope("invalid")).toBe("everyone");
        expect(sanitizeBlocklistScope(null)).toBe("everyone");

        expect(sanitizeBlocklistMatchMode("regex")).toBe("regex");
        expect(sanitizeBlocklistMatchMode("substring")).toBe("substring");
        expect(sanitizeBlocklistMatchMode("other")).toBe("substring");
    });

    it("maps raw api payload into sanitized BlocklistConfig", () => {
        const mapped = mapBlocklistFromApi({
            scope: "non_contacts",
            match_peer_fields: false,
            match_message: true,
            entries: [{ id: "e1", enabled: true, text: "spam", match_mode: "substring" }],
        });
        expect(mapped.scope).toBe("non_contacts");
        expect(mapped.match_peer_fields).toBe(false);
        expect(mapped.match_message).toBe(true);
        expect(mapped.entries).toHaveLength(1);
        expect(mapped.entries[0].text).toBe("spam");
    });

    it("creates default config and normalizes config for save", () => {
        const defaults = createDefaultBlocklistConfig();
        expect(defaults.scope).toBe("non_contacts");
        expect(defaults.entries).toHaveLength(0);

        const normalized = normalizeBlocklistForSave({
            scope: "contacts",
            match_peer_fields: true,
            match_message: false,
            entries: [{ id: "1", enabled: true, text: " hello ", match_mode: "substring" }],
        });
        expect(normalized.scope).toBe("contacts");
        expect(normalized.entries[0].text).toBe("hello");
    });
});

describe("registerMessageBlocklistFeature", () => {
    beforeEach(() => {
        clearRoutes();
        clearFeatureIds();
    });

    afterEach(() => {
        clearRoutes();
        clearFeatureIds();
    });

    it("registers message-blocklist route correctly", () => {
        registerMessageBlocklistFeature();
        expect(listFeatureIds()).toContain("message-blocklist");
        const route = listRoutes().find((r) => r.name === "message-blocklist");
        expect(route).toBeTruthy();
        expect(route?.path).toBe("/tools/message-blocklist");
        expect(route?.mount).toBe("svelte");
    });
});

describe("MessageBlocklistPage.svelte", () => {
    let axiosMock;

    beforeEach(() => {
        vi.clearAllMocks();
        axiosMock = {
            get: vi.fn(),
            put: vi.fn(),
            post: vi.fn(),
        };
        window.api = axiosMock;

        registerTranslator(null);
        registerFallbackMessages({
            app: { tools: "Tools" },
            tools: {
                back_to_tools: "Back",
                message_blocklist: {
                    title: "Message Blocklist",
                    description: "Filter inbound messages",
                    beta_notice_title: "Beta Notice",
                    beta_notice_body: "Rules apply locally.",
                    enable_label: "Enable Blocklist",
                    enable_hint: "Drop matching messages",
                    entries_heading: "Blocklist Entries",
                    export: "Export",
                    import: "Import",
                    add_entry: "Add Entry",
                    scope_label: "Scope",
                    scope_everyone: "Everyone",
                    scope_contacts: "Contacts Only",
                    scope_non_contacts: "Non-contacts Only",
                    match_in_label: "Match In",
                    match_message: "Message Body",
                    match_peer_fields: "Sender Fields",
                    empty_entries: "No blocklist entries",
                    entry_enabled: "Active",
                    remove_entry: "Remove",
                    entry_placeholder: "Filter term or pattern",
                    match_mode_substring: "Substring",
                    match_mode_regex: "Regex",
                    save: "Save",
                    saving: "Saving...",
                    saved: "Blocklist saved",
                    revert: "Revert",
                    load_failed: "Failed to load",
                    save_failed: "Failed to save",
                    export_failed: "Failed to export",
                    exported: "Exported",
                    import_failed: "Failed to import",
                    import_merge_confirm: "Merge with existing entries?",
                    imported_merge: "Imported and merged",
                    imported_replace: "Imported and replaced",
                    enabled_toast: "Blocklist enabled",
                    disabled_toast: "Blocklist disabled",
                },
            },
        });

        axiosMock.get.mockImplementation((url) => {
            if (url === API_MESSAGE_BLOCKLIST_EXPORT) {
                return Promise.resolve({
                    data: {
                        schema: "meshchatx.message_blocklist",
                        version: 1,
                        entries: [],
                    },
                });
            }
            if (url === API_MESSAGE_BLOCKLIST) {
                return Promise.resolve({
                    data: {
                        enabled: false,
                        blocklist: {
                            scope: "non_contacts",
                            match_peer_fields: false,
                            match_message: true,
                            entries: [{ id: "e1", enabled: true, text: "spam", match_mode: "substring" }],
                        },
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });

        axiosMock.put.mockResolvedValue({
            data: {
                enabled: true,
                blocklist: {
                    scope: "non_contacts",
                    match_peer_fields: false,
                    match_message: true,
                    entries: [{ id: "e1", enabled: true, text: "spam", match_mode: "substring" }],
                },
            },
        });
    });

    afterEach(() => {
        cleanup();
        delete window.api;
    });

    it("renders and loads blocklist from API", async () => {
        render(MessageBlocklistPage);
        expect(screen.getByText("Message Blocklist")).toBeTruthy();
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith(API_MESSAGE_BLOCKLIST);
        });
        expect(await screen.findByDisplayValue("spam")).toBeTruthy();
    });

    it("saves blocklist via PUT when save button is clicked", async () => {
        render(MessageBlocklistPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith(API_MESSAGE_BLOCKLIST);
        });

        const saveButton = screen.getByText("Save");
        await fireEvent.click(saveButton);

        await waitFor(() => {
            expect(axiosMock.put).toHaveBeenCalledWith(
                API_MESSAGE_BLOCKLIST,
                expect.objectContaining({
                    enabled: false,
                    blocklist: expect.objectContaining({
                        entries: expect.arrayContaining([
                            expect.objectContaining({ text: "spam", match_mode: "substring" }),
                        ]),
                    }),
                })
            );
        });
        expect(ToastUtils.success).toHaveBeenCalledWith("Blocklist saved");
    });

    it("adds a new entry on button click", async () => {
        render(MessageBlocklistPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith(API_MESSAGE_BLOCKLIST);
        });

        const addButton = screen.getByText("Add Entry");
        await fireEvent.click(addButton);

        const inputs = screen.getAllByPlaceholderText("Filter term or pattern");
        expect(inputs.length).toBe(2);

        const saveButton = screen.getByText("Save");
        await fireEvent.click(saveButton);

        await waitFor(() => {
            expect(axiosMock.put).toHaveBeenCalled();
        });
    });

    it("exports blocklist via export endpoint", async () => {
        render(MessageBlocklistPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith(API_MESSAGE_BLOCKLIST);
        });

        const exportButton = screen.getByText("Export");
        await fireEvent.click(exportButton);

        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith(API_MESSAGE_BLOCKLIST_EXPORT);
        });
        expect(DownloadUtils.downloadFile).toHaveBeenCalled();
        expect(ToastUtils.success).toHaveBeenCalledWith("Exported");
    });
});
