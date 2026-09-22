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

<script>
import { clampFloatingToViewport } from "../../js/clampFloatingToViewport.js";

export default {
    name: "ContextMenuPanel",
    inheritAttrs: false,
    props: {
        show: {
            type: Boolean,
            required: true,
        },
        x: {
            type: Number,
            required: true,
        },
        y: {
            type: Number,
            required: true,
        },
        panelClass: {
            type: String,
            default: "",
        },
    },
    data() {
        return {
            adjustedLeft: 0,
            adjustedTop: 0,
            panelMaxHeight: null,
            repositionRaf: null,
            caretStyle: null,
            caretBorderClass: "border-t border-l",
        };
    },
    computed: {
        panelStyle() {
            const style = {
                top: `${this.adjustedTop}px`,
                left: `${this.adjustedLeft}px`,
            };
            if (this.panelMaxHeight != null) {
                style.maxHeight = `${this.panelMaxHeight}px`;
                style.overflowY = "auto";
            }
            return style;
        },
    },
    watch: {
        show: {
            immediate: true,
            handler(visible) {
                this.cancelReposition();
                if (!visible) {
                    this.panelMaxHeight = null;
                    this.caretStyle = null;
                    return;
                }
                this.adjustedLeft = this.x;
                this.adjustedTop = this.y;
                this.panelMaxHeight = null;
                this.caretStyle = null;
                this.scheduleReposition();
            },
        },
        x() {
            if (this.show) {
                this.scheduleReposition();
            }
        },
        y() {
            if (this.show) {
                this.scheduleReposition();
            }
        },
    },
    mounted() {
        window.addEventListener("resize", this.onWindowResize);
    },
    beforeUnmount() {
        window.removeEventListener("resize", this.onWindowResize);
        this.cancelReposition();
    },
    methods: {
        onWindowResize() {
            if (this.show) {
                this.repositionToViewport();
            }
        },
        cancelReposition() {
            if (this.repositionRaf != null) {
                cancelAnimationFrame(this.repositionRaf);
                this.repositionRaf = null;
            }
        },
        scheduleReposition() {
            this.cancelReposition();
            this.repositionRaf = requestAnimationFrame(() => {
                this.repositionRaf = null;
                this.$nextTick(() => this.repositionToViewport());
            });
        },
        repositionToViewport() {
            const el = this.$refs.panel;
            if (!el || !this.show) {
                return;
            }
            const rect = el.getBoundingClientRect();
            const { left, top, maxHeight } = clampFloatingToViewport(this.x, this.y, rect.width, rect.height);
            this.adjustedLeft = left;
            this.adjustedTop = top;
            this.panelMaxHeight = maxHeight;
            this.updateCaret(left, top, rect.width, rect.height);
        },
        updateCaret(left, top, width, height) {
            const ox = this.x;
            const oy = this.y;
            // An anchor inside or on the panel edge has nothing to point at.
            const insideX = ox >= left && ox <= left + width;
            const insideY = oy >= top && oy <= top + height;
            if (insideX && insideY) {
                this.caretStyle = null;
                return;
            }
            const size = 5;
            // Keep the caret on the straight part of the edge: rounded-xl
            // corners span 12px and the caret is 10px wide.
            const margin = 18;
            if (oy <= top) {
                const cx = Math.min(Math.max(ox, left + margin), left + width - margin);
                this.caretStyle = { left: `${cx - size}px`, top: `${top - size}px` };
                this.caretBorderClass = "border-t border-l";
            } else if (oy >= top + height) {
                const cx = Math.min(Math.max(ox, left + margin), left + width - margin);
                this.caretStyle = { left: `${cx - size}px`, top: `${top + height - size}px` };
                this.caretBorderClass = "border-b border-r";
            } else if (ox <= left) {
                const cy = Math.min(Math.max(oy, top + margin), top + height - margin);
                this.caretStyle = { left: `${left - size}px`, top: `${cy - size}px` };
                this.caretBorderClass = "border-b border-l";
            } else {
                const cy = Math.min(Math.max(oy, top + margin), top + height - margin);
                this.caretStyle = { left: `${left + width - size}px`, top: `${cy - size}px` };
                this.caretBorderClass = "border-t border-r";
            }
        },
    },
};
</script>
