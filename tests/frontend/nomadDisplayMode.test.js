// SPDX-License-Identifier: 0BSD
import { describe, it, expect, beforeEach } from "vitest";
import {
    computeNomadFitScale,
    getNomadDisplayMode,
    setNomadDisplayMode,
    normalizeNomadDisplayMode,
    NOMAD_DISPLAY_MODE_KEY,
    NOMAD_DISPLAY_MODE_EVENT,
} from "../../meshchatx/src/frontend/js/nomadDisplayMode.js";

describe("nomadDisplayMode", () => {
    beforeEach(() => {
        window.localStorage.clear();
    });

    it("defaults to fit when nothing is stored", () => {
        expect(getNomadDisplayMode()).toBe("fit");
    });

    it("persists the choice and rejects unknown values", () => {
        expect(setNomadDisplayMode("scroll")).toBe("scroll");
        expect(window.localStorage.getItem(NOMAD_DISPLAY_MODE_KEY)).toBe("scroll");
        expect(getNomadDisplayMode()).toBe("scroll");
        expect(setNomadDisplayMode("bogus")).toBe("scroll");
        expect(getNomadDisplayMode()).toBe("scroll");
    });

    it("dispatches a change event with the new mode", () => {
        let detail = null;
        const listener = (e) => {
            detail = e.detail;
        };
        window.addEventListener(NOMAD_DISPLAY_MODE_EVENT, listener);
        setNomadDisplayMode("scroll");
        window.removeEventListener(NOMAD_DISPLAY_MODE_EVENT, listener);
        expect(detail).toBe("scroll");
    });

    it("normalizeNomadDisplayMode only accepts fit and scroll", () => {
        expect(normalizeNomadDisplayMode("fit")).toBe("fit");
        expect(normalizeNomadDisplayMode("scroll")).toBe("scroll");
        expect(normalizeNomadDisplayMode("")).toBe(null);
        expect(normalizeNomadDisplayMode(42)).toBe(null);
    });

    it("computeNomadFitScale shrinks wide content and clamps to the floor", () => {
        expect(computeNomadFitScale(800, 400)).toBe(0.5);
        expect(computeNomadFitScale(400, 400)).toBe(1);
        expect(computeNomadFitScale(200, 400)).toBe(1);
        expect(computeNomadFitScale(10000, 100)).toBe(0.05);
        expect(computeNomadFitScale(0, 400)).toBe(1);
        expect(computeNomadFitScale(800, 0)).toBe(1);
        expect(computeNomadFitScale(NaN, 400)).toBe(1);
    });
});
