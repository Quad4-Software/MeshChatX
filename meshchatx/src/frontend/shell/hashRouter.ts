// SPDX-License-Identifier: 0BSD

/**
 * Framework-free hash router over routeRegistry.
 * Replaces vue-router for feature pages during the Svelte host flip.
 * Parses "#/path?query#fragment", matches registry paths with ":param" and
 * ":param?" segments, and exposes a small vue-router shaped shim for callers
 * that still take a router object (CallOverlay, FatalErrorPage, PluginHost).
 */

import { listRoutes, registerRoute, unregisterRoute } from "../js/registries/routeRegistry.js";
import type { PageMountKind, RouteRegistryEntry } from "../js/registries/routeRegistry.js";

export interface RouteTarget {
    name?: string;
    path?: string;
    params?: Record<string, unknown>;
    query?: Record<string, unknown>;
    hash?: string;
}

export interface ActiveRoute {
    name: string;
    path: string;
    fullPath: string;
    params: Record<string, string>;
    query: Record<string, string>;
    hash: string;
    meta: Record<string, unknown>;
    mount: PageMountKind;
    featureLoad: (() => Promise<unknown>) | null;
    routeProps: Record<string, unknown>;
    matched: boolean;
}

export type NavigationDecision = { allow: true } | { allow: false; redirect: string };
export type NavigationGuard = (to: ActiveRoute) => Promise<NavigationDecision> | NavigationDecision;
export type RouteListener = (route: ActiveRoute | null) => void;

interface PathSegment {
    literal: string | null;
    param: string | null;
    optional: boolean;
}

/** Redirect table applied before matching. Mirrors the vue-router "/" record. */
const REDIRECTS: Record<string, string> = {
    "/": "/messages",
    "": "/messages",
};

const listeners = new Set<RouteListener>();

let currentRoute: ActiveRoute | null = null;
let navigationGuard: NavigationGuard | null = null;
let started = false;
let resolveToken = 0;

function compilePath(pattern: string): PathSegment[] {
    return String(pattern)
        .split("/")
        .filter((part) => part.length > 0)
        .map((part) => {
            if (part.startsWith(":")) {
                const optional = part.endsWith("?");
                return {
                    literal: null,
                    param: part.slice(1, optional ? -1 : undefined),
                    optional,
                };
            }
            return { literal: part, param: null, optional: false };
        });
}

function matchSegments(segments: PathSegment[], parts: string[]): Record<string, string> | null {
    const params: Record<string, string> = {};
    let index = 0;
    for (const segment of segments) {
        if (segment.param) {
            if (index < parts.length) {
                try {
                    params[segment.param] = decodeURIComponent(parts[index]);
                } catch {
                    params[segment.param] = parts[index];
                }
                index += 1;
            } else if (!segment.optional) {
                return null;
            }
            continue;
        }
        if (index < parts.length && parts[index] === segment.literal) {
            index += 1;
            continue;
        }
        return null;
    }
    if (index !== parts.length) {
        return null;
    }
    return params;
}

function parseQuery(search: string): Record<string, string> {
    const query: Record<string, string> = {};
    if (!search) {
        return query;
    }
    const params = new URLSearchParams(search);
    for (const [key, value] of params.entries()) {
        query[key] = value;
    }
    return query;
}

function serializeQuery(query: Record<string, unknown> | undefined): string {
    if (!query) {
        return "";
    }
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
        if (value == null || value === "") {
            continue;
        }
        params.set(key, String(value));
    }
    const text = params.toString();
    return text ? `?${text}` : "";
}

/**
 * Split "#/path?a=1#frag" into its three parts.
 */
