// SPDX-License-Identifier: 0BSD

import { render, fireEvent, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import SettingsPage from "../../meshchatx/src/frontend/features/settings/components/SettingsPage.svelte";
import GlobalState from "../../meshchatx/src/frontend/js/GlobalState";
import { createWindowApi, buildFullServerConfig } from "./fixtures/settingsPageTestApi.js";
import { registerCoreContributions } from "../../meshchatx/src/frontend/js/registries/registerCoreContributions.js";

registerCoreContributions();

vi.mock("../../meshchatx/src/frontend/js/WebSocketConnection", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
        emit: vi.fn(),
        send: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
        loading: vi.fn(),
        dismiss: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn().mockResolvedValue(true),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/KeyboardShortcuts", () => ({
    default: {
        getDefaultShortcuts: vi.fn(() => []),
        send: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ElectronUtils", () => ({
    default: {
        isElectron: vi.fn(() => false),
        isWindowsElectron: vi.fn(() => false),
        getScreenSecuritySettings: vi.fn(async () => null),
        setScreenSecurityEnabled: vi.fn(async () => null),
        getCloseSettings: vi.fn(async () => null),
        setCloseSettings: vi.fn(async () => null),
    },
}));

function renderPage() {
    window.api = createWindowApi({ current: buildFullServerConfig() });
    return render(SettingsPage);
}

describe("SettingsPage search", () => {
    beforeEach(() => {
        registerCoreContributions();
        GlobalState.pluginsEnabled = true;
    });

    afterEach(() => {
        GlobalState.pluginsEnabled = true;
        delete window.api;
        vi.clearAllMocks();
        document.body.innerHTML = "";
    });

    it("empty query shows the active tab only", async () => {
        const { container } = renderPage();
        expect(container.textContent).toContain("Appearance");
        expect(container.textContent).not.toContain("Inbound stamp cost");
    });

    it("filters sections by keyword and shows the empty state when nothing matches", async () => {
        const { container } = renderPage();
        const searchInput = container.querySelector('input[type="search"]');
        await fireEvent.input(searchInput, { target: { value: "theme" } });

        expect(container.textContent).toContain("Appearance");
        expect(container.textContent).not.toContain("Page Archiver");

        await fireEvent.input(searchInput, { target: { value: "zzz-no-such-setting" } });
        expect(container.textContent).toContain("No results found");
        expect(container.textContent).toContain('No settings match "zzz-no-such-setting"');
    });

    it("matches a tab label across that tab's sections", async () => {
        const { container } = renderPage();
        const searchInput = container.querySelector('input[type="search"]');
        await fireEvent.input(searchInput, { target: { value: "network" } });

        expect(container.textContent).toContain("Transport");
        expect(container.textContent).toContain("Network Security");
    });

    it("matches hyphenated and compact queries", async () => {
        const { container } = renderPage();
        const searchInput = container.querySelector('input[type="search"]');
        await fireEvent.input(searchInput, { target: { value: "dark-mode" } });
        expect(container.textContent).toContain("Appearance");

        await fireEvent.input(searchInput, { target: { value: "darkmode" } });
        expect(container.textContent).toContain("Appearance");
    });

    it("clicking a matching tab during search filters to that tab", async () => {
        const { container } = renderPage();
        const searchInput = container.querySelector('input[type="search"]');
        await fireEvent.input(searchInput, { target: { value: "privacy" } });

        expect(container.textContent).toContain("Privacy Data & device");

        const tabs = container.querySelectorAll(".settings-nav__tab");
        for (const tab of tabs) {
            if (tab.textContent.includes("Privacy")) {
                await fireEvent.click(tab);
                break;
            }
        }
        expect(container.textContent).toContain("Privacy Data & device");
    });

    it("slash focuses the search field when not typing in an input", async () => {
        const { container } = renderPage();
        const input = container.querySelector('input[type="search"]');
        expect(input).not.toBeNull();

        window.dispatchEvent(new KeyboardEvent("keydown", { key: "/", bubbles: true }));
        await waitFor(() => {
            expect(document.activeElement).toBe(input);
        });
    });

    it("clearSettingsSearch restores tab browsing", async () => {
        const { container } = renderPage();
        const searchInput = container.querySelector('input[type="search"]');
        await fireEvent.input(searchInput, { target: { value: "theme" } });

        const clearBtn = container.querySelector('button[type="button"] svg[aria-label="close"]')?.closest("button");
        if (clearBtn) {
            await fireEvent.click(clearBtn);
        } else {
            await fireEvent.input(searchInput, { target: { value: "" } });
        }

        expect(container.textContent).toContain("Appearance");
        expect(container.textContent).not.toContain("Inbound stamp cost");
    });
});
