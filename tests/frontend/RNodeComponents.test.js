// SPDX-License-Identifier: 0BSD

import { render, cleanup, fireEvent } from "@testing-library/svelte";
import { describe, it, expect, afterEach } from "vitest";
import RNodeCapabilitiesBanner from "../../meshchatx/src/frontend/features/rnode-flasher/components/RNodeCapabilitiesBanner.svelte";
import RNodeDeviceSelector from "../../meshchatx/src/frontend/features/rnode-flasher/components/RNodeDeviceSelector.svelte";
import RNodeFlashAction from "../../meshchatx/src/frontend/features/rnode-flasher/components/RNodeFlashAction.svelte";
import RNodeAdvancedTools from "../../meshchatx/src/frontend/features/rnode-flasher/components/RNodeAdvancedTools.svelte";
import RNodeDiagnosticsPanel from "../../meshchatx/src/frontend/features/rnode-flasher/components/RNodeDiagnosticsPanel.svelte";
import { detectCapabilities } from "../../meshchatx/src/frontend/js/rnode/Capabilities.js";
import { t } from "../../meshchatx/src/frontend/js/i18n.js";

describe("RNodeCapabilitiesBanner", () => {
    afterEach(() => {
        cleanup();
    });

    it("renders nothing when all transports are available", () => {
        const env = { isSecureContext: true, navigator: { userAgent: "x", serial: {}, bluetooth: {} } };
        const caps = detectCapabilities({ env });
        const { container } = render(RNodeCapabilitiesBanner, { props: { capabilities: caps } });
        expect(container.textContent?.trim()).toBe("");
    });

    it("shows a serial warning with load polyfill action when polyfill missing", async () => {
        const env = { isSecureContext: true, navigator: { userAgent: "x", usb: {} } };
        const caps = detectCapabilities({ env });
        let actionEmitted = null;
        const { container } = render(RNodeCapabilitiesBanner, {
            props: {
                capabilities: caps,
                onaction: (a) => {
                    actionEmitted = a;
                },
            },
        });
        expect(container.textContent).toContain(t("tools.rnode_flasher.support.serial.title"));
        const button = Array.from(container.querySelectorAll("button")).find((b) =>
            b.textContent?.includes(t("tools.rnode_flasher.support.actions.load_polyfill"))
        );
        expect(button).toBeDefined();
        if (button) await fireEvent.click(button);
        expect(actionEmitted).toBe("load-polyfill");
    });

    it("shows bluetooth warning with android actions when bridge available", () => {
        const env = { isSecureContext: true, navigator: { userAgent: "Android" } };
        const caps = detectCapabilities({ env });
        const { container } = render(RNodeCapabilitiesBanner, {
            props: {
                capabilities: caps,
                androidAvailable: true,
            },
        });
        expect(container.textContent).toContain(t("tools.rnode_flasher.support.bluetooth.title"));
        const labels = Array.from(container.querySelectorAll("button")).map((b) => b.textContent || "");
        expect(labels.some((l) => l.includes(t("tools.rnode_flasher.support.actions.open_native")))).toBe(true);
        expect(labels.some((l) => l.includes(t("tools.rnode_flasher.support.actions.open_settings")))).toBe(true);
        expect(labels.some((l) => l.includes(t("tools.rnode_flasher.support.actions.request_bluetooth")))).toBe(false);
    });

    it("shows request bluetooth when android permission is required", () => {
        const env = {
            isSecureContext: true,
            navigator: { userAgent: "Android" },
            MeshChatXAndroid: { hasBluetoothPermissions: () => false },
        };
        const caps = detectCapabilities({ env });
        const { container } = render(RNodeCapabilitiesBanner, {
            props: {
                capabilities: caps,
                androidAvailable: true,
            },
        });
        const labels = Array.from(container.querySelectorAll("button")).map((b) => b.textContent || "");
        expect(labels.some((l) => l.includes(t("tools.rnode_flasher.support.actions.request_bluetooth")))).toBe(true);
        expect(labels.some((l) => l.includes(t("tools.rnode_flasher.support.actions.open_settings")))).toBe(true);
    });

    it("shows desktop Try Bluetooth and Recheck actions when Web Bluetooth is missing", () => {
        const env = { isSecureContext: true, navigator: { userAgent: "Mozilla/5.0 Brave/1.0" } };
        const caps = detectCapabilities({ env });
        const { container } = render(RNodeCapabilitiesBanner, {
            props: {
                capabilities: caps,
                androidAvailable: false,
            },
        });
        expect(caps.transports.bluetooth.reason).toBe("brave_flag_disabled");
        const labels = Array.from(container.querySelectorAll("button")).map((b) => b.textContent || "");
        expect(labels.some((l) => l.includes(t("tools.rnode_flasher.support.actions.probe_bluetooth")))).toBe(true);
        expect(labels.some((l) => l.includes(t("tools.rnode_flasher.support.actions.recheck_capabilities")))).toBe(
            true
        );
    });
});

