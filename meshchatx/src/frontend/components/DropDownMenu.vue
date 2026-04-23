<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div
        v-click-outside="{ handler: onClickOutsideMenu, capture: true }"
        class="cursor-default relative inline-block text-left"
    >
        <!-- menu button -->
        <div ref="dropdown-button" class="touch-manipulation" @click.stop="toggleMenu">
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
                    class="overflow-x-hidden fixed z-[200] w-56 rounded-md bg-white dark:bg-zinc-800 shadow-lg border border-gray-200 dark:border-zinc-700 focus:outline-none"
                    :style="dropdownPanelStyle"
                    @click.stop="hideMenu"
                >
                    <slot name="items" />
                </div>
            </Transition>
        </Teleport>
    </div>
</template>

<script>
import { clampFloatingToViewport } from "../js/clampFloatingToViewport.js";

export default {
    name: "DropDownMenu",
    data() {
        return {
            isShowingMenu: false,
            dropdownPosition: null,
        };
    },
    computed: {
        dropdownPanelStyle() {
            if (!this.dropdownPosition) {
                return {};
            }
            const style = {
                left: `${this.dropdownPosition.x}px`,
                top: `${this.dropdownPosition.y}px`,
            };
            if (this.dropdownPosition.maxHeight != null) {
                style.maxHeight = `${this.dropdownPosition.maxHeight}px`;
                style.overflowY = "auto";
            } else {
                style.overflow = "hidden";
            }
            return style;
        },
    },
    methods: {
        toggleMenu() {
            if (this.isShowingMenu) {
                this.hideMenu();
            } else {
                this.showMenu();
            }
        },
        showMenu() {
            this.isShowingMenu = true;
            this.adjustDropdownPosition();
        },
        hideMenu() {
            this.isShowingMenu = false;
            this.dropdownPosition = null;
        },
        onClickOutsideMenu() {
            if (this.isShowingMenu) {
                this.hideMenu();
            }
        },
        adjustDropdownPosition() {
            this.$nextTick(() => {
                const button = this.$refs["dropdown-button"];
                if (!button) return;

                const buttonRect = button.getBoundingClientRect();
                const menuWidth = 224;
                let x = buttonRect.right - menuWidth;
                x = Math.min(Math.max(8, x), window.innerWidth - menuWidth - 8);

                const spaceBelow = window.innerHeight - buttonRect.bottom - 4;
                const spaceAbove = buttonRect.top - 8;
                let y = spaceBelow >= spaceAbove ? buttonRect.bottom + 4 : Math.max(8, buttonRect.top - 200 - 4);

                this.dropdownPosition = { x, y, maxHeight: null };
                this.$nextTick(() => {
                    const panel = this.$refs.dropdownPanel;
                    if (!panel) return;
                    const rect = panel.getBoundingClientRect();
                    const { left, top, maxHeight } = clampFloatingToViewport(rect.left, rect.top, rect.width, rect.height);
                    this.dropdownPosition = { x: left, y: top, maxHeight };
                });
            });
        },
    },
};
</script>
