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

<script>
import PluginSlotRenderer from "./PluginSlotRenderer.vue";
import { pluginHost } from "../../js/plugins/PluginHost.js";
import { GlobalState } from "../../js/GlobalState.js";
import { resolveEffectiveTheme, shellCanvasBackgroundStyle } from "../../theme/themeEngine.js";

export default {
    name: "PluginPage",
    components: { PluginSlotRenderer },
    props: {
        pluginId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            descriptor: null,
            uiError: "",
            allowedWidgets: [],
            allowHtmlFrame: false,
        };
    },
    computed: {
        config() {
            return GlobalState.config || {};
        },
        effectiveThemeMode() {
            return resolveEffectiveTheme(this.config.theme);
        },
        pageStyle() {
            const transparency = Number(this.config.ui_transparency) || 0;
            if (transparency <= 0) {
                return {};
            }
            return {
                backgroundColor: shellCanvasBackgroundStyle(this.config, this.effectiveThemeMode),
            };
        },
        panelClass() {
            const glass = this.config.ui_glass_enabled !== false;
            return glass ? "glass-card bg-sem-surface/90" : "bg-sem-surface";
        },
    },
    mounted() {
        const caps = pluginHost.getPluginUiCaps(this.pluginId);
        this.allowedWidgets = caps.allowedWidgets || [];
        this.allowHtmlFrame = Boolean(caps.allowHtmlFrame);
        this.descriptor = pluginHost.getLastDescriptor(this.pluginId);
        this.uiError = pluginHost.getLastUiError(this.pluginId) || "";
        this.uiListener = (event) => {
            if (event.detail?.pluginId === this.pluginId) {
                this.descriptor = event.detail.descriptor;
                this.uiError = event.detail.error || "";
            }
        };
        this.errorListener = (event) => {
            if (event.detail?.pluginId === this.pluginId && event.detail?.uiError) {
                this.uiError = event.detail.message || "";
            }
        };
        window.addEventListener("meshchatx-plugin-ui", this.uiListener);
        window.addEventListener("meshchatx-plugin-ui-error", this.errorListener);
        pluginHost.requestUiRefresh(this.pluginId);
    },
    beforeUnmount() {
        window.removeEventListener("meshchatx-plugin-ui", this.uiListener);
        window.removeEventListener("meshchatx-plugin-ui-error", this.errorListener);
    },
    methods: {
        onAction(actionId) {
            pluginHost.postAction(this.pluginId, actionId);
        },
        onInput(payload) {
            pluginHost.postInput(this.pluginId, payload.id, payload.value);
        },
    },
};
</script>
