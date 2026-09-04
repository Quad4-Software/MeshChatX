/* SPDX-License-Identifier: 0BSD */
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ChannelPromptModal from "@/components/ChannelPromptModal.vue";
import { channelPromptSeenKey } from "@/js/releaseChannel.js";

describe("ChannelPromptModal.vue", () => {
    let apiMock;

    const appInfo = {
        build_channel: "testing",
        version: "4.8.6",
        display_version: "4.8.6-dev",
        git_commit_short: "abcdef0",
        channel_prompt_seen: "",
        channel_prompt: {
            focus_areas: ["messaging"],
            bug_report_steps: ["Open About"],
            bug_report_lxmf: "f489752fbef161c64d65e385a4e9fc74",
            notes: "",
        },
    };

    beforeEach(() => {
        apiMock = {
            get: vi.fn(),
            post: vi.fn().mockResolvedValue({ data: { message: "ok" } }),
        };
        window.api = apiMock;
    });

    const mountModal = () =>
        mount(ChannelPromptModal, {
            global: {
                mocks: {
                    $t: (key, params) => (params ? `${key}:${JSON.stringify(params)}` : key),
                },
                stubs: {
                    AppUpdatePrompt: {
                        name: "AppUpdatePrompt",
                        props: ["modelValue", "title", "description", "primaryLabel", "secondaryLabel"],
                        emits: ["update:modelValue", "primary", "secondary"],
                        template: `
                            <div class="app-update-prompt" v-if="modelValue">
                                <slot />
                                <button type="button" data-testid="primary" @click="$emit('primary')">primary</button>
                            </div>
                        `,
                    },
                },
            },
        });

    it("posts channel-prompt seen on dismiss and stops re-showing", async () => {
        const wrapper = mountModal();
        const info = { ...appInfo };
        expect(wrapper.vm.show(info)).toBe(true);
        expect(wrapper.vm.visible).toBe(true);

        await wrapper.vm.onDismiss();

        const expectedKey = channelPromptSeenKey(info);
        expect(apiMock.post).toHaveBeenCalledWith("/api/v1/app/channel-prompt/seen", {
            key: expectedKey,
        });
        expect(info.channel_prompt_seen).toBe(expectedKey);
        expect(wrapper.vm.visible).toBe(false);
        expect(wrapper.vm.show(info)).toBe(false);
    });
});
