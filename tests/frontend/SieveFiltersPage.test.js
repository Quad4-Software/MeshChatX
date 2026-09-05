// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, fireEvent, waitFor, screen } from "@testing-library/svelte";
import SieveFiltersPage from "@/features/sieve-filters/SieveFiltersPage.svelte";
import ToastUtils from "@/js/ToastUtils.js";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import {
    createDefaultRule,
    ensureValidAction,
    ensureValidMatchTargets,
    formatTermsText,
    mapRuleFromApi,
    newRuleId,
    normalizeFiltersForSave,
    normalizeRuleForSave,
    parseTermsInput,
    reorderRules,
} from "@/features/sieve-filters/lib/sieveRules.ts";
import { registerSieveFiltersFeature } from "@/features/sieve-filters/index.ts";
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

describe("sieve-filters lib helpers", () => {
    it("generates unique rule id and default rule", () => {
        const id = newRuleId();
        expect(typeof id).toBe("string");
        expect(id.length).toBeGreaterThan(0);

        const folders = [{ id: 10, name: "Spam" }];
        const rule = createDefaultRule(folders);
        expect(rule.enabled).toBe(true);
        expect(rule.scope).toBe("everyone");
        expect(rule.action).toBe("ignore");
        expect(rule.folder_id).toBe(10);
        expect(rule.match_peer_fields).toBe(true);
        expect(rule.match_message).toBe(false);
    });

    it("maps raw api payload correctly and converts block to hide", () => {
        const raw = { action: "block", terms: ["spam", "ad"], scope: "contacts" };
        const mapped = mapRuleFromApi(raw);
        expect(mapped.action).toBe("hide");
        expect(mapped.terms).toEqual(["spam", "ad"]);
        expect(mapped.scope).toBe("contacts");
    });

    it("normalizes rules for save payload", () => {
        const rule = {
            id: "r1",
            enabled: true,
            scope: "non_contacts",
            terms: ["xyz"],
            action: "hide",
            folder_id: 5,
            match_peer_fields: false,
            match_message: false,
            match_mode: "substring",
        };
        const normalized = normalizeRuleForSave(rule);
        expect(normalized.match_peer_fields).toBe(true);
        expect(normalized.folder_id).toBeNull();

        const batch = normalizeFiltersForSave([rule]);
        expect(batch).toHaveLength(1);
    });

    it("parses and formats terms input", () => {
        expect(parseTermsInput("a, b\nc\n\n")).toEqual(["a", "b", "c"]);
        expect(formatTermsText(["foo", "bar"])).toBe("foo\nbar");
    });

    it("reorders rules by delta", () => {
        const r1 = createDefaultRule();
        const r2 = createDefaultRule();
        const list = [r1, r2];

        const moved = reorderRules(list, 0, 1);
        expect(moved[0].id).toBe(r2.id);
        expect(moved[1].id).toBe(r1.id);

        const outOfBounds = reorderRules(list, 0, -1);
        expect(outOfBounds).toBe(list);
    });

    it("ensures valid action and match targets", () => {
        const folders = [{ id: 42, name: "Archive" }];
        const rule = createDefaultRule();
        rule.action = "folder";
        rule.folder_id = null;
        ensureValidAction(rule, folders);
        expect(rule.folder_id).toBe(42);

        rule.action = "hide";
        ensureValidAction(rule, folders);
        expect(rule.folder_id).toBeNull();

        rule.match_peer_fields = false;
        rule.match_message = false;
        ensureValidMatchTargets(rule);
        expect(rule.match_peer_fields).toBe(true);
    });
});

describe("registerSieveFiltersFeature", () => {
    beforeEach(() => {
        clearRoutes();
        clearFeatureIds();
    });

    afterEach(() => {
        clearRoutes();
        clearFeatureIds();
    });

    it("registers sieve-filters route correctly", () => {
        registerSieveFiltersFeature();
        expect(listFeatureIds()).toContain("sieve-filters");
        const route = listRoutes().find((r) => r.name === "sieve-filters");
        expect(route).toBeTruthy();
        expect(route?.path).toBe("/tools/sieve-filters");
        expect(route?.mount).toBe("svelte");
    });
});

