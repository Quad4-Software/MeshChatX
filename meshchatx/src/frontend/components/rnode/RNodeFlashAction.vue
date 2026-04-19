<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-3">
        <div
            v-if="errorMessage"
            class="flex items-start gap-2 p-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"
            role="alert"
        >
            <MaterialDesignIcon
                icon-name="alert-circle"
                class="size-4 mt-0.5 text-red-600 dark:text-red-400 shrink-0"
            />
            <span class="text-xs text-red-600 dark:text-red-400 break-words">{{ errorMessage }}</span>
        </div>

        <button
            :disabled="!canFlash || isFlashing"
            data-testid="rnode-flash-btn"
            class="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-green-600 hover:bg-green-700 px-4 py-3 text-sm font-bold text-white shadow-lg shadow-green-600/20 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
            @click="$emit('flash')"
        >
            <v-progress-circular v-if="isFlashing" indeterminate size="16" width="2" />
            <MaterialDesignIcon v-else icon-name="flash" class="size-5" />
            <span>
                {{
                    isFlashing
                        ? $t("tools.rnode_flasher.flashing", { percentage: flashingProgress })
                        : $t("tools.rnode_flasher.flash_now")
                }}
            </span>
        </button>

        <div v-if="isFlashing" class="space-y-1.5 pt-1" role="status" aria-live="polite">
            <v-progress-linear :model-value="flashingProgress" color="green" height="8" rounded />
            <div class="flex items-center justify-between text-[10px] font-mono">
                <span class="text-gray-500 dark:text-zinc-500 truncate">{{ flashingStatus }}</span>
                <span class="text-gray-700 dark:text-zinc-300 font-bold">{{ flashingProgress }}%</span>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "RNodeFlashAction",
    components: { MaterialDesignIcon },
    props: {
        canFlash: { type: Boolean, default: false },
        isFlashing: { type: Boolean, default: false },
        flashingProgress: { type: Number, default: 0 },
        flashingStatus: { type: String, default: "" },
        errorMessage: { type: String, default: null },
    },
    emits: ["flash"],
};
</script>
