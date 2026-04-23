<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        v-if="show"
        ref="panel"
        class="context-menu-panel"
        :class="panelClass"
        :style="panelStyle"
        v-bind="$attrs"
    >
        <slot name="header" />
        <slot />
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
                    return;
                }
                this.adjustedLeft = this.x;
                this.adjustedTop = this.y;
                this.panelMaxHeight = null;
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
        },
    },
};
</script>
