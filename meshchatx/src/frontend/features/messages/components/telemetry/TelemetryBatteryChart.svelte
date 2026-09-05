<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../../js/i18n.js";
    import {
        buildTelemetryBatteryChartSpec,
        clampBatteryPercent,
        interpolateBatteryByTime,
    } from "../../../../js/telemetryBatteryChartSpec.js";
    import { formatDate } from "../../../../libs/datetime.js";

    export type BatterySample = {
        x: number;
        y: number;
    };

    type HoverPoint = {
        gx: number;
        gy: number;
        pct: number;
        timeLabel: string;
        tipLeft: number;
        tipTop: number;
    };

    let {
        samples,
        idSuffix = "default",
    }: {
        samples: BatterySample[];
        idSuffix?: string;
    } = $props();

    let chartSvg: SVGSVGElement | undefined = $state();
    let chartWrap: HTMLDivElement | undefined = $state();
    let hover: HoverPoint | null = $state(null);

    const spec = $derived(buildTelemetryBatteryChartSpec(samples, idSuffix));
    const firstPct = $derived(samples.length ? Math.round(samples[0].y) : 0);
    const lastPct = $derived(samples.length ? Math.round(samples[samples.length - 1].y) : 0);
    const startLabel = $derived(samples.length ? formatDate(samples[0].x * 1000, "MMM D, HH:mm") : "");
    const endLabel = $derived(samples.length ? formatDate(samples[samples.length - 1].x * 1000, "MMM D, HH:mm") : "");

    function svgPointFromClient(clientX: number, clientY: number): DOMPoint | null {
        const ctm = chartSvg?.getScreenCTM();
        if (!ctm) return null;
        return new DOMPoint(clientX, clientY).matrixTransform(ctm.inverse());
    }

    function updateHoverFromClient(clientX: number, clientY: number) {
        if (!spec) return;
        const point = svgPointFromClient(clientX, clientY);
        if (!point) return;

        const { PL, PR, PT, PB, minX, maxX } = spec.layout;
        const gx = Math.min(Math.max(point.x, PL), PR);
        const rangeX = maxX - minX || 1;
        const timestamp = minX + ((gx - PL) / (PR - PL)) * rangeX;
        const { y } = interpolateBatteryByTime(samples, timestamp);
        const gy = PT + (1 - clampBatteryPercent(y) / 100) * (PB - PT);
        const bounds = chartWrap?.getBoundingClientRect();
        const tipLeft = bounds ? Math.min(Math.max(clientX - bounds.left, 10), Math.max(10, bounds.width - 10)) : 0;
        const tipTop = bounds ? clientY - bounds.top : 0;

        hover = {
            gx,
            gy,
            pct: Math.round(y),
            timeLabel: formatDate(timestamp * 1000, "MMM D, HH:mm"),
            tipLeft,
            tipTop,
        };
    }

    function onPointer(event: PointerEvent) {
        updateHoverFromClient(event.clientX, event.clientY);
    }
</script>

