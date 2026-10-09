// SPDX-License-Identifier: 0BSD

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import RelayMessageEntry from "@/components/relay/RelayMessageEntry.vue";
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
            mountEntry(actionEntry({ dup_count: 1 })).find('[data-testid="duplicate-count"]').exists()
        ).toBe(false);
        expect(
            mountEntry(actionEntry()).find('[data-testid="duplicate-count"]').exists()
        ).toBe(false);
    });

    it("omits the badge when the page pref is off", () => {
        const page = makePage({ showDupCount: () => false });
        const wrapper = mountEntry(actionEntry({ dup_count: 3 }), page);
        expect(wrapper.find('[data-testid="duplicate-count"]').exists()).toBe(false);
    });
});
