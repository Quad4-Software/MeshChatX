const { test, expect } = require("@playwright/test");
const { e2ePost, E2E_BACKEND_ORIGIN, prepareE2eSession } = require("./helpers");

// Live coverage for the favourite card dots menu. Rename and Remove go
// through in-app dialogs, so a broken dialog host or a stray click-outside
// handler makes both silently do nothing while the header star keeps
// working. Chrome stops dispatch once the panel is removed mid-click, so
// jsdom unit tests cannot catch this class of bug.
test.describe("NomadNet favourite context menu", () => {
    test("rename and remove from the dots menu reach the API", async ({ page, request }) => {
        await prepareE2eSession(request);

        const hash = "f".repeat(32);
        const added = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/favourites/add`, {
            destination_hash: hash,
            display_name: "E2E Favourite",
            aspect: "nomadnetwork.node",
        });
        expect(added.ok()).toBeTruthy();

        await page.goto("/#/nomadnetwork");

        const card = page.locator(".favourite-card").filter({ hasText: "E2E Favourite" });
        await expect(card).toBeVisible({ timeout: 20000 });

        // Rename through the dots menu.
        await card.locator("button").last().click();
        const menu = page.locator(".context-menu-panel").filter({ hasText: "Rename" });
        await expect(menu).toBeVisible();
        await menu.getByText("Rename", { exact: true }).click();

        const promptInput = page.locator('input[autocomplete="off"]');
        await expect(promptInput).toBeVisible({ timeout: 5000 });
        await promptInput.fill("E2E Renamed");
        const renameRequest = page.waitForRequest(
            (r) => r.url().includes(`/favourites/${hash}/rename`) && r.method() === "POST"
        );
        await page.getByRole("button", { name: "OK", exact: true }).click();
        await renameRequest;
        await expect(page.locator(".favourite-card").filter({ hasText: "E2E Renamed" })).toBeVisible();

        // Remove through the dots menu.
        const renamed = page.locator(".favourite-card").filter({ hasText: "E2E Renamed" });
        await renamed.locator("button").last().click();
        await page
            .locator(".context-menu-panel")
            .filter({ hasText: "Remove" })
            .getByText("Remove", { exact: true })
            .click();

        const confirmButton = page.getByRole("button", { name: "Confirm", exact: true });
        await expect(confirmButton).toBeVisible({ timeout: 5000 });
        const deleteRequest = page.waitForRequest(
            (r) => r.url().includes(`/favourites/${hash}`) && r.method() === "DELETE"
        );
        await confirmButton.click();
        await deleteRequest;
        await expect(page.locator(".favourite-card").filter({ hasText: "E2E Renamed" })).toHaveCount(0);
    });
});
