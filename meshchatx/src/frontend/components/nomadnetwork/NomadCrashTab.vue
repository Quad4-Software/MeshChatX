<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="nomad-crash-tab relative h-full min-h-0 w-full min-w-0 bg-black">
        <iframe
            ref="frame"
            class="nomad-crash-tab__frame absolute inset-0 h-full w-full border-0 bg-black"
            title="Nomad page renderer"
            sandbox="allow-scripts"
            allow="local-network-access"
            :src="frameSrc"
            :style="frameStyle"
            @load="onFrameLoad"
        ></iframe>

        <div
            v-if="status === 'hung' || status === 'crashed'"
            class="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-black/80 px-4 text-center text-gray-100"
            role="alert"
        >
            <div class="text-lg font-semibold">{{ $t("nomadnet.crash_tab_title") }}</div>
            <div class="max-w-md text-sm text-gray-300">{{ $t("nomadnet.crash_tab_body") }}</div>
            <div class="flex flex-wrap items-center justify-center gap-2">
                <button
                    type="button"
                    class="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-blue-500"
                    @click="reloadFrame"
                >
                    {{ $t("nomadnet.crash_tab_reload") }}
                </button>
                <button
                    type="button"
                    class="rounded-lg bg-zinc-700 px-3 py-1.5 text-sm font-semibold text-white hover:bg-zinc-600"
                    @click="$emit('view-source')"
                >
                    {{ $t("nomadnet.view_source") }}
                </button>
                <button
                    type="button"
                    class="rounded-lg bg-red-700 px-3 py-1.5 text-sm font-semibold text-white hover:bg-red-600"
                    @click="abortRender"
                >
                    {{ $t("common.cancel") }}
                </button>
            </div>
        </div>
    </div>
</template>

<script>
import { nomadCrashTabRendererUrl, NOMAD_CRASH_TAB_CHANNEL } from "../../js/nomadCrashTabShell";

const WATCHDOG_MS = 12000;
const PING_INTERVAL_MS = 2000;
/**
 * Coalesced wake after a freeze often skips the 1s watchdog ticks. Silence
 * larger than this is a stall, not a live hang.
 */
const WATCHDOG_STALL_MS = 20000;
/** Wall-clock cap for one paint. Ping liveness alone cannot clear a hung import. */
const RENDER_DEADLINE_MS = 20000;
const RENDER_DEADLINE_MIN_RESUME_MS = 1000;

