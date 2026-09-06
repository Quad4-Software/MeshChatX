// SPDX-License-Identifier: 0BSD

import { isCancelledPageContent, isFailedPageContent } from "./nomadPageDownloads.js";

export interface CrashTabHostVisibilityInput {
    selectedNode: unknown;
    nodePagePath: string | null | undefined;
    showCancelledPageState: boolean;
    nodePageContent: string | null | undefined;
    showEmptyPageState: boolean;
}

/**
 * Keep the sandboxed crash-tab iframe mounted during download/render so it stays warm.
 * Hide it for cancelled, failed, and empty page states.
 */
export function shouldShowCrashTabHost(input: CrashTabHostVisibilityInput): boolean {
    if (!input.selectedNode || !input.nodePagePath) {
        return false;
    }
    if (input.showCancelledPageState) {
        return false;
    }
    if (isFailedPageContent(input.nodePageContent)) {
        return false;
    }
    if (input.showEmptyPageState) {
        return false;
    }
    return true;
}

export interface CrashTabPageContentInput {
    isLoadingNodePage: boolean;
    nodePageContent: string | null | undefined;
}

/** Content pushed into the crash-tab frame (empty while downloading or on status text). */
export function resolveCrashTabPageContent(input: CrashTabPageContentInput): string {
    if (input.isLoadingNodePage) {
        return "";
    }
    if (isCancelledPageContent(input.nodePageContent) || isFailedPageContent(input.nodePageContent)) {
        return "";
    }
    return input.nodePageContent || "";
}

export interface CanRetryCrashTabRenderInput {
    pageRenderAborted: boolean;
    nodePageContent: string | null | undefined;
}

/** Retry is only for crash-tab paint abort, not download-cancelled sentinels. */
export function canRetryCrashTabRender(input: CanRetryCrashTabRenderInput): boolean {
    return Boolean(
        input.pageRenderAborted &&
        input.nodePageContent &&
        !isCancelledPageContent(input.nodePageContent) &&
        !isFailedPageContent(input.nodePageContent)
    );
}

/** Path-based content classes for the isolated renderer (Vue NomadNetworkPage parity). */
export function resolveNomadCrashTabContentClass(options: {
    nodePagePath: string | null | undefined;
    isShowingNodePageSource: boolean;
    nomadRenderedShellFullBleed?: boolean;
    nomadShellDark?: boolean;
}): string {
    if (options.isShowingNodePageSource) {
        return "source bg-black";
    }
    if (!options.nodePagePath) {
        return "";
    }
    const [p] = options.nodePagePath.split("`");
    const pl = (p || "").toLowerCase();
    const classes: string[] = [];
    if (pl.endsWith(".mu") || pl.endsWith(".md") || pl.endsWith(".html")) {
        classes.push("nomad-page-rich");
    }
    if (pl.endsWith(".html")) {
        classes.push("nomad-page-html-host");
    } else if (pl.endsWith(".md")) {
        classes.push("nomad-markdown-host");
    } else if (pl.endsWith(".mu")) {
        classes.push("bg-black");
    } else {
        classes.push("plaintext-page");
    }
    if (options.nomadRenderedShellFullBleed) {
        classes.push("pad");
        if (options.nomadShellDark) {
            classes.push("nomad-shell-dark");
        }
    }
    return classes.join(" ");
}
