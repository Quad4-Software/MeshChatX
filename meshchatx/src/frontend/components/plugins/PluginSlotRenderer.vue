<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="plugin-slot space-y-6">
        <div
            v-if="uiError"
            class="rounded-lg border border-sem-danger/40 bg-sem-danger/10 px-3 py-2 text-sm text-sem-danger"
        >
            {{ uiError }}
        </div>
        <PluginSlotNode
            v-for="(node, index) in nodes"
            :key="index"
            :node="node"
            :plugin-id="pluginId"
            :allowed-widgets="allowedWidgets"
            :allow-html-frame="allowHtmlFrame"
            @action="$emit('action', $event)"
            @input="$emit('input', $event)"
        />
    </div>
</template>

<script>
import PluginSlotNode from "./PluginSlotNode.vue";

export default {
    name: "PluginSlotRenderer",
    components: { PluginSlotNode },
    props: {
        descriptor: {
            type: Object,
            default: null,
        },
        pluginId: {
            type: String,
            required: true,
        },
        allowedWidgets: {
            type: Array,
            default: () => [],
        },
        allowHtmlFrame: {
            type: Boolean,
            default: false,
        },
        uiError: {
            type: String,
            default: "",
        },
    },
    emits: ["action", "input"],
    computed: {
        nodes() {
            if (!this.descriptor) {
                return [];
            }
            if (this.descriptor.type === "column" && Array.isArray(this.descriptor.children)) {
                return this.descriptor.children;
            }
            return [this.descriptor];
        },
    },
};
</script>
