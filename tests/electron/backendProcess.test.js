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
    proc.kill = vi.fn();
    return proc;
}

function createManager(overrides = {}) {
    return createBackendProcessManager({
        log: vi.fn(),
        getDefaultStorageDir: () => "/tmp/storage",
        getDefaultReticulumConfigDir: () => "/tmp/reticulum",
        getMainWindowPageKind: () => "app",
        isQuiting: () => false,
        notifyRenderer: vi.fn(),
        showCrashPage: vi.fn(),
        spawn: vi.fn(),
        ...overrides,
    });
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

    it("notifies loading screen when backend exits during startup", async () => {
        const notifyRenderer = vi.fn();
        const showCrashPage = vi.fn();
        const manager = createBackendProcessManager({
            log: vi.fn(),
            getDefaultStorageDir: () => "/tmp/storage",
            getDefaultReticulumConfigDir: () => "/tmp/reticulum",
            getMainWindowPageKind: () => "loading",
            isQuiting: () => false,
            notifyRenderer,
            showCrashPage,
            spawn: spawnMock,
        });

        manager.setUserProvidedArguments([]);
        await manager.spawnBackend("/tmp/ReticulumMeshChatX", { backend: { ok: true, issues: [] } });
        fakeProc.emit("exit", 9);
        await new Promise((resolve) => setImmediate(resolve));

        expect(notifyRenderer).toHaveBeenCalledWith(
            "backend-startup-failed",
            expect.objectContaining({ code: 9, paths: expect.any(Object) })
        );
        expect(showCrashPage).not.toHaveBeenCalled();
        expect(manager.getLastCrash()).toEqual(expect.objectContaining({ code: 9 }));
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

    it("skips AppContainer launcher on win32 by default", async () => {
        const previousPlatform = process.platform;
        const previousEnv = process.env.MESHCHAT_APPCONTAINER;
        Object.defineProperty(process, "platform", { value: "win32" });
        delete process.env.MESHCHAT_APPCONTAINER;
        try {
            const manager = createBackendProcessManager({
                log: vi.fn(),
                getDefaultStorageDir: () => "C:\\Users\\test\\.reticulum-meshchatx",
                getDefaultReticulumConfigDir: () => "C:\\Users\\test\\.reticulum",
                getMainWindowPageKind: () => "loading",
                isQuiting: () => false,
                notifyRenderer: vi.fn(),
                showCrashPage: vi.fn(),
                spawn: spawnMock,
            });
            manager.setUserProvidedArguments([]);
            await manager.spawnBackend("C:\\App\\ReticulumMeshChatX.exe", {
                backend: { ok: true, issues: [] },
            });
            const args = spawnMock.mock.calls[0][1];
            expect(args).not.toContain("--meshchatx-run-module");
            expect(args[0]).toBe("--headless");
        } finally {
            Object.defineProperty(process, "platform", { value: previousPlatform });
            if (previousEnv === undefined) {
                delete process.env.MESHCHAT_APPCONTAINER;
            } else {
                process.env.MESHCHAT_APPCONTAINER = previousEnv;
            }
        }
    });

    it("does not use AppContainer launcher on non-win32 platforms", async () => {
        const previousPlatform = process.platform;
        const previousEnv = process.env.MESHCHAT_APPCONTAINER;
        Object.defineProperty(process, "platform", { value: "linux" });
        delete process.env.MESHCHAT_APPCONTAINER;
        try {
            const manager = createBackendProcessManager({
                log: vi.fn(),
                getDefaultStorageDir: () => "/tmp/storage",
                getDefaultReticulumConfigDir: () => "/tmp/reticulum",
                getMainWindowPageKind: () => "loading",
                isQuiting: () => false,
                notifyRenderer: vi.fn(),
                showCrashPage: vi.fn(),
                spawn: spawnMock,
            });
            manager.setUserProvidedArguments([]);
            await manager.spawnBackend("/tmp/ReticulumMeshChatX", { backend: { ok: true, issues: [] } });
            const args = spawnMock.mock.calls[0][1];
            expect(args).not.toContain("--meshchatx-run-module");
            expect(args[0]).toBe("--headless");
        } finally {
            Object.defineProperty(process, "platform", { value: previousPlatform });
            if (previousEnv === undefined) {
                delete process.env.MESHCHAT_APPCONTAINER;
            } else {
                process.env.MESHCHAT_APPCONTAINER = previousEnv;
            }
        }
    });

    it("wraps win32 spawn through the AppContainer launcher when MESHCHAT_APPCONTAINER=1", async () => {
        const previousPlatform = process.platform;
        const previousEnv = process.env.MESHCHAT_APPCONTAINER;
        Object.defineProperty(process, "platform", { value: "win32" });
        process.env.MESHCHAT_APPCONTAINER = "1";
        try {
            const manager = createBackendProcessManager({
                log: vi.fn(),
                getDefaultStorageDir: () => "C:\\Users\\test\\.reticulum-meshchatx",
                getDefaultReticulumConfigDir: () => "C:\\Users\\test\\.reticulum",
                getMainWindowPageKind: () => "loading",
                isQuiting: () => false,
                notifyRenderer: vi.fn(),
                showCrashPage: vi.fn(),
                spawn: spawnMock,
            });
            manager.setUserProvidedArguments([]);
            await manager.spawnBackend("C:\\App\\ReticulumMeshChatX.exe", {
                backend: { ok: true, issues: [] },
            });
            expect(spawnMock).toHaveBeenCalledWith(
                "C:\\App\\ReticulumMeshChatX.exe",
                expect.arrayContaining([
                    "--meshchatx-run-module",
                    "meshchatx.src.backend.appcontainer_launcher",
                    "--headless",
                    "--port",
                    "9337",
                ]),
                expect.objectContaining({ windowsHide: true })
            );
        } finally {
            Object.defineProperty(process, "platform", { value: previousPlatform });
            if (previousEnv === undefined) {
                delete process.env.MESHCHAT_APPCONTAINER;
            } else {
                process.env.MESHCHAT_APPCONTAINER = previousEnv;
            }
        }
    });

    it("wraps win32 spawn through the AppContainer launcher when MESHCHAT_APPCONTAINER=auto", async () => {
        const previousPlatform = process.platform;
        const previousEnv = process.env.MESHCHAT_APPCONTAINER;
        Object.defineProperty(process, "platform", { value: "win32" });
        process.env.MESHCHAT_APPCONTAINER = "auto";
        try {
            const manager = createBackendProcessManager({
                log: vi.fn(),
                getDefaultStorageDir: () => "C:\\Users\\test\\.reticulum-meshchatx",
                getDefaultReticulumConfigDir: () => "C:\\Users\\test\\.reticulum",
                getMainWindowPageKind: () => "loading",
                isQuiting: () => false,
                notifyRenderer: vi.fn(),
                showCrashPage: vi.fn(),
                spawn: spawnMock,
            });
            manager.setUserProvidedArguments([]);
            await manager.spawnBackend("C:\\App\\ReticulumMeshChatX.exe", {
                backend: { ok: true, issues: [] },
            });
            expect(spawnMock).toHaveBeenCalledWith(
                "C:\\App\\ReticulumMeshChatX.exe",
                expect.arrayContaining([
                    "--meshchatx-run-module",
                    "meshchatx.src.backend.appcontainer_launcher",
                    "--headless",
                    "--port",
                    "9337",
                ]),
                expect.objectContaining({ windowsHide: true })
            );
        } finally {
            Object.defineProperty(process, "platform", { value: previousPlatform });
            if (previousEnv === undefined) {
                delete process.env.MESHCHAT_APPCONTAINER;
            } else {
                process.env.MESHCHAT_APPCONTAINER = previousEnv;
            }
        }
    });

    it("skips AppContainer launcher when MESHCHAT_APPCONTAINER=0 on win32", async () => {
        const previousPlatform = process.platform;
        const previousEnv = process.env.MESHCHAT_APPCONTAINER;
        Object.defineProperty(process, "platform", { value: "win32" });
        process.env.MESHCHAT_APPCONTAINER = "0";
        try {
            const manager = createBackendProcessManager({
                log: vi.fn(),
                getDefaultStorageDir: () => "C:\\Users\\test\\.reticulum-meshchatx",
                getDefaultReticulumConfigDir: () => "C:\\Users\\test\\.reticulum",
                getMainWindowPageKind: () => "loading",
                isQuiting: () => false,
                notifyRenderer: vi.fn(),
                showCrashPage: vi.fn(),
                spawn: spawnMock,
            });
            manager.setUserProvidedArguments([]);
            await manager.spawnBackend("C:\\App\\ReticulumMeshChatX.exe", {
                backend: { ok: true, issues: [] },
            });
            const args = spawnMock.mock.calls[0][1];
            expect(args).not.toContain("--meshchatx-run-module");
            expect(args[0]).toBe("--headless");
        } finally {
            Object.defineProperty(process, "platform", { value: previousPlatform });
            if (previousEnv === undefined) {
                delete process.env.MESHCHAT_APPCONTAINER;
            } else {
                process.env.MESHCHAT_APPCONTAINER = previousEnv;
            }
        }
    });

    it("attaches an error listener before the pid check so spawn ENOENT cannot crash", async () => {
        const { EventEmitter } = require("node:events");
        const badProc = new EventEmitter();
        badProc.pid = undefined;
        const manager = createManager({ spawn: vi.fn(() => badProc) });
        manager.setUserProvidedArguments([]);
        await expect(
            manager.spawnBackend("/nonexistent/ReticulumMeshChatX", { backend: { ok: true, issues: [] } })
        ).rejects.toThrow("no PID");
        // The late async spawn error must be consumed by the guard listener.
        expect(() => badProc.emit("error", new Error("spawn ENOENT"))).not.toThrow();
    });

    it("does not add default dir flags when argv uses the --flag=value form", async () => {
        const proc = createFakeChildProcess();
        const spawn = vi.fn(() => proc);
        const manager = createManager({ spawn });
        manager.setUserProvidedArguments(["--storage-dir=/custom/storage", "--reticulum-config-dir=/custom/rns"]);
        await manager.spawnBackend("/tmp/ReticulumMeshChatX", { backend: { ok: true, issues: [] } });
        const args = spawn.mock.calls[0][1];
        expect(args).not.toContain("--storage-dir");
        expect(args).not.toContain("--reticulum-config-dir");
        expect(args).toContain("--storage-dir=/custom/storage");
        expect(args).toContain("--reticulum-config-dir=/custom/rns");
    });

    it("runMaintenanceTask stops the backend, awaits its exit, and tracks the maintenance child", async () => {
        const backendProc = createFakeChildProcess();
        backendProc.kill = vi.fn(() => {
            backendProc.exitCode = 0;
            setImmediate(() => backendProc.emit("exit", 0));
        });
        const maintProc = createFakeChildProcess();
        maintProc.pid = 5555;
        const spawn = vi.fn().mockReturnValueOnce(backendProc).mockReturnValueOnce(maintProc);
        const manager = createManager({ spawn });
        manager.setUserProvidedArguments([]);
        manager.resolveExecutablePath(() => "/tmp/ReticulumMeshChatX");

        await manager.spawnBackend("/tmp/ReticulumMeshChatX", { backend: { ok: true, issues: [] } });
        const promise = manager.runMaintenanceTask(["--restore-db", "/tmp/backup.zip"]);
        await vi.waitFor(() => expect(manager.getChildProcess()).toBe(maintProc));
        expect(backendProc.kill).toHaveBeenCalledWith("SIGTERM");

        maintProc.emit("exit", 0);
        const result = await promise;
        expect(result.ok).toBe(true);
        expect(manager.getChildProcess()).toBeNull();
    });

    it("runMaintenanceTask reports spawn failure without an unhandled error event", async () => {
        const { EventEmitter } = require("node:events");
        const badProc = new EventEmitter();
        badProc.pid = undefined;
        const manager = createManager({ spawn: vi.fn(() => badProc) });
        manager.setUserProvidedArguments([]);
        manager.resolveExecutablePath(() => "/tmp/ReticulumMeshChatX");
        const result = await manager.runMaintenanceTask(["--restore-db", "/tmp/backup.zip"]);
        expect(result.ok).toBe(false);
        expect(() => badProc.emit("error", new Error("spawn ENOENT"))).not.toThrow();
    });
});
