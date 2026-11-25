// @ts-check

/**
 * Endpoint wrappers for /api/v1/lxmf-messages.
 * Each function maps one HTTP call through window.api. Add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants";

export function getAttachmentAudio(hash, ...rest) {
    return window.api.get(apiPath(`/lxmf-messages/attachment/${hash}/audio`), ...rest);
}
export function getAttachmentFile(hash, ...rest) {
    return window.api.get(apiPath(`/lxmf-messages/attachment/${hash}/file`), ...rest);
}
export function getAttachmentImage(hash, ...rest) {
    return window.api.get(apiPath(`/lxmf-messages/attachment/${hash}/image`), ...rest);
}
export function getConversation(peerHash, ...rest) {
    return window.api.get(apiPath(`/lxmf-messages/conversation/${peerHash}`), ...rest);
}