export function parseHashLocation(raw: string): { path: string; search: string; hash: string } {
    let rest = String(raw || "");
    if (rest.startsWith("#")) {
        rest = rest.slice(1);
    }
    let hash = "";
    const hashIndex = rest.indexOf("#");
    if (hashIndex >= 0) {
        hash = rest.slice(hashIndex);
        rest = rest.slice(0, hashIndex);
    }
    let search = "";
    const queryIndex = rest.indexOf("?");
    if (queryIndex >= 0) {
        search = rest.slice(queryIndex + 1);
        rest = rest.slice(0, queryIndex);
    }
    if (!rest.startsWith("/")) {
        rest = `/${rest}`;
    }
    return { path: rest, search, hash };
}

function buildPathForEntry(entry: RouteRegistryEntry, params: Record<string, unknown> | undefined): string {
    const segments = compilePath(entry.path);
    const parts: string[] = [];
    for (const segment of segments) {
        if (!segment.param) {
            parts.push(segment.literal as string);
            continue;
        }
        const value = params ? params[segment.param] : undefined;
        if (value == null || value === "") {
            if (segment.optional) {
                continue;
            }
            throw new Error(`hashRouter: route "${entry.name}" needs param "${segment.param}"`);
        }
        parts.push(encodeURIComponent(String(value)));
    }
    return `/${parts.join("/")}`;
}

/**
 * Turn a route target into the hash body ("/messages/ab12?x=1#frag"), no leading "#".
 */
export function resolveTarget(target: RouteTarget | string): string {
    if (typeof target === "string") {
        const parsed = parseHashLocation(target);
        return `${parsed.path}${parsed.search ? `?${parsed.search}` : ""}${parsed.hash}`;
    }
    if (!target || typeof target !== "object") {
        return "/";
    }
    let path = "";
    if (target.path) {
        path = parseHashLocation(target.path).path;
    } else if (target.name) {
        const entry = listRoutes().find((candidate) => candidate.name === target.name);
        if (!entry) {
            throw new Error(`hashRouter: unknown route name "${target.name}"`);
        }
        path = buildPathForEntry(entry, target.params);
    } else {
        path = "/";
    }
    const search = serializeQuery(target.query);
    const hash = target.hash ? (target.hash.startsWith("#") ? target.hash : `#${target.hash}`) : "";
    return `${path}${search}${hash}`;
}

function unmatchedRoute(path: string, query: Record<string, string>, hash: string): ActiveRoute {
    return {
        name: "",
        path,
        fullPath: `${path}${serializeQuery(query)}${hash}`,
        params: {},
        query,
        hash,
        meta: {},
        mount: "svelte",
        featureLoad: null,
        routeProps: {},
        matched: false,
    };
}

/**
 * Match a hash body against the registry without touching the current route.
 */
export function resolveRoute(path: string, search = "", hash = ""): ActiveRoute {
    const query = parseQuery(search);
    const parts = path.split("/").filter((part) => part.length > 0);
    for (const entry of listRoutes()) {
        const params = matchSegments(compilePath(entry.path), parts);
        if (!params) {
            continue;
        }
        return {
            name: entry.name,
            path: entry.path,
            fullPath: `${path}${serializeQuery(query)}${hash}`,
            params,
            query,
            hash,
            meta: (entry.meta || {}) as Record<string, unknown>,
            mount: entry.mount,
            featureLoad: typeof entry.load === "function" ? entry.load : null,
            routeProps: (entry.routeProps || {}) as Record<string, unknown>,
            matched: true,
        };
    }
    return unmatchedRoute(path, query, hash);
}

export function getCurrentRoute(): ActiveRoute | null {
    return currentRoute;
}

/**
 * True when the outlet must keep the mounted page alive after navigating away.
 */
export function shouldKeepAlive(route: ActiveRoute | null): boolean {
    return Boolean(route?.meta?.keepAlive);
}

export function subscribe(listener: RouteListener): () => void {
    if (typeof listener !== "function") {
        throw new Error("hashRouter: subscribe needs a function");
    }
    listeners.add(listener);
    listener(currentRoute);
    return () => {
        listeners.delete(listener);
    };
}

function notify(): void {
    for (const listener of [...listeners]) {
        try {
            listener(currentRoute);
        } catch (error) {
            console.error("hashRouter listener failed", error);
        }
    }
}

