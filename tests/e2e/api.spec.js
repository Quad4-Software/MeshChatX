const { test, expect } = require("@playwright/test");
const { prepareE2eSession } = require("./helpers");

test.describe("HTTP API (via Vite proxy)", () => {
    test.beforeEach(async ({ request }) => {
        await prepareE2eSession(request);
    });

    test("database backups list returns JSON", async ({ request }) => {
        const res = await request.get("/api/v1/database/backups");
        expect(res.ok()).toBeTruthy();
        const body = await res.json();
        expect(body).toHaveProperty("backups");
        expect(Array.isArray(body.backups)).toBeTruthy();
    });
});
