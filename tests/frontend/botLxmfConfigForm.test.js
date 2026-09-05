import { describe, it, expect } from "vitest";

import {
    buildLxmfConfigPatch,
    defaultLxmfConfigDraft,
    draftFromBotLxmfConfig,
} from "../../meshchatx/src/frontend/features/bots/lib/botLxmfConfigForm.js";

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
        expect(buildLxmfConfigPatch(draft, { clearEmpty: true })).toEqual({
            propagation_mode: "inherit",
            propagation_node: null,
            propagation_fallback_enabled: null,
            direct_delivery_retries: null,
            opportunistic_sending: null,
            announce_interval_seconds: null,
            stamp_cost: null,
        });
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
});
