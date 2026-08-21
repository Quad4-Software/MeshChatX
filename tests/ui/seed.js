const {
    E2E_BACKEND_ORIGIN,
    e2ePost,
    prepareE2eSession,
    seedE2eLongConversationThread,
    seedE2eAltShortConversationThread,
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

module.exports = {
    seedUiSimulatedData,
    padHash,
};
