import { describe, expect, it, vi } from "vitest";
import { createRendererCrashHandler, describeExitCode, disableGpuMarkerPath } from "../../electron/rendererCrash.js";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

function flush() {
    return new Promise((resolve) => setImmediate(resolve));
}

function createFixture(overrides = {}) {
    const webContents = { id: 1 };
    const win = {
        webContents,
        isDestroyed: () => false,
    };
    const state = {
        win,
        webContents,
        quiting: false,
        hwAccel: true,
        nowTs: 1000000,
        openedPaths: [],
        relaunches: 0,
        quits: 0,
        logs: [],
        storageDir: fs.mkdtempSync(path.join(os.tmpdir(), "meshchatx-renderercrash-")),
        dumpsDir: path.join(os.tmpdir(), "meshchatx-dumps"),
    };
    const showMessageBox = vi.fn(async () => ({ response: 0 }));
    const handler = createRendererCrashHandler({
        dialog: {},
        shell: {
            openPath: async (target) => {
                state.openedPaths.push(target);
                return "";
            },
        },
        log: (message) => state.logs.push(message),
        getMainWindow: () => state.win,
        isQuiting: () => state.quiting,
        getStorageDir: () => state.storageDir,
        getCrashDumpsDir: () => state.dumpsDir,
        isHardwareAccelerationEnabled: () => state.hwAccel,
        now: () => state.nowTs,
        defer: (fn) => fn(),
        relaunch: () => {
            state.relaunches += 1;
        },
        requestQuit: () => {
            state.quits += 1;
        },
        showMessageBox,
        ...overrides,
    });
    return { state, handler, showMessageBox };
}