describe("SieveFiltersPage.svelte", () => {
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
                sieve_filters: {
                    title: "Sieve Filters",
                    description: "Rule-based message filtering",
                    rules_heading: "Filter Rules",
                    add_rule: "Add Rule",
                    order_hint: "Rules evaluated in order",
                    empty_rules: "No rules configured",
                    save: "Save",
                    saving: "Saving...",
                    saved: "Filters saved",
                    revert: "Revert",
                    load_failed: "Failed to load filters",
                    save_failed: "Failed to save filters",
                    flow_heading: "Execution Flow",
                    flow_source: "Inbound LXMF Message",
                    flow_source_hint: "Evaluated top to bottom",
                    flow_if: "Rule",
                    flow_hide: "Hide Message",
                    action_ignore: "Ignore Message",
                    flow_banish: "Banish Sender",
                    flow_folder: "Move to Folder",
                    flow_no_rules: "No Rules Configured",
                    graph_scope_everyone: "Everyone",
                    graph_scope_contacts: "Contacts Only",
                    graph_scope_non_contacts: "Non-contacts Only",
                    graph_match_peer: "Sender Info",
                    graph_match_message: "Message Body",
                    graph_match_mode_substring: "Substring",
                    graph_match_mode_regex: "Regex",
                    terms_label: "Match Terms",
                    terms_placeholder: "Enter terms separated by commas or newlines",
                    rule_title: "Rule #{index}",
                    action_label: "Action",
                    action_hide: "Hide",
                    action_folder: "Move to folder",
                    action_banish: "Banish",
                    match_in_label: "Match Targets",
                    match_peer_fields: "Sender info",
                    match_message: "Message content",
                    scope_label: "Scope",
                    scope_everyone: "Everyone",
                    scope_contacts: "Contacts only",
                    scope_non_contacts: "Non-contacts only",
                    match_mode_label: "Mode",
                    match_mode_substring: "Substring",
                    match_mode_regex: "Regex",
                    folder_label: "Folder",
                    remove_rule: "Remove Rule",
                    move_up: "Move Up",
                    move_down: "Move Down",
                },
            },
        });

        axiosMock.get.mockImplementation((url) => {
            if (url.includes("sieve-filters")) {
                return Promise.resolve({
                    data: {
                        filters: [
                            {
                                id: "r1",
                                enabled: true,
                                scope: "everyone",
                                terms: ["spam"],
                                action: "ignore",
                                folder_id: null,
                                match_peer_fields: true,
                                match_message: false,
                                match_mode: "substring",
                            },
                        ],
                    },
                });
            }
            if (url.includes("folders")) {
                return Promise.resolve({ data: [{ id: 1, name: "Inbox" }] });
            }
            return Promise.resolve({ data: {} });
        });

        axiosMock.put.mockResolvedValue({
            data: {
                filters: [
                    {
                        id: "r1",
                        enabled: true,
                        scope: "everyone",
                        terms: ["spam"],
                        action: "ignore",
                        folder_id: null,
                        match_peer_fields: true,
                        match_message: false,
                        match_mode: "substring",
                    },
                ],
            },
        });
    });

    afterEach(() => {
        cleanup();
        delete window.api;
    });

    it("loads filters and folders from the API", async () => {
        render(SieveFiltersPage);
        expect(screen.getByText("Sieve Filters")).toBeTruthy();

        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/lxmf/sieve-filters");
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/lxmf/folders");
        });

        expect(await screen.findByDisplayValue("spam")).toBeTruthy();
    });

    it("saves filters via PUT when save button is clicked", async () => {
        render(SieveFiltersPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/lxmf/sieve-filters");
        });

        const saveButton = screen.getByText("Save");
        await fireEvent.click(saveButton);

        await waitFor(() => {
            expect(axiosMock.put).toHaveBeenCalledWith(
                "/api/v1/lxmf/sieve-filters",
                expect.objectContaining({
                    filters: expect.arrayContaining([
                        expect.objectContaining({
                            terms: ["spam"],
                            match_peer_fields: true,
                            match_message: false,
                            match_mode: "substring",
                        }),
                    ]),
                })
            );
        });
        expect(ToastUtils.success).toHaveBeenCalledWith("Filters saved");
    });

    it("adds a rule on button click", async () => {
        render(SieveFiltersPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/lxmf/sieve-filters");
        });

        const addButton = screen.getByText("Add Rule");
        await fireEvent.click(addButton);

        const ruleCards = screen.getAllByPlaceholderText("Enter terms separated by commas or newlines");
        expect(ruleCards.length).toBe(2);
    });

    it("toasts API errors on save", async () => {
        axiosMock.put.mockRejectedValue({
            response: { data: { message: "Unknown folder_id 9" } },
        });

        render(SieveFiltersPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/lxmf/sieve-filters");
        });

        const saveButton = screen.getByText("Save");
        await fireEvent.click(saveButton);

        await waitFor(() => {
            expect(ToastUtils.error).toHaveBeenCalledWith("Unknown folder_id 9");
        });
    });
});
