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

    test("active sessions list returns JSON with warning fields", async ({ request }) => {
        const res = await request.get("/api/v1/app/sessions");
        expect(res.ok()).toBeTruthy();
        const body = await res.json();
        expect(body).toHaveProperty("count");
        expect(body).toHaveProperty("sessions");
        expect(body).toHaveProperty("warning");
        expect(body).toHaveProperty("warning_enabled");
        expect(Array.isArray(body.sessions)).toBeTruthy();
        expect(body.count).toBeGreaterThanOrEqual(0);
        expect(body.warning).toBe(body.warning_enabled && body.count >= 2);
    });

    test("config exposes multi_session_warning_enabled", async ({ request }) => {
        const res = await request.get("/api/v1/config");
        expect(res.ok()).toBeTruthy();
        const body = await res.json();
        expect(body.config).toHaveProperty("multi_session_warning_enabled");
        expect(typeof body.config.multi_session_warning_enabled).toBe("boolean");
    });
});
