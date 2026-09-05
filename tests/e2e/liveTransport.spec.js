const { test, expect } = require("@playwright/test");

test.describe("Live transport status + settings (WSS path)", () => {
    test("status advertises webtransport object when sidecar off", async ({ request }) => {
        const res = await request.get("/api/v1/status");
        expect(res.ok()).toBeTruthy();
        const body = await res.json();
        expect(body.webtransport).toBeTruthy();
        expect(body.webtransport.experimental).toBe(true);
        expect(typeof body.webtransport.server_available).toBe("boolean");
        if (body.webtransport.server_available !== true) {
            expect([
                "disabled",
                "http_only",
                "aioquic_missing",
                "bind_failed",
                "landlock_udp",
                "unsupported_platform",
                "listener_pending",
            ]).toContain(body.webtransport.reason);
        }
    });
});
