// SPDX-License-Identifier: 0BSD

/** Minimum viewport width in pixels for side-by-side split layout */
export const SPLIT_MIN_WIDTH = 1024;

/** Default pagination page size for archives list */
export const DEFAULT_PAGE_LIMIT = 25;

/** Search input debounce delay in milliseconds */
export const SEARCH_DEBOUNCE_MS = 300;

/** API endpoint for nomadnet archives list and item operations */
export const API_NOMADNET_ARCHIVES = "/api/v1/nomadnet/archives";

/** API endpoint for nomadnet archive recrawl */
export const API_NOMADNET_ARCHIVES_RECRAWL = "/api/v1/nomadnet/archives/recrawl";

/** API endpoint for crawl opt-outs */
export const API_NOMADNET_OPT_OUTS = "/api/v1/nomadnet/crawl/opt-outs";
