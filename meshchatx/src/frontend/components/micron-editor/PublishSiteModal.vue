<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        v-if="show"
        class="fixed inset-0 z-100 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/50"
        @click.self="close"
    >
        <div
            class="w-full sm:max-w-xl flex flex-col max-sm:h-[92dvh] max-sm:max-h-[92dvh] sm:max-h-[90vh] rounded-t-2xl sm:rounded-lg border border-sem-border bg-sem-surface shadow-xl touch-pan-y min-h-0"
        >
            <div class="flex justify-between items-start gap-2 p-3 sm:p-5 border-b border-sem-border shrink-0">
                <div class="min-w-0 pr-2">
                    <h3 class="text-lg sm:text-xl font-bold text-sem-fg">
                        {{ $t("tools.micron_editor.publish_site_title") }}
                    </h3>
                    <p class="text-sm text-gray-600 dark:text-gray-400 mt-0.5">
                        {{ $t("tools.micron_editor.publish_site_hint") }}
                    </p>
                </div>
                <button
                    type="button"
                    class="p-2 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 shrink-0"
                    :disabled="busy"
                    @click="close"
                >
                    <MaterialDesignIcon icon-name="close" class="size-5" />
                </button>
            </div>

            <div class="flex-1 min-h-0 overflow-y-auto p-3 sm:p-5 space-y-4">
                <div>
                    <label class="block text-xs font-bold uppercase tracking-wider text-sem-fg-muted mb-1.5">
                        {{ $t("tools.micron_editor.publish_site_server") }}
                    </label>
                    <select
                        v-model="selectedNodeId"
                        class="w-full rounded-lg border border-sem-border bg-sem-surface text-sem-fg px-3 py-2 text-sm focus:outline-hidden focus:ring-2 focus:ring-sem-accent"
                        :disabled="busy"
                    >
                        <option v-for="pn in pageNodes" :key="pn.node_id" :value="pn.node_id">
                            {{ pn.name }}{{ pn.running ? "" : " · " + $t("tools.micron_editor.publish_will_start") }}
                        </option>
                        <option value="__new">{{ $t("tools.micron_editor.publish_site_new_server") }}</option>
                    </select>
                    <input
                        v-if="selectedNodeId === '__new'"
                        v-model="newServerName"
                        type="text"
                        class="mt-2 w-full rounded-lg border border-sem-border bg-sem-surface text-sem-fg px-3 py-2 text-sm focus:outline-hidden focus:ring-2 focus:ring-sem-accent"
                        :placeholder="$t('tools.micron_editor.publish_site_new_server_name')"
                        :disabled="busy"
                    />
                </div>

                <div>
                    <div class="text-xs font-bold uppercase tracking-wider text-sem-fg-muted mb-1.5">
                        {{ $t("tools.micron_editor.publish_site_pages") }}
                    </div>
                    <ul class="space-y-1">
                        <li
                            v-for="(entry, index) in entries"
                            :key="entry.tabId"
                            draggable="true"
                            class="flex items-center gap-2 rounded-lg border border-sem-border bg-sem-surface-muted px-2 py-1.5 transition-colors"
                            :class="{ 'opacity-50': !entry.include, 'ring-2 ring-sem-accent': dragOverIndex === index }"
                            @dragstart="onDragStart(index)"
                            @dragover.prevent="dragOverIndex = index"
                            @dragleave="dragOverIndex = -1"
                            @drop.prevent="onDrop(index)"
                            @dragend="dragOverIndex = -1"
                        >
                            <MaterialDesignIcon
                                icon-name="drag-vertical"
                                class="size-4 text-sem-fg-muted cursor-grab shrink-0"
                            />
                            <input
                                v-model="entry.include"
                                type="checkbox"
                                class="size-4 shrink-0 accent-teal-600"
                                :disabled="busy"
                                :title="$t('tools.micron_editor.publish_site_include')"
                            />
                            <span class="text-xs text-sem-fg-muted truncate w-24 shrink-0" :title="entry.tabName">{{
                                entry.tabName
                            }}</span>
                            <input
                                v-model="entry.filename"
                                type="text"
                                spellcheck="false"
                                class="flex-1 min-w-0 rounded-md border border-sem-border bg-sem-surface text-sem-fg px-2 py-1 text-xs font-mono focus:outline-hidden focus:ring-2 focus:ring-sem-accent"
                                :disabled="busy || !entry.include"
                                @input="entry.filename = sanitizeFilename(entry.filename)"
                            />
                            <button
                                type="button"
                                class="p-1 rounded-md text-sem-fg-muted hover:text-sem-fg hover:bg-sem-surface disabled:opacity-30"
                                :disabled="busy || index === 0"
                                :title="$t('tools.micron_editor.publish_site_move_up')"
                                @click="moveEntry(index, -1)"
                            >
                                <MaterialDesignIcon icon-name="arrow-up" class="size-3.5" />
                            </button>
                            <button
                                type="button"
                                class="p-1 rounded-md text-sem-fg-muted hover:text-sem-fg hover:bg-sem-surface disabled:opacity-30"
                                :disabled="busy || index === entries.length - 1"
                                :title="$t('tools.micron_editor.publish_site_move_down')"
                                @click="moveEntry(index, 1)"
                            >
                                <MaterialDesignIcon icon-name="arrow-down" class="size-3.5" />
                            </button>
                        </li>
                    </ul>
                </div>

                <label class="flex items-start gap-2 text-sm text-sem-fg cursor-pointer">
                    <input
                        v-model="generateIndex"
                        type="checkbox"
                        class="size-4 mt-0.5 shrink-0 accent-teal-600"
                        :disabled="busy"
                    />
                    <span>
                        {{ $t("tools.micron_editor.publish_site_index") }}
                        <span class="block text-xs text-sem-fg-muted">
                            {{ $t("tools.micron_editor.publish_site_index_hint") }}
                        </span>
                    </span>
                </label>
            </div>

            <div class="flex items-center justify-end gap-2 p-3 sm:p-5 border-t border-sem-border shrink-0">
                <button type="button" class="secondary-chip py-1.5! px-3!" :disabled="busy" @click="close">
                    {{ $t("common.cancel") }}
                </button>
                <button
                    type="button"
                    class="primary-chip py-1.5! px-3!"
                    :disabled="busy || includedCount === 0 || !canSubmit"
                    @click="submit"
                >
                    {{ $t("tools.micron_editor.publish_site_publish", { count: includedCount }) }}
                </button>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

