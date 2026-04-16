const crypto = require("crypto");
const { expect } = require("@playwright/test");

const E2E_BACKEND_PORT = process.env.E2E_BACKEND_PORT || "18079";
const E2E_BACKEND_ORIGIN = `http://127.0.0.1:${E2E_BACKEND_PORT}`;

const E2E_SCROLL_PEER_HASH = `e2e0${"0".repeat(28)}`;

function buildE2eLxmfRow({ peerHash, localHash, index, total, inbound }) {
    const hash = crypto.randomBytes(16).toString("hex");
    const baseTs = Math.floor(Date.now() / 1000) - total;
    return {
        hash,
        source_hash: inbound ? peerHash : localHash,
        destination_hash: inbound ? localHash : peerHash,
        peer_hash: peerHash,
        state: "delivered",
        progress: 1.0,
        is_incoming: inbound ? 1 : 0,
        method: "direct",
        delivery_attempts: 1,
        next_delivery_attempt_at: null,
        title: "",
        content: `E2E scroll seed ${String(index).padStart(3, "0")} ${"x".repeat(64)}`,
        fields: "{}",
        timestamp: baseTs + index,
        rssi: null,
        snr: null,
        quality: null,
        is_spam: 0,
        reply_to_hash: null,
        attachments_stripped: 0,
    };
}

/**
 * @param {import('@playwright/test').APIRequestContext} request
 * @returns {Promise<string>}
 */
async function getE2eLocalLxmfHash(request) {
    const cfgRes = await request.get(`${E2E_BACKEND_ORIGIN}/api/v1/config`);
    expect(cfgRes.ok()).toBeTruthy();
    const cfgBody = await cfgRes.json();
    const localHash = cfgBody.config?.lxmf_address_hash;
    expect(localHash && String(localHash).length === 32).toBeTruthy();
    return localHash;
}

/**
 * Inserts LXMF rows via maintenance import so the messages UI has a long thread for scroll tests.
 * @param {import('@playwright/test').APIRequestContext} request
 * @param {{ messageCount?: number }} [opts]
 * @returns {Promise<{ peerHash: string, localHash: string }>}
 */
async function seedE2eLongConversationThread(request, opts = {}) {
    const messageCount = opts.messageCount ?? 45;
    const localHash = await getE2eLocalLxmfHash(request);

    const peerHash = E2E_SCROLL_PEER_HASH;
    const messages = [];
    for (let i = 0; i < messageCount; i++) {
        messages.push(
            buildE2eLxmfRow({
                peerHash,
                localHash,
                index: i,
                total: messageCount,
                inbound: i % 2 === 0,
            })
        );
    }
    const imp = await request.post(`${E2E_BACKEND_ORIGIN}/api/v1/maintenance/messages/import`, {
        data: { messages },
    });
    expect(imp.ok()).toBeTruthy();
    return { peerHash, localHash };
}

const PALETTE_PLACEHOLDER = /Search commands,\s*(routes|navigate),\s*or peers\.{0,3}/i;

/**
 * Marks tutorial and changelog as seen on the E2E backend so first-load modals
 * (v-overlay scrim) do not block pointer clicks on the shell.
 */
async function prepareE2eSession(request) {
    const tutorial = await request.post(`${E2E_BACKEND_ORIGIN}/api/v1/app/tutorial/seen`);
    expect(tutorial.ok()).toBeTruthy();
    const changelog = await request.post(`${E2E_BACKEND_ORIGIN}/api/v1/app/changelog/seen`, {
        data: { version: "999.999.999" },
    });
    expect(changelog.ok()).toBeTruthy();
}

async function openCommandPalette(page) {
    await page.waitForLoadState("domcontentloaded");
    await page.keyboard.press("Control+K");
    let input = page.getByPlaceholder(PALETTE_PLACEHOLDER);
    if ((await input.count()) === 0) {
        await page.evaluate(() => {
            const ctrlK = new KeyboardEvent("keydown", {
                key: "k",
                code: "KeyK",
                ctrlKey: true,
                bubbles: true,
                cancelable: true,
            });
            window.dispatchEvent(ctrlK);
            document.dispatchEvent(ctrlK);
        });
        input = page.getByPlaceholder(PALETTE_PLACEHOLDER);
    }
    await expect(input).toBeVisible({ timeout: 15000 });
}

async function dismissMapOnboardingTooltip(page) {
    const onboardingBackdrop = page.locator(
        "div.fixed.inset-0.z-\\[100\\].pointer-events-none > div.absolute.inset-0.bg-black\\/50.pointer-events-auto"
    );
    if ((await onboardingBackdrop.count()) > 0) {
        await onboardingBackdrop.click({ timeout: 5000 });
        await expect(onboardingBackdrop).toBeHidden({ timeout: 10000 });
    }
}

module.exports = {
    E2E_BACKEND_ORIGIN,
    E2E_SCROLL_PEER_HASH,
    PALETTE_PLACEHOLDER,
    dismissMapOnboardingTooltip,
    openCommandPalette,
    prepareE2eSession,
    getE2eLocalLxmfHash,
    seedE2eLongConversationThread,
};
