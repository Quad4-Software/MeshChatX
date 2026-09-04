/* SPDX-License-Identifier: 0BSD */
import { describe, it, expect } from "vitest";
import {
    channelBadgeClass,
    channelBugReportTarget,
    channelLabelKey,
    channelPromptSeenKey,
    normalizeReleaseChannel,
    shouldShowChannelPrompt,
} from "../../meshchatx/src/frontend/js/releaseChannel.js";

describe("releaseChannel", () => {
    it("normalizes legacy channel names", () => {
        expect(normalizeReleaseChannel("nightly")).toBe("testing");
        expect(normalizeReleaseChannel("preview")).toBe("beta");
        expect(normalizeReleaseChannel("preview-dev")).toBe("beta");
        expect(normalizeReleaseChannel("release")).toBe("stable");
        expect(normalizeReleaseChannel("testing")).toBe("testing");
        expect(normalizeReleaseChannel("")).toBe("local");
    });

    it("maps label keys and badge classes", () => {
        expect(channelLabelKey("testing")).toBe("about.channel_testing");
        expect(channelLabelKey("beta")).toBe("about.channel_beta");
        expect(channelBadgeClass("stable")).toContain("emerald");
        expect(channelBadgeClass("testing")).toContain("amber");
    });

    it("builds seen keys and gates the prompt", () => {
        const info = {
            build_channel: "testing",
            version: "4.8.6",
            display_version: "4.8.6-dev",
            git_commit_short: "abcdef0",
            channel_prompt_seen: "",
        };
        expect(channelPromptSeenKey(info)).toBe("testing:4.8.6-dev:abcdef0");
        expect(shouldShowChannelPrompt(info)).toBe(true);
        expect(
            shouldShowChannelPrompt({
                ...info,
                channel_prompt_seen: "testing:4.8.6-dev:abcdef0",
            })
        ).toBe(false);
        expect(shouldShowChannelPrompt({ ...info, build_channel: "stable" })).toBe(false);
        expect(shouldShowChannelPrompt({ ...info, build_channel: "local" })).toBe(false);
    });

    it("prefers LXMF bug report target", () => {
        expect(
            channelBugReportTarget({
                bug_report_lxmf: "f489752fbef161c64d65e385a4e9fc74",
                bug_report_url: "https://example.test",
            })
        ).toEqual({ kind: "lxmf", value: "f489752fbef161c64d65e385a4e9fc74" });
    });
});
