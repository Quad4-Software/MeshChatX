// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import {
    isLoopbackOrLanIp,
    sessionsAreLocalOnly,
    shouldWarnMultiSession,
    shouldShowMultiSessionToast,
} from "../../meshchatx/src/frontend/js/activeSessions.js";

describe("activeSessions oracles", () => {
    it("classifies loopback and lan addresses", () => {
        expect(isLoopbackOrLanIp("127.0.0.1")).toBe(true);
        expect(isLoopbackOrLanIp("::1")).toBe(true);
        expect(isLoopbackOrLanIp("[::1]")).toBe(true);
        expect(isLoopbackOrLanIp("10.1.2.3")).toBe(true);
        expect(isLoopbackOrLanIp("192.168.0.10")).toBe(true);
        expect(isLoopbackOrLanIp("172.16.0.1")).toBe(true);
        expect(isLoopbackOrLanIp("169.254.1.1")).toBe(true);
        expect(isLoopbackOrLanIp("fd12::1")).toBe(true);
        expect(isLoopbackOrLanIp("fe80::1")).toBe(true);
        expect(isLoopbackOrLanIp("8.8.8.8")).toBe(false);
        expect(isLoopbackOrLanIp("unknown")).toBe(false);
        expect(sessionsAreLocalOnly([{ ip: "127.0.0.1" }, { ip: "10.0.0.2" }])).toBe(true);
        expect(sessionsAreLocalOnly([{ ip: "127.0.0.1" }, { ip: "1.1.1.1" }])).toBe(false);
    });

    it("warns only when count is at least two and setting is on", () => {
        expect(shouldWarnMultiSession(0, true)).toBe(false);
        expect(shouldWarnMultiSession(1, true)).toBe(false);
        expect(shouldWarnMultiSession(2, true)).toBe(true);
        expect(shouldWarnMultiSession(5, true)).toBe(true);
        expect(shouldWarnMultiSession(2, false)).toBe(false);
        expect(shouldWarnMultiSession(2, undefined)).toBe(true);
        expect(shouldWarnMultiSession(Number.NaN, true)).toBe(false);
    });

    it("does not warn when every session is localhost or lan", () => {
        const local = [{ ip: "127.0.0.1" }, { ip: "192.168.1.5" }];
        expect(shouldWarnMultiSession(2, true, local)).toBe(false);
        expect(shouldWarnMultiSession(2, true, [{ ip: "1.1.1.1" }, { ip: "2.2.2.2" }])).toBe(true);
        expect(shouldWarnMultiSession(2, true, [{ ip: "127.0.0.1" }, { ip: "8.8.8.8" }])).toBe(true);
    });

    it("toasts once per multi-session episode", () => {
        expect(shouldShowMultiSessionToast(1, true, false)).toEqual({
            show: false,
            warned: false,
        });
        expect(shouldShowMultiSessionToast(2, true, false)).toEqual({
            show: true,
            warned: true,
        });
        expect(shouldShowMultiSessionToast(3, true, true)).toEqual({
            show: false,
            warned: true,
        });
        expect(shouldShowMultiSessionToast(1, true, true)).toEqual({
            show: false,
            warned: false,
        });
        expect(shouldShowMultiSessionToast(2, false, false)).toEqual({
            show: false,
            warned: false,
        });
        expect(shouldShowMultiSessionToast(2, true, false, [{ ip: "127.0.0.1" }, { ip: "10.0.0.1" }])).toEqual({
            show: false,
            warned: false,
        });
    });
});
