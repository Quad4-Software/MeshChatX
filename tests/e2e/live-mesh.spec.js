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

async function interfaceBytes(request) {
    const res = await request.get(`${E2E_BACKEND_ORIGIN}/api/v1/interface-stats`);
    if (!res.ok()) {
        return null;
    }
    const body = await res.json();
    const ifs = body.interface_stats?.interfaces || [];
    let rx = 0,
        tx = 0;
    for (const i of ifs) {
        rx += Number(i.rxb || 0);
        tx += Number(i.txb || 0);
    }
    return { rx, tx };
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
        // Wait until the peer's announce is in the table so the send path is warm.
        await expect
            .poll(
                async () => {
                    const res = await request.get(`${E2E_BACKEND_ORIGIN}/api/v1/announces?limit=50`);
                    if (!res.ok()) {
                        return false;
                    }
                    const rows = (await res.json()).announces || [];
                    return rows.some((a) => a.destination_hash === peer.lxmf_dest);
                },
                { timeout: 60000, intervals: [500, 1000, 2000] }
            )
            .toBe(true);
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

test.describe("Live mesh LXST call", () => {
    test.setTimeout(180000);
    test.skip(!peerReady(), "live peer subprocess not running");

    test("dial a real peer, establish, and hang up", async ({ request }) => {
        await prepareE2eSession(request);
        const peer = peerReady();

        const statusBefore = await request.get(`${E2E_BACKEND_ORIGIN}/api/v1/telephone/status`);
        expect(statusBefore.ok()).toBeTruthy();
        const before = await statusBefore.json();
        expect(before.enabled).toBe(true);

        const dial = await e2ePost(
            request,
            `${E2E_BACKEND_ORIGIN}/api/v1/telephone/call/${peer.identity_hash}?timeout=60`
        );
        expect(dial.ok(), await dial.text()).toBeTruthy();

        // Real LXST signalling over the link: CALLING -> RINGING ->
        // peer auto-answers -> ESTABLISHED (6).
        await expect
            .poll(
                async () => {
                    const res = await request.get(`${E2E_BACKEND_ORIGIN}/api/v1/telephone/status`);
                    if (!res.ok()) {
                        return null;
                    }
                    const body = await res.json();
                    return body.active_call ? body.active_call.status : null;
                },
                { timeout: 120000, intervals: [1000, 2000, 3000] }
            )
            .toBe(6);

        const hangup = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/telephone/hangup`);
        expect(hangup.ok(), await hangup.text()).toBeTruthy();

        await expect
            .poll(
                async () => {
                    const res = await request.get(`${E2E_BACKEND_ORIGIN}/api/v1/telephone/status`);
                    if (!res.ok()) {
                        return null;
                    }
                    const body = await res.json();
                    return body.active_call === null || body.active_call === undefined;
                },
                { timeout: 30000, intervals: [500, 1000, 2000] }
            )
            .toBe(true);
    });
});

test.describe("Live mesh traffic budget", () => {
    test.setTimeout(120000);
    test.skip(!peerReady(), "live peer subprocess not running");

    test("idle announce traffic stays bounded", async ({ request }) => {
        await prepareE2eSession(request);
        const before = await interfaceBytes(request);
        expect(before, "interface-stats must report byte counters").not.toBeNull();

        // Let the peer's announce loop and any backend churn run; a #125-class
        // announce/path storm would blow through this in seconds.
        await new Promise((r) => setTimeout(r, 20000));

        const after = await interfaceBytes(request);
        const deltaRx = after.rx - before.rx;
        const deltaTx = after.tx - before.tx;
        // Peer announces 3 destinations every ~2s plus keepalives; budget is
        // generous for jitter but orders of magnitude under any storm.
        expect(deltaRx).toBeLessThan(1_000_000);
        expect(deltaTx).toBeLessThan(1_000_000);
    });

    test("full chat flow traffic stays bounded", async ({ request }) => {
        await prepareE2eSession(request);
        const peer = peerReady();
        const before = await interfaceBytes(request);
        expect(before).not.toBeNull();

        // One real RRC round-trip plus an LXMF exchange, then measure. The
        // flows themselves are a few KB; the cap catches unbounded retries.
        const marker = `e2e-budget-${Date.now()}`;
        await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/lxmf-messages/send`, {
            lxmf_message: { destination_hash: peer.lxmf_dest, content: marker },
        });
        await expect
            .poll(() => readJsonl(PEER_INBOX).some((m) => m.content === marker), {
                timeout: 60000,
                intervals: [500, 1000, 2000],
            })
            .toBe(true);
        await new Promise((r) => setTimeout(r, 3000));

        const after = await interfaceBytes(request);
        const delta = after.rx - before.rx + (after.tx - before.tx);
        expect(delta).toBeLessThan(2_000_000);
    });
});