{#if spec}
    <div class="space-y-2">
        <div class="flex items-start justify-between gap-2 border-b border-gray-200/70 pb-2 dark:border-zinc-700/70">
            <div class="flex items-center gap-2 min-w-0">
                <MaterialDesignIcon iconName="battery-high" class="size-4 shrink-0 text-sky-600 dark:text-sky-400" />
                <span class="text-[11px] font-semibold uppercase tracking-wide text-sem-fg-muted truncate">
                    {t("messages.telemetry_battery_trend")}
                </span>
            </div>
            <span class="text-[11px] tabular-nums font-medium text-sem-fg-muted shrink-0">
                {t("messages.telemetry_battery_range", { from: firstPct, to: lastPct })}
            </span>
        </div>
        <div class="flex gap-1.5">
            <div
                class="flex flex-col justify-between text-[9px] font-medium text-sem-fg-muted pr-0.5 pt-0.5 pb-6 w-5 text-right tabular-nums select-none"
            >
                <span>100</span>
                <span>75</span>
                <span>50</span>
                <span>25</span>
                <span>0</span>
            </div>
            <div
                bind:this={chartWrap}
                class="relative flex-1 min-w-0 cursor-crosshair touch-none"
                onpointerdown={onPointer}
                onpointermove={onPointer}
                onpointerleave={() => (hover = null)}
                role="presentation"
            >
                <svg
                    bind:this={chartSvg}
                    class="block h-44 w-full text-sky-600 dark:text-sky-400"
                    viewBox={spec.viewBox}
                    role="img"
                    aria-label={t("messages.telemetry_battery_trend")}
                >
                    <defs>
                        <linearGradient id={spec.gradientId} x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" stop-color="rgb(14, 165, 233)" stop-opacity="0.38" />
                            <stop offset="55%" stop-color="rgb(56, 189, 248)" stop-opacity="0.14" />
                            <stop offset="100%" stop-color="rgb(125, 211, 252)" stop-opacity="0.03" />
                        </linearGradient>
                        <linearGradient id={spec.strokeGradientId} x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stop-color="rgb(2, 132, 199)" />
                            <stop offset="100%" stop-color="rgb(14, 165, 233)" />
                        </linearGradient>
                    </defs>
                    <g class="text-gray-200/90 dark:text-zinc-700/90" stroke="currentColor" stroke-width="0.5">
                        {#each spec.gridLines as gridLine (gridLine.label)}
                            <line
                                x1="0"
                                x2="100"
                                y1={gridLine.y1}
                                y2={gridLine.y2}
                                vector-effect="non-scaling-stroke"
                            />
                        {/each}
                    </g>
                    <path d={spec.areaPath} fill={`url(#${spec.gradientId})`} stroke="none" />
                    <path
                        d={spec.linePath}
                        fill="none"
                        stroke={`url(#${spec.strokeGradientId})`}
                        stroke-width="1.25"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        vector-effect="non-scaling-stroke"
                    />
                    <circle
                        cx={spec.first.x}
                        cy={spec.first.y}
                        r="1.5"
                        fill="white"
                        class="dark:fill-zinc-900"
                        stroke="rgb(2, 132, 199)"
                        stroke-width="1"
                        vector-effect="non-scaling-stroke"
                    />
                    <circle
                        cx={spec.last.x}
                        cy={spec.last.y}
                        r="2"
                        fill="rgb(14, 165, 233)"
                        stroke="white"
                        stroke-width="0.85"
                        class="dark:stroke-zinc-900"
                        vector-effect="non-scaling-stroke"
                    />
                    {#if hover}
                        <line
                            x1={hover.gx}
                            x2={hover.gx}
                            y1={spec.layout.PT}
                            y2={spec.plotBottom}
                            stroke="currentColor"
                            class="text-sky-600/70 dark:text-sky-400/80"
                            stroke-width="0.65"
                            stroke-dasharray="3 2.5"
                            vector-effect="non-scaling-stroke"
                            stroke-linecap="round"
                        />
                        <circle
                            cx={hover.gx}
                            cy={hover.gy}
                            r="2"
                            fill="white"
                            class="dark:fill-zinc-900"
                            stroke="rgb(2, 132, 199)"
                            stroke-width="1"
                            vector-effect="non-scaling-stroke"
                        />
                    {/if}
                </svg>
                {#if hover}
                    <div
                        class="pointer-events-none absolute z-10 rounded-md border border-sky-200/90 bg-white/95 px-2 py-1 text-[10px] font-semibold tabular-nums text-sky-900 shadow-md dark:border-sky-800 dark:bg-zinc-900/95 dark:text-sky-100"
                        style:left={`${hover.tipLeft}px`}
                        style:top={`${hover.tipTop}px`}
                        style:transform="translate(-50%, calc(-100% - 6px))"
                    >
                        <div>{hover.pct}%</div>
                        <div class="font-normal text-sem-fg-muted">{hover.timeLabel}</div>
                    </div>
                {/if}
                <div
                    class="pointer-events-none absolute inset-x-0 bottom-0 flex h-6 justify-between px-0.5 text-[9px] tabular-nums text-sem-fg-muted"
                >
                    <span class="truncate max-w-[45%]">{startLabel}</span>
                    <span class="truncate max-w-[45%] text-right">{endLabel}</span>
                </div>
            </div>
        </div>
    </div>
{/if}
