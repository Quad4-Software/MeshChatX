// SPDX-License-Identifier: 0BSD

import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import MiniChat from "@/components/map/MiniChat.vue";

describe("MiniChat.vue", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn(() => Promise.resolve({ data: { lxmf_messages: [] } })),
            post: vi.fn(() =>
                Promise.resolve({
                    data: { lxmf_message: { hash: "abc", content: "hello", created_at: 99 } },
                })
            ),
        };
        window.api = axiosMock;
    });

    afterEach(() => {
        delete window.api;
    });

    const mountMiniChat = () =>
        mount(MiniChat, {
            props: { destinationHash: "a".repeat(32) },
            global: {
                mocks: { $t: (key) => key },
                stubs: { MaterialDesignIcon: true },
            },
        });

    it("fetches recent messages on mount", async () => {
        mountMiniChat();
        await vi.waitFor(() =>
            expect(axiosMock.get).toHaveBeenCalledWith(expect.stringContaining("lxmf-messages/conversation"))
        );
    });

    it("caps the local message list at 40 entries after sending", async () => {
        const wrapper = mountMiniChat();
        await vi.waitFor(() => expect(wrapper.vm.loading).toBe(false));
        for (let i = 0; i < 42; i++) {
            wrapper.vm.messages.push({ content: `msg-${i}`, timestamp: i });
        }

        wrapper.vm.newMessage = "hello";
        await wrapper.vm.sendMessage();

        expect(wrapper.vm.messages.length).toBeLessThanOrEqual(40);
        expect(wrapper.vm.messages.at(-1).content).toBe("hello");
        expect(wrapper.vm.messages[0].content).toBe("msg-3");
    });
});
