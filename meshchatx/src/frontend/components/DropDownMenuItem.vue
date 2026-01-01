<template>
    <div
        class="cursor-pointer flex p-3 space-x-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-zinc-700"
    >
        <slot />
    </div>
</template>

<script>
export default {
    name: "DropDownMenuItem",
};
</script>
