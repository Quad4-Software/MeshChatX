// Regression coverage for relay chat history paging in the virtualized
// message list. All /api/v1 traffic is mocked in-page: one connected hub, one
// room with 600 seeded messages, paging honored exactly like the backend
// (limit + before_seq + has_more).
const { test, expect } = require("@playwright/test");

const HUB_HASH = "a".repeat(32);
const ROOM = "general";
const TOTAL_MESSAGES = 600;
const SCROLL_SEL = ".overflow-y-auto.custom-scrollbar.bg-sem-canvas";

function seedMessages() {
    const out = [];
    for (let i = 1; i <= TOTAL_MESSAGES; i++) {
        out.push({
            kind: "msg",
            room: ROOM,
            src: "b".repeat(32),
            nick: "alice",
            text: `seed message ${String(i).padStart(4, "0")}`,
            ts: 1700000000 + i * 1000,
            mention: false,
            seq: i,
        });
    }
    return out;
}

function fulfillJson(route, body, status = 200) {
    return route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(body),
    });
}

async function installRrcMocks(page, requestLog) {
    const allMessages = seedMessages();
    await page.route("**/api/v1/**", (route) => {
        const url = new URL(route.request().url());
        const path = url.pathname;
        const method = route.request().method();
        if (path === "/api/v1/status") {
            return fulfillJson(route, {
                status: "ok",
                network_ready: true,
                ui_ready: true,
                is_loopback_bind: true,
            });
        }
        if (path === "/api/v1/auth/csrf") {
            return fulfillJson(route, { csrf_token: "x".repeat(32) });
        }
        if (path === "/api/v1/auth/status") {
            return fulfillJson(route, { auth_enabled: false, authenticated: true });
        }
        if (path === "/api/v1/rrc/hubs" && method === "GET") {
            return fulfillJson(route, {
                hubs: [
                    {
                        hub_hash: HUB_HASH,
                        dest_name: "e2e",
                        name: "E2E Hub",
                        display_name: "E2E Hub",
                        custom_name: null,
                        status: 2,
                        status_text: "connected",
                        connected: true,
                        rooms: [ROOM],
                        known_rooms: [ROOM],
                        unread_rooms: [],
                        unread_counts: {},
                        total_unread: 0,
                        mention_rooms: [],
                        available_rooms: {},
                        stored_key_rooms: [],
                        member_count: 2,
                    },
                ],
            });
        }
        if (/^\/api\/v1\/rrc\/hubs\/[0-9a-f]+\/rooms\/[^/]+\/messages$/.test(path) && method === "GET") {
            const limit = Math.min(parseInt(url.searchParams.get("limit") || "150", 10), 500);
            const beforeRaw = url.searchParams.get("before_seq");
            const beforeSeq = beforeRaw ? parseInt(beforeRaw, 10) : null;
            let msgs = allMessages.slice();
            if (beforeSeq !== null) {
                msgs = msgs.filter((m) => m.seq < beforeSeq);
            }
            let hasMore = false;
            if (msgs.length > limit) {
                hasMore = true;
                msgs = msgs.slice(-limit);
            }
            requestLog.push({ before_seq: beforeSeq, returned: msgs.length, has_more: hasMore });
            return fulfillJson(route, { messages: msgs, members: [], has_more: hasMore });
        }
        return fulfillJson(route, {});
    });
}

async function openRoom(page) {
    await page.goto(`/#/relay-chat?hub=${HUB_HASH}&room=${ROOM}`);
    await page.waitForSelector(`${SCROLL_SEL} [data-index]`, { timeout: 30000 });
    await page.waitForTimeout(800);
}

// The first timeline row whose bottom edge is inside the viewport.
function topVisibleRow(page) {
    return page.locator(SCROLL_SEL).evaluate((el) => {
        const rows = [...el.querySelectorAll("[data-index]")];
        const viewTop = el.getBoundingClientRect().top;
        const first = rows.find((r) => r.getBoundingClientRect().bottom > viewTop);
        if (!first) {
            return null;
        }
        return {
            text: first.textContent.match(/seed message \d+/)?.[0] || "",
            viewportTop: first.getBoundingClientRect().top - viewTop,
        };
    });
}