describe("RNodeDeviceSelector", () => {
    afterEach(() => {
        cleanup();
    });

    it("disables transports that are not available", () => {
        const caps = detectCapabilities({ env: { isSecureContext: true, navigator: { userAgent: "Android" } } });
        const { container } = render(RNodeDeviceSelector, {
            props: {
                connectionMethod: "wifi",
                wifiHost: "192.168.1.50",
                selectedProduct: null,
                selectedModel: null,
                products: [{ id: 1, name: "Test", platform: 0x80, models: [{ id: 1, name: "M" }] }],
                capabilities: caps,
            },
        });
        const serialBtn = container.querySelector('[data-testid="rnode-transport-serial"]');
        const wifiBtn = container.querySelector('[data-testid="rnode-transport-wifi"]');
        expect(serialBtn?.hasAttribute("disabled")).toBe(true);
        expect(wifiBtn?.hasAttribute("disabled")).toBe(false);
    });

    it("shows DFU mode button only for nRF52 + serial", () => {
        const caps = detectCapabilities({ env: { isSecureContext: true, navigator: { userAgent: "x", serial: {} } } });
        const product = { id: 1, name: "P", platform: 0x70, models: [] };
        const { container } = render(RNodeDeviceSelector, {
            props: {
                connectionMethod: "serial",
                wifiHost: "",
                selectedProduct: product,
                selectedModel: null,
                products: [product],
                capabilities: caps,
            },
        });
        expect(container.textContent).toContain(t("tools.rnode_flasher.enter_dfu_mode"));
    });
});

describe("RNodeFlashAction", () => {
    afterEach(() => {
        cleanup();
    });

    it("disables flash button when canFlash=false", () => {
        const { container } = render(RNodeFlashAction, { props: { canFlash: false } });
        const btn = container.querySelector('[data-testid="rnode-flash-btn"]');
        expect(btn?.hasAttribute("disabled")).toBe(true);
    });

    it("renders error message when provided", () => {
        const { container } = render(RNodeFlashAction, { props: { errorMessage: "boom" } });
        expect(container.textContent).toContain("boom");
    });

    it("emits flash event when button clicked", async () => {
        let flashed = false;
        const { container } = render(RNodeFlashAction, {
            props: {
                canFlash: true,
                onflash: () => {
                    flashed = true;
                },
            },
        });
        const btn = container.querySelector('[data-testid="rnode-flash-btn"]');
        if (btn) await fireEvent.click(btn);
        expect(flashed).toBe(true);
    });
});

describe("RNodeAdvancedTools", () => {
    afterEach(() => {
        cleanup();
    });

    it("hides actions listed in disabledActions", () => {
        const { container } = render(RNodeAdvancedTools, {
            props: {
                disabledActions: ["dump-eeprom", "wipe-eeprom"],
            },
        });
        expect(container.textContent).not.toContain(t("tools.rnode_flasher.dump_eeprom"));
        expect(container.textContent).not.toContain(t("tools.rnode_flasher.wipe_eeprom"));
        expect(container.textContent).toContain(t("tools.rnode_flasher.detect_rnode"));
    });

    it("emits action with action id", async () => {
        let emittedAction = null;
        const { container } = render(RNodeAdvancedTools, {
            props: {
                onaction: (a) => {
                    emittedAction = a;
                },
            },
        });
        const btn = Array.from(container.querySelectorAll("button")).find((b) =>
            b.textContent?.includes(t("tools.rnode_flasher.detect_rnode"))
        );
        expect(btn).toBeDefined();
        if (btn) await fireEvent.click(btn);
        expect(emittedAction).toBe("detect");
    });
});

describe("RNodeDiagnosticsPanel", () => {
    afterEach(() => {
        cleanup();
    });

    it("renders nothing when no diagnostics", () => {
        const { container } = render(RNodeDiagnosticsPanel, { props: { diagnostics: null } });
        expect(container.textContent?.trim()).toBe("");
    });

    it("shows healthy badge when no issues", () => {
        const { container } = render(RNodeDiagnosticsPanel, {
            props: {
                diagnostics: { issues: [], suggestionKeys: [], summary: { firmware_version: "1.80" } },
            },
        });
        expect(container.textContent).toContain(t("tools.rnode_flasher.diagnostics.healthy"));
    });

    it("shows issues list and needs_attention badge when issues exist", () => {
        const { container } = render(RNodeDiagnosticsPanel, {
            props: {
                diagnostics: {
                    issues: ["not_provisioned"],
                    suggestionKeys: ["tools.rnode_flasher.diagnostics.suggestions.not_provisioned"],
                    summary: { firmware_version: "1.80" },
                },
            },
        });
        expect(container.textContent).toContain(t("tools.rnode_flasher.diagnostics.needs_attention"));
        expect(container.textContent).toContain(t("tools.rnode_flasher.diagnostics.suggestions.not_provisioned"));
    });
});
