// SPDX-License-Identifier: 0BSD

import "emoji-picker-element";
import emojiPickerEnDataUrl from "emoji-picker-element-data/en/emojibase/data.json?url";
import GlobalState from "../../../js/GlobalState.js";

export const EMOJI_PICKER_DATA_URL: string = emojiPickerEnDataUrl;

export function emojiPickerThemeClass(): string {
    void GlobalState.config?.theme;
    return GlobalState.config?.theme === "dark" ? "dark" : "light";
}

export function unicodeFromEmojiClickEvent(event: Event): string {
    const detail = (event as CustomEvent).detail as
        { unicode?: string; emoji?: { unicode?: string } } | string | undefined;
    if (!detail) {
        return "";
    }
    if (typeof detail === "string") {
        return detail;
    }
    return detail.unicode || detail.emoji?.unicode || "";
}
