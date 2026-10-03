<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="flex flex-wrap items-center gap-1">
        <slot name="leading" />
        <button
            v-for="def in visibleDefs"
            :key="def.id"
            type="button"
            :class="[
                'inline-flex cursor-pointer select-none items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium transition-colors',
                activeSet.has(def.id)
                    ? 'bg-sem-action-primary text-sem-action-primary-text'
                    : 'bg-sem-surface-muted text-sem-fg',
                dropTargetId === def.id ? 'ring-1 ring-sem-accent' : '',
                draggingId === def.id ? 'opacity-50' : '',
            ]"
            draggable="true"
            :title="$t(def.labelKey)"
            @click="$emit('toggle', def.id)"
            @dragstart="onChipDragStart($event, def.id)"
            @dragover.prevent="onChipDragOver(def.id)"
            @dragleave="onChipDragLeave(def.id)"
            @drop.prevent="onChipDrop(def.id)"
            @dragend="onChipDragEnd"
        >
            <MaterialDesignIcon :icon-name="def.icon" class="size-3.5" />
            <span>{{ $t(def.labelKey) }}</span>
        </button>
        <button
            type="button"
            :class="[
                'inline-flex cursor-pointer select-none items-center gap-0.5 rounded-full px-1.5 py-0.5 text-xs transition-colors',
                'border border-dashed border-sem-border text-sem-fg-muted hover:border-sem-accent hover:text-sem-accent',
                dropTargetId === '__end__' ? 'ring-1 ring-sem-accent' : '',
            ]"
            :title="$t('messages.filters_add_chip')"
            @click="editModal.show = true"
            @drop.prevent="onChipDrop('__end__')"
            @dragover.prevent="onChipDragOver('__end__')"
            @dragleave="onChipDragLeave('__end__')"
        >
            <MaterialDesignIcon icon-name="plus" class="size-3.5" />
        </button>
        <div class="relative" @click.stop>
            <button
                type="button"
                class="relative p-1 text-sem-fg-muted transition-colors hover:text-sem-accent"
                :title="$t('messages.more_filters')"
                @click="menu.show = !menu.show"
            >
                <MaterialDesignIcon icon-name="filter-variant" class="size-5" />
                <span
                    v-if="hiddenActiveCount > 0"
                    class="absolute -right-0.5 -top-0.5 flex size-3.5 items-center justify-center rounded-full bg-sem-action-primary text-[9px] font-bold text-sem-action-primary-text"
                    >{{ hiddenActiveCount }}</span
                >
            </button>
            <div
                v-if="menu.show"
                v-click-outside="{ handler: () => (menu.show = false), capture: true }"
                class="absolute right-0 top-full z-60 mt-1 animate-in fade-in zoom-in duration-100"
            >
                <div
                    class="dropdown-caret pointer-events-none absolute -top-[4px] right-3 border-l border-t border-sem-border"
                    aria-hidden="true"
                ></div>
                <div
                    class="min-w-[180px] overflow-hidden rounded-xl border border-sem-border bg-sem-surface py-1 shadow-xl"
                >
                    <button
                        v-for="def in defs"
                        :key="def.id"
                        type="button"
                        class="flex w-full items-center gap-2 px-3 py-2 text-sm transition-colors hover:bg-sem-surface-muted"
                        :class="activeSet.has(def.id) ? 'text-sem-accent' : 'text-sem-fg-muted'"
                        @click="$emit('toggle', def.id)"
                    >
                        <MaterialDesignIcon :icon-name="def.icon" class="size-4" />
                        <span class="flex-1 truncate text-left">{{ $t(def.labelKey) }}</span>
                        <MaterialDesignIcon
                            v-if="activeSet.has(def.id)"
                            icon-name="check"
                            class="size-4 text-sem-accent"
                        />
                    </button>
                    <div class="my-1 border-t border-sem-border"></div>
                    <button
                        type="button"
                        class="flex w-full items-center gap-2 px-3 py-2 text-sm text-sem-fg-muted transition-colors hover:bg-sem-surface-muted"
                        @click="
                            menu.show = false;
                            editModal.show = true;
                        "
                    >
                        <MaterialDesignIcon icon-name="pencil-outline" class="size-4" />
                        <span class="flex-1 text-left">{{ $t("messages.filters_edit") }}</span>
                    </button>
                </div>
            </div>
        </div>
        <SidebarFilterEditModal
            :show="editModal.show"
            :context="context"
            :layout="layout"
            @close="editModal.show = false"
            @save="onLayoutSave"
        />
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import SidebarFilterEditModal from "./modals/SidebarFilterEditModal.vue";
import {
    loadSidebarFilterLayout,
    moveSidebarFilter,
    saveSidebarFilterLayout,
    sidebarFilterDefs,
} from "../../js/messages/sidebarFilters.js";

export default {
    name: "SidebarFilterBar",
    components: {
        MaterialDesignIcon,
        SidebarFilterEditModal,
    },
    props: {
        context: {
            type: String,
            required: true,
        },
        active: {
            type: Array,
            default: () => [],
        },
    },
    emits: ["toggle", "layout-changed"],
    data() {
        return {
            layout: loadSidebarFilterLayout(),
            draggingId: null,
            dropTargetId: null,
            menu: { show: false },
            editModal: { show: false },
        };
    },
    computed: {
        defs() {
            return sidebarFilterDefs(this.context);
        },
        defMap() {
            return new Map(this.defs.map((d) => [d.id, d]));
        },
        visibleDefs() {
            return (this.layout[this.context] || []).map((id) => this.defMap.get(id)).filter(Boolean);
        },
        activeSet() {
            return new Set(this.active);
        },
        hiddenActiveCount() {
            const visible = new Set(this.layout[this.context] || []);
            return this.active.filter((id) => !visible.has(id)).length;
        },
    },
    methods: {
        onLayoutSave(order) {
            const next = { ...this.layout, [this.context]: order };
            saveSidebarFilterLayout(next);
            this.layout = next;
            this.editModal.show = false;
            this.$emit("layout-changed", order);
        },
        onChipDragStart(event, id) {
            this.draggingId = id;
            event.dataTransfer.effectAllowed = "move";
            event.dataTransfer.setData("text/plain", `mcx-sidebar-filter:${id}`);
        },
        onChipDragOver(id) {
            if (!this.draggingId || this.draggingId === id) {
                return;
            }
            this.dropTargetId = id;
        },
        onChipDragLeave(id) {
            if (this.dropTargetId === id) {
                this.dropTargetId = null;
            }
        },
        onChipDrop(id) {
            if (!this.draggingId || this.draggingId === id) {
                return;
            }
            const target = id === "__end__" ? null : id;
            this.layout = moveSidebarFilter(this.layout, this.context, this.draggingId, target);
            this.$emit("layout-changed", this.layout[this.context]);
            this.dropTargetId = null;
        },
        onChipDragEnd() {
            this.draggingId = null;
            this.dropTargetId = null;
        },
    },
};
</script>
