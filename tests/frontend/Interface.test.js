// SPDX-License-Identifier: 0BSD

import { render, fireEvent } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach } from "vitest";
import InterfaceCard from "../../meshchatx/src/frontend/features/interfaces/components/InterfaceCard.svelte";

vi.mock("../../meshchatx/src/frontend/js/DialogUtils", () => ({
    default: { alert: vi.fn() },
}));

const defaultIface = {
    _name: "Default Interface",
    type: "AutoInterface",
    enabled: true,
    discoverable: true,
};

function renderInterface(props = {}) {
    return render(InterfaceCard, {
        props: { iface: { ...defaultIface, ...props }, isReticulumRunning: true },
    });
}

describe("InterfaceCard.svelte", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("renders interface name and type", () => {
        const { getByText } = renderInterface();
        expect(getByText("Default Interface")).toBeTruthy();
        expect(getByText("AutoInterface")).toBeTruthy();
    });

    it("calls ondisable callback when Disable button is clicked", async () => {
        const ondisable = vi.fn();
        const { container } = render(InterfaceCard, {
            props: { iface: defaultIface, isReticulumRunning: true, ondisable },
        });
        const disableBtn = container.querySelector('button[title="interface.disable"]');
        expect(disableBtn).toBeTruthy();
        if (disableBtn) {
            await fireEvent.click(disableBtn);
        }
        expect(ondisable).toHaveBeenCalledTimes(1);
    });

    it("calls onenable callback when Enable button is clicked for disabled interface", async () => {
        const onenable = vi.fn();
        const { container } = render(InterfaceCard, {
            props: { iface: { ...defaultIface, enabled: false }, isReticulumRunning: true, onenable },
        });
        const enableBtn = container.querySelector('button[title="interface.enable"]');
        expect(enableBtn).toBeTruthy();
        if (enableBtn) {
            await fireEvent.click(enableBtn);
        }
        expect(onenable).toHaveBeenCalledTimes(1);
    });

    it("has overflow containment classes on card and content", () => {
        const { container } = renderInterface();
        const card = container.querySelector(".interface-card");
        expect(card?.classList.contains("min-w-0")).toBe(true);
        const contentArea = container.querySelector(".min-w-0.space-y-2");
        expect(contentArea).toBeTruthy();
    });

    it("has word-wrap on description for long host:port", () => {
        const { container } = renderInterface({
            _name: "RNS Testnet Amsterdam",
            type: "TCPClientInterface",
            target_host: "amsterdam.connect.reticulum.network",
            target_port: 4965,
        });
        const desc = container.querySelector(".text-sm.text-sem-fg-muted");
        expect(desc?.classList.contains("wrap-break-word")).toBe(true);
        expect(desc?.classList.contains("min-w-0")).toBe(true);
    });

    it("has responsive layout classes for stacking on small screens", () => {
        const { container } = renderInterface();
        const outer = container.querySelector(".flex.flex-col.sm\\:flex-row");
        expect(outer).toBeTruthy();
    });

    it("renders without overflow when given very long name and description", () => {
        const longName = "A".repeat(120);
        const { container } = renderInterface({
            _name: longName,
            type: "TCPClientInterface",
            target_host: "very-long-hostname-that-could-overflow-on-mobile.example.reticulum.network",
            target_port: 4242,
        });
        const card = container.querySelector(".interface-card");
        expect(card).toBeTruthy();
        const contentWrapper = container.querySelector(".min-w-0.space-y-2");
        expect(contentWrapper).toBeTruthy();
        const nameEl = container.querySelector(".truncate.min-w-0");
        expect(nameEl).toBeTruthy();
    });

    it("action buttons and dropdown have shrink-0 to prevent squashing", () => {
        const { container } = renderInterface();
        const actionsCol = container.querySelector(
            ".flex.flex-row.items-center.gap-1.sm\\:relative.sm\\:z-auto.sm\\:flex.sm\\:flex-row.sm\\:gap-2.sm\\:items-center.sm\\:shrink-0.sm\\:justify-end"
        );
        expect(actionsCol).toBeTruthy();
        expect(actionsCol?.classList.contains("sm:shrink-0")).toBe(true);
        const btn = container.querySelector('button[title="interface.disable"]');
        expect(btn?.classList.contains("shrink-0")).toBe(true);
        const dropdown = container.querySelector(".relative.z-50.shrink-0");
        expect(dropdown).toBeTruthy();
    });

    it("detail-value has break-all for long addresses", () => {
        const { container } = renderInterface({
            _name: "UDP Test",
            type: "UDPInterface",
            listen_ip: "0.0.0.0",
            listen_port: 4242,
            forward_ip: "192.168.1.100",
            forward_port: 4242,
        });
        const detailValues = container.querySelectorAll(".detail-value");
        expect(detailValues.length).toBeGreaterThan(0);
        detailValues.forEach((el) => {
            expect(el.classList.contains("break-all")).toBe(true);
            expect(el.classList.contains("min-w-0")).toBe(true);
        });
    });

    it("shows public relay endpoint for non-IFAC BackboneInterface", () => {
        const { container } = renderInterface({
            _name: "0rbit Iceland",
            type: "BackboneInterface",
            remote: "iceland.example",
            target_port: 4242,
        });
        expect(container.textContent).toContain("iceland.example:4242");
        expect(container.textContent).not.toContain("IFAC tunnel");
    });

    it("shows IFAC tunnel label for BackboneInterface with passphrase", () => {
        const { container } = renderInterface({
            _name: "kin.earth",
            type: "BackboneInterface",
            remote: "rns.kin.earth",
            target_port: 4242,
            network_name: "kin.earth",
            passphrase: "secret",
        });
        expect(container.textContent).toContain("Backbone (IFAC tunnel)");
    });

    it("shows IFAC tunnel label when backbone stats include ifac_signature", () => {
        const { container } = renderInterface({
            _name: "kin.earth",
            type: "BackboneInterface",
            remote: "rns.kin.earth",
            target_port: 4242,
            _stats: { ifac_signature: "a".repeat(64), ifac_size: 16 },
        });
        expect(container.textContent).toContain("Backbone (IFAC tunnel)");
    });
});

describe("InterfaceCard.svelte overflow at different viewports", () => {
    it("card has min-w-0 so it can shrink in grid", () => {
        const { container } = renderInterface();
        expect(container.querySelector(".interface-card")?.classList.contains("min-w-0")).toBe(true);
    });

    it("icon and chips have shrink-0 so they do not collapse", () => {
        const { container } = renderInterface();
        expect(container.querySelector(".interface-card__icon")?.classList.contains("shrink-0")).toBe(true);
        expect(container.querySelector(".type-chip")?.classList.contains("shrink-0")).toBe(true);
    });
});
