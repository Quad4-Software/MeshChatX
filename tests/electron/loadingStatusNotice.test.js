import { describe, expect, it } from "vitest";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const notice = require("../../electron/loadingStatusNotice.js");

describe("electron/loadingStatusNotice", () => {
    it("classifyConnectionIssue prefers backend-exited when runtime not running", () => {
        const r = notice.classifyConnectionIssue(
            [],
            {
                running: false,
                lastExitCode: 1,
            },
            {
                crash: { stderr: "MemoryError: out of memory", stdout: "" },
                paths: { backendLogPath: "C:\\Users\\x\\.reticulum-meshchatx\\logs\\meshchatx.log" },
            }
        );
        expect(r.reason).toBe("backend-exited");
        expect(r.category).toBe("memory");
        expect(r.logHint).toContain("meshchatx.log");
    });

    it("classifyConnectionIssue parses MESHCHAT_MEMORY startup lines", () => {
        const r = notice.classifyConnectionIssue(
            [],
            {
                running: false,
                lastExitCode: 1,
            },
            {
                crash: {
                    stderr: "",
                    stdout: "MESHCHAT_MEMORY: total_mb=4096.0 available_mb=120.0 percent_used=97.0 action=abort emergency=false",
                },
            }
        );
        expect(r.category).toBe("memory");
        expect(r.detail).toContain("120");
    });

    it("classifyConnectionIssue flags loopback blocked", () => {
        const r = notice.classifyConnectionIssue([{ kind: "address-unreachable" }], { running: true });
        expect(r.reason).toBe("loopback-blocked");
    });

    it("classifyConnectionIssue uses starting before network threshold", () => {
        const r = notice.classifyConnectionIssue([{ kind: "network-error" }], { running: true }, { attemptCount: 1 });
        expect(r.reason).toBe("starting");
    });

    it("classifyFetchError maps address unreachable", () => {
        expect(notice.classifyFetchError({ name: "Error", message: "net::ERR_ADDRESS_UNREACHABLE" })).toBe(
            "address-unreachable"
        );
    });

    it("classifyFetchError defaults to network-error", () => {
        expect(notice.classifyFetchError({ name: "TypeError", message: "fetch failed" })).toBe("network-error");
    });
});
