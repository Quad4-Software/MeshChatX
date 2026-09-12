// @ts-check

/**
 * Endpoint wrappers for /api/v1/lxmf-messages.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function remove(hash, ...rest) {
    return window.api.delete(apiPath(`/lxmf-messages/${hash}`), ...rest);
}
export function deleteConversation(destinationHash, ...rest) {
    return window.api.delete(apiPath(`/lxmf-messages/conversation/${destinationHash}`), ...rest);
}
export function getUri(hash, ...rest) {
    return window.api.get(apiPath(`/lxmf-messages/${hash}/uri`), ...rest);
}
export function getUri2(messageHash, ...rest) {
    return window.api.get(apiPath(`/lxmf-messages/${messageHash}/uri`), ...rest);
}
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
export function getConversationX(destinationHash, ...rest) {
    return window.api.get(apiPath(`/lxmf-messages/conversation/${destinationHash}?count=20&order=desc`), ...rest);
}
export function getConversation2(destinationHash, ...rest) {
    return window.api.get(apiPath(`/lxmf-messages/conversation/${destinationHash}`), ...rest);
}
export function cancelLxmfMessages(lxmfMessageHash, data, ...rest) {
    return window.api.post(apiPath(`/lxmf-messages/${lxmfMessageHash}/cancel`), data, ...rest);
}
export function cancelLxmfMessages2(messageHash, data, ...rest) {
    return window.api.post(apiPath(`/lxmf-messages/${messageHash}/cancel`), data, ...rest);
}
export function createReactions(data, ...rest) {
    return window.api.post(apiPath("/lxmf-messages/reactions"), data, ...rest);
}
export function sendLxmfMessages(data, ...rest) {
    return window.api.post(apiPath("/lxmf-messages/send"), data, ...rest);
}
