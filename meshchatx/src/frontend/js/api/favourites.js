// @ts-check

/**
 * Endpoint wrappers for /api/v1/favourites.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function remove(h, ...rest) {
    return window.api.delete(apiPath(`/favourites/${h}`), ...rest);
}
export function delete2(destinationHash, ...rest) {
    return window.api.delete(apiPath(`/favourites/${destinationHash}`), ...rest);
}
export function listFavourites(...rest) {
    return window.api.get(apiPath("/favourites"), ...rest);
}
export function postIdentifyOnConnect(destinationHash, data, ...rest) {
    return window.api.post(apiPath(`/favourites/${destinationHash}/identify-on-connect`), data, ...rest);
}
export function postRename(destinationHash, data, ...rest) {
    return window.api.post(apiPath(`/favourites/${destinationHash}/rename`), data, ...rest);
}
export function addFavourites(data, ...rest) {
    return window.api.post(apiPath("/favourites/add"), data, ...rest);
}
export function importFavourites(data, ...rest) {
    return window.api.post(apiPath("/favourites/import"), data, ...rest);
}
