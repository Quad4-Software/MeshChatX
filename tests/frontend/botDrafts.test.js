// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import {
    buildCustomPayload,
    buildRrcPayload,
    defaultCustomDraft,
    defaultRrcDraft,
    draftFromBotCustom,
    draftFromBotRrc,
} from "../../meshchatx/src/frontend/features/bots/lib/botDrafts.ts";

describe("botDrafts", () => {
    it("builds a custom payload from named commands only", () => {
        const payload = buildCustomPayload({
            welcome: " hi ",
            commands: [
                { name: " joke ", response: " ha ", description: "" },
                { name: "", response: "skip" },
                { name: "who", response: "me", description: " info " },
            ],
        });
        expect(payload).toEqual({
            welcome: "hi",
            commands: [
                { name: "joke", response: "ha" },
                { name: "who", response: "me", description: "info" },
            ],
        });
    });

    it("omits welcome when blank", () => {
        const payload = buildCustomPayload({
            welcome: "  ",
            commands: [{ name: "a", response: "b", description: "" }],
        });
        expect(payload).toEqual({ commands: [{ name: "a", response: "b" }] });
    });

    it("round-trips a stored custom config into a draft", () => {
        const draft = draftFromBotCustom({
            welcome: "hey",
            commands: [{ name: "x", response: "y" }, "junk", { response: "no-name" }],
        });
        expect(draft.welcome).toBe("hey");
        expect(draft.commands).toEqual([{ name: "x", response: "y", description: "" }]);
    });

    it("builds an rrc payload with normalized hub and rooms", () => {
        const payload = buildRrcPayload({
            hub: " AABBCCDDEEFF00112233445566778899 ",
            rooms: "#Lobby, general,, ",
            nick: " helper ",
            mention_only: false,
            prefix: "?",
            rate_seconds: "5",
        });
        expect(payload).toEqual({
            hub: "aabbccddeeff00112233445566778899",
            rooms: ["Lobby", "general"],
            nick: "helper",
            mention_only: false,
            prefix: "?",
            rate_seconds: 5,
        });
    });

    it("clamps rrc rate seconds and defaults missing fields", () => {
        const payload = buildRrcPayload({
            ...defaultRrcDraft(),
            rate_seconds: "99999",
        });
        expect(payload.rate_seconds).toBe(3600);
        expect(payload.prefix).toBe("!");
        expect(payload.mention_only).toBe(true);
        expect(payload.nick).toBeNull();
    });

    it("round-trips a stored rrc config into a draft", () => {
        const draft = draftFromBotRrc({
            hub: "aa".repeat(16),
            rooms: ["a", "b"],
            nick: "bot",
            mention_only: false,
            prefix: ".",
            rate_seconds: 12,
        });
        expect(draft).toEqual({
            hub: "aa".repeat(16),
            rooms: "a, b",
            nick: "bot",
            mention_only: false,
            prefix: ".",
            rate_seconds: "12",
        });
        expect(draftFromBotRrc(null)).toEqual(defaultRrcDraft());
    });
});
