import { RETICULUM_MANUAL_INTERFACES_COMMON_OPTIONS_REL } from "./reticulumDocsEntryUrl.js";

export type HashRouterPushFacade = {
    push: (target: unknown) => unknown;
};

export type DocsDeepLinkScheme = "meshchatx" | "meshchat";

/** Open the in-app documentation tool to a path under /reticulum-docs/. */
export function openBundledReticulumManualPath(
    router: HashRouterPushFacade,
    relPath: string = RETICULUM_MANUAL_INTERFACES_COMMON_OPTIONS_REL
): unknown {
    return router.push({
        name: "documentation",
        query: { reticulum: encodeURIComponent(relPath) },
    });
}

/**
 * Host-agnostic deep link for the bundled Reticulum manual (handled in
 * appShellLinks handleProtocolLink). Use in LXMF, notifications, or when the
 * browser base URL is unknown.
 */
export function bundledReticulumManualDeepLink(relPath: string, scheme: DocsDeepLinkScheme = "meshchatx"): string {
    const s = scheme === "meshchat" ? "meshchat" : "meshchatx";
    const q = new URLSearchParams();
    q.set("reticulum", relPath);
    return `${s}://docs?${q.toString()}`;
}
