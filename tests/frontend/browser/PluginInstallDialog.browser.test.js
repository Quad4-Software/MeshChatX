// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import { render } from "vitest-browser-svelte";
import { page } from "vitest/browser";
import PluginInstallDialog from "../../../meshchatx/src/frontend/features/settings/components/PluginInstallDialog.svelte";

const preview = {
    id: "demo.plugin",
    name: "Demo Plugin",
    version: "1.0.0",
    description: "Test plugin",
    permissions: ["network:fetch", "ui:toast"],
    requires_network_fetch: true,
    network_endpoints: ["https://example.com/api"],
    signature: { present: false, valid: false },
    security_findings: [],
};

describe("PluginInstallDialog permission checkboxes (browser)", () => {
    it("toggles nested grantedMap entries and reports them on confirm", async () => {
        const confirmed = [];
        const result = await render(PluginInstallDialog, {
            open: true,
            preview,
            confirming: false,
            onconfirm: (data) => confirmed.push(data),
        });

        const checkboxes = page.getByRole("checkbox");
        await expect.element(checkboxes.nth(0)).toBeChecked();
        await expect.element(checkboxes.nth(1)).toBeChecked();
        await expect
            .element(page.getByText("Network access is not granted. These URLs will remain blocked."))
            .not.toBeInTheDocument();

        await checkboxes.nth(0).click();
        await expect.element(checkboxes.nth(0)).not.toBeChecked();
        await expect
            .element(page.getByText("Network access is not granted. These URLs will remain blocked."))
            .toBeInTheDocument();

        await page.getByRole("button", { name: "Install" }).click();
        expect(confirmed).toHaveLength(1);
        expect(confirmed[0].grantedPermissions).toEqual(["ui:toast"]);

        await result.unmount();
    });
});
