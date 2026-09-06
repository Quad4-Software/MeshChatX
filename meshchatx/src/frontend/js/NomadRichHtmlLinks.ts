import LinkUtils from "./LinkUtils.js";

const HEX32 = /^[a-fA-F0-9]{32}$/;

export function openExternalHttpUrl(url: string, opener: typeof window.open = window.open.bind(window)): void {
    if (!url) {
        return;
    }
    opener(url, "_blank", "noopener,noreferrer");
}

function stopEvent(event: MouseEvent): void {
    event.preventDefault?.();
    event.stopPropagation?.();
}

function escapeCssIdent(id: string): string {
    if (typeof CSS !== "undefined" && typeof CSS.escape === "function") {
        return CSS.escape(id);
    }
    // Escape backslash before quote so selectors cannot break out of the quoted form.
    return String(id).replace(/\\/g, "\\\\").replace(/"/g, '\\"');
}

function scrollToElementId(id: string, scrollRoot: Element | null): void {
    const escapedId = escapeCssIdent(id);
    const el = scrollRoot ? scrollRoot.querySelector(`#${escapedId}`) : document.getElementById(id);
    if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
}

export type RichHtmlLinkClickOptions = {
    scrollRoot?: Element | null;
    onNomadUrl?: (url: string) => void;
    onLxmfAddress?: (address: string) => void;
    onOpenNode?: (destination: string, fields: string | null) => void;
    openExternalHttp?: (url: string) => void | Promise<void>;
    blockUnhandledAnchors?: boolean;
};

/**
 * Intercepts clicks inside rich HTML containers so nomad/mesh links stay
 * in-app, http(s) links open externally, and other navigation does not trap the shell.
 * Returns true when the click was handled.
 */
export function handleRichHtmlLinkClick(event: MouseEvent, options: RichHtmlLinkClickOptions = {}): boolean {
    const {
        scrollRoot = null,
        onNomadUrl,
        onLxmfAddress,
        onOpenNode,
        openExternalHttp = openExternalHttpUrl,
        blockUnhandledAnchors = true,
    } = options;

    const target = event.target as Element | null;
    if (!target || typeof target.closest !== "function") {
        return false;
    }

    const nomadLink = target.closest("a.nomadnet-link[data-nomadnet-url]");
    if (nomadLink && onNomadUrl) {
        stopEvent(event);
        const url = nomadLink.getAttribute("data-nomadnet-url");
        if (url) {
            onNomadUrl(url);
        }
        return true;
    }

    const lxmfLink = target.closest("a.lxmf-link[data-lxmf-address]");
    if (lxmfLink && onLxmfAddress) {
        stopEvent(event);
        const address = lxmfLink.getAttribute("data-lxmf-address");
        if (address && HEX32.test(address)) {
            onLxmfAddress(address);
        }
        return true;
    }

    const externalAnchor = target.closest("a[href], a[data-http-url]");
    if (externalAnchor && !externalAnchor.classList.contains("nomadnet-link")) {
        const dataHttp = externalAnchor.getAttribute("data-http-url");
        const href = externalAnchor.getAttribute("href");
        const httpHref = dataHttp
            ? LinkUtils.httpUrlHrefOrNull(dataHttp.trim())
            : href
              ? LinkUtils.httpUrlHrefOrNull(href.trim())
              : null;
        if (httpHref) {
            stopEvent(event);
            openExternalHttp(httpHref);
            return true;
        }
    }

    const fragAnchor = target.closest("a[href]");
    const fragHref = fragAnchor?.getAttribute("href");
    if (
        fragAnchor &&
        fragHref &&
        fragHref !== "#" &&
        fragHref.startsWith("#") &&
        !fragAnchor.getAttribute("data-nomadnet-url")
    ) {
        stopEvent(event);
        const raw = fragHref.slice(1);
        scrollToElementId(decodeURIComponent(raw), scrollRoot);
        return true;
    }

    const nodeLink = target.closest('[data-action="openNode"]');
    if (nodeLink && onOpenNode) {
        stopEvent(event);
        const destination = nodeLink.getAttribute("data-destination");
        if (destination) {
            onOpenNode(destination, nodeLink.getAttribute("data-fields"));
        }
        return true;
    }

    if (blockUnhandledAnchors) {
        const anchor = target.closest("a[href]");
        if (anchor) {
            const href = (anchor.getAttribute("href") || "").trim();
            if (href && href !== "#" && !href.startsWith("#")) {
                stopEvent(event);
                return true;
            }
        }
    }

    return false;
}
