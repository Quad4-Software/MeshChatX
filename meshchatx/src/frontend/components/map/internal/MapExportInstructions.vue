<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="absolute top-4 left-1/2 -translate-x-1/2 z-20 px-4 py-2 bg-blue-600 text-white rounded-full shadow-lg font-medium text-sm animate-bounce"
    >
        {{ $t("map.export_instructions") }}
    </div>
</template>

<script>
export default {
    name: "MapExportInstructions",
};
</script>
