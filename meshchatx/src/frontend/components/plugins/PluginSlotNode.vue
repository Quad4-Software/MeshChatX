<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <p v-if="node.type === 'text'" :class="textClass">
        {{ node.value }}
    </p>

    <div v-else-if="node.type === 'input'" class="space-y-1.5">
        <label v-if="node.label" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
            {{ node.label }}
        </label>
        <textarea
            v-if="node.multiline"
            class="w-full rounded-lg border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2.5 text-sm text-gray-900 dark:text-gray-100 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 min-h-[6rem]"
            :placeholder="node.placeholder || ''"
            :value="node.value || ''"
            @input="$emit('input', { id: node.id, value: $event.target.value })"
        />
        <input
            v-else
            class="w-full rounded-lg border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2.5 text-sm text-gray-900 dark:text-gray-100 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500"
            type="text"
            :placeholder="node.placeholder || ''"
            :value="node.value || ''"
            @input="$emit('input', { id: node.id, value: $event.target.value })"
        />
    </div>

    <label
        v-else-if="node.type === 'checkbox'"
        class="flex items-start gap-2.5 text-sm text-gray-700 dark:text-gray-300 cursor-pointer"
    >
        <input
            class="mt-0.5 rounded border-gray-300 dark:border-zinc-600 text-blue-600 focus:ring-blue-500/40"
            type="checkbox"
            :checked="Boolean(node.checked)"
            @change="$emit('input', { id: node.id, value: $event.target.checked ? '1' : '0' })"
        />
        <span>{{ node.label }}</span>
    </label>

    <button v-else-if="node.type === 'button'" type="button" :class="buttonClass" @click="$emit('action', node.id)">
        {{ node.label }}
    </button>

    <span
        v-else-if="node.type === 'badge'"
        class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium whitespace-nowrap"
        :class="badgeClass"
    >
        {{ node.label }}
    </span>

    <div v-else-if="node.type === 'actions'" class="flex flex-wrap items-center gap-2">
        <button
            v-for="action in node.items || []"
            :key="action.id"
            type="button"
            :class="actionButtonClass(action)"
            @click="$emit('action', action.id)"
        >
            {{ action.label }}
        </button>
    </div>

    <div
        v-else-if="node.type === 'section'"
        class="rounded-xl border border-gray-200 dark:border-zinc-800 bg-gray-50/70 dark:bg-zinc-900/40 p-4 sm:p-5 space-y-4"
    >
        <div v-if="node.title || node.description" class="space-y-1">
            <h2 v-if="node.title" class="text-base font-semibold text-gray-900 dark:text-gray-100">
                {{ node.title }}
            </h2>
            <p v-if="node.description" class="text-sm text-gray-600 dark:text-gray-400">
                {{ node.description }}
            </p>
        </div>
        <PluginSlotNode
            v-for="(child, index) in node.children || []"
            :key="index"
            :node="child"
            @action="$emit('action', $event)"
            @input="$emit('input', $event)"
        />
    </div>

    <div v-else-if="node.type === 'list'" class="space-y-2">
        <div
            v-if="(node.items || []).length && node.variant === 'cards'"
            class="rounded-lg border border-gray-200 dark:border-zinc-800 overflow-hidden divide-y divide-gray-200 dark:divide-zinc-800 bg-white dark:bg-zinc-950"
        >
            <PluginSlotNode
                v-for="(item, index) in node.items || []"
                :key="index"
                :node="item"
                @action="$emit('action', $event)"
                @input="$emit('input', $event)"
            />
        </div>
        <template v-else>
            <PluginSlotNode
                v-for="(item, index) in node.items || []"
                :key="index"
                :node="item"
                @action="$emit('action', $event)"
                @input="$emit('input', $event)"
            />
        </template>
        <p
            v-if="!(node.items || []).length"
            class="rounded-lg border border-dashed border-gray-300 dark:border-zinc-700 px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400"
        >
            {{ node.emptyText || "" }}
        </p>
    </div>

    <div v-else-if="node.type === 'row'" :class="rowClass">
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
    computed: {
        textClass() {
            const variant = this.node.variant || "body";
            const map = {
                title: "text-xl font-bold tracking-tight text-gray-900 dark:text-gray-100",
                subtitle: "text-base font-semibold text-gray-900 dark:text-gray-100",
                body: "text-sm leading-relaxed text-gray-700 dark:text-gray-300",
                caption: "text-xs text-gray-500 dark:text-gray-400",
                mono: "font-mono text-xs text-gray-800 dark:text-gray-200 break-all",
                stat: "text-sm font-medium text-gray-800 dark:text-gray-200",
            };
            return map[variant] || map.body;
        },
        buttonClass() {
            return this.actionButtonClass(this.node);
        },
        rowClass() {
            const variant = this.node.variant || "default";
            if (variant === "path") {
                return "grid grid-cols-1 sm:grid-cols-[minmax(0,1.15fr)_auto_minmax(0,1.35fr)_auto] gap-x-4 gap-y-2 items-center px-4 py-3 text-sm";
            }
            if (variant === "announce") {
                return "grid grid-cols-1 sm:grid-cols-[auto_minmax(0,0.75fr)_minmax(0,1fr)_minmax(0,1.1fr)] gap-x-4 gap-y-2 items-center px-4 py-3 text-sm";
            }
            if (variant === "card") {
                return "grid grid-cols-1 sm:grid-cols-[minmax(0,1.15fr)_auto_minmax(0,1.35fr)_auto] gap-x-4 gap-y-2 items-center px-4 py-3 text-sm bg-white dark:bg-zinc-950";
            }
            if (variant === "announce-card") {
                return "grid grid-cols-1 sm:grid-cols-[auto_minmax(0,0.75fr)_minmax(0,1fr)_minmax(0,1.1fr)] gap-x-4 gap-y-2 items-center px-4 py-3 text-sm bg-white dark:bg-zinc-950";
            }
            return "flex flex-wrap items-center gap-3 text-sm";
        },
        badgeClass() {
            const variant = this.node.variant || "muted";
            const map = {
                success: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200",
                danger: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200",
                muted: "bg-gray-100 text-gray-700 dark:bg-zinc-800 dark:text-zinc-300",
            };
            return map[variant] || map.muted;
        },
    },
    methods: {
        actionButtonClass(action) {
            const base =
                "inline-flex items-center justify-center px-4 py-2 rounded-lg text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500/40 w-fit";
            if (action.variant === "secondary") {
                return `${base} border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-900 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-zinc-800`;
            }
            if (action.variant === "danger") {
                return `${base} border border-red-300 dark:border-red-800 bg-white dark:bg-zinc-900 text-red-600 dark:text-red-300 hover:bg-red-50 dark:hover:bg-red-950/30`;
            }
            return `${base} bg-blue-600 text-white hover:bg-blue-700`;
        },
    },
};
</script>
