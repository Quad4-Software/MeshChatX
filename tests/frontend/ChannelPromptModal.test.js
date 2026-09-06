/* SPDX-License-Identifier: 0BSD */
import { cleanup, render } from "@testing-library/svelte";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ChannelPromptModal from "@/features/app-shell/components/ChannelPromptModal.svelte";
import { channelPromptSeenKey } from "@/js/releaseChannel.js";

describe("ChannelPromptModal.svelte", () => {
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

    afterEach(() => {
        cleanup();
    });

    it("posts channel-prompt seen on dismiss and stops re-showing", async () => {
        const { component } = render(ChannelPromptModal);
        const info = { ...appInfo };
        expect(component.show(info)).toBe(true);

        await component.onDismiss();

        const expectedKey = channelPromptSeenKey(info);
        expect(apiMock.post).toHaveBeenCalledWith("/api/v1/app/channel-prompt/seen", {
            key: expectedKey,
        });
        expect(info.channel_prompt_seen).toBe(expectedKey);
        expect(component.show(info)).toBe(false);
    });
});
