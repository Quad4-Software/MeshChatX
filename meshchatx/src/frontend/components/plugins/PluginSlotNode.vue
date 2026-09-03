<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <p v-if="node.type === 'text'" :class="textClass">
        {{ node.value }}
    </p>

    <div v-else-if="node.type === 'input'" class="space-y-1.5">
        <label v-if="node.label" class="block text-sm font-medium text-sem-fg">
            {{ node.label }}
        </label>
        <textarea
            v-if="node.multiline"
            class="input-field min-h-[6rem]"
            :placeholder="node.placeholder || ''"
            :value="node.value || ''"
            @input="$emit('input', { id: node.id, value: $event.target.value })"
        />
        <input
            v-else
            class="input-field"
            type="text"
            :placeholder="node.placeholder || ''"
            :value="node.value || ''"
            @input="$emit('input', { id: node.id, value: $event.target.value })"
        />
    </div>

    <div v-else-if="node.type === 'number'" class="space-y-1.5">
        <label v-if="node.label" class="block text-sm font-medium text-sem-fg">
            {{ node.label }}
        </label>
        <input
            class="input-field"
            type="number"
            :placeholder="node.placeholder || ''"
            :value="node.value ?? ''"
            :min="node.min"
            :max="node.max"
            :step="node.step"
            @input="$emit('input', { id: node.id, value: $event.target.value })"
        />
    </div>

    <div v-else-if="node.type === 'select'" class="space-y-1.5">
        <label v-if="node.label" class="block text-sm font-medium text-sem-fg">
            {{ node.label }}
        </label>
        <select
            class="input-field"
            :value="node.value || ''"
            @change="$emit('input', { id: node.id, value: $event.target.value })"
        >
            <option v-if="node.placeholder" value="" disabled>
                {{ node.placeholder }}
            </option>
            <option v-for="opt in selectOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
            </option>
        </select>
    </div>

    <label v-else-if="node.type === 'checkbox'" class="flex items-start gap-2.5 text-sm text-sem-fg cursor-pointer">
        <input
            class="mt-0.5 rounded border-sem-border text-sem-accent focus:ring-sem-focus/40"
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

    <div v-else-if="node.type === 'progress'" class="space-y-1">
        <div v-if="node.label" class="text-xs text-sem-fg-muted">{{ node.label }}</div>
        <div class="h-2 w-full overflow-hidden rounded-full bg-sem-surface-muted">
            <div
                class="h-full rounded-full bg-sem-action-primary transition-all"
                :style="{ width: `${progressPercent}%` }"
            />
        </div>
    </div>

    <hr v-else-if="node.type === 'separator'" class="border-0 border-t border-sem-border" />

    <div
        v-else-if="node.type === 'empty'"
        class="rounded-lg border border-dashed border-sem-border px-4 py-8 text-center text-sm text-sem-fg-muted"
    >
        {{ node.value || node.label || "" }}
    </div>

    <pre
        v-else-if="node.type === 'code'"
        class="overflow-auto rounded-lg border border-sem-border bg-sem-surface-muted p-3 font-mono text-xs text-sem-fg whitespace-pre-wrap break-all"
        :style="codeStyle"
        >{{ node.value || "" }}</pre>

    <img
        v-else-if="node.type === 'image' && safeImageSrc"
        :src="safeImageSrc"
        :alt="node.alt || ''"
        class="max-w-full rounded-lg border border-sem-border"
    />

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

    <div v-else-if="node.type === 'tabs'" class="space-y-4">
        <div class="flex flex-wrap gap-2 border-b border-sem-border pb-2">
            <button
                v-for="tab in tabItems"
                :key="tab.id"
                type="button"
                class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
                :class="
                    tab.id === activeTabId
                        ? 'bg-sem-action-primary text-white'
                        : 'text-sem-fg-muted hover:bg-sem-surface-muted'
                "
                @click="$emit('action', `tab:${tab.id}`)"
            >
                {{ tab.label }}
            </button>
        </div>
        <PluginSlotNode
            v-for="(child, index) in activeTabChildren"
            :key="index"
            :node="child"
            :plugin-id="pluginId"
            :allowed-widgets="allowedWidgets"
            :allow-html-frame="allowHtmlFrame"
            @action="$emit('action', $event)"
            @input="$emit('input', $event)"
        />
    </div>

    <div v-else-if="node.type === 'table'" class="overflow-x-auto rounded-lg border border-sem-border">
        <table class="min-w-full text-sm text-sem-fg">
            <thead class="bg-sem-surface-muted text-left text-xs uppercase tracking-wide text-sem-fg-muted">
                <tr>
                    <th v-for="(col, ci) in tableColumns" :key="ci" class="px-3 py-2 font-medium">
                        {{ col }}
                    </th>
                </tr>
            </thead>
            <tbody class="divide-y divide-sem-border bg-sem-surface">
                <tr v-for="(row, ri) in tableRows" :key="ri">
                    <td v-for="(cell, ci) in row" :key="ci" class="px-3 py-2 align-top">
                        <template v-if="cell && typeof cell === 'object' && cell.type">
                            <PluginSlotNode
                                :node="cell"
                                :plugin-id="pluginId"
                                :allowed-widgets="allowedWidgets"
                                :allow-html-frame="allowHtmlFrame"
                                @action="$emit('action', $event)"
                                @input="$emit('input', $event)"
                            />
                        </template>
                        <span v-else>{{ cell }}</span>
                    </td>
                </tr>
            </tbody>
        </table>
        <p v-if="!tableRows.length" class="px-4 py-6 text-center text-sm text-sem-fg-muted">
            {{ node.emptyText || "" }}
        </p>
    </div>

    <div
        v-else-if="node.type === 'section'"
        class="rounded-xl border border-sem-border bg-sem-surface-muted/70 p-4 sm:p-5 space-y-4"
    >
        <div v-if="node.title || node.description" class="space-y-1">
            <h2 v-if="node.title" class="text-base font-semibold text-sem-fg">
                {{ node.title }}
            </h2>
            <p v-if="node.description" class="text-sm text-sem-fg-muted">
                {{ node.description }}
            </p>
        </div>
        <PluginSlotNode
            v-for="(child, index) in node.children || []"
            :key="index"
            :node="child"
            :plugin-id="pluginId"
            :allowed-widgets="allowedWidgets"
            :allow-html-frame="allowHtmlFrame"
            @action="$emit('action', $event)"
            @input="$emit('input', $event)"
        />
    </div>

    <div v-else-if="node.type === 'list'" class="space-y-2">
        <div
            v-if="(node.items || []).length && node.variant === 'cards'"
            class="rounded-lg border border-sem-border overflow-hidden divide-y divide-sem-border bg-sem-surface"
        >
            <PluginSlotNode
                v-for="(item, index) in node.items || []"
                :key="index"
                :node="item"
                :plugin-id="pluginId"
                :allowed-widgets="allowedWidgets"
                :allow-html-frame="allowHtmlFrame"
                @action="$emit('action', $event)"
                @input="$emit('input', $event)"
            />
        </div>
        <template v-else>
            <PluginSlotNode
                v-for="(item, index) in node.items || []"
                :key="index"
                :node="item"
                :plugin-id="pluginId"
                :allowed-widgets="allowedWidgets"
                :allow-html-frame="allowHtmlFrame"
                @action="$emit('action', $event)"
                @input="$emit('input', $event)"
            />
        </template>
        <p
            v-if="!(node.items || []).length"
            class="rounded-lg border border-dashed border-sem-border px-4 py-8 text-center text-sm text-sem-fg-muted"
        >
            {{ node.emptyText || "" }}
        </p>
    </div>

    <div v-else-if="node.type === 'row'" :class="rowClass">
        <PluginSlotNode
            v-for="(child, index) in node.children || []"
            :key="index"
            :node="child"
            :plugin-id="pluginId"
            :allowed-widgets="allowedWidgets"
            :allow-html-frame="allowHtmlFrame"
            @action="$emit('action', $event)"
            @input="$emit('input', $event)"
        />
    </div>

    <div v-else-if="node.type === 'column'" class="space-y-4">
        <PluginSlotNode
            v-for="(child, index) in node.children || []"
            :key="index"
            :node="child"
            :plugin-id="pluginId"
            :allowed-widgets="allowedWidgets"
            :allow-html-frame="allowHtmlFrame"
            @action="$emit('action', $event)"
            @input="$emit('input', $event)"
        />
    </div>

    <component :is="widgetComponent" v-else-if="node.type === 'widget' && widgetComponent" v-bind="node.props || {}" />

    <PluginHtmlFrame
        v-else-if="node.type === 'html-frame' && allowHtmlFrame"
        :plugin-id="pluginId"
        :frame-id="node.id || ''"
        :src="safeImageSrc || node.src || ''"
        :srcdoc="node.srcdoc || ''"
        :title="node.title || ''"
        :min-height="node.minHeight || '12rem'"
        @frame-action="$emit('action', $event)"
    />

    <div
        v-else-if="node.type"
        class="rounded-lg border border-sem-border bg-sem-surface-muted px-3 py-2 text-sm text-sem-danger"
    >
        Unknown or disallowed UI node: {{ node.type }}
    </div>
