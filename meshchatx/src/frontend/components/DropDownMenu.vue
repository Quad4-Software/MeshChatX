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
                    class="overflow-hidden fixed z-[200] w-56 rounded-md bg-white dark:bg-zinc-800 shadow-lg border border-gray-200 dark:border-zinc-700 focus:outline-none"
                    :style="{
                        left: dropdownPosition.x + 'px',
                        top: dropdownPosition.y + 'px',
                    }"
                    @click.stop="hideMenu"
                >
                    <slot name="items" />
                </div>
            </Transition>
        </Teleport>
    </div>
</template>

<script>
export default {
    name: "DropDownMenu",
    data() {
        return {
            isShowingMenu: false,
            dropdownPosition: null,
        };
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
                const estimatedHeight = 200;
                const spaceBelow = window.innerHeight - buttonRect.bottom;
                const spaceAbove = buttonRect.top;

                let x = buttonRect.right - 224;
                if (x < 8) x = 8;
                if (x + 224 > window.innerWidth) x = window.innerWidth - 224 - 8;

                let y;
                if (spaceBelow >= estimatedHeight || spaceBelow >= spaceAbove) {
                    y = buttonRect.bottom + 4;
                } else {
                    y = buttonRect.top - estimatedHeight - 4;
                }
                if (y < 8) y = 8;
                if (y + estimatedHeight > window.innerHeight - 8) y = window.innerHeight - estimatedHeight - 8;

                this.dropdownPosition = { x, y };
            });
        },
    },
};
</script>
