<template>
    <RouterLink v-slot="{ href, navigate, isActive }" :to="to" custom>
        <a
            :href="href"
            type="button"
            :class="[
                isActive
                    ? 'bg-blue-100 text-blue-800 group:text-blue-800 dark:bg-zinc-800 dark:text-blue-300'
                    : 'hover:bg-gray-100 dark:hover:bg-zinc-700',
            ]"
            class="w-full text-gray-800 dark:text-zinc-200 group flex gap-x-3 rounded-r-full p-2 mr-2 text-sm leading-6 font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 dark:focus-visible:outline-zinc-500 overflow-hidden"
            @click="handleNavigate($event, navigate)"
        >
            <span class="my-auto shrink-0">
                <slot name="icon"></slot>
            </span>
            <span v-if="!isCollapsed" class="my-auto flex w-full truncate">
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
    },
    emits: ["click"],
    methods: {
        handleNavigate(event, navigate) {
            // emit click event for SidebarLink element
            this.$emit("click");

            // handle navigation
            navigate(event);
        },
    },
};
</script>