describe("electron/rendererCrash", () => {
    it("ignores non-crash reasons without showing a dialog", () => {
        const { state, handler, showMessageBox } = createFixture();
        handler.handle(state.webContents, { reason: "clean-exit", exitCode: 0 });
        handler.handle(state.webContents, { reason: "killed", exitCode: 0 });
        expect(showMessageBox).not.toHaveBeenCalled();
        expect(state.relaunches).toBe(0);
    });

    it("ignores crashes from other webContents", () => {
        const { handler, showMessageBox } = createFixture();
        handler.handle({ id: 99 }, { reason: "crashed", exitCode: -2147483645 });
        expect(showMessageBox).not.toHaveBeenCalled();
    });

    it("ignores crashes while quitting or with a destroyed window", () => {
        const { state, handler, showMessageBox } = createFixture();
        state.quiting = true;
        handler.handle(state.webContents, { reason: "crashed", exitCode: 1 });
        state.quiting = false;
        state.win = null;
        handler.handle(state.webContents, { reason: "crashed", exitCode: 1 });
        expect(showMessageBox).not.toHaveBeenCalled();
    });

    it("relaunches when the default button is chosen", async () => {
        const { state, handler, showMessageBox } = createFixture();
        handler.handle(state.webContents, { reason: "crashed", exitCode: -2147483645 });
        await flush();
        expect(showMessageBox).toHaveBeenCalledTimes(1);
        expect(state.relaunches).toBe(1);
        expect(state.quits).toBe(0);
    });

    it("shows a dialog with crash details and the dumps path", async () => {
        const { state, handler, showMessageBox } = createFixture();
        handler.handle(state.webContents, { reason: "crashed", exitCode: -2147483645 });
        await flush();
        const options = showMessageBox.mock.calls[0][1];
        expect(options.detail).toContain("crashed");
        expect(options.detail).toContain("0x80000003");
        expect(options.detail).toContain(state.dumpsDir);
        expect(options.buttons).toHaveLength(4);
    });

    it("writes the disable-gpu marker before relaunching without GPU", async () => {
        const { state, handler } = createFixture({
            showMessageBox: vi.fn(async () => ({ response: 1 })),
        });
        try {
            handler.handle(state.webContents, { reason: "crashed", exitCode: -2147483645 });
            await flush();
            expect(fs.existsSync(disableGpuMarkerPath(state.storageDir))).toBe(true);
            expect(state.relaunches).toBe(1);
        } finally {
            fs.rmSync(state.storageDir, { recursive: true, force: true });
        }
    });

    it("opens the dumps folder then re-prompts", async () => {
        const showMessageBox = vi.fn().mockResolvedValueOnce({ response: 2 }).mockResolvedValueOnce({ response: 3 });
        const { state, handler } = createFixture({ showMessageBox });
        handler.handle(state.webContents, { reason: "crashed", exitCode: 1 });
        await flush();
        expect(state.openedPaths).toEqual([state.dumpsDir]);
        expect(showMessageBox).toHaveBeenCalledTimes(2);
        expect(state.quits).toBe(1);
    });

    it("quits when the quit button is chosen", async () => {
        const { state, handler } = createFixture({
            showMessageBox: vi.fn(async () => ({ response: 3 })),
        });
        handler.handle(state.webContents, { reason: "abnormal-exit", exitCode: 5 });
        await flush();
        expect(state.quits).toBe(1);
        expect(state.relaunches).toBe(0);
    });

    it("suppresses a second dialog while one is already open", async () => {
        let release;
        const showMessageBox = vi.fn(() => new Promise((resolve) => (release = resolve)));
        const { state, handler } = createFixture({ showMessageBox });
        handler.handle(state.webContents, { reason: "crashed", exitCode: 1 });
        handler.handle(state.webContents, { reason: "crashed", exitCode: 1 });
        await flush();
        expect(showMessageBox).toHaveBeenCalledTimes(1);
        release({ response: 3 });
        await flush();
        expect(state.quits).toBe(1);
    });

    it("auto-disables GPU and relaunches after a GPU crash storm", async () => {
        const { state, handler } = createFixture();
        try {
            for (let i = 0; i < 2; i += 1) {
                handler.handleChildProcessGone({ type: "GPU", reason: "crashed", exitCode: -2147483645 });
            }
            expect(state.relaunches).toBe(0);
            handler.handleChildProcessGone({ type: "GPU", reason: "crashed", exitCode: -2147483645 });
            expect(fs.existsSync(disableGpuMarkerPath(state.storageDir))).toBe(true);
            expect(state.relaunches).toBe(1);
            // A renderer crash during the storm must not also open the dialog
            handler.handle(state.webContents, { reason: "crashed", exitCode: -2147483645 });
            await flush();
            expect(state.relaunches).toBe(1);
        } finally {
            fs.rmSync(state.storageDir, { recursive: true, force: true });
        }
    });

    it("ignores non-GPU and non-crash child process exits", () => {
        const { state, handler } = createFixture();
        for (let i = 0; i < 5; i += 1) {
            handler.handleChildProcessGone({ type: "Utility", reason: "crashed", exitCode: 1 });
            handler.handleChildProcessGone({ type: "GPU", reason: "clean-exit", exitCode: 0 });
        }
        expect(state.relaunches).toBe(0);
    });

    it("does not auto-recover when GPU acceleration is already off", () => {
        const { state, handler } = createFixture();
        state.hwAccel = false;
        for (let i = 0; i < 5; i += 1) {
            handler.handleChildProcessGone({ type: "GPU", reason: "crashed", exitCode: 1 });
        }
        expect(state.relaunches).toBe(0);
    });

    it("does not auto-recover when the disable-gpu marker already exists", () => {
        const { state, handler } = createFixture();
        try {
            fs.writeFileSync(disableGpuMarkerPath(state.storageDir), "manual\n");
            for (let i = 0; i < 5; i += 1) {
                handler.handleChildProcessGone({ type: "GPU", reason: "crashed", exitCode: 1 });
            }
            expect(state.relaunches).toBe(0);
        } finally {
            fs.rmSync(state.storageDir, { recursive: true, force: true });
        }
    });

    it("does not auto-recover without a main window or while quitting", () => {
        const { state, handler } = createFixture();
        state.win = null;
        for (let i = 0; i < 5; i += 1) {
            handler.handleChildProcessGone({ type: "GPU", reason: "crashed", exitCode: 1 });
        }
        expect(state.relaunches).toBe(0);
        state.win = { webContents: state.webContents, isDestroyed: () => false };
        state.quiting = true;
        for (let i = 0; i < 5; i += 1) {
            handler.handleChildProcessGone({ type: "GPU", reason: "crashed", exitCode: 1 });
        }
        expect(state.relaunches).toBe(0);
    });

    it("only counts GPU crashes inside the storm window", () => {
        const { state, handler } = createFixture();
        handler.handleChildProcessGone({ type: "GPU", reason: "crashed", exitCode: 1 });
        handler.handleChildProcessGone({ type: "GPU", reason: "crashed", exitCode: 1 });
        state.nowTs += 21000;
        handler.handleChildProcessGone({ type: "GPU", reason: "crashed", exitCode: 1 });
        expect(state.relaunches).toBe(0);
        handler.handleChildProcessGone({ type: "GPU", reason: "crashed", exitCode: 1 });
        handler.handleChildProcessGone({ type: "GPU", reason: "crashed", exitCode: 1 });
        expect(state.relaunches).toBe(1);
    });

    it("formats signed exit codes as hex", () => {
        expect(describeExitCode(-2147483645)).toBe("-2147483645 (0x80000003)");
        expect(describeExitCode(null)).toBe("unknown");
        expect(describeExitCode(1)).toBe("1 (0x00000001)");
    });
});
