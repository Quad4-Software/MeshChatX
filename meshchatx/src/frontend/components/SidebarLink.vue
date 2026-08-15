<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <RouterLink v-slot="{ href, navigate, isActive }" :to="to" custom>
        <a
            :href="href"
            type="button"
            :draggable="false"
            :class="[
                collapsedActiveClass(isActive),
                isCollapsed ? 'overflow-visible justify-center rounded-none' : 'overflow-hidden rounded-r-full mr-2',
            ]"
            class="w-full text-gray-800 dark:text-zinc-200 group flex gap-x-3 p-2 text-sm leading-6 font-semibold focus-visible:outline-solid focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 dark:focus-visible:outline-zinc-500"
            @click="handleNavigate($event, navigate)"
        >
            <span class="my-auto shrink-0">
                <slot name="icon"></slot>
            </span>
            <span v-if="!isCollapsed" class="my-auto flex w-full truncate transition-all duration-300">
                <slot name="text"></slot>
            </span>
        </a>
    </RouterLink>
</template>

<script>
export default {
    name: "SidebarLink",
    props: {
        to: {
            type: Object,
            required: true,
        },
        isCollapsed: {
            type: Boolean,
            default: false,
        },
        editMode: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["click"],
    methods: {
        collapsedActiveClass(isActive) {
            if (this.isCollapsed && isActive) {
                return [
                    "text-blue-800 dark:text-blue-300",
                    "bg-black/[0.04] dark:bg-black/40",
                    "shadow-[inset_2px_2px_5px_rgba(0,0,0,0.18),inset_-1px_-1px_2px_rgba(255,255,255,0.8)]",
                    "dark:shadow-[inset_2px_2px_6px_rgba(0,0,0,0.72),inset_-1px_-1px_1px_rgba(255,255,255,0.07)]",
                ].join(" ");
            }
            if (isActive) {
                return "bg-blue-100 text-blue-800 group:text-blue-800 dark:bg-zinc-800 dark:text-blue-300";
            }
            return "hover:bg-gray-100 dark:hover:bg-zinc-700";
        },
        handleNavigate(event, navigate) {
            this.$emit("click");
            if (this.editMode) {
                event.preventDefault();
                return;
            }
            navigate(event);
        },
    },
};
</script>
