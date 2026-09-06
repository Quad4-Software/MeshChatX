// SPDX-License-Identifier: 0BSD

import { mount } from "svelte";
import DOMPurify from "dompurify";
import "./style.css";
import "./css/nomad-page-chrome.css";
import { injectMeshchatThemeVariables } from "./theme/designTokens.js";
import { initSvelteI18n, getCurrentUiLocale } from "./js/localeLoader.js";

injectMeshchatThemeVariables();

(window as unknown as Window & { DOMPurify: typeof DOMPurify }).DOMPurify = DOMPurify;
import "./fonts/RobotoMonoNerdFont/font.css";
import { startCodec2ScriptsBackgroundLoad } from "./js/Codec2Loader";
import { createApiClient } from "./js/apiClient.js";
import { fetchCsrfToken } from "./js/csrfToken.js";
import { registerCoreContributions } from "./js/registries/registerCoreContributions.js";
import { registerAllFeatures } from "./features/registerAllFeatures.js";
import { installWsEventBridge } from "./js/registries/wsEventBridge.js";
import { getCurrentRoute, navigate, router, setNavigationGuard, start as startHashRouter } from "./shell/hashRouter.js";
import { pluginHost } from "./js/plugins/PluginHost.js";
import GlobalState from "./js/GlobalState.js";
import { recoveryLocationForNetworkError } from "./js/networkRecovery.js";
import ElectronUtils from "./js/ElectronUtils.js";
import {
    decideControllerChangeReload,
    isIgnorableServiceWorkerRegistrationError,
    serviceWorkerRegisterOptions,
    shouldRegisterServiceWorker,
    unregisterServiceWorkersIfPresent,
} from "./js/pwa/swClientRegister.js";
import "./js/HeapMonitor.js";

registerCoreContributions();
registerAllFeatures();
installWsEventBridge();

import App from "./features/app-shell/App.svelte";
import enMessages from "./locales/en.json";

await initSvelteI18n(enMessages as Record<string, unknown>);

if (!window.location.hash || window.location.hash === "#") {
    history.replaceState(null, "", "#/messages");
}

pluginHost.attachRouter(router);

const apiClient = createApiClient({
    onAuthError() {
        GlobalState.authenticated = false;
        GlobalState.authEnabled = true;
        GlobalState.authSessionResolved = true;
        if (getCurrentRoute()?.name !== "auth") {
            void navigate("/auth");
        }
    },
});
(window as unknown as { api: typeof apiClient }).api = apiClient;

import { waitForMeshReady, waitForNetworkReady } from "./js/networkStartupWait.js";
import { resolveAuthNavigation } from "./js/authSessionSync.js";
import { reportFatalError } from "./js/fatalErrorState.js";
import { showBootSplashFatalError } from "./js/bootSplashError.js";

function setBootSplashLine(text: string): void {
    const splash = typeof document !== "undefined" ? document.getElementById("meshchatx-boot-splash") : null;
    const line = splash?.querySelector("[data-boot-line]");
    if (line && text) {
        line.textContent = text;
    }
}

function markBootSplashError(): void {
    const splash = typeof document !== "undefined" ? document.getElementById("meshchatx-boot-splash") : null;
    if (splash) {
        splash.setAttribute("data-state", "error");
    }
}

