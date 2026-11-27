<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <Teleport to="body">
        <div
            v-if="modelValue"
            ref="dialog"
            class="fixed inset-0 z-[200] flex items-center justify-center bg-black/50 backdrop-blur-xs"
            :class="
                fullscreen
                    ? 'p-0 pt-[env(safe-area-inset-top)] pr-[env(safe-area-inset-right)] pb-[env(safe-area-inset-bottom)] pl-[env(safe-area-inset-left)]'
                    : 'p-4 pt-[max(0.75rem,env(safe-area-inset-top))] pb-[max(0.75rem,env(safe-area-inset-bottom))]'
            "
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

<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import MaterialDesignIcon from "./MaterialDesignIcon.vue";

defineOptions({ name: "AppModal" });

const props = withDefaults(
    defineProps<{
        modelValue?: boolean;
        title?: string;
        persistent?: boolean;
        maxWidth?: number | string;
        fullscreen?: boolean;
        scrollable?: boolean;
        showClose?: boolean;
        panelClass?: string;
        bodyClass?: string;
    }>(),
    {
        modelValue: false,
        title: "",
        persistent: false,
        maxWidth: 520,
        fullscreen: false,
        scrollable: true,
        showClose: false,
        panelClass: "",
        bodyClass: "overflow-y-auto overscroll-contain",
    }
);

const emit = defineEmits<{
    "update:modelValue": [value: boolean];
    close: [];
}>();

let previouslyFocused: Element | null = null;
let focusTrapHandler: ((e: KeyboardEvent) => void) | null = null;

const dialog = ref<HTMLElement | null>(null);

const panelStyle = computed(() => {
    if (props.fullscreen) {
        return { maxHeight: "100%", height: "100%", maxWidth: "100%", width: "100%" };
    }
    const raw = props.maxWidth;
    const px = typeof raw === "number" ? `${raw}px` : String(raw);
    return {
        maxWidth: px.includes("px") || px.includes("rem") || px.includes("%") ? px : `${px}px`,
        maxHeight: "min(90dvh, 100%)",
    };
});

watch(
    () => props.modelValue,
    (newVal) => {
        if (newVal) {
            previouslyFocused = document.activeElement;
            nextTick(() => {
                attachFocusTrap();
                focusFirst();
            });
        } else {
            detachFocusTrap();
            if (previouslyFocused && typeof (previouslyFocused as HTMLElement).focus === "function") {
                (previouslyFocused as HTMLElement).focus();
            }
        }
    },
    { immediate: true }
);

function close() {
    emit("update:modelValue", false);
    emit("close");
}

function onBackdropClick() {
    if (!props.persistent) {
        close();
    }
}

function getFocusableElements(): HTMLElement[] {
    const root = dialog.value;
    if (!root) {
        return [];
    }
    const selector =
        'button:not([disabled]), [href]:not([tabindex="-1"]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
    return Array.from(root.querySelectorAll<HTMLElement>(selector)).filter(
        (el) => !(el as any).disabled && el.getAttribute("aria-hidden") !== "true" && el.getAttribute("hidden") === null
    );
}

function focusFirst() {
    const focusable = getFocusableElements();
    if (focusable.length > 0) {
        focusable[0].focus();
    }
}

function handleFocusTrap(e: KeyboardEvent) {
    if (e.key !== "Tab") return;
    const focusable = getFocusableElements();
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
}

function attachFocusTrap() {
    detachFocusTrap();
    focusTrapHandler = (e: KeyboardEvent) => handleFocusTrap(e);
    if (dialog.value) {
        dialog.value.addEventListener("keydown", focusTrapHandler, true);
    }
}

function detachFocusTrap() {
    if (focusTrapHandler && dialog.value) {
        dialog.value.removeEventListener("keydown", focusTrapHandler, true);
    }
    focusTrapHandler = null;
}
</script>
