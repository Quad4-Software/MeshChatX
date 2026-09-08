<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-3">
        <div
            v-if="errorMessage"
            class="flex items-start gap-2 p-3 rounded-xl bg-sem-danger/10 border border-sem-danger/40"
            role="alert"
        >
            <MaterialDesignIcon icon-name="alert-circle" class="size-4 mt-0.5 text-sem-danger shrink-0" />
            <span class="text-xs text-sem-danger wrap-break-word">{{ errorMessage }}</span>
        </div>

        <button
            :disabled="!canFlash || isFlashing"
            data-testid="rnode-flash-btn"
            class="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-sem-action-primary hover:bg-sem-action-primary-hover px-4 py-3 text-sm font-bold text-white shadow-lg shadow-sem-action-primary/20 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
            @click="$emit('flash')"
        >
            <MaterialDesignIcon v-if="isFlashing" icon-name="loading" class="size-4 animate-spin text-white" />
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
            <div class="h-2 overflow-hidden rounded-full bg-sem-surface-muted">
                <div
                    class="h-full rounded-full bg-sem-action-primary transition-[width]"
                    :style="{ width: `${flashingProgress}%` }"
                />
            </div>
            <div class="flex items-center justify-between text-[10px] font-mono">
                <span class="text-sem-fg-muted truncate">{{ flashingStatus }}</span>
                <span class="text-sem-fg-muted font-bold">{{ flashingProgress }}%</span>
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