test.describe("Live mesh multi-hub RRC", () => {
    test.setTimeout(300000);
    test.skip(!peerReady(), "live peer subprocess not running");

    test.beforeEach(async ({ request }) => {
        await prepareE2eSession(request);
    });

    async function hubStatus(request, hubHash) {
        const res = await request.get(`${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs`);
        if (!res.ok()) {
            return null;
        }
        const body = await res.json();
        const hub = (body.hubs || []).find((h) => h.hash === hubHash || h.hub_hash === hubHash);
        return hub ? hub.status : null;
    }

    async function connectHub(request, hubHash) {
        const add = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs`, {
            hub_hash: hubHash,
            name: `hub-${hubHash.slice(0, 6)}`,
        });
        expect(add.ok(), await add.text()).toBeTruthy();
        await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/connect`, {});
        await expect
            .poll(() => hubStatus(request, hubHash), { timeout: 120000, intervals: [1000, 2000, 3000] })
            .toBe(2);
    }

    test("connect to all live hubs and echo in each room", async ({ request }) => {
        const peer = peerReady();
        const hubHashes = peer.hub_hashes || [peer.hub_hash];
        expect(hubHashes.length).toBeGreaterThanOrEqual(3);

        for (const hubHash of hubHashes) {
            await connectHub(request, hubHash);
        }

        // Join lobby on every hub and send one message per hub.
        for (const hubHash of hubHashes) {
            const join = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/rooms`, {
                room: "lobby",
            });
            expect(join.ok(), await join.text()).toBeTruthy();
        }

        for (const [i, hubHash] of hubHashes.entries()) {
            const marker = `e2e-multi-${i}-${Date.now()}`;
            const send = await e2ePost(
                request,
                `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/rooms/lobby/messages`,
                { text: marker }
            );
            expect(send.ok(), await send.text()).toBeTruthy();

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
                        const mine = (body.messages || []).filter((r) => r.text === marker);
                        return mine.length ? mine[mine.length - 1].delivery : null;
                    },
                    { timeout: 60000, intervals: [500, 1000, 2000] }
                )
                .toBe("sent");
        }
    });

    test("second room on hub A isolates echo traffic", async ({ request }) => {
        const peer = peerReady();
        const hubHash = peer.hub_hashes?.[0] || peer.hub_hash;
        await connectHub(request, hubHash);

        const join = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/rooms`, {
            room: "test-room",
        });
        expect(join.ok(), await join.text()).toBeTruthy();

        const marker = `e2e-room2-${Date.now()}`;
        await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/rooms/test-room/messages`, {
            text: marker,
        });
        await expect
            .poll(
                async () => {
                    const res = await request.get(
                        `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/rooms/test-room/messages`
                    );
                    if (!res.ok()) {
                        return null;
                    }
                    const body = await res.json();
                    const mine = (body.messages || []).filter((r) => r.text === marker);
                    return mine.length ? mine[mine.length - 1].delivery : null;
                },
                { timeout: 60000, intervals: [500, 1000, 2000] }
            )
            .toBe("sent");

        // The message must not bleed into lobby history.
        const lobby = await request.get(`${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/rooms/lobby/messages`);
        const lobbyBody = await lobby.json();
        expect((lobbyBody.messages || []).some((r) => r.text === marker)).toBe(false);
    });

    test("disconnect and reconnect cycle keeps hub usable", async ({ request }) => {
        const peer = peerReady();
        const hubHash = peer.hub_hashes?.[1] || peer.hub_hash;
        await connectHub(request, hubHash);

        const off = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/disconnect`, {});
        expect(off.ok(), await off.text()).toBeTruthy();
        await expect.poll(() => hubStatus(request, hubHash), { timeout: 30000 }).toBe(0);

        await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/connect`, {});
        await expect
            .poll(() => hubStatus(request, hubHash), { timeout: 120000, intervals: [1000, 2000, 3000] })
            .toBe(2);

        const marker = `e2e-reconnect-${Date.now()}`;
        const send = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/rooms/lobby/messages`, {
            text: marker,
        });
        expect(send.ok(), await send.text()).toBeTruthy();
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
                    const mine = (body.messages || []).filter((r) => r.text === marker);
                    return mine.length ? mine[mine.length - 1].delivery : null;
                },
                { timeout: 60000, intervals: [500, 1000, 2000] }
            )
            .toBe("sent");
    });
});

