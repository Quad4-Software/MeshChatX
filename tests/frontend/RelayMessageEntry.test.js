// SPDX-License-Identifier: 0BSD

import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import RelayMessageEntry from "@/components/relay/RelayMessageEntry.vue";
import { renderRelayMicronHtml } from "@/js/relay/relayMicron.js";
import { createTestI18n } from "./testI18n.js";

function makePage(overrides = {}) {
    return {
        showDupCount: (msg) => Number(msg?.dup_count) > 1,
        formatTime: () => "12:00",
        displayName: () => "carol",
        nameStyle: () => "",
        renderMessageHtml: (text) => text,
        handleMessageHtmlClick: () => {},
        messageKey: (msg) => `seq-${msg.seq}`,
        relayMessageDisplayText: (msg) => msg.text,
        relayMessageTranslation: () => null,
        toggleRelayMessageOriginal: () => {},
        retryRelayMessage: () => {},
        ...overrides,
    };
}

function mountEntry(entry, page = makePage()) {
    return mount(RelayMessageEntry, {
        props: { entry, page },
        global: { plugins: [createTestI18n()] },
    });
}

const actionEntry = (overrides = {}) => ({
    type: "message",
    msg: {
        kind: "action",
        seq: 1,
        text: "waves",
        ts: 1,
        nick: "carol",
        ...overrides,
    },
});

describe("RelayMessageEntry.vue", () => {
    it("shows the repeat badge on action rows", () => {
        const wrapper = mountEntry(actionEntry({ dup_count: 2 }));
        expect(wrapper.find('[data-testid="duplicate-count"]').text()).toBe("x2");
    });

    it("shows the repeat badge on message rows", () => {
        const wrapper = mountEntry({
            type: "message",
            msg: { kind: "msg", seq: 2, text: "hello", ts: 1, nick: "carol", dup_count: 5 },
        });
        expect(wrapper.find('[data-testid="duplicate-count"]').text()).toBe("x5");
    });

    it("omits the badge when the count is one or absent", () => {
        expect(
            mountEntry(actionEntry({ dup_count: 1 }))
                .find('[data-testid="duplicate-count"]')
                .exists()
        ).toBe(false);
        expect(mountEntry(actionEntry()).find('[data-testid="duplicate-count"]').exists()).toBe(false);
    });

    it("omits the badge when the page pref is off", () => {
        const page = makePage({ showDupCount: () => false });
        const wrapper = mountEntry(actionEntry({ dup_count: 3 }), page);
        expect(wrapper.find('[data-testid="duplicate-count"]').exists()).toBe(false);
    });

    describe("Micron art", () => {
        const msgEntry = (text, seq = 3) => ({
            type: "message",
            msg: { kind: "msg", seq, text, ts: 1, nick: "carol" },
        });

        it("draws a message with Micron colour as one unwrapped monospace line", () => {
            const page = makePage({ renderMessageHtml: (text) => renderRelayMicronHtml(text) });
            const wrapper = mountEntry(msgEntry("  ¦B00f  ¦b ¦Ff00x"), page);
            const row = wrapper.find('[data-msg-key="seq-3"]');
            expect(row.classes()).not.toContain("py-1");
            expect(wrapper.find("[data-micron-art]").classes()).toContain("flex");
            const body = wrapper.find('[data-testid="relay-message-body"]');
            expect(body.classes()).toEqual(expect.arrayContaining(["font-mono", "whitespace-pre", "overflow-hidden"]));
            expect(body.classes()).not.toContain("wrap-break-word");
            expect(body.element.textContent).toBe("     x");
        });

        it("keeps plain messages on the existing wrapped layout", () => {
            const renderMessageHtml = vi.fn((text) => text);
            const wrapper = mountEntry(msgEntry("hello  world"), makePage({ renderMessageHtml }));
            expect(renderMessageHtml).toHaveBeenCalledWith("hello  world");
            expect(wrapper.find("[data-micron-art]").exists()).toBe(false);
            expect(wrapper.find('[data-msg-key="seq-3"]').classes()).toEqual(
                expect.arrayContaining(["rounded-lg", "py-1"])
            );
            const body = wrapper.find('[data-testid="relay-message-body"]');
            expect(body.classes()).toEqual(["whitespace-pre-wrap", "wrap-break-word"]);
        });

        it("keeps formatted text without colour on the wrapped layout", () => {
            const wrapper = mountEntry(msgEntry("¦!bold¦! words"));
            expect(wrapper.find("[data-micron-art]").exists()).toBe(false);
        });

        it("asks for tags to be stripped from actions", () => {
            const renderMessageHtml = vi.fn((text) => text);
            mountEntry(actionEntry({ text: "¦Ff00waves" }), makePage({ renderMessageHtml }));
            expect(renderMessageHtml).toHaveBeenCalledWith("¦Ff00waves", { stripMicron: true });
        });
    });
});
