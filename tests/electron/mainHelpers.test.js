import { describe, expect, it } from "vitest";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const {
    getUserProvidedArguments,
    parseArgvFlag,
    resolvePortableStorageRoots,
    formatRenderProcessGoneDetails,
    isLocalBackendUrl,
    shouldOpenInElectronWindow,
} = require("../../electron/mainHelpers.js");
const path = require("node:path");

describe("electron/mainHelpers", () => {
    it("getUserProvidedArguments filters ignored flags and skips argv[0]", () => {
        const argv = ["/app/electron", "--no-https", "--no-sandbox", "--ozone-platform-hint=auto", "--port", "1"];
        expect(getUserProvidedArguments(argv)).toEqual(["--no-https", "--port", "1"]);
    });

    it("formatRenderProcessGoneDetails handles null/undefined", () => {
        expect(formatRenderProcessGoneDetails(null)).toBe("no details");
        expect(formatRenderProcessGoneDetails(undefined)).toBe("no details");
    });

    it("formatRenderProcessGoneDetails serializes reason and exitCode", () => {
        const s = formatRenderProcessGoneDetails({ reason: "crashed", exitCode: 5 });
        expect(s).toContain("crashed");
        expect(s).toContain("5");
    });

    it("isLocalBackendUrl matches localhost backends only", () => {
        expect(isLocalBackendUrl("https://127.0.0.1:9337/api")).toBe(true);
        expect(isLocalBackendUrl("http://localhost:9337/")).toBe(true);
        expect(isLocalBackendUrl("https://127.0.0.1:9337/#/call")).toBe(true);
        expect(isLocalBackendUrl("https://example.com")).toBe(false);
        expect(isLocalBackendUrl("")).toBe(false);
        expect(isLocalBackendUrl("http://127.0.0.1:9337@example.com")).toBe(false);
        expect(isLocalBackendUrl("http://127.0.0.1:9337@example.com/whatever")).toBe(false);
        expect(isLocalBackendUrl("http://127.0.0.1:9337@example.com/#/popout/map")).toBe(false);
        expect(isLocalBackendUrl("https://127.0.0.1:9337@example.com/call.html")).toBe(false);
        expect(isLocalBackendUrl("http://127.0.0.1:80")).toBe(false);
        expect(isLocalBackendUrl("http://localhost")).toBe(false);
        expect(isLocalBackendUrl("file:///etc/passwd")).toBe(false);
    });

    it("shouldOpenInElectronWindow keeps local popouts and call windows in Electron", () => {
        expect(shouldOpenInElectronWindow("https://127.0.0.1:9337/#/popout/map")).toBe(true);
        expect(shouldOpenInElectronWindow("https://127.0.0.1:9337/call.html")).toBe(true);
        expect(shouldOpenInElectronWindow("http://localhost:9337/#/popout/messages/abc")).toBe(true);
        expect(shouldOpenInElectronWindow("blob:https://127.0.0.1:9337/print")).toBe(true);
        expect(shouldOpenInElectronWindow("https://127.0.0.1:9337/rnode-flasher/index.html")).toBe(false);
        expect(shouldOpenInElectronWindow("https://127.0.0.1:9337/?q=/call.html")).toBe(false);
        expect(shouldOpenInElectronWindow("https://example.com/#/popout/map")).toBe(false);
        expect(shouldOpenInElectronWindow("http://127.0.0.1:9337@example.com/#/popout/map")).toBe(false);
        expect(shouldOpenInElectronWindow("http://127.0.0.1:9337@example.com/call.html")).toBe(false);
        expect(shouldOpenInElectronWindow("blob:https://example.com/print")).toBe(false);
        expect(shouldOpenInElectronWindow("blob:http://127.0.0.1:9337@example.com/uuid")).toBe(false);
        expect(shouldOpenInElectronWindow("")).toBe(false);
    });

    it("shouldAllowInWindowNavigation keeps local backend URLs in Electron", () => {
        const { shouldAllowInWindowNavigation } = require("../../electron/mainHelpers.js");
        expect(shouldAllowInWindowNavigation("https://127.0.0.1:9337/#/tools/micron-editor")).toBe(true);
        expect(shouldAllowInWindowNavigation("http://localhost:9337/")).toBe(true);
        expect(shouldAllowInWindowNavigation("blob:https://127.0.0.1:9337/print")).toBe(true);
        expect(shouldAllowInWindowNavigation("https://example.com/")).toBe(false);
        expect(shouldAllowInWindowNavigation("http://127.0.0.1:9337@example.com/whatever")).toBe(false);
        expect(shouldAllowInWindowNavigation("file:///etc/passwd")).toBe(false);
        expect(shouldAllowInWindowNavigation("data:text/html,x")).toBe(false);
        expect(shouldAllowInWindowNavigation("blob:https://example.com/uuid")).toBe(false);
        expect(shouldAllowInWindowNavigation("blob:http://127.0.0.1:9337@example.com/uuid")).toBe(false);
    });

    it("isTrustedShellOrigin allows loading/crash file pages and the local backend only", () => {
        const { isTrustedShellOrigin, isTrustedShellFileUrl } = require("../../electron/mainHelpers.js");
        expect(isTrustedShellFileUrl("file:///opt/meshchatx/electron/loading.html")).toBe(true);
        expect(isTrustedShellFileUrl("file:///C:/Program%20Files/MeshChatX/crash.html")).toBe(true);
        expect(isTrustedShellFileUrl("file:///etc/passwd")).toBe(false);
        expect(isTrustedShellOrigin("file:///opt/meshchatx/electron/loading.html")).toBe(true);
        expect(isTrustedShellOrigin("https://127.0.0.1:9337/#/messages")).toBe(true);
        expect(isTrustedShellOrigin("blob:https://127.0.0.1:9337/print")).toBe(true);
        expect(isTrustedShellOrigin("https://example.com/")).toBe(false);
        expect(isTrustedShellOrigin("http://127.0.0.1:9337@example.com/")).toBe(false);
        expect(isTrustedShellOrigin("data:text/html,x")).toBe(false);
        expect(isTrustedShellOrigin("file:///tmp/evil.html")).toBe(false);
    });

    it("isTrustedIpcEvent uses senderFrame.url then sender.getURL", () => {
        const { isTrustedIpcEvent } = require("../../electron/mainHelpers.js");
        expect(isTrustedIpcEvent({ senderFrame: { url: "https://127.0.0.1:9337/" } })).toBe(true);
        expect(isTrustedIpcEvent({ senderFrame: { url: "http://127.0.0.1:9337@example.com/" } })).toBe(false);
        expect(isTrustedIpcEvent({ senderFrame: { url: "https://example.com/" } })).toBe(false);
        expect(
            isTrustedIpcEvent({
                sender: { getURL: () => "file:///opt/meshchatx/electron/loading.html" },
            })
        ).toBe(true);
        expect(isTrustedIpcEvent({})).toBe(false);
        expect(isTrustedIpcEvent(null)).toBe(false);
    });

    it("parseArgvFlag reads a value following the flag", () => {
        expect(parseArgvFlag(["--storage-dir", "/mnt/persist"], "--storage-dir")).toBe("/mnt/persist");
    });

    it("parseArgvFlag returns null when the flag is missing or has no value", () => {
        expect(parseArgvFlag(["--headless"], "--storage-dir")).toBeNull();
        expect(parseArgvFlag(["--storage-dir"], "--storage-dir")).toBeNull();
        expect(parseArgvFlag(["--storage-dir", "--headless"], "--storage-dir")).toBeNull();
    });
});

