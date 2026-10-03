<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div
        v-if="show"
        class="fixed inset-0 z-100 flex items-center justify-center bg-black/50 p-4 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-[max(0.75rem,env(safe-area-inset-top))] backdrop-blur-xs"
        @click.self="onCancel"
    >
        <div
            class="flex max-h-[min(90dvh,34rem)] w-full max-w-sm flex-col overflow-hidden rounded-2xl bg-sem-surface shadow-2xl"
        >
            <div class="flex items-center justify-between border-b border-sem-border px-5 py-4">
                <h3 class="text-base font-bold text-sem-fg">
                    {{ $t("messages.filters_edit_title") }}
                </h3>
                <button type="button" class="text-sem-fg-muted transition-colors hover:text-sem-fg" @click="onCancel">
                    <MaterialDesignIcon icon-name="close" class="size-5" />
                </button>
            </div>
            <div class="px-5 pt-3 text-xs text-sem-fg-muted">
                {{ $t("messages.filters_edit_hint") }}
            </div>
            <div class="flex-1 overflow-y-auto p-3">
                <div
                    v-for="(row, index) in working"
                    :key="row.id"
                    class="group flex items-center gap-2 rounded-lg px-2 py-1.5 transition-colors"
                    :class="[
                        dropIndex === index ? 'bg-sem-surface-muted ring-1 ring-sem-accent' : '',
                        dragIndex === index ? 'opacity-40' : '',
                    ]"
                    draggable="true"
                    @dragstart="onRowDragStart($event, index)"
                    @dragover.prevent="onRowDragOver(index)"
                    @dragleave="onRowDragLeave(index)"
                    @drop.prevent="onRowDrop(index)"
                    @dragend="onRowDragEnd"
                >
                    <MaterialDesignIcon
                        icon-name="drag-vertical"
                        class="size-5 shrink-0 cursor-grab text-sem-fg-muted"
                    />
                    <MaterialDesignIcon :icon-name="defFor(row.id).icon" class="size-4 shrink-0 text-sem-fg-muted" />
                    <span class="min-w-0 flex-1 truncate text-sm text-sem-fg">{{ rowLabel(row.id) }}</span>
                    <button
                        v-if="isCustomId(row.id)"
                        type="button"
                        class="flex size-6 items-center justify-center rounded text-sem-fg-muted transition-colors hover:bg-sem-surface hover:text-sem-action-danger"
                        :title="$t('messages.filters_custom_remove')"
                        @click="removeCustom(index)"
                    >
                        <MaterialDesignIcon icon-name="trash-can-outline" class="size-4" />
                    </button>
                    <button
                        type="button"
                        class="flex size-6 items-center justify-center rounded text-sem-fg-muted transition-colors hover:bg-sem-surface hover:text-sem-fg"
                        :disabled="index === 0"
                        :class="{ 'opacity-40': index === 0 }"
                        :title="$t('messages.filter_move_up')"
                        @click="moveRow(index, -1)"
                    >
                        <MaterialDesignIcon icon-name="chevron-up" class="size-4" />
                    </button>
                    <button
                        type="button"
                        class="flex size-6 items-center justify-center rounded text-sem-fg-muted transition-colors hover:bg-sem-surface hover:text-sem-fg"
                        :disabled="index === working.length - 1"
                        :class="{ 'opacity-40': index === working.length - 1 }"
                        :title="$t('messages.filter_move_down')"
                        @click="moveRow(index, 1)"
                    >
                        <MaterialDesignIcon icon-name="chevron-down" class="size-4" />
                    </button>
                    <button
                        type="button"
                        role="switch"
                        :aria-checked="row.shown"
                        class="relative h-5 w-9 shrink-0 rounded-full transition-colors"
                        :class="row.shown ? 'bg-sem-action-primary' : 'bg-sem-surface-muted border border-sem-border'"
                        :title="$t(row.shown ? 'messages.filter_shown_in_bar' : 'messages.filter_hidden_in_bar')"
                        @click="row.shown = !row.shown"
                    >
                        <span
                            class="absolute top-0.5 size-4 rounded-full shadow ring-1 ring-sem-border transition-all"
                            :class="row.shown ? 'bg-sem-action-primary-text' : 'bg-sem-fg-muted'"
                            :style="row.shown ? 'inset-inline-start: 1.1rem' : 'inset-inline-start: 0.2rem'"
                        ></span>
                    </button>
                </div>

                <div class="mt-4 border-t border-sem-border pt-3">
                    <div class="px-2 text-xs font-semibold uppercase tracking-wide text-sem-fg-muted">
                        {{ $t("messages.filters_custom_title") }}
                    </div>
                    <div class="px-2 pt-1 text-xs text-sem-fg-muted">
                        {{ $t("messages.filters_custom_hint") }}
                    </div>
                    <div class="mt-2 space-y-2 px-2">
                        <input
                            v-model="customName"
                            type="text"
                            maxlength="40"
                            :placeholder="$t('messages.filters_custom_name')"
                            class="input-field w-full px-3 py-1.5 text-sm"
                        />
                        <input
                            v-model="customQuery"
                            type="text"
                            maxlength="200"
                            :placeholder="$t('messages.filters_custom_query')"
                            class="input-field w-full px-3 py-1.5 text-sm"
                            @keydown.enter.prevent="addCustom"
                        />
                        <button
                            type="button"
                            class="flex w-full items-center justify-center gap-1 rounded-lg border border-dashed border-sem-border px-3 py-1.5 text-sm text-sem-fg-muted transition-colors hover:border-sem-accent hover:text-sem-accent"
                            :disabled="!canAddCustom"
                            :class="{ 'opacity-40': !canAddCustom }"
                            @click="addCustom"
                        >
                            <MaterialDesignIcon icon-name="plus" class="size-4" />
                            {{ $t("messages.filters_custom_add") }}
                        </button>
                    </div>
                </div>
            </div>
            <div class="flex items-center justify-end gap-2 border-t border-sem-border px-5 py-3">
                <button
                    type="button"
                    class="rounded-lg px-3 py-1.5 text-sm font-medium text-sem-fg-muted transition-colors hover:bg-sem-surface-muted hover:text-sem-fg"
                    @click="onCancel"
                >
                    {{ $t("common.cancel") }}
                </button>
                <button
                    type="button"
                    class="rounded-lg bg-sem-action-primary px-3 py-1.5 text-sm font-medium text-sem-action-primary-text transition-colors"
                    @click="onDone"
                >
                    {{ $t("common.done") }}
                </button>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";
