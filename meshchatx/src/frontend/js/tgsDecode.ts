/**
 * Decompress a .tgs payload (gzip) or parse raw JSON. Used by sticker TGS playback.
 */

export async function decodeTgsBuffer(buf: ArrayBuffer): Promise<Record<string, unknown>> {
    const view = new Uint8Array(buf);
    if (view.length >= 2 && view[0] === 0x1f && view[1] === 0x8b) {
        if (typeof DecompressionStream !== "undefined") {
            const ds = new DecompressionStream("gzip");
            const stream = new Blob([buf]).stream().pipeThrough(ds);
            const out = await new Response(stream).text();
            return JSON.parse(out) as Record<string, unknown>;
        }
        throw new Error("DecompressionStream not available");
    }
    const text = new TextDecoder().decode(view);
    return JSON.parse(text) as Record<string, unknown>;
}
