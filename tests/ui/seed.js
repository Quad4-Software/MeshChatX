const {
    E2E_BACKEND_ORIGIN,
    E2E_SCROLL_PEER_HASH,
    E2E_SCROLL_ALT_PEER_HASH,
    buildE2eLxmfRow,
    e2ePost,
    prepareE2eSession,
    seedE2eLongConversationThread,
    seedE2eAltShortConversationThread,
    getE2eLocalLxmfHash,
} = require("../e2e/helpers");
const { waitForBackendReady } = require("./wait-ready");

function padHash(prefix, index, width = 32) {
    const body = `${prefix}${String(index).padStart(4, "0")}`;
    return body.padEnd(width, "0").slice(0, width);
}

/**
 * Seed contacts, favourites, and LXMF threads so list pages have simulated load.
 * @param {import('@playwright/test').APIRequestContext} request
 * @param {{ contactCount?: number, favouriteCount?: number, messageCount?: number }} [opts]
 */
async function seedUiSimulatedData(request, opts = {}) {
    await waitForBackendReady(request);
    await prepareE2eSession(request);

    const contactCount = opts.contactCount ?? 40;
    const favouriteCount = opts.favouriteCount ?? 25;
    const messageCount = opts.messageCount ?? 45;

    await seedE2eLongConversationThread(request, { messageCount });
    await seedE2eAltShortConversationThread(request, { messageCount: 12 });

    const contacts = [];
    for (let i = 0; i < contactCount; i++) {
        const hash = padHash("c0", i);
        contacts.push({
            name: `Sim Contact ${i}`,
            remote_identity_hash: hash,
            lxmf_address: hash,
        });
    }
    const contactsRes = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/telephone/contacts/import`, { contacts });
    if (!contactsRes.ok()) {
        throw new Error(`contacts import failed: ${contactsRes.status()}`);
    }

    const favourites = [];
    for (let i = 0; i < favouriteCount; i++) {
        favourites.push({
            destination_hash: padHash("n0", i),
            display_name: `Sim Nomad ${i}`,
            aspect: "nomadnetwork.node",
        });
    }
    const favRes = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/favourites/import`, {
        favourites,
    });
    if (!favRes.ok()) {
        throw new Error(`favourites import failed: ${favRes.status()}`);
    }

    return {
        contactCount,
        favouriteCount,
        messageCount,
    };
}

const DEMO_PEERS = [
    {
        hash: E2E_SCROLL_PEER_HASH,
        name: "Ada Lovelace",
        icon: { icon_name: "account", fg_color: "#ffffff", bg_color: "#0e7490" },
    },
    {
        hash: E2E_SCROLL_ALT_PEER_HASH,
        name: "Rover Relay",
        icon: { icon_name: "antenna", fg_color: "#ffffff", bg_color: "#7c3aed" },
    },
    {
        hash: padHash("de", 1),
        name: "MeshBot",
        icon: { icon_name: "robot", fg_color: "#111111", bg_color: "#fbbf24" },
    },
];

const DEMO_THREAD_LINES = [
    "Hey, are you seeing the new relay announce?",
    "Yes, latency over LoRa is better than expected.",
    "I pushed the antenna up another meter. RSSI improved a lot.",
    "Nice. Can you still reach the ridge node?",
    "Barely. I get about one announce every few minutes.",
    "Send me a voice note when you are back in range.",
    "Will do. Also try the offline map pack tonight.",
    "Already cached. The map holds up without any uplink.",
];

/**
 * Seed a small, realistic demo dataset for screenshots: named peers with icon
 * metadata and a short natural conversation.
 * @param {import('@playwright/test').APIRequestContext} request
 */
async function seedUiDemoData(request) {
    await waitForBackendReady(request);
    await prepareE2eSession(request);
    const localHash = await getE2eLocalLxmfHash(request);

    const contacts = DEMO_PEERS.map((peer) => ({
        name: peer.name,
        remote_identity_hash: peer.hash,
        lxmf_address: peer.hash,
        lxmf_icon: {
            icon_name: peer.icon.icon_name,
            foreground_colour: peer.icon.fg_color,
            background_colour: peer.icon.bg_color,
        },
    }));
    const contactsRes = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/telephone/contacts/import`, {
        contacts,
    });
    if (!contactsRes.ok()) {
        throw new Error(`demo contacts import failed: ${contactsRes.status()}`);
    }

    const messages = DEMO_THREAD_LINES.map((content, i) => {
        const row = buildE2eLxmfRow({
            peerHash: DEMO_PEERS[0].hash,
            localHash,
            index: i,
            total: DEMO_THREAD_LINES.length,
            inbound: i % 2 === 0,
        });
        row.content = content;
        return row;
    });
    const sideThreads = [
        [DEMO_PEERS[1], ["Telemetry uplink stable overnight.", "Copy. Rebroadcasting your announces."]],
        [DEMO_PEERS[2], ["status", "Uptime 41 days. Heap at 62 percent."]],
    ];
    for (const [peer, lines] of sideThreads) {
        lines.forEach((content, i) => {
            const row = buildE2eLxmfRow({
                peerHash: peer.hash,
                localHash,
                index: i,
                total: lines.length,
                inbound: i % 2 === 0,
            });
            row.content = content;
            row.timestamp += 3600;
            messages.push(row);
        });
    }
    const imp = await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/maintenance/messages/import`, {
        messages,
    });
    if (!imp.ok()) {
        throw new Error(`demo messages import failed: ${imp.status()}`);
    }

    for (const peer of DEMO_PEERS) {
        await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/destination/${peer.hash}/custom-display-name/update`, {
            display_name: peer.name,
        });
    }

    const favourites = [];
    for (let i = 0; i < 6; i++) {
        favourites.push({
            destination_hash: padHash("n0", i),
            display_name: `Ridge Node ${i}`,
            aspect: "nomadnetwork.node",
        });
    }
    await e2ePost(request, `${E2E_BACKEND_ORIGIN}/api/v1/favourites/import`, { favourites });

    return { demoPeerHash: DEMO_PEERS[0].hash, localHash };
}

module.exports = {
    DEMO_PEERS,
    seedUiSimulatedData,
    seedUiDemoData,
    padHash,
};
