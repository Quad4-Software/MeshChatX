<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Mounts the Svelte feature page for the active hashRouter route.
     * Routes with meta.keepAlive keep their container in the DOM, hidden, so
     * the page keeps its state across navigation the way Vue KeepAlive did.
     */
    import { mount, onDestroy, unmount } from "svelte";
    import { getCurrentRoute, subscribe } from "./hashRouter.js";
    import type { ActiveRoute } from "./hashRouter.js";

    const CONTAINER_CLASS =
        "feature-page-host flex flex-1 min-h-0 h-full min-w-0 w-full overflow-hidden bg-sem-canvas";

    interface MountedPage {
        container: HTMLElement;
        app: Record<string, unknown> | null;
        key: string;
        props: Record<string, unknown>;
    }

    let root: HTMLDivElement | undefined = $state();

    const keepAliveCache = new Map<string, MountedPage>();
    let transient: MountedPage | null = null;
    let renderToken = 0;
    let pendingRoute = $state<ActiveRoute | null>(getCurrentRoute());

    const unsubscribe = subscribe((route) => {
        pendingRoute = route;
    });

    onDestroy(() => {
        unsubscribe();
        destroyPage(transient);
        transient = null;
        for (const entry of keepAliveCache.values()) {
            destroyPage(entry);
        }
        keepAliveCache.clear();
    });

    $effect(() => {
        const route = pendingRoute;
        if (!root) {
            return;
        }
        void render(route);
    });

    function pageProps(route: ActiveRoute): Record<string, unknown> {
        return {
            ...route.routeProps,
            ...route.params,
            routeQuery: { ...route.query },
        };
    }

    /**
     * Remount identity. Mirrors the old Vue keying: keepAlive and stableKey
     * routes remount only on param change, everything else on full path change.
     */
    function mountKeyFor(route: ActiveRoute): string {
        if (route.meta?.keepAlive || route.meta?.stableKey) {
            return `${route.name}:${JSON.stringify(route.params)}`;
        }
        return `${route.name}:${route.fullPath}`;
    }

    function createProps(initial: Record<string, unknown>): Record<string, unknown> {
        const props = $state({ ...initial });
        return props;
    }

    function destroyPage(page: MountedPage | null): void {
        if (!page) {
            return;
        }
        if (page.app) {
            try {
                unmount(page.app);
            } catch {
                /* already gone */
            }
            page.app = null;
        }
        page.container.remove();
    }

    function syncProps(page: MountedPage, next: Record<string, unknown>): void {
        for (const key of Object.keys(page.props)) {
            if (!(key in next)) {
                delete page.props[key];
            }
        }
        Object.assign(page.props, next);
    }

    function hideCachedExcept(activeName: string): void {
        for (const [name, entry] of keepAliveCache.entries()) {
            entry.container.style.display = name === activeName ? "" : "none";
        }
    }

    function newContainer(): HTMLElement {
        const container = document.createElement("div");
        container.className = CONTAINER_CLASS;
        return container;
    }

    async function mountPage(page: MountedPage, route: ActiveRoute, token: number): Promise<void> {
        const load = route.featureLoad;
        if (typeof load !== "function") {
            console.error("PageOutlet: route has no featureLoad", route.name);
            return;
        }
        if (route.mount !== "svelte") {
            console.error("PageOutlet: only svelte routes are supported", route.name, route.mount);
            return;
        }
        const module = await load();
        if (token !== renderToken) {
            return;
        }
        const resolved = module as { default?: unknown } | null;
        const Component = resolved && typeof resolved === "object" && "default" in resolved ? resolved.default : module;
        if (!Component) {
            console.error("PageOutlet: load() returned no default export", route.name);
            return;
        }
        page.app = mount(Component as Parameters<typeof mount>[0], {
            target: page.container,
            props: page.props,
        }) as Record<string, unknown>;
    }

    async function render(route: ActiveRoute | null): Promise<void> {
        if (!root) {
            return;
        }
        const token = ++renderToken;
        if (!route || !route.matched) {
            destroyPage(transient);
            transient = null;
            hideCachedExcept("");
            return;
        }

        const key = mountKeyFor(route);
        const nextProps = pageProps(route);

        if (route.meta?.keepAlive) {
            destroyPage(transient);
            transient = null;
            hideCachedExcept(route.name);

            let entry = keepAliveCache.get(route.name) ?? null;
            if (entry && entry.key === key) {
                syncProps(entry, nextProps);
                if (!entry.container.isConnected) {
                    root.appendChild(entry.container);
                }
                entry.container.style.display = "";
                return;
            }
            if (entry) {
                if (entry.app) {
                    try {
                        unmount(entry.app);
                    } catch {
                        /* already gone */
                    }
                    entry.app = null;
                }
                entry.container.replaceChildren();
                entry.key = key;
                syncProps(entry, nextProps);
            } else {
                entry = {
                    container: newContainer(),
                    app: null,
                    key,
                    props: createProps(nextProps),
                };
                keepAliveCache.set(route.name, entry);
            }
            if (!entry.container.isConnected) {
                root.appendChild(entry.container);
            }
            entry.container.style.display = "";
            await mountPage(entry, route, token);
            return;
        }

        hideCachedExcept("");
        if (transient && transient.key === key) {
            syncProps(transient, nextProps);
            return;
        }
        destroyPage(transient);
        const page: MountedPage = {
            container: newContainer(),
            app: null,
            key,
            props: createProps(nextProps),
        };
        transient = page;
        root.appendChild(page.container);
        await mountPage(page, route, token);
        if (token !== renderToken && transient === page) {
            destroyPage(page);
            transient = null;
        }
    }
</script>

<div bind:this={root} class="flex flex-1 min-h-0 h-full min-w-0 w-full overflow-hidden"></div>
