const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");
const { E2E_BACKEND_ORIGIN, e2ePost, prepareE2eSession } = require("./helpers");

// Real two-peer mesh e2e: a standalone RNS+LXMF+RRC process links into the
// e2e backend over a TCP interface pair. Nothing is mocked: announces, path
// resolution, link establishment, LXMF delivery and the RRC
// HELLO/JOIN/echo flow all run over real Reticulum sockets.
const SHARE = process.env.E2E_PEER_SHARE || "/tmp/meshchatx-e2e-peer-share";
const READY = path.join(SHARE, "peer_ready.json");
const PEER_INBOX = path.join(SHARE, "peer_inbox.jsonl");
const PEER_OUTBOX = path.join(SHARE, "peer_outbox.jsonl");

function peerReady() {
    if (!fs.existsSync(READY)) {
        return null;
    }
    return JSON.parse(fs.readFileSync(READY, "utf8"));
}

function readJsonl(file) {
    if (!fs.existsSync(file)) {
        return [];
    }
    return fs
        .readFileSync(file, "utf8")
        .split("\n")
        .filter((l) => l.trim())
        .map((l) => JSON.parse(l));
}

async function localLxmfHash(request) {
    const cfg = await request.get(`${E2E_BACKEND_ORIGIN}/api/v1/config`);
    expect(cfg.ok()).toBeTruthy();
    const hash = (await cfg.json()).config?.lxmf_address_hash;
    expect(hash && String(hash).length).toBe(32);
    return hash;
}

test.describe("Live mesh e2e (real RNS peer)", () => {
    test.setTimeout(120000);
    // RRC cold-connect spans a full path-request window; give it headroom.
    test.skip(!peerReady(), "live peer subprocess not running");

    test.beforeEach(async ({ request }) => {
        await prepareE2eSession(request);
    });

    test("outbound LXMF reaches the real peer", async ({ request }) => {
        const peer = peerReady();
        const marker = `e2e-live-${Date.now()}`;
        const res = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/lxmf-messages/send`, {
            lxmf_message: {
                destination_hash: peer.lxmf_dest,
                content: marker,
            },
        });
        expect(res.ok(), await res.text()).toBeTruthy();

        // Peer inbox is written only when the LXMF delivery actually lands
        // over the link: announce -> path -> link -> direct delivery.
        await expect
            .poll(() => readJsonl(PEER_INBOX).some((m) => m.content === marker), {
                timeout: 60000,
                intervals: [500, 1000, 2000],
            })
            .toBe(true);
    });

    test("inbound LXMF from the real peer reaches the backend", async ({ request }) => {
        const peer = peerReady();
        const localHash = await localLxmfHash(request);
        const marker = `e2e-inbound-${Date.now()}`;
        fs.appendFileSync(PEER_OUTBOX, `${JSON.stringify({ dest: localHash, content: marker })}\n`);

        // Peer sends to the backend lxmf.delivery destination; the backend
        // stores it under the peer's conversation hash.
        await expect
            .poll(
                async () => {
                    const res = await request.get(
                        `${E2E_BACKEND_ORIGIN}/api/v1/lxmf-messages/conversation/${peer.lxmf_dest}`
                    );
                    if (!res.ok()) {
                        return false;
                    }
                    const body = await res.json();
                    const rows = body.messages || body.lxmf_messages || [];
                    return rows.some((m) => m.content === marker);
                },
                { timeout: 90000, intervals: [1000, 2000, 3000] }
            )
            .toBe(true);
    });

    test("RRC hub connect, join, and echo over a real link", async ({ request }) => {
        test.setTimeout(240000);
        const peer = peerReady();
        const hubHash = peer.hub_hash;

        const add = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs`, {
            hub_hash: hubHash,
            name: "E2E Live Hub",
        });
        expect(add.ok(), await add.text()).toBeTruthy();

        const connect = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/connect`, {});
        expect(connect.ok(), await connect.text()).toBeTruthy();

        // Path request + identity recall + link + HELLO + WELCOME.
        await expect
            .poll(
                async () => {
                    const res = await request.get(`${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs`);
                    if (!res.ok()) {
                        return null;
                    }
                    const body = await res.json();
                    const hub = (body.hubs || []).find((h) => h.hash === hubHash || h.hub_hash === hubHash);
                    return hub ? hub.status : null;
                },
                { timeout: 90000, intervals: [1000, 2000, 3000] }
            )
            .toBe(2); // RRCHub.STATUS_CONNECTED

        const join = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/rooms`, {
            room: "lobby",
        });
        expect(join.ok(), await join.text()).toBeTruthy();

        const marker = `e2e-rrc-${Date.now()}`;
        const send = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/rooms/lobby/messages`, {
            text: marker,
        });
        expect(send.ok(), await send.text()).toBeTruthy();

        // The hub relays our message back over the link; the echo flips the
        // delivery state to sent and lands in room history.
        await expect
            .poll(
                async () => {
                    const res = await request.get(
                        `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/rooms/lobby/messages`
                    );
                    if (!res.ok()) {
                        return null;
                    }
                    const body = await res.json();
                    const rows = body.messages || [];
                    const mine = rows.filter((r) => r.text === marker);
                    if (!mine.length) {
                        return null;
                    }
                    return mine[mine.length - 1].delivery || "unknown";
                },
                { timeout: 60000, intervals: [500, 1000, 2000] }
            )
            .toBe("sent");
    });
});
