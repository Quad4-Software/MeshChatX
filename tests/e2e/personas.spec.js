const { test, expect } = require("@playwright/test");
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const { E2E_BACKEND_ORIGIN, e2ePost, prepareE2eSession, seedE2eLongConversationThread } = require("./helpers");

// Scripted persona crawl: three deterministic strategies over the route list,
// no LLM in the loop. Each persona stresses a different failure mode and all
// share the same oracle: uncaught pageerror, console error, HTTP 5xx, or a
// blank rendered body fails the test.

const ROUTES = [
    "/",
    "/about",
    "/interfaces",
    "/interfaces/add",
    "/messages",
    "/contacts",
    "/map",
    "/network-visualiser",
    "/relay-chat",
    "/archives",
    "/propagation-nodes",
    "/ping",
    "/rncp",
    "/rns-filesync",
    "/rnsh",
    "/rnx",
    "/rnstatus",
    "/rnpath",
    "/rnpath-trace",
    "/rnprobe",
    "/translator",
    "/bots",
    "/bots/new",
    "/forwarder",
    "/micron-editor",
    "/tools/reticulum-config-editor",
    "/mesh-server",
    "/documentation",
    "/profile/icon",
    "/settings",
    "/identities",
    "/blocked",
    "/tools",
    "/licenses",
    "/tools/paper-message",
    "/tools/nearby",
    "/tools/sieve-filters",
    "/tools/message-blocklist",
    "/tools/rnode-flasher",
    "/tools/repository-server",
    "/debug/logs",
    "/changelog",
    "/tutorial",
    "/call",
    "/nomadnetwork",
];

const SKIP_BUTTON =
    /delete|remove|wipe|clear|erase|format|flash|uninstall|block|unblock|call|dial|hang\s*up|send|shutdown|restart|reboot|logout|log\s*out|purge|destroy|factory|reset|import|export|upload|download|backup|restore|sign|authorize|approve|grant|execute|panic|save|apply|submit|confirm|accept|agree|allow|deny|\byes\b|\bok\b|connect|disconnect|enable|disable|provision|announce|pair|add|create|\bnew\b|update|install|\bset\b|switch|start|stop|\brun\b|purchase|pay|subscribe/i;

const IGNORED_CONSOLE_ERRORS = [
    /net::ERR_/i,
    /failed to fetch/i,
    /WebSocket/i,
    /404/,
    // Adversarial input is expected to produce 4xx rejections. the frontend
    // surfaces those as validation toasts. 5xx still means a real crash.
    /Failed to load resource: the server responded with a status of 4\d\d/i,
];

function watchErrors(page, errors) {
    page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
    page.on("console", (msg) => {
        if (msg.type() !== "error") {
            return;
        }
        const text = msg.text();
        if (!IGNORED_CONSOLE_ERRORS.some((re) => re.test(text))) {
            errors.push(`console: ${text}`);
        }
    });
    page.on("response", (resp) => {
        const status = resp.status();
        const url = resp.url();
        if (status >= 500 && !IGNORED_CONSOLE_ERRORS.some((re) => re.test(url))) {
            errors.push(`http ${status}: ${url}`);
        }
    });
}

async function assertRouteHealthy(page, errors, route) {
    const bodyText = await page
        .locator("body")
        .innerText()
        .catch(() => "");
    expect(bodyText.trim().length, `route ${route} rendered an empty body`).toBeGreaterThan(0);
    expect(errors, `route ${route}`).toEqual([]);
}

async function buttonLabel(btn) {
    return [
        (await btn.innerText().catch(() => "")) || "",
        (await btn.getAttribute("aria-label").catch(() => "")) || "",
        (await btn.getAttribute("title").catch(() => "")) || "",
    ]
        .join(" ")
        .trim();
}

const TEXT_INPUT_SELECTOR = [
    'input[type="text"]:visible',
    'input[type="search"]:visible',
    'input[type="url"]:visible',
    'input[type="email"]:visible',
    'input[type="number"]:visible',
    'input[type="password"]:visible',
    "input:not([type]):visible",
    "textarea:visible",
].join(", ");

const SHARE = process.env.E2E_PEER_SHARE || "/tmp/meshchatx-e2e-peer-share";
const READY = path.join(SHARE, "peer_ready.json");

function peerReady() {
    if (!fs.existsSync(READY)) {
        return null;
    }
    return JSON.parse(fs.readFileSync(READY, "utf8"));
}

