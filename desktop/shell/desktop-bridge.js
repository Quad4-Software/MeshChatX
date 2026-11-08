/* MeshChatX desktop bridge (Wails).
 * Loaded synchronously in <head> before the app bundle. Provides
 * window.desktop with the same surface the Electron preload exposed,
 * plus internal helpers window.__desktopBridge used by Go replies/events.
 * No-ops entirely in plain browsers (no native postMessage channel).
 */
(function () {
    "use strict";

    // Only the top-level frame may use the bridge: sandboxed subframes share
    // the postMessage channel on Linux/Windows but must never reach Go.
    if (window.top !== window) {
        return;
    }

    function nativePostMessage() {
        try {
            if (
                window.webkit &&
                window.webkit.messageHandlers &&
                window.webkit.messageHandlers.external &&
                typeof window.webkit.messageHandlers.external.postMessage === "function"
            ) {
                return function (payload) {
                    window.webkit.messageHandlers.external.postMessage(payload);
                };
            }
        } catch {
            /* best-effort */
        }
        try {
            if (window.chrome && window.chrome.webview && typeof window.chrome.webview.postMessage === "function") {
                return function (payload) {
                    window.chrome.webview.postMessage(payload);
                };
            }
        } catch {
            /* best-effort */
        }
        return null;
    }

    var postMessage = nativePostMessage();
    if (!postMessage) {
        return;
    }

    var WAILS_ASSET_ORIGINS = {
        "wails://localhost": true,
        "http://wails.localhost": true,
        "https://wails.localhost": true,
        "http://wails.localhost:80": true,
        "https://wails.localhost:443": true,
    };
    var BACKEND_HOSTS = { "127.0.0.1": true, localhost: true, "[::1]": true, "::1": true };
    var BACKEND_PORTS = { 9337: true, 9338: true };

    // The app server may bind a random loopback port when 9338 is busy; the
    // page itself is served from that origin, so "same port as this page"
    // is trusted too. Go re-checks the registered port strictly.
    function pageBackendPort() {
        try {
            var u = new URL(window.location.href);
            if (u.protocol !== "http:" && u.protocol !== "https:") {
                return "";
            }
            var host = u.hostname;
            if (host.charAt(0) === "[") {
                host = host.slice(1, -1);
            }
            if (!BACKEND_HOSTS[host]) {
                return "";
            }
            return u.port || (u.protocol === "https:" ? "443" : "80");
        } catch {
            return "";
        }
    }
    var SELF_BACKEND_PORT = pageBackendPort();

    function parseUrlMaybe(raw) {
        try {
            return new URL(String(raw), window.location.href);
        } catch {
            return null;
        }
    }

    function isLocalBackendUrl(raw) {
        if (typeof raw !== "string") {
            return false;
        }
        var url;
        try {
            url = new URL(raw);
        } catch {
            return false;
        }
        if (url.protocol !== "http:" && url.protocol !== "https:") {
            return false;
        }
        if (url.username || url.password) {
            return false;
        }
        var host = url.hostname;
        if (host.charAt(0) === "[") {
            host = host.slice(1, -1);
        }
        if (!BACKEND_HOSTS[host]) {
            return false;
        }
        var port = url.port || (url.protocol === "https:" ? "443" : "80");
        return BACKEND_PORTS[port] === true || (SELF_BACKEND_PORT !== "" && port === SELF_BACKEND_PORT);
    }

    function isTrustedBlobUrl(raw) {
        if (typeof raw !== "string" || raw.indexOf("blob:") !== 0) {
            return false;
        }
        var inner = raw.slice(5);
        // Find the path slash AFTER the scheme's "://" — a bare indexOf("/")
        // matches the slash inside "https://" and yields a relative path that
        // isLocalBackendUrl always rejects.
        var schemeEnd = inner.indexOf("://");
        var slash = schemeEnd < 0 ? -1 : inner.indexOf("/", schemeEnd + 3);
        if (slash < 0) {
            return false;
        }
        var innerUrl = inner.slice(slash + 1);
        return isLocalBackendUrl(innerUrl);
    }

    function isTrustedShellOrigin(href) {
        if (typeof href !== "string" || !href) {
            return false;
        }
        if (WAILS_ASSET_ORIGINS[href.split("#")[0].split("?")[0]] && href.indexOf("wails") === 0) {
            return true;
        }
        var url = parseUrlMaybe(href);
        if (!url) {
            return false;
        }
        var scheme = url.protocol;
        var authority = scheme + "//" + url.host;
        if (WAILS_ASSET_ORIGINS[authority] || WAILS_ASSET_ORIGINS[scheme + "://" + url.hostname]) {
            return true;
        }
        if (scheme === "blob:") {
            return isTrustedBlobUrl(href);
        }
        return isLocalBackendUrl(href);
    }

    var nextId = 1;
    var pending = Object.create(null);
    var listeners = Object.create(null);
    // Per-page-load capability token pushed by Go via __init. Kept only in
    // this closure — never on window/globals/DOM — so sandboxed subframes
    // (which share postMessage but not this frame's closures) cannot call
    // bridge methods. Messages sent before __init are queued briefly.
    var bridgeToken = "";
    var initQueue = [];
    var MAX_INIT_QUEUE = 64;

    function safeJsonParse(text, fallback) {
        try {
            return JSON.parse(text);
        } catch {
            return fallback;
        }
    }

    function resolve(id, ok, payloadJson) {
        var entry = pending[id];
        if (!entry) {
            return;
        }
        delete pending[id];
        var payload = safeJsonParse(payloadJson, null);
        if (ok) {
            entry.resolve(payload);
        } else {
            var message = "Desktop bridge error";
            if (payload && typeof payload.error === "string" && payload.error) {
                message = payload.error;
            }
            entry.reject(new Error(message));
        }
    }

    // Deep links can arrive before the app registers its listener; keep a few
    // and replay them to the first listener.
    var replayable = { "open-protocol-link": true };
    var replayBuffer = Object.create(null);
    var MAX_REPLAY = 8;

    function emit(name, payloadJson) {
        var cbs = listeners[name];
        var payload = safeJsonParse(payloadJson, null);
        if (!cbs || !cbs.length) {
            if (replayable[name]) {
                var buf = replayBuffer[name] || (replayBuffer[name] = []);
                if (buf.length >= MAX_REPLAY) {
                    buf.shift();
                }
                buf.push(payload);
            }
            return;
        }
        for (var i = 0; i < cbs.length; i++) {
            try {
                cbs[i](payload);
            } catch {
                /* best-effort */
            }
        }
    }

    window.__desktopBridge = {
        resolve: resolve,
        emit: emit,
        ready: true,
        // Called once per page load by Go's ExecJS (main frame only).
        __init: function (token) {
            if (typeof token !== "string" || !token) {
                return;
            }
            bridgeToken = token;
            var q = initQueue;
            initQueue = [];
            for (var i = 0; i < q.length; i++) {
                q[i]();
            }
        },
    };

    // Wails only flushes queued ExecJS replies after the page announces
    // "wails:runtime:ready"; the framework consumes this message before it
    // reaches RawMessageHandler, and it is what makes Go->JS replies work on
    // pages that do not load the Wails JS runtime.
    try {
        postMessage("wails:runtime:ready");
    } catch {
        /* best-effort */
    }

    function invokeTrusted(method, args) {
        return new Promise(function (resolvePromise, rejectPromise) {
            if (!isTrustedShellOrigin(window.location.href)) {
                rejectPromise(new Error("MeshChatX desktop bridge blocked for this origin"));
                return;
            }
            var send = function () {
                var id = nextId++;
                pending[id] = { resolve: resolvePromise, reject: rejectPromise };
                try {
                    postMessage(JSON.stringify({ v: 1, id: id, method: method, args: args || [], t: bridgeToken }));
                } catch (e) {
                    delete pending[id];
                    rejectPromise(e);
                }
            };
            if (!bridgeToken) {
                if (initQueue.length >= MAX_INIT_QUEUE) {
                    rejectPromise(new Error("MeshChatX desktop bridge not initialised"));
                    return;
                }
                var timer = setTimeout(function () {
                    rejectPromise(new Error("MeshChatX desktop bridge not initialised"));
                }, 10000);
                initQueue.push(function () {
                    clearTimeout(timer);
                    send();
                });
                return;
            }
            send();
        });
    }

    function on(channel, callback) {
        if (typeof callback !== "function") {
            return function () {};
        }
        if (!listeners[channel]) {
            listeners[channel] = [];
        }
        var wrapper = function (payload) {
            try {
                callback(payload);
            } catch {
                /* best-effort */
            }
        };
        listeners[channel].push(wrapper);
        var buffered = replayBuffer[channel];
        if (buffered && buffered.length) {
            replayBuffer[channel] = [];
            setTimeout(function () {
                for (var i = 0; i < buffered.length; i++) {
                    wrapper(buffered[i]);
                }
            }, 0);
        }
        return function () {
            var arr = listeners[channel];
            if (!arr) {
                return;
            }
            var idx = arr.indexOf(wrapper);
            if (idx >= 0) {
                arr.splice(idx, 1);
            }
        };
    }

    function detectPlatform() {
        var ua = String((window.navigator && window.navigator.userAgent) || "").toLowerCase();
        var platform = String((window.navigator && window.navigator.platform) || "").toLowerCase();
        if (ua.indexOf("windows") >= 0 || platform.indexOf("win") === 0) {
            return "win32";
        }
        if (ua.indexOf("mac os") >= 0 || ua.indexOf("macintosh") >= 0 || platform.indexOf("mac") === 0) {
            return "darwin";
        }
        return "linux";
    }

    var desktop = {
        appVersion: function () {
            return invokeTrusted("app-version");
        },
        runtimeInfo: function () {
            return invokeTrusted("runtime-info");
        },
        alert: function (message) {
            return invokeTrusted("alert", [message]);
        },
        confirm: function (message) {
            return invokeTrusted("confirm", [message]);
        },
        prompt: function (message, defaultValue) {
            return invokeTrusted("prompt", [message, defaultValue == null ? "" : String(defaultValue)]);
        },
        relaunch: function () {
            return invokeTrusted("relaunch");
        },
        relaunchEmergency: function () {
            return invokeTrusted("relaunch-emergency");
        },
        relaunchAutoRecover: function () {
            return invokeTrusted("relaunch-auto-recover");
        },
        applyUpdate: function () {
            return invokeTrusted("update-apply");
        },
        getCrashRecoveryInfo: function () {
            return invokeTrusted("crash-recovery-info");
        },
        restoreDatabaseBackup: function (backupPath) {
            return invokeTrusted("restore-database-backup", [backupPath]);
        },
        pickDatabaseBackup: function () {
            return invokeTrusted("pick-database-backup");
        },
        shutdown: function () {
            return invokeTrusted("shutdown");
        },
        getCloseSettings: function () {
            return invokeTrusted("get-close-settings");
        },
        setCloseSettings: function (partial) {
            return invokeTrusted("set-close-settings", [partial || {}]);
        },
        getUiTheme: function () {
            return invokeTrusted("get-ui-theme");
        },
        setUiTheme: function (preference) {
            return invokeTrusted("set-ui-theme", [preference]);
        },
        getPlatform: function () {
            return detectPlatform();
        },
        getScreenSecuritySettings: function () {
            return invokeTrusted("get-screen-security-settings");
        },
        setScreenSecurityEnabled: function (enabled) {
            return invokeTrusted("set-screen-security-enabled", [enabled === true]);
        },
        getMemoryUsage: function () {
            return invokeTrusted("get-memory-usage");
        },
        getBatteryStatus: function () {
            return invokeTrusted("get-battery-status");
        },
        showPathInFolder: function (targetPath) {
            return invokeTrusted("showPathInFolder", [targetPath]);
        },
        openPath: function (targetPath) {
            return invokeTrusted("open-path", [targetPath]);
        },
        pickFile: function () {
            return invokeTrusted("pick-file");
        },
        pickDirectory: function () {
            return invokeTrusted("pick-directory");
        },
        isHardwareAccelerationEnabled: function () {
            return invokeTrusted("is-hardware-acceleration-enabled");
        },
        getIntegrityStatus: function () {
            return invokeTrusted("get-integrity-status");
        },
        showNotification: function (title, body, silent, destinationHash) {
            invokeTrusted("show-notification", [
                {
                    title: title,
                    body: body,
                    silent: silent === true,
                    destinationHash: destinationHash == null ? null : String(destinationHash),
                },
            ]).catch(function () {});
        },
        closeMessageNotifications: function (destinationHash) {
            return invokeTrusted("close-message-notifications", [destinationHash == null ? null : destinationHash]);
        },
        setPowerSaveBlocker: function (enabled) {
            return invokeTrusted("set-power-save-blocker", [enabled === true]);
        },
        onProtocolLink: function (callback) {
            return on("open-protocol-link", function (payload) {
                if (typeof callback === "function") {
                    callback(typeof payload === "string" ? payload : payload && payload.url);
                }
            });
        },
        backendHttpOnly: function () {
            return invokeTrusted("backend-http-only");
        },
        backendRuntimeState: function () {
            return invokeTrusted("backend-runtime-state");
        },
        backendStartupDiagnostics: function () {
            return invokeTrusted("backend-startup-diagnostics");
        },
        markBackendHealthy: function () {
            return invokeTrusted("mark-backend-healthy");
        },
        restartBackend: function () {
            return invokeTrusted("restart-backend");
        },
        openBackendCrashReport: function () {
            return invokeTrusted("open-backend-crash-report");
        },
        onBackendProcessExited: function (callback) {
            return on("backend-process-exited", function (payload) {
                if (typeof callback === "function") {
                    callback(payload);
                }
            });
        },
        onBackendStartupFailed: function (callback) {
            return on("backend-startup-failed", function (payload) {
                if (typeof callback === "function") {
                    callback(payload);
                }
            });
        },
        // Extra bridge surface used by shell pages (loading/crash/close/prompt).
        onLog: function (callback) {
            return on("log", callback);
        },
        getBackendProbeTarget: function () {
            return invokeTrusted("backend-probe-target");
        },
        backendProbe: function (protocol) {
            return invokeTrusted("backend-probe", [protocol]);
        },
        backendConfig: function (protocol) {
            return invokeTrusted("backend-config", [protocol]);
        },
        openApp: function (url) {
            return invokeTrusted("open-app", [url]);
        },
        downloadBegin: function (name, size) {
            return invokeTrusted("download-begin", [name, size]);
        },
        downloadChunk: function (id, dataBase64) {
            return invokeTrusted("download-chunk", [id, dataBase64]);
        },
        downloadEnd: function (id) {
            return invokeTrusted("download-end", [id]);
        },
        downloadAbort: function (id) {
            return invokeTrusted("download-abort", [id]);
        },
        openWindow: function (spec) {
            return invokeTrusted("open-window", [spec]);
        },
        closeWindow: function (name) {
            return invokeTrusted("close-window", [name]);
        },
        windowResult: function (name, result) {
            return invokeTrusted("window-result", [name, result]);
        },
        requestCloseDialog: function () {
            return invokeTrusted("request-close-dialog");
        },
        serialListPorts: function () {
            return invokeTrusted("serial-list-ports");
        },
        serialRequestPort: function (opts) {
            return invokeTrusted("serial-request-port", [opts || {}]);
        },
        serialOpen: function (opts) {
            return invokeTrusted("serial-open", [opts || {}]);
        },
        serialRead: function (opts) {
            return invokeTrusted("serial-read", [opts || {}]);
        },
        serialWrite: function (opts) {
            return invokeTrusted("serial-write", [opts || {}]);
        },
        serialClose: function (opts) {
            return invokeTrusted("serial-close", [opts || {}]);
        },
        serialSetSignals: function (opts) {
            return invokeTrusted("serial-set-signals", [opts || {}]);
        },
        serialGetSignals: function (opts) {
            return invokeTrusted("serial-get-signals", [opts || {}]);
        },
        serialGetInfo: function (opts) {
            return invokeTrusted("serial-get-info", [opts || {}]);
        },
        serialForget: function (opts) {
            return invokeTrusted("serial-forget", [opts || {}]);
        },
    };

    window.desktop = desktop;

    // ---- Navigation / window.open guards ------------------------------------
    // Wails has no new-window handler; route window.open and untrusted link
    // clicks through the Go side which applies the shell navigation rules.

    function featuresToSize(features) {
        var width = 0;
        var height = 0;
        try {
            var parts = String(features || "").split(",");
            for (var i = 0; i < parts.length; i++) {
                var kv = parts[i].split("=");
                if (kv.length !== 2) {
                    continue;
                }
                var key = kv[0].trim().toLowerCase();
                var val = parseInt(kv[1].trim(), 10);
                if (key === "width" || key === "innerwidth") {
                    width = val;
                } else if (key === "height" || key === "innerheight") {
                    height = val;
                }
            }
        } catch {
            /* best-effort */
        }
        return { width: width, height: height };
    }

    window.open = function (url, target, features) {
        var href = url == null ? "" : String(url);
        if (!href || href === "about:blank") {
            // Used by print flows (document.write into a blank window). Deny
            // silently like a popup blocker would; callers have fallbacks.
            return null;
        }
        var size = featuresToSize(features);
        invokeTrusted("open-window", [
            {
                url: href,
                target: target == null ? "_blank" : String(target),
                width: size.width,
                height: size.height,
            },
        ]).catch(function () {});
        return null;
    };

    document.addEventListener(
        "click",
        function (event) {
            var anchor = event.target && event.target.closest ? event.target.closest("a[href]") : null;
            if (!anchor) {
                return;
            }
            var href = anchor.getAttribute("href");
            if (!href) {
                return;
            }
            var resolved;
            try {
                resolved = new URL(href, window.location.href).href;
            } catch {
                return;
            }
            var opensNew =
                anchor.target === "_blank" ||
                anchor.hasAttribute("download") ||
                event.ctrlKey ||
                event.metaKey ||
                event.shiftKey ||
                event.altKey;
            var isLocalBackend = isLocalBackendUrl(resolved);
            var isWailsAsset = isTrustedShellOrigin(window.location.href) && isTrustedShellOrigin(resolved);
            if (isLocalBackend && !opensNew) {
                return; // in-window navigation stays inside the shell
            }
            if (isWailsAsset && !opensNew) {
                return; // asset-origin internal navigation
            }
            if (anchor.hasAttribute("download")) {
                return; // handled by download interceptor below
            }
            event.preventDefault();
            event.stopPropagation();
            invokeTrusted("open-external", [resolved]).catch(function () {});
        },
        true
    );

    // ---- Downloads -----------------------------------------------------------
    // WebKitGTK drops <a download>/blob saves; stream them through the bridge
    // into <Downloads>/MeshChatX on the Go side.

    var activeDownloads = Object.create(null);

    function sanitizeDownloadName(name) {
        var base =
            String(name || "download")
                .split(/[\\/]/)
                .pop() || "download";
        base = Array.from(base)
            .map(function (ch) {
                var c = ch.charCodeAt(0);
                return c < 0x20 ||
                    ch === "<" ||
                    ch === ">" ||
                    ch === ":" ||
                    ch === '"' ||
                    ch === "|" ||
                    ch === "?" ||
                    ch === "*"
                    ? "_"
                    : ch;
            })
            .join("")
            .trim();
        if (!base || base === "." || base === "..") {
            base = "download";
        }
        return base.slice(0, 200);
    }

    function saveBlob(blob, suggestedName) {
        var name = sanitizeDownloadName(suggestedName);
        var reader;
        try {
            reader = new FileReader();
        } catch {
            return;
        }
        reader.onload = function () {
            var dataUrl = String(reader.result || "");
            var comma = dataUrl.indexOf(",");
            var base64 = comma >= 0 ? dataUrl.slice(comma + 1) : "";
            var id = "dl-" + Date.now() + "-" + Math.floor(Math.random() * 1e6);
            var CHUNK = 512 * 1024;
            var total = Math.max(1, Math.ceil(base64.length / CHUNK));
            var index = 0;
            invokeTrusted("download-begin", [name, blob.size || base64.length])
                .then(function (res) {
                    if (!res || res.ok === false) {
                        return;
                    }
                    activeDownloads[id] = res.id || id;
                    function pump() {
                        if (index >= total) {
                            invokeTrusted("download-end", [activeDownloads[id]]).catch(function () {});
                            delete activeDownloads[id];
                            return;
                        }
                        var part = base64.slice(index * CHUNK, (index + 1) * CHUNK);
                        index += 1;
                        invokeTrusted("download-chunk", [activeDownloads[id], part])
                            .then(pump)
                            .catch(function () {
                                invokeTrusted("download-abort", [activeDownloads[id]]).catch(function () {});
                                delete activeDownloads[id];
                            });
                    }
                    pump();
                })
                .catch(function () {});
        };
        reader.readAsDataURL(blob);
    }

    function interceptDownloadClick(event) {
        var anchor = event.target && event.target.closest ? event.target.closest("a[download]") : null;
        if (!anchor) {
            return;
        }
        var href = anchor.getAttribute("href") || "";
        var name = anchor.getAttribute("download") || "";
        if (!href || href.indexOf("javascript:") === 0 || href.indexOf("data:") === 0) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        var resolved;
        try {
            resolved = new URL(href, window.location.href).href;
        } catch {
            return;
        }
        fetch(resolved, { credentials: "include" })
            .then(function (resp) {
                if (!resp.ok) {
                    throw new Error("download fetch failed: " + resp.status);
                }
                var cd = resp.headers.get("content-disposition") || "";
                var m = /filename\*=UTF-8''([^;]+)/i.exec(cd) || /filename="?([^";]+)"?/i.exec(cd);
                if (!name && m && m[1]) {
                    try {
                        name = decodeURIComponent(m[1]);
                    } catch {
                        name = m[1];
                    }
                }
                return resp.blob().then(function (blob) {
                    saveBlob(blob, name || "download");
                });
            })
            .catch(function () {});
    }

    document.addEventListener("click", interceptDownloadClick, true);

    var nativeAnchorClick = HTMLAnchorElement.prototype.click;
    HTMLAnchorElement.prototype.click = function () {
        if (this.hasAttribute && this.hasAttribute("download")) {
            // Synthetic clicks have no DOM event target; hand the interceptor
            // a stand-in so detached anchors work too.
            interceptDownloadClick({
                target: this,
                preventDefault: function () {},
                stopPropagation: function () {},
            });
            return;
        }
        return nativeAnchorClick.apply(this, arguments);
    };

    // Expose for shell pages that need the raw postMessage (none today, but
    // keeps the door open without re-detecting channels).
    window.__desktopBridge.postMessage = postMessage;

    // ---- navigator.serial polyfill ------------------------------------------
    // WebKit has no Web Serial; the Go bridge exposes token-gated serial
    // access. Installed only when the platform lacks a native implementation.
    (function installSerialPolyfill() {
        if (!desktop.serialRequestPort) {
            return;
        }
        try {
            if (navigator.serial) {
                return;
            }
        } catch {
            return;
        }
        if (typeof ReadableStream !== "function" || typeof WritableStream !== "function") {
            return;
        }

        var grantedPorts = [];

        function bytesToB64(u8) {
            var s = "";
            for (var i = 0; i < u8.length; i += 8192) {
                s += String.fromCharCode.apply(null, u8.subarray(i, Math.min(i + 8192, u8.length)));
            }
            return btoa(s);
        }

        function b64ToBytes(b64) {
            var s = atob(b64);
            var u8 = new Uint8Array(s.length);
            for (var i = 0; i < s.length; i++) {
                u8[i] = s.charCodeAt(i);
            }
            return u8;
        }

        function MeshChatXSerialPort(token, info) {
            this._token = token;
            this._info = info || {};
            this._open = false;
            this._readable = null;
            this._writable = null;
        }

        MeshChatXSerialPort.prototype.getInfo = function () {
            var self = this;
            return desktop.serialGetInfo({ token: this._token }).then(function (info) {
                self._info = info || self._info;
                return {
                    usbVendorId: info && info.usbVendorId != null ? info.usbVendorId : undefined,
                    usbProductId: info && info.usbProductId != null ? info.usbProductId : undefined,
                };
            });
        };

        MeshChatXSerialPort.prototype.forget = function () {
            var idx = grantedPorts.indexOf(this);
            if (idx >= 0) {
                grantedPorts.splice(idx, 1);
            }
            return desktop.serialForget({ token: this._token });
        };

        MeshChatXSerialPort.prototype.open = function (options) {
            var self = this;
            options = options || {};
            var opts = {
                token: this._token,
                baudRate: typeof options.baudRate === "number" ? options.baudRate : 9600,
                dataBits: typeof options.dataBits === "number" ? options.dataBits : 8,
                stopBits: options.stopBits || "one",
                parity: options.parity || "none",
                flowControl: options.flowControl || "none",
            };
            return desktop.serialOpen(opts).then(function () {
                self._open = true;
                self._readable = new ReadableStream({
                    highWaterMark: 16,
                    pull: function (controller) {
                        return self._pull(controller);
                    },
                });
                self._writable = new WritableStream({
                    write: function (chunk) {
                        var u8 = chunk instanceof Uint8Array ? chunk : new Uint8Array(chunk);
                        return desktop.serialWrite({ token: self._token, data: bytesToB64(u8) }).then(function (res) {
                            if (!res || typeof res.written !== "number") {
                                throw new Error("serial write failed");
                            }
                        });
                    },
                    close: function () {
                        return desktop.serialClose({ token: self._token }).catch(function () {});
                    },
                    abort: function () {
                        return desktop.serialClose({ token: self._token }).catch(function () {});
                    },
                });
            });
        };

        MeshChatXSerialPort.prototype._pull = function (controller) {
            var token = this._token;
            var settled = false;
            var off = function () {};
            var finish = function () {
                if (!settled) {
                    settled = true;
                    off();
                }
            };
            function drain() {
                return desktop
                    .serialRead({ token: token, maxBytes: 65536 })
                    .then(function (res) {
                        if (settled) {
                            return;
                        }
                        if (res && res.data) {
                            var bytes = b64ToBytes(res.data);
                            if (bytes.length) {
                                controller.enqueue(bytes);
                                finish();
                                return;
                            }
                        }
                        // Empty: wait for the next serial-data nudge, then retry.
                        // Unsubscribe the previous listener first — re-registering
                        // without off() leaks one listener per empty read and each
                        // serial-data event then fires all of them.
                        off();
                        off = on("serial-data", function (payload) {
                            if (payload && payload.token === token) {
                                if (payload.closed) {
                                    finish();
                                    controller.error(new Error("serial port closed"));
                                    return;
                                }
                                drain().catch(function (e) {
                                    if (!settled) {
                                        settled = true;
                                        off();
                                        controller.error(e);
                                    }
                                });
                            }
                        });
                    })
                    .catch(function (e) {
                        if (!settled) {
                            settled = true;
                            off();
                            controller.error(e);
                        }
                    });
            }
            drain();
            return new Promise(function (resolve) {
                var prevFinish = finish;
                finish = function () {
                    prevFinish();
                    resolve();
                };
            });
        };

        Object.defineProperty(MeshChatXSerialPort.prototype, "readable", {
            get: function () {
                return this._open ? this._readable : null;
            },
            configurable: true,
        });
        Object.defineProperty(MeshChatXSerialPort.prototype, "writable", {
            get: function () {
                return this._open ? this._writable : null;
            },
            configurable: true,
        });

        MeshChatXSerialPort.prototype.close = function () {
            this._open = false;
            var r = this._readable;
            var w = this._writable;
            this._readable = null;
            this._writable = null;
            var p = desktop.serialClose({ token: this._token }).catch(function () {});
            try {
                if (r) {
                    r.cancel().catch(function () {});
                }
                if (w) {
                    w.abort().catch(function () {});
                }
            } catch {
                /* best-effort */
            }
            return p.then(function () {});
        };

        MeshChatXSerialPort.prototype.setSignals = function (signals) {
            signals = signals || {};
            return desktop.serialSetSignals({
                token: this._token,
                dtr: signals.dataTerminalReady,
                rts: signals.requestToSend,
            });
        };

        MeshChatXSerialPort.prototype.getSignals = function () {
            return desktop.serialGetSignals({ token: this._token }).then(function (sig) {
                sig = sig || {};
                return {
                    dataTerminalReady: sig.dtr === true,
                    requestToSend: sig.rts === true,
                    clearToSend: sig.cts === true,
                    dataSetReady: sig.dsr === true,
                    carrierDetect: sig.cd === true,
                    ringIndicator: sig.ring === true,
                };
            });
        };

        MeshChatXSerialPort.prototype.addEventListener = function () {};
        MeshChatXSerialPort.prototype.removeEventListener = function () {};

        var serial = {
            requestPort: function (options) {
                options = options || {};
                return desktop.serialRequestPort({ filters: options.filters || [] }).then(function (res) {
                    if (!res || !res.token) {
                        var err = new Error("No port selected");
                        err.name = "NotFoundError";
                        throw err;
                    }
                    var port = new MeshChatXSerialPort(res.token, res.port);
                    grantedPorts.push(port);
                    return port;
                });
            },
            getPorts: function () {
                return Promise.resolve(grantedPorts.slice());
            },
            addEventListener: function () {},
            removeEventListener: function () {},
            onconnect: null,
            ondisconnect: null,
        };

        try {
            Object.defineProperty(navigator, "serial", {
                value: serial,
                configurable: true,
                enumerable: true,
            });
        } catch {
            /* best-effort */
        }
    })();
})();
