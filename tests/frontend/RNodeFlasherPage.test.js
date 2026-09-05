// SPDX-License-Identifier: 0BSD

import { render, cleanup, fireEvent, screen } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

const { toastError, toastSuccess, toastInfo, toastWarning } = vi.hoisted(() => ({
    toastError: vi.fn(),
    toastSuccess: vi.fn(),
    toastInfo: vi.fn(),
    toastWarning: vi.fn(),
}));

vi.mock("@/js/ToastUtils.js", () => ({
    default: {
        error: toastError,
        success: toastSuccess,
        info: toastInfo,
        warning: toastWarning,
    },
}));

import RNodeFlasherPage from "../../meshchatx/src/frontend/features/rnode-flasher/RNodeFlasherPage.svelte";
import { t } from "../../meshchatx/src/frontend/js/i18n.js";

describe("RNodeFlasherPage.svelte", () => {
    beforeEach(() => {
        toastError.mockClear();
        toastSuccess.mockClear();
        toastInfo.mockClear();
        toastWarning.mockClear();
    });

    afterEach(() => {
        cleanup();
        vi.restoreAllMocks();
    });

    it("renders the flasher page", () => {
        const { container } = render(RNodeFlasherPage);
        expect(container.textContent).toContain(t("tools.rnode_flasher.title"));
        expect(container.textContent).toContain(t("tools.rnode_flasher.select_device"));
    });

    it("toggles advanced mode", async () => {
        const { container } = render(RNodeFlasherPage);
        expect(container.textContent).not.toContain(t("tools.rnode_flasher.advanced_tools"));

        const advancedButton = container.querySelector('[data-testid="rnode-advanced-toggle"]');
        expect(advancedButton).toBeDefined();
        expect(advancedButton).not.toBeNull();
        if (advancedButton) {
            await fireEvent.click(advancedButton);
        }

        expect(container.textContent).toContain(t("tools.rnode_flasher.advanced_tools"));
    });

    it("switches connection method", async () => {
        const { container } = render(RNodeFlasherPage);

        const wifiButton = container.querySelector('[data-testid="rnode-transport-wifi"]');
        expect(wifiButton).toBeTruthy();
        await fireEvent.click(wifiButton);

        expect(container.querySelector("input#rnf-wifi-host")).toBeTruthy();
    });

    it("loads products from products.js", () => {
        const { container } = render(RNodeFlasherPage);
        const options = container.querySelectorAll("select#rnf-product-select option");
        expect(options.length).toBeGreaterThan(1);
    });

    it("links footer firmware and flasher pages to GitHub", () => {
        const { container } = render(RNodeFlasherPage);
        const html = container.innerHTML;
        expect(html).toContain('href="https://github.com/markqvist/RNode_Firmware"');
        expect(html).toContain('href="https://github.com/liamcottle/rnode-flasher"');
    });
});