</template>

<script>
import PluginHtmlFrame from "./PluginHtmlFrame.vue";
import { resolveHostWidget } from "../../js/plugins/pluginHostWidgets.js";
import { sanitizePluginAssetSrc } from "../../js/plugins/pluginUiDescriptor.js";

export default {
    name: "PluginSlotNode",
    components: { PluginHtmlFrame },
    props: {
        node: {
            type: Object,
            required: true,
        },
        pluginId: {
            type: String,
            default: "",
        },
        allowedWidgets: {
            type: Array,
            default: () => [],
        },
        allowHtmlFrame: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["action", "input"],
    computed: {
        textClass() {
            const variant = this.node.variant || "body";
            const map = {
                title: "text-xl font-bold tracking-tight text-sem-fg",
                subtitle: "text-base font-semibold text-sem-fg",
                body: "text-sm leading-relaxed text-sem-fg",
                caption: "text-xs text-sem-fg-muted",
                mono: "font-mono text-xs text-sem-fg break-all",
                stat: "text-sm font-medium text-sem-fg",
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
                return "grid grid-cols-1 sm:grid-cols-[minmax(0,1.15fr)_auto_minmax(0,1.35fr)_auto] gap-x-4 gap-y-2 items-center px-4 py-3 text-sm bg-sem-surface";
            }
            if (variant === "announce-card") {
                return "grid grid-cols-1 sm:grid-cols-[auto_minmax(0,0.75fr)_minmax(0,1fr)_minmax(0,1.1fr)] gap-x-4 gap-y-2 items-center px-4 py-3 text-sm bg-sem-surface";
            }
            return "flex flex-wrap items-center gap-3 text-sm";
        },
        badgeClass() {
            const variant = this.node.variant || "muted";
            const map = {
                success: "bg-sem-success/15 text-sem-success",
                danger: "bg-sem-danger/15 text-sem-danger",
                warning: "bg-sem-warning/15 text-sem-warning",
                info: "bg-sem-info/15 text-sem-info",
                muted: "bg-sem-surface-muted text-sem-fg-muted",
            };
            return map[variant] || map.muted;
        },
        selectOptions() {
            const options = this.node.options || [];
            return options.map((opt) => {
                if (opt && typeof opt === "object") {
                    return {
                        value: String(opt.value ?? ""),
                        label: String(opt.label ?? opt.value ?? ""),
                    };
                }
                return { value: String(opt), label: String(opt) };
            });
        },
        progressPercent() {
            const value = Number(this.node.value);
            const max = Number(this.node.max);
            const pct = Number.isFinite(value) ? (max > 0 ? (value / max) * 100 : value) : 0;
            return Math.max(0, Math.min(100, pct));
        },
        codeStyle() {
            if (this.node.maxHeight) {
                return { maxHeight: String(this.node.maxHeight) };
            }
            return { maxHeight: "16rem" };
        },
        safeImageSrc() {
            if (!this.pluginId || !this.node.src) {
                return "";
            }
            return sanitizePluginAssetSrc(this.pluginId, this.node.src) || "";
        },
        tabItems() {
            return (this.node.tabs || []).map((tab) => ({
                id: String(tab.id || ""),
                label: String(tab.label || tab.id || ""),
            }));
        },
        activeTabId() {
            return String(this.node.active || this.tabItems[0]?.id || "");
        },
        activeTabChildren() {
            const panels = this.node.panels || [];
            const match = panels.find((p) => String(p.id) === this.activeTabId);
            if (match && Array.isArray(match.children)) {
                return match.children;
            }
            if (match && match.type) {
                return [match];
            }
            return [];
        },
        tableColumns() {
            return (this.node.columns || []).map((c) => (typeof c === "string" ? c : String(c?.label || "")));
        },
        tableRows() {
            return (this.node.rows || []).map((row) => {
                if (Array.isArray(row)) {
                    return row;
                }
                if (row && typeof row === "object" && Array.isArray(row.cells)) {
                    return row.cells;
                }
                return [];
            });
        },
        widgetComponent() {
            if (this.node.type !== "widget") {
                return null;
            }
            const name = this.node.name;
            if (!this.allowedWidgets.includes(name)) {
                return null;
            }
            return resolveHostWidget(name);
        },
    },
    methods: {
        actionButtonClass(action) {
            const base =
                "inline-flex items-center justify-center px-4 py-2 rounded-lg text-sm font-medium transition-colors focus:outline-hidden focus:ring-2 focus:ring-sem-focus/40 w-fit";
            if (action.variant === "secondary") {
                return `${base} secondary-chip border border-sem-border bg-sem-surface text-sem-fg hover:bg-sem-surface-muted`;
            }
            if (action.variant === "danger") {
                return `${base} danger-chip border border-sem-danger/40 bg-sem-surface text-sem-danger hover:bg-sem-danger/10`;
            }
            return `${base} primary-chip bg-sem-action-primary text-white hover:bg-sem-action-primary-hover`;
        },
    },
};
</script>
