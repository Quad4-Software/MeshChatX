<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <iframe
        ref="frame"
        class="w-full rounded-lg border border-sem-border bg-sem-surface"
        :style="{ minHeight: minHeight }"
        :title="title || 'Plugin frame'"
        :src="frameSrc"
        :srcdoc="frameSrcdoc"
        sandbox="allow-scripts"
        referrerpolicy="no-referrer"
        @load="onLoad"
    />
</template>

<script>
const CHANNEL = "meshchatx-plugin-html-frame";

export default {
    name: "PluginHtmlFrame",
    props: {
        pluginId: { type: String, required: true },
        frameId: { type: String, default: "" },
        src: { type: String, default: "" },
        srcdoc: { type: String, default: "" },
        title: { type: String, default: "" },
        minHeight: { type: String, default: "12rem" },
        csp: {
            type: String,
            default: "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:;",
        },
    },
    emits: ["frame-action"],
    computed: {
        frameSrc() {
            return this.src || undefined;
        },
        frameSrcdoc() {
            if (this.src) {
                return undefined;
            }
            if (!this.srcdoc) {
                return undefined;
            }
            const meta = `<meta http-equiv="Content-Security-Policy" content="${this.csp.replace(/"/g, "")}">`;
            if (this.srcdoc.includes("<head>")) {
                return this.srcdoc.replace("<head>", `<head>${meta}`);
            }
            return `<!DOCTYPE html><html><head>${meta}</head><body>${this.srcdoc}</body></html>`;
        },
    },
    mounted() {
        this.onMessage = (event) => {
            if (event.source !== this.$refs.frame?.contentWindow) {
                return;
            }
            const data = event.data;
            if (!data || data.channel !== CHANNEL || data.pluginId !== this.pluginId) {
                return;
            }
            if (typeof data.actionId === "string") {
                this.$emit("frame-action", data.actionId);
            }
        };
        window.addEventListener("message", this.onMessage);
    },
    beforeUnmount() {
        window.removeEventListener("message", this.onMessage);
    },
    methods: {
        onLoad() {
            try {
                this.$refs.frame?.contentWindow?.postMessage(
                    {
                        channel: CHANNEL,
                        type: "ready",
                        pluginId: this.pluginId,
                        frameId: this.frameId,
                    },
                    "*"
                );
            } catch {
                /* opaque sandbox */
            }
        },
    },
};
</script>
