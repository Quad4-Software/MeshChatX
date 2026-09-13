// SPDX-License-Identifier: 0BSD

export type IngestUriToast = {
    info?: (msg: unknown) => void;
    error?: (msg: unknown) => void;
};

export type IngestUriRouter = {
    push: (location: { name?: string; query?: Record<string, unknown> } | string) => Promise<unknown> | unknown;
};

/** Returns true when navigation was handled. */
export async function handleLxmIngestUriResult(
    json: Record<string, unknown>,
    {
        router,
        toast = null,
    }: {
        router: IngestUriRouter;
        toast?: IngestUriToast | null;
    }
): Promise<boolean> {
    if (json.ingest_type === "map_view" && json.map_query) {
        const mq = json.map_query as Record<string, unknown>;
        const query: Record<string, string> = {
            lat: String(mq.lat),
            lon: String(mq.lon),
            zoom: String(mq.zoom),
        };
        if (mq.layers) {
            query.layers = String(mq.layers);
        }
        if (mq.label) {
            query.label = String(mq.label);
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
        const dq = json.docs_query as Record<string, unknown> | null | undefined;
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
