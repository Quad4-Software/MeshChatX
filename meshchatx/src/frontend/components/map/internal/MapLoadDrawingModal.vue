<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div v-if="show" class="fixed inset-0 z-100 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs">
        <div
            class="bg-sem-surface w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200"
        >
            <div class="p-6">
                <div class="flex items-center justify-between mb-6">
                    <h2 class="text-xl font-bold text-sem-fg flex items-center gap-2">
                        <MaterialDesignIcon icon-name="folder-open-outline" class="size-6 text-sem-info" />
                        {{ $t("map.load_drawing_title") }}
                    </h2>
                    <button class="text-sem-fg-muted hover:text-sem-fg-secondary" @click="$emit('close')">
                        <MaterialDesignIcon icon-name="close" class="size-6" />
                    </button>
                </div>

                <div v-if="loading" class="py-12 flex flex-col items-center justify-center">
                    <MaterialDesignIcon icon-name="loading" class="size-10 animate-spin text-sem-info mb-4" />
                    <span class="text-sm font-medium text-sem-fg-muted">{{ $t("map.loading_drawings") }}</span>
                </div>

                <div
                    v-else-if="drawings.length === 0"
                    class="py-12 flex flex-col items-center justify-center text-center"
                >
                    <div class="size-16 bg-sem-surface-muted rounded-full flex items-center justify-center mb-4">
                        <MaterialDesignIcon icon-name="folder-outline" class="size-8 text-sem-fg-muted" />
                    </div>
                    <h3 class="text-lg font-bold text-sem-fg">{{ $t("map.no_drawings") }}</h3>
                    <p class="text-sm text-sem-fg-muted mt-1">{{ $t("map.no_drawings_desc") }}</p>
                </div>

                <div v-else class="max-h-[400px] overflow-y-auto space-y-2 pr-2">
                    <div
                        v-for="drawing in drawings"
                        :key="drawing.id"
                        class="group p-4 bg-sem-surface-muted/50 hover:bg-sem-info/15 dark:hover:bg-sem-info/15 rounded-2xl border border-transparent hover:border-sem-info dark:hover:border-sem-info transition-all cursor-pointer flex items-center justify-between"
                        @click="$emit('load', drawing)"
                    >
                        <div class="flex-1 min-w-0 mr-4">
                            <div class="font-bold text-sem-fg truncate">{{ drawing.name }}</div>
                            <div class="text-xs text-sem-fg-muted mt-0.5">
                                {{ $t("map.saved_on") }} {{ new Date(drawing.updated_at).toLocaleString() }}
                            </div>
                        </div>
                        <button
                            class="p-2 text-sem-fg-muted hover:text-sem-danger transition-colors"
                            :title="$t('common.delete')"
                            @click.stop="$emit('delete', drawing)"
                        >
                            <MaterialDesignIcon icon-name="trash-can-outline" class="size-5" />
                        </button>
                    </div>
                </div>

                <div class="mt-8 flex justify-end">
                    <button
                        type="button"
                        class="px-6 py-2.5 rounded-xl border border-sem-border text-sm font-semibold text-sem-fg hover:bg-sem-surface-muted transition"
                        @click="$emit('close')"
                    >
                        {{ $t("common.close") }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";

export default {
    name: "MapLoadDrawingModal",
    components: {
        MaterialDesignIcon,
    },
    props: {
        show: {
            type: Boolean,
            default: false,
        },
        loading: {
            type: Boolean,
            default: false,
        },
        drawings: {
            type: Array,
            default: () => [],
        },
    },
    emits: ["close", "load", "delete"],
};
</script>
