<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div v-if="cv.showOutboundTransferProgress(lxmfMessage)" class="w-full shrink-0" :class="shellClass">
        <div class="flex items-center gap-1.5">
            <div class="flex-1 h-1 rounded-full overflow-hidden" :class="trackClass">
                <div
                    class="h-full rounded-full transition-all duration-300"
                    :class="barClass"
                    :style="{ width: cv.outboundTransferProgressPercent(lxmfMessage) + '%' }"
                ></div>
            </div>
            <span class="text-[10px] font-semibold tabular-nums shrink-0" :class="percentClass">
                {{ cv.outboundSendingProgressLabel(lxmfMessage) }}
            </span>
        </div>
        <div v-if="statsLabel" class="text-[9px] tabular-nums truncate mt-0.5 leading-tight" :class="statsClass">
            {{ statsLabel }}
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
    defineProps<{
        lxmfMessage: Record<string, any>;
        chatItem: Record<string, any>;
        cv: Record<string, any>;
        variant?: "bubble" | "image";
    }>(),
    {
        variant: "bubble",
    }
);

const statsLabel = computed(() => props.cv.outboundTransferStatsLabel(props.lxmfMessage, props.chatItem));
const isImage = computed(() => props.variant === "image");
const shellClass = computed(() =>
    isImage.value
        ? "bg-black/75 backdrop-blur-md px-2.5 py-1.5"
        : "border-t border-black/8 dark:border-white/10 bg-black/[0.04] dark:bg-white/[0.05] px-3 py-1.5"
);
const trackClass = computed(() => (isImage.value ? "bg-white/20" : "bg-sem-surface-muted/90 bg-sem-surface"));
const barClass = computed(() => (isImage.value ? "bg-sem-surface" : "bg-sem-accent"));
const percentClass = computed(() => (isImage.value ? "text-white/95" : "text-sem-fg-muted"));
const statsClass = computed(() => (isImage.value ? "text-white/75" : "text-sem-fg-muted"));
</script>
