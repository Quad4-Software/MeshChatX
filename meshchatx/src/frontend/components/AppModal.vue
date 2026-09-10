<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <Teleport to="body">
        <div
            v-if="modelValue"
            ref="dialog"
            class="fixed inset-0 z-[200] flex items-center justify-center p-4 pt-[max(0.75rem,env(safe-area-inset-top))] pb-[max(0.75rem,env(safe-area-inset-bottom))] bg-black/50 backdrop-blur-xs"
            @click.self="onBackdropClick"
        >
            <div
                class="modal-panel flex w-full flex-col"
                :class="panelClass"
                :style="panelStyle"
                role="dialog"
                aria-modal="true"
            >
                <div v-if="$slots.header || title" class="modal-panel__header">
                    <slot name="header">
                        <h2 v-if="title" class="min-w-0 flex-1 text-lg font-semibold text-sem-fg">
                            {{ title }}
                        </h2>
                    </slot>
                    <button
                        v-if="showClose"
                        type="button"
                        class="icon-btn-muted shrink-0 rounded-lg p-2"
                        :aria-label="$t('common.close')"
                        @click="close"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-5" />
                    </button>
                </div>
                <div class="min-h-0 flex-1" :class="bodyClass">
                    <slot />
                </div>
                <div v-if="$slots.actions" class="modal-panel__footer">
                    <slot name="actions" />
                </div>
            </div>
        </div>
    </Teleport>
</template>

<script>
import MaterialDesignIcon from "./MaterialDesignIcon.vue";

export default {
    name: "AppModal",
    components: {
        MaterialDesignIcon,
    },
    props: {
        modelValue: {
            type: Boolean,
            default: false,
        },
        title: {
            type: String,
            default: "",
        },
        persistent: {
            type: Boolean,
            default: false,
        },
        maxWidth: {
            type: [Number, String],
            default: 520,
        },
        fullscreen: {
            type: Boolean,
            default: false,
        },
        scrollable: {
            type: Boolean,
            default: true,
        },
        showClose: {
            type: Boolean,
            default: false,
        },
        panelClass: {
            type: String,
            default: "",
        },
        bodyClass: {
            type: String,
            default: "overflow-y-auto overscroll-contain",
        },
    },
    emits: ["update:modelValue", "close"],
    data() {
        return {
            previouslyFocused: null,
            focusTrapHandler: null,
        };
    },
    computed: {
        panelStyle() {
            if (this.fullscreen) {
                return { maxHeight: "100dvh", height: "100dvh", maxWidth: "100vw", width: "100vw" };
            }
            const raw = this.maxWidth;
            const px = typeof raw === "number" ? `${raw}px` : String(raw);
            return {
                maxWidth: px.includes("px") || px.includes("rem") || px.includes("%") ? px : `${px}px`,
                maxHeight: "min(90dvh, 100%)",
            };
        },
    },
    watch: {
        modelValue: {
            immediate: true,
            handler(newVal) {
                if (newVal) {
                    this.previouslyFocused = document.activeElement;
                    this.$nextTick(() => {
                        this.attachFocusTrap();
                        this.focusFirst();
                    });
                } else {
                    this.detachFocusTrap();
                    if (this.previouslyFocused && typeof this.previouslyFocused.focus === "function") {
                        this.previouslyFocused.focus();
                    }
                }
            },
        },
    },
    methods: {
        close() {
            this.$emit("update:modelValue", false);
            this.$emit("close");
        },
        onBackdropClick() {
            if (!this.persistent) {
                this.close();
            }
        },
        getFocusableElements() {
            const root = this.$refs.dialog;
            if (!root) {
                return [];
            }
            const selector =
                'button:not([disabled]), [href]:not([tabindex="-1"]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
            return Array.from(root.querySelectorAll(selector)).filter(
                (el) => !el.disabled && el.getAttribute("aria-hidden") !== "true" && el.getAttribute("hidden") === null
            );
        },
        focusFirst() {
            const focusable = this.getFocusableElements();
            if (focusable.length > 0) {
                focusable[0].focus();
            }
        },
        handleFocusTrap(e) {
            if (e.key !== "Tab") return;
            const focusable = this.getFocusableElements();
            if (focusable.length === 0) return;
            const first = focusable[0];
            const last = focusable[focusable.length - 1];
            if (e.shiftKey && document.activeElement === first) {
                e.preventDefault();
                last.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
                e.preventDefault();
                first.focus();
            }
        },
        attachFocusTrap() {
            this.detachFocusTrap();
            this.focusTrapHandler = (e) => this.handleFocusTrap(e);
            if (this.$refs.dialog) {
                this.$refs.dialog.addEventListener("keydown", this.focusTrapHandler, true);
            }
        },
        detachFocusTrap() {
            if (this.focusTrapHandler && this.$refs.dialog) {
                this.$refs.dialog.removeEventListener("keydown", this.focusTrapHandler, true);
            }
            this.focusTrapHandler = null;
        },
    },
};
</script>
