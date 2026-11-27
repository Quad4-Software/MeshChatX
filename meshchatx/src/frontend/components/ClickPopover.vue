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

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

defineOptions({ name: "ClickPopover" });

const props = withDefaults(
    defineProps<{
        modelValue?: boolean;
        placement?: string;
    }>(),
    {
        modelValue: false,
        placement: "bottom",
    }
);

const emit = defineEmits<{
    "update:modelValue": [value: boolean];
}>();

const open = ref(props.modelValue);
const panelStyle = ref<Record<string, string>>({});

const rootRef = ref<HTMLElement | null>(null);
const panelRef = ref<HTMLElement | null>(null);
const activatorRef = ref<HTMLElement | null>(null);

watch(
    () => props.modelValue,
    (value) => {
        open.value = value;
        if (value) {
            nextTick(() => positionPanel());
        }
    }
);

watch(open, (value) => {
    emit("update:modelValue", value);
});

let onDocClick: ((event: MouseEvent) => void) | null = null;
let onDocKeydown: ((event: KeyboardEvent) => void) | null = null;

onMounted(() => {
    onDocClick = (event: MouseEvent) => {
        if (!open.value) {
            return;
        }
        const target = event.target as Node;
        if (rootRef.value?.contains(target) || panelRef.value?.contains(target)) {
            return;
        }
        open.value = false;
    };
    onDocKeydown = (event: KeyboardEvent) => {
        if (event.key === "Escape" && open.value) {
            open.value = false;
        }
    };
    document.addEventListener("click", onDocClick, true);
    document.addEventListener("keydown", onDocKeydown);
});

onBeforeUnmount(() => {
    if (onDocClick) {
        document.removeEventListener("click", onDocClick, true);
    }
    if (onDocKeydown) {
        document.removeEventListener("keydown", onDocKeydown);
    }
});

function toggle() {
    open.value = !open.value;
    if (open.value) {
        nextTick(() => positionPanel());
    }
}

function positionPanel() {
    const activator = activatorRef.value;
    if (!activator || typeof activator.getBoundingClientRect !== "function") {
        return;
    }
    const rect = activator.getBoundingClientRect();
    const gap = 6;
    if (props.placement === "bottom") {
        panelStyle.value = {
            top: `${rect.bottom + gap}px`,
            left: `${rect.left}px`,
        };
        return;
    }
    panelStyle.value = {
        top: `${rect.bottom + gap}px`,
        left: `${rect.left}px`,
    };
}
</script>
