<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div
        v-click-outside="{ handler: onClickOutsideMenu, capture: true }"
        class="cursor-default relative inline-block text-left"
    >
        <!-- menu button -->
        <div ref="dropdown-button" @click.stop="toggleMenu">
            <slot>
                <div
                    class="size-8 border border-sem-border rounded-sm shadow-sm cursor-pointer"
                    :style="{ 'background-color': colour }"
                ></div>
            </slot>
        </div>

        <!-- drop down menu -->
        <Transition
            enter-active-class="transition ease-out duration-100"
            enter-from-class="transform opacity-0 scale-95"
            enter-to-class="transform opacity-100 scale-100"
            leave-active-class="transition ease-in duration-75"
            leave-from-class="transform opacity-100 scale-100"
            leave-to-class="transform opacity-0 scale-95"
        >
            <div
                v-if="isShowingMenu"
                class="absolute left-0 z-100 mt-2 rounded-xl border border-sem-border bg-sem-surface p-3 shadow-xl"
            >
                <input
                    :value="normalizedColour"
                    type="color"
                    class="block h-10 w-full cursor-pointer rounded-lg border border-sem-border bg-transparent p-0"
                    @input="onNativeColorInput"
                />
                <div class="mt-2 grid grid-cols-6 gap-1.5">
                    <button
                        v-for="swatch in swatches"
                        :key="swatch"
                        type="button"
                        class="size-6 rounded-md border border-sem-border"
                        :style="{ backgroundColor: swatch }"
                        :title="swatch"
                        @click="selectSwatch(swatch)"
                    ></button>
                </div>
            </div>
        </Transition>
    </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";

const DEFAULT_SWATCHES = [
    "#ef4444",
    "#f97316",
    "#eab308",
    "#22c55e",
    "#3b82f6",
    "#8b5cf6",
    "#ec4899",
    "#64748b",
    "#ffffff",
    "#18181b",
    "#0ea5e9",
    "#14b8a6",
];

function normalizeHexColour(value: unknown): string {
    if (typeof value !== "string") {
        return "";
    }
    let hex = value.trim();
    if (hex.length === 9) {
        hex = hex.substring(0, 7);
    }
    if (/^#[0-9a-fA-F]{6}$/.test(hex)) {
        return hex.toLowerCase();
    }
    return "";
}

const props = withDefaults(
    defineProps<{
        colour?: string;
    }>(),
    {
        colour: "",
    }
);

const emit = defineEmits<{
    "update:colour": [value: string];
}>();

const isShowingMenu = ref(false);
const swatches = DEFAULT_SWATCHES;

const normalizedColour = computed(() => normalizeHexColour(props.colour) || "#3b82f6");

function toggleMenu() {
    if (isShowingMenu.value) {
        hideMenu();
    } else {
        showMenu();
    }
}

function showMenu() {
    isShowingMenu.value = true;
}

function hideMenu() {
    isShowingMenu.value = false;
}

function onClickOutsideMenu(event: Event) {
    if (isShowingMenu.value) {
        // Do not suppress contextmenu: right-click outside the picker
        // should dismiss it without killing the native context menu.
        if (event.type === "click") {
            event.preventDefault();
        }
        hideMenu();
    }
}

function onNativeColorInput(event: Event) {
    const value = (event?.target as HTMLInputElement)?.value;
    if (typeof value === "string" && value) {
        emit("update:colour", normalizeHexColour(value));
    }
}

function selectSwatch(value: string) {
    emit("update:colour", normalizeHexColour(value));
}
</script>
