<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="plugin-slot space-y-4">
        <template v-for="(node, index) in nodes" :key="index">
            <component
                :is="resolveComponent(node)"
                v-bind="nodeProps(node)"
                @click="onNodeAction(node)"
                @input="onNodeInput(node, $event)"
            />
        </template>
    </div>
</template>

<script>
export default {
    name: "PluginSlotRenderer",
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
    methods: {
        resolveComponent(node) {
            switch (node.type) {
                case "text":
                    return "p";
                case "button":
                    return "button";
                case "input":
                    return "input";
                case "list":
                    return "div";
                case "row":
                    return "div";
                default:
                    return "div";
            }
        },
        nodeProps(node) {
            if (node.type === "text") {
                return {
                    class:
                        node.variant === "title"
                            ? "text-lg font-semibold text-gray-900 dark:text-gray-100"
                            : "text-sm text-gray-700 dark:text-gray-300",
                    textContent: node.value,
                };
            }
            if (node.type === "button") {
                return {
                    class: "px-3 py-2 rounded-md bg-blue-600 text-white text-sm hover:bg-blue-700",
                    type: "button",
                    "data-action-id": node.id,
                };
            }
            if (node.type === "input") {
                return {
                    class: "w-full rounded-md border border-gray-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm",
                    type: "text",
                    placeholder: node.placeholder || "",
                    "data-input-id": node.id,
                    value: node.value || "",
                };
            }
            if (node.type === "list") {
                return { class: "space-y-2" };
            }
            if (node.type === "row") {
                return { class: "flex items-center justify-between gap-3 text-sm" };
            }
            return {};
        },
        onNodeAction(node) {
            if (node.type === "button" && node.id) {
                this.$emit("action", node.id);
            }
        },
        onNodeInput(node, event) {
            if (node.type === "input" && node.id) {
                this.$emit("input", { id: node.id, value: event.target.value });
            }
        },
    },
};
</script>
