// SPDX-License-Identifier: 0BSD

import { render, waitFor, fireEvent } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AddInterfacePage from "../../meshchatx/src/frontend/features/interfaces/AddInterfacePage.svelte";
import {
    saveInterfaceApi,
    fetchInterfaceModulesApi,
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
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        showSuccess: vi.fn(),
        showError: vi.fn(),
    },
}));

function findAwareTile(container) {
    return [...container.querySelectorAll("button")].find((b) => b.textContent.includes("WiFi Aware"));
}

async function waitForAwareTile(container, { disabled } = {}) {
    let tile;
    await waitFor(() => {
        tile = findAwareTile(container);
        expect(tile).toBeTruthy();
        if (disabled !== undefined) {
            expect(tile.disabled).toBe(disabled);
        }
    });
    return tile;
}

describe("AddInterfacePage.svelte interface options", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockAxios.get.mockImplementation(async (url) => {
            if (String(url).includes("/api/v1/config")) {
                return { data: { config: { is_transport_enabled: true } } };
            }
            if (String(url).includes("/api/v1/reticulum/instance")) {
                return { data: { instance: { enable_transport: true } } };
            }
            if (String(url).includes("/api/v1/reticulum/interface-modules")) {
                return {
                    data: {
                        interface_path: "/tmp/meshchatx/reticulum/interfaces",
                        modules: [{ name: "ExampleInterface", filename: "ExampleInterface.py", size: 12 }],
                    },
                };
            }
            if (String(url).includes("/api/v1/reticulum/interfaces")) {
                return { data: { interfaces: {} } };
            }
            if (String(url).includes("/api/v1/locallink/capabilities")) {
                return { data: { supported: false, wifi_aware: false, wifi_aware_available: false } };
            }
            return { data: {} };
        });
        mockAxios.post.mockResolvedValue({ data: { message: "ok" } });
    });

    it("loads installed interface modules for custom external type", async () => {
        const res = await fetchInterfaceModulesApi();
        expect(mockAxios.get).toHaveBeenCalledWith("/api/v1/reticulum/interface-modules");
        expect(res.interface_path).toContain("interfaces");
        expect(res.modules).toHaveLength(1);
    });

    it("sends AutoInterface group/discovery/data port settings", async () => {
        const payload = {
            type: "AutoInterface",
            group_id: "homelab",
            discovery_scope: "site",
            discovery_port: 35000,
            data_port: 35001,
            multicast_address_type: "permanent",
            devices: "eth0,wlan0",
            ignored_devices: "tun0",
        };

        await saveInterfaceApi("AutoLAN", payload, false);

        expect(mockAxios.post).toHaveBeenCalledWith(
            "/api/v1/reticulum/interfaces/add",
            expect.objectContaining({
                name: "AutoLAN",
                type: "AutoInterface",
                group_id: "homelab",
                discovery_scope: "site",
                discovery_port: 35000,
                data_port: 35001,
                multicast_address_type: "permanent",
                devices: "eth0,wlan0",
                ignored_devices: "tun0",
            })
        );
    });

    it("sends TCP client advanced options (kiss/i2p/timeout/mtu)", async () => {
        const payload = {
            type: "TCPClientInterface",
            target_host: "example.com",
            target_port: 4242,
            kiss_framing: true,
            i2p_tunneled: true,
            connect_timeout: 12,
            max_reconnect_tries: 7,
            fixed_mtu: 512,
        };

        await saveInterfaceApi("TCPC", payload, false);

        expect(mockAxios.post).toHaveBeenCalledWith(
            "/api/v1/reticulum/interfaces/add",
            expect.objectContaining({
                name: "TCPC",
                type: "TCPClientInterface",
                target_host: "example.com",
                target_port: 4242,
                kiss_framing: true,
                i2p_tunneled: true,
                connect_timeout: 12,
                max_reconnect_tries: 7,
                fixed_mtu: 512,
            })
        );
    });

    it("sends RNode LoRa parameters", async () => {
        const payload = {
            type: "RNodeInterface",
            port: "/dev/ttyUSB0",
            frequency: 868000000,
            bandwidth: 125000,
            spreadingfactor: 7,
            codingrate: 5,
            txpower: 14,
            flow_control: true,
            autotune: true,
        };

        await saveInterfaceApi("LoRa", payload, false);

        expect(mockAxios.post).toHaveBeenCalledWith(
            "/api/v1/reticulum/interfaces/add",
            expect.objectContaining({
                name: "LoRa",
                type: "RNodeInterface",
                port: "/dev/ttyUSB0",
                frequency: 868000000,
                bandwidth: 125000,
                spreadingfactor: 7,
                codingrate: 5,
                txpower: 14,
                flow_control: true,
                autotune: true,
            })
        );
    });

    it("sends HTTPInterface parameters", async () => {
        const payload = {
            type: "HTTPInterface",
            http_tunnel_mode: "client",
            server_url: "https://hub.example:8080/rns",
            poll_interval: 0.2,
            mtu: 2048,
        };

        await saveInterfaceApi("HTTPTunnel", payload, false);

        expect(mockAxios.post).toHaveBeenCalledWith(
            "/api/v1/reticulum/interfaces/add",
            expect.objectContaining({
                name: "HTTPTunnel",
                type: "HTTPInterface",
                http_tunnel_mode: "client",
                server_url: "https://hub.example:8080/rns",
                poll_interval: 0.2,
                mtu: 2048,
            })
        );
    });

    it("sends I2PInterface parameters", async () => {
        const payload = {
            type: "I2PInterface",
            connectable: true,
            peers: ["node1.b32.i2p", "node2.b32.i2p"],
        };

        await saveInterfaceApi("I2P", payload, false);

        expect(mockAxios.post).toHaveBeenCalledWith(
            "/api/v1/reticulum/interfaces/add",
            expect.objectContaining({
                name: "I2P",
                type: "I2PInterface",
                connectable: true,
                peers: ["node1.b32.i2p", "node2.b32.i2p"],
            })
        );
    });

    it("greys out the WiFi Aware tile when local-link is unsupported", async () => {
        const { container, component } = render(AddInterfacePage);
        await waitFor(() => {
            expect(mockAxios.get).toHaveBeenCalledWith("/api/v1/locallink/capabilities");
        });

        const tile = await waitForAwareTile(container, { disabled: true });
        expect(tile.textContent).toContain("Android only");
        expect(component.getAwareInterfaceSupported()).toBe(false);
    });

    it("enables the WiFi Aware tile and posts role plus peers on supported devices", async () => {
        mockAxios.get.mockImplementation(async (url) => {
            if (String(url).includes("/api/v1/locallink/capabilities")) {
                return {
                    data: {
                        supported: true,
                        wifi_aware: true,
                        wifi_aware_available: true,
                        permission_nearby_wifi: true,
                    },
                };
            }
            if (String(url).includes("/api/v1/reticulum/interfaces")) {
                return { data: { interfaces: {} } };
            }
            return { data: {} };
        });
        const { container, component } = render(AddInterfacePage);

        const tile = await waitForAwareTile(container, { disabled: false });
        expect(component.getAwareInterfaceSupported()).toBe(true);

        const nameInput = container.querySelector("#iface-name-input");
        await fireEvent.input(nameInput, { target: { value: "Nan" } });
        await fireEvent.click(tile);

        const publishBtn = await waitFor(() => {
            const btn = [...container.querySelectorAll("button")].find((b) =>
                b.textContent.includes("Be found (publish)")
            );
            expect(btn).toBeTruthy();
            return btn;
        });
        await fireEvent.click(publishBtn);

        const peersInput = container.querySelector("#iface-aware-peers");
        await fireEvent.input(peersInput, { target: { value: "3" } });

        await component.saveInterface();

        const addCall = mockAxios.post.mock.calls.find((c) => String(c[0]).includes("/reticulum/interfaces/add"));
        expect(addCall).toBeTruthy();
        expect(addCall[1].type).toBe("AwareInterface");
        expect(addCall[1].mode).toBe("publish");
        expect(addCall[1].peers).toBe(3);
    });

    it("blocks the Aware save when the device reports unsupported", async () => {
        const { container, component } = render(AddInterfacePage);
        await waitFor(() => {
            expect(mockAxios.get).toHaveBeenCalledWith("/api/v1/locallink/capabilities");
        });

        const nameInput = container.querySelector("#iface-name-input");
        await fireEvent.input(nameInput, { target: { value: "Nan" } });
        component.setInterfaceType("AwareInterface");
        await component.saveInterface();

        const addCall = mockAxios.post.mock.calls.find((c) => String(c[0]).includes("/reticulum/interfaces/add"));
        expect(addCall).toBeUndefined();
    });

    it("shows the permission banner on supported devices missing nearby-wifi permission", async () => {
        mockAxios.get.mockImplementation(async (url) => {
            if (String(url).includes("/api/v1/locallink/capabilities")) {
                return {
                    data: {
                        supported: true,
                        wifi_aware: true,
                        wifi_aware_available: true,
                        permission_nearby_wifi: false,
                    },
                };
            }
            if (String(url).includes("/api/v1/reticulum/interfaces")) {
                return { data: { interfaces: {} } };
            }
            return { data: {} };
        });
        const { container, component } = render(AddInterfacePage);

        const tile = await waitForAwareTile(container, { disabled: false });
        expect(component.getAwareInterfaceSupported()).toBe(true);
        expect(component.getAwareNeedsPermission()).toBe(true);

        await fireEvent.click(tile);
        await waitFor(() => {
            expect(container.textContent).toContain("Nearby devices permission");
        });
    });
});
