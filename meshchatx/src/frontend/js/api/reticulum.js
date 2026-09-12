// @ts-check

/**
 * Endpoint wrappers for /api/v1/reticulum.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function deleteInterfaceModules(typeName, ...rest) {
    return window.api.delete(apiPath(`/reticulum/interface-modules/${typeName}`), ...rest);
}
export function getBlackhole(...rest) {
    return window.api.get(apiPath("/reticulum/blackhole"), ...rest);
}
export function getConfigRaw(...rest) {
    return window.api.get(apiPath("/reticulum/config/raw"), ...rest);
}
export function listDiscoveredInterfaces(...rest) {
    return window.api.get(apiPath("/reticulum/discovered-interfaces"), ...rest);
}
export function getDiscovery(...rest) {
    return window.api.get(apiPath("/reticulum/discovery"), ...rest);
}
export function getInstance(...rest) {
    return window.api.get(apiPath("/reticulum/instance"), ...rest);
}
export function listInterfaceModules(...rest) {
    return window.api.get(apiPath("/reticulum/interface-modules"), ...rest);
}
export function listInterfaces(...rest) {
    return window.api.get(apiPath("/reticulum/interfaces"), ...rest);
}
export function listManagementIdentities(...rest) {
    return window.api.get(apiPath("/reticulum/management-identities"), ...rest);
}
export function updateDiscovery(data, ...rest) {
    return window.api.patch(apiPath("/reticulum/discovery"), data, ...rest);
}
export function updateInstance(data, ...rest) {
    return window.api.patch(apiPath("/reticulum/instance"), data, ...rest);
}
export function resetConfig(data, ...rest) {
    return window.api.post(apiPath("/reticulum/config/reset"), data, ...rest);
}
export function createInterfaceModules(data, ...rest) {
    return window.api.post(apiPath("/reticulum/interface-modules"), data, ...rest);
}
export function addInterfaces(data, ...rest) {
    return window.api.post(apiPath("/reticulum/interfaces/add"), data, ...rest);
}
export function deleteInterfaces(data, ...rest) {
    return window.api.post(apiPath("/reticulum/interfaces/delete"), data, ...rest);
}
export function disableInterfaces(data, ...rest) {
    return window.api.post(apiPath("/reticulum/interfaces/disable"), data, ...rest);
}
export function enableInterfaces(data, ...rest) {
    return window.api.post(apiPath("/reticulum/interfaces/enable"), data, ...rest);
}
export function exportInterfaces(data, ...rest) {
    return window.api.post(apiPath("/reticulum/interfaces/export"), data, ...rest);
}
export function importInterfaces(data, ...rest) {
    return window.api.post(apiPath("/reticulum/interfaces/import"), data, ...rest);
}
export function postInterfacesImportPreview(data, ...rest) {
    return window.api.post(apiPath("/reticulum/interfaces/import-preview"), data, ...rest);
}
export function createManagementIdentities(data, ...rest) {
    return window.api.post(apiPath("/reticulum/management-identities"), data, ...rest);
}
export function recoverReticulum(data, ...rest) {
    return window.api.post(apiPath("/reticulum/recover"), data, ...rest);
}
export function reloadReticulum(data, ...rest) {
    return window.api.post(apiPath("/reticulum/reload"), data, ...rest);
}
export function updateConfigRaw(data, ...rest) {
    return window.api.put(apiPath("/reticulum/config/raw"), data, ...rest);
}
