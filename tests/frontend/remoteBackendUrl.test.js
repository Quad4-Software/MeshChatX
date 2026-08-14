import { describe, expect, it } from "vitest";
import {
    LOCAL_BACKEND_URL,
    isValidRemoteBackendUrl,
    normalizeRemoteBackendUrl,
    resolveEffectiveBackendUrl,
} from "../../meshchatx/src/frontend/js/remoteBackendUrl.js";

describe("remoteBackendUrl", () => {
    it("treats empty as local", () => {
        expect(normalizeRemoteBackendUrl("")).toBeNull();
        expect(normalizeRemoteBackendUrl("  ")).toBeNull();
        expect(resolveEffectiveBackendUrl("")).toBe(LOCAL_BACKEND_URL);
        expect(isValidRemoteBackendUrl("")).toBe(true);
    });

    it("normalizes http(s) LAN origins", () => {
        expect(normalizeRemoteBackendUrl("http://192.168.1.10:9337/")).toBe("http://192.168.1.10:9337");
        expect(normalizeRemoteBackendUrl("HTTPS://Mesh.Example:8443/app/")).toBe("https://mesh.example:8443/app");
    });

    it("rejects unsafe URLs", () => {
        expect(normalizeRemoteBackendUrl("javascript:alert(1)")).toBeNull();
        expect(normalizeRemoteBackendUrl("file:///tmp/x")).toBeNull();
        expect(normalizeRemoteBackendUrl("https://user:pass@192.168.1.10:9337")).toBeNull();
        expect(normalizeRemoteBackendUrl("http://127.0.0.1:8000@example.com")).toBeNull();
        expect(isValidRemoteBackendUrl("not a url")).toBe(false);
    });
});
