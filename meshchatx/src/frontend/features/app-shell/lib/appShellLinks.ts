// SPDX-License-Identifier: 0BSD

/**
 * Protocol link handling for the app shell.
 * handleProtocolLink / openRelayShareLink live here so the Svelte shell stays
 * small and the URI rules stay testable without a component.
 */

import LiveTransport from "../../../js/liveTransport.js";
import ToastUtils from "../../../js/ToastUtils.js";
import GlobalState from "../../../js/GlobalState.js";
import { t } from "../../../js/i18n.js";
import { applyRelayShareLink, parseMeshchatRelayUri } from "../../../js/relayLinkUtils.js";
import type { RouteTarget } from "../../../shell/hashRouter.js";

export interface ShellRouter {
    push: (target: RouteTarget | string) => Promise<unknown> | unknown;
    replace?: (target: RouteTarget | string) => Promise<unknown> | unknown;
}

const KNOWN_MESHCHATX_HOSTS = ["map", "docs", "relay", "app"];

/**
 * Join a relay hub share link and open Relay Chat on it.
 */
export async function openRelayShareLink(router: ShellRouter, uri: string): Promise<void> {
    const parsed = parseMeshchatRelayUri(uri);
    if (!parsed) {
        ToastUtils.error(t("messages.relay_link_invalid"));
        return;
    }
    if (GlobalState.config?.rrc_enabled === false) {
        ToastUtils.warning(t("messages.relay_link_disabled"));
        return;
    }
    try {
        const result = await applyRelayShareLink(parsed);
        await router.push({
            name: "relay-chat",
            query: {
                hub: result.hub_hash,
                ...(result.room ? { room: result.room } : {}),
            },
        });
        ToastUtils.success(t("messages.relay_link_opened"));
    } catch (e) {
        const error = e as { response?: { data?: { message?: string } } };
        ToastUtils.error(error.response?.data?.message || t("messages.relay_link_failed"));
    }
}

/**
 * Route a meshchatx://, lxmf://, lxma:// or rns:// link from Electron, Android
 * intents, or the in-app link handler.
 */
export function handleProtocolLink(router: ShellRouter, url: string): void {
    try {
        const normalizedUrl = String(url || "").trim();
        if (!normalizedUrl) {
            return;
        }
        if (/^meshchatx:\/\/app\/messages\/?/i.test(normalizedUrl)) {
            let destinationHash = "";
            try {
                const parsed = new URL(normalizedUrl);
                const parts = String(parsed.pathname || "")
                    .split("/")
                    .filter((part) => part.length > 0);
                if (parts.length >= 2 && parts[0].toLowerCase() === "messages") {
                    destinationHash = String(parts[1] || "").trim();
                }
            } catch {
                /* keep destinationHash empty */
            }
            if (/^[0-9a-fA-F]{8,64}$/.test(destinationHash)) {
                void router.push({
                    name: "messages",
                    params: { destinationHash: destinationHash.toLowerCase() },
                });
                return;
            }
            void router.push({ name: "messages" });
            return;
        }
        if (/^meshchatx:\/\/app\/call\/?/i.test(normalizedUrl)) {
            void router.push({ name: "call", query: { tab: "phone" } });
            return;
        }
        try {
            const parsed = new URL(normalizedUrl);
            const proto = parsed.protocol.toLowerCase();
            const host = parsed.hostname.toLowerCase();
            if ((proto === "meshchatx:" || proto === "meshchat:") && host === "docs") {
                let rel = parsed.searchParams.get("reticulum") ?? parsed.searchParams.get("path") ?? "";
                rel = String(rel).trim();
                if (!rel && parsed.pathname && parsed.pathname !== "/") {
                    try {
                        rel = decodeURIComponent(parsed.pathname.replace(/^\/+/, ""));
                    } catch {
                        rel = parsed.pathname.replace(/^\/+/, "");
                    }
                }
                if (rel) {
                    void router.push({
                        name: "documentation",
                        query: { reticulum: encodeURIComponent(rel) },
                    });
                } else {
                    void router.push({ name: "documentation" });
                }
                return;
            }
        } catch {
            /* not a valid URL, continue */
        }
        if (/^(meshchatx|meshchat):\/\/map\b/i.test(normalizedUrl)) {
            LiveTransport.send(
                JSON.stringify({
                    type: "lxm.ingest_uri",
                    uri: normalizedUrl,
                })
            );
            return;
        }
        if (/^(meshchatx|meshchat):\/\/relay\b/i.test(normalizedUrl)) {
            void openRelayShareLink(router, normalizedUrl);
            return;
        }
        if (/^(meshchatx|meshchat):\/\//i.test(normalizedUrl)) {
            try {
                const parsed = new URL(normalizedUrl);
                const host = (parsed.hostname || "").toLowerCase();
                if (host && !KNOWN_MESHCHATX_HOSTS.includes(host)) {
                    ToastUtils.error(t("messages.unknown_meshchatx_link", { host }));
                    return;
                }
            } catch {
                ToastUtils.error(t("messages.unknown_meshchatx_link_generic"));
                return;
            }
        }
        if (/^lxm(a|f)?:\/\//i.test(normalizedUrl)) {
            LiveTransport.send(
                JSON.stringify({
                    type: "lxm.ingest_uri",
                    uri: normalizedUrl,
                })
            );
        }

        const cleanUrl = normalizedUrl
            .replace(/^lxma:\/\//i, "")
            .replace(/^lxmf:\/\//i, "")
            .replace(/^rns:\/\//i, "");
        const hash = cleanUrl.split(":")[0].split("/")[0].replace("/", "");
        if (hash && hash.length === 32) {
            void router.push({
                name: "messages",
                params: { destinationHash: hash },
            });
        }
    } catch (e) {
        console.error("Failed to handle protocol link:", e);
    }
}
