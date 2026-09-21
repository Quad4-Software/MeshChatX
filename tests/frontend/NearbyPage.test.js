// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, waitFor } from "@testing-library/svelte";
import NearbyPage from "../../meshchatx/src/frontend/features/nearby/NearbyPage.svelte";
import { createTestI18n } from "./testI18n.js";
import {
    createNearbyState,
    createNearbyTimers,
    nfcSharePayload,
    nfcPayloadJoinable,
    onQrScanned,
    confirmJoin,
} from "../../meshchatx/src/frontend/features/nearby/lib/nearbyActions.js";
import {
    startP2p,
    startAware,
    stopAwarePolling,
    joinFromNfc,
} from "../../meshchatx/src/frontend/features/nearby/lib/nearbyTransports.js";

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
        showSuccess: vi.fn(),
        showError: vi.fn(),
    },
}));

function makeApi(caps) {
    return {
        get: vi.fn((url) => {
            if (url === "/api/v1/locallink/capabilities") {
                return Promise.resolve({ data: caps });
            }
            if (url === "/api/v1/locallink/hotspot/status") {
                return Promise.resolve({ data: { active: false } });
            }
            if (url === "/api/v1/reticulum/interfaces") {
                return Promise.resolve({ data: { interfaces: {} } });
            }
            return Promise.resolve({ data: {} });
        }),
        post: vi.fn(() => Promise.resolve({ data: {} })),
    };
}

const androidCaps = {
    supported: true,
    hotspot: true,
    wifi_join_specifier: true,
    wifi_aware: true,
    wifi_aware_available: false,
    wifi_direct: true,
    nfc: true,
    permission_nearby_wifi: true,
    hotspot_active: false,
    join_network_connected: false,
    satellite: { feature: true, enabled: null },
};

describe("NearbyPage UI", () => {
    beforeEach(() => {
        createTestI18n();
        window.api = makeApi(androidCaps);
    });

    afterEach(() => {
        cleanup();
        delete window.MeshChatXAndroid;
    });

    it("renders capability badges for an Android device", async () => {
        const { container } = render(NearbyPage);
        await waitFor(() => {
            expect(container.textContent).toContain("Hotspot");
            expect(container.textContent).toContain("Satellite");
        });
        expect(container.textContent).not.toContain("only available in the Android app");
    });

    it("shows the Android-only notice on unsupported platforms", async () => {
        window.api = makeApi({ supported: false });
        const { container } = render(NearbyPage);
        await waitFor(() => {
            expect(container.textContent).toContain("only available in the Android app");
        });
    });

    it("shows the permission banner when nearby wifi is not granted", async () => {
        window.api = makeApi({ ...androidCaps, permission_nearby_wifi: false });
        window.MeshChatXAndroid = { hasNearbyWifiPermissions: () => false };
        const { container } = render(NearbyPage);
        await waitFor(() => {
            expect(container.textContent).toContain("permission is required");
        });
    });

    it("hides the permission banner when nearby wifi is granted", async () => {
        const { container } = render(NearbyPage);
        await waitFor(() => {
            expect(container.textContent).toContain("WiFi Aware");
        });
        expect(container.textContent).not.toContain("permission is required");
    });

    it("renders the wifi direct, aware, and nfc cards", async () => {
        const { container } = render(NearbyPage);
        await waitFor(() => {
            expect(container.textContent).toContain("WiFi Direct group");
        });
        expect(container.textContent).toContain("WiFi Aware");
        expect(container.textContent).toContain("NFC tap");
    });
});

describe("nearbyActions", () => {
    let state;
    let timers;

    beforeEach(() => {
        createTestI18n();
        window.api = makeApi(androidCaps);
        state = createNearbyState();
        timers = createNearbyTimers();
    });

    afterEach(() => {
        stopAwarePolling(timers);
        delete window.MeshChatXAndroid;
    });

    it("accepts a wifi QR payload into the pending join", () => {
        expect(onQrScanned(state, "WIFI:T:WPA;S:PeerNet;P:sekret123;;")).toBe(true);
        expect(state.pendingJoin).not.toBeNull();
        expect(state.pendingJoin.ssid).toBe("PeerNet");
        expect(state.scannerError).toBeNull();
    });

    it("rejects non-wifi QR payloads without joining", () => {
        expect(onQrScanned(state, "https://evil.example/x")).toBe(false);
        expect(state.pendingJoin).toBeNull();
        expect(window.api.post).not.toHaveBeenCalled();
    });

    it("posts a join request after confirmation", async () => {
        window.api.post = vi.fn(() => Promise.resolve({ data: { ok: true, status: "requested" } }));
        state.pendingJoin = { ssid: "PeerNet", passphrase: "sekret123" };
        await confirmJoin(state);
        expect(window.api.post).toHaveBeenCalledWith("/api/v1/locallink/wifi/join", {
            ssid: "PeerNet",
            passphrase: "sekret123",
        });
        expect(state.pendingJoin).toBeNull();
    });

    it("posts p2p group start and stores credentials", async () => {
        window.api.post = vi.fn(() =>
            Promise.resolve({ data: { ok: true, ssid: "DIRECT-mc-ab", passphrase: "pskpskpsk1" } })
        );
        await startP2p(state);
        expect(window.api.post).toHaveBeenCalledWith("/api/v1/locallink/p2p/start", {});
        expect(state.p2pActive).toBe(true);
        expect(state.p2pSsid).toBe("DIRECT-mc-ab");
    });

    it("posts aware start with the selected mode", async () => {
        window.api.post = vi.fn(() => Promise.resolve({ data: { ok: true, role: "publish" } }));
        state.awareMode = "publish";
        await startAware(state);
        expect(window.api.post).toHaveBeenCalledWith("/api/v1/locallink/aware/start", {
            mode: "publish",
        });
        expect(state.awareStatus.role).toBe("publish");
    });

    it("only shares nfc credentials when a network is active", () => {
        expect(nfcSharePayload(state)).toBeNull();
        state.hotspotActive = true;
        state.hotspotSsid = "Net";
        state.hotspotPassphrase = "sekret123";
        expect(nfcSharePayload(state)).toBe("WIFI:T:WPA;S:Net;P:sekret123;;");
    });

    it("joins from a read nfc wifi payload via the confirm dialog", () => {
        state.nfcLastPayload = "WIFI:T:WPA;S:TapNet;P:sekret123;;";
        expect(nfcPayloadJoinable(state)).toBe(true);
        joinFromNfc(state);
        expect(state.pendingJoin).toEqual({
            ssid: "TapNet",
            passphrase: "sekret123",
            security: "WPA",
            hidden: false,
        });
    });

    it("does not offer join for non-wifi nfc payloads", () => {
        state.nfcLastPayload = "just some text";
        expect(nfcPayloadJoinable(state)).toBe(false);
    });
});