export default {
    name: "NomadCrashTab",
    props: {
        path: {
            type: String,
            default: "",
        },
        content: {
            type: String,
            default: "",
        },
        showSource: {
            type: Boolean,
            default: false,
        },
        pagePartials: {
            type: Object,
            default: () => ({}),
        },
        renderOptions: {
            type: Object,
            default: () => ({}),
        },
        contentClass: {
            type: String,
            default: "",
        },
        color: {
            type: String,
            default: "",
        },
        background: {
            type: String,
            default: "#000000",
        },
        active: {
            type: Boolean,
            default: true,
        },
        /** When false, keep the frame dark/hidden (download or shell busy banner). */
        reveal: {
            type: Boolean,
            default: true,
        },
    },
    emits: [
        "navigate",
        "partials",
        "view-source",
        "ready",
        "hung",
        "render-started",
        "render-done",
        "aborted",
        "shell-background",
    ],
    data() {
        return {
            frameSrc: nomadCrashTabRendererUrl(),
            status: "loading",
            frameGeneration: 0,
            pendingPingId: 0,
            lastPongAt: 0,
            frameReady: false,
            framePainted: false,
            watchdogTimer: null,
            pingTimer: null,
            renderEpoch: 0,
            pushRenderQueued: false,
            // After abort, do not re-push the same content when the iframe reloads.
            skipRenderUntilPropChange: false,
            renderDeadlineTimer: null,
            lastPostedRenderKey: "",
            chromePushQueued: false,
            livenessPaused: false,
            renderDeadlineParked: false,
            renderDeadlineRemainingMs: 0,
            renderDeadlineArmedAt: 0,
        };
    },
    computed: {
        frameStyle() {
            const bg = this.background && this.background !== "transparent" ? this.background : "#000000";
            const show = this.reveal && this.framePainted && this.status !== "rendering" && this.status !== "loading";
            return {
                backgroundColor: bg,
                opacity: show ? "1" : "0",
            };
        },
        renderOptionsKey() {
            try {
                return JSON.stringify(this.renderOptions || {});
            } catch {
                return "";
            }
        },
        pagePartialsKey() {
            try {
                return JSON.stringify(this.pagePartials || {});
            } catch {
                return "";
            }
        },
        /**
         * Full repaint identity. Chrome-only props are excluded so shell-background
         * feedback cannot loop render-started and stick Loading page forever.
         */
        contentRenderKey() {
            return [
                this.path || "",
                this.showSource ? "1" : "0",
                this.content || "",
                this.renderOptionsKey,
                this.pagePartialsKey,
            ].join("\u0001");
        },
    },
    watch: {
        path() {
            this.skipRenderUntilPropChange = false;
            this.schedulePushRender();
        },
        content() {
            this.skipRenderUntilPropChange = false;
            this.schedulePushRender();
        },
        showSource() {
            this.skipRenderUntilPropChange = false;
            this.schedulePushRender();
        },
        // Identity-stable keys. A deep watch on renderOptions re-fires every parent
        // re-render because nomadRenderOptions() returns a fresh object, which loops
        // render-started forever and sticks the Loading page banner.
        renderOptionsKey() {
            this.skipRenderUntilPropChange = false;
            this.schedulePushRender();
        },
        pagePartialsKey() {
            this.skipRenderUntilPropChange = false;
            this.schedulePushRender();
        },
        // Chrome-only: update paint without a full Micron pass or render-started.
        contentClass() {
            this.schedulePushChrome();
        },
        color() {
            this.schedulePushChrome();
        },
        background() {
            this.schedulePushChrome();
        },
        active(isActive) {
            if (isActive && !this.livenessPaused && !this.isDocumentHidden()) {
                this.startWatchdog();
            } else {
                this.stopWatchdog();
            }
        },
    },
    mounted() {
        window.addEventListener("message", this.onWindowMessage);
        window.addEventListener("visibilitychange", this.onVisibilityChange);
        if (typeof document !== "undefined") {
            document.addEventListener("freeze", this.onPageFreeze);
            document.addEventListener("resume", this.onPageResume);
        }
        if (this.isDocumentHidden()) {
            this.pauseLivenessForBackground();
        } else if (this.active) {
            this.startWatchdog();
        }
    },
    beforeUnmount() {
        window.removeEventListener("message", this.onWindowMessage);
        window.removeEventListener("visibilitychange", this.onVisibilityChange);
        if (typeof document !== "undefined") {
            document.removeEventListener("freeze", this.onPageFreeze);
            document.removeEventListener("resume", this.onPageResume);
        }
        this.stopWatchdog();
        this.clearRenderDeadline();
    },
    methods: {
        /**
         * postMessage requires the structured clone algorithm. Vue reactive
         * proxies in pagePartials / renderOptions are not cloneable.
         */
        toCloneableMessage(msg) {
            if (typeof structuredClone === "function") {
                try {
                    return structuredClone({ channel: NOMAD_CRASH_TAB_CHANNEL, ...msg });
                } catch {
                    // Fall through to JSON for Proxy-backed objects.
                }
            }
            try {
                return JSON.parse(JSON.stringify({ channel: NOMAD_CRASH_TAB_CHANNEL, ...msg }));
            } catch {
                return null;
            }
        },
        postToFrame(msg) {
            const frame = this.$refs.frame;
            if (!frame || !frame.contentWindow) {
                return false;
            }
            const payload = this.toCloneableMessage(msg);
            if (!payload) {
                return false;
            }
            // Opaque-origin targets only accept "*" as targetOrigin (HTML postMessage).
            // Receive-side still requires event.origin === "null".
            frame.contentWindow.postMessage(payload, "*");
            return true;
        },
        onFrameLoad() {
            // Readiness comes from the frame's "ready" postMessage. The iframe load
            // event can fire after that and must not clobber frameReady / cancel a
            // pending nextTick pushRender (that left Loading page stuck forever).
            this.lastPongAt = Date.now();
        },
        schedulePushRender() {
            if (this.pushRenderQueued) {
                return;
            }
            this.pushRenderQueued = true;
            queueMicrotask(() => {
                this.pushRenderQueued = false;
                this.pushRender();
            });
        },
        schedulePushChrome() {
            if (this.chromePushQueued) {
                return;
            }
            this.chromePushQueued = true;
            queueMicrotask(() => {
                this.chromePushQueued = false;
                this.pushChrome();
            });
        },
        pushChrome() {
            if (!this.frameReady || this.skipRenderUntilPropChange) {
                return;
            }
            if (this.content == null || this.content === "") {
                return;
            }
            // Full paint still pending: chrome rides along with the next render.
            if (this.status === "rendering" || this.status === "loading") {
                return;
            }
            this.postToFrame({
                type: "chrome",
                className: this.contentClass || "",
                color: this.color || "#dddddd",
                background: this.background || "#000000",
                showSource: this.showSource === true,
            });
        },
        isDocumentHidden() {
            if (typeof document === "undefined") {
                return false;
            }
            if (document.visibilityState === "hidden") {
                return true;
            }
            return document.hidden === true;
        },
        onVisibilityChange() {
            if (this.isDocumentHidden()) {
                this.pauseLivenessForBackground();
                return;
            }
            this.resumeLivenessFromBackground();
        },
        onPageFreeze() {
            this.pauseLivenessForBackground();
        },
        onPageResume() {
            if (this.isDocumentHidden()) {
                return;
            }
            this.resumeLivenessFromBackground();
        },
        pauseLivenessForBackground() {
            if (this.livenessPaused) {
                this.parkRenderDeadline();
                this.stopWatchdog();
                return;
            }
            this.livenessPaused = true;
            this.stopWatchdog();
            this.parkRenderDeadline();
        },
        resumeLivenessFromBackground() {
            this.livenessPaused = false;
            this.lastPongAt = Date.now();
            if (this.active) {
                this.startWatchdog();
                this.pingNow();
            }
            this.unparkRenderDeadline();
        },
        clearRenderDeadline() {
            if (this.renderDeadlineTimer != null) {
                clearTimeout(this.renderDeadlineTimer);
                this.renderDeadlineTimer = null;
            }
            this.renderDeadlineParked = false;
            this.renderDeadlineRemainingMs = 0;
            this.renderDeadlineArmedAt = 0;
        },
        parkRenderDeadline() {
            if (this.renderDeadlineTimer != null) {
                clearTimeout(this.renderDeadlineTimer);
                this.renderDeadlineTimer = null;
                const elapsed = Date.now() - (this.renderDeadlineArmedAt || Date.now());
                const left = (this.renderDeadlineRemainingMs || RENDER_DEADLINE_MS) - elapsed;
                this.renderDeadlineRemainingMs = Math.max(RENDER_DEADLINE_MIN_RESUME_MS, left);
                this.renderDeadlineParked = true;
                return;
            }
            if (this.status === "rendering" || this.status === "loading") {
                this.renderDeadlineParked = true;
                if (!this.renderDeadlineRemainingMs) {
                    this.renderDeadlineRemainingMs = RENDER_DEADLINE_MS;
                }
            }
        },
        unparkRenderDeadline() {
            if (!this.renderDeadlineParked) {
                return;
            }
            this.renderDeadlineParked = false;
            if (this.status !== "rendering" && this.status !== "loading") {
                this.renderDeadlineRemainingMs = 0;
                return;
            }
            this.armRenderDeadline(this.renderDeadlineRemainingMs || RENDER_DEADLINE_MS);
        },
        armRenderDeadline(timeoutMs) {
            this.clearRenderDeadline();
            const wait = timeoutMs == null ? RENDER_DEADLINE_MS : timeoutMs;
            this.renderDeadlineRemainingMs = wait;
            if (this.livenessPaused || this.isDocumentHidden()) {
                this.renderDeadlineParked = true;
                return;
            }
            const epoch = this.renderEpoch;
            this.renderDeadlineArmedAt = Date.now();
            this.renderDeadlineTimer = setTimeout(() => {
                this.renderDeadlineTimer = null;
                if (epoch !== this.renderEpoch) {
                    return;
                }
                if (this.status !== "rendering" && this.status !== "loading") {
                    return;
                }
                if (this.livenessPaused || this.isDocumentHidden()) {
                    this.renderDeadlineParked = true;
                    if (!this.renderDeadlineRemainingMs) {
                        this.renderDeadlineRemainingMs = RENDER_DEADLINE_MS;
                    }
                    return;
                }
                this.status = "hung";
                this.framePainted = false;
                this.$emit("hung");
            }, wait);
        },
        pushRender() {
            if (this.skipRenderUntilPropChange) {
                return;
            }
            if (!this.frameReady) {
                // Content is waiting on a frame that has not posted ready yet.
                if (this.content && this.status === "loading") {
                    this.armRenderDeadline();
                }
                return;
            }
            if (this.content == null || this.content === "") {
                this.framePainted = false;
                this.lastPostedRenderKey = "";
                this.clearRenderDeadline();
                this.postToFrame({ type: "clear" });
                this.status = "ready";
                // Do not emit render-done for clears. That raced with
                // beginCrashTabRenderWait and could clear the busy banner early,
                // or interact badly with a following real render.
                return;
            }
            const renderKey = this.contentRenderKey;
            if (renderKey === this.lastPostedRenderKey && this.status === "ready" && this.framePainted) {
                this.pushChrome();
                return;
            }
            this.renderEpoch += 1;
            const epoch = this.renderEpoch;
            this.framePainted = false;
            this.status = "rendering";
            this.lastPongAt = Date.now();
            this.lastPostedRenderKey = renderKey;
            this.$emit("render-started");
            this.armRenderDeadline();
            // Let the shell paint the loading banner before heavy iframe work.
            this.$nextTick(() => {
                if (this.skipRenderUntilPropChange || epoch !== this.renderEpoch) {
                    return;
                }
                const posted = this.postToFrame({
                    type: "render",
                    path: this.path || "",
                    content: this.content || "",
                    showSource: this.showSource === true,
                    pagePartials: this.pagePartials || {},
                    renderOptions: this.renderOptions || {},
                    className: this.contentClass || "",
                    color: this.color || "#dddddd",
                    background: this.background || "#000000",
                });
                if (!posted) {
                    this.clearRenderDeadline();
                    this.status = "crashed";
                    this.$emit("hung");
                }
            });
        },
        onWindowMessage(event) {
            const frame = this.$refs.frame;
            if (!frame || event.source !== frame.contentWindow) {
                return;
            }
            // Opaque sandboxed renderer posts with origin "null".
            if (event.origin !== "null") {
                return;
            }
            const data = event.data;
            if (!data || data.channel !== NOMAD_CRASH_TAB_CHANNEL) {
                return;
            }
            if (data.type === "ready") {
                this.frameReady = true;
                this.lastPostedRenderKey = "";
                this.clearRenderDeadline();
                this.status = this.skipRenderUntilPropChange ? "aborted" : "ready";
                this.lastPongAt = Date.now();
                this.$emit("ready");
                this.schedulePushRender();
                return;
            }
            if (data.type === "pong") {
                this.lastPongAt = Date.now();
                if (this.status === "hung" || this.status === "crashed") {
                    this.status = "ready";
                }
                return;
            }
            if (data.type === "render-started") {
                if (this.skipRenderUntilPropChange) {
                    return;
                }
                this.status = "rendering";
                this.lastPongAt = Date.now();
                return;
            }
            if (data.type === "render-done") {
                this.clearRenderDeadline();
                this.status = "ready";
                this.framePainted = true;
                this.lastPongAt = Date.now();
                this.$emit("render-done");
                this.$emit("partials", Array.isArray(data.partials) ? data.partials : []);
                return;
            }
            if (data.type === "render-error") {
                this.clearRenderDeadline();
                this.status = "crashed";
                this.framePainted = false;
                this.$emit("hung");
                return;
            }
            if (data.type === "shell-background") {
                this.$emit("shell-background", data.background || null);
                return;
            }
            if (data.type === "aborted") {
                this.clearRenderDeadline();
                this.status = "aborted";
                this.framePainted = false;
                // abortRender already emitted. Ignore the frame echo after hard cancel.
                if (!this.skipRenderUntilPropChange) {
                    this.$emit("aborted");
                }
                return;
            }
            if (data.type === "navigate") {
                this.$emit("navigate", {
                    kind: data.kind,
                    url: data.url,
                    fields: data.fields,
                    fieldSpec: data.fieldSpec,
                    button: data.button,
                    ctrlKey: data.ctrlKey,
                    metaKey: data.metaKey,
                });
            }
        },
        pingNow() {
            if (!this.active || !this.frameReady) {
                return;
            }
            if (this.livenessPaused || this.isDocumentHidden()) {
                return;
            }
            this.pendingPingId += 1;
            this.postToFrame({ type: "ping", id: this.pendingPingId });
        },
        checkWatchdog() {
            if (!this.active || !this.frameReady) {
                return;
            }
            if (this.livenessPaused || this.isDocumentHidden()) {
                return;
            }
            if (this.status !== "rendering" && this.status !== "ready") {
                return;
            }
            const silentMs = Date.now() - this.lastPongAt;
            if (silentMs <= WATCHDOG_MS) {
                return;
            }
            if (silentMs > WATCHDOG_STALL_MS) {
                this.lastPongAt = Date.now();
                this.pingNow();
                return;
            }
            if (this.status !== "hung") {
                this.clearRenderDeadline();
                this.status = "hung";
                this.$emit("hung");
            }
        },
        startWatchdog() {
            this.stopWatchdog();
            if (!this.active || this.livenessPaused || this.isDocumentHidden()) {
                return;
            }
            this.lastPongAt = Date.now();
            this.pingTimer = setInterval(() => {
                this.pingNow();
            }, PING_INTERVAL_MS);
            this.watchdogTimer = setInterval(() => {
                this.checkWatchdog();
            }, 1000);
        },
        stopWatchdog() {
            if (this.pingTimer != null) {
                clearInterval(this.pingTimer);
                this.pingTimer = null;
            }
            if (this.watchdogTimer != null) {
                clearInterval(this.watchdogTimer);
                this.watchdogTimer = null;
            }
        },
        reloadFrame() {
            this.clearRenderDeadline();
            this.status = "loading";
            this.frameReady = false;
            this.framePainted = false;
            this.lastPostedRenderKey = "";
            this.frameSrc = `${nomadCrashTabRendererUrl()}?t=${Date.now()}`;
            this.frameGeneration += 1;
            this.lastPongAt = Date.now();
        },
        abortRender() {
            this.renderEpoch += 1;
            this.skipRenderUntilPropChange = true;
            this.framePainted = false;
            this.lastPostedRenderKey = "";
            this.clearRenderDeadline();
            this.postToFrame({ type: "abort" });
            // Hard cancel: tear down the sandboxed renderer process/context.
            this.reloadFrame();
            this.status = "aborted";
            this.$emit("render-done");
            this.$emit("aborted");
        },
        setPartialHtml(partialId, html) {
            if (this.skipRenderUntilPropChange) {
                return;
            }
            this.postToFrame({ type: "set-partial", id: partialId, html: html || "" });
        },
    },
};
</script>
