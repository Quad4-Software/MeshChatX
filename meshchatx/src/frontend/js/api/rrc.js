// @ts-check

/**
 * Endpoint wrappers for /api/v1/rrc.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function deleteHubs(hubHash, ...rest) {
    return window.api.delete(apiPath(`/rrc/hubs/${hubHash}`), ...rest);
}
export function deleteHubsRooms(hubHash, encodeRoomroom, ...rest) {
    return window.api.delete(apiPath(`/rrc/hubs/${hubHash}/rooms/${encodeRoomroom}`), ...rest);
}
export function deleteHubsRoomsKey(hubHash, encodeRoomroomName, ...rest) {
    return window.api.delete(apiPath(`/rrc/hubs/${hubHash}/rooms/${encodeRoomroomName}/key`), ...rest);
}
export function deleteHubsRooms2(selectedHubHash, encodeRoomroom, ...rest) {
    return window.api.delete(apiPath(`/rrc/hubs/${selectedHubHash}/rooms/${encodeRoomroom}`), ...rest);
}
export function deleteHubsRoomsMessages(selectedHubHash, selectedRoom, ...rest) {
    return window.api.delete(apiPath(`/rrc/hubs/${selectedHubHash}/rooms/${selectedRoom}/messages`), ...rest);
}
export function deleteServers(id, ...rest) {
    return window.api.delete(apiPath(`/rrc/servers/${id}`), ...rest);
}
export function deleteServersRooms(id, encodeRoomroom, ...rest) {
    return window.api.delete(apiPath(`/rrc/servers/${id}/rooms/${encodeRoomroom}`), ...rest);
}
export function deleteServersRooms2(id, room, ...rest) {
    return window.api.delete(apiPath(`/rrc/servers/${id}/rooms/${room}`), ...rest);
}
export function listHubs(...rest) {
    return window.api.get(apiPath("/rrc/hubs"), ...rest);
}
export function getHubsRoomsMessages(hubHash, encodeRoomroom, ...rest) {
    return window.api.get(apiPath(`/rrc/hubs/${hubHash}/rooms/${encodeRoomroom}/messages`), ...rest);
}
export function getHubsRoomsMessages2(selectedHubHash, selectedRoom, ...rest) {
    return window.api.get(apiPath(`/rrc/hubs/${selectedHubHash}/rooms/${selectedRoom}/messages`), ...rest);
}
export function getSearch(...rest) {
    return window.api.get(apiPath("/rrc/search"), ...rest);
}
export function listServers(...rest) {
    return window.api.get(apiPath("/rrc/servers"), ...rest);
}
export function getServersActivity(id, ...rest) {
    return window.api.get(apiPath(`/rrc/servers/${id}/activity`), ...rest);
}
export function getServersMembers(id, ...rest) {
    return window.api.get(apiPath(`/rrc/servers/${id}/members`), ...rest);
}
export function getServersMessages(id, ...rest) {
    return window.api.get(apiPath(`/rrc/servers/${id}/messages`), ...rest);
}
export function getServersStats(id, ...rest) {
    return window.api.get(apiPath(`/rrc/servers/${id}/stats`), ...rest);
}
export function updateHubs(settingsHubHash, data, ...rest) {
    return window.api.patch(apiPath(`/rrc/hubs/${settingsHubHash}`), data, ...rest);
}
export function updateServers(hostHubSettingsId, data, ...rest) {
    return window.api.patch(apiPath(`/rrc/servers/${hostHubSettingsId}`), data, ...rest);
}
export function postActiveClear(data, ...rest) {
    return window.api.post(apiPath("/rrc/active/clear"), data, ...rest);
}
export function createHubs(data, ...rest) {
    return window.api.post(apiPath("/rrc/hubs"), data, ...rest);
}
export function connectHubs(hubHash, data, ...rest) {
    return window.api.post(apiPath(`/rrc/hubs/${hubHash}/connect`), data, ...rest);
}
export function disconnectHubs(hubHash, data, ...rest) {
    return window.api.post(apiPath(`/rrc/hubs/${hubHash}/disconnect`), data, ...rest);
}
export function createHubsRooms(hubHash, data, ...rest) {
    return window.api.post(apiPath(`/rrc/hubs/${hubHash}/rooms`), data, ...rest);
}
export function postHubsRoomsList(hubHash, data, ...rest) {
    return window.api.post(apiPath(`/rrc/hubs/${hubHash}/rooms/list`), data, ...rest);
}
export function postHubsRoomsRead(hubHash, encodeRoomroom, data, ...rest) {
    return window.api.post(apiPath(`/rrc/hubs/${hubHash}/rooms/${encodeRoomroom}/read`), data, ...rest);
}
export function postHubsCommand(selectedHubHash, data, ...rest) {
    return window.api.post(apiPath(`/rrc/hubs/${selectedHubHash}/command`), data, ...rest);
}
export function createHubsRoomsMessages(selectedHubHash, selectedRoom, data, ...rest) {
    return window.api.post(apiPath(`/rrc/hubs/${selectedHubHash}/rooms/${selectedRoom}/messages`), data, ...rest);
}
export function createServers(data, ...rest) {
    return window.api.post(apiPath("/rrc/servers"), data, ...rest);
}
export function announceServers(id, data, ...rest) {
    return window.api.post(apiPath(`/rrc/servers/${id}/announce`), data, ...rest);
}
export function createServersRooms(id, data, ...rest) {
    return window.api.post(apiPath(`/rrc/servers/${id}/rooms`), data, ...rest);
}
export function startServers(id, data, ...rest) {
    return window.api.post(apiPath(`/rrc/servers/${id}/start`), data, ...rest);
}
export function stopServers(id, data, ...rest) {
    return window.api.post(apiPath(`/rrc/servers/${id}/stop`), data, ...rest);
}
export function moderateServers(id, data, ...rest) {
    return window.api.post(apiPath(`/rrc/servers/${id}/moderate`), data, ...rest);
}
export function createServersRooms2(id, data, ...rest) {
    return window.api.post(apiPath(`/rrc/servers/${id}/rooms`), data, ...rest);
}
export function updateHubsRoomsOrder(hubHash, data, ...rest) {
    return window.api.put(apiPath(`/rrc/hubs/${hubHash}/rooms/order`), data, ...rest);
}
export function updateHubsOrder(data, ...rest) {
    return window.api.put(apiPath("/rrc/hubs/order"), data, ...rest);
}
export function updateServersRoomsKey(id, selectedRoom, data, ...rest) {
    return window.api.put(apiPath(`/rrc/servers/${id}/rooms/${selectedRoom}/key`), data, ...rest);
}