const networkReady = await waitForNetworkReady({
    onLine: setBootSplashLine,
    onErrorState: markBootSplashError,
    onDegraded: (error) => {
        GlobalState.networkDegraded = true;
        GlobalState.networkDegradedError = error || "RNS unavailable";
        GlobalState.networkStarting = false;
        GlobalState.networkReady = false;
    },
});
if (networkReady) {
    if (networkReady === "degraded") {
        GlobalState.networkDegraded = true;
        GlobalState.networkStarting = false;
        GlobalState.networkReady = false;
    } else if (networkReady === "ui") {
        GlobalState.networkStarting = true;
        GlobalState.networkReady = false;
    } else {
        GlobalState.networkStarting = false;
        GlobalState.networkReady = true;
    }
    try {
        const statusResponse = await apiClient.get("/api/v1/status");
        const statusData = statusResponse.data as { demo_mode?: boolean; is_loopback_bind?: boolean } | undefined;
        GlobalState.demoMode = !!statusData?.demo_mode;
        if (typeof statusData?.is_loopback_bind === "boolean") {
            GlobalState.isLoopbackBind = statusData.is_loopback_bind;
        }
    } catch {
        // status optional during early boot
    }
    if (GlobalState.demoMode) {
        try {
            const { DEMO_UI_LANGUAGE_STORAGE_KEY } = await import("./js/demoUiPrefs.js");
            const { setLocale } = await import("./js/localeLoader.js");
            const storedLang =
                typeof localStorage !== "undefined" ? localStorage.getItem(DEMO_UI_LANGUAGE_STORAGE_KEY) : null;
            if (storedLang) {
                await setLocale(null, storedLang);
            }
        } catch {
            // locale overlay optional
        }
    }
    try {
        await fetchCsrfToken(apiClient);
    } catch {
        // CSRF token will be retried on the next mutating request if needed.
    }

    setNavigationGuard(async (to) => {
        const decision = await resolveAuthNavigation(to, apiClient);
        if ("allow" in decision) {
            return { allow: true };
        }
        return { allow: false, redirect: decision.redirect };
    });

    function registerMeshchatServiceWorker(): void {
        if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) {
            return;
        }
        if (
            !shouldRegisterServiceWorker({
                isDev: import.meta.env.DEV,
                isElectron: ElectronUtils.isElectron(),
            })
        ) {
            void unregisterServiceWorkersIfPresent(navigator.serviceWorker);
            return;
        }
        let refreshing = false;
        const hadController = Boolean(navigator.serviceWorker.controller);
        navigator.serviceWorker.addEventListener("controllerchange", () => {
            const decision = decideControllerChangeReload({ hadController, refreshing });
            refreshing = decision.nextRefreshing;
            if (decision.shouldReload) {
                window.location.reload();
            }
        });
        navigator.serviceWorker
            .register("/service-worker.js", serviceWorkerRegisterOptions() as RegistrationOptions)
            .then((registration) => {
                const requestUpdate = () => {
                    try {
                        void registration.update();
                    } catch {
                        // ignore update failures
                    }
                };
                document.addEventListener("visibilitychange", () => {
                    if (document.visibilityState === "visible") {
                        requestUpdate();
                    }
                });
                requestUpdate();
            })
            .catch((error) => {
                if (isIgnorableServiceWorkerRegistrationError(error)) {
                    return;
                }
                console.debug("Service worker registration failed:", error);
            });
    }

    function removeBootSplash(splash: HTMLElement | null): void {
        if (!splash || !splash.isConnected) {
            return;
        }
        splash.setAttribute("aria-busy", "false");
        splash.style.transition = "opacity 140ms ease";
        splash.style.opacity = "0";
        window.setTimeout(() => {
            if (splash.isConnected) {
                splash.remove();
            }
        }, 160);
    }

    function preloadCriticalRouteChunks(): void {
        void import("./features/messages/MessagesPage.svelte");
        void import("./features/contacts/ContactsPage.svelte");
        void import("./features/interfaces/InterfacesPage.svelte");
    }

    function bootstrap(): void {
        registerMeshchatServiceWorker();
        const splash = typeof document !== "undefined" ? document.getElementById("meshchatx-boot-splash") : null;
        // Svelte has no app-level error handler. Only uncaught
        // exceptions carry event.error, so resource load failures stay silent.
        window.addEventListener("error", (event) => {
            if (!(event.error instanceof Error)) {
                return;
            }
            console.error("MeshChatX render error:", event.error);
            reportFatalError({
                kind: "frontend",
                message: event.error.message,
                stack: event.error.stack,
                context: "window",
            });
        });
        try {
            startHashRouter();
            const target = document.getElementById("app");
            if (!target) {
                throw new Error("missing #app mount target");
            }
            mount(App, { target });
        } catch (e) {
            const error = e as { message?: string; stack?: string };
            console.error("MeshChatX bootstrap failed:", e);
            showBootSplashFatalError({
                kind: "frontend",
                title: "Failed to start",
                message: "Failed to start. Try reloading the page.",
                details: error?.message ? String(error.message) : "",
                stack: error?.stack,
            });
            return;
        }
        try {
            const pendingRoute = localStorage.getItem("meshchatx_open_after_relaunch");
            if (pendingRoute) {
                localStorage.removeItem("meshchatx_open_after_relaunch");
                if (pendingRoute.startsWith("#/")) {
                    void router.replace(pendingRoute.slice(1));
                }
            }
        } catch {
            // ignore
        }
        // Keep splash until the first painted frame so WebView does not flash white.
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                removeBootSplash(splash);
            });
        });
        preloadCriticalRouteChunks();
        if (GlobalState.networkReady) {
            void startCodec2ScriptsBackgroundLoad();
            void loadPluginsIfEnabled();
        } else if (GlobalState.networkStarting) {
            void waitForMeshReady({
                onLine: () => {},
                onDegraded: (error) => {
                    GlobalState.networkDegraded = true;
                    GlobalState.networkDegradedError = error || "RNS unavailable";
                    GlobalState.networkStarting = false;
                    GlobalState.networkReady = false;
                },
            }).then((meshState) => {
                if (meshState === "ready") {
                    GlobalState.networkStarting = false;
                    GlobalState.networkReady = true;
                    GlobalState.networkDegraded = false;
                    GlobalState.networkDegradedError = null;
                    void startCodec2ScriptsBackgroundLoad();
                    void loadPluginsIfEnabled();
                } else if (meshState === "degraded") {
                    GlobalState.networkStarting = false;
                    GlobalState.networkReady = false;
                } else {
                    GlobalState.networkStarting = false;
                    GlobalState.networkReady = false;
                    GlobalState.networkDegraded = true;
                    GlobalState.networkDegradedError = GlobalState.networkDegradedError || "RNS startup timed out";
                }
            });
        }
        if (GlobalState.networkDegraded) {
            const recoveryLocation = recoveryLocationForNetworkError(GlobalState.networkDegradedError);
            if (recoveryLocation) {
                try {
                    router.replace(recoveryLocation);
                } catch {
                    // Route may not exist yet during early boot, but the banner still guides the user.
                }
            }
        }
    }

    async function loadPluginsIfEnabled(): Promise<void> {
        if (!(GlobalState.authenticated || !GlobalState.authEnabled)) {
            return;
        }
        try {
            const response = await apiClient.get("/api/v1/plugins");
            const pluginsData = response.data as { plugins_enabled?: boolean } | undefined;
            GlobalState.pluginsEnabled = pluginsData?.plugins_enabled !== false;
            if (!GlobalState.pluginsEnabled) {
                return;
            }
            await pluginHost.loadEnabledPlugins(apiClient, getCurrentUiLocale());
        } catch (error) {
            console.debug("Plugin host bootstrap failed:", error);
        }
    }

    bootstrap();
} else {
    const splash = typeof document !== "undefined" ? document.getElementById("meshchatx-boot-splash") : null;
    const line = splash?.querySelector("[data-boot-line]")?.textContent || "Network startup timed out. Try reloading.";
    showBootSplashFatalError({
        kind: "backend",
        title: "Backend unreachable",
        message: line,
        details: "The local MeshChatX backend did not become ready during startup.\nStatus endpoint: /api/v1/status",
    });
}
