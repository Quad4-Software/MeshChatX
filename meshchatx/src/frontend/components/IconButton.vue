<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <button
        type="button"
        class="text-gray-500 hover:text-sem-fg-muted dark:hover:text-zinc-100 hover:bg-sem-surface-muted p-2 rounded-full w-9 h-9 flex items-center justify-center shrink-0 transition-all duration-200"
    >
        <slot />
    </button>
</template>

<script>
export default {
    name: "IconButton",
};
</script>
