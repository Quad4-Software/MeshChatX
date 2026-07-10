import { createApp } from "vue";
import { createRouter, createWebHashHistory } from "vue-router";
import { createI18n } from "vue-i18n";
import vClickOutside from "click-outside-vue3";
import DOMPurify from "dompurify";
import "./style.css";
import { injectMeshchatThemeVariables, vuetifyThemesFromTokens } from "./theme/designTokens.js";

injectMeshchatThemeVariables();

window.DOMPurify = DOMPurify;
import "@mdi/font/css/materialdesignicons.css";
import "./fonts/RobotoMonoNerdFont/font.css";
import { startCodec2ScriptsBackgroundLoad } from "./js/Codec2Loader";
import { createApiClient } from "./js/apiClient.js";
import { fetchCsrfToken } from "./js/csrfToken.js";
import { registerCoreContributions } from "./js/registries/registerCoreContributions.js";
import { installWsEventBridge } from "./js/registries/wsEventBridge.js";
import { pluginHost } from "./js/plugins/PluginHost.js";
import GlobalState from "./js/GlobalState.js";
import "./js/HeapMonitor.js";

registerCoreContributions();
installWsEventBridge();

import App from "./components/App.vue";
import ChangelogModal from "./components/ChangelogModal.vue";
import TutorialModal from "./components/TutorialModal.vue";

const localeModules = import.meta.glob("./locales/*.json", { eager: true });
const messages = {};
for (const filePath in localeModules) {
    const code = filePath.match(/\/([^/]+)\.json$/)[1];
    messages[code] = localeModules[filePath].default;
}

const i18n = createI18n({
    legacy: false,
    locale: "en",
    fallbackLocale: "en",
    messages,
});

// init vuetify
import { createVuetify } from "vuetify";
const vuetify = createVuetify({
    theme: {
        defaultTheme: "light",
        themes: vuetifyThemesFromTokens(),
    },
});

