import LinkUtils from "./LinkUtils.js";

const HEX32 = /^[a-fA-F0-9]{32}$/;

export function openExternalHttpUrl(url, opener = window.open.bind(window)) {
    if (!url) {
        return;
    }
    opener(url, "_blank", "noopener,noreferrer");
}

function stopEvent(event) {
    event.preventDefault?.();
    event.stopPropagation?.();
}

function scrollToElementId(id, scrollRoot) {
    const escapedId =
        typeof CSS !== "undefined" && typeof CSS.escape === "function" ? CSS.escape(id) : id.replace(/"/g, '\\"');
    const el = scrollRoot ? scrollRoot.querySelector(`#${escapedId}`) : document.getElementById(id);
    if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
}

/**
 * Intercepts clicks inside rich HTML (v-html) containers so nomad/mesh links stay
 * in-app, http(s) links open externally, and other navigation does not trap the shell.
 *
 * @param {MouseEvent} event
 * @param {object} [options]
 * @param {Element|null} [options.scrollRoot] - scope fragment anchor scrolling
 * @param {(url: string) => void} [options.onNomadUrl] - data-nomadnet-url handler
 * @param {(address: string) => void} [options.onLxmfAddress] - data-lxmf-address handler
 * @param {(destination: string, fields: string|null) => void} [options.onOpenNode]
 * @param {(url: string) => void|Promise<void>} [options.openExternalHttp]
 * @param {boolean} [options.blockUnhandledAnchors=true]
 * @returns {boolean} true when the click was handled
 */
export function handleRichHtmlLinkClick(event, options = {}) {
    const {
        scrollRoot = null,
        onNomadUrl,
        onLxmfAddress,
        onOpenNode,
        openExternalHttp = openExternalHttpUrl,
        blockUnhandledAnchors = true,
    } = options;

    const nomadLink = event.target.closest("a.nomadnet-link[data-nomadnet-url]");
    if (nomadLink && onNomadUrl) {
        stopEvent(event);
        const url = nomadLink.getAttribute("data-nomadnet-url");
        if (url) {
            onNomadUrl(url);
        }
        return true;
    }

    const lxmfLink = event.target.closest("a.lxmf-link[data-lxmf-address]");
    if (lxmfLink && onLxmfAddress) {
        stopEvent(event);
        const address = lxmfLink.getAttribute("data-lxmf-address");
        if (address && HEX32.test(address)) {
            onLxmfAddress(address);
        }
        return true;
    }

    const externalAnchor = event.target.closest("a[href]");
    if (externalAnchor && !externalAnchor.classList.contains("nomadnet-link")) {
        const href = externalAnchor.getAttribute("href");
        const httpHref = href ? LinkUtils.httpUrlHrefOrNull(href.trim()) : null;
        if (httpHref) {
            stopEvent(event);
            openExternalHttp(httpHref);
            return true;
        }
    }

    const fragAnchor = event.target.closest("a[href]");
    if (
        fragAnchor &&
        fragAnchor.getAttribute("href") &&
        fragAnchor.getAttribute("href") !== "#" &&
        fragAnchor.getAttribute("href").startsWith("#") &&
        !fragAnchor.getAttribute("data-nomadnet-url")
    ) {
        stopEvent(event);
        const raw = fragAnchor.getAttribute("href").slice(1);
        scrollToElementId(decodeURIComponent(raw), scrollRoot);
        return true;
    }

    const nodeLink = event.target.closest('[data-action="openNode"]');
    if (nodeLink && onOpenNode) {
        stopEvent(event);
        const destination = nodeLink.getAttribute("data-destination");
        if (destination) {
            onOpenNode(destination, nodeLink.getAttribute("data-fields"));
        }
        return true;
    }

    if (blockUnhandledAnchors) {
        const anchor = event.target.closest("a[href]");
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
