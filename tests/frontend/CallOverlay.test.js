// SPDX-License-Identifier: 0BSD

import { render, cleanup, screen } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import CallOverlay from "@/features/call/components/CallOverlay.svelte";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import en from "@/locales/en.json";

describe("CallOverlay.svelte", () => {
    const defaultProps = {
        activeCall: {
            hash: "call1",
            remote_identity_hash: "test_hash_long_enough_to_format",
            remote_identity_name: "Test User",
            status: 6,
            is_incoming: false,
            is_voicemail: false,
            call_start_time: Date.now() / 1000 - 60,
            tx_bytes: 1024,
            rx_bytes: 2048,
        },
        isEnded: false,
        wasDeclined: false,
        voicemailStatus: {
            is_recording: false,
        },
    };

    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages(en);
        window.api = {
            get: vi.fn().mockResolvedValue({ data: {} }),
            post: vi.fn().mockResolvedValue({ data: {} }),
        };
    });

    afterEach(() => {
        cleanup();
        delete window.api;
    });

    it("renders when there is an active call", () => {
        render(CallOverlay, defaultProps);
        expect(screen.getByText("Test User")).toBeTruthy();
    });

    it("shows remote hash fragments if name is missing", () => {
        render(CallOverlay, {
            ...defaultProps,
            activeCall: {
                ...defaultProps.activeCall,
                remote_identity_name: null,
                remote_identity_hash: "deadbeefcafebabedeadbeefcafebabe",
            },
        });
        expect(screen.getByText(/deadbeef/i)).toBeTruthy();
    });

    it("renders declined state", () => {
        render(CallOverlay, {
            ...defaultProps,
            activeCall: null,
            wasDeclined: true,
            initiationTargetName: "Declined Peer",
        });
        expect(screen.getByText(/Declined Peer|call\.unknown/i)).toBeTruthy();
    });
});
