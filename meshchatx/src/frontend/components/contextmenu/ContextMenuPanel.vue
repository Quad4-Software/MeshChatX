<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <!-- Single element root: directives like v-click-outside are ignored on
         fragment roots. display:contents keeps this wrapper box-free so fixed
         positioning and layout are unchanged. -->
    <div class="contents">
        <div v-if="show" ref="panel" class="context-menu-panel" :class="panelClass" :style="panelStyle" v-bind="$attrs">
            <slot name="header" />
            <slot />
        </div>
        <div
            v-if="show && caretStyle"
            class="dropdown-caret fixed z-300 border-sem-border"
            :class="caretBorderClass"
            :style="caretStyle"
            aria-hidden="true"
        ></div>
    </div>
</template>

<script setup lang="ts">
import { computed, getCurrentInstance, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { clampFloatingToViewport } from "../../js/clampFloatingToViewport.js";
import { HANDLERS_PROPERTY } from "../../libs/clickOutside.js";

defineOptions({ name: "ContextMenuPanel", inheritAttrs: false });

const props = withDefaults(
    defineProps<{
        show: boolean;
        x: number;
        y: number;
        panelClass?: string;
    }>(),
    {
        panelClass: "",
    }
);

const instance = getCurrentInstance();

const adjustedLeft = ref(0);
const adjustedTop = ref(0);
const panelMaxHeight = ref<number | null>(null);
const caretStyle = ref<Record<string, string> | null>(null);
const caretBorderClass = ref("border-t border-l");

let repositionRaf: number | null = null;

const panel = ref<HTMLElement | null>(null);

const panelStyle = computed(() => {
    const style: Record<string, string> = {
        top: `${adjustedTop.value}px`,
        left: `${adjustedLeft.value}px`,
    };
    if (panelMaxHeight.value != null) {
        style.maxHeight = `${panelMaxHeight.value}px`;
        style.overflowY = "auto";
    }
    return style;
});

watch(
    () => props.show,
    (visible) => {
        cancelReposition();
        if (!visible) {
            panelMaxHeight.value = null;
            caretStyle.value = null;
            return;
        }
        adjustedLeft.value = props.x;
        adjustedTop.value = props.y;
        panelMaxHeight.value = null;
        caretStyle.value = null;
        scheduleReposition();
    },
    { immediate: true }
);

watch(
    () => props.x,
    () => {
        if (props.show) {
            scheduleReposition();
        }
    }
);

watch(
    () => props.y,
    () => {
        if (props.show) {
            scheduleReposition();
        }
    }
);

onMounted(() => {
    window.addEventListener("resize", onWindowResize);
    window.addEventListener("keydown", onPanelKeydown, true);
});

onBeforeUnmount(() => {
    window.removeEventListener("resize", onWindowResize);
    window.removeEventListener("keydown", onPanelKeydown, true);
    cancelReposition();
});

function menuItems(): HTMLElement[] {
    const el = panel.value;
    if (!el) {
        return [];
    }
    return Array.from(el.querySelectorAll<HTMLElement>(".context-item:not(:disabled)"));
}

function focusMenuItem(offset: number) {
    const items = menuItems();
    if (items.length === 0) {
        return;
    }
    const active = document.activeElement as HTMLElement;
    const idx = items.indexOf(active);
    const next = idx < 0 ? (offset > 0 ? 0 : items.length - 1) : (idx + offset + items.length) % items.length;
    items[next].focus();
}

function onPanelKeydown(event: KeyboardEvent) {
    if (!props.show) {
        return;
    }
    if (event.key === "Escape" || event.key === "Tab") {
        // Route the dismissal through the parent v-click-outside
        // handler stored on this component's root element so every
        // consumer closes without per-menu wiring. Each entry is the
        // same handler bound per event name, so firing one is enough.
        event.preventDefault();
        event.stopPropagation();
        const entries = ((instance?.proxy as any)?.$el?.[HANDLERS_PROPERTY] || []) as any[];
        const entry = entries.find((e) => e.event === "click" || e.event === "contextmenu" || e.event === "touchstart");
        entry?.handler({ target: document.documentElement });
        return;
    }
    if (event.key === "ArrowDown") {
        event.preventDefault();
        focusMenuItem(1);
    } else if (event.key === "ArrowUp") {
        event.preventDefault();
        focusMenuItem(-1);
    } else if (event.key === "Home") {
        event.preventDefault();
        menuItems()[0]?.focus();
    } else if (event.key === "End") {
        event.preventDefault();
        menuItems().at(-1)?.focus();
    }
}

function onWindowResize() {
    if (props.show) {
        repositionToViewport();
    }
}

function cancelReposition() {
    if (repositionRaf != null) {
        cancelAnimationFrame(repositionRaf);
        repositionRaf = null;
    }
}

function scheduleReposition() {
    cancelReposition();
    repositionRaf = requestAnimationFrame(() => {
        repositionRaf = null;
        nextTick(() => repositionToViewport());
    });
}

function repositionToViewport() {
    const el = panel.value;
    if (!el || !props.show) {
        return;
    }
    const rect = el.getBoundingClientRect();
    const { left, top, maxHeight } = clampFloatingToViewport(props.x, props.y, rect.width, rect.height);
    adjustedLeft.value = left;
    adjustedTop.value = top;
    panelMaxHeight.value = maxHeight;
    updateCaret(left, top, rect.width, rect.height);
}

function updateCaret(left: number, top: number, width: number, height: number) {
    const ox = props.x;
    const oy = props.y;
    // An anchor inside or on the panel edge has nothing to point at.
    const insideX = ox >= left && ox <= left + width;
    const insideY = oy >= top && oy <= top + height;
    if (insideX && insideY) {
        caretStyle.value = null;
        return;
    }
    const size = 5;
    // Keep the caret on the straight part of the edge: rounded-xl
    // corners span 12px and the caret is 10px wide.
    const margin = 18;
    if (oy <= top) {
        const cx = Math.min(Math.max(ox, left + margin), left + width - margin);
        caretStyle.value = { left: `${cx - size}px`, top: `${top - size}px` };
        caretBorderClass.value = "border-t border-l";
    } else if (oy >= top + height) {
        const cx = Math.min(Math.max(ox, left + margin), left + width - margin);
        caretStyle.value = { left: `${cx - size}px`, top: `${top + height - size}px` };
        caretBorderClass.value = "border-b border-r";
    } else if (ox <= left) {
        const cy = Math.min(Math.max(oy, top + margin), top + height - margin);
        caretStyle.value = { left: `${left - size}px`, top: `${cy - size}px` };
        caretBorderClass.value = "border-b border-l";
    } else {
        const cy = Math.min(Math.max(oy, top + margin), top + height - margin);
        caretStyle.value = { left: `${left + width - size}px`, top: `${cy - size}px` };
        caretBorderClass.value = "border-t border-r";
    }
}
</script>
