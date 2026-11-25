// @ts-check

/**
 * Endpoint wrappers for /api/v1/rrc.
 * Each function maps one HTTP call through window.api. Add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants";

export function getHubsRoomsMessages(hubHash, encodeRoomroom, ...rest) {
    return window.api.get(apiPath(`/rrc/hubs/${hubHash}/rooms/${encodeRoomroom}/messages`), ...rest);
}
export function getSearch(...rest) {
    return window.api.get(apiPath("/rrc/search"), ...rest);
}
export function getServersMembers(id, ...rest) {
    return window.api.get(apiPath(`/rrc/servers/${id}/members`), ...rest);
}
export function getServersMessages(id, ...rest) {
    return window.api.get(apiPath(`/rrc/servers/${id}/messages`), ...rest);
}
