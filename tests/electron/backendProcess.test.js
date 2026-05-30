import { beforeEach, describe, expect, it, vi } from "vitest";
import { createBackendProcessManager } from "../../electron/backendProcess.js";

function createFakeChildProcess() {
    const { EventEmitter } = require("node:events");
    const proc = new EventEmitter();
    proc.stdout = new EventEmitter();
    proc.stdout.setEncoding = () => {};
    proc.stderr = new EventEmitter();
    proc.stderr.setEncoding = () => {};
    proc.pid = 4242;
    proc.exitCode = null;
    proc.signalCode = null;
    return proc;
}

describe("electron/backendProcess", () => {
    let fakeProc;
    let spawnMock;

    beforeEach(() => {
        fakeProc = createFakeChildProcess();
        spawnMock = vi.fn(() => fakeProc);
    });

    it("keeps the shell open and notifies renderer when backend exits during app use", async () => {
        const notifyRenderer = vi.fn();
        const showCrashPage = vi.fn();
        const manager = createBackendProcessManager({
            log: vi.fn(),
            getDefaultStorageDir: () => "/tmp/storage",
            getDefaultReticulumConfigDir: () => "/tmp/reticulum",
            getMainWindowPageKind: () => "app",
            isQuiting: () => false,
            notifyRenderer,
            showCrashPage,
            spawn: spawnMock,
        });

        manager.setUserProvidedArguments([]);
        await manager.spawnBackend("/tmp/ReticulumMeshChatX", { backend: { ok: true, issues: [] } });

        fakeProc.emit("exit", 255);
        await new Promise((resolve) => setImmediate(resolve));

        expect(notifyRenderer).toHaveBeenCalledWith("backend-process-exited", expect.objectContaining({ code: 255 }));
        expect(showCrashPage).not.toHaveBeenCalled();
        expect(manager.getRuntimeState().running).toBe(false);
        expect(manager.getRuntimeState().lastExitCode).toBe(255);
    });

    it("opens the crash page when backend exits outside the main shell", async () => {
        const notifyRenderer = vi.fn();
        const showCrashPage = vi.fn();
        const manager = createBackendProcessManager({
            log: vi.fn(),
            getDefaultStorageDir: () => "/tmp/storage",
            getDefaultReticulumConfigDir: () => "/tmp/reticulum",
            getMainWindowPageKind: () => "other",
            isQuiting: () => false,
            notifyRenderer,
            showCrashPage,
            spawn: spawnMock,
        });

        manager.setUserProvidedArguments([]);
        await manager.spawnBackend("/tmp/ReticulumMeshChatX", { backend: { ok: true, issues: [] } });
        fakeProc.emit("exit", 1);
        await new Promise((resolve) => setImmediate(resolve));

        expect(notifyRenderer).toHaveBeenCalled();
        expect(showCrashPage).toHaveBeenCalledWith(expect.objectContaining({ code: 1 }));
    });
});
