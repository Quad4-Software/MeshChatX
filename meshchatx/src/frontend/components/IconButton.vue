<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <button
        type="button"
        class="icon-btn-sem press-feedback text-sem-fg-muted hover:text-sem-fg hover:bg-sem-surface-muted p-2 rounded-full min-w-11 min-h-11 w-11 h-11 flex items-center justify-center shrink-0 transition-colors duration-200 focus-ring-sem"
    >
        <slot />
    </button>
</template>

<script>
export default {
    name: "IconButton",
};
</script>