import { isCustomFilterId, makeCustomFilter } from "../../../js/messages/sidebarFilters.js";

export default {
    name: "SidebarFilterEditModal",
    components: {
        MaterialDesignIcon,
    },
    props: {
        show: {
            type: Boolean,
            default: false,
        },
        context: {
            type: String,
            required: true,
        },
        layout: {
            type: Object,
            required: true,
        },
        defs: {
            type: Array,
            required: true,
        },
    },
    emits: ["close", "save"],
    data() {
        return {
            working: [],
            customDefs: [],
            customName: "",
            customQuery: "",
            dragIndex: null,
            dropIndex: null,
        };
    },
    computed: {
        defMap() {
            return new Map([...this.defs, ...this.customDefs].map((d) => [d.id, d]));
        },
        canAddCustom() {
            return this.customName.trim().length > 0 && this.customQuery.trim().length > 0;
        },
    },
    watch: {
        show(visible) {
            if (visible) {
                this.rebuild();
            }
        },
    },
    methods: {
        defFor(id) {
            return this.defMap.get(id) || { id, labelKey: "", label: "", icon: "filter-variant" };
        },
        rowLabel(id) {
            const def = this.defFor(id);
            return def.label || (def.labelKey ? this.$t(def.labelKey) : id);
        },
        isCustomId(id) {
            return isCustomFilterId(id);
        },
        addCustom() {
            if (!this.canAddCustom) {
                return;
            }
            const def = makeCustomFilter(this.customName, this.customQuery);
            this.customDefs = [...this.customDefs, def];
            this.working.push({ id: def.id, shown: true });
            this.customName = "";
            this.customQuery = "";
        },
        removeCustom(index) {
            const [row] = this.working.splice(index, 1);
            this.customDefs = this.customDefs.filter((d) => d.id !== row.id);
        },
        rebuild() {
            const shownOrder = this.layout[this.context] || [];
            const shownSet = new Set(shownOrder);
            const customDefs = (this.layout.custom?.[this.context] || []).map((d) => ({ ...d }));
            const defMap = new Map([...this.defs, ...customDefs].map((d) => [d.id, d]));
            const rows = shownOrder.filter((id) => defMap.has(id)).map((id) => ({ id, shown: true }));
            for (const def of [...this.defs, ...customDefs]) {
                if (!shownSet.has(def.id)) {
                    rows.push({ id: def.id, shown: false });
                }
            }
            this.working = rows;
            this.customDefs = customDefs;
            this.customName = "";
            this.customQuery = "";
            this.dragIndex = null;
            this.dropIndex = null;
        },
        onRowDragStart(event, index) {
            this.dragIndex = index;
            event.dataTransfer.effectAllowed = "move";
            event.dataTransfer.setData("text/plain", `mcx-sidebar-filter-row:${index}`);
        },
        onRowDragOver(index) {
            if (this.dragIndex === null || this.dragIndex === index) {
                return;
            }
            this.dropIndex = index;
        },
        onRowDragLeave(index) {
            if (this.dropIndex === index) {
                this.dropIndex = null;
            }
        },
        onRowDrop(index) {
            if (this.dragIndex === null || this.dragIndex === index) {
                return;
            }
            const [row] = this.working.splice(this.dragIndex, 1);
            this.working.splice(index, 0, row);
            this.dragIndex = null;
            this.dropIndex = null;
        },
        onRowDragEnd() {
            this.dragIndex = null;
            this.dropIndex = null;
        },
        moveRow(index, delta) {
            const target = index + delta;
            if (target < 0 || target >= this.working.length) {
                return;
            }
            const [row] = this.working.splice(index, 1);
            this.working.splice(target, 0, row);
        },
        onCancel() {
            this.rebuild();
            this.$emit("close");
        },
        onDone() {
            this.$emit(
                "save",
                this.working.filter((r) => r.shown).map((r) => r.id),
                this.customDefs
            );
        },
    },
};
</script>
