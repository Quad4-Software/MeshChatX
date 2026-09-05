// SPDX-License-Identifier: 0BSD

/** Default timeout in seconds for remote queries */
export const DEFAULT_REMOTE_TIMEOUT = 15;

/** Default number of path items per page */
export const DEFAULT_ITEMS_PER_PAGE = 50;

/** Allowed items per page options */
export const ITEMS_PER_PAGE_OPTIONS = [20, 50, 100, 250] as const;

/** Path state representing responsive */
export const PATH_STATE_RESPONSIVE = 2;

/** Path state representing unresponsive */
export const PATH_STATE_UNRESPONSIVE = 1;

/** Hex character length for 16 byte Reticulum destination hashes */
export const DESTINATION_HASH_HEX_LENGTH = 32;

/** Available navigation tabs for RNPath page */
export const RNPATH_TABS = ["table", "rates", "actions"] as const;