const ALLOWED_PAGE_EXTENSIONS = [".mu", ".md", ".txt", ".html"];
const NEW_SERVER = "__new";

export default {
    name: "PublishSiteModal",
    components: {
        MaterialDesignIcon,
    },
    props: {
        show: {
            type: Boolean,
            default: false,
        },
        tabs: {
            type: Array,
            default: () => [],
        },
        pageNodes: {
            type: Array,
            default: () => [],
        },
        busy: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["close", "publish"],
    data() {
        return {
            selectedNodeId: "",
            newServerName: "",
            entries: [],
            generateIndex: true,
            dragIndex: -1,
            dragOverIndex: -1,
        };
    },
    computed: {
        includedCount() {
            return this.entries.filter((e) => e.include && e.filename.trim()).length;
        },
        canSubmit() {
            if (this.selectedNodeId === NEW_SERVER) {
                return this.newServerName.trim().length > 0;
            }
            return Boolean(this.selectedNodeId);
        },
    },
    watch: {
        show: {
            immediate: true,
            handler(visible) {
                if (visible) {
                    this.reset();
                }
            },
        },
    },
    methods: {
        reset() {
            this.selectedNodeId = this.pageNodes[0]?.node_id || NEW_SERVER;
            this.newServerName = "";
            this.generateIndex = true;
            this.dragIndex = -1;
            this.dragOverIndex = -1;
            this.entries = this.tabs.map((tab, index) => ({
                tabId: tab.id,
                tabName: tab.name || "",
                content: tab.content,
                include: true,
                filename: this.defaultFilename(tab, index),
            }));
        },
        defaultFilename(tab, index) {
            const raw = String(tab?.name || "").trim();
            const cleaned = this.sanitizeFilename(raw.replace(/\s+/g, "_"));
            const lower = cleaned.toLowerCase();
            for (const ext of ALLOWED_PAGE_EXTENSIONS) {
                if (lower.endsWith(ext)) {
                    return cleaned;
                }
            }
            const base = cleaned || `page_${index + 1}`;
            return `${base}.mu`;
        },
        sanitizeFilename(value) {
            return String(value || "")
                .replace(/\s+/g, "_")
                .replace(/[^\w.-]/g, "")
                .replace(/\.{2,}/g, ".")
                .replace(/^\.+/, "");
        },
        moveEntry(index, delta) {
            const target = index + delta;
            if (target < 0 || target >= this.entries.length) {
                return;
            }
            const [item] = this.entries.splice(index, 1);
            this.entries.splice(target, 0, item);
        },
        onDragStart(index) {
            this.dragIndex = index;
        },
        onDrop(index) {
            if (this.dragIndex < 0 || this.dragIndex === index) {
                return;
            }
            const [item] = this.entries.splice(this.dragIndex, 1);
            this.entries.splice(index, 0, item);
            this.dragIndex = -1;
        },
        close() {
            if (this.busy) {
                return;
            }
            this.$emit("close");
        },
        submit() {
            const pages = this.entries
                .filter((e) => e.include && e.filename.trim())
                .map((e) => ({
                    name: e.filename.trim(),
                    content: e.content,
                    label: e.tabName,
                }));
            if (pages.length === 0 || !this.canSubmit) {
                return;
            }
            this.$emit("publish", {
                nodeId: this.selectedNodeId === NEW_SERVER ? null : this.selectedNodeId,
                newServerName: this.selectedNodeId === NEW_SERVER ? this.newServerName.trim() : "",
                pages,
                generateIndex: this.generateIndex,
            });
        },
    },
};
</script>
