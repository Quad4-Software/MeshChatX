// SPDX-License-Identifier: 0BSD

import { render, fireEvent, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach } from "vitest";
import InterfacesPage from "../../meshchatx/src/frontend/features/interfaces/InterfacesPage.svelte";
import AddInterfacePage from "../../meshchatx/src/frontend/features/interfaces/AddInterfacePage.svelte";
import DiscoveredInterfaceCard from "../../meshchatx/src/frontend/features/interfaces/components/DiscoveredInterfaceCard.svelte";
import {
    discoveredNetworkName,
    discoveredPassphrase,
    maskPassphrase,
    formatDiscoveredConfig,
} from "../../meshchatx/src/frontend/features/interfaces/lib/interfacesFormat.js";

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

const ifaceWithIfac = {
    name: "kin.earth",
    type: "BackboneInterface",
    reachable_on: "rns.kin.earth",
    port: 4242,
    transport_id: "eea3d09f02143e157b3dae83060ee843",
    network_id: "abc123",
    discovery_hash: "kin-earth-1",
    network_name: "kin.earth",
    passphrase: "asty8vT8spXNQdCnPVMATbCKkwUxuzG9",
    ifac_netname: "kin.earth",
    ifac_netkey: "asty8vT8spXNQdCnPVMATbCKkwUxuzG9",
    publish_ifac: true,
    config_entry:
        "[[kin.earth]]\n  type = BackboneInterface\n  enabled = yes\n  remote = rns.kin.earth\n  target_port = 4242\n  network_name = kin.earth\n  passphrase = asty8vT8spXNQdCnPVMATbCKkwUxuzG9",
};

describe("InterfacesPage discovered IFAC display", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        Object.defineProperty(navigator, "clipboard", {
            value: { writeText: vi.fn(() => Promise.resolve()) },
            configurable: true,
        });
    });

    it("derives network_name and passphrase from either alias", () => {
        expect(discoveredNetworkName(ifaceWithIfac)).toBe("kin.earth");
        expect(discoveredPassphrase(ifaceWithIfac)).toBe("asty8vT8spXNQdCnPVMATbCKkwUxuzG9");

        const rawOnly = {
            name: "raw",
            ifac_netname: "raw.net",
            ifac_netkey: "rawkey",
        };
        expect(discoveredNetworkName(rawOnly)).toBe("raw.net");
        expect(discoveredPassphrase(rawOnly)).toBe("rawkey");

        expect(discoveredNetworkName({ name: "open" })).toBe(null);
        expect(discoveredPassphrase({ name: "open" })).toBe(null);
    });

    it("masks passphrase for display safety", () => {
        expect(maskPassphrase("asty8vT8spXNQdCnPVMATbCKkwUxuzG9")).toMatch(/^as\*+G9$/);
        expect(maskPassphrase("ab")).toBe("**");
        expect(maskPassphrase("")).toBe("");
        expect(maskPassphrase(null)).toBe("");
    });

    it("renders network_name and passphrase chips when announce includes IFAC", () => {
        const { getByTestId, queryByText } = render(DiscoveredInterfaceCard, {
            props: { iface: ifaceWithIfac },
        });

        const netEl = getByTestId("discovered-network-name");
        expect(netEl.textContent).toContain("kin.earth");

        const passEl = getByTestId("discovered-passphrase");
        expect(passEl.textContent).toMatch(/as\*+G9/);
        expect(queryByText("asty8vT8spXNQdCnPVMATbCKkwUxuzG9")).toBeNull();
    });

    it("does not render passphrase row when announce omits IFAC", () => {
        const { queryByTestId } = render(DiscoveredInterfaceCard, {
            props: {
                iface: {
                    name: "open",
                    type: "BackboneInterface",
                    reachable_on: "10.0.0.1",
                    port: 4242,
                },
            },
        });

        expect(queryByTestId("discovered-network-name")).toBeNull();
        expect(queryByTestId("discovered-passphrase")).toBeNull();
    });

    it("formatDiscoveredConfig returns config snippet or generates one", () => {
        const text = formatDiscoveredConfig(ifaceWithIfac);
        expect(text).toContain("[[kin.earth]]");
        expect(text).toContain("BackboneInterface");
    });
});

describe("AddInterfacePage discovered prefill", () => {
    it("applies a query prefill to the form on mount", async () => {
        const { getByDisplayValue } = render(AddInterfacePage, {
            props: {
                routeQuery: {
                    name: "kin.earth",
                    type: "BackboneInterface",
                    target_host: "rns.kin.earth",
                    target_port: "4242",
                },
            },
        });

        await waitFor(() => {
            expect(getByDisplayValue("kin.earth")).toBeTruthy();
            expect(getByDisplayValue("rns.kin.earth")).toBeTruthy();
            expect(getByDisplayValue("4242")).toBeTruthy();
        });
    });
});
