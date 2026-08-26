<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div v-if="show" class="fixed inset-0 z-100 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs">
        <div
            class="bg-sem-surface w-full max-w-md rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200"
        >
            <div class="p-6">
                <h2 class="text-xl font-bold text-sem-fg flex items-center gap-2">
                    <MaterialDesignIcon icon-name="content-save-outline" class="size-6 text-blue-500" />
                    {{ $t("map.save_drawing_title") }}
                </h2>
                <p class="text-sm text-sem-fg-muted mt-1">{{ $t("map.save_drawing_desc") }}</p>

                <div class="mt-6">
                    <label class="block text-xs font-bold text-sem-fg-muted uppercase tracking-widest mb-2">
                        {{ $t("map.drawing_name") }}
                    </label>
                    <input
                        ref="newDrawingNameInput"
                        :value="name"
                        type="text"
                        class="w-full px-4 py-3 bg-gray-50 dark:bg-zinc-800 border-none rounded-xl text-sm focus:ring-2 focus:ring-blue-500 transition-all dark:text-white"
                        :placeholder="$t('map.drawing_name_placeholder')"
                        @input="$emit('update:name', $event.target.value)"
                        @keyup.enter="$emit('save')"
                    />
                </div>

                <div class="mt-8 flex gap-3">
                    <button
                        type="button"
                        class="flex-1 px-4 py-2.5 rounded-xl border border-sem-border text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-sem-surface-muted transition"
                        @click="$emit('close')"
                    >
                        {{ $t("common.close") }}
                    </button>
                    <button
                        type="button"
                        class="flex-1 px-4 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-semibold shadow-lg shadow-blue-500/25 hover:bg-blue-500 transition active:scale-95 disabled:opacity-50"
                        :disabled="!String(name || '').trim()"
                        @click="$emit('save')"
                    >
                        {{ $t("common.save") }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";

export default {
    name: "MapSaveDrawingModal",
    components: {
        MaterialDesignIcon,
    },
    props: {
        show: {
            type: Boolean,
            default: false,
        },
        name: {
            type: String,
            default: "",
        },
    },
    emits: ["close", "save", "update:name"],
    methods: {
        focusNameInput() {
            this.$nextTick(() => {
                this.$refs.newDrawingNameInput?.focus?.();
            });
        },
    },
};
</script>