test.describe("Live mesh restart and fault matrix", () => {
    test.setTimeout(300000);
    test.skip(!peerReady(), "live peer subprocess not running");

    const { execFileSync } = require("child_process");
    const META = path.join(SHARE, "stack_meta.json");
    const CHAOS_MODE = path.join(SHARE, "chaos.mode");
    const RESTART_SH = path.join(__dirname, "../../scripts/e2e/restart-backend.sh");

    function stackMeta() {
        if (!fs.existsSync(META)) {
            return null;
        }
        return JSON.parse(fs.readFileSync(META, "utf8"));
    }

    function setChaos(mode) {
        fs.writeFileSync(CHAOS_MODE, mode);
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

    async function connectHub(request, hubHash) {
        const add = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs`, {
            hub_hash: hubHash,
            name: `hub-${hubHash.slice(0, 6)}`,
        });
        expect(add.ok(), await add.text()).toBeTruthy();
        await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/connect`, {});
        await expect
            .poll(() => hubStatus(request, hubHash), {
                timeout: 120000,
                intervals: [1000, 2000, 3000],
            })
            .toBe(2);
    }

    test("backend restart with warm storage reconnects within SLA", async ({ request }) => {
        const peer = peerReady();
        const meta = stackMeta();
        test.skip(!meta, "stack meta missing - cannot restart backend");
        const hubHash = peer.hub_hashes?.[0] || peer.hub_hash;
        await connectHub(request, hubHash);

        // Warm known_destinations + empty path table is exactly the
        // dead-link stall fixed in 4dd36c06. Restart and time the recovery.
        const t0 = Date.now();
        execFileSync("bash", [RESTART_SH, META], { timeout: 240000, stdio: "inherit" });
        await prepareE2eSession(request);

        // Hub entry persists with auto_reconnect - no manual connect needed.
        await expect
            .poll(() => hubStatus(request, hubHash), {
                timeout: 90000,
                intervals: [500, 1000, 2000],
            })
            .toBe(2);
        const elapsed = Date.now() - t0;
        // A dead-link stall used to burn the whole establishment timeout
        // (~2-3 min). Assert the healthy bound instead.
        expect(elapsed).toBeLessThan(90000);
    });

    test("link flap during connected session recovers", async ({ request }) => {
        const peer = peerReady();
        const hubHash = peer.hub_hashes?.[0] || peer.hub_hash;
        await connectHub(request, hubHash);

        // Drop every proxied connection - equivalent to the interface dying.
        setChaos("drop");
        await new Promise((r) => setTimeout(r, 3000));
        setChaos("pass");

        await expect
            .poll(() => hubStatus(request, hubHash), {
                timeout: 120000,
                intervals: [1000, 2000, 3000],
            })
            .toBe(2);

        const marker = `e2e-flap-${Date.now()}`;
        await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/rooms`, {
            room: "lobby",
        });
        const send = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/rooms/lobby/messages`, {
            text: marker,
        });
        expect(send.ok(), await send.text()).toBeTruthy();
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
                    const mine = (body.messages || []).filter((r) => r.text === marker);
                    return mine.length ? mine[mine.length - 1].delivery : null;
                },
                { timeout: 60000, intervals: [500, 1000, 2000] }
            )
            .toBe("sent");
    });

    test("network partition during connect cannot stall forever", async ({ request }) => {
        const peer = peerReady();
        const hubHash = peer.hub_hashes?.[2] || peer.hub_hash;
        // Blackhole the link, then start a connect: bounded window + fail.
        setChaos("partition");
        await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs`, {
            hub_hash: hubHash,
            name: "partition-hub",
        });
        await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/connect`, {});
        // A bounded attempt must surface as failed, not hang CONNECTING.
        await expect
            .poll(() => hubStatus(request, hubHash), {
                timeout: 120000,
                intervals: [1000, 2000, 3000],
            })
            .toBe(0);
        setChaos("pass");
        await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/connect`, {});
        await expect
            .poll(() => hubStatus(request, hubHash), {
                timeout: 120000,
                intervals: [1000, 2000, 3000],
            })
            .toBe(2);
    });
});

test.describe("Live mesh adversarial announce storm", () => {
    test.setTimeout(240000);
    test.skip(!peerReady(), "live peer subprocess not running");

    const PEER_MODE = path.join(SHARE, "peer.mode");

    test("announce storm keeps backend responsive and traffic bounded", async ({ request }) => {
        const peer = peerReady();
        const hubHash = peer.hub_hashes?.[0] || peer.hub_hash;

        // Establish a connected hub first.
        const add = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs`, {
            hub_hash: hubHash,
            name: "storm-hub",
        });
        expect(add.ok(), await add.text()).toBeTruthy();
        await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/connect`, {});
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
                { timeout: 120000, intervals: [1000, 2000, 3000] }
            )
            .toBe(2);

        const t0 = Date.now();
        const b0 = await interfaceBytes(request);

        // 40 synthetic hub announces on every peer tick for 25s. Mirrors the
        // churn profile that produced the unbounded traffic incident.
        fs.writeFileSync(PEER_MODE, "40");
        await new Promise((r) => setTimeout(r, 25000));
        fs.writeFileSync(PEER_MODE, "0");

        // Backend must stay responsive under the storm.
        const status = await request.get(`${E2E_BACKEND_ORIGIN}/api/v1/status`);
        expect(status.ok()).toBeTruthy();
        const hubs = await request.get(`${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs`);
        expect(hubs.ok()).toBeTruthy();

        // Traffic bounded: storm announces are small; runaway re-announces or
        // path storms would blow past 4MB in 25s.
        const b1 = await interfaceBytes(request);
        const total = b1.rx - b0.rx + (b1.tx - b0.tx);
        console.log(`storm window: ${((Date.now() - t0) / 1000).toFixed(0)}s traffic=${total} bytes`);
        expect(total).toBeLessThan(4 * 1024 * 1024);

        // Path table must not grow unboundedly: at most the 40 storm
        // destinations plus a margin.
        const pt = await request.get(`${E2E_BACKEND_ORIGIN}/api/v1/path-table`);
        if (pt.ok()) {
            const body = await pt.json();
            const size = (body.path_table || body || []).length;
            expect(size).toBeLessThan(80);
        }
    });
});

const SHARE2 = process.env.E2E_PEER2_SHARE || "/tmp/meshchatx-e2e-peer2-share";

function peer2Ready() {
    const p = path.join(SHARE2, "peer_ready.json");
    return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, "utf8")) : null;
}

test.describe("Live mesh two-peer isolation", () => {
    test.setTimeout(300000);
    test.skip(!peerReady() || !peer2Ready(), "second live peer not running");

    test("LXMF delivered to the correct peer only", async ({ request }) => {
        const p1 = peerReady();
        const p2 = peer2Ready();
        const m1 = `e2e-p1-${Date.now()}`;
        const m2 = `e2e-p2-${Date.now()}`;

        for (const [dest, marker] of [
            [p1.lxmf_dest, m1],
            [p2.lxmf_dest, m2],
        ]) {
            const res = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/lxmf-messages/send`, {
                lxmf_message: { destination_hash: dest, content: marker },
            });
            expect(res.ok(), await res.text()).toBeTruthy();
        }

        // Wait for each peer inbox file to contain its own marker.
        const inboxes = [
            [path.join(SHARE, "peer_inbox.jsonl"), m1],
            [path.join(SHARE2, "peer_inbox.jsonl"), m2],
        ];
        for (const [file, marker] of inboxes) {
            await expect
                .poll(
                    () => {
                        const lines = fs.existsSync(file) ? fs.readFileSync(file, "utf8") : "";
                        return lines.includes(marker);
                    },
                    { timeout: 120000, intervals: [1000, 2000, 3000] }
                )
                .toBe(true);
        }

        // Cross-isolation: each inbox must NOT contain the other marker.
        const i1 = fs.readFileSync(path.join(SHARE, "peer_inbox.jsonl"), "utf8");
        const i2 = fs.readFileSync(path.join(SHARE2, "peer_inbox.jsonl"), "utf8");
        expect(i1.includes(m2)).toBeFalsy();
        expect(i2.includes(m1)).toBeFalsy();
    });

    test("hubs on both peers connect and route independently", async ({ request }) => {
        const p1 = peerReady();
        const p2 = peer2Ready();
        const h1 = p1.hub_hashes?.[0] || p1.hub_hash;
        const h2 = p2.hub_hashes?.[0] || p2.hub_hash;
        expect(h1).not.toBe(h2);

        for (const h of [h1, h2]) {
            const add = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs`, {
                hub_hash: h,
                name: `multi-${h.slice(0, 6)}`,
            });
            expect(add.ok(), await add.text()).toBeTruthy();
            await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${h}/connect`, {});
            await expect
                .poll(
                    async () => {
                        const res = await request.get(`${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs`);
                        if (!res.ok()) {
                            return null;
                        }
                        const body = await res.json();
                        const hub = (body.hubs || []).find((x) => x.hash === h || x.hub_hash === h);
                        return hub ? hub.status : null;
                    },
                    { timeout: 120000, intervals: [1000, 2000, 3000] }
                )
                .toBe(2);
            await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${h}/rooms`, { room: "lobby" });
        }

        // Send a distinct marker to each hub and confirm each echo lands in
        // the right room history only.
        const markers = [
            [h1, `e2e-mh1-${Date.now()}`],
            [h2, `e2e-mh2-${Date.now()}`],
        ];
        for (const [h, marker] of markers) {
            const send = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${h}/rooms/lobby/messages`, {
                text: marker,
            });
            expect(send.ok(), await send.text()).toBeTruthy();
            await expect
                .poll(
                    async () => {
                        const res = await request.get(
                            `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${h}/rooms/lobby/messages`
                        );
                        if (!res.ok()) {
                            return null;
                        }
                        const body = await res.json();
                        const mine = (body.messages || []).filter((r) => r.text === marker);
                        return mine.length ? mine[mine.length - 1].delivery : null;
                    },
                    { timeout: 60000, intervals: [500, 1000, 2000] }
                )
                .toBe("sent");
        }
        // Room isolation across peers: h1 history must not contain h2 marker.
        const h1msgs = await (
            await request.get(`${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${h1}/rooms/lobby/messages`)
        ).json();
        expect((h1msgs.messages || []).some((r) => r.text === markers[1][1])).toBeFalsy();
    });
});

