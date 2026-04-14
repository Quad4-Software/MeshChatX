const { test, expect } = require("@playwright/test");
const { prepareE2eSession } = require("./helpers");

test.describe("Messages (conversations)", () => {
    test.beforeEach(async ({ request }) => {
        await prepareE2eSession(request);
    });

    test("shows conversation sidebar and empty chat state", async ({ page }) => {
        await page.goto("/#/messages");
        await expect(page).toHaveURL(/#\/messages/);
        await expect(page.getByText("Conversations", { exact: true }).first()).toBeVisible({ timeout: 25000 });
        await expect(page.getByText("No Conversations", { exact: true })).toBeVisible({ timeout: 25000 });
        await expect(page.getByText("No Active Chat", { exact: true })).toBeVisible({ timeout: 25000 });
        await expect(page.getByText(/Select a peer from the sidebar/i)).toBeVisible({ timeout: 15000 });
    });

    test("switches sidebar to Announces tab and shows peer discovery copy", async ({ page }) => {
        await page.goto("/#/messages");
        await page.getByText("Announces", { exact: true }).first().click();
        await expect(page.getByPlaceholder(/Search .* recent announces/i)).toBeVisible({ timeout: 20000 });
        await expect(
            page.getByText(/No Peers Discovered|Waiting for someone to announce/i).first()
        ).toBeVisible({ timeout: 20000 });
    });

    test("sidebar navigates between Nomad Network and Messages", async ({ page }) => {
        await page.goto("/#/nomadnetwork");
        await expect(page).toHaveURL(/#\/nomadnetwork/);
        await expect(page.getByText("No Active Node", { exact: true })).toBeVisible({ timeout: 30000 });

        const sideNav = page.locator("ul.py-3");
        await sideNav.locator('a[href*="#/messages"]').click();
        await expect(page).toHaveURL(/#\/messages/, { timeout: 15000 });
        await expect(page.getByText("No Active Chat", { exact: true })).toBeVisible({ timeout: 25000 });

        await sideNav.locator('a[href*="#/nomadnetwork"]').click();
        await expect(page).toHaveURL(/#\/nomadnetwork/, { timeout: 15000 });
        await expect(page.getByText("No Active Node", { exact: true })).toBeVisible({ timeout: 25000 });
    });
});

test.describe("Nomad Network", () => {
    test.beforeEach(async ({ request }) => {
        await prepareE2eSession(request);
    });

    test("shows empty state and sidebar tabs", async ({ page }) => {
        await page.goto("/#/nomadnetwork");
        await expect(page).toHaveURL(/#\/nomadnetwork/);
        await expect(page.getByText("No Active Node", { exact: true })).toBeVisible({ timeout: 25000 });
        await expect(page.getByText(/Select a Node to start browsing/i)).toBeVisible({ timeout: 15000 });
        await expect(page.getByText("Favourites", { exact: true }).first()).toBeVisible({ timeout: 15000 });
        await expect(page.getByText("Announces", { exact: true }).first()).toBeVisible({ timeout: 15000 });
    });
});

test.describe("Network visualiser", () => {
    test.beforeEach(async ({ request }) => {
        await prepareE2eSession(request);
    });

    test("shows mesh header, graph container, and node search", async ({ page }) => {
        await page.goto("/#/network-visualiser");
        await expect(page).toHaveURL(/#\/network-visualiser/);
        await expect(page.getByText("Reticulum Mesh", { exact: true })).toBeVisible({ timeout: 30000 });
        await expect(page.locator("#network")).toBeAttached();
        await expect(page.getByPlaceholder(/Search nodes \(\d+\)/)).toBeVisible({ timeout: 30000 });
    });

    test("collapses and expands control panel via header", async ({ page }) => {
        await page.goto("/#/network-visualiser");
        await expect(page.getByText("Reticulum Mesh", { exact: true })).toBeVisible({ timeout: 30000 });
        await expect(page.getByText("Auto Update", { exact: true })).toBeVisible({ timeout: 30000 });
        await page.getByText("Reticulum Mesh", { exact: true }).click();
        await expect(page.getByText("Auto Update", { exact: true })).toBeHidden({ timeout: 10000 });
        await page.getByText("Reticulum Mesh", { exact: true }).click();
        await expect(page.getByText("Auto Update", { exact: true })).toBeVisible({ timeout: 10000 });
    });
});
