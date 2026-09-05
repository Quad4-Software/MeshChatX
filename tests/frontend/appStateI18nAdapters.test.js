// SPDX-License-Identifier: 0BSD

import { describe, it, expect, beforeEach } from "vitest";
import {
    subscribeAppState,
    getAppState,
    patchAppState,
    patchAppConfig,
} from "../../meshchatx/src/frontend/js/appState.js";
import { t, registerTranslator, registerFallbackMessages } from "../../meshchatx/src/frontend/js/i18n.js";

describe("appState adapter", () => {
    it("getAppState returns the same object", () => {
        const state = { a: 1 };
        expect(getAppState(state)).toBe(state);
    });

    it("subscribe receives snapshot and unsubscribe stops updates", () => {
        const state = { n: 0 };
        const seen = [];
        const unsub = subscribeAppState(state, (snap) => seen.push(snap.n));
        expect(seen).toEqual([0]);
        patchAppState(state, { n: 2 });
        expect(seen).toEqual([0, 2]);
        unsub();
        patchAppState(state, { n: 3 });
        expect(seen).toEqual([0, 2]);
        expect(state.n).toBe(3);
    });

    it("patchAppConfig merges config", () => {
        const state = { config: { a: 1 } };
        patchAppConfig(state, { b: 2 });
        expect(state.config).toEqual({ a: 1, b: 2 });
    });
});

describe("i18n adapter", () => {
    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages(null);
    });

    it("returns key when nothing registered", () => {
        expect(t("missing.key")).toBe("missing.key");
    });

    it("uses fallback messages with interpolation", () => {
        registerFallbackMessages({
            hello: "Hi {name}",
            nested: { title: "Title" },
        });
        expect(t("hello", { name: "Ada" })).toBe("Hi Ada");
        expect(t("nested.title")).toBe("Title");
    });

    it("prefers registered translator", () => {
        registerFallbackMessages({ x: "fallback" });
        registerTranslator((key) => (key === "x" ? "from-t" : key));
        expect(t("x")).toBe("from-t");
    });
});
