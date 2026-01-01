<template>
    <div
        v-click-outside="{ handler: onClickOutsideMenu, capture: true }"
        class="cursor-default relative inline-block text-left"
    >
        <!-- menu button -->
        <div ref="dropdown-button" @click.stop="toggleMenu">
            <slot name="button" />
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
                class="overflow-hidden absolute right-0 z-50 mr-4 w-56 rounded-md bg-white dark:bg-zinc-800 shadow-lg border border-gray-200 dark:border-zinc-700 focus:outline-none"
                :class="[dropdownClass]"
                @click.stop="hideMenu"
            >
                <slot name="items" />
            </div>
        </Transition>
    </div>
</template>

<script>
export default {
    name: "DropDownMenu",
    data() {
        return {
            isShowingMenu: false,
            dropdownClass: null,
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
        },
        onClickOutsideMenu(event) {
            if (this.isShowingMenu) {
                event.preventDefault();
                this.hideMenu();
            }
        },
        adjustDropdownPosition() {
            this.$nextTick(() => {
                // find button and dropdown
                const button = this.$refs["dropdown-button"];
                if (!button) {
                    return;
                }

                const dropdown = button.parentElement?.querySelector(".absolute");
                if (!dropdown) {
                    return;
                }

                // get bounding box of button
                const buttonRect = button.getBoundingClientRect();

                // calculate how much space is under and above the button
                const spaceBelowButton = window.innerHeight - buttonRect.bottom;
                const spaceAboveButton = buttonRect.top;

                // estimate dropdown height (will be measured after render)
                const estimatedDropdownHeight = 150;

                // calculate if there is enough space available to show dropdown
                const hasEnoughSpaceAboveButton = spaceAboveButton > estimatedDropdownHeight;
                const hasEnoughSpaceBelowButton = spaceBelowButton > estimatedDropdownHeight;

                // show dropdown above button
                if (hasEnoughSpaceAboveButton && !hasEnoughSpaceBelowButton) {
                    this.dropdownClass = "bottom-0 mb-12";
                    return;
                }

                // otherwise fallback to showing dropdown below button
                this.dropdownClass = "top-0 mt-12";
            });
        },
    },
};
</script>
