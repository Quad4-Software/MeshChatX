const { test, expect } = require("@playwright/test");
const { prepareE2eSession } = require("./helpers");

test.describe("Deep-linked routes", () => {
    test.beforeEach(async ({ request }) => {
        await prepareE2eSession(request);
    });

    test("contacts page shows title and search", async ({ page }) => {
        await page.goto("/#/contacts");
        await expect(page).toHaveURL(/#\/contacts/);
        await expect(page.getByRole("heading", { name: "Contacts", exact: true })).toBeVisible({ timeout: 20000 });
        await expect(page.getByPlaceholder("Search contacts...", { exact: true })).toBeVisible();
    });

    test("map page shows map title and mode toggles", async ({ page }) => {
        await page.goto("/#/map");
        await expect(page).toHaveURL(/#\/map/);
        await expect(page.getByRole("heading", { name: "Map", exact: true })).toBeVisible({ timeout: 20000 });
        await expect(page.getByText("Online Mode", { exact: true })).toBeVisible();
    });

    test("archives page shows sidebar search", async ({ page }) => {
        await page.goto("/#/archives");
        await expect(page).toHaveURL(/#\/archives/);
        await expect(page.getByPlaceholder("Search nodes or content...", { exact: true })).toBeVisible({
            timeout: 20000,
        });
    });

    test("interfaces page lists add interface action", async ({ page }) => {
        await page.goto("/#/interfaces");
        await expect(page).toHaveURL(/#\/interfaces/);
        await expect(page.getByRole("link", { name: /Add Interface/i })).toBeVisible({ timeout: 20000 });
    });

    test("interfaces add route shows add interface heading", async ({ page }) => {
        await page.goto("/#/interfaces/add");
        await expect(page).toHaveURL(/#\/interfaces\/add/);
        await expect(page.locator("h1").filter({ hasText: "Add Interface" })).toBeVisible({ timeout: 20000 });
    });

    test("identities page shows identities heading", async ({ page }) => {
        await page.goto("/#/identities");
        await expect(page).toHaveURL(/#\/identities/);
        await expect(page.getByRole("heading", { name: "Identities", exact: true })).toBeVisible({ timeout: 20000 });
    });

    test("network visualiser shows mesh chrome", async ({ page }) => {
        await page.goto("/#/network-visualiser");
        await expect(page).toHaveURL(/#\/network-visualiser/);
        await expect(page.getByText("Reticulum Mesh", { exact: true })).toBeVisible({ timeout: 30000 });
    });

    test("propagation nodes route loads empty state or searchable list", async ({ page }) => {
        await page.goto("/#/propagation-nodes");
        await expect(page).toHaveURL(/#\/propagation-nodes/);
        await expect(page.getByText("Hosted Propagation Node", { exact: true })).toBeVisible({ timeout: 20000 });

        const emptyState = page.getByText("No Propagation Nodes", { exact: true });
        const searchInput = page.getByPlaceholder(/Search \d+ Propagation Nodes\.\.\./);
        const hasEmptyState = (await emptyState.count()) > 0;
        if (hasEmptyState) {
            await expect(emptyState).toBeVisible({ timeout: 20000 });
        } else {
            await expect(searchInput).toBeVisible({ timeout: 20000 });
        }
    });

    test("ping tool page shows title", async ({ page }) => {
        await page.goto("/#/ping");
        await expect(page).toHaveURL(/#\/ping/);
        await expect(page.getByText("Ping Mesh Peers", { exact: true })).toBeVisible({ timeout: 20000 });
    });

    test("documentation page shows title", async ({ page }) => {
        await page.goto("/#/documentation");
        await expect(page).toHaveURL(/#\/documentation/);
        await expect(page.getByRole("heading", { name: "Documentation", exact: true })).toBeVisible({
            timeout: 20000,
        });
    });

    test("blocked page shows banished heading", async ({ page }) => {
        await page.goto("/#/blocked");
        await expect(page).toHaveURL(/#\/blocked/);
        await expect(page.getByRole("heading", { name: "Banished", exact: true })).toBeVisible({ timeout: 20000 });
    });

    test("header telephone button opens call route", async ({ page }) => {
        await page.goto("/#/messages");
        await page.getByTitle("Telephone", { exact: true }).click();
        await expect(page).toHaveURL(/#\/call/, { timeout: 15000 });
        await expect(page.getByRole("button", { name: "Phone", exact: true })).toBeVisible({ timeout: 20000 });
    });
});
