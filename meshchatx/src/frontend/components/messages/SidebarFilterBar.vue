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
            :title="def.label || $t(def.labelKey)"
            @click="$emit('toggle', def.id)"
            @dragstart="onChipDragStart($event, def.id)"
            @dragover.prevent="onChipDragOver(def.id)"
            @dragleave="onChipDragLeave(def.id)"
            @drop.prevent="onChipDrop(def.id)"
            @dragend="onChipDragEnd"
        >
            <MaterialDesignIcon :icon-name="def.icon" class="size-3.5 -translate-y-px" />
            <span>{{ def.label || $t(def.labelKey) }}</span>
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
        <button
            ref="menuButton"
            type="button"
            class="relative p-1 text-sem-fg-muted transition-colors hover:text-sem-accent"
            :title="$t('messages.more_filters')"
            @click="toggleMenu"
        >
            <MaterialDesignIcon icon-name="filter-variant" class="size-5" />
            <span
                v-if="hiddenActiveCount > 0"
                class="absolute -right-0.5 -top-0.5 flex size-3.5 items-center justify-center rounded-full bg-sem-action-primary text-[9px] font-bold text-sem-action-primary-text"
                >{{ hiddenActiveCount }}</span
            >
        </button>
        <Teleport to="body">
            <div
                v-if="menu.show"
                v-click-outside="{ handler: onOutsideClick, capture: true }"
                class="fixed z-300 animate-in fade-in zoom-in duration-100"
                :style="menuStyle"
                @click.stop
            >
                <div
                    class="dropdown-caret pointer-events-none absolute -top-[4px] right-3 border-l border-t border-sem-border"
                    aria-hidden="true"
                ></div>
                <div class="dropdown-panel min-w-[180px] rounded-xl py-1 shadow-xl">
                    <button
                        v-for="def in defs"
                        :key="def.id"
                        type="button"
                        class="flex w-full items-center gap-2 px-3 py-2 text-sm transition-colors hover:bg-sem-surface-muted"
                        :class="activeSet.has(def.id) ? 'text-sem-accent' : 'text-sem-fg-muted'"
                        @click="$emit('toggle', def.id)"
                    >
                        <MaterialDesignIcon :icon-name="def.icon" class="size-4" />
                        <span class="flex-1 truncate text-left">{{ def.label || $t(def.labelKey) }}</span>
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
                            closeMenu();
                            editModal.show = true;
                        "
                    >
                        <MaterialDesignIcon icon-name="pencil-outline" class="size-4" />
                        <span class="flex-1 text-left">{{ $t("messages.filters_edit") }}</span>
                    </button>
                </div>
            </div>
        </Teleport>
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
    resolveSidebarFilterDefs,
    saveSidebarFilterLayout,
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
    emits: ["toggle", "layout-changed", "defs-changed"],
    data() {
        return {
            layout: loadSidebarFilterLayout(),
            draggingId: null,
            dropTargetId: null,
            menu: { show: false, top: 0, right: 0 },
            editModal: { show: false },
        };
    },
    computed: {
        defs() {
            return resolveSidebarFilterDefs(this.context, this.layout);
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
        menuStyle() {
            return {
                top: `${this.menu.top}px`,
                right: `${this.menu.right}px`,
            };
        },
    },
    methods: {
        toggleMenu() {
            if (this.menu.show) {
                this.menu.show = false;
                return;
            }
            // Fixed positioning escapes every ancestor stacking context and
            // overflow clip, so the menu always renders above the sidebar.
            const rect = this.$refs.menuButton.getBoundingClientRect();
            this.menu.top = Math.round(rect.bottom + 4);
            this.menu.right = Math.max(4, Math.round(window.innerWidth - rect.right));
            this.menu.show = true;
        },
        closeMenu() {
            this.menu.show = false;
        },
        onOutsideClick(event) {
            // Trigger clicks are "outside" the teleported panel, so skip them
            // here and let the button toggle do its close-then-reopen dance.
            if (this.$refs.menuButton?.contains(event.target)) {
                return;
            }
            this.menu.show = false;
        },
        onLayoutSave(order, customDefs) {
            const next = {
                ...this.layout,
                [this.context]: order,
                custom: { ...(this.layout.custom || {}), [this.context]: customDefs || [] },
            };
            saveSidebarFilterLayout(next);
            this.layout = next;
            this.editModal.show = false;
            this.$emit("layout-changed", order);
            this.$emit("defs-changed", this.defs);
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
