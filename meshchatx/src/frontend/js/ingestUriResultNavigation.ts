// SPDX-License-Identifier: 0BSD

/**
 * @param {Record<string, unknown>} json
 * @param {{ push: (location: object) => Promise<unknown> }} router
 * @param {{ info?: (msg: string) => void, error?: (msg: string) => void } | null} [toast]
 * @returns {Promise<boolean>} true when navigation was handled
 */
export async function handleLxmIngestUriResult(json, { router, toast = null }) {
    if (json.ingest_type === "map_view" && json.map_query) {
        const mq = json.map_query;
        const query: any = {
            lat: String(mq.lat),
            lon: String(mq.lon),
            zoom: String(mq.zoom),
        };
        if (mq.layers) {
            query.layers = mq.layers;
        }
        if (mq.label) {
            query.label = mq.label;
        }
        await router.push({ name: "map", query });
        if (json.status === "error") {
            toast?.error?.(json.message);
        } else if (json.message) {
            toast?.info?.(json.message);
        }
        return true;
    }

    if (json.ingest_type === "docs_view") {
        const dq = json.docs_query;
        const rel = dq && typeof dq.reticulum === "string" ? dq.reticulum.trim() : "";
        if (rel) {
            await router.push({
                name: "documentation",
                query: { reticulum: encodeURIComponent(rel) },
            });
        } else {
            await router.push({ name: "documentation" });
        }
        if (json.status === "error") {
            toast?.error?.(json.message);
        } else if (json.message) {
            toast?.info?.(json.message);
        }
        return true;
    }

    return false;
}
