import { readFileSync } from "fs";
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
    });

    describe("nomad mesh file upload", () => {
        it("PageNode.add_file always writes binary data", () => {
            const src = readSource("meshchatx/src/backend/page_node.py");
            expect(src).toContain('with open(file_path, "wb") as f:');
            expect(src).not.toMatch(/mode\s*=\s*["']wb["']\s*if\s*isinstance\(data,\s*bytes\)/);
        });

        it("multipart upload path reaches add_file from meshchat handler", () => {
            const meshchat = readSource("meshchatx/meshchat.py");
            expect(meshchat).toContain("async def page_nodes_upload_file");
            expect(meshchat).toContain("node.add_file(filename, file_data)");
        });

        it("page node upload returns JSON errors instead of unhandled 500s", () => {
            const meshchat = readSource("meshchatx/meshchat.py");
            const start = meshchat.indexOf("async def page_nodes_upload_file");
            expect(start).toBeGreaterThan(-1);
            const end = meshchat.indexOf("async def page_nodes_delete_file", start);
            const block = meshchat.slice(start, end);
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
            expect(main).toContain("attachInWindowNavigationGuard");
            expect(main).toContain("setWindowOpenHandler");
        });

        it("Android WebView opens external http(s) in the system browser", () => {
            const src = readSource("android/app/src/main/java/com/meshchatx/MainActivity.java");
            expect(src).toContain("openExternalBrowserUri");
            expect(src).toContain("Intent.ACTION_VIEW");
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
        expect(gradle).toMatch(
            /dependsOn\(tasks\.named\("syncMeshchatPython"\),\s*tasks\.named\("syncLxmfyPython"\)\)/
        );
        const initPy = readSource("vendor/lxmfy/lxmfy/__init__.py");
        expect(initPy.length).toBeGreaterThan(0);
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
        const meshchat = readSource("meshchatx/meshchat.py");
        expect(meshchat).toContain("/api/v1/plugins/preview");
        expect(meshchat).toContain("granted_permissions");
        expect(meshchat).toContain("/api/v1/plugins/trusted-publishers");
        expect(meshchat).toContain("/api/v1/sideband-plugins");
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
});
