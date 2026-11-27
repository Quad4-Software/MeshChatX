// SPDX-License-Identifier: 0BSD

import { describe, expect, it, vi, afterEach } from "vitest";
import { PluginHost } from "../../meshchatx/src/frontend/js/plugins/PluginHost.js";

function makePlugin() {
    return {
        id: "com.test.concurrent-load",
        manifest: {
            id: "com.test.concurrent-load",
            version: "1.0.0",
            apiVersion: 1,
            frontend: { type: "js", entry: "main.js" },
        },
        granted_permissions: [],
    };
}

function makeWorkerStub() {
    const ctor = vi.fn(function () {
        this.postMessage = vi.fn();
        this.terminate = vi.fn();
        this.addEventListener = vi.fn();
        this.onmessage = null;
        this.onerror = null;
    });
    vi.stubGlobal("Worker", ctor);
    return ctor;
}

function makeGatedApiClient() {
    let release;
    const gate = new Promise((r) => {
        release = r;
    });
    const apiClient = {
        get: vi.fn(async () => {
            await gate;
            return { data: "self.postMessage({type:'ready'})" };
        }),
        post: vi.fn(async () => ({ data: {} })),
    };
    return { apiClient, release };
}

afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

describe("PluginHost.loadPlugin", () => {
    it("dedupes concurrent loads of the same plugin", async () => {
        const workerCtor = makeWorkerStub();
        const { apiClient, release } = makeGatedApiClient();
        const host = new PluginHost();
        const plugin = makePlugin();

        const p1 = host.loadPlugin(plugin, apiClient);
        const p2 = host.loadPlugin(plugin, apiClient);
        release();
        await Promise.all([p1, p2]);

        expect(workerCtor).toHaveBeenCalledTimes(1);
        expect(host.instances.size).toBe(1);
        expect(host.instances.has(plugin.id)).toBe(true);
    });

    it("terminates the worker when unloaded mid-load", async () => {
        const workerCtor = makeWorkerStub();
        const { apiClient, release } = makeGatedApiClient();
        const host = new PluginHost();
        const plugin = makePlugin();

        const p = host.loadPlugin(plugin, apiClient);
        host.unloadPlugin(plugin.id);
        release();
        await p;

        expect(host.instances.has(plugin.id)).toBe(false);
        expect(workerCtor).toHaveBeenCalledTimes(1);
        expect(workerCtor.mock.instances[0].terminate).toHaveBeenCalled();
    });
});
