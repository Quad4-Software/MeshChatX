// Two-instance messaging backbone: deterministic Playwright driving both
// UIs against the live Alice/Bob pair started by pair-up.sh.
//
// Covers: text delivery both ways, attachment send, and (best-effort) a
// call signaling attempt. The agent prompts (prompts/pair-*.md) layer
// exploratory work on top of this verified baseline.
//
// Usage: node tests/agentic/pair-messaging.cjs [--skip-call]

const { chromium } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const SHARE = process.env.AGENTIC_PAIRSHARE || path.resolve(__dirname, "out", "pairshare");
const PAIR = JSON.parse(fs.readFileSync(path.join(SHARE, "pair.json"), "utf8"));

async function csrf(request, base) {
    const res = await request.get(`${base}/api/v1/auth/csrf`);
    return (await res.json()).csrf_token;
}

async function post(request, base, p, data) {
    return request.post(`${base}${p}`, {
        headers: { "X-CSRF-Token": await csrf(request, base) },
        data,
    });
}

async function sendMessage(request, from, toHash, content, fields) {
    const res = await post(request, from, "/api/v1/lxmf-messages/send", {
        lxmf_message: { destination_hash: toHash, content, fields },
    });
    if (!res.ok()) {
        throw new Error(`send failed ${res.status()}: ${await res.text()}`);
    }
    return res.json();
}

async function conversation(request, apiBase, peerHash) {
    const res = await request.get(`${apiBase}/api/v1/lxmf-messages/conversation/${peerHash}`);
    if (!res.ok()) {
        return [];
    }
    const body = await res.json();
    return body.messages || body.lxmf_messages || body.conversation || [];
}

async function waitForMessage(request, apiBase, peerHash, needle, timeoutMs = 90000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
        const msgs = await conversation(request, apiBase, peerHash);
        const hit = msgs.find(
            (m) => (m.content || "").includes(needle) || (m.title || "").includes(needle),
        );
        if (hit) {
            return hit;
        }
        await new Promise((r) => setTimeout(r, 1500));
    }
    return null;
}

async function main() {
    const skipCall = process.argv.includes("--skip-call");
    const results = [];

    const browser = await chromium.launch();
    const ctx = await browser.newContext();
    const req = ctx.request;

    // 1. Text A -> B
    const marker1 = `pair-msg-${Date.now()}`;
    await sendMessage(req, PAIR.alice.api, PAIR.bob.lxmf_address, marker1);
    const got1 = await waitForMessage(req, PAIR.bob.url, PAIR.alice.lxmf_address, marker1);
    results.push({ step: "text A->B", ok: Boolean(got1) });
    console.log(`${got1 ? "ok " : "!! "}text A->B ${got1 ? "delivered" : "not delivered"}`);

    // 2. Text B -> A (reply direction)
    const marker2 = `pair-reply-${Date.now()}`;
    await sendMessage(req, PAIR.bob.url, PAIR.alice.lxmf_address, marker2);
    const got2 = await waitForMessage(req, PAIR.alice.api, PAIR.bob.lxmf_address, marker2);
    results.push({ step: "text B->A", ok: Boolean(got2) });
    console.log(`${got2 ? "ok " : "!! "}text B->A ${got2 ? "delivered" : "not delivered"}`);

    // 3. Attachment A -> B (tiny png through file_attachments field)
    const png = Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
        "base64",
    );
    const marker3 = `pair-attach-${Date.now()}`;
    await sendMessage(req, PAIR.alice.api, PAIR.bob.lxmf_address, marker3, {
        file_attachments: [
            {
                file_name: "probe.png",
                file_bytes: png.toString("base64"),
            },
        ],
    });
    const got3 = await waitForMessage(req, PAIR.bob.url, PAIR.alice.lxmf_address, marker3);
    const hasAttachment =
        got3 && JSON.stringify(got3).match(/file_attachments|probe\.png|attachment/i);
    results.push({ step: "attachment A->B", ok: Boolean(hasAttachment) });
    console.log(
        `${hasAttachment ? "ok " : "!! "}attachment A->B ${hasAttachment ? "received" : got3 ? "msg arrived but no attachment" : "not delivered"}`,
    );

    // 4. Call signaling (best-effort: headless has no audio, we only check
    //    the call UI entry appears and the call route loads on both sides).
    if (!skipCall) {
        const pageA = await ctx.newPage();
        const pageB = await ctx.newPage();
        try {
            await pageA.goto(`${PAIR.alice.url}/#/messages/${PAIR.bob.lxmf_address}`, {
                waitUntil: "domcontentloaded",
            });
            await pageB.goto(`${PAIR.bob.url}/#/call`, { waitUntil: "domcontentloaded" });
            await pageA.waitForTimeout(2000);
            await pageB.waitForTimeout(2000);
            const callBtnA = await pageA
                .locator('button:visible, a:visible', { hasText: /call|dial|phone/i })
                .count();
            const callUiB = await pageB.locator("text=/call|telephone|dial|waiting/i").count();
            const ok = callBtnA > 0 && callUiB > 0;
            results.push({ step: "call signaling ui", ok });
            console.log(`${ok ? "ok " : "!! "}call ui present (A controls=${callBtnA}, B call page=${callUiB})`);
        } catch (e) {
            results.push({ step: "call signaling ui", ok: false, error: String(e) });
            console.log(`!! call signaling ui: ${e}`);
        }
    }

    await browser.close();

    const failed = results.filter((r) => !r.ok);
    console.log(`\npair messaging: ${results.length - failed.length}/${results.length} ok`);
    process.exit(failed.length ? 1 : 0);
}

main().catch((e) => {
    console.error(e);
    process.exit(2);
});
