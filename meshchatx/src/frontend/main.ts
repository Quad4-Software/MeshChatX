// SPDX-License-Identifier: 0BSD

import { createApp } from "vue";
import { createRouter, createWebHashHistory } from "vue-router";
import { createI18n } from "vue-i18n";
import vClickOutside from "./libs/clickOutside.js";
import DOMPurify from "dompurify";
import "./style.css";
import "./css/nomad-page-chrome.css";
import { injectMeshchatThemeVariables } from "./theme/designTokens.js";
import { registerUiI18n } from "./js/localeLoader.js";
import { registerTranslator, registerFallbackMessages } from "./js/i18n.js";

injectMeshchatThemeVariables();

(window as unknown as Window & { DOMPurify: typeof DOMPurify }).DOMPurify = DOMPurify;
import "./fonts/RobotoMonoNerdFont/font.css";
import { startCodec2ScriptsBackgroundLoad } from "./js/Codec2Loader";
import { createApiClient } from "./js/apiClient.js";
import { fetchCsrfToken } from "./js/csrfToken.js";
import { registerCoreContributions } from "./js/registries/registerCoreContributions.js";
import { registerAllFeatures } from "./features/registerAllFeatures.js";
import { installWsEventBridge } from "./js/registries/wsEventBridge.js";
import { buildRouterRoutesFromRegistry } from "./shell/buildRouterRoutes.js";
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

import App from "./components/App.vue";
import ChangelogModal from "./components/ChangelogModal.vue";
import TutorialModal from "./components/TutorialModal.vue";
import enMessages from "./locales/en.json";

const i18n = createI18n({
    legacy: false,
    locale: "en",
    fallbackLocale: "en",
    messages: {
        en: enMessages,
    },
});
registerUiI18n(i18n);
registerFallbackMessages(enMessages);
registerTranslator((key, values) => i18n.global.t(key, values));

if (!window.location.hash || window.location.hash === "#") {
    history.replaceState(null, "", "#/messages");
}

const router = createRouter({
    history: createWebHashHistory(),
    routes: [
        ...buildRouterRoutesFromRegistry(),
        {
            path: "/",
            redirect: "/messages",
        },
        {
            name: "changelog",
            path: "/changelog",
            component: ChangelogModal,
            meta: { isPage: true },
        },
        {
            name: "tutorial",
            path: "/tutorial",
            component: TutorialModal,
            meta: { isPage: true },
        },
    ],
});

pluginHost.attachRouter(router);

const apiClient = createApiClient({
    onAuthError() {
        GlobalState.authenticated = false;
        GlobalState.authEnabled = true;
        GlobalState.authSessionResolved = true;
        if (router.currentRoute.value.name !== "auth") {
            router.push("/auth");
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
                await setLocale(i18n, storedLang);
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

    router.beforeEach(async (to, _from, next) => {
        const decision = await resolveAuthNavigation(to, apiClient);
        if (decision.allow) {
            next();
            return;
        }
        next(decision.redirect);
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
        const app = createApp(App);
        app.config.errorHandler = (err, _instance, info) => {
            console.error("MeshChatX render error:", err, info);
            const renderError = err instanceof Error ? err : new Error(String(err));
            reportFatalError({
                kind: "frontend",
                message: renderError.message,
                stack: renderError.stack,
                context: typeof info === "string" ? info : "",
            });
        };
        router.onError((error) => {
            console.error("MeshChatX router error:", error);
            reportFatalError({
                kind: "frontend",
                message: error?.message || String(error),
                stack: error?.stack,
                context: "router",
            });
        });
        try {
            app.use(router).use(i18n).use(vClickOutside).mount("#app");
        } catch (e) {
            console.error("MeshChatX bootstrap failed:", e);
            showBootSplashFatalError({
                kind: "frontend",
                title: "Failed to start",
                message: "Failed to start. Try reloading the page.",
                details: e?.message ? String(e.message) : "",
                stack: e?.stack,
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
            await pluginHost.loadEnabledPlugins(apiClient, i18n.global.locale.value);
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
