// SPDX-License-Identifier: 0BSD

import { formatFatalErrorReport, recordFatalErrorLocally, type FatalErrorRecord } from "../../../js/fatalErrorState.js";
import { copyTextToClipboard } from "../../../js/clipboardUtils.js";
import { BUGS_PLUGIN_FALLBACK_HASH, BUGS_PLUGIN_ROUTE_NAME } from "./constants.js";

export interface FatalErrorSummary {
    kind: "backend" | "frontend";
    title: string;
    message: string;
    detailBody: string;
    hasDetails: boolean;
}

/**
 * Derive summary presentation fields from a fatal error record
 */
export function resolveFatalErrorSummary(
    error: FatalErrorRecord | null | undefined,
    fallbackBackendTitle: string,
    fallbackFrontendTitle: string
): FatalErrorSummary {
    const kind = error?.kind === "backend" ? "backend" : "frontend";
    const defaultTitle = kind === "backend" ? fallbackBackendTitle : fallbackFrontendTitle;
    const title = error?.title || defaultTitle;
    const message = error?.message || "";
    const detailBody = [error?.details, error?.context, error?.stack].filter(Boolean).join("\n\n");
    const hasDetails = Boolean(detailBody);

    return {
        kind,
        title,
        message,
        detailBody,
        hasDetails,
    };
}

/**
 * Save report locally and navigate to the bugs plugin
 */
export async function reportFatalErrorLocally(
    error: FatalErrorRecord | null | undefined,
    router?: { push?: (target: { name: string }) => void }
): Promise<boolean> {
    if (!error) {
        return false;
    }
    const normalized: FatalErrorRecord = {
        ...error,
        timestamp: typeof error.timestamp === "number" ? error.timestamp : Date.now(),
    };
    const result = await recordFatalErrorLocally(normalized);
    if (!result?.ok) {
        return false;
    }
    try {
        router?.push?.({ name: BUGS_PLUGIN_ROUTE_NAME });
    } catch {
        if (typeof window !== "undefined") {
            window.location.hash = BUGS_PLUGIN_FALLBACK_HASH;
        }
    }
    return true;
}

/**
 * Format and copy fatal error report to clipboard
 */
export async function copyFatalErrorReport(error: FatalErrorRecord | null | undefined): Promise<boolean> {
    if (!error) {
        return false;
    }
    const normalized: FatalErrorRecord = {
        ...error,
        timestamp: typeof error.timestamp === "number" ? error.timestamp : Date.now(),
    };
    const report = formatFatalErrorReport(normalized);
    return await copyTextToClipboard(report);
}
