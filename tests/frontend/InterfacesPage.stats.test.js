// SPDX-License-Identifier: 0BSD

import { render, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach } from "vitest";
import InterfacesPage from "../../meshchatx/src/frontend/features/interfaces/InterfacesPage.svelte";
import {
    fetchInterfaces,
    fetchInterfaceStats,
} from "../../meshchatx/src/frontend/features/interfaces/lib/interfacesApi.js";

vi.mock("../../meshchatx/src/frontend/js/GlobalState", () => ({
    default: {
        config: { theme: "light" },
        hasPendingInterfaceChanges: false,
        modifiedInterfaceNames: new Set(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
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

describe("InterfacesPage interface-stats merge", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        window.api = {
            get: vi.fn((url) => {
                if (url.includes("/api/v1/reticulum/interfaces")) {
                    return Promise.resolve({
                        data: {
                            interfaces: {
                                "RNode LoRa Interface": { type: "RNodeInterface", enabled: true },
                            },
                        },
                    });
                }
                if (url.includes("/api/v1/app/info")) {
                    return Promise.resolve({ data: { app_info: { is_reticulum_running: true } } });
                }
                if (url.includes("/api/v1/interface-stats")) {
                    return Promise.resolve({
                        data: {
                            interface_stats: {
                                interfaces: [
                                    {
                                        interface_name: "RNode LoRa Interface",
                                        short_name: "LoRa",
                                        status: true,
                                        rxb: 100,
                                        txb: 50,
                                    },
                                ],
                            },
                        },
                    });
                }
                if (url.includes("/api/v1/reticulum/discovery")) {
                    return Promise.resolve({ data: { discovery: {} } });
                }
                if (url.includes("/api/v1/reticulum/discovered-interfaces")) {
                    return Promise.resolve({ data: { interfaces: [], active: [] } });
                }
                return Promise.resolve({ data: {} });
            }),
        };
    });

    it("indexes stats by interface_name so config keys match live status", async () => {
        const { getByText } = render(InterfacesPage);
        await waitFor(() => {
            expect(getByText("RNode LoRa Interface")).toBeTruthy();
        });

        const stats = await fetchInterfaceStats();
        expect(stats["RNode LoRa Interface"]).toBeDefined();
        expect(stats["RNode LoRa Interface"].status).toBe(true);
        expect(stats["RNode LoRa Interface"].short_name).toBe("LoRa");
    });

    it("keeps hostname section names such as artyom.ddns.net in the tile list", async () => {
        window.api.get = vi.fn((url) => {
            if (url.includes("/api/v1/reticulum/interfaces")) {
                return Promise.resolve({
                    data: {
                        interfaces: {
                            "Default Interface": { type: "AutoInterface", enabled: true },
                            "artyom.ddns.net": {
                                type: "TCPClientInterface",
                                interface_enabled: "True",
                                target_host: "10.100.11.12",
                                target_port: "4242",
                            },
                            "Catz-Node (TCP)": { type: "TCPClientInterface", enabled: true },
                        },
                    },
                });
            }
            if (url.includes("/api/v1/app/info")) {
                return Promise.resolve({ data: { app_info: { is_reticulum_running: true } } });
            }
            if (url.includes("/api/v1/interface-stats")) {
                return Promise.resolve({ data: { interface_stats: { interfaces: [] } } });
            }
            if (url.includes("/api/v1/reticulum/discovery")) {
                return Promise.resolve({ data: { discovery: {} } });
            }
            if (url.includes("/api/v1/reticulum/discovered-interfaces")) {
                return Promise.resolve({ data: { interfaces: [], active: [] } });
            }
            return Promise.resolve({ data: {} });
        });

        const { getByText } = render(InterfacesPage);
        await waitFor(() => {
            expect(getByText("artyom.ddns.net")).toBeTruthy();
            expect(getByText("Default Interface")).toBeTruthy();
            expect(getByText("Catz-Node (TCP)")).toBeTruthy();
        });
    });

    it("falls back to short_name when interface_name is absent", async () => {
        window.api.get = vi.fn((url) => {
            if (url.includes("/api/v1/reticulum/interfaces")) {
                return Promise.resolve({ data: { interfaces: { LoRa: { type: "RNodeInterface" } } } });
            }
            if (url.includes("/api/v1/app/info")) {
                return Promise.resolve({ data: { app_info: { is_reticulum_running: true } } });
            }
            if (url.includes("/api/v1/interface-stats")) {
                return Promise.resolve({
                    data: {
                        interface_stats: {
                            interfaces: [{ short_name: "LoRa", status: true }],
                        },
                    },
                });
            }
            if (url.includes("/api/v1/reticulum/discovery")) {
                return Promise.resolve({ data: { discovery: {} } });
            }
            if (url.includes("/api/v1/reticulum/discovered-interfaces")) {
                return Promise.resolve({ data: { interfaces: [], active: [] } });
            }
            return Promise.resolve({ data: {} });
        });

        const stats = await fetchInterfaceStats();
        expect(stats.LoRa.status).toBe(true);
    });
});
