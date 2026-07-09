(function (root, factory) {
    const exported = factory();
    if (typeof module !== "undefined" && module.exports) {
        module.exports = exported;
    }
    root.MeshchatLoadingStatusProbe = exported;
})(typeof globalThis !== "undefined" ? globalThis : window, function () {
    function parseStatusJson(text) {
        if (text == null) {
            return null;
        }
        try {
            return JSON.parse(String(text));
        } catch {
            return null;
        }
    }

    /**
     * Decide whether an HTTP status probe response means the Electron loading
     * page can navigate into the app shell.
     *
     * HTTP may be up while RNS is still starting (`status: "starting"`).
     */
    function evaluateStatusResponse(httpStatus, bodyText) {
        if (Number(httpStatus) !== 200) {
            return {
                ok: false,
                failure: { kind: "http-error", status: Number(httpStatus) || 0 },
            };
        }
        const data = parseStatusJson(bodyText);
        if (!data || typeof data !== "object") {
            return { ok: false, failure: { kind: "invalid-payload" } };
        }
        if (data.status === "failed") {
            return {
                ok: false,
                failure: {
                    kind: "startup-failed",
                    error: typeof data.error === "string" ? data.error : "",
                    stage: data.stage || "failed",
                },
            };
        }
        if (data.status === "ok" || data.status === "starting") {
            return {
                ok: true,
                stage: data.stage || data.status,
                networkReady: !!data.network_ready,
            };
        }
        return { ok: false, failure: { kind: "invalid-payload" } };
    }

    return {
        parseStatusJson,
        evaluateStatusResponse,
    };
});
