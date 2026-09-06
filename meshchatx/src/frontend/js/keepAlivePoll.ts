// SPDX-License-Identifier: 0BSD

/**
 * Keep-alive browsers leave embedded pages mounted. Skip background polls
 * while the tab or route is not the one on screen.
 */
export function shouldPollKeepAliveEmbedded(embedded: boolean, isActive: boolean): boolean {
    if (embedded && !isActive) {
        return false;
    }
    return true;
}