async function seedContacts(request, count) {
    for (let i = 0; i < count; i++) {
        const res = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/telephone/contacts`, {
            name: `E2E Persona Contact ${i}`,
            remote_identity_hash: crypto.randomBytes(16).toString("hex"),
        });
        expect(res.ok(), await res.text()).toBeTruthy();
    }
}

async function hubStatus(request, hubHash) {
    const res = await request.get(`${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs`);
    if (!res.ok()) {
        return null;
    }
    const body = await res.json();
    const hub = (body.hubs || []).find((h) => h.hash === hubHash || h.hub_hash === hubHash);
    return hub ? hub.status : null;
}

// Populates /relay-chat via the live peer's RRC hub when the stack provides
// one (same API flow as live-mesh.spec.js). Returns false when no peer is up.
async function seedRrcRoom(request) {
    const peer = peerReady();
    if (!peer) {
        return false;
    }
    const hubHash = peer.hub_hash;
    const add = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs`, {
        hub_hash: hubHash,
        name: "E2E Persona Hub",
    });
    expect(add.ok(), await add.text()).toBeTruthy();
    await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/connect`, {});
    await expect.poll(() => hubStatus(request, hubHash), { timeout: 90000, intervals: [1000, 2000, 3000] }).toBe(2);
    const join = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/rooms`, {
        room: "lobby",
    });
    expect(join.ok(), await join.text()).toBeTruthy();
    for (let i = 0; i < 5; i++) {
        await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/rooms/lobby/messages`, {
            text: `e2e-persona-${i}-${Date.now()}`,
        });
    }
    return true;
}

test.describe("Persona exploratory crawl", () => {
    test.setTimeout(900000);
    test.describe.configure({ mode: "serial" });

    test.beforeEach(async ({ request }) => {
        await prepareE2eSession(request);
    });

    test("impatient persona clicks fast and navigates away mid-action", async ({ page }) => {
        const errors = [];
        watchErrors(page, errors);

        const clicked = [];
        for (const route of ROUTES) {
            errors.length = 0;
            await page.goto(`/#${route}`, { waitUntil: "domcontentloaded" });
            // Bound the wait for the app shell to mount, but never settle:
            // the persona clicks whatever is painted and moves on.
            await page
                .locator("button")
                .first()
                .waitFor({ state: "attached", timeout: 8000 })
                .catch(() => {});

            const buttons = await page.locator("button:visible").all();
            let clicks = 0;
            for (const btn of buttons) {
                if (clicks >= 3) {
                    break;
                }
                const label = await buttonLabel(btn);
                if (!label || SKIP_BUTTON.test(label)) {
                    continue;
                }
                try {
                    await btn.click({ timeout: 1000 });
                    clicks += 1;
                    // ZERO wait between clicks: race-condition coverage means
                    // the next click lands before the last action settles.
                } catch {
                    // Covered or detached element: skip.
                }
            }
            clicked.push(`${route}:${clicks}`);
            // Next loop iteration navigates away mid-action by design.
            await assertRouteHealthy(page, errors, route);
        }
        console.log(`impatient clicks: ${clicked.join(", ")}`);
    });

    test("adversarial persona fills every text input with hostile strings", async ({ page }) => {
        const errors = [];
        watchErrors(page, errors);

        const PAYLOADS = ["</script><img src=x>", "A".repeat(10000), "../../etc/passwd", "\uD800", "%s%s%s"];

        const filledLog = [];
        for (const route of ROUTES) {
            errors.length = 0;
            await page.goto(`/#${route}`, { waitUntil: "domcontentloaded" });
            await page.waitForTimeout(700);

            const inputs = await page.locator(TEXT_INPUT_SELECTOR).all();
            let fills = 0;
            for (const input of inputs.slice(0, 6)) {
                for (const payload of PAYLOADS) {
                    try {
                        await input.fill(payload, { timeout: 1500 });
                        await input.evaluate((el) => el.blur());
                        fills += 1;
                    } catch {
                        // Input detached or became readonly: move on.
                        break;
                    }
                }
            }
            filledLog.push(`${route}:${fills}`);
            await page.waitForTimeout(300);
            await assertRouteHealthy(page, errors, route);
        }
        console.log(`adversarial fills: ${filledLog.join(", ")}`);
    });

    test("data-heavy persona seeds backend state then crawls populated routes", async ({ page, request }) => {
        await seedE2eLongConversationThread(request, { messageCount: 60 });
        await seedContacts(request, 8);
        const rrcSeeded = await seedRrcRoom(request).catch((e) => {
            console.warn(`rrc seed skipped: ${e.message}`);
            return false;
        });
        console.log(`data-heavy seed: contacts=8 thread=60 rrc=${rrcSeeded}`);

        const errors = [];
        watchErrors(page, errors);

        for (const route of ROUTES) {
            errors.length = 0;
            await page.goto(`/#${route}`, { waitUntil: "domcontentloaded" });
            await page.waitForTimeout(1000);

            // Light interaction on populated state: open one safe control.
            const buttons = await page.locator("button:visible").all();
            for (const btn of buttons.slice(0, 2)) {
                const label = await buttonLabel(btn);
                if (!label || SKIP_BUTTON.test(label)) {
                    continue;
                }
                try {
                    await btn.click({ timeout: 1200 });
                    await page.waitForTimeout(200);
                    await page.keyboard.press("Escape");
                } catch {
                    // Unclickable element: skip.
                }
            }
            await assertRouteHealthy(page, errors, route);
        }
    });
});
