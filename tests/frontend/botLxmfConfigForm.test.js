import { describe, it, expect } from "vitest";

import {
    buildLxmfConfigPatch,
    defaultLxmfConfigDraft,
    draftFromBotLxmfConfig,
    parseAdminsDraft,
} from "../../meshchatx/src/frontend/components/tools/internal/botLxmfConfigForm.js";

describe("botLxmfConfigForm", () => {
    it("returns empty patch for default draft", () => {
        expect(buildLxmfConfigPatch(defaultLxmfConfigDraft())).toEqual({});
    });

    it("builds manual propagation patch", () => {
        const draft = defaultLxmfConfigDraft();
        draft.propagation_mode = "manual";
        draft.propagation_node = "a".repeat(32);
        expect(buildLxmfConfigPatch(draft)).toEqual({
            propagation_mode: "manual",
            propagation_node: "a".repeat(32),
        });
    });

    it("clearEmpty sends nulls to drop stored overrides", () => {
        const draft = defaultLxmfConfigDraft();
        draft.direct_delivery_retries = "";
        draft.stamp_cost = "";
        const patch = buildLxmfConfigPatch(draft, { clearEmpty: true });
        expect(patch.propagation_mode).toBe("inherit");
        // every overridable key clears to null so stored overrides drop
        for (const [key, value] of Object.entries(patch)) {
            if (key === "propagation_mode") continue;
            expect(value, key).toBeNull();
        }
        for (const key of Object.keys(defaultLxmfConfigDraft())) {
            expect(patch, key).toHaveProperty(key);
        }
    });

    it("restores stored bot config into draft", () => {
        const draft = draftFromBotLxmfConfig({
            propagation_mode: "autopeer",
            direct_delivery_retries: 2,
            opportunistic_sending: false,
        });
        expect(draft.propagation_mode).toBe("autopeer");
        expect(draft.direct_delivery_retries).toBe("2");
        expect(draft.opportunistic_sending).toBe("false");
    });

    it("builds extended security and anti-spam overrides", () => {
        const draft = defaultLxmfConfigDraft();
        draft.command_prefix = "?";
        draft.signature_verification_enabled = "true";
        draft.require_stamps = "false";
        draft.rate_limit = "7";
        draft.cooldown = "30";
        draft.max_warnings = "2";
        draft.warning_timeout = "120";
        draft.message_queue_size = "80";
        draft.admins = `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n<bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb>, junk`;
        expect(buildLxmfConfigPatch(draft)).toEqual({
            command_prefix: "?",
            signature_verification_enabled: true,
            require_stamps: false,
            rate_limit: 7,
            cooldown: 30,
            max_warnings: 2,
            warning_timeout: 120,
            message_queue_size: 80,
            admins: ["a".repeat(32), "b".repeat(32)],
        });
    });

    it("restores admins list and tri-state security flags into draft", () => {
        const draft = draftFromBotLxmfConfig({
            admins: ["a".repeat(32)],
            require_message_signatures: true,
            permissions_enabled: false,
            command_prefix: "!",
        });
        expect(draft.admins).toBe("a".repeat(32));
        expect(draft.require_message_signatures).toBe("true");
        expect(draft.permissions_enabled).toBe("false");
        expect(draft.command_prefix).toBe("!");
    });

    it("parseAdminsDraft filters non-hash tokens and normalizes", () => {
        expect(parseAdminsDraft("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA, x\n" + "b".repeat(32))).toEqual([
            "a".repeat(32),
            "b".repeat(32),
        ]);
        expect(parseAdminsDraft("")).toEqual([]);
    });
});
