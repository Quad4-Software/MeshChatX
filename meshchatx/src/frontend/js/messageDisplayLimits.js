/**
 * Inline message body and raw modal use this limit so huge LXMF bodies
 * do not lock the UI (markdown/DOM cost). Copy still sends full text.
 */
export const MESSAGE_BODY_MAX_DISPLAY_CHARS = 32000;

/**
 * @param {unknown} content
 * @returns {boolean}
 */
export function isStringTooLargeForInlineDisplay(content) {
    return typeof content === "string" && content.length > MESSAGE_BODY_MAX_DISPLAY_CHARS;
}
