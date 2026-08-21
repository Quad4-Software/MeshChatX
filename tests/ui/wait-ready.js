const { E2E_BACKEND_ORIGIN } = require("../e2e/helpers");

/**
 * Wait until /api/v1/status reports status ok (HTTP can bind earlier).
 * @param {import('@playwright/test').APIRequestContext} request
 * @param {string} [origin]
 * @param {{ timeoutMs?: number }} [opts]
 */
async function waitForBackendReady(request, origin = E2E_BACKEND_ORIGIN, opts = {}) {
    const timeoutMs = opts.timeoutMs ?? 240000;
    const started = Date.now();
    let last = "";
    while (Date.now() - started < timeoutMs) {
        try {
            const res = await request.get(`${origin}/api/v1/status`);
            if (res.ok()) {
                const body = await res.json();
                last = JSON.stringify(body);
                if (body.status === "ok") {
                    return body;
                }
            } else {
                last = `HTTP ${res.status()}`;
            }
        } catch (err) {
            last = String(err && err.message ? err.message : err);
        }
        await new Promise((r) => setTimeout(r, 1000));
    }
    throw new Error(`backend not ready within ${timeoutMs}ms (${origin}): ${last}`);
}

module.exports = {
    waitForBackendReady,
};
