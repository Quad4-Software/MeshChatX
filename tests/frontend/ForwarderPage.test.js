import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, fireEvent, waitFor } from "@testing-library/svelte";
import ForwarderPage from "@/features/forwarder/ForwarderPage.svelte";
import WebSocketConnection from "@/js/WebSocketConnection";
import ToastUtils from "@/js/ToastUtils";
import DialogUtils from "@/js/DialogUtils";
import { dispatchWsEvent } from "@/js/registries/wsEventRegistry.js";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import { isValidForwarderDestinationHash } from "@/features/forwarder/lib/forwarderHash.ts";

vi.mock("@/js/WebSocketConnection", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
        send: vi.fn(() => true),
    },
}));

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
    },
}));

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(() => Promise.resolve(true)),
    },
}));

describe("forwarderHash", () => {
    it("accepts 32 hex chars", () => {
        expect(isValidForwarderDestinationHash("a".repeat(32))).toBe(true);
        expect(isValidForwarderDestinationHash("not-a-hash")).toBe(false);
    });
});

describe("ForwarderPage.svelte", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        WebSocketConnection.send.mockReturnValue(true);
        registerTranslator(null);
        registerFallbackMessages({
            app: { tools: "Tools" },
            tools: {
                back_to_tools: "Back",
                forwarder: {
                    title: "forwarder.title",
                    description: "desc",
                },
            },
            forwarder: {
                add_rule: "forwarder.add_rule",
                name: "Name",
                name_placeholder: "Name",
                forward_to_hash: "Hash",
                destination_placeholder: "dest",
                source_filter: "Source",
                source_filter_placeholder: "src",
                add_button: "Add",
                active_rules: "Rules",
                no_rules: "None",
                active: "forwarder.active",
                disabled: "forwarder.disabled",
                forwarding_to: "to {hash}",
                source_filter_display: "from {hash}",
                invalid_hash: "bad",
                send_failed: "fail",
                rule_added: "added",
                delete_confirm: "delete?",
                rule_deleted: "deleted",
            },
            common: { delete: "Delete" },
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("renders the forwarder page", async () => {
        const { getByText } = render(ForwarderPage);
        await waitFor(() => {
            expect(getByText("forwarder.title")).toBeTruthy();
            expect(getByText("forwarder.add_rule")).toBeTruthy();
        });
    });

    it("fetches rules on mount", async () => {
        render(ForwarderPage);
        await waitFor(() => {
            expect(WebSocketConnection.send).toHaveBeenCalledWith(
                JSON.stringify({
                    type: "lxmf.forwarding.rules.get",
                })
            );
        });
    });

    it("adds a new rule", async () => {
        const { container, getByText } = render(ForwarderPage);
        await waitFor(() => expect(getByText("forwarder.add_rule")).toBeTruthy());

        const inputs = container.querySelectorAll('input[type="text"]');
        await fireEvent.input(inputs[0], { target: { value: "Test Rule" } });
        await fireEvent.input(inputs[1], { target: { value: "a".repeat(32) } });

        await fireEvent.click(container.querySelector("button.bg-blue-600"));

        expect(WebSocketConnection.send).toHaveBeenCalledWith(
            JSON.stringify({
                type: "lxmf.forwarding.rule.add",
                rule: {
                    name: "Test Rule",
                    forward_to_hash: "a".repeat(32),
                    source_filter_hash: "",
                    is_active: true,
                },
            })
        );
    });

    it("handles incoming rules from websocket", async () => {
        const { getByText } = render(ForwarderPage);
        await waitFor(() => expect(WebSocketConnection.send).toHaveBeenCalled());
        await dispatchWsEvent("lxmf.forwarding.rules", {
            type: "lxmf.forwarding.rules",
            rules: [{ id: "rule1", name: "Rule 1", forward_to_hash: "hash1", is_active: true }],
        });
        await waitFor(() => expect(getByText("Rule 1")).toBeTruthy());
    });

    it("toggles a rule", async () => {
        const { getByTitle } = render(ForwarderPage);
        await waitFor(() => expect(WebSocketConnection.send).toHaveBeenCalled());
        await dispatchWsEvent("lxmf.forwarding.rules", {
            rules: [{ id: "rule1", name: "Rule 1", forward_to_hash: "hash1", is_active: true }],
        });
        await waitFor(() => expect(getByTitle("forwarder.disabled")).toBeTruthy());
        await fireEvent.click(getByTitle("forwarder.disabled"));

        expect(WebSocketConnection.send).toHaveBeenCalledWith(
            JSON.stringify({
                type: "lxmf.forwarding.rule.toggle",
                id: "rule1",
            })
        );
    });

    it("rejects a non-hex destination hash", async () => {
        const { container, getByText } = render(ForwarderPage);
        await waitFor(() => expect(getByText("forwarder.add_rule")).toBeTruthy());
        const inputs = container.querySelectorAll('input[type="text"]');
        await fireEvent.input(inputs[0], { target: { value: "bad" } });
        await fireEvent.input(inputs[1], { target: { value: "not-a-hash" } });
        await fireEvent.click(container.querySelector("button.bg-blue-600"));
        expect(ToastUtils.warning).toHaveBeenCalled();
        const addCalls = WebSocketConnection.send.mock.calls.filter((call) =>
            String(call[0]).includes("lxmf.forwarding.rule.add")
        );
        expect(addCalls).toHaveLength(0);
    });

    it("deletes a rule after confirm", async () => {
        const { getByTitle } = render(ForwarderPage);
        await waitFor(() => expect(WebSocketConnection.send).toHaveBeenCalled());
        await dispatchWsEvent("lxmf.forwarding.rules", {
            rules: [{ id: "rule1", name: "Rule 1", forward_to_hash: "a".repeat(32), is_active: true }],
        });
        await waitFor(() => expect(getByTitle("Delete")).toBeTruthy());
        await fireEvent.click(getByTitle("Delete"));
        await waitFor(() => expect(DialogUtils.confirm).toHaveBeenCalled());
        expect(WebSocketConnection.send).toHaveBeenCalledWith(
            JSON.stringify({
                type: "lxmf.forwarding.rule.delete",
                id: "rule1",
            })
        );
        expect(ToastUtils.success).toHaveBeenCalled();
    });
});
