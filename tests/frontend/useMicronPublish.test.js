// SPDX-License-Identifier: 0BSD

import { describe, expect, it, vi, beforeEach } from "vitest";
import { useMicronPublish } from "../../meshchatx/src/frontend/js/micron/useMicronPublish.js";
import DialogUtils from "@/js/DialogUtils";
import ToastUtils from "@/js/ToastUtils";

const micronEditorT = (key, params = {}) => {
    const strings = {
        "tools.micron_editor.new_tab": "New Tab",
        "tools.micron_editor.publish_prompt_name":
            'index.mu already exists on "{server}". Enter a page name (without .mu):',
        "tools.micron_editor.publish_published": 'Published "{page}" to {server}',
        "tools.micron_editor.publish_failed": "Failed to publish page",
    };
    let out = strings[key] ?? key;
    for (const [k, v] of Object.entries(params)) {
        out = out.replace(`{${k}}`, String(v));
    }
    return out;
};

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(),
        alert: vi.fn(),
        prompt: vi.fn(),
    },
}));

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
    },
}));

describe("useMicronPublish", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        window.api = {
            get: vi.fn().mockResolvedValue({ data: [] }),
            post: vi.fn().mockResolvedValue({ data: {} }),
        };
    });

    const makePublish = (overrides = {}) =>
        useMicronPublish({
            t: micronEditorT,
            pushRoute: vi.fn(),
            getActiveTab: () => ({ id: 1, name: "New Tab 1", content: "x" }),
            uploadImages: vi.fn().mockResolvedValue({ uploaded: 0, failed: 0 }),
            ...overrides,
        });

    it("starts with publish state closed and idle", () => {
        const publish = makePublish();
        expect(publish.showPublishMenu.value).toBe(false);
        expect(publish.showPublishSiteModal.value).toBe(false);
        expect(publish.pageNodes.value).toEqual([]);
        expect(publish.publishBusy.value).toBe(false);
        expect(publish.lastPublished.value).toBeNull();
    });

    it("togglePublishMenu loads page nodes when opening", async () => {
        window.api.get.mockResolvedValue({ data: [{ node_id: "n1", name: "Srv" }] });
        const publish = makePublish();
        await publish.togglePublishMenu();
        expect(publish.showPublishMenu.value).toBe(true);
        expect(window.api.get).toHaveBeenCalledWith("/api/v1/page-nodes");
        expect(publish.pageNodes.value).toEqual([{ node_id: "n1", name: "Srv" }]);
        await publish.togglePublishMenu();
        expect(publish.showPublishMenu.value).toBe(false);
    });

    it("togglePublishMenu falls back to an empty node list on error", async () => {
        window.api.get.mockRejectedValue(new Error("offline"));
        const publish = makePublish();
        await publish.togglePublishMenu();
        expect(publish.pageNodes.value).toEqual([]);
    });

    it("isUnsetMicronTabName matches default new tab labels", () => {
        const publish = makePublish();
        expect(publish.isUnsetMicronTabName("New Tab 2")).toBe(true);
        expect(publish.isUnsetMicronTabName("Homepage")).toBe(false);
        expect(publish.isUnsetMicronTabName("")).toBe(true);
    });

    it("tabNameToPageBase strips known page extensions", () => {
        const publish = makePublish();
        expect(publish.tabNameToPageBase({ name: "About Page.mu" })).toBe("About_Page");
        expect(publish.tabNameToPageBase({ name: "Landing.html" })).toBe("Landing");
        expect(publish.tabNameToPageBase({ name: "Notes" })).toBe("Notes");
    });

    it("pageBaseWithExtension preserves the tab extension", () => {
        const publish = makePublish();
        expect(publish.pageBaseWithExtension("landing", { name: "Landing.html" })).toBe("landing.html");
        expect(publish.pageBaseWithExtension("index", { name: "New Tab 1" })).toBe("index");
        expect(publish.pageBaseWithExtension("  ", { name: "a.mu" })).toBe("");
    });

    it("resolvePublishPageBase uses index when server has no index.mu", async () => {
        const publish = makePublish();
        await expect(
            publish.resolvePublishPageBase({ name: "New Tab 1" }, [], "srv")
        ).resolves.toBe("index");
    });

    it("resolvePublishPageBase uses tab name when index.mu exists and tab is renamed", async () => {
        const publish = makePublish();
        await expect(
            publish.resolvePublishPageBase({ name: "About Page" }, ["index.mu"], "srv")
        ).resolves.toBe("About_Page");
    });

    it("resolvePublishPageBase prompts when index.mu exists and tab name is unset", async () => {
        DialogUtils.prompt.mockResolvedValue("custom_page");
        const publish = makePublish();
        await expect(
            publish.resolvePublishPageBase({ name: "New Tab 1" }, ["index.mu"], "srv")
        ).resolves.toBe("custom_page");
        expect(DialogUtils.prompt).toHaveBeenCalled();
    });

    it("nomadPagePathForName builds /page/ paths", () => {
        const publish = makePublish();
        expect(publish.nomadPagePathForName("about.mu")).toBe("/page/about.mu");
        expect(publish.nomadPagePathForName("/page/x.mu")).toBe("/page/x.mu");
        expect(publish.nomadPagePathForName("")).toBe("/page/index.mu");
    });

    it("buildSiteIndexPage emits micron links for each page", () => {
        const publish = makePublish();
        const dest = "d".repeat(32);
        const content = publish.buildSiteIndexPage(dest, [
            { name: "about.mu", label: "About" },
            { name: "news.mu", label: "News [x]" },
        ]);
        expect(content).toContain(`[About\`${dest}:/page/about.mu]`);
        expect(content).toContain(`[News x\`${dest}:/page/news.mu]`);
    });

    it("rememberPublished records the destination and openPublishedInNomadNet routes", async () => {
        const pushRoute = vi.fn();
        const publish = makePublish({ pushRoute });
        const dest = "a".repeat(32);
        publish.rememberPublished({ destination_hash: dest, name: "Srv" }, "index.mu");
        expect(publish.lastPublished.value).toEqual({
            destinationHash: dest,
            pagePath: "/page/index.mu",
            pageName: "index.mu",
            serverName: "Srv",
        });
        publish.openPublishedInNomadNet();
        expect(pushRoute).toHaveBeenCalledWith({
            name: "nomadnetwork",
            params: { destinationHash: dest },
            query: { path: "/page/index.mu", newTab: "1" },
        });
    });

    it("rememberPublished ignores non-hash destinations", () => {
        const publish = makePublish();
        publish.rememberPublished({ destination_hash: "nope", name: "Srv" }, "index.mu");
        expect(publish.lastPublished.value).toBeNull();
    });

    it("publishToNode posts index.mu and uploads referenced images", async () => {
        const dest = "a".repeat(32);
        window.api.get.mockResolvedValue({ data: { pages: [] } });
        window.api.post.mockResolvedValue({ data: { name: "index.mu" } });
        DialogUtils.confirm.mockResolvedValue(false);
        const uploadImages = vi.fn().mockResolvedValue({ uploaded: 1, failed: 0 });
        const publish = makePublish({ uploadImages });
        await publish.publishToNode({ node_id: "n1", name: "My Server", running: true, destination_hash: dest });
        expect(window.api.post).toHaveBeenCalledWith("/api/v1/page-nodes/n1/pages", {
            name: "index",
            content: "x",
        });
        expect(uploadImages).toHaveBeenCalledWith(
            expect.objectContaining({ node_id: "n1" }),
            ["x"]
        );
        expect(publish.lastPublished.value?.pageName).toBe("index.mu");
        expect(publish.publishBusy.value).toBe(false);
    });

    it("publishToNode starts a stopped node before publishing", async () => {
        const dest = "c".repeat(32);
        window.api.get.mockResolvedValue({ data: { pages: [] } });
        window.api.post
            .mockResolvedValueOnce({ data: { destination_hash: dest } })
            .mockResolvedValueOnce({ data: { name: "index.mu" } });
        DialogUtils.confirm.mockResolvedValue(false);
        const publish = makePublish();
        await publish.publishToNode({ node_id: "n3", name: "Stopped", running: false });
        expect(window.api.post).toHaveBeenNthCalledWith(1, "/api/v1/page-nodes/n3/start");
        expect(window.api.post).toHaveBeenNthCalledWith(2, "/api/v1/page-nodes/n3/pages", {
            name: "index",
            content: "x",
        });
    });

    it("publishSite uploads pages in order and writes the index page", async () => {
        const dest = "e".repeat(32);
        window.api.post.mockResolvedValue({ data: {} });
        DialogUtils.confirm.mockResolvedValue(false);
        const publish = makePublish();
        publish.pageNodes.value = [{ node_id: "n9", name: "Srv", running: true, destination_hash: dest }];
        await publish.publishSite({
            nodeId: "n9",
            pages: [
                { name: "one.mu", content: "1", label: "One" },
                { name: "two.mu", content: "2", label: "Two" },
            ],
            generateIndex: true,
        });
        const posts = window.api.post.mock.calls.filter((c) => c[0] === "/api/v1/page-nodes/n9/pages");
        expect(posts.map((c) => c[1].name)).toEqual(["one.mu", "two.mu", "index.mu"]);
        expect(posts[2][1].content).toContain(`[One\`${dest}:/page/one.mu]`);
        expect(publish.lastPublished.value?.pageName).toBe("index.mu");
        expect(publish.showPublishSiteModal.value).toBe(false);
    });

    it("publishSite creates a new server when no nodeId is given", async () => {
        const dest = "f".repeat(32);
        window.api.post
            .mockResolvedValueOnce({ data: { node_id: "n10", name: "Fresh", running: false } })
            .mockResolvedValueOnce({ data: { destination_hash: dest } })
            .mockResolvedValue({ data: {} });
        DialogUtils.confirm.mockResolvedValue(false);
        const publish = makePublish();
        await publish.publishSite({
            nodeId: null,
            newServerName: "Fresh",
            pages: [{ name: "index.mu", content: "home", label: "Home" }],
            generateIndex: false,
        });
        expect(window.api.post).toHaveBeenNthCalledWith(1, "/api/v1/page-nodes", { name: "Fresh" });
        expect(window.api.post).toHaveBeenNthCalledWith(2, "/api/v1/page-nodes/n10/start");
        expect(window.api.post).toHaveBeenNthCalledWith(3, "/api/v1/page-nodes/n10/pages", {
            name: "index.mu",
            content: "home",
        });
    });

    it("createMeshServerAndPublish creates, starts, publishes, and can open NomadNet", async () => {
        const dest = "b".repeat(32);
        window.api.get.mockResolvedValue({ data: { pages: [] } });
        window.api.post
            .mockResolvedValueOnce({ data: { node_id: "n2", name: "Micron Pages", running: false } })
            .mockResolvedValueOnce({ data: { destination_hash: dest } })
            .mockResolvedValueOnce({ data: { name: "index.mu" } });
        DialogUtils.prompt.mockResolvedValue("Micron Pages");
        DialogUtils.confirm.mockResolvedValue(true);
        const pushRoute = vi.fn();
        const publish = makePublish({ pushRoute });
        await publish.createMeshServerAndPublish();
        expect(window.api.post).toHaveBeenNthCalledWith(1, "/api/v1/page-nodes", { name: "Micron Pages" });
        expect(window.api.post).toHaveBeenNthCalledWith(2, "/api/v1/page-nodes/n2/start");
        expect(window.api.post).toHaveBeenNthCalledWith(3, "/api/v1/page-nodes/n2/pages", {
            name: "index",
            content: "x",
        });
        expect(pushRoute).toHaveBeenCalledWith({
            name: "nomadnetwork",
            params: { destinationHash: dest },
            query: { path: "/page/index.mu", newTab: "1" },
        });
    });
});
