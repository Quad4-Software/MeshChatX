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
