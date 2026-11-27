<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div
        v-click-outside="{ handler: onClickOutsideMenu, capture: true }"
        class="cursor-default relative inline-block text-left"
    >
        <!-- menu button -->
        <div ref="dropdownButton" class="touch-manipulation" @click.stop="toggleMenu">
            <slot name="button" />
        </div>

        <Teleport to="body">
            <Transition
                enter-active-class="transition ease-out duration-100"
                enter-from-class="transform opacity-0 scale-95"
                enter-to-class="transform opacity-100 scale-100"
                leave-active-class="transition ease-in duration-75"
                leave-from-class="transform opacity-100 scale-100"
                leave-to-class="transform opacity-0 scale-95"
            >
                <div
                    v-if="isShowingMenu && dropdownPosition"
                    ref="dropdownPanel"
                    class="dropdown-panel overflow-x-hidden fixed z-200 w-56 focus:outline-hidden"
                    :style="dropdownPanelStyle"
                    @click.stop="hideMenu"
                >
                    <slot name="items" />
                </div>
            </Transition>
            <div
                v-if="isShowingMenu && caretStyle"
                class="dropdown-caret fixed z-200 border-sem-border"
                :class="dropdownPosition?.opensUp ? 'border-b border-r' : 'border-t border-l'"
                :style="caretStyle"
                aria-hidden="true"
            ></div>
        </Teleport>
    </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from "vue";
import { clampFloatingToViewport } from "../js/clampFloatingToViewport.js";

const isShowingMenu = ref(false);
const dropdownPosition = ref<Record<string, any> | null>(null);
const caretStyle = ref<Record<string, string> | null>(null);

const dropdownPanel = ref<HTMLElement | null>(null);
const dropdownButton = ref<HTMLElement | null>(null);

const dropdownPanelStyle = computed(() => {
    if (!dropdownPosition.value) {
        return {};
    }
    const style: Record<string, string> = {
        left: `${dropdownPosition.value.x}px`,
        top: `${dropdownPosition.value.y}px`,
    };
    if (dropdownPosition.value.maxHeight != null) {
        style.maxHeight = `${dropdownPosition.value.maxHeight}px`;
        style.overflowY = "auto";
    } else {
        style.overflow = "hidden";
    }
    return style;
});

function toggleMenu() {
    if (isShowingMenu.value) {
        hideMenu();
    } else {
        showMenu();
    }
}

function showMenu() {
    isShowingMenu.value = true;
    adjustDropdownPosition();
}

function hideMenu() {
    isShowingMenu.value = false;
    dropdownPosition.value = null;
    caretStyle.value = null;
}

function onClickOutsideMenu(event: Event) {
    // The panel is teleported to body, so it is not a descendant of
    // the element the click-outside directive watches. Touches on
    // menu items must not count as outside.
    const panel = dropdownPanel.value;
    if (event && panel) {
        const path = typeof event.composedPath === "function" ? event.composedPath() : null;
        if ((path && path.includes(panel)) || panel.contains(event.target as Node)) {
            return;
        }
    }
    if (isShowingMenu.value) {
        hideMenu();
    }
}

function adjustDropdownPosition() {
    nextTick(() => {
        const button = dropdownButton.value;
        if (!button) return;

        const buttonRect = button.getBoundingClientRect();
        const menuWidth = 224;
        let x = buttonRect.right - menuWidth;
        x = Math.min(Math.max(8, x), window.innerWidth - menuWidth - 8);

        const spaceBelow = window.innerHeight - buttonRect.bottom - 4;
        const spaceAbove = buttonRect.top - 8;
        const opensUp = spaceAbove > spaceBelow;
        const y = opensUp ? Math.max(8, buttonRect.top - 200 - 4) : buttonRect.bottom + 4;

        dropdownPosition.value = { x, y, maxHeight: null, opensUp };
        nextTick(() => {
            const panel = dropdownPanel.value;
            if (!panel) return;
            const rect = panel.getBoundingClientRect();
            const { left, top, maxHeight } = clampFloatingToViewport(rect.left, rect.top, rect.width, rect.height);
            dropdownPosition.value = { x: left, y: top, maxHeight, opensUp };
            const buttonCenterX = buttonRect.left + buttonRect.width / 2;
            const caretX = Math.min(Math.max(buttonCenterX, left + 12), left + rect.width - 12);
            caretStyle.value = {
                left: `${caretX - 5}px`,
                top: opensUp ? `${top + rect.height - 5}px` : `${top - 5}px`,
            };
        });
    });
}
</script>
