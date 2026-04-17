import { describe, expect, it } from "vitest";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const { classifyConnectionIssue, classifyFetchError } = require("../../electron/loadingStatusNotice.js");

describe("loadingStatusNotice", () => {
    it("classifies backend exits before connection succeeds", () => {
        const issue = classifyConnectionIssue([], {
            running: false,
            lastExitCode: 1,
        });
        expect(issue.reason).toBe("backend-exited");
        expect(issue.headline).toContain("stopped");
    });

    it("classifies address-unreachable network errors as loopback blocks", () => {
        const issue = classifyConnectionIssue([{ kind: "address-unreachable" }, { kind: "network-error" }]);
        expect(issue.reason).toBe("loopback-blocked");
        expect(issue.detail).toContain("firewall");
    });

    it("classifies HTTP 5xx failures as backend-side startup errors", () => {
        const issue = classifyConnectionIssue([{ kind: "http-error", status: 503 }]);
        expect(issue.reason).toBe("backend-http-error");
        expect(issue.headline).toContain("internal error");
    });

    it("delays generic network-blocked warnings while backend may still be starting", () => {
        const issue = classifyConnectionIssue([{ kind: "network-error" }], null, {
            attemptCount: 10,
            networkWarnAfterAttempts: 24,
        });
        expect(issue.reason).toBe("starting");
    });

    it("shows generic network-blocked warning after startup grace period", () => {
        const issue = classifyConnectionIssue([{ kind: "network-error" }], null, {
            attemptCount: 30,
            networkWarnAfterAttempts: 24,
        });
        expect(issue.reason).toBe("network-blocked");
        expect(issue.detail).toContain("firewall");
    });

    it("classifies invalid payload responses as backend response issues", () => {
        const issue = classifyConnectionIssue([{ kind: "invalid-payload" }]);
        expect(issue.reason).toBe("backend-invalid-response");
    });

    it("parses ERR_ADDRESS_UNREACHABLE fetch errors", () => {
        const kind = classifyFetchError(new TypeError("net::ERR_ADDRESS_UNREACHABLE"));
        expect(kind).toBe("address-unreachable");
    });

    it("treats other fetch failures as generic network errors", () => {
        const kind = classifyFetchError(new TypeError("Failed to fetch"));
        expect(kind).toBe("network-error");
    });
});
