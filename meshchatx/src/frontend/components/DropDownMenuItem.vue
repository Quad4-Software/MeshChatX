<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="cursor-pointer flex p-3 space-x-2 text-sm text-sem-fg hover:bg-sem-surface-muted">
        <slot />
    </div>
</template>

<script>
export default {
    name: "DropDownMenuItem",
};
</script>
