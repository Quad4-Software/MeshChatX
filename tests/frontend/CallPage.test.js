// SPDX-License-Identifier: 0BSD

import { render, cleanup, screen, fireEvent } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import CallPage from "@/features/call/CallPage.svelte";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import en from "@/locales/en.json";
import { sanitizeCallInputHash } from "@/features/call/lib/callHistory.ts";
import {
    executeToggleMicrophone,
    executeSetPttActive,
    executeSwitchCallMode,
} from "@/features/call/lib/callPageActions.ts";

describe("CallPage.svelte", () => {
    let api;

    beforeEach(() => {
        if (!Element.prototype.animate) {
            Element.prototype.animate = vi.fn(() => ({
                finished: Promise.resolve(),
                cancel: vi.fn(),
                onfinish: null,
            }));
        }
        registerTranslator(null);
        registerFallbackMessages(en);
        api = {
            get: vi.fn().mockImplementation((url) => {
                if (url.includes("/api/v1/config")) {
                    return Promise.resolve({ data: { config: { telephone_enabled: true } } });
                }
                if (url.includes("/api/v1/telephone/history")) {
                    return Promise.resolve({ data: { call_history: [] } });
                }
                if (url.includes("/api/v1/announces")) {
                    return Promise.resolve({ data: { announces: [] } });
                }
                if (url.includes("/api/v1/telephone/status")) {
                    return Promise.resolve({ data: { active_call: null } });
                }
                if (url.includes("/api/v1/telephone/voicemail/status")) {
                    return Promise.resolve({
                        data: {
                            has_espeak: false,
                            is_recording: false,
                            is_greeting_recording: false,
                            has_greeting: false,
                        },
                    });
                }
                if (url.includes("/api/v1/telephone/voicemails")) {
                    return Promise.resolve({ data: { voicemails: [], unread_count: 0 } });
                }
                if (url.includes("/api/v1/telephone/ringtones/status")) {
                    return Promise.resolve({
                        data: {
                            has_custom_ringtone: false,
                            enabled: true,
                            filename: null,
                            id: null,
                            volume: 0.5,
                        },
                    });
                }
                if (url.includes("/api/v1/telephone/ringtones")) {
                    return Promise.resolve({ data: [] });
                }
                if (url.includes("/api/v1/telephone/audio-profiles")) {
                    return Promise.resolve({ data: { audio_profiles: [], default_audio_profile_id: null } });
                }
                if (url.includes("/api/v1/telephone/call-modes")) {
                    return Promise.resolve({
                        data: {
                            default_call_mode_id: 1,
                            call_modes: [
                                { id: 1, name: "Full Duplex", abbrev: "FDX", is_half_duplex: false },
                                { id: 2, name: "Half Duplex", abbrev: "HDX", is_half_duplex: true },
                            ],
                        },
                    });
                }
                if (url.includes("/api/v1/telephone/contacts")) {
                    return Promise.resolve({ data: { contacts: [], total_count: 0 } });
                }
                if (url.includes("/api/v1/telephone/recordings")) {
                    return Promise.resolve({ data: { recordings: [] } });
                }
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
            patch: vi.fn().mockResolvedValue({ data: {} }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.api = api;
    });

    afterEach(() => {
        cleanup();
        delete window.api;
    });

    it("respects tab query parameter on mount", async () => {
        render(CallPage, { routeQuery: { tab: "voicemail" } });
        expect(await screen.findByText("Voicemail")).toBeTruthy();
    });

    it("renders tabs correctly", async () => {
        render(CallPage);
        expect(await screen.findByText("Phone")).toBeTruthy();
        expect(screen.getByText("Phonebook")).toBeTruthy();
        expect(screen.getByText("Voicemail")).toBeTruthy();
        expect(screen.getByText("Contacts")).toBeTruthy();
    });

    it("switches tabs when Phonebook is clicked", async () => {
        render(CallPage);
        await screen.findByText("Phone");
        await fireEvent.click(screen.getByText("Phonebook"));
        expect(screen.getByText("Phonebook")).toBeTruthy();
    });

    it("displays New Call UI when telephone is enabled", async () => {
        render(CallPage);
        expect(await screen.findByText("New Call")).toBeTruthy();
    });

    it("sanitizeCallInputHash extracts 32-char RNS hash from pasted text", () => {
        const pasted = "call me at abcdef0123456789abcdef0123456789 please";
        expect(sanitizeCallInputHash(pasted)).toBe("abcdef0123456789abcdef0123456789");
    });

    it("executeToggleMicrophone posts mute-transmit", async () => {
        await executeToggleMicrophone(false);
        expect(api.post).toHaveBeenCalledWith(expect.stringContaining("/api/v1/telephone/mute-transmit"));
    });

    it("executeSwitchCallMode and executeSetPttActive hit telephone endpoints", async () => {
        api.post.mockResolvedValueOnce({
            data: { mode_id: 2, is_half_duplex: true, is_ptt_active: false },
        });
        await executeSwitchCallMode(2);
        expect(api.post).toHaveBeenCalledWith(expect.stringContaining("/api/v1/telephone/switch-call-mode/2"));

        api.post.mockResolvedValueOnce({ data: { is_ptt_active: true } });
        await executeSetPttActive(true, true);
        expect(api.post).toHaveBeenCalledWith("/api/v1/telephone/ptt", { active: true });
    });
});