function rowViewportTopForText(page, text) {
    return page.locator(SCROLL_SEL).evaluate((el, needle) => {
        const row = [...el.querySelectorAll("[data-index]")].find((r) => r.textContent.includes(needle));
        if (!row) {
            return null;
        }
        return row.getBoundingClientRect().top - el.getBoundingClientRect().top;
    }, text);
}

test.describe("relay chat history paging", () => {
    test("scrolling up pages back to the oldest message", async ({ page }) => {
        const requestLog = [];
        await installRrcMocks(page, requestLog);
        await openRoom(page);

        // Wheel upward until the oldest seeded message renders.
        await page.locator(SCROLL_SEL).hover();
        let reachedTop = false;
        for (let i = 0; i < 80 && !reachedTop; i++) {
            await page.mouse.wheel(0, -700);
            await page.waitForTimeout(250);
            reachedTop = await page.locator(SCROLL_SEL).evaluate((el) => el.textContent.includes("seed message 0001"));
        }
        expect(reachedTop).toBeTruthy();

        // History must have been paged backwards: initial fetch (before_seq
        // null) then descending before_seq cursors down to the floor.
        const cursors = requestLog.map((r) => r.before_seq).filter((v) => v !== null);
        expect(cursors.length).toBeGreaterThanOrEqual(5);
        expect(cursors).toEqual([...cursors].sort((a, b) => b - a));
        expect(cursors[0]).toBe(451);
        expect(cursors.at(-1)).toBe(51);
        expect(requestLog.at(-1).has_more).toBe(false);
    });

    test("a prepend keeps rendered rows mounted and roughly anchored", async ({ page }) => {
        const requestLog = [];
        await installRrcMocks(page, requestLog);
        await openRoom(page);

        // Park just above the load edge so rendered rows settle, then dip
        // below the threshold to trigger exactly one older-page fetch.
        const scrollEl = page.locator(SCROLL_SEL);
        await scrollEl.evaluate((el) => {
            el.scrollTop = 250;
        });
        await page.waitForTimeout(500);
        const before = await topVisibleRow(page);
        expect(before).not.toBeNull();
        const scrollHeightBefore = await scrollEl.evaluate((el) => el.scrollHeight);

        // Tag the rendered row nodes. With index-derived keys a prepend
        // remounts every row and the tags vanish; with stable entry keys the
        // same DOM nodes follow their entries.
        await scrollEl.evaluate((el) => {
            for (const row of el.querySelectorAll("[data-index]")) {
                row.setAttribute("data-e2e-row-tag", "1");
            }
        });

        await scrollEl.evaluate((el) => {
            el.scrollTop = 100;
        });
        await page.waitForFunction(
            (sh) => document.querySelector(".overflow-y-auto.custom-scrollbar.bg-sem-canvas").scrollHeight !== sh,
            scrollHeightBefore,
            { timeout: 10000 }
        );
        await page.waitForTimeout(1200);
        expect(requestLog.filter((r) => r.before_seq !== null).length).toBeGreaterThanOrEqual(1);

        // Prepend must not remount the still-rendered rows.
        const taggedStillMounted = await scrollEl.evaluate(
            (el) => el.querySelectorAll("[data-index][data-e2e-row-tag]").length
        );
        expect(taggedStillMounted).toBeGreaterThan(0);

        // The row that sat at the top of the viewport stays near its old
        // offset. Residual error is bounded by estimate-vs-measured height
        // of the unrendered prepended rows.
        const afterTop = await rowViewportTopForText(page, before.text);
        expect(afterTop).not.toBeNull();
        expect(Math.abs(afterTop - before.viewportTop)).toBeLessThanOrEqual(200);
    });
});
