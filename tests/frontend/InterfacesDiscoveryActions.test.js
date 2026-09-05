// SPDX-License-Identifier: 0BSD

import { render, fireEvent, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach } from "vitest";
import InterfacesPage from "../../meshchatx/src/frontend/features/interfaces/InterfacesPage.svelte";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils.js";

vi.mock("../../meshchatx/src/frontend/js/GlobalState", () => ({
    default: {
        config: { theme: "light" },
        hasPendingInterfaceChanges: false,
        modifiedInterfaceNames: new Set(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        showSuccess: vi.fn(),
        showError: vi.fn(),
        loading: vi.fn(),
        dismiss: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ElectronUtils", () => ({
    default: {
        relaunch: vi.fn(),
        isElectron: () => false,
        isWindowsElectron: () => false,
    },
}));

const mockAxios = {
    get: vi.fn((url) => {
        if (url.includes("/api/v1/reticulum/interfaces")) {
            return Promise.resolve({ data: { interfaces: {} } });
        }
        if (url.includes("/api/v1/app/info")) {
            return Promise.resolve({ data: { app_info: { is_reticulum_running: true } } });
        }
        if (url.includes("/api/v1/interface-stats")) {
            return Promise.resolve({ data: { interface_stats: { interfaces: [] } } });
        }
        if (url.includes("/api/v1/reticulum/discovery")) {
            return Promise.resolve({
                data: {
                    discovery: {
                        discover_interfaces: true,
                        interface_discovery_whitelist: "",
                        interface_discovery_blacklist: "",
                    },
                },
            });
        }
        if (url.includes("/api/v1/reticulum/discovered-interfaces")) {
            return Promise.resolve({
                data: {
                    interfaces: [
                        {
                            name: "Peer Node",
                            type: "TCPClientInterface",
                            reachable_on: "10.0.0.8",
                            port: 4242,
                            discovery_hash: "hash-1",
                        },
                    ],
                    active: [],
                },
            });
        }
        return Promise.resolve({ data: {} });
    }),
    post: vi.fn(() => Promise.resolve({ data: {} })),
    patch: vi.fn(() => Promise.resolve({ data: {} })),
};
window.api = mockAxios;

describe("InterfacesPage discovery actions", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("shows discovery action menu and allows announce", async () => {
        const { container, getByText } = render(InterfacesPage);

        await waitFor(() => {
            expect(getByText("Peer Node")).toBeTruthy();
        });

        const actionButton = container.querySelector('button[title="Discovery actions"]');
        expect(actionButton).toBeTruthy();
        if (actionButton) {
            await fireEvent.click(actionButton);
        }

        expect(getByText("Allow this announce")).toBeTruthy();
        const allowButton = getByText("Allow this announce");
        await fireEvent.click(allowButton);

        expect(mockAxios.patch).toHaveBeenCalledWith("/api/v1/reticulum/discovery", {
            interface_discovery_whitelist: "10.0.0.8:4242",
            interface_discovery_blacklist: null,
        });
    });

    it("blacklists announce and removes same token from whitelist", async () => {
        mockAxios.get.mockImplementation((url) => {
            if (url.includes("/api/v1/reticulum/interfaces")) {
                return Promise.resolve({ data: { interfaces: {} } });
            }
            if (url.includes("/api/v1/app/info")) {
                return Promise.resolve({ data: { app_info: { is_reticulum_running: true } } });
            }
            if (url.includes("/api/v1/interface-stats")) {
                return Promise.resolve({ data: { interface_stats: { interfaces: [] } } });
            }
            if (url.includes("/api/v1/reticulum/discovery")) {
                return Promise.resolve({
                    data: {
                        discovery: {
                            discover_interfaces: true,
                            interface_discovery_whitelist: "10.0.0.8:4242,other",
                            interface_discovery_blacklist: "",
                        },
                    },
                });
            }
            if (url.includes("/api/v1/reticulum/discovered-interfaces")) {
                return Promise.resolve({
                    data: {
                        interfaces: [
                            {
                                name: "Peer Node",
                                type: "TCPClientInterface",
                                reachable_on: "10.0.0.8",
                                port: 4242,
                                discovery_hash: "hash-2",
                            },
                        ],
                        active: [],
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });

        const { container, getByText } = render(InterfacesPage);

        await waitFor(() => {
            expect(getByText("Peer Node")).toBeTruthy();
        });

        const actionButton = container.querySelector('button[title="Discovery actions"]');
        expect(actionButton).toBeTruthy();
        if (actionButton) {
            await fireEvent.click(actionButton);
        }

        const blockButton = getByText("Blacklist this announce");
        expect(blockButton).toBeTruthy();
        await fireEvent.click(blockButton);

        expect(mockAxios.patch).toHaveBeenCalledWith("/api/v1/reticulum/discovery", {
            interface_discovery_whitelist: "other",
            interface_discovery_blacklist: "10.0.0.8:4242",
        });
    });

    it("reloadRns posts reticulum restart endpoint", async () => {
        const { getByText } = render(InterfacesPage);

        await waitFor(() => {
            expect(getByText("Restart RNS")).toBeTruthy();
        });

        const reloadBtn = getByText("Restart RNS").closest("button");
        expect(reloadBtn).toBeTruthy();
        if (reloadBtn) {
            await fireEvent.click(reloadBtn);
        }

        expect(ToastUtils.loading).toHaveBeenCalledWith("app.reloading_rns", 0, "interfaces-rns-reload");
        expect(mockAxios.post).toHaveBeenCalledWith("/api/v1/reticulum/reload");
        expect(ToastUtils.dismiss).toHaveBeenCalledWith("interfaces-rns-reload");
    });
});
