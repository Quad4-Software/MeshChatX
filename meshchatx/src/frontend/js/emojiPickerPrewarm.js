// SPDX-License-Identifier: 0BSD

// Prewarm emoji-picker-element's IndexedDB cache so the picker opens
// instantly instead of fetching ~1MB of emoji JSON on first open.
import emojiPickerEnDataUrl from "emoji-picker-element-data/en/emojibase/data.json?url";

let started = false;

export function prewarmEmojiPicker() {
    if (started) {
        return;
    }
    started = true;
    const kick = async () => {
        try {
            const { Database } = await import("emoji-picker-element");
            const db = new Database({ dataSource: emojiPickerEnDataUrl });
            await db.ready();
        } catch {
            // Prewarm is best-effort. the picker lazily loads on open anyway.
        }
    };
    if (typeof requestIdleCallback === "function") {
        requestIdleCallback(kick, { timeout: 3000 });
    } else {
        setTimeout(kick, 0);
    }
}
