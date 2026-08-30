<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="nomad-crash-tab relative h-full min-h-0 w-full min-w-0">
        <iframe
            ref="frame"
            class="nomad-crash-tab__frame absolute inset-0 h-full w-full border-0 bg-transparent"
            title="Nomad page renderer"
            sandbox="allow-scripts"
            allow="local-network-access"
            :src="frameSrc"
            @load="onFrameLoad"
        ></iframe>

        <div
            v-if="status === 'rendering'"
            class="pointer-events-none absolute inset-x-0 top-0 z-10 flex justify-center p-2"
        >
            <div class="rounded bg-black/70 px-2 py-1 text-xs text-gray-200">
                {{ $t("nomadnet.crash_tab_rendering") }}
            </div>
        </div>

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
            default: "transparent",
        },
        active: {
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
            watchdogTimer: null,
            pingTimer: null,
            renderEpoch: 0,
            // After abort, do not re-push the same content when the iframe reloads.
            skipRenderUntilPropChange: false,
        };
    },
    watch: {
        path() {
            this.skipRenderUntilPropChange = false;
            this.pushRender();
        },
        content() {
            this.skipRenderUntilPropChange = false;
            this.pushRender();
        },
        showSource() {
            this.skipRenderUntilPropChange = false;
            this.pushRender();
        },
        pagePartials: {
            deep: true,
            handler() {
                this.skipRenderUntilPropChange = false;
                this.pushRender();
            },
        },
        renderOptions: {
            deep: true,
            handler() {
                this.skipRenderUntilPropChange = false;
                this.pushRender();
            },
        },
        contentClass() {
            this.skipRenderUntilPropChange = false;
            this.pushRender();
        },
        color() {
            this.skipRenderUntilPropChange = false;
            this.pushRender();
        },
        background() {
            this.skipRenderUntilPropChange = false;
            this.pushRender();
        },
        active(isActive) {
            if (isActive) {
                this.startWatchdog();
            } else {
                this.stopWatchdog();
            }
        },
    },
    mounted() {
        window.addEventListener("message", this.onWindowMessage);
        if (this.active) {
            this.startWatchdog();
        }
    },
    beforeUnmount() {
        window.removeEventListener("message", this.onWindowMessage);
        this.stopWatchdog();
    },
    methods: {
        /**
         * postMessage requires the structured clone algorithm. Vue reactive
         * proxies in pagePartials / renderOptions are not cloneable.
         */
        toCloneableMessage(msg) {
            try {
                return JSON.parse(JSON.stringify(msg));
            } catch {
                return null;
            }
        },
        postToFrame(msg) {
            const frame = this.$refs.frame;
            if (!frame || !frame.contentWindow) {
                return false;
            }
            const payload = this.toCloneableMessage({ channel: NOMAD_CRASH_TAB_CHANNEL, ...msg });
            if (!payload) {
                return false;
            }
            frame.contentWindow.postMessage(payload, "*");
            return true;
        },
        onFrameLoad() {
            this.frameReady = false;
            this.status = "loading";
            this.frameGeneration += 1;
            this.lastPongAt = Date.now();
        },
        pushRender() {
            if (this.skipRenderUntilPropChange) {
                return;
            }
            if (!this.frameReady) {
                return;
            }
            if (this.content == null || this.content === "") {
                this.postToFrame({ type: "clear" });
                this.status = "ready";
                return;
            }
            this.renderEpoch += 1;
            this.status = "rendering";
            this.lastPongAt = Date.now();
            this.$emit("render-started");
            const posted = this.postToFrame({
                type: "render",
                path: this.path || "",
                content: this.content || "",
                showSource: this.showSource === true,
                pagePartials: this.pagePartials || {},
                renderOptions: this.renderOptions || {},
                className: this.contentClass || "",
                color: this.color || "",
                background: this.background || "transparent",
            });
            if (!posted) {
                this.status = "crashed";
                this.$emit("hung");
            }
        },
        onWindowMessage(event) {
            const frame = this.$refs.frame;
            if (!frame || event.source !== frame.contentWindow) {
                return;
            }
            const data = event.data;
            if (!data || data.channel !== NOMAD_CRASH_TAB_CHANNEL) {
                return;
            }
            if (data.type === "ready") {
                this.frameReady = true;
                this.status = this.skipRenderUntilPropChange ? "aborted" : "ready";
                this.lastPongAt = Date.now();
                this.$emit("ready");
                this.pushRender();
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
                this.status = "ready";
                this.lastPongAt = Date.now();
                this.$emit("render-done");
                this.$emit("partials", Array.isArray(data.partials) ? data.partials : []);
                return;
            }
            if (data.type === "render-error") {
                this.status = "crashed";
                this.$emit("hung");
                return;
            }
            if (data.type === "shell-background") {
                this.$emit("shell-background", data.background || null);
                return;
            }
            if (data.type === "aborted") {
                this.status = "aborted";
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
        startWatchdog() {
            this.stopWatchdog();
            this.lastPongAt = Date.now();
            this.pingTimer = setInterval(() => {
                if (!this.active || !this.frameReady) {
                    return;
                }
                this.pendingPingId += 1;
                this.postToFrame({ type: "ping", id: this.pendingPingId });
            }, PING_INTERVAL_MS);
            this.watchdogTimer = setInterval(() => {
                if (!this.active || !this.frameReady) {
                    return;
                }
                if (this.status !== "rendering" && this.status !== "ready") {
                    return;
                }
                if (Date.now() - this.lastPongAt > WATCHDOG_MS) {
                    if (this.status !== "hung") {
                        this.status = "hung";
                        this.$emit("hung");
                    }
                }
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
            this.status = "loading";
            this.frameReady = false;
            this.frameSrc = `${nomadCrashTabRendererUrl()}?t=${Date.now()}`;
            this.frameGeneration += 1;
            this.lastPongAt = Date.now();
        },
        abortRender() {
            this.renderEpoch += 1;
            this.skipRenderUntilPropChange = true;
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
