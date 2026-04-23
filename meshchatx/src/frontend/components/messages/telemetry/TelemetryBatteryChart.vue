<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div v-if="spec" class="space-y-2">
        <div class="flex items-start justify-between gap-2 border-b border-gray-200/70 pb-2 dark:border-zinc-700/70">
            <div class="flex items-center gap-2 min-w-0">
                <MaterialDesignIcon icon-name="battery-high" class="size-4 shrink-0 text-sky-600 dark:text-sky-400" />
                <span
                    class="text-[11px] font-semibold uppercase tracking-wide text-gray-500 dark:text-zinc-400 truncate"
                >
                    {{ $t("messages.telemetry_battery_trend") }}
                </span>
            </div>
            <span class="text-[11px] tabular-nums font-medium text-gray-600 dark:text-zinc-300 shrink-0">
                {{ $t("messages.telemetry_battery_range", { from: firstPct, to: lastPct }) }}
            </span>
        </div>
        <div class="flex gap-1.5">
            <div
                class="flex flex-col justify-between text-[9px] font-medium text-gray-400 dark:text-zinc-500 pr-0.5 pt-0.5 pb-6 w-5 text-right tabular-nums select-none"
            >
                <span>100</span>
                <span>75</span>
                <span>50</span>
                <span>25</span>
                <span>0</span>
            </div>
            <div
                ref="chartWrap"
                class="relative flex-1 min-w-0 cursor-crosshair touch-none"
                @mouseleave="onChartLeave"
                @mousemove="onChartMove"
                @touchstart="onChartTouch"
                @touchmove.prevent="onChartTouch"
                @touchend="onChartLeave"
            >
                <svg
                    ref="chartSvg"
                    class="block h-44 w-full text-sky-600 dark:text-sky-400"
                    :viewBox="spec.viewBox"
                    role="img"
                    :aria-label="$t('messages.telemetry_battery_trend')"
                >
                    <defs>
                        <linearGradient :id="spec.gradientId" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" stop-color="rgb(14, 165, 233)" stop-opacity="0.38" />
                            <stop offset="55%" stop-color="rgb(56, 189, 248)" stop-opacity="0.14" />
                            <stop offset="100%" stop-color="rgb(125, 211, 252)" stop-opacity="0.03" />
                        </linearGradient>
                        <linearGradient :id="spec.strokeGradientId" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stop-color="rgb(2, 132, 199)" />
                            <stop offset="100%" stop-color="rgb(14, 165, 233)" />
                        </linearGradient>
                    </defs>
                    <g class="text-gray-200/90 dark:text-zinc-700/90" stroke="currentColor" stroke-width="0.5">
                        <line
                            v-for="(g, idx) in spec.gridLines"
                            :key="idx"
                            :x1="0"
                            :x2="100"
                            :y1="g.y1"
                            :y2="g.y2"
                            vector-effect="non-scaling-stroke"
                        />
                    </g>
                    <path :d="spec.areaPath" :fill="`url(#${spec.gradientId})`" stroke="none" />
                    <path
                        :d="spec.linePath"
                        fill="none"
                        :stroke="`url(#${spec.strokeGradientId})`"
                        stroke-width="1.25"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        vector-effect="non-scaling-stroke"
                    />
                    <circle
                        :cx="spec.first.x"
                        :cy="spec.first.y"
                        r="1.5"
                        fill="white"
                        class="dark:fill-zinc-900"
                        stroke="rgb(2, 132, 199)"
                        stroke-width="1"
                        vector-effect="non-scaling-stroke"
                    />
                    <circle
                        :cx="spec.last.x"
                        :cy="spec.last.y"
                        r="2"
                        fill="rgb(14, 165, 233)"
                        stroke="white"
                        stroke-width="0.85"
                        class="dark:stroke-zinc-900"
                        vector-effect="non-scaling-stroke"
                    />
                    <g v-if="hover">
                        <line
                            :x1="hover.gx"
                            :x2="hover.gx"
                            :y1="spec.layout.PT"
                            :y2="spec.plotBottom"
                            stroke="currentColor"
                            class="text-sky-600/70 dark:text-sky-400/80"
                            stroke-width="0.65"
                            stroke-dasharray="3 2.5"
                            vector-effect="non-scaling-stroke"
                            stroke-linecap="round"
                        />
                        <circle
                            :cx="hover.gx"
                            :cy="hover.gy"
                            r="2"
                            fill="white"
                            class="dark:fill-zinc-900"
                            stroke="rgb(2, 132, 199)"
                            stroke-width="1"
                            vector-effect="non-scaling-stroke"
                        />
                    </g>
                </svg>
                <div
                    v-if="hover"
                    class="pointer-events-none absolute z-10 rounded-md border border-sky-200/90 bg-white/95 px-2 py-1 text-[10px] font-semibold tabular-nums text-sky-900 shadow-md dark:border-sky-800 dark:bg-zinc-900/95 dark:text-sky-100"
                    :style="hoverTipStyle"
                >
                    <div>{{ hover.pct }}%</div>
                    <div class="font-normal text-gray-500 dark:text-zinc-400">{{ hover.timeLabel }}</div>
                </div>
                <div
                    class="pointer-events-none absolute inset-x-0 bottom-0 flex h-6 justify-between px-0.5 text-[9px] tabular-nums text-gray-400 dark:text-zinc-500"
                >
                    <span class="truncate max-w-[45%]">{{ startLabel }}</span>
                    <span class="truncate max-w-[45%] text-right">{{ endLabel }}</span>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";
