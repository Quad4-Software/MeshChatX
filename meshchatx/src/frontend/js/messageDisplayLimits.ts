// SPDX-License-Identifier: 0BSD

/**
 * Inline message body and raw modal use this limit so huge LXMF bodies
 * do not lock the UI (markdown and DOM cost). Copy still sends full text.
 */
export const MESSAGE_BODY_MAX_DISPLAY_CHARS = 32000;

export function isStringTooLargeForInlineDisplay(content: unknown): boolean {
    return typeof content === "string" && content.length > MESSAGE_BODY_MAX_DISPLAY_CHARS;
}
