const { test, expect } = require("@playwright/test");
const {
    prepareE2eSession,
    seedE2eLongConversationThread,
    getE2eLocalLxmfHash,
    E2E_SCROLL_PEER_HASH,
} = require("./helpers");

async function scrollMetrics(page) {
    const loc = page.locator("#messages");
    await expect(loc).toBeVisible({ timeout: 30000 });
    return loc.evaluate((el) => ({
        scrollTop: el.scrollTop,
        scrollHeight: el.scrollHeight,
        clientHeight: el.clientHeight,
    }));
}

async function setMessagesToBottom(page) {
    await page.locator("#messages").evaluate((el) => {
        const inner = el.firstElementChild;
        const reverse = inner && getComputedStyle(inner).flexDirection === "column-reverse";
        if (reverse) {
            el.scrollTop = 0;
            return;
        }
        el.scrollTop = Math.max(0, el.scrollHeight - el.clientHeight);
    });
}

async function messagesDistanceFromBottom(page) {
    return page.locator("#messages").evaluate((el) => {
        const inner = el.firstElementChild;
        const reverse = inner && getComputedStyle(inner).flexDirection === "column-reverse";
        const max = Math.max(0, el.scrollHeight - el.clientHeight);
        if (reverse) {
            return el.scrollTop;
        }
        return max - el.scrollTop;
    });
}

async function messagesNearBottom(page) {
    return page.locator("#messages").evaluate((el) => {
        const inner = el.firstElementChild;
        const reverse = inner && getComputedStyle(inner).flexDirection === "column-reverse";
        const max = Math.max(0, el.scrollHeight - el.clientHeight);
        const eps = 12;
        if (reverse) {
            return el.scrollTop <= eps;
        }
        return max - el.scrollTop <= eps;
    });
}

async function waitForMessagesOverflow(page) {
    await page.waitForFunction(
        () => {
            const el = document.getElementById("messages");
            if (!el) {
                return false;
            }
            return el.scrollHeight > el.clientHeight + 100;
        },
        null,
        { timeout: 30000 }
    );
}

test.describe("Messages conversation scroll", () => {
    test.use({ viewport: { width: 1280, height: 360 } });

    test.beforeAll(async ({ request }) => {
        await prepareE2eSession(request);
        await seedE2eLongConversationThread(request, { messageCount: 120 });
    });

    test.beforeEach(async ({ request }) => {
        await prepareE2eSession(request);
    });

    test("starts near bottom with a long thread", async ({ page }) => {
        await page.goto("/#/messages");
        await expect(page.getByText("Conversations", { exact: true }).first()).toBeVisible({ timeout: 25000 });
        await page
            .locator(".conversation-item")
            .filter({ hasText: /E2E scroll seed/ })
            .first()
            .click();
        await expect(page.locator("#messages")).toBeVisible({ timeout: 25000 });
        await expect(
            page
                .locator("#messages")
                .getByText(/E2E scroll seed 119/)
                .first()
        ).toBeVisible({
            timeout: 25000,
        });

        await waitForMessagesOverflow(page);
        const m = await scrollMetrics(page);
        expect(m.scrollHeight).toBeGreaterThan(m.clientHeight + 80);
        expect(await messagesNearBottom(page)).toBe(true);
    });

    test("does not jump to bottom when scrolled up and inbound arrives", async ({ page, request }) => {
        const localHash = await getE2eLocalLxmfHash(request);
        await page.goto("/#/messages");
        await expect(page.getByText("Conversations", { exact: true }).first()).toBeVisible({ timeout: 25000 });
        await page
            .locator(".conversation-item")
            .filter({ hasText: /E2E scroll seed/ })
            .first()
            .click();
        await expect(page.locator("#messages")).toBeVisible({ timeout: 25000 });
        await waitForMessagesOverflow(page);

        await page.locator("#messages").evaluate(() => {
            const el = document.getElementById("messages");
            if (!el) {
                return;
            }
            const max = Math.max(0, el.scrollHeight - el.clientHeight);
            el.scrollTop = Math.max(0, max - 200);
        });
        await page.waitForTimeout(300);
        const before = await scrollMetrics(page);
        expect(await messagesNearBottom(page)).toBe(false);

        await page.evaluate(
            ({ peerHash, localHash: lh }) => {
                const buf = new Uint8Array(16);
                window.crypto.getRandomValues(buf);
                const hash = Array.from(buf, (b) => b.toString(16).padStart(2, "0")).join("");
                return import("/js/WebSocketConnection.js").then((mod) => {
                    mod.default.emit("message", {
                        data: JSON.stringify({
                            type: "lxmf.delivery",
                            lxmf_message: {
                                hash,
                                source_hash: peerHash,
                                destination_hash: lh,
                                content: "E2E synthetic inbound (scroll up)",
                                timestamp: Math.floor(Date.now() / 1000),
                            },
                        }),
                    });
                });
            },
            { peerHash: E2E_SCROLL_PEER_HASH, localHash }
        );

        await page.waitForTimeout(500);
        expect(await messagesNearBottom(page)).toBe(false);
    });

    test("stays pinned to bottom when new inbound arrives while at bottom", async ({ page, request }) => {
        const localHash = await getE2eLocalLxmfHash(request);
        await page.goto("/#/messages");
        await expect(page.getByText("Conversations", { exact: true }).first()).toBeVisible({ timeout: 25000 });
        await page
            .locator(".conversation-item")
            .filter({ hasText: /E2E scroll seed/ })
            .first()
            .click();
        await expect(page.locator("#messages")).toBeVisible({ timeout: 25000 });
        await waitForMessagesOverflow(page);

        await setMessagesToBottom(page);
        await page.waitForTimeout(200);
        expect(await messagesNearBottom(page)).toBe(true);

        await page.evaluate(
            ({ peerHash, localHash: lh }) => {
                const buf = new Uint8Array(16);
                window.crypto.getRandomValues(buf);
                const hash = Array.from(buf, (b) => b.toString(16).padStart(2, "0")).join("");
                return import("/js/WebSocketConnection.js").then((mod) => {
                    mod.default.emit("message", {
                        data: JSON.stringify({
                            type: "lxmf.delivery",
                            lxmf_message: {
                                hash,
                                source_hash: peerHash,
                                destination_hash: lh,
                                content: "E2E synthetic inbound (at bottom)",
                                timestamp: Math.floor(Date.now() / 1000),
                            },
                        }),
                    });
                });
            },
            { peerHash: E2E_SCROLL_PEER_HASH, localHash }
        );

        await page.waitForTimeout(600);
        expect(await messagesNearBottom(page)).toBe(true);
    });

    test("preserves scroll anchor when loading older messages from the top", async ({ page }) => {
        await page.goto("/#/messages");
        await expect(page.getByText("Conversations", { exact: true }).first()).toBeVisible({ timeout: 25000 });
        await page
            .locator(".conversation-item")
            .filter({ hasText: /E2E scroll seed/ })
            .first()
            .click();
        await expect(page.locator("#messages")).toBeVisible({ timeout: 25000 });
        await waitForMessagesOverflow(page);

        const initial = await scrollMetrics(page);
        expect(initial.scrollHeight).toBeGreaterThan(initial.clientHeight + 80);

        await page.locator("#messages").hover();
        for (let i = 0; i < 60; i++) {
            await page.mouse.wheel(0, -500);
        }
        await page.waitForTimeout(2500);
        const loaded = await scrollMetrics(page);
        if (loaded.scrollHeight > initial.scrollHeight) {
            expect(await messagesDistanceFromBottom(page)).toBeGreaterThan(8);
        }
    });
});
