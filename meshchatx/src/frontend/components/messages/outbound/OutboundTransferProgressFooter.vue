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

<script>
export default {
    name: "OutboundTransferProgressFooter",
    props: {
        lxmfMessage: {
            type: Object,
            required: true,
        },
        chatItem: {
            type: Object,
            required: true,
        },
        cv: {
            type: Object,
            required: true,
        },
        variant: {
            type: String,
            default: "bubble",
            validator: (value) => ["bubble", "image"].includes(value),
        },
    },
    computed: {
        statsLabel() {
            return this.cv.outboundTransferStatsLabel(this.lxmfMessage, this.chatItem);
        },
        shellClass() {
            if (this.variant === "image") {
                return "bg-black/75 backdrop-blur-md px-2.5 py-1.5";
            }
            return "border-t border-black/8 dark:border-white/10 bg-black/[0.04] dark:bg-white/[0.05] px-3 py-1.5";
        },
        trackClass() {
            return this.variant === "image" ? "bg-white/20" : "bg-gray-200/90 dark:bg-zinc-700/90";
        },
        barClass() {
            return this.variant === "image" ? "bg-white" : "bg-blue-500 dark:bg-blue-400";
        },
        percentClass() {
            return this.variant === "image" ? "text-white/95" : "text-gray-500 dark:text-zinc-400";
        },
        statsClass() {
            return this.variant === "image" ? "text-white/75" : "text-gray-400 dark:text-zinc-500";
        },
    },
};
</script>
