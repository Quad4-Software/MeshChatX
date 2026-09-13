import { describe, it, expect } from "vitest";
import { normalizeRemoteBackendUrl } from "@/js/remoteBackendUrl.js";

// Independent oracle: only http(s) with a hostname, no userinfo, no fragment,
// and a pathname stripped of trailing slashes passes.
function oracle(raw) {
    if (raw == null) {
        return null;
    }
    const trimmed = String(raw).trim();
    if (!trimmed) {
        return null;
    }
    let url;
    try {
        url = new URL(trimmed);
    } catch {
        return null;
    }
    const scheme = url.protocol.replace(/:$/, "").toLowerCase();
    if (scheme !== "http" && scheme !== "https") {
        return null;
    }
    if (url.username || url.password) {
        return null;
    }
    if (!url.hostname) {
        return null;
    }
    let out = `${scheme}://${url.hostname.toLowerCase()}`;
    if (url.port) {
        out += `:${url.port}`;
    }
    let path = url.pathname || "";
    if (path && path !== "/") {
        while (path.length > 1 && path.endsWith("/")) {
            path = path.slice(0, -1);
        }
        out += path;
    }
    return out;
}

const cases = [
    "",
    "  ",
    null,
    undefined,
    "not a url",
    "http://192.168.1.10:9337/",
    "HTTPS://Mesh.Example:8443/app/",
    "https://mesh.example:8443/app",
    "https://mesh.example:8443/app///",
    "javascript:alert(1)",
    "file:///tmp/x",
    "https://user:pass@192.168.1.10:9337",
    "http://127.0.0.1:8000@example.com",
    "http://user@host.test/api/",
    "https://example.com#frag",
    "https://example.com?query=1",
    "http://[::1]:8000/",
    "http://localhost/",
    "http://127.0.0.1:9337/",
    "http://0.0.0.0:9337/",
    "ftp://files.example/",
    "data:text/html,hello",
    "blob:https://example.com/uuid",
    " https://example.com/ ",
    "https://Example.COM:8443/API/",
];

describe("remoteBackendUrl oracles", () => {
    it.each(cases)("normalizes %j according to the URL oracle", (input) => {
        expect(normalizeRemoteBackendUrl(input)).toBe(oracle(input));
    });
});
