<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <p
        v-if="node.type === 'text'"
        :class="
            node.variant === 'title'
                ? 'text-lg font-semibold text-gray-900 dark:text-gray-100'
                : 'text-sm text-gray-700 dark:text-gray-300'
        "
    >
        {{ node.value }}
    </p>

    <div v-else-if="node.type === 'input'" class="space-y-1">
        <label v-if="node.label" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
            {{ node.label }}
        </label>
        <input
            class="w-full rounded-md border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm"
            type="text"
            :placeholder="node.placeholder || ''"
            :value="node.value || ''"
            @input="$emit('input', { id: node.id, value: $event.target.value })"
        />
    </div>

    <button
        v-else-if="node.type === 'button'"
        type="button"
        class="px-3 py-2 rounded-md bg-blue-600 text-white text-sm hover:bg-blue-700"
        @click="$emit('action', node.id)"
    >
        {{ node.label }}
    </button>

    <div v-else-if="node.type === 'list'" class="space-y-2">
        <PluginSlotNode
            v-for="(item, index) in node.items || []"
            :key="index"
            :node="item"
            @action="$emit('action', $event)"
            @input="$emit('input', $event)"
        />
        <p v-if="!(node.items || []).length" class="text-sm text-gray-500 dark:text-gray-400">
            {{ node.emptyText || "" }}
        </p>
    </div>

    <div v-else-if="node.type === 'row'" class="flex items-center justify-between gap-3 text-sm">
        <PluginSlotNode
            v-for="(child, index) in node.children || []"
            :key="index"
            :node="child"
            @action="$emit('action', $event)"
            @input="$emit('input', $event)"
        />
    </div>

    <div v-else-if="node.type === 'column'" class="space-y-4">
        <PluginSlotNode
            v-for="(child, index) in node.children || []"
            :key="index"
            :node="child"
            @action="$emit('action', $event)"
            @input="$emit('input', $event)"
        />
    </div>
</template>

<script>
export default {
    name: "PluginSlotNode",
    props: {
        node: {
            type: Object,
            required: true,
        },
    },
    emits: ["action", "input"],
};
</script>