import {
    buildTelemetryBatteryChartSpec,
    clampBatteryPercent,
    interpolateBatteryByTime,
} from "../../../js/telemetryBatteryChartSpec.js";
import dayjs from "dayjs";

export default {
    name: "TelemetryBatteryChart",
    components: { MaterialDesignIcon },
    props: {
        samples: {
            type: Array,
            required: true,
        },
        idSuffix: {
            type: String,
            default: "default",
        },
    },
    data() {
        return {
            hover: null,
        };
    },
    computed: {
        spec() {
            return buildTelemetryBatteryChartSpec(this.samples, this.idSuffix);
        },
        firstPct() {
            if (!this.samples.length) return 0;
            return Math.round(this.samples[0].y);
        },
        lastPct() {
            if (!this.samples.length) return 0;
            return Math.round(this.samples[this.samples.length - 1].y);
        },
        startLabel() {
            if (!this.samples.length) return "";
            return dayjs(this.samples[0].x * 1000).format("MMM D, HH:mm");
        },
        endLabel() {
            if (!this.samples.length) return "";
            return dayjs(this.samples[this.samples.length - 1].x * 1000).format("MMM D, HH:mm");
        },
        hoverTipStyle() {
            if (!this.hover) return {};
            return {
                left: `${this.hover.tipLeft}px`,
                top: `${this.hover.tipTop}px`,
                transform: "translate(-50%, calc(-100% - 6px))",
            };
        },
    },
    methods: {
        svgPointFromClient(clientX, clientY) {
            const svg = this.$refs.chartSvg;
            if (!svg) return null;
            const ctm = svg.getScreenCTM();
            if (!ctm) return null;
            return new DOMPoint(clientX, clientY).matrixTransform(ctm.inverse());
        },
        updateHoverFromClient(clientX, clientY) {
            const spec = this.spec;
            if (!spec) return;
            const p = this.svgPointFromClient(clientX, clientY);
            if (!p) return;
            const { PL, PR, PT, PB, minX, maxX } = spec.layout;
            let gx = p.x;
            if (gx < PL) gx = PL;
            if (gx > PR) gx = PR;
            const rangeX = maxX - minX || 1;
            const ts = minX + ((gx - PL) / (PR - PL)) * rangeX;
            const { y } = interpolateBatteryByTime(this.samples, ts);
            const gy = PT + (1 - clampBatteryPercent(y) / 100) * (PB - PT);
            const wrap = this.$refs.chartWrap;
            let tipLeft = 0;
            let tipTop = 0;
            if (wrap) {
                const r = wrap.getBoundingClientRect();
                tipLeft = Math.min(Math.max(clientX - r.left, 10), Math.max(10, r.width - 10));
                tipTop = clientY - r.top;
            }
            this.hover = {
                gx,
                gy,
                pct: Math.round(y),
                timeLabel: dayjs(ts * 1000).format("MMM D, HH:mm"),
                tipLeft,
                tipTop,
            };
        },
        onChartMove(ev) {
            this.updateHoverFromClient(ev.clientX, ev.clientY);
        },
        onChartTouch(ev) {
            const t = ev.touches[0];
            if (t) this.updateHoverFromClient(t.clientX, t.clientY);
        },
        onChartLeave() {
            this.hover = null;
        },
    },
};
</script>
