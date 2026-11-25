// @ts-check

/**
 * Endpoint wrappers for /api/v1/stickers.
 * Each function maps one HTTP call through window.api. Add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants";

export function getImage(id, ...rest) {
    return window.api.get(apiPath(`/stickers/${id}/image`), ...rest);
}
