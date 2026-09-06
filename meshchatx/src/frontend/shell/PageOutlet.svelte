<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /**
     * Mounts the Svelte feature page for the active hashRouter route.
     * Routes with meta.keepAlive keep their container in the DOM, hidden, so
     * the page keeps its state across navigation.
     * Routes with meta.stableKey keep one mount and receive prop updates
     * (conversation switches) without tearing down the page.
     */
    import { mount, onDestroy, unmount, untrack } from "svelte";
    import { getCurrentRoute, subscribe } from "./hashRouter.js";
    import type { ActiveRoute } from "./hashRouter.js";
    import { pageOutletMountKey } from "./pageOutletMountKey.js";

    const CONTAINER_CLASS = "feature-page-host flex flex-1 min-h-0 h-full min-w-0 w-full overflow-hidden bg-sem-canvas";

    interface MountedPage {
        container: HTMLElement;
        app: Record<string, unknown> | null;
        key: string;
        props: Record<string, unknown>;
    }

    let root: HTMLDivElement | undefined = $state();

    const keepAliveCache = new Map<string, MountedPage>();
    let transient: MountedPage | null = null;
    let renderGeneration = 0;
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

    // Track only route + root. render() syncs $state page props; that must stay
    // untracked or stableKey/keepAlive updates re-enter this effect forever
    // (effect_update_depth_exceeded) and leave the outlet stuck on the prior page.
    $effect(() => {
        const route = pendingRoute;
        if (!root) {
            return;
        }
        untrack(() => {
            void render(route);
        });
    });

    function pageProps(route: ActiveRoute): Record<string, unknown> {
        return {
            ...route.routeProps,
            ...route.params,
            routeQuery: { ...route.query },
        };
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

    async function mountPage(page: MountedPage, route: ActiveRoute, generation: number): Promise<void> {
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
        if (generation !== renderGeneration) {
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
        const generation = ++renderGeneration;
        if (!route || !route.matched) {
            destroyPage(transient);
            transient = null;
            hideCachedExcept("");
            return;
        }

        const key = pageOutletMountKey(route);
        const nextProps = pageProps(route);

        if (route.meta?.keepAlive) {
            destroyPage(transient);
            transient = null;
            hideCachedExcept(route.name);

            let entry = keepAliveCache.get(route.name) ?? null;
            if (entry && entry.key === key) {
                syncProps(entry, nextProps);
                if (!entry.container.isConnected) {
                    // eslint-disable-next-line svelte/no-dom-manipulating -- keepAlive host reattach
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
                // eslint-disable-next-line svelte/no-dom-manipulating -- keepAlive host attach
                root.appendChild(entry.container);
            }
            entry.container.style.display = "";
            try {
                await mountPage(entry, route, generation);
            } catch (error) {
                console.error("PageOutlet: keepAlive mount failed", route.name, error);
            }
            return;
        }

        hideCachedExcept("");
        if (transient && transient.key === key) {
            syncProps(transient, nextProps);
            return;
        }

        // Keep the previous page painted until the next mount finishes so async
        // chunk loads do not flash an empty (often light) canvas in dark mode.
        // Do not claim `transient` until mount succeeds so a superseded load can
        // discard itself without ripping out the still-visible previous page.
        const page: MountedPage = {
            container: newContainer(),
            app: null,
            key,
            props: createProps(nextProps),
        };
        page.container.style.position = "absolute";
        page.container.style.inset = "0";
        page.container.style.visibility = "hidden";
        page.container.setAttribute("aria-hidden", "true");
        // eslint-disable-next-line svelte/no-dom-manipulating -- PageOutlet mounts feature hosts
        root.appendChild(page.container);
        try {
            await mountPage(page, route, generation);
        } catch (error) {
            console.error("PageOutlet: mount failed", route.name, error);
            destroyPage(page);
            return;
        }
        if (generation !== renderGeneration) {
            destroyPage(page);
            return;
        }
        if (!page.app) {
            destroyPage(page);
            return;
        }
        const prev = transient;
        transient = page;
        if (prev && prev !== page) {
            destroyPage(prev);
        }
        page.container.style.position = "";
        page.container.style.inset = "";
        page.container.style.visibility = "";
        page.container.removeAttribute("aria-hidden");
    }
</script>

<div bind:this={root} class="relative flex flex-1 min-h-0 h-full min-w-0 w-full overflow-hidden bg-sem-canvas"></div>