const router = createRouter({
    history: createWebHashHistory(),
    routes: [
        {
            name: "auth",
            path: "/auth",
            component: () => import("./components/auth/AuthPage.vue"),
        },
        {
            path: "/",
            redirect: "/messages",
        },
        {
            name: "about",
            path: "/about",
            component: () => import("./components/about/AboutPage.vue"),
        },
        {
            name: "interfaces",
            path: "/interfaces",
            component: () => import("./components/interfaces/InterfacesPage.vue"),
        },
        {
            name: "interfaces.add",
            path: "/interfaces/add",
            component: () => import("./components/interfaces/AddInterfacePage.vue"),
        },
        {
            name: "interfaces.edit",
            path: "/interfaces/edit",
            component: () => import("./components/interfaces/AddInterfacePage.vue"),
            props: {
                interface_name: String,
            },
        },
        {
            name: "messages",
            path: "/messages/:destinationHash?",
            props: true,
            meta: { stableKey: true },
            component: () => import("./components/messages/MessagesPage.vue"),
        },
        {
            name: "contacts",
            path: "/contacts",
            component: () => import("./components/contacts/ContactsPage.vue"),
        },
        {
            name: "map",
            path: "/map",
            meta: { keepAlive: true },
            component: () => import("./components/map/MapBrowser.vue"),
        },
        {
            name: "map-popout",
            path: "/popout/map",
            meta: { popoutType: "map", isPopout: true },
            component: () => import("./components/map/MapPage.vue"),
        },
        {
            name: "messages-popout",
            path: "/popout/messages/:destinationHash?",
            props: true,
            meta: { popoutType: "conversation", isPopout: true },
            component: () => import("./components/messages/MessagesPage.vue"),
        },
        {
            name: "network-visualiser",
            path: "/network-visualiser",
            component: () => import("./components/network-visualiser/NetworkVisualiserPage.vue"),
        },
        {
            name: "nomadnetwork",
            path: "/nomadnetwork/:destinationHash?",
            props: true,
            meta: { keepAlive: true },
            component: () => import("./components/nomadnetwork/NomadNetworkBrowser.vue"),
        },
        {
            name: "relay-chat",
            path: "/relay-chat",
            component: () => import("./components/relay/RelayChatPage.vue"),
        },
        {
            name: "relay-chat-popout",
            path: "/popout/relay-chat/:hubHash/:room?",
            props: true,
            meta: { popoutType: "relay", isPopout: true },
            component: () => import("./components/relay/RelayChatPage.vue"),
        },
        {
            name: "archives",
            path: "/archives",
            component: () => import("./components/archives/ArchivesPage.vue"),
        },
        {
            name: "nomadnetwork-popout",
            path: "/popout/nomadnetwork/:destinationHash?",
            props: true,
            meta: { popoutType: "nomad", isPopout: true },
            component: () => import("./components/nomadnetwork/NomadNetworkPage.vue"),
        },
        {
            name: "propagation-nodes",
            path: "/propagation-nodes",
            component: () => import("./components/propagation-nodes/PropagationNodesPage.vue"),
        },
        {
            name: "ping",
            path: "/ping",
            component: () => import("./components/ping/PingPage.vue"),
        },
        {
            name: "rncp",
            path: "/rncp",
            component: () => import("./components/rncp/RNCPPage.vue"),
        },
        {
            name: "rnsh",
            path: "/rnsh",
            component: () => import("./components/tools/RNSHManagerPage.vue"),
        },
        {
            name: "rnstatus",
            path: "/rnstatus",
            component: () => import("./components/rnstatus/RNStatusPage.vue"),
        },
        {
            name: "rnpath",
            path: "/rnpath",
            component: () => import("./components/tools/RNPathPage.vue"),
        },
        {
            name: "rnpath-trace",
            path: "/rnpath-trace",
            component: () => import("./components/tools/RNPathTracePage.vue"),
        },
        {
            name: "rnprobe",
            path: "/rnprobe",
            component: () => import("./components/rnprobe/RNProbePage.vue"),
        },
        {
            name: "translator",
            path: "/translator",
            component: () => import("./components/translator/TranslatorPage.vue"),
        },
        {
            name: "bots",
            path: "/bots",
            component: () => import("./components/tools/BotsPage.vue"),
        },
        {
            name: "forwarder",
            path: "/forwarder",
            component: () => import("./components/forwarder/ForwarderPage.vue"),
        },
        {
            name: "micron-editor",
            path: "/micron-editor",
            component: () => import("./components/micron-editor/MicronEditorPage.vue"),
        },
        {
            name: "reticulum-config-editor",
            path: "/tools/reticulum-config-editor",
            component: () => import("./components/tools/ReticulumConfigEditorPage.vue"),
        },
        {
            name: "mesh-server",
            path: "/mesh-server",
            component: () => import("./components/page-nodes/PageNodesPage.vue"),
        },
        {
            name: "documentation",
            path: "/documentation",
            component: () => import("./components/docs/DocsPage.vue"),
        },
        {
            name: "profile.icon",
            path: "/profile/icon",
            component: () => import("./components/profile/ProfileIconPage.vue"),
        },
        {
            name: "settings",
            path: "/settings",
            component: () => import("./components/settings/SettingsPage.vue"),
        },
        {
            name: "identities",
            path: "/identities",
            component: () => import("./components/settings/IdentitiesPage.vue"),
        },
        {
            name: "blocked",
            path: "/blocked",
            component: () => import("./components/blocked/BlockedPage.vue"),
        },
        {
            name: "tools",
            path: "/tools",
            component: () => import("./components/tools/ToolsPage.vue"),
        },
        {
            name: "licenses",
            path: "/licenses",
            component: () => import("./components/licenses/LicensesPage.vue"),
        },
        {
            name: "paper-message",
            path: "/tools/paper-message",
            component: () => import("./components/tools/PaperMessagePage.vue"),
        },
        {
            name: "sieve-filters",
            path: "/tools/sieve-filters",
            component: () => import("./components/tools/SieveFiltersPage.vue"),
        },
        {
            name: "message-blocklist",
            path: "/tools/message-blocklist",
            component: () => import("./components/tools/MessageBlocklistPage.vue"),
        },
        {
            name: "rnode-flasher",
            path: "/tools/rnode-flasher",
            component: () => import("./components/tools/RNodeFlasherPage.vue"),
        },
        {
            name: "repository-server",
            path: "/tools/repository-server",
            component: () => import("./components/tools/RepositoryServerPage.vue"),
        },
        {
            name: "debug-logs",
            path: "/debug/logs",
            component: () => import("./components/debug/DebugLogsPage.vue"),
        },
        {
            name: "call",
            path: "/call",
            component: () => import("./components/call/CallPage.vue"),
        },
        {
            name: "call-popout",
            path: "/popout/call",
            meta: { isPopout: true },
            component: () => import("./components/call/CallPage.vue"),
        },
        {
            name: "plugin-mcx-bugs",
            path: "/plugins/com.meshchatx.mcx-bugs",
            component: () => import("./components/plugins/PluginPage.vue"),
            props: { pluginId: "com.meshchatx.mcx-bugs" },
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

window.api = createApiClient({
    onAuthError() {
        if (router.currentRoute.value.name !== "auth") {
            GlobalState.authenticated = false;
            router.push("/auth");
        }
    },
});

import { waitForNetworkReady } from "./js/networkStartupWait.js";

function setBootSplashLine(text) {
    const splash = typeof document !== "undefined" ? document.getElementById("meshchatx-boot-splash") : null;
    const line = splash?.querySelector("[data-boot-line]");
    if (line && text) {
        line.textContent = text;
    }
}

function markBootSplashError() {
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
        GlobalState.networkDegradedError = error || "Mesh network unavailable";
    },
});
if (networkReady) {
    if (networkReady === "degraded") {
        GlobalState.networkDegraded = true;
    }
    try {
        await fetchCsrfToken(window.api);
    } catch {
        // CSRF token will be retried on the next mutating request if needed.
    }

    router.beforeEach(async (to, from, next) => {
        try {
            const response = await window.api.get("/api/v1/auth/status");
            const status = response.data;
            GlobalState.authEnabled = !!status.auth_enabled;
            GlobalState.authenticated = !!status.authenticated;
            GlobalState.authSessionResolved = true;

            if (!status.auth_enabled) {
                next();
                return;
            }

            if (status.authenticated) {
                if (to.name === "auth") {
                    next("/");
                } else {
                    next();
                }
                return;
            }

            if (to.name === "auth") {
                next();
                return;
            }

            next("/auth");
        } catch (e) {
            GlobalState.authSessionResolved = true;
            if (e.response?.status === 401 || e.response?.status === 403) {
                GlobalState.authenticated = false;
                next("/auth");
            } else {
                next();
            }
        }
    });

    function registerMeshchatServiceWorker() {
        if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) {
            return;
        }
        navigator.serviceWorker.register("/service-worker.js").catch((error) => {
            const errorMessage = error.message || "";
            const errorName = error.name || "";
            if (
                errorName === "SecurityError" ||
                errorMessage.includes("SSL certificate") ||
                errorMessage.includes("certificate")
            ) {
                return;
            }
            console.debug("Service worker registration failed:", error);
        });
    }

    function removeBootSplash(splash) {
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

    function preloadCriticalRouteChunks() {
        void import("./components/messages/MessagesPage.vue");
        void import("./components/contacts/ContactsPage.vue");
        void import("./components/interfaces/InterfacesPage.vue");
    }

    function bootstrap() {
        registerMeshchatServiceWorker();
        const splash = typeof document !== "undefined" ? document.getElementById("meshchatx-boot-splash") : null;
        try {
            createApp(App).use(router).use(vuetify).use(i18n).use(vClickOutside).mount("#app");
        } catch (e) {
            console.error("MeshChatX bootstrap failed:", e);
            if (splash) {
                splash.setAttribute("data-state", "error");
                const line = splash.querySelector("[data-boot-line]");
                if (line) {
                    line.textContent = "Failed to start. Try closing and reopening the app.";
                }
            }
            return;
        }
        // Keep splash until the first painted frame so WebView does not flash white.
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                removeBootSplash(splash);
            });
        });
        preloadCriticalRouteChunks();
        void startCodec2ScriptsBackgroundLoad();
        void loadPluginsIfEnabled();
        if (GlobalState.networkDegraded) {
            try {
                router.replace({ name: "interfaces" });
            } catch {
                // Route may not exist yet during early boot; banner still guides the user.
            }
        }
    }

    async function loadPluginsIfEnabled() {
        if (!(GlobalState.authenticated || !GlobalState.authEnabled)) {
            return;
        }
        try {
            const response = await window.api.get("/api/v1/plugins");
            GlobalState.pluginsEnabled = response.data?.plugins_enabled !== false;
            if (!GlobalState.pluginsEnabled) {
                return;
            }
            await pluginHost.loadEnabledPlugins(window.api, i18n.global.locale.value);
        } catch (error) {
            console.debug("Plugin host bootstrap failed:", error);
        }
    }

    bootstrap();
}
