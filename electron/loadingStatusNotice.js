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

    function parseMemoryLogLine(text) {
        if (!text || typeof text !== "string") {
            return null;
        }
        for (const rawLine of text.split(/\r?\n/)) {
            const line = rawLine.trim();
            if (!line.startsWith("MESHCHAT_MEMORY:")) {
                continue;
            }
            const parsed = {};
            const payload = line.slice("MESHCHAT_MEMORY:".length).trim();
            for (const token of payload.split(/\s+/)) {
                const idx = token.indexOf("=");
                if (idx <= 0) {
                    continue;
                }
                const key = token.slice(0, idx);
                const value = token.slice(idx + 1);
                if (key === "total_mb" || key === "available_mb" || key === "percent_used") {
                    const num = Number(value);
                    if (Number.isFinite(num)) {
                        parsed[key] = num;
                    }
                } else {
                    parsed[key] = value;
                }
            }
            return Object.keys(parsed).length > 0 ? parsed : null;
        }
        return null;
    }

    /**
     * @param {string} stderr
     * @param {string} stdout
     * @param {number|null|undefined} exitCode
     * @returns {{ category: string, summary: string, hints: string[] }}
     */
    function diagnoseBackendCrash(stderr, stdout, exitCode) {
        const combined = `${stdout || ""}\n${stderr || ""}`.toLowerCase();
        const rawCombined = `${stdout || ""}\n${stderr || ""}`;
        const hints = [];
        const memoryLine = parseMemoryLogLine(rawCombined);

        if (memoryLine) {
            const available = Number(memoryLine.available_mb);
            const action = String(memoryLine.action || "");
            if (action === "abort" || (Number.isFinite(available) && available < 200)) {
                hints.push("Close other apps to free RAM, then relaunch.");
                hints.push("Try Emergency Mode if the device has 4 GB RAM or less.");
                return {
                    category: "memory",
                    summary: Number.isFinite(available)
                        ? `The backend reported critically low memory (${available.toFixed(0)} MB available).`
                        : "The backend aborted startup due to critically low memory.",
                    hints,
                };
            }
            if (action === "warn") {
                hints.push("Try Emergency Mode if the device has 4 GB RAM or less.");
                return {
                    category: "memory",
                    summary: Number.isFinite(available)
                        ? `The backend detected limited memory (${available.toFixed(0)} MB available).`
                        : "The backend detected limited system memory during startup.",
                    hints,
                };
            }
        }

        if (
            combined.includes("memoryerror") ||
            combined.includes("out of memory") ||
            combined.includes("cannot allocate memory")
        ) {
            hints.push("Close other apps to free RAM, then relaunch.");
            hints.push("Try Emergency Mode if the device has 4 GB RAM or less.");
            return {
                category: "memory",
                summary: "The backend likely ran out of memory during startup.",
                hints,
            };
        }

        if (
            combined.includes("address already in use") ||
            combined.includes("eaddrinuse") ||
            combined.includes("only one usage of each socket")
        ) {
            hints.push("End any ReticulumMeshChatX.exe process in Task Manager, then relaunch.");
            return {
                category: "port-conflict",
                summary: "Port 9337 is already in use.",
                hints,
            };
        }

        if (
            combined.includes("eacces") ||
            combined.includes("eperm") ||
            combined.includes("permission denied") ||
            combined.includes("access is denied")
        ) {
            hints.push("Ensure the MeshChatX data folder is writable.");
            return {
                category: "permission",
                summary: "The backend could not access a required file or folder.",
                hints,
            };
        }

        if (combined.includes("!!! application crash detected !!!")) {
            hints.push("Open meshchatx.log for the full diagnostic trace from the crash recovery engine.");
            return {
                category: "python-crash",
                summary: "The backend crash recovery system reported a fatal Python error.",
                hints,
            };
        }

        if (exitCode != null && exitCode !== 0) {
            hints.push("Open the logs folder below and review meshchatx.log and last-backend-crash.json.");
            return {
                category: "exit-code",
                summary: `The backend exited with code ${exitCode}.`,
                hints,
            };
        }

        return {
            category: "unknown",
            summary: "The backend stopped before the UI could connect.",
            hints: ["Review the saved crash report and meshchatx.log for details."],
        };
    }

    function formatLogPathHint(paths) {
        if (!paths || typeof paths !== "object") {
            return "";
        }
        if (paths.backendLogPath) {
            return `Logs: ${paths.backendLogPath}`;
        }
        if (paths.logsDir) {
            return `Logs folder: ${paths.logsDir}`;
        }
        return "";
    }

    /**
     * @param {unknown[]} failures
     * @param {object|null} runtimeState
     * @param {object} options
     * @returns {object}
     */
    function classifyConnectionIssue(failures, runtimeState, options) {
        const entries = Array.isArray(failures) ? failures : [];
        const state = runtimeState && typeof runtimeState === "object" ? runtimeState : null;
        const opts = options && typeof options === "object" ? options : {};
        const attemptCount = Number(opts.attemptCount) || 0;
        const networkWarnAfterAttempts = Number(opts.networkWarnAfterAttempts) || 24;
        const crash = opts.crash && typeof opts.crash === "object" ? opts.crash : null;
        const paths = opts.paths && typeof opts.paths === "object" ? opts.paths : null;

        if (state && state.running === false && state.lastExitCode != null) {
            const diagnosis = diagnoseBackendCrash(crash?.stderr || "", crash?.stdout || "", state.lastExitCode);
            const logHint = formatLogPathHint(paths);
            const detailParts = [diagnosis.summary, ...diagnosis.hints];
            if (logHint) {
                detailParts.push(logHint);
            }
            return {
                reason: "backend-exited",
                headline: "The backend process stopped unexpectedly.",
                detail: detailParts.join(" "),
                category: diagnosis.category,
                exitCode: state.lastExitCode,
                hints: diagnosis.hints,
                logHint,
                crash,
                paths,
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
        classifyConnectionIssue,
        classifyFetchError,
        diagnoseBackendCrash,
        formatLogPathHint,
    };
});
