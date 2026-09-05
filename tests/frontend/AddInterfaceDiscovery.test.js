// SPDX-License-Identifier: 0BSD

import { render, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AddInterfacePage from "../../meshchatx/src/frontend/features/interfaces/AddInterfacePage.svelte";
import {
    parseRawConfig,
    buildPayloadFromImportedConfig,
} from "../../meshchatx/src/frontend/features/interfaces/lib/addInterfaceState.js";
import {
    saveInterfaceApi,
    fetchInterfaceToEdit,
} from "../../meshchatx/src/frontend/features/interfaces/lib/interfacesApi.js";

const mockAxios = {
    get: vi.fn(),
    post: vi.fn(),
};
window.api = mockAxios;

vi.mock("../../meshchatx/src/frontend/js/DialogUtils", () => ({
    default: {
        alert: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        showSuccess: vi.fn(),
        showError: vi.fn(),
    },
}));

describe("AddInterfacePage.svelte discovery", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockAxios.get.mockResolvedValue({ data: {} });
        mockAxios.post.mockResolvedValue({ data: { message: "ok" } });
    });

    it("adds discovery fields when interface is discoverable", async () => {
        const payload = {
            type: "TCPClientInterface",
            target_host: "example.com",
            target_port: 4242,
            discoverable: true,
            discovery_name: "Region A",
            announce_interval: 720,
            reachable_on: "/usr/local/bin/ip.sh",
        };

        await saveInterfaceApi("TestIface", payload, false);

        expect(mockAxios.post).toHaveBeenCalledWith(
            "/api/v1/reticulum/interfaces/add",
            expect.objectContaining({
                name: "TestIface",
                type: "TCPClientInterface",
                discoverable: true,
                discovery_name: "Region A",
                announce_interval: 720,
                reachable_on: "/usr/local/bin/ip.sh",
            })
        );
    });

    it("does not require latitude or longitude (optional coordinates)", async () => {
        const payload = {
            type: "TCPClientInterface",
            target_host: "example.com",
            target_port: 4242,
            discoverable: true,
            discovery_name: "X",
            announce_interval: 360,
            reachable_on: "192.0.2.1",
            latitude: null,
            longitude: null,
            height: null,
        };

        await saveInterfaceApi("NoCoords", payload, false);

        const sent = mockAxios.post.mock.calls[0][1];
        expect(sent.latitude).toBe(null);
        expect(sent.longitude).toBe(null);
        expect(sent.height).toBe(null);
        expect(sent.discoverable).toBe(true);
    });

    it("sends coordinates when set", async () => {
        const payload = {
            type: "TCPClientInterface",
            target_host: "example.com",
            target_port: 4242,
            discoverable: true,
            discovery_name: "Y",
            announce_interval: 360,
            reachable_on: "192.0.2.2",
            latitude: 51.5,
            longitude: -0.12,
            height: 42,
        };

        await saveInterfaceApi("WithCoords", payload, false);

        const sent = mockAxios.post.mock.calls[0][1];
        expect(sent.latitude).toBe(51.5);
        expect(sent.longitude).toBe(-0.12);
        expect(sent.height).toBe(42);
    });

    it("toggles discovery_encrypt and publish_ifac in payload", async () => {
        const payload = {
            type: "TCPClientInterface",
            target_host: "example.com",
            target_port: 4242,
            discoverable: true,
            discovery_name: "Z",
            announce_interval: 120,
            reachable_on: "10.0.0.1",
            discovery_encrypt: true,
            publish_ifac: false,
        };

        await saveInterfaceApi("Enc", payload, false);

        const sent = mockAxios.post.mock.calls[0][1];
        expect(sent.discovery_encrypt).toBe(true);
        expect(sent.publish_ifac).toBe(false);
    });

    it("fuzz: random safe discovery_name and announce_interval still save", async () => {
        for (let i = 0; i < 15; i++) {
            vi.clearAllMocks();
            mockAxios.post.mockResolvedValue({ data: { message: "ok" } });

            const name = `node-${Math.random().toString(36).slice(2, 10)}`;
            const interval = Math.max(5, Math.floor(Math.random() * 10000));

            const payload = {
                type: "TCPClientInterface",
                target_host: "example.com",
                target_port: 4242,
                discoverable: true,
                discovery_name: name,
                announce_interval: interval,
                reachable_on: "192.0.2.1",
            };

            await saveInterfaceApi("Fuzz", payload, false);

            const sent = mockAxios.post.mock.calls[0][1];
            expect(sent.discovery_name).toBe(name);
            expect(sent.announce_interval).toBe(interval);
        }
    });

    it("loadInterfaceToEdit restores discoverable and coordinates from API", async () => {
        mockAxios.get.mockImplementation((url) => {
            if (url === "/api/v1/reticulum/interfaces") {
                return Promise.resolve({
                    data: {
                        interfaces: {
                            MyIface: {
                                type: "TCPClientInterface",
                                target_host: "h.example",
                                target_port: "5555",
                                discoverable: "yes",
                                discovery_name: "Loaded",
                                announce_interval: 180,
                                reachable_on: "192.0.2.3",
                                latitude: 12.34,
                                longitude: 56.78,
                                height: 100,
                                discovery_stamp_value: 18,
                                discovery_encrypt: true,
                                publish_ifac: false,
                            },
                        },
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });

        const iface = await fetchInterfaceToEdit("MyIface");

        expect(iface.type).toBe("TCPClientInterface");
        expect(iface.discovery_name).toBe("Loaded");
        expect(iface.announce_interval).toBe(180);
        expect(iface.latitude).toBe(12.34);
        expect(iface.longitude).toBe(56.78);
        expect(iface.height).toBe(100);
        expect(iface.discovery_stamp_value).toBe(18);
        expect(iface.discovery_encrypt).toBe(true);
        expect(iface.publish_ifac).toBe(false);
    });

    it("parseRawConfig parses config blocks and builds payload", () => {
        const raw = `[[Auto Node]]
type = TCPClientInterface
target_host = auto.example
target_port = 4242`;
        const configs = parseRawConfig(raw);
        expect(configs).toHaveLength(1);
        expect(configs[0].name).toBe("Auto Node");
        expect(configs[0].target_host).toBe("auto.example");
        expect(configs[0].target_port).toBe(4242);

        const payload = buildPayloadFromImportedConfig(configs[0]);
        expect(payload.name).toBe("Auto Node");
        expect(payload.type).toBe("TCPClientInterface");
        expect(payload.target_host).toBe("auto.example");
        expect(payload.target_port).toBe(4242);
    });

    it("renders AddInterfacePage with prefilled query", async () => {
        const { getByDisplayValue } = render(AddInterfacePage, {
            props: {
                routeQuery: {
                    type: "TCPClientInterface",
                    name: "PreName",
                    target_host: "10.0.0.5",
                    target_port: "4242",
                },
            },
        });

        await waitFor(() => {
            expect(getByDisplayValue("PreName")).toBeTruthy();
            expect(getByDisplayValue("10.0.0.5")).toBeTruthy();
            expect(getByDisplayValue("4242")).toBeTruthy();
        });
    });
});
