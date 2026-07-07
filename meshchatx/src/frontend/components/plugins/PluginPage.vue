<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="h-full overflow-y-auto p-4 sm:p-6">
        <div
            class="mx-auto max-w-3xl rounded-xl border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4 sm:p-6"
        >
            <PluginSlotRenderer :plugin-id="pluginId" :descriptor="descriptor" @action="onAction" @input="onInput" />
        </div>
    </div>
</template>

<script>
import PluginSlotRenderer from "./PluginSlotRenderer.vue";
import { pluginHost } from "../../js/plugins/PluginHost.js";

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
        };
    },
    mounted() {
        this.descriptor = pluginHost.getLastDescriptor(this.pluginId);
        this.uiListener = (event) => {
            if (event.detail?.pluginId === this.pluginId) {
                this.descriptor = event.detail.descriptor;
            }
        };
        window.addEventListener("meshchatx-plugin-ui", this.uiListener);
        pluginHost.requestUiRefresh(this.pluginId);
    },
    beforeUnmount() {
        window.removeEventListener("meshchatx-plugin-ui", this.uiListener);
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
