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
            @action="emit('action', $event)"
            @input="emit('input', $event)"
        />
    </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import PluginSlotNode from "./PluginSlotNode.vue";

interface SlotNode {
    type?: string;
    children?: SlotNode[];
    [key: string]: any;
}

const props = withDefaults(
    defineProps<{
        descriptor?: SlotNode | null;
        pluginId: string;
        allowedWidgets?: string[];
        allowHtmlFrame?: boolean;
        uiError?: string;
    }>(),
    {
        descriptor: null,
        allowedWidgets: () => [],
        allowHtmlFrame: false,
        uiError: "",
    }
);

const emit = defineEmits<{
    action: [event: any];
    input: [event: any];
}>();

const nodes = computed(() => {
    if (!props.descriptor) {
        return [];
    }
    if (props.descriptor.type === "column" && Array.isArray(props.descriptor.children)) {
        return props.descriptor.children;
    }
    return [props.descriptor];
});
</script>
