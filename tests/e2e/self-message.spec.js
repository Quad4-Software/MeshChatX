const { test, expect } = require("@playwright/test");
const { E2E_BACKEND_ORIGIN, e2ePost, prepareE2eSession } = require("./helpers");

test.describe("E2E CSRF API helpers", () => {
    test("POST /app/tutorial/seen without CSRF token is rejected", async ({ request }) => {
        const res = await request.post(`${E2E_BACKEND_ORIGIN}/api/v1/app/tutorial/seen`);
        expect(res.status()).toBe(403);
    });

    test("e2ePost succeeds for tutorial and changelog seen", async ({ request }) => {
        await prepareE2eSession(request);
    });
});

test.describe("Local self-message API", () => {
    test.beforeEach(async ({ request }) => {
        await prepareE2eSession(request);
    });

    test("POST lxmf-messages/send to own LXMF hash returns delivered local", async ({ request }) => {
        const cfg = await request.get(`${E2E_BACKEND_ORIGIN}/api/v1/config`);
        expect(cfg.ok()).toBeTruthy();
        const localHash = (await cfg.json()).config?.lxmf_address_hash;
        expect(localHash && String(localHash).length).toBe(32);

        const res = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/lxmf-messages/send`, {
            lxmf_message: {
                destination_hash: localHash,
                content: "E2E personal note",
            },
        });
        expect(res.ok(), await res.text()).toBeTruthy();
        const body = await res.json();
        const lm = body.lxmf_message;
        expect(lm.state).toBe("delivered");
        expect(lm.method).toBe("local");
        expect(lm.content).toBe("E2E personal note");
    });

    test("propagated send to self is rejected", async ({ request }) => {
        const cfg = await request.get(`${E2E_BACKEND_ORIGIN}/api/v1/config`);
        const localHash = (await cfg.json()).config?.lxmf_address_hash;
        const res = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/lxmf-messages/send`, {
            delivery_method: "propagated",
            lxmf_message: {
                destination_hash: localHash,
                content: "nope",
            },
        });
        expect(res.ok()).toBeFalsy();
        expect(res.status()).toBeGreaterThanOrEqual(400);
    });
});