/**
 * Install the auth guard. Runs before every committed navigation.
 */
export function setNavigationGuard(guard: NavigationGuard | null): void {
    navigationGuard = typeof guard === "function" ? guard : null;
}

function currentHashBody(): string {
    const parsed = parseHashLocation(typeof window === "undefined" ? "" : window.location.hash);
    return `${parsed.path}${parsed.search ? `?${parsed.search}` : ""}${parsed.hash}`;
}

async function applyLocation(): Promise<void> {
    const token = ++resolveToken;
    const parsed = parseHashLocation(window.location.hash);
    const redirect = REDIRECTS[parsed.path];
    if (redirect) {
        writeHash(`${redirect}${parsed.search ? `?${parsed.search}` : ""}${parsed.hash}`, true);
        return;
    }
    const next = resolveRoute(parsed.path, parsed.search, parsed.hash);
    if (navigationGuard) {
        let decision: NavigationDecision = { allow: true };
        try {
            decision = await navigationGuard(next);
        } catch (error) {
            console.error("hashRouter guard failed", error);
        }
        if (token !== resolveToken) {
            return;
        }
        if (!decision.allow) {
            writeHash(decision.redirect, true);
            return;
        }
    }
    if (token !== resolveToken) {
        return;
    }
    currentRoute = next;
    notify();
}

function writeHash(body: string, replace: boolean): void {
    const resolved = resolveTarget(body);
    const nextHash = `#${resolved}`;
    if (currentHashBody() === resolved) {
        void applyLocation();
        return;
    }
    if (replace) {
        history.replaceState(null, "", nextHash);
        void applyLocation();
        return;
    }
    window.location.hash = nextHash;
}

/**
 * Navigate to a path string or a {name, params, query, hash} target.
 */
export function navigate(target: RouteTarget | string, options: { replace?: boolean } = {}): Promise<void> {
    try {
        writeHash(resolveTarget(target), options.replace === true);
    } catch (error) {
        console.error("hashRouter navigate failed", error);
    }
    return Promise.resolve();
}

function onHashChange(): void {
    void applyLocation();
}

export function start(): void {
    if (started || typeof window === "undefined") {
        return;
    }
    started = true;
    window.addEventListener("hashchange", onHashChange);
    void applyLocation();
}

export function stop(): void {
    if (!started || typeof window === "undefined") {
        return;
    }
    started = false;
    window.removeEventListener("hashchange", onHashChange);
}

/**
 * Drop router state between tests.
 */
export function resetForTests(): void {
    stop();
    listeners.clear();
    navigationGuard = null;
    currentRoute = null;
    resolveToken = 0;
}

interface DynamicRouteRecord {
    name: string;
    path: string;
    meta?: { featureLoad?: () => Promise<unknown> };
    props?: Record<string, unknown>;
}

/**
 * vue-router shaped facade for callers that still accept a router object.
 * Only the members MeshChatX actually uses are implemented.
 */
export const router = {
    get currentRoute(): { value: ActiveRoute | null } {
        return { value: currentRoute };
    },
    push(target: RouteTarget | string): Promise<void> {
        return navigate(target);
    },
    replace(target: RouteTarget | string): Promise<void> {
        return navigate(target, { replace: true });
    },
    hasRoute(name: string): boolean {
        return listRoutes().some((entry) => entry.name === name);
    },
    addRoute(record: DynamicRouteRecord): void {
        const load = record.meta?.featureLoad;
        if (typeof load !== "function") {
            throw new Error(`hashRouter: addRoute("${record.name}") needs meta.featureLoad`);
        }
        registerRoute({
            name: record.name,
            path: record.path,
            mount: "svelte",
            load,
            meta: { ...(record.meta || {}) },
            routeProps: record.props && typeof record.props === "object" ? record.props : undefined,
        });
    },
    removeRoute(name: string): void {
        unregisterRoute(name);
    },
};

export default router;