test.describe("Live mesh RRC history and pagination", () => {
    test.setTimeout(420000);
    test.skip(!peerReady(), "live peer subprocess not running");

    test("room history survives backend restart and pages backwards", async ({ request }) => {
        const peer = peerReady();
        const hubHash = peer.hub_hashes?.[0] || peer.hub_hash;
        const marker = `hist-${Date.now()}`;

        const add = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs`, {
            hub_hash: hubHash,
            name: "hist-hub",
        });
        expect(add.ok(), await add.text()).toBeTruthy();
        await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/connect`, {});
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
                { timeout: 120000, intervals: [1000, 2000] }
            )
            .toBe(2);
        await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/rooms`, { room: "lobby" });

        // One uniquely marked message; after restart it must come back from
        // disk history, not from the live link.
        const send = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/rooms/lobby/messages`, {
            text: `${marker}-old`,
        });
        expect(send.ok(), await send.text()).toBeTruthy();
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
                    return (body.messages || []).some((m) => m.text === `${marker}-old` && m.delivery === "sent");
                },
                { timeout: 60000, intervals: [500, 1000] }
            )
            .toBe(true);

        // Warm-restart the backend: same storage, empty in-memory state.
        const { execFileSync } = require("child_process");
        const RESTART_SH = path.join(__dirname, "../../scripts/e2e/restart-backend.sh");
        const META = path.join(SHARE, "stack_meta.json");
        execFileSync("bash", [RESTART_SH, META], {
            timeout: 240000,
            stdio: "inherit",
        });
        await prepareE2eSession(request);

        // The stored message must reload from history files.
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
                    return (body.messages || []).some((m) => m.text === `${marker}-old`);
                },
                { timeout: 120000, intervals: [1000, 2000] }
            )
            .toBe(true);

        // before_seq pagination: the first page's oldest seq must page the
        // next batch, and a second fetch with that seq must not repeat it.
        const res = await request.get(`${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/rooms/lobby/messages`);
        const body = await res.json();
        const seqs = (body.messages || []).map((m) => m.seq).filter((s) => typeof s === "number");
        expect(seqs.length).toBeGreaterThan(0);
        const oldest = Math.min(...seqs);
        const older = await request.get(
            `${E2E_BACKEND_ORIGIN}/api/v1/rrc/hubs/${hubHash}/rooms/lobby/messages?before_seq=${oldest}`
        );
        if (older.ok()) {
            const obody = await older.json();
            const oseqs = (obody.messages || []).map((m) => m.seq);
            for (const s of oseqs) {
                expect(s).toBeLessThan(oldest);
            }
        }
    });
});
