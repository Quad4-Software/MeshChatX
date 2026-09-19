import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import NearbyPage from "@/components/tools/NearbyPage.vue";
import { mountToolsPageGlobals } from "./testI18n.js";

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

function mountPage() {
    const globals = mountToolsPageGlobals();
    globals.stubs = {
        ...globals.stubs,
        RouterLink: { template: "<a><slot/></a>", props: ["to"] },
    };
    return mount(NearbyPage, { global: globals });
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

describe("NearbyPage", () => {
    beforeEach(() => {
        window.api = makeApi(androidCaps);
    });

    afterEach(() => {
        delete window.MeshChatXAndroid;
    });

    it("renders capability badges for an Android device", async () => {
        const wrapper = mountPage();
        await new Promise((resolve) => setTimeout(resolve, 0));
        const text = wrapper.text();
        expect(text).toContain("Hotspot");
        expect(text).toContain("WiFi Aware");
        expect(text).toContain("Satellite");
        expect(text).not.toContain("only available in the Android app");
    });

    it("shows the Android-only notice on unsupported platforms", async () => {
        window.api = makeApi({ supported: false });
        const wrapper = mountPage();
        await new Promise((resolve) => setTimeout(resolve, 0));
        expect(wrapper.text()).toContain("only available in the Android app");
    });

    it("shows the permission banner when nearby wifi is not granted", async () => {
        window.api = makeApi({ ...androidCaps, permission_nearby_wifi: false });
        window.MeshChatXAndroid = { hasNearbyWifiPermissions: () => false };
        const wrapper = mountPage();
        await new Promise((resolve) => setTimeout(resolve, 0));
        expect(wrapper.text()).toContain("permission is required");
    });

    it("hides the permission banner when nearby wifi is granted", async () => {
        const wrapper = mountPage();
        await new Promise((resolve) => setTimeout(resolve, 0));
        expect(wrapper.text()).not.toContain("permission is required");
    });

    it("shows a confirm dialog with the scanned ssid before joining", async () => {
        const wrapper = mountPage();
        await new Promise((resolve) => setTimeout(resolve, 0));
        wrapper.vm.onQrScanned("WIFI:T:WPA;S:PeerNet;P:sekret123;;");
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.pendingJoin).not.toBeNull();
        expect(wrapper.text()).toContain("PeerNet");
    });

    it("rejects non-wifi QR payloads without joining", async () => {
        const wrapper = mountPage();
        await new Promise((resolve) => setTimeout(resolve, 0));
        wrapper.vm.onQrScanned("https://evil.example/x");
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.pendingJoin).toBeNull();
        expect(window.api.post).not.toHaveBeenCalled();
    });

    it("posts a join request after confirmation", async () => {
        window.api.post = vi.fn(() => Promise.resolve({ data: { ok: true, status: "requested" } }));
        const wrapper = mountPage();
        await new Promise((resolve) => setTimeout(resolve, 0));
        wrapper.vm.pendingJoin = { ssid: "PeerNet", passphrase: "sekret123" };
        await wrapper.vm.confirmJoin();
        expect(window.api.post).toHaveBeenCalledWith("/api/v1/locallink/wifi/join", {
            ssid: "PeerNet",
            passphrase: "sekret123",
        });
    });

    it("renders the wifi direct, aware, and nfc cards", async () => {
        const wrapper = mountPage();
        await new Promise((resolve) => setTimeout(resolve, 0));
        const text = wrapper.text();
        expect(text).toContain("WiFi Direct group");
        expect(text).toContain("WiFi Aware");
        expect(text).toContain("NFC tap");
    });

    it("posts p2p group start and stores credentials", async () => {
        window.api.post = vi.fn(() =>
            Promise.resolve({
                data: { ok: true, ssid: "DIRECT-mc-ab", passphrase: "pskpskpsk1" },
            })
        );
        const wrapper = mountPage();
        await new Promise((resolve) => setTimeout(resolve, 0));
        await wrapper.vm.startP2p();
        expect(window.api.post).toHaveBeenCalledWith("/api/v1/locallink/p2p/start", {});
        expect(wrapper.vm.p2pActive).toBe(true);
        expect(wrapper.vm.p2pSsid).toBe("DIRECT-mc-ab");
    });

    it("posts aware start with the selected mode", async () => {
        window.api.post = vi.fn(() => Promise.resolve({ data: { ok: true, role: "publish" } }));
        const wrapper = mountPage();
        await new Promise((resolve) => setTimeout(resolve, 0));
        wrapper.vm.awareMode = "publish";
        await wrapper.vm.startAware();
        expect(window.api.post).toHaveBeenCalledWith("/api/v1/locallink/aware/start", {
            mode: "publish",
        });
        expect(wrapper.vm.awareStatus.role).toBe("publish");
        wrapper.vm.stopAwarePolling();
    });

    it("only shares nfc credentials when a network is active", async () => {
        const wrapper = mountPage();
        await new Promise((resolve) => setTimeout(resolve, 0));
        expect(wrapper.vm.nfcSharePayload).toBeNull();
        wrapper.vm.hotspotActive = true;
        wrapper.vm.hotspotSsid = "Net";
        wrapper.vm.hotspotPassphrase = "sekret123";
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.nfcSharePayload).toBe("WIFI:T:WPA;S:Net;P:sekret123;;");
    });

    it("joins from a read nfc wifi payload via the confirm dialog", async () => {
        const wrapper = mountPage();
        await new Promise((resolve) => setTimeout(resolve, 0));
        wrapper.vm.nfcLastPayload = "WIFI:T:WPA;S:TapNet;P:sekret123;;";
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.nfcPayloadJoinable).toBe(true);
        wrapper.vm.joinFromNfc();
        expect(wrapper.vm.pendingJoin).toEqual({
            ssid: "TapNet",
            passphrase: "sekret123",
            security: "WPA",
            hidden: false,
        });
    });

    it("does not offer join for non-wifi nfc payloads", async () => {
        const wrapper = mountPage();
        await new Promise((resolve) => setTimeout(resolve, 0));
        wrapper.vm.nfcLastPayload = "just some text";
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.nfcPayloadJoinable).toBe(false);
    });
});