describe("electron/mainHelpers resolvePortableStorageRoots (portable mode)", () => {
    const homeDir = path.join("home", "user");

    function resolve(overrides = {}) {
        return resolvePortableStorageRoots({
            argv: ["/app/electron"],
            env: {},
            homeDir,
            isWindows: false,
            portableExecutableDir: null,
            ...overrides,
        });
    }

    it("defaults to the home directory when nothing is configured", () => {
        expect(resolve()).toEqual({
            storageDir: path.join(homeDir, ".reticulum-meshchatx"),
            reticulumConfigDir: path.join(homeDir, ".reticulum"),
        });
    });

    it("derives storage and reticulum roots from --data-dir", () => {
        const roots = resolve({ argv: ["/app/electron", "--data-dir", "/mnt/tails/persist"] });
        expect(roots).toEqual({
            storageDir: path.resolve("/mnt/tails/persist", "storage"),
            reticulumConfigDir: path.resolve("/mnt/tails/persist", ".reticulum"),
        });
    });

    it("derives storage and reticulum roots from MESHCHAT_DATA_DIR", () => {
        const roots = resolve({ env: { MESHCHAT_DATA_DIR: "/mnt/tails/persist" } });
        expect(roots).toEqual({
            storageDir: path.resolve("/mnt/tails/persist", "storage"),
            reticulumConfigDir: path.resolve("/mnt/tails/persist", ".reticulum"),
        });
    });

    it("explicit --storage-dir and --reticulum-config-dir win over --data-dir", () => {
        const roots = resolve({
            argv: ["/app/electron", "--data-dir", "/mnt/tails/persist", "--storage-dir", "/mnt/tails/custom-storage"],
        });
        expect(roots.storageDir).toBe("/mnt/tails/custom-storage");
        expect(roots.reticulumConfigDir).toBe(path.resolve("/mnt/tails/persist", ".reticulum"));
    });

    it("explicit MESHCHAT_STORAGE_DIR / MESHCHAT_RETICULUM_CONFIG_DIR env vars win over MESHCHAT_DATA_DIR", () => {
        const roots = resolve({
            env: {
                MESHCHAT_DATA_DIR: "/mnt/tails/persist",
                MESHCHAT_STORAGE_DIR: "/mnt/tails/custom-storage",
            },
        });
        expect(roots.storageDir).toBe("/mnt/tails/custom-storage");
        expect(roots.reticulumConfigDir).toBe(path.resolve("/mnt/tails/persist", ".reticulum"));
    });

    it("argv flags win over env vars for the same setting", () => {
        const roots = resolve({
            argv: ["/app/electron", "--data-dir", "/mnt/argv-persist"],
            env: { MESHCHAT_DATA_DIR: "/mnt/env-persist" },
        });
        expect(roots.storageDir).toBe(path.resolve("/mnt/argv-persist", "storage"));
    });

    it("falls back to the Windows portable executable directory when set", () => {
        const roots = resolve({
            isWindows: true,
            portableExecutableDir: "E:\\Portable",
        });
        expect(roots).toEqual({
            storageDir: path.join("E:\\Portable", ".reticulum-meshchatx"),
            reticulumConfigDir: path.join("E:\\Portable", ".reticulum"),
        });
    });

    it("ignores the Windows portable executable directory on non-Windows platforms", () => {
        const roots = resolve({
            isWindows: false,
            portableExecutableDir: "/mnt/portable",
        });
        expect(roots.storageDir).toBe(path.join(homeDir, ".reticulum-meshchatx"));
    });

    it("--data-dir wins over the Windows portable executable directory", () => {
        const roots = resolve({
            argv: ["/app/electron", "--data-dir", "/mnt/tails/persist"],
            isWindows: true,
            portableExecutableDir: "E:\\Portable",
        });
        expect(roots.storageDir).toBe(path.resolve("/mnt/tails/persist", "storage"));
    });
});
