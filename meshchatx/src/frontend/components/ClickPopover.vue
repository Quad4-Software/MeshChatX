<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div ref="rootRef" class="relative inline-flex">
        <div
            ref="activatorRef"
            class="inline-flex"
            tabindex="0"
            role="button"
            @click="toggle"
            @keydown.enter.prevent="toggle"
            @keydown.space.prevent="toggle"
        >
            <slot name="activator" />
        </div>
        <Teleport to="body">
            <div
                v-if="open"
                ref="panelRef"
                class="fixed z-[250] max-w-[min(20rem,85vw)]"
                :style="panelStyle"
                @click.stop
            >
                <slot />
            </div>
        </Teleport>
    </div>
</template>

<script>
export default {
    name: "ClickPopover",
    props: {
        modelValue: {
            type: Boolean,
            default: false,
        },
        placement: {
            type: String,
            default: "bottom",
        },
    },
    emits: ["update:modelValue"],
    data() {
        return {
            open: this.modelValue,
            panelStyle: {},
            onDocClick: null,
            onDocKeydown: null,
        };
    },
    watch: {
        modelValue(value) {
            this.open = value;
            if (value) {
                this.$nextTick(() => this.positionPanel());
            }
        },
        open(value) {
            this.$emit("update:modelValue", value);
        },
    },
    mounted() {
        this.onDocClick = (event) => {
            if (!this.open) {
                return;
            }
            const root = this.$refs.rootRef;
            const panel = this.$refs.panelRef;
            if (root?.contains(event.target) || panel?.contains(event.target)) {
                return;
            }
            this.open = false;
        };
        this.onDocKeydown = (event) => {
            if (event.key === "Escape" && this.open) {
                this.open = false;
            }
        };
        document.addEventListener("click", this.onDocClick, true);
        document.addEventListener("keydown", this.onDocKeydown);
    },
    beforeUnmount() {
        document.removeEventListener("click", this.onDocClick, true);
        document.removeEventListener("keydown", this.onDocKeydown);
    },
    methods: {
        toggle() {
            this.open = !this.open;
            if (this.open) {
                this.$nextTick(() => this.positionPanel());
            }
        },
        positionPanel() {
            const activator = this.$refs.activatorRef;
            if (!activator || typeof activator.getBoundingClientRect !== "function") {
                return;
            }
            const rect = activator.getBoundingClientRect();
            const gap = 6;
            if (this.placement === "bottom") {
                this.panelStyle = {
                    top: `${rect.bottom + gap}px`,
                    left: `${rect.left}px`,
                };
                return;
            }
            this.panelStyle = {
                top: `${rect.bottom + gap}px`,
                left: `${rect.left}px`,
            };
        },
    },
};
</script>
