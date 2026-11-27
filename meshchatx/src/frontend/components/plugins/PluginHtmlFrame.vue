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

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

const CHANNEL = "meshchatx-plugin-html-frame";

const props = withDefaults(
    defineProps<{
        pluginId: string;
        frameId?: string;
        src?: string;
        srcdoc?: string;
        title?: string;
        minHeight?: string;
        csp?: string;
    }>(),
    {
        frameId: "",
        src: "",
        srcdoc: "",
        title: "",
        minHeight: "12rem",
        csp: "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:;",
    }
);

const emit = defineEmits<{
    "frame-action": [actionId: string];
}>();

const frame = ref<HTMLIFrameElement | null>(null);

const frameSrc = computed(() => props.src || undefined);
const frameSrcdoc = computed(() => {
    if (props.src) {
        return undefined;
    }
    if (!props.srcdoc) {
        return undefined;
    }
    const meta = `<meta http-equiv="Content-Security-Policy" content="${props.csp.replace(/"/g, "")}">`;
    if (props.srcdoc.includes("<head>")) {
        return props.srcdoc.replace("<head>", `<head>${meta}`);
    }
    return `<!DOCTYPE html><html><head>${meta}</head><body>${props.srcdoc}</body></html>`;
});

function onLoad() {
    try {
        frame.value?.contentWindow?.postMessage(
            {
                channel: CHANNEL,
                type: "ready",
                pluginId: props.pluginId,
                frameId: props.frameId,
            },
            "*"
        );
    } catch {
        /* opaque sandbox */
    }
}

let onMessage: ((event: MessageEvent) => void) | null = null;

onMounted(() => {
    onMessage = (event: MessageEvent) => {
        if (event.source !== frame.value?.contentWindow) {
            return;
        }
        const data = event.data;
        if (!data || data.channel !== CHANNEL || data.pluginId !== props.pluginId) {
            return;
        }
        if (typeof data.actionId === "string") {
            emit("frame-action", data.actionId);
        }
    };
    window.addEventListener("message", onMessage);
});

onBeforeUnmount(() => {
    if (onMessage) {
        window.removeEventListener("message", onMessage);
    }
});
</script>
