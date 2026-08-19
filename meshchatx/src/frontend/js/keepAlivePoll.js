// SPDX-License-Identifier: 0BSD

/**
 * Keep-alive browsers leave embedded pages mounted. Skip background polls
 * while the tab or route is not the one on screen.
 * @param {boolean} embedded
 * @param {boolean} isActive
 * @returns {boolean}
 */
export function shouldPollKeepAliveEmbedded(embedded, isActive) {
    if (embedded && !isActive) {
        return false;
    }
    return true;
}
