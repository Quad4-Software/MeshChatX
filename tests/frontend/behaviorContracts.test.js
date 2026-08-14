import { readFileSync, readdirSync, statSync } from "fs";
import { join } from "path";
import { describe, it, expect } from "vitest";

function readSource(relativePath) {
    return readFileSync(join(process.cwd(), relativePath), "utf8");
}

function readSources(relativePaths) {
    return relativePaths.map((p) => readSource(p)).join("\n");
}

describe("behavior contracts: user-visible wiring must stay connected", () => {
    describe("cancel send", () => {
        it("ConversationMessageEntry exposes cancel for in-flight outbound messages", () => {
            const src = readSource("meshchatx/src/frontend/components/messages/ConversationMessageEntry.vue");
            expect(src).toContain("canCancelOutboundSend");
            expect(src).toContain("cancelSendingMessage");
            expect(src).toContain("messages.cancel_send");
        });

        it("ConversationViewer implements cancelSendingMessage and canCancelOutboundSend", () => {
            const src = readSource("meshchatx/src/frontend/components/messages/ConversationViewer.vue");
            expect(src).toContain("async cancelSendingMessage(");
            expect(src).toContain("canCancelOutboundSend(");
            expect(src).toContain("/lxmf-messages/${");
            expect(src).toContain("/cancel");
            expect(src).toContain("_outboundQueue.cancelJob");
        });

        it("outbound send jobs carry a cancelKey for queue cancellation", () => {
            const src = readSource("meshchatx/src/frontend/components/messages/ConversationViewer.vue");
            expect(src).toContain("cancelKey:");
            expect(src).toContain("job.cancelled");
        });
    });

    describe("downloads", () => {
        const downloadSurfaces = [
            ["AboutPage.vue", "meshchatx/src/frontend/components/about/AboutPage.vue"],
            ["IdentitiesPage.vue", "meshchatx/src/frontend/components/settings/IdentitiesPage.vue"],
            ["ConversationViewer.vue", "meshchatx/src/frontend/components/messages/ConversationViewer.vue"],
        ];

        it.each(downloadSurfaces)("%s routes saves through DownloadUtils", (_, relativePath) => {
            const src = readSource(relativePath);
            expect(src).toContain("DownloadUtils");
        });

        it("backup and identity exports do not use browser-only anchor downloads", () => {
            for (const relativePath of [
                "meshchatx/src/frontend/components/about/AboutPage.vue",
                "meshchatx/src/frontend/components/settings/IdentitiesPage.vue",
            ]) {
                const src = readSource(relativePath);
                expect(src).not.toMatch(/link\.setAttribute\(\s*["']download["']/);
                expect(src).not.toMatch(/link\.click\(\)/);
                expect(src).not.toMatch(/createObjectURL\(/);
            }
        });

        it("chat file attachments do not rely on WebView-unfriendly anchor downloads", () => {
            const src = readSource("meshchatx/src/frontend/components/messages/ConversationMessageEntry.vue");
            expect(src).toContain("downloadLxmfFileAttachment");
            expect(src).not.toMatch(/:download\s*=\s*["']file_attachment\.file_name["']/);
            expect(src).not.toMatch(/\/attachment\/\$\{chatItem\.lxmf_message\.hash\}\/file\?file_index=\$\{index\}/);
        });

        it("DownloadUtils supports Android bridge and browser fallback", () => {
            const src = readSource("meshchatx/src/frontend/js/DownloadUtils.js");
            expect(src).toContain("MeshChatXAndroid");
            expect(src).toContain("saveDownload");
            expect(src).toContain("_triggerBrowserDownload");
            expect(src).toContain("downloadFromApiResponse");
        });

        it("Android MainActivity wires WebView downloads and the JS save bridge", () => {
            const src = readSource("android/app/src/main/java/com/meshchatx/MainActivity.java");
            expect(src).toContain("setDownloadListener");
            expect(src).toContain("saveDownload");
            expect(src).toContain("persistMeshchatDownload");
            expect(src).toContain("MeshChatXAndroidBridge");
        });

        it("Android MainActivity supports opt-in screenshot and clipboard privacy", () => {
            const src = readSource("android/app/src/main/java/com/meshchatx/MainActivity.java");
            expect(src).toContain("FLAG_SECURE");
            expect(src).toContain("PREF_BLOCK_SCREENSHOTS");
            expect(src).toContain("setBlockScreenshots");
            expect(src).toContain("PREF_CLEAR_CLIPBOARD_ON_BACKGROUND");
            expect(src).toContain("setClearClipboardOnBackground");
            expect(src).toContain("setFilterTouchesWhenObscured");
            expect(src).toMatch(/getBoolean\(\s*PREF_BLOCK_SCREENSHOTS\s*,\s*false\s*\)/);
            expect(src).toMatch(/getBoolean\(\s*PREF_CLEAR_CLIPBOARD_ON_BACKGROUND\s*,\s*false\s*\)/);
        });

        it("Android MainActivity supports configurable remote backend URL", () => {
            const src = readSource("android/app/src/main/java/com/meshchatx/MainActivity.java");
            expect(src).toContain("PREF_REMOTE_BACKEND_URL");
            expect(src).toContain("setRemoteBackendUrlAndRestart");
            expect(src).toContain("isRemoteBackendMode");
            expect(src).toContain("offerSwitchToLocalBackend");
            const util = readSource("android/app/src/main/java/com/meshchatx/RemoteBackendUrl.java");
            expect(util).toContain("normalize");
            expect(util).toContain("LOCAL_BACKEND_URL");
            expect(util).toContain("isAllowedShellNavigation");
            expect(src).toContain("isAllowedShellNavigation");
        });

        it("SettingsPage deep-scopes shared toggle styles for extracted sections", () => {
            const src = readSource("meshchatx/src/frontend/components/settings/SettingsPage.vue");
            expect(src).toContain(":deep(.setting-toggle)");
            expect(src).toContain(":deep(.setting-toggle__label)");
            expect(src).toContain(":deep(.setting-toggle__title)");
        });

        it("Docker runtime images install libseccomp for Seccomp-BPF", () => {
            const alpine = readSource("scripts/docker/runtime-setup.sh");
            const chainguard = readSource("scripts/docker/runtime-setup-chainguard.sh");
            expect(alpine).toMatch(/apk add[^\n]*libseccomp/);
            expect(chainguard).toMatch(/apk add[^\n]*libseccomp/);
        });

        it("Android backup of app data is disabled", () => {
            const src = readSource("android/app/src/main/AndroidManifest.xml");
            expect(src).toMatch(/android:allowBackup\s*=\s*"false"/);
        });
    });

    describe("nomad mesh file upload", () => {
        it("PageNode.add_file always writes binary data", () => {
            const src = readSource("meshchatx/src/backend/page_node.py");
            expect(src).toContain('with open(file_path, "wb") as f:');
            expect(src).not.toMatch(/mode\s*=\s*["']wb["']\s*if\s*isinstance\(data,\s*bytes\)/);
        });

        it("multipart upload path reaches add_file from meshchat handler", () => {
            const handler = readSources(["meshchatx/meshchat.py", "meshchatx/src/backend/http/routes/page_nodes.py"]);
            expect(handler).toContain("async def page_nodes_upload_file");
            expect(handler).toContain("node.add_file(filename, file_data)");
        });

        it("page node upload returns JSON errors instead of unhandled 500s", () => {
            const handler = readSources(["meshchatx/meshchat.py", "meshchatx/src/backend/http/routes/page_nodes.py"]);
            const start = handler.indexOf("async def page_nodes_upload_file");
            expect(start).toBeGreaterThan(-1);
            const end = handler.indexOf("async def page_nodes_delete_file", start);
            const block = handler.slice(start, end);
            expect(block).toContain("except ValueError as e:");
            expect(block).toContain("except OSError as e:");
            expect(block).toContain("Failed to write file:");
        });
    });

    describe("rich html link policy", () => {
        const surfaces = [
            ["MicronEditorPage.vue", "meshchatx/src/frontend/components/micron-editor/MicronEditorPage.vue"],
            ["NomadNetworkPage.vue", "meshchatx/src/frontend/components/nomadnetwork/NomadNetworkPage.vue"],
            ["ArchivesPage.vue", "meshchatx/src/frontend/components/archives/ArchivesPage.vue"],
            ["RNCPPage.vue", "meshchatx/src/frontend/components/rncp/RNCPPage.vue"],
            ["ConversationViewer.vue", "meshchatx/src/frontend/components/messages/ConversationViewer.vue"],
        ];

        it.each(surfaces)("%s uses shared rich html link handler", (_, relativePath) => {
            const src = readSource(relativePath);
            expect(src).toContain("NomadRichHtmlLinks");
            expect(src).toContain("handleRichHtmlLinkClick");
        });

        it("electron main attaches in-window navigation and popout guards", () => {
            const main = readSource("electron/main.js");
            expect(main).toContain("web-contents-created");
            expect(main).toContain("attachInWindowNavigationGuard");
            expect(main).toContain("will-navigate");
            expect(main).toContain("will-redirect");
            expect(main).toContain("will-frame-navigate");
            expect(main).toContain("will-attach-webview");
            expect(main).toContain("setWindowOpenHandler");
            const preload = readSource("electron/preload.js");
            expect(preload).toContain("isTrustedShellOrigin");
            expect(preload).toContain("invokeTrusted");
            const origin = readSource("electron/shellOrigin.js");
            expect(origin).not.toMatch(/startsWith\(\s*["']https?:\/\/127/);
            expect(origin).toContain("parsed.username");
            expect(origin).toContain("isTrustedIpcEvent");
            expect(main).toContain("function trustedIpcHandle");
            expect(main).toContain("isTrustedIpcEvent");
            expect(main).not.toMatch(/ipcMain\.handle\("/);
        });

        it("Android WebView opens external http(s) in the system browser", () => {
            const src = readSource("android/app/src/main/java/com/meshchatx/MainActivity.java");
            expect(src).toContain("openExternalBrowserUri");
            expect(src).toContain("Intent.ACTION_VIEW");
            expect(src).toContain("setAllowFileAccess(false)");
            expect(src).toContain("setAllowFileAccessFromFileURLs(false)");
            expect(src).toContain("setAllowUniversalAccessFromFileURLs(false)");
            expect(src).toContain("MIXED_CONTENT_NEVER_ALLOW");
            expect(src).not.toContain("MIXED_CONTENT_ALWAYS_ALLOW");
        });
    });
});

describe("behavior contracts: dead API surface", () => {
    it("cancel endpoint is declared in the HTTP route manifest", () => {
        const manifest = readSource("tests/backend/fixtures/http_api_routes.json");
        expect(manifest).toContain('"/api/v1/lxmf-messages/{hash}/cancel"');
    });

    it("frontend cancel helper is referenced outside its definition file", () => {
        const viewer = readSource("meshchatx/src/frontend/components/messages/ConversationViewer.vue");
        const entry = readSource("meshchatx/src/frontend/components/messages/ConversationMessageEntry.vue");
        expect(entry.match(/cancelSendingMessage/g)?.length ?? 0).toBeGreaterThanOrEqual(1);
        expect(viewer).toContain("cancelSendingMessage(");
    });
});

describe("behavior contracts: Android Chaquopy Python sync", () => {
    it("Gradle syncs vendored lxmfy into Chaquopy python sources", () => {
        const gradle = readSource("android/app/build.gradle");
        expect(gradle).toContain("vendor/lxmfy/lxmfy");
        expect(gradle).toContain("syncLxmfyPython");
        expect(gradle).toContain("src/main/python/lxmfy");
        expect(gradle).toContain("syncRnsFilesyncPython");
        expect(gradle).toContain("vendor/rns_filesync/rns_filesync");
        expect(gradle).toContain("src/main/python/rns_filesync");
        expect(gradle).toMatch(/syncMeshchatPython/);
        expect(gradle).toMatch(/syncLxmfyPython/);
        expect(gradle).toMatch(/syncRnsFilesyncPython/);
        expect(gradle).toContain("httpx[http2]==0.28.1");
        expect(gradle).toContain("httpx-0.28.1-");
        const wheelScript = readSource("scripts/build-android-wheels-local.sh");
        expect(wheelScript).toContain("httpx[http2]");
        expect(wheelScript).toContain("HTTPX_VERSION");
        const lxmfyInit = readSource("vendor/lxmfy/lxmfy/__init__.py");
        expect(lxmfyInit.length).toBeGreaterThan(0);
        const filesyncInit = readSource("vendor/rns_filesync/rns_filesync/__init__.py");
        expect(filesyncInit.length).toBeGreaterThan(0);
        const httpIface = readSource("vendor/rns_over_http/HTTPInterface.py");
        expect(httpIface).toContain("interface_class");
        const packagedHttp = readSource("meshchatx/src/backend/data/interfaces/HTTPInterface.py");
        expect(packagedHttp).toContain("interface_class");
    });

    it("Android wrapper clears stale storage lock before main()", () => {
        const wrapper = readSource("android/app/src/main/python/meshchat_wrapper.py");
        expect(wrapper).toContain("_clear_stale_storage_lock");
        expect(wrapper).toContain(".meshchatx.lock");
        const lock = readSource("meshchatx/src/backend/storage_lock.py");
        expect(lock).toContain("_flock_unsupported");
        expect(lock).toContain("_acquire_soft");
    });
});

describe("behavior contracts: Reticulum instance settings", () => {
    it("Settings transport section wires Sideband-parity instance controls", () => {
        const page = readSource("meshchatx/src/frontend/components/settings/SettingsPage.vue");
        expect(page).toContain("share-reticulum-instance");
        expect(page).toContain("obfuscate-hops");
        expect(page).toContain("copyRpcConfigSnippet");
        expect(page).toContain("fetchReticulumInstanceSettings");
        expect(page).toContain("applyReticulumInstanceSettings");
        const service = readSource("meshchatx/src/frontend/js/settings/settingsReticulumInstanceService.js");
        expect(service).toContain("/api/v1/reticulum/instance");
        const selfCheck = readSource("meshchatx/src/backend/self_check.py");
        expect(selfCheck).toContain("http_reticulum_instance_good");
        expect(selfCheck).toContain("/api/v1/reticulum/instance");
    });
});

describe("behavior contracts: RNS Link API", () => {
    it("keeps generic rns.link transport wired for plugins and self-check", () => {
        const meshchat = readSource("meshchatx/meshchat.py");
        expect(meshchat).toContain("rns.link.open");
        expect(meshchat).toContain("rns.link.request");
        expect(meshchat).toContain("websocket_rns_link_good");
        const manager = readSource("meshchatx/src/backend/rns_link_manager.py");
        expect(manager).toContain("class RnsLinkManager");
        expect(manager).toContain("rns.link.event");
        const plugins = readSource("meshchatx/src/backend/plugin_manager.py");
        expect(plugins).toContain("rnsLink.open");
        expect(plugins).toContain("rns.link.event");
        const selfCheck = readSource("meshchatx/src/backend/self_check.py");
        expect(selfCheck).toContain("websocket_rns_link_good");
        expect(selfCheck).toContain("_probe_rns_link_api");
        expect(selfCheck).toContain("http_plugins_good");
        expect(selfCheck).toContain("http_sideband_plugins_good");
        expect(selfCheck).toContain("http_rrc_hubs_good");
        expect(selfCheck).toContain("http_rrc_servers_good");
        expect(selfCheck).toContain("plugins_runtime_good");
        expect(selfCheck).toContain("check_plugins_runtime");
        const guard = readSource("meshchatx/src/backend/websocket_config_guard.py");
        expect(guard).toContain("rns.link.open");
        expect(guard).toContain("rns.link.close");
    });
});

describe("behavior contracts: plugin install permissions", () => {
    it("previews ZIP installs and lists network endpoints before grant", () => {
        const handler = readSources([
            "meshchatx/meshchat.py",
            "meshchatx/src/backend/http/routes/plugins.py",
            "meshchatx/src/backend/http/routes/sideband.py",
        ]);
        expect(handler).toContain("/api/v1/plugins/preview");
        expect(handler).toContain("granted_permissions");
        expect(handler).toContain("/api/v1/plugins/trusted-publishers");
        expect(handler).toContain("/api/v1/sideband-plugins");
        const section = readSource("meshchatx/src/frontend/components/settings/PluginsSettingsSection.vue");
        expect(section).toContain("PluginInstallDialog");
        expect(section).toContain("/api/v1/plugins/preview");
        expect(section).toContain("granted_permissions");
        expect(section).toContain(".wasm");
        expect(section).toContain("trustPublisher");
        expect(section).toContain("sideband");
        const dialog = readSource("meshchatx/src/frontend/components/settings/PluginInstallDialog.vue");
        expect(dialog).toContain("network_endpoints");
        expect(dialog).toContain("grantedMap");
        expect(dialog).toContain("signatureBlocksInstall");
        expect(dialog).toContain("trustPublisher");
        expect(dialog).toContain("security_findings");
        const perms = readSource("meshchatx/src/backend/plugin_permissions.py");
        expect(perms).toContain("collect_network_endpoints");
        expect(perms).toContain('permission_id_for_network("fetch")');
        expect(perms).toContain("KNOWN_NETWORK");
        const manager = readSource("meshchatx/src/backend/plugin_manager.py");
        expect(manager).toContain("preview_from_zip_bytes");
        expect(manager).toContain("granted_allows_network_fetch");
        expect(manager).toContain("require_valid_signature");
        expect(manager).toContain("backend.type");
    });
});

describe("behavior contracts: phased startup and early UI mount", () => {
    it("frontend mounts on ui_ready and continues polling for mesh ready", () => {
        const wait = readSource("meshchatx/src/frontend/js/networkStartupWait.js");
        expect(wait).toContain('kind: "ui"');
        expect(wait).toContain("mountOnUiReady");
        expect(wait).toContain("waitForMeshReady");
        expect(wait).toContain("hasOwnProperty.call");
        const main = readSource("meshchatx/src/frontend/main.js");
        expect(main).toContain("waitForMeshReady");
        expect(main).toContain('networkReady === "ui"');
        expect(main).toContain("networkStarting");
        expect(main).toContain('from "./locales/en.json"');
        expect(main).not.toMatch(/import\.meta\.glob\(\s*["'].*locales.*["']\s*,\s*\{\s*eager:\s*true/);
    });

    it("App gates shell until mesh ready and shows starting banner", () => {
        const app = readSource("meshchatx/src/frontend/components/App.vue");
        expect(app).toContain("waitForMeshThenStartShell");
        expect(app).toContain("showNetworkStartingBanner");
        expect(app).toContain("networkStarting");
        expect(app).toContain("network_starting");
        const banners = readSource("meshchatx/src/frontend/components/layout/AppShellBanners.vue");
        expect(banners).toContain("showNetworkStarting");
        expect(banners).toContain("networkStartingLabel");
        expect(banners).toContain("open-settings");
        expect(banners).toContain("open-interfaces");
    });

    it("backend publishes ui_ready early and defers secondary identity services", () => {
        const mesh = readSource("meshchatx/meshchat.py");
        expect(mesh).toContain("self._ui_ready = True");
        expect(mesh).toContain("_finish_deferred_startup_services");
        expect(mesh).toContain("_start_deferred_reticulum_services");
        const identity = readSource("meshchatx/src/backend/identity_context.py");
        expect(identity).toContain("def setup_deferred_services");
        expect(identity).toContain("_deferred_setup_in_progress");
        expect(identity).toContain("_deferred_setup_finished");
        expect(identity).toContain("critical_only=True");
        expect(identity).toContain("quick=True");
        expect(identity).toContain("populate=False");
    });

    it("integrity critical path and docs populate helpers stay available", () => {
        const integrity = readSource("meshchatx/src/backend/integrity_manager.py");
        expect(integrity).toContain("critical_only");
        const docs = readSource("meshchatx/src/backend/docs_manager.py");
        expect(docs).toContain("ensure_meshchatx_docs_populated");
        expect(docs).toContain("populate: bool = True");
        const database = readSource("meshchatx/src/backend/database/__init__.py");
        expect(database).toContain("quick: bool = False");
        expect(database).toContain("quick_check");
    });
});

describe("behavior contracts: network visualiser performance", () => {
    it("keeps lean physics and edge-hide options for large meshes", () => {
        const src = readSource("meshchatx/src/frontend/components/network-visualiser/NetworkVisualiser.vue");
        expect(src).toContain("hideEdgesOnDrag: true");
        expect(src).toContain("hideEdgesOnZoom: true");
        expect(src).toMatch(/avoidOverlap:\s*0/);
        expect(src).toContain('solver: "barnesHut"');
        const perf = readSource("meshchatx/src/frontend/js/networkVisualiserPerf.js");
        expect(perf).toContain("dedupeIconQueueEntries");
        expect(perf).toContain("pickAdaptiveFetchConcurrency");
    });

    it("prefers WebGL with WASM scene and keeps vis-network fallback", () => {
        const src = readSource("meshchatx/src/frontend/components/network-visualiser/NetworkVisualiser.vue");
        expect(src).toContain("tryStartWebGL");
        expect(src).toContain("initVisNetwork");
        expect(src).toContain("preferredRenderer");
        expect(src).toContain('name: "nomadnetwork"');
        expect(src).toContain("openAnnounceDestination");
        const engine = readSource("meshchatx/src/frontend/js/networkVisualiserWebGLEngine.js");
        expect(engine).toContain("meshchatxVisualiserSceneSet");
        expect(engine).toContain("createVisualiserWebGLEngine");
        expect(engine).toContain('pointerMode = "pinch"');
        expect(engine).toContain("meshchatxVisualiserSceneZoomAt");
        expect(engine).toContain("updateNodeImages");
        expect(engine).toContain("labelByIndex");
        expect(engine).toContain("collectWebGLLabels");
        expect(engine).toContain("lodLevelFromScale");
        const webgl = readSource("meshchatx/src/frontend/js/networkVisualiserWebGL.js");
        expect(webgl).toContain("u_atlas");
        expect(webgl).toContain("network-webgl-labels");
        expect(webgl).toContain("resolveVisualiserAssetUrl");
        expect(webgl).toContain("mergeSceneNodesWithTextures");
        expect(webgl).not.toContain("zoom >= 0.45");
        const prefs = readSource("meshchatx/src/frontend/js/settings/settingsVisualiserPrefs.js");
        expect(prefs).toContain("persistVisualiserRenderer");
        expect(prefs).toContain("persistVisualiserViewMode");
        expect(prefs).toContain('"auto"');
        expect(prefs).toContain('"webgl"');
        expect(prefs).toContain('"vis"');
        expect(prefs).toContain('"planet"');
        const planet = readSource("meshchatx/src/frontend/js/networkVisualiserPlanet.js");
        expect(planet).toContain("projectPlanetScene");
        expect(planet).toContain("layoutToSphere");
        expect(engine).toContain("setViewMode");
        expect(engine).toContain("projectPlanetScene");
    });
});

describe("behavior contracts: locale, theme, and call audio", () => {
    it("App persists shell config through HTTP PATCH helpers", () => {
        const app = readSource("meshchatx/src/frontend/components/App.vue");
        expect(app).toContain("patchServerConfig");
        expect(app).toContain("normalizeUiLocaleCode");
        expect(app).toContain("async applyLocale(");
        expect(app).toContain("setLocale(this.$i18n");
    });

    it("main.js registers the real i18n composer for Options API locale switches", () => {
        const main = readSource("meshchatx/src/frontend/main.js");
        expect(main).toContain("registerUiI18n");
        expect(main).toContain("registerUiI18n(i18n)");
        const loader = readSource("meshchatx/src/frontend/js/localeLoader.js");
        expect(loader).toContain("export function registerUiI18n");
        expect(loader).toContain("hasLocaleMessageApi");
    });

    it("Settings language change applies vue-i18n locale after PATCH", () => {
        const settings = readSource("meshchatx/src/frontend/components/settings/SettingsPage.vue");
        expect(settings).toContain("async onLanguageChange()");
        expect(settings).toContain("setLocale(this.$i18n");
        expect(settings).toContain("patchServerConfig");
    });

    it("Docs manual language picker is isolated from UI config.language", () => {
        const docs = readSource("meshchatx/src/frontend/components/docs/DocsPage.vue");
        expect(docs).toContain("reticulumDocsLang");
        expect(docs).not.toMatch(/setLanguage[\s\S]{0,400}api\.patch/);
    });

    it("boot-theme.js clears html.dark when light is selected", () => {
        const boot = readSource("meshchatx/src/frontend/public/boot-theme.js");
        expect(boot).toContain('classList.remove("dark")');
    });

    it("network visualiser theme follows GlobalState before html.dark fallback", () => {
        const vis = readSource("meshchatx/src/frontend/components/network-visualiser/NetworkVisualiser.vue");
        expect(vis).toContain("resolveVisualiserIsDark");
        expect(vis).toContain('theme === "light"');
        expect(vis).toContain("GlobalState.config");
    });

    it("CallPage refresh devices uses getUserMedia before device enumeration", () => {
        const call = readSource("meshchatx/src/frontend/components/call/CallPage.vue");
        expect(call).toContain("Wide-open { audio: true } is what");
        expect(call).toMatch(/requestAudioPermission[\s\S]*promptMicrophoneAccess/);
        expect(call).toMatch(/requestAudioPermission[\s\S]*promptMicrophoneAccess[\s\S]*refreshAudioDevices/);
    });
});

function listVueFiles(dir) {
    const out = [];
    for (const name of readdirSync(dir)) {
        const p = join(dir, name);
        if (statSync(p).isDirectory()) {
            out.push(...listVueFiles(p));
        } else if (name.endsWith(".vue")) {
            out.push(p);
        }
    }
    return out;
}

const VHTML_SANITIZER_TOKENS = [
    "renderMarkdown",
    "renderMessageHtml",
    "sanitizeNomadHtml",
    "renderNomadPageByPath",
    "renderNomadHtmlPage",
    "renderNomadMarkdown",
    "convertMicronToHtml",
    "sanitizeRenderedMicronHtml",
    "drawFeatureDescriptionSanitized",
    "highlightMatch",
    "changelogHtml",
    "selectedDocContent.html",
    "$t(",
    "MarkdownRenderer",
];

describe("behavior contracts: security gates", () => {
    it("WebSocket Origin check is wired on both upgrade paths", () => {
        const src = readSource("meshchatx/src/backend/http/routes/websocket_upgrade.py");
        expect(src).toContain("websocket_origin_allowed");
        expect(src).toContain("_reject_forbidden_ws_origin");
        expect(src).toContain('{"error": "Forbidden origin"}');
    });

    it("WebSocket auth fails closed except ping", () => {
        const src = readSource("meshchatx/src/backend/websocket_config_guard.py");
        const match = src.match(/WEBSOCKET_PUBLIC_TYPES = frozenset\(\s*\{([^}]+)\}/s);
        expect(match).toBeTruthy();
        const members = [...match[1].matchAll(/"([^"]+)"/g)].map((m) => m[1]);
        expect(members).toEqual(["ping"]);
        expect(src).toContain("websocket_type_requires_auth");
        expect(src).toContain("if msg_type in WEBSOCKET_PUBLIC_TYPES:");
    });

    it("FileSync reserved tops include ssl", () => {
        const src = readSource("meshchatx/src/backend/rns_filesync_handler.py");
        const start = src.indexOf("_RESERVED_SYNC_TOP");
        expect(start).toBeGreaterThan(-1);
        const block = src.slice(start, src.indexOf(")", start) + 1);
        expect(block).toContain('"ssl"');
    });

    it("plugin invoke and hooks re-hash backends and purge pycache", () => {
        const manager = readSource("meshchatx/src/backend/plugin_manager.py");
        const invokeStart = manager.indexOf("def invoke(");
        const invokeBlock = manager.slice(invokeStart, manager.indexOf("def dispatch_hook(", invokeStart));
        expect(invokeBlock).toContain("self._require_untampered_backend(record)");
        const hookStart = manager.indexOf("def dispatch_hook(");
        const hookBlock = manager.slice(hookStart, hookStart + 800);
        expect(hookBlock).toContain("self._require_untampered_backend(record)");
        const runtime = readSource("meshchatx/src/backend/plugin_python_runtime.py");
        expect(runtime).toContain("def _purge_entry_pycache");
        expect(runtime).toContain("self._purge_entry_pycache(entry_path)");
    });

    it("plugin network scan parses hostname instead of prefix-matching loopback", () => {
        const src = readSource("meshchatx/src/backend/plugin_permissions.py");
        const start = src.indexOf("def _is_external_http_url");
        const block = src.slice(start, src.indexOf("\ndef ", start + 1));
        expect(block).toContain("urlparse(value)");
        expect(block).toContain("parsed.hostname");
        expect(block).not.toMatch(/"127\.0\.0\.1" in /);
        expect(block).not.toMatch(/"localhost" in /);
    });

    it("Electron ipcMain.handle is wrapped by trustedIpcHandle", () => {
        const main = readSource("electron/main.js");
        expect(main).toContain("function trustedIpcHandle");
        expect(main).toContain("isTrustedIpcEvent");
        expect(main).not.toMatch(/ipcMain\.handle\("/);
    });

    it("v-html sites name a sanitizer and do not use a bare file-level disable", () => {
        const vueRoot = join(process.cwd(), "meshchatx/src/frontend/components");
        const files = listVueFiles(vueRoot);
        const withVHtml = [];
        for (const abs of files) {
            const src = readFileSync(abs, "utf8");
            if (!src.includes("v-html")) {
                continue;
            }
            withVHtml.push(abs);
            expect(src, abs).not.toMatch(/eslint-disable\s+vue\/no-v-html\s*-->/);
            const named = VHTML_SANITIZER_TOKENS.some((token) => src.includes(token));
            expect(named, abs).toBe(true);
        }
        expect(withVHtml.length).toBeGreaterThan(5);
    });

    it("LAN bind warning is a banner, not a process exit", () => {
        const app = readSource("meshchatx/src/frontend/components/App.vue");
        expect(app).toContain("showLanBindNoAuthBanner");
        expect(app).toContain("shouldShowLanBindNoAuthBanner");
        expect(app).toContain("lan_bind_no_auth_banner");
        const banners = readSource("meshchatx/src/frontend/components/layout/AppShellBanners.vue");
        expect(banners).toContain("showLanBindNoAuth");
        expect(banners).toContain("lanBindNoAuthLabel");
        const helper = readSource("meshchatx/src/frontend/js/lanBindWarning.js");
        expect(helper).toContain("isElectron");
        expect(helper).toContain("isAndroid");
        expect(helper).toContain("dismissLanBindNoAuthBanner");
        expect(helper).toContain("isLanBindNoAuthBannerDismissed");
        expect(helper).not.toContain("process.exit");
        expect(helper).not.toContain("sys.exit");
    });

    it("mesh payload caps stay named constants with drop-not-hang reasons", () => {
        const announce = readSource("meshchatx/src/backend/announce_manager.py");
        expect(announce).toContain("MAX_ANNOUNCE_APP_DATA_BYTES = 2048");
        const rrc = readSource("meshchatx/src/backend/rrc/protocol.py");
        expect(rrc).toContain("DEFAULT_MAX_MSG_BYTES = 350");
        const geo = readSource("meshchatx/src/backend/map_geo_validator.py");
        expect(geo).toContain('raise GeoValidationError("file_too_large")');
    });
});
