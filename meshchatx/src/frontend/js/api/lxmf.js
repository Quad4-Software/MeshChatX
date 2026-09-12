// @ts-check

/**
 * Endpoint wrappers for /api/v1/lxmf.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function deleteFolders(id, ...rest) {
    return window.api.delete(apiPath(`/lxmf/folders/${id}`), ...rest);
}
export function listConversationPins(...rest) {
    return window.api.get(apiPath("/lxmf/conversation-pins"), ...rest);
}
export function listConversations(...rest) {
    return window.api.get(apiPath("/lxmf/conversations"), ...rest);
}
export function listFolders(...rest) {
    return window.api.get(apiPath("/lxmf/folders"), ...rest);
}
export function getFoldersExport(...rest) {
    return window.api.get(apiPath("/lxmf/folders/export"), ...rest);
}
export function getMessageBlocklist(...rest) {
    return window.api.get(apiPath("/lxmf/message-blocklist"), ...rest);
}
export function getMessageBlocklistExport(...rest) {
    return window.api.get(apiPath("/lxmf/message-blocklist/export"), ...rest);
}
export function getPropagationNodeStatus(...rest) {
    return window.api.get(apiPath("/lxmf/propagation-node/status"), ...rest);
}
export function listPropagationNodes(...rest) {
    return window.api.get(apiPath("/lxmf/propagation-nodes"), ...rest);
}
export function listSieveFilters(...rest) {
    return window.api.get(apiPath("/lxmf/sieve-filters"), ...rest);
}
export function updateFolders(id, data, ...rest) {
    return window.api.patch(apiPath(`/lxmf/folders/${id}`), data, ...rest);
}
export function toggleConversationPins(data, ...rest) {
    return window.api.post(apiPath("/lxmf/conversation-pins/toggle"), data, ...rest);
}
export function markAsReadConversations(destinationHash, data, ...rest) {
    return window.api.post(apiPath(`/lxmf/conversations/${destinationHash}/mark-as-read`), data, ...rest);
}
export function markAsReadConversations2(normalized, data, ...rest) {
    return window.api.post(apiPath(`/lxmf/conversations/${normalized}/mark-as-read`), data, ...rest);
}
export function bulkDeleteConversations(data, ...rest) {
    return window.api.post(apiPath("/lxmf/conversations/bulk-delete"), data, ...rest);
}
export function bulkMarkAsReadConversations(data, ...rest) {
    return window.api.post(apiPath("/lxmf/conversations/bulk-mark-as-read"), data, ...rest);
}
export function moveToFolderConversations(data, ...rest) {
    return window.api.post(apiPath("/lxmf/conversations/move-to-folder"), data, ...rest);
}
export function createFolders(data, ...rest) {
    return window.api.post(apiPath("/lxmf/folders"), data, ...rest);
}
export function importFolders(data, ...rest) {
    return window.api.post(apiPath("/lxmf/folders/import"), data, ...rest);
}
export function importMessageBlocklist(data, ...rest) {
    return window.api.post(apiPath("/lxmf/message-blocklist/import"), data, ...rest);
}
export function cancelInboundPropagationNode(data, ...rest) {
    return window.api.post(apiPath("/lxmf/propagation-node/cancel-inbound"), data, ...rest);
}
export function restartPropagationNode(data, ...rest) {
    return window.api.post(apiPath("/lxmf/propagation-node/restart"), data, ...rest);
}
export function stopPropagationNode(data, ...rest) {
    return window.api.post(apiPath("/lxmf/propagation-node/stop"), data, ...rest);
}
export function stopSyncPropagationNode(data, ...rest) {
    return window.api.post(apiPath("/lxmf/propagation-node/stop-sync"), data, ...rest);
}
export function syncPropagationNode(data, ...rest) {
    return window.api.post(apiPath("/lxmf/propagation-node/sync"), data, ...rest);
}
export function updateMessageBlocklist(data, ...rest) {
    return window.api.put(apiPath("/lxmf/message-blocklist"), data, ...rest);
}
export function updateSieveFilters(data, ...rest) {
    return window.api.put(apiPath("/lxmf/sieve-filters"), data, ...rest);
}
