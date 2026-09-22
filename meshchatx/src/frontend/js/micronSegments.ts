/**
 * Pure Micron markup segment splitting, shared by the main-thread parser
 * (MicronParser) and the render worker. No DOM access allowed in here.
 */

// eslint-disable-next-line security/detect-unsafe-regex -- fixed pattern, bounded input (single line)
export const MICRON_PARTIAL_LINE_REGEX =
    /^`\{([a-f0-9]{32}):([^`}]*)(?:`(\d+)(?:`([^}]*))?)?\}$/;

export type MicronSegment =
    | { type: "mu"; text: string }
    | { type: "partial"; line: string };

/**
 * Split markup into contiguous micron segments and standalone partial-include
 * lines. Partial lines must render through the DOM-based JS parser; mu
 * segments are pure string-to-string and can run off the main thread.
 */
export function splitMicronWasmSegments(markup): MicronSegment[] {
    if (markup == null) {
        return [];
    }
    const lines = String(markup).split("\n");
    const segments: MicronSegment[] = [];
    let buf: string[] = [];
    for (const line of lines) {
        const trimmed = line.trim();
        if (MICRON_PARTIAL_LINE_REGEX.test(trimmed)) {
            if (buf.length) {
                segments.push({ type: "mu", text: buf.join("\n") });
                buf = [];
            }
            segments.push({ type: "partial", line });
        } else {
            buf.push(line);
        }
    }
    if (buf.length) {
        segments.push({ type: "mu", text: buf.join("\n") });
    }
    return segments;
}
