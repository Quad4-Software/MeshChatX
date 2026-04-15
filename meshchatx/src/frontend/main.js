import { createApp, defineAsyncComponent } from "vue";
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
import { ensureCodec2ScriptsLoaded } from "./js/Codec2Loader";
import { createApiClient } from "./js/apiClient.js";

import App from "./components/App.vue";
import ChangelogModal from "./components/ChangelogModal.vue";
import TutorialModal from "./components/TutorialModal.vue";
import GlobalState from "./js/GlobalState";

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
            component: defineAsyncComponent(() => import("./components/auth/AuthPage.vue")),
        },
        {
            path: "/",
            redirect: "/messages",
        },
        {
            name: "about",
            path: "/about",
            component: defineAsyncComponent(() => import("./components/about/AboutPage.vue")),
        },
        {
            name: "interfaces",
            path: "/interfaces",
            component: defineAsyncComponent(() => import("./components/interfaces/InterfacesPage.vue")),
        },
        {
            name: "interfaces.add",
            path: "/interfaces/add",
            component: defineAsyncComponent(() => import("./components/interfaces/AddInterfacePage.vue")),
        },
        {
            name: "interfaces.edit",
            path: "/interfaces/edit",
            component: defineAsyncComponent(() => import("./components/interfaces/AddInterfacePage.vue")),
            props: {
                interface_name: String,
            },
        },
        {
            name: "messages",
            path: "/messages/:destinationHash?",
            props: true,
            component: defineAsyncComponent(() => import("./components/messages/MessagesPage.vue")),
        },
        {
            name: "contacts",
            path: "/contacts",
            component: defineAsyncComponent(() => import("./components/contacts/ContactsPage.vue")),
        },
        {
            name: "map",
            path: "/map",
            component: defineAsyncComponent(() => import("./components/map/MapPage.vue")),
        },
        {
            name: "map-popout",
            path: "/popout/map",
            meta: { popoutType: "map", isPopout: true },
            component: defineAsyncComponent(() => import("./components/map/MapPage.vue")),
        },
        {
            name: "messages-popout",
            path: "/popout/messages/:destinationHash?",
            props: true,
            meta: { popoutType: "conversation", isPopout: true },
            component: defineAsyncComponent(() => import("./components/messages/MessagesPage.vue")),
        },
        {
            name: "network-visualiser",
            path: "/network-visualiser",
            component: defineAsyncComponent(() => import("./components/network-visualiser/NetworkVisualiserPage.vue")),
        },
        {
            name: "nomadnetwork",
            path: "/nomadnetwork/:destinationHash?",
            props: true,
            component: defineAsyncComponent(() => import("./components/nomadnetwork/NomadNetworkPage.vue")),
        },
        {
            name: "archives",
            path: "/archives",
            component: defineAsyncComponent(() => import("./components/archives/ArchivesPage.vue")),
        },
        {
            name: "nomadnetwork-popout",
            path: "/popout/nomadnetwork/:destinationHash?",
            props: true,
            meta: { popoutType: "nomad", isPopout: true },
            component: defineAsyncComponent(() => import("./components/nomadnetwork/NomadNetworkPage.vue")),
        },
        {
            name: "propagation-nodes",
            path: "/propagation-nodes",
            component: defineAsyncComponent(() => import("./components/propagation-nodes/PropagationNodesPage.vue")),
        },
        {
            name: "ping",
            path: "/ping",
            component: defineAsyncComponent(() => import("./components/ping/PingPage.vue")),
        },
        {
            name: "rncp",
            path: "/rncp",
            component: defineAsyncComponent(() => import("./components/rncp/RNCPPage.vue")),
        },
        {
            name: "rnstatus",
            path: "/rnstatus",
            component: defineAsyncComponent(() => import("./components/rnstatus/RNStatusPage.vue")),
        },
        {
            name: "rnpath",
            path: "/rnpath",
            component: defineAsyncComponent(() => import("./components/tools/RNPathPage.vue")),
        },
        {
            name: "rnpath-trace",
            path: "/rnpath-trace",
            component: defineAsyncComponent(() => import("./components/tools/RNPathTracePage.vue")),
        },
        {
            name: "rnprobe",
            path: "/rnprobe",
            component: defineAsyncComponent(() => import("./components/rnprobe/RNProbePage.vue")),
        },
        {
            name: "translator",
            path: "/translator",
            component: defineAsyncComponent(() => import("./components/translator/TranslatorPage.vue")),
        },
        {
            name: "bots",
            path: "/bots",
            component: defineAsyncComponent(() => import("./components/tools/BotsPage.vue")),
        },
        {
            name: "forwarder",
            path: "/forwarder",
            component: defineAsyncComponent(() => import("./components/forwarder/ForwarderPage.vue")),
        },
        {
            name: "micron-editor",
            path: "/micron-editor",
            component: defineAsyncComponent(() => import("./components/micron-editor/MicronEditorPage.vue")),
        },
        {
            name: "mesh-server",
            path: "/mesh-server",
            component: defineAsyncComponent(() => import("./components/page-nodes/PageNodesPage.vue")),
        },
        {
            name: "documentation",
            path: "/documentation",
            component: defineAsyncComponent(() => import("./components/docs/DocsPage.vue")),
        },
        {
            name: "profile.icon",
            path: "/profile/icon",
            component: defineAsyncComponent(() => import("./components/profile/ProfileIconPage.vue")),
        },
        {
            name: "settings",
            path: "/settings",
            component: defineAsyncComponent(() => import("./components/settings/SettingsPage.vue")),
        },
        {
            name: "identities",
            path: "/identities",
            component: defineAsyncComponent(() => import("./components/settings/IdentitiesPage.vue")),
        },
        {
            name: "blocked",
            path: "/blocked",
            component: defineAsyncComponent(() => import("./components/blocked/BlockedPage.vue")),
        },
        {
            name: "tools",
            path: "/tools",
            component: defineAsyncComponent(() => import("./components/tools/ToolsPage.vue")),
        },
        {
            name: "licenses",
            path: "/licenses",
            component: defineAsyncComponent(() => import("./components/licenses/LicensesPage.vue")),
        },
        {
            name: "paper-message",
            path: "/tools/paper-message",
            component: defineAsyncComponent(() => import("./components/tools/PaperMessagePage.vue")),
        },
        {
            name: "rnode-flasher",
            path: "/tools/rnode-flasher",
            component: defineAsyncComponent(() => import("./components/tools/RNodeFlasherPage.vue")),
        },
        {
            name: "debug-logs",
            path: "/debug/logs",
            component: defineAsyncComponent(() => import("./components/debug/DebugLogsPage.vue")),
        },
        {
            name: "call",
            path: "/call",
            component: defineAsyncComponent(() => import("./components/call/CallPage.vue")),
        },
        {
            name: "call-popout",
            path: "/popout/call",
            meta: { isPopout: true },
            component: defineAsyncComponent(() => import("./components/call/CallPage.vue")),
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

async function bootstrap() {
    await ensureCodec2ScriptsLoaded();
    createApp(App).use(router).use(vuetify).use(i18n).use(vClickOutside).mount("#app");
}

bootstrap();
