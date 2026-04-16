<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <button
        type="button"
        class="text-gray-500 hover:text-gray-700 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-gray-100 dark:hover:bg-zinc-800 p-2 rounded-full w-9 h-9 flex items-center justify-center flex-shrink-0 transition-all duration-200"
    >
        <slot />
    </button>
</template>

<script>
export default {
    name: "IconButton",
};
</script>
