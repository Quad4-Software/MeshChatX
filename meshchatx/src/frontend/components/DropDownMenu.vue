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

<script>
import { clampFloatingToViewport } from "../js/clampFloatingToViewport.js";

export default {
    name: "DropDownMenu",
    data() {
        return {
            isShowingMenu: false,
            dropdownPosition: null,
            caretStyle: null,
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
            this.caretStyle = null;
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
                const opensUp = spaceAbove > spaceBelow;
                const y = opensUp ? Math.max(8, buttonRect.top - 200 - 4) : buttonRect.bottom + 4;

                this.dropdownPosition = { x, y, maxHeight: null, opensUp };
                this.$nextTick(() => {
                    const panel = this.$refs.dropdownPanel;
                    if (!panel) return;
                    const rect = panel.getBoundingClientRect();
                    const { left, top, maxHeight } = clampFloatingToViewport(
                        rect.left,
                        rect.top,
                        rect.width,
                        rect.height
                    );
                    this.dropdownPosition = { x: left, y: top, maxHeight, opensUp };
                    const buttonCenterX = buttonRect.left + buttonRect.width / 2;
                    const caretX = Math.min(Math.max(buttonCenterX, left + 12), left + rect.width - 12);
                    this.caretStyle = {
                        left: `${caretX - 5}px`,
                        top: opensUp ? `${top + rect.height - 5}px` : `${top - 5}px`,
                    };
                });
            });
        },
    },
};
</script>
