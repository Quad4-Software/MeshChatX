(function (root, factory) {
    const exported = factory();
    if (typeof module !== "undefined" && module.exports) {
        module.exports = exported;
    }
    root.MeshchatLoadingStatusNotice = exported;
})(typeof globalThis !== "undefined" ? globalThis : window, function () {
    function toLowerText(value) {
        if (value == null) {
            return "";
        }
        return String(value).toLowerCase();
    }

    function classifyConnectionIssue(failures, runtimeState, options) {
        const entries = Array.isArray(failures) ? failures : [];
        const state = runtimeState && typeof runtimeState === "object" ? runtimeState : null;
        const opts = options && typeof options === "object" ? options : {};
        const attemptCount = Number(opts.attemptCount) || 0;
        const networkWarnAfterAttempts = Number(opts.networkWarnAfterAttempts) || 24;

        if (state && state.running === false && state.lastExitCode != null) {
            return {
                reason: "backend-exited",
                headline: "The backend process stopped unexpectedly.",
                detail: "Please restart MeshChatX. If this keeps happening, review crash logs.",
            };
        }

        const hasAddressUnreachable = entries.some((entry) => entry && entry.kind === "address-unreachable");
        if (hasAddressUnreachable) {
            return {
                reason: "loopback-blocked",
                headline: "Cannot reach local backend on 127.0.0.1:9337.",
                detail: "A firewall, VPN, sandbox, or loopback policy may be blocking local connections.",
            };
        }

        const hasNetworkError = entries.some((entry) => entry && entry.kind === "network-error");
        if (hasNetworkError) {
            if (attemptCount < networkWarnAfterAttempts) {
                return {
                    reason: "starting",
                    headline: "Waiting for backend startup.",
                    detail: "MeshChatX is still initializing services.",
                };
            }
            return {
                reason: "network-blocked",
                headline: "Still waiting for local backend connection.",
                detail: "If startup stays stuck, firewall or network filtering software may be blocking localhost traffic.",
            };
        }

        const hasServerError = entries.some(
            (entry) => entry && entry.kind === "http-error" && Number(entry.status) >= 500
        );
        if (hasServerError) {
            return {
                reason: "backend-http-error",
                headline: "Backend is running but reported an internal error.",
                detail: "MeshChatX will keep retrying while the backend finishes startup.",
            };
        }

        const hasInvalidPayload = entries.some((entry) => entry && entry.kind === "invalid-payload");
        if (hasInvalidPayload) {
            return {
                reason: "backend-invalid-response",
                headline: "Backend responded with invalid startup data.",
                detail: "MeshChatX will continue retrying while the backend stabilizes.",
            };
        }

        return {
            reason: "starting",
            headline: "Waiting for backend startup.",
            detail: "MeshChatX is still initializing services.",
        };
    }

    function classifyFetchError(error) {
        const message = `${toLowerText(error && error.name)} ${toLowerText(error && error.message)}`.trim();
        if (
            message.includes("err_address_unreachable") ||
            message.includes("address_unreachable") ||
            message.includes("ehostunreach")
        ) {
            return "address-unreachable";
        }
        return "network-error";
    }

    return {
        classifyConnectionIssue: classifyConnectionIssue,
        classifyFetchError: classifyFetchError,
    };
});
