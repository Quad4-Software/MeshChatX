<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="h-full overflow-y-auto p-4 sm:p-6" :style="pageStyle">
        <div class="mx-auto max-w-5xl rounded-xl border border-sem-border p-4 sm:p-6 shadow-sm" :class="panelClass">
            <PluginSlotRenderer
                :plugin-id="pluginId"
                :descriptor="descriptor"
                :allowed-widgets="allowedWidgets"
                :allow-html-frame="allowHtmlFrame"
                :ui-error="uiError"
                @action="onAction"
                @input="onInput"
            />
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useConfigStore } from "../../js/stores/configStore";

import PluginSlotRenderer from "./PluginSlotRenderer.vue";
import { pluginHost } from "../../js/plugins/PluginHost.js";
import { resolveEffectiveTheme, shellCanvasBackgroundStyle } from "../../theme/themeEngine.js";

const props = defineProps<{
    pluginId: string;
}>();

const descriptor = ref<any>(null);
const uiError = ref("");
const allowedWidgets = ref<string[]>([]);
const allowHtmlFrame = ref(false);

const config = computed(() => useConfigStore().config || {});
const effectiveThemeMode = computed(() => resolveEffectiveTheme(config.value.theme));
const pageStyle = computed(() => {
    const transparency = Number(config.value.ui_transparency) || 0;
    if (transparency <= 0) {
        return {};
    }
    return {
        backgroundColor: shellCanvasBackgroundStyle(config.value, effectiveThemeMode.value),
    };
});
const panelClass = computed(() => {
    const glass = config.value.ui_glass_enabled !== false;
    return glass ? "glass-card bg-sem-surface/90" : "bg-sem-surface";
});

let uiListener: ((event: Event) => void) | null = null;
let errorListener: ((event: Event) => void) | null = null;

onMounted(() => {
    const caps = pluginHost.getPluginUiCaps(props.pluginId);
    allowedWidgets.value = caps.allowedWidgets || [];
    allowHtmlFrame.value = Boolean(caps.allowHtmlFrame);
    descriptor.value = pluginHost.getLastDescriptor(props.pluginId);
    uiError.value = pluginHost.getLastUiError(props.pluginId) || "";
    uiListener = (event: Event) => {
        const detail = (event as CustomEvent).detail;
        if (detail?.pluginId === props.pluginId) {
            descriptor.value = detail.descriptor;
            uiError.value = detail.error || "";
        }
    };
    errorListener = (event: Event) => {
        const detail = (event as CustomEvent).detail;
        if (detail?.pluginId === props.pluginId && detail?.uiError) {
            uiError.value = detail.message || "";
        }
    };
    window.addEventListener("meshchatx-plugin-ui", uiListener);
    window.addEventListener("meshchatx-plugin-ui-error", errorListener);
    pluginHost.requestUiRefresh(props.pluginId);
});

onBeforeUnmount(() => {
    if (uiListener) {
        window.removeEventListener("meshchatx-plugin-ui", uiListener);
    }
    if (errorListener) {
        window.removeEventListener("meshchatx-plugin-ui-error", errorListener);
    }
});

function onAction(actionId: string) {
    pluginHost.postAction(props.pluginId, actionId);
}

function onInput(payload: { id: string; value: any }) {
    pluginHost.postInput(props.pluginId, payload.id, payload.value);
}
</script>
