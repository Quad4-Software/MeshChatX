// @ts-check

/**
 * Endpoint wrappers for /api/v1/nomadnet.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function deleteArchives(...rest) {
    return window.api.delete(apiPath("/nomadnet/archives"), ...rest);
}
export function listArchives(...rest) {
    return window.api.get(apiPath("/nomadnet/archives"), ...rest);
}
export function getArchives(id, ...rest) {
    return window.api.get(apiPath(`/nomadnet/archives/${id}`), ...rest);
}
export function getArchivesExport(...rest) {
    return window.api.get(apiPath("/nomadnet/archives/export"), ...rest);
}
export function recrawlArchives(data, ...rest) {
    return window.api.post(apiPath("/nomadnet/archives/recrawl"), data, ...rest);
}
export function optOutsCrawl(data, ...rest) {
    return window.api.post(apiPath("/nomadnet/crawl/opt-outs"), data, ...rest);
}
