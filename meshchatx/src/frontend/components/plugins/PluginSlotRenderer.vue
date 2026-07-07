<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="plugin-slot space-y-6">
        <PluginSlotNode
            v-for="(node, index) in nodes"
            :key="index"
            :node="node"
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
